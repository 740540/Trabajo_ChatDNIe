# dnie_im/messenger.py - ALWAYS LOOKUP CURRENT NAME

"""
Main application coordinator.
FIXED: Always use current peer name from discovery, never session.peer.name (which might be IP).
"""

import asyncio
import secrets
import struct
from datetime import datetime
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from identity.im_identity import IMIdentity
from crypto.noise_ik import NoiseIKState
from crypto.protocol import ProtocolFrame
from network.transport import UDPTransport
from network.discovery import ServiceDiscovery
from session.session import Session, Peer
from session.contact_book import ContactBook
from session.chat_history import ChatHistoryManager
from session.message_queue import MessageQueue
from ui.tui import ChatTUI


class DNIeMessenger:
    """High-level orchestrator for the DNIe instant messenger."""

    def __init__(self, username: str):
        self.username = username
        self.identity = IMIdentity()
        self.noise = NoiseIKState()
        self.transport = UDPTransport()
        self.discovery: ServiceDiscovery | None = None
        self.tui = ChatTUI()
        self.contact_book = ContactBook()
        self.chat_history: ChatHistoryManager | None = None
        self.message_queue: MessageQueue | None = None
        self.running = False
        self.loop: asyncio.AbstractEventLoop | None = None

        # Peer-to-session mapping
        self.peer_sessions = {}

        # Track online peers
        self.online_peers = set()

        # Track handshake state to prevent loops
        self.handshake_initiated = set()

        # Wire TUI callbacks
        self.tui.message_send_callback = self.on_message_send
        self.tui.handshake_callback = self.manual_handshake

    def _get_current_peer_name(self, peer_id: str) -> str:
        """Look up current peer name from discovered_peers by peer_id."""
        if self.discovery:
            for p in self.discovery.discovered_peers.values():
                if p.peer_id == peer_id:
                    return p.name
        # Fallback to shortened peer_id if not found
        return f"peer_{peer_id[:8]}"

    async def initialize(self, pin: str):
        """Initialize DNIe identity, transport, mDNS, and chat history."""
        self.tui.append_chat("🚀 Inicializando DNIe Instant Messenger...")

        if not self.identity.authenticate_with_pin(pin):
            raise Exception("Autenticación DNIe fallida")

        cert_info = self.identity.get_certificate_info()
        self.tui.append_chat(f"👤 Usuario: {cert_info.get('common_name', 'Unknown')}")
        self.tui.append_chat(f"🔑 Peer ID: {cert_info.get('peer_id', 'Unknown')}")

        certificate = self.identity.certificate
        user_id = self.identity.peer_id or "unknown"

        # Encrypted history manager
        self.chat_history = ChatHistoryManager(user_id=user_id, certificate=certificate)

        # Encrypted message queue manager
        self.message_queue = MessageQueue(user_id=user_id, certificate=certificate)

        # Pass username AND peer_id to GUI
        if hasattr(self.tui, 'set_username'):
            self.tui.set_username(self.username)
        if hasattr(self.tui, 'set_my_peer_id'):
            self.tui.set_my_peer_id(self.identity.peer_id)

        # Start UDP transport
        await self.transport.start()

        # Start mDNS discovery + advertising
        self.discovery = ServiceDiscovery(self.identity)
        self.discovery.static_public_key = self.noise.get_static_public()
        self.discovery.on_peer_discovered_callback = self.on_peer_discovered
        self.discovery.on_peer_disconnected_callback = self.on_peer_disconnected
        self.discovery.on_peer_renamed_callback = self.on_peer_renamed
        await self.discovery.start_advertising(self.username)

        self.tui.append_chat("📡 Buscando peers en la red local...")

    def _should_initiate_to_peer(self, peer: Peer) -> bool:
        """
        Deterministic rule: only initiate if our peer_id is LOWER than theirs.
        This prevents crossing handshakes.
        """
        my_peer_id = self.identity.peer_id or ""
        their_peer_id = peer.peer_id or ""

        if not my_peer_id or not their_peer_id:
            print(f"[DEBUG] No peer IDs, using IP comparison")
            return True

        result = my_peer_id < their_peer_id
        print(f"[DEBUG] Should initiate to {peer.name}? {result} (my_id={my_peer_id[:8]}..., their_id={their_peer_id[:8]}...)")
        return result

    # ---------- Discovery callbacks ----------

    def on_peer_discovered(self, peer: Peer):
        """Called (in zeroconf thread) when a new peer is discovered."""
        print(f"[DEBUG] on_peer_discovered called for {peer.name} ({peer.peer_id})")
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._handle_peer_discovered(peer), self.loop)

    async def _handle_peer_discovered(self, peer: Peer):
        peer_id = peer.peer_id or f"{peer.address}:{peer.port}"

        was_offline = peer_id not in self.online_peers

        self.online_peers.add(peer_id)
        print(f"[DEBUG] Peer {peer.name} marked as ONLINE. Total online: {len(self.online_peers)}")

        if was_offline:
            self.tui.append_chat(f"🔍 Peer conectado: {peer.name} ({peer.peer_id})")
        else:
            self.tui.append_chat(f"🔄 Peer actualizado: {peer.name}")

        self.update_peer_list()

        # FIXED: Update session peer name if session already exists
        peer_key = f"{peer.address}:{peer.port}"
        if peer_key in self.peer_sessions:
            print(f"[DEBUG] Updating session peer info for {peer.name}")
            self.peer_sessions[peer_key].peer = peer

        needs_handshake = peer_key not in self.handshake_initiated and peer_key not in self.peer_sessions

        if needs_handshake:
            if self._should_initiate_to_peer(peer):
                print(f"[DEBUG] We should initiate to {peer.name}, initiating handshake")
                await self.initiate_handshake(peer)
            else:
                print(f"[DEBUG] They should initiate to us, waiting for handshake from {peer.name}")

    async def _check_and_send_queued_messages(self, peer: Peer):
        """Check if we have queued messages for this peer and send them."""
        if not self.message_queue:
            return

        peer_id = peer.peer_id or f"{peer.address}:{peer.port}"
        peer_key = f"{peer.address}:{peer.port}"

        if peer_key not in self.peer_sessions:
            print(f"[DEBUG] No session yet for {peer.name}, skipping queue check")
            return

        queued_count = self.message_queue.get_queue_count(peer_id)
        if queued_count > 0:
            print(f"[DEBUG] Found {queued_count} queued messages for {peer.name}, sending now")
            await self._send_queued_messages(peer)
        else:
            print(f"[DEBUG] No queued messages for {peer.name}")

    async def _send_queued_messages(self, peer: Peer):
        """Send all queued messages to a peer that just came online."""
        if not self.message_queue:
            return

        peer_id = peer.peer_id or f"{peer.address}:{peer.port}"
        queued = self.message_queue.get_queued_messages(peer_id, clear=True)

        if not queued:
            return

        print(f"[DEBUG] Attempting to send {len(queued)} queued messages to {peer.name}")

        peer_key = f"{peer.address}:{peer.port}"
        session = self.peer_sessions.get(peer_key)

        if not session:
            print(f"[WARNING] No session for {peer.name}, re-queueing messages")
            for msg in queued:
                self.message_queue.enqueue_message(peer_id, msg['text'], msg.get('metadata'))
            return

        sent_count = 0
        for msg in queued:
            try:
                text = msg['text']

                cipher = ChaCha20Poly1305(session.send_key)
                nonce = b"\x00" * 4 + struct.pack("<Q", session.send_nonce)
                ciphertext = cipher.encrypt(nonce, text.encode("utf-8"), None)
                session.send_nonce += 1

                frame = ProtocolFrame.pack_frame(
                    cid=session.connection_id,
                    stream_id=0,
                    frame_type=ProtocolFrame.FRAME_DATA,
                    payload=ciphertext,
                )

                await self.transport.send_frame(peer.address, peer.port, frame)
                sent_count += 1
                await asyncio.sleep(0.15)

            except Exception as e:
                print(f"[ERROR] Error enviando mensaje encolado: {e}")

        if sent_count > 0:
            self.tui.append_chat(f"✅ {sent_count} mensaje(s) encolado(s) enviado(s) a {peer.name}")

    def on_peer_disconnected(self, peer: Peer):
        """Called (in zeroconf thread) when a peer disappears."""
        print(f"[DEBUG] on_peer_disconnected called for {peer.name} ({peer.peer_id})")
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._handle_peer_disconnected(peer), self.loop)

    async def _handle_peer_disconnected(self, peer: Peer):
        peer_id = peer.peer_id or f"{peer.address}:{peer.port}"

        was_online = peer_id in self.online_peers
        self.online_peers.discard(peer_id)

        ts = datetime.now().replace(microsecond=0).isoformat()
        msg_text = f"{peer.name} se ha desconectado"

        self.tui.append_chat(f"⚠️ {msg_text}", msg_type="disconnect")

        if self.chat_history and peer.peer_id:
            msg_obj = {
                "timestamp": ts,
                "sender": "system",
                "text": msg_text,
                "type": "disconnect",
            }
            self.chat_history.add_message(peer.peer_id, msg_obj)

        peer_key = f"{peer.address}:{peer.port}"
        if peer_key in self.peer_sessions:
            del self.peer_sessions[peer_key]

        self.handshake_initiated.discard(peer_key)

        current_peer = self.tui.get_current_peer()
        if current_peer and current_peer.peer_id == peer_id:
            disconnect_msg = f"⚠️ {peer.name} está desconectado. Los mensajes se guardarán hasta que vuelva."
            self.tui.append_chat(disconnect_msg, msg_type="disconnect")

        self.update_peer_list()

    def on_peer_renamed(self, peer: Peer, old_name: str, new_name: str):
        """Called (in zeroconf thread) when a peer changes its name."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self._handle_peer_renamed(peer, old_name, new_name), 
                self.loop
            )

    async def _handle_peer_renamed(self, peer: Peer, old_name: str, new_name: str):
        """Handle peer name change in the main event loop."""
        self.tui.append_chat(
            f"📝 {old_name} ha cambiado su nombre a {new_name} (ID: {peer.peer_id})"
        )

        self.update_peer_list()

        # Update session peer reference
        peer_key = f"{peer.address}:{peer.port}"
        if peer_key in self.peer_sessions:
            self.peer_sessions[peer_key].peer = peer

    def update_peer_list(self):
        """Push discovered peers into the TUI list."""
        if self.discovery:
            peers = list(self.discovery.discovered_peers.values())
            self.tui.update_contacts(peers)

    # ---------- Handshake ----------

    async def initiate_handshake(self, peer: Peer):
        """Initiator side of Noise IK handshake."""
        try:
            if not peer.static_public_key:
                self.tui.append_chat(f"⚠️ No hay clave pública para {peer.name}")
                return

            peer_key = f"{peer.address}:{peer.port}"

            if peer_key in self.handshake_initiated or peer_key in self.peer_sessions:
                print(f"[DEBUG] Handshake already done with {peer.name}, skipping")
                return

            self.handshake_initiated.add(peer_key)

            rs_pub_bytes = peer.static_public_key
            msg, k_send, k_recv = self.noise.initiate(rs_pub_bytes)

            cid = secrets.token_bytes(8)
            session = Session(
                connection_id=cid,
                peer=peer,
                send_key=k_send,
                recv_key=k_recv,
            )
            self.transport.register_session(cid, session)

            self.peer_sessions[peer_key] = session

            frame = ProtocolFrame.pack_frame(
                cid=cid,
                stream_id=0,
                frame_type=ProtocolFrame.FRAME_HANDSHAKE,
                payload=msg,
            )
            await self.transport.send_frame(peer.address, peer.port, frame)

            print(f"[DEBUG] Handshake INITIATED to {peer.name}")
            self.tui.append_chat(f"🤝 Handshake iniciado con {peer.name}")

            await asyncio.sleep(0.5)
            await self._check_and_send_queued_messages(peer)

        except Exception as e:
            self.tui.append_chat(f"⚠️ Error iniciando handshake con {peer.name}: {e}")
            peer_key = f"{peer.address}:{peer.port}"
            self.handshake_initiated.discard(peer_key)

    async def handle_handshake(self, cid: bytes, payload: bytes, addr: Tuple[str, int]):
        """Responder side: derive keys from initiator's IK message."""
        try:
            print(f"[DEBUG] Handshake RECEIVED from {addr[0]}:{addr[1]}")

            k_send, k_recv = self.noise.respond(payload)

            peer = None
            if self.discovery:
                for p in self.discovery.discovered_peers.values():
                    if p.address == addr[0]:
                        peer = p
                        print(f"[DEBUG] Found peer in discovered_peers: {p.name}")
                        break

            # FIXED: Create temporary peer but mark it as temporary
            if not peer:
                print(f"[DEBUG] Peer not in discovered_peers yet, creating temporary peer")
                # Use a placeholder name that will be updated when discovery completes
                peer = Peer(name=f"temp_{addr[0]}", address=addr[0], port=addr[1])

            peer_key = f"{peer.address}:{peer.port}"

            if peer_key in self.peer_sessions:
                old_session = self.peer_sessions[peer_key]
                self.transport.sessions.pop(old_session.connection_id, None)

            session = Session(
                connection_id=cid,
                peer=peer,
                send_key=k_send,
                recv_key=k_recv,
            )
            self.transport.register_session(cid, session)

            self.peer_sessions[peer_key] = session

            print(f"[DEBUG] Handshake COMPLETED with {peer.address}:{peer.port}")

            # Display with current name if available
            display_name = peer.name if not peer.name.startswith("temp_") else addr[0]
            self.tui.append_chat(f"🔐 Handshake completado con {display_name}")
            self.update_peer_list()

            self.handshake_initiated.add(peer_key)

            await self._check_and_send_queued_messages(peer)

        except Exception as e:
            self.tui.append_chat(f"⚠️ Handshake error: {e}")

    def manual_handshake(self):
        """Triggered from TUI (Ctrl+H) to start handshake with selected peer."""
        peer = self.tui.get_current_peer()
        if not peer:
            self.tui.append_chat("⚠️ No hay peer seleccionado para handshake.")
            return

        if not self.loop:
            self.tui.append_chat("⚠️ No hay event loop disponible.")
            return

        asyncio.run_coroutine_threadsafe(self.initiate_handshake(peer), self.loop)

    async def send_goodbye_to_all(self):
        """Send GOODBYE frame to all connected peers before shutdown."""
        print("[DEBUG] Sending GOODBYE to all peers...")

        goodbye_tasks = []

        for peer_key, session in list(self.peer_sessions.items()):
            try:
                frame = ProtocolFrame.pack_frame(
                    cid=session.connection_id,
                    stream_id=0,
                    frame_type=ProtocolFrame.FRAME_GOODBYE,
                    payload=b'',
                )

                task = self.transport.send_frame(
                    session.peer.address,
                    session.peer.port,
                    frame,
                )
                goodbye_tasks.append(task)

            except Exception as e:
                print(f"[ERROR] Failed to queue GOODBYE for {session.peer.name}: {e}")

        if goodbye_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*goodbye_tasks, return_exceptions=True),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                print(f"[WARNING] GOODBYE timeout")

    async def handle_goodbye(self, cid: bytes, addr: Tuple[str, int]):
        """Handle GOODBYE frame from peer (explicit disconnect)."""
        session = self.transport.get_session(cid)
        if not session:
            return

        peer_id = session.peer.peer_id or f"{session.peer.address}:{session.peer.port}"

        # FIXED: Look up current name instead of using session.peer.name
        peer_name = self._get_current_peer_name(peer_id) if session.peer.peer_id else session.peer.name

        self.online_peers.discard(peer_id)

        self.tui.append_chat(f"👋 {peer_name} ha cerrado la sesión", msg_type="disconnect")

        if self.chat_history and session.peer.peer_id:
            msg_obj = {
                "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                "sender": "system",
                "text": f"{peer_name} cerró sesión",
                "type": "disconnect",
            }
            self.chat_history.add_message(session.peer.peer_id, msg_obj)

        current_peer = self.tui.get_current_peer()
        if current_peer and current_peer.peer_id == peer_id:
            self.tui.append_chat(
                f"⚠️ {peer_name} está desconectado. Los mensajes se guardarán hasta que vuelva.",
                msg_type="disconnect"
            )

        peer_key = f"{session.peer.address}:{session.peer.port}"
        if peer_key in self.peer_sessions:
            del self.peer_sessions[peer_key]
        self.handshake_initiated.discard(peer_key)

        self.update_peer_list()

    # ---------- Sending and receiving data ----------

    def on_message_send(self, text: str):
        """Called by TUI when user presses Enter."""
        text = text.strip()
        if not text:
            return

        current_peer = self.tui.get_current_peer()
        if not current_peer:
            self.tui.append_chat("⚠️ No hay ningún peer seleccionado.")
            return

        peer_id = current_peer.peer_id or f"{current_peer.address}:{current_peer.port}"
        peer_key = f"{current_peer.address}:{current_peer.port}"

        is_online = peer_id in self.online_peers
        has_session = peer_key in self.peer_sessions

        if not is_online or not has_session:
            self.tui.append_chat(f"[Tú → {current_peer.name}]: {text}", msg_type="queued")

            if self.message_queue:
                self.message_queue.enqueue_message(peer_id, text, {
                    'sender': self.username,
                    'timestamp': datetime.now().isoformat()
                })
                queue_count = self.message_queue.get_queue_count(peer_id)
                self.tui.append_chat(
                    f"📬 {current_peer.name} está desconectado. Mensaje encolado (total: {queue_count})"
                )

                if self.chat_history and current_peer.peer_id:
                    msg_obj = {
                        "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                        "sender": self.username,
                        "text": text,
                        "type": "queued",
                    }
                    self.chat_history.add_message(current_peer.peer_id, msg_obj)
            return

        # Include our peer_id in the message
        my_peer_id = self.identity.peer_id or "unknown"
        message_with_id = f"PEERID:{my_peer_id}|{text}"

        self.tui.append_chat(f"[Tú → {current_peer.name}]: {text}", msg_type="user")

        if self.chat_history and current_peer.peer_id:
            msg_obj = {
                "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                "sender": self.username,
                "sender_peer_id": my_peer_id,
                "text": text,
                "type": "user",
            }
            self.chat_history.add_message(current_peer.peer_id, msg_obj)

        session = self.peer_sessions[peer_key]

        try:
            cipher = ChaCha20Poly1305(session.send_key)
            nonce = b"\x00" * 4 + struct.pack("<Q", session.send_nonce)
            ciphertext = cipher.encrypt(nonce, message_with_id.encode("utf-8"), None)
            session.send_nonce += 1

            frame = ProtocolFrame.pack_frame(
                cid=session.connection_id,
                stream_id=0,
                frame_type=ProtocolFrame.FRAME_DATA,
                payload=ciphertext,
            )

            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.transport.send_frame(
                        current_peer.address,
                        current_peer.port,
                        frame,
                    ),
                    self.loop,
                )

        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")

    async def message_receiver_loop(self):
        """Background task to receive frames and dispatch them."""
        while self.running:
            try:
                data, addr = await self.transport.recv_frame()
                cid, stream_id, frame_type, payload = ProtocolFrame.unpack_frame(data)

                if frame_type == ProtocolFrame.FRAME_HANDSHAKE:
                    await self.handle_handshake(cid, payload, addr)
                elif frame_type == ProtocolFrame.FRAME_DATA:
                    await self.handle_data(cid, stream_id, payload)
                elif frame_type == ProtocolFrame.FRAME_GOODBYE:
                    await self.handle_goodbye(cid, addr)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] Error recibiendo: {e}")

    async def handle_data(self, cid: bytes, stream_id: int, encrypted_payload: bytes):
        """Decrypt incoming DATA frame and show/store it."""
        session = self.transport.get_session(cid)
        if not session:
            print(f"[ERROR] Received DATA for unknown session")
            return

        try:
            cipher = ChaCha20Poly1305(session.recv_key)
            nonce = b"\x00" * 4 + struct.pack("<Q", session.recv_nonce)
            plaintext = cipher.decrypt(nonce, encrypted_payload, None)
            session.recv_nonce += 1

            message = plaintext.decode("utf-8")

            # Parse peer_id from message
            if message.startswith("PEERID:"):
                # Format: PEERID:abc123...|actual message
                parts = message.split("|", 1)
                sender_peer_id = parts[0].replace("PEERID:", "")
                actual_message = parts[1] if len(parts) > 1 else ""

                print(f"[DEBUG] Received from peer_id {sender_peer_id[:8]}...: {actual_message}")

                # FIXED: Look up current name from discovered_peers
                sender_name = self._get_current_peer_name(sender_peer_id)
                print(f"[DEBUG] Sender name looked up: {sender_name}")

                # Pass message with peer_id to GUI
                self.tui.append_chat(
                    f"[PEERID:{sender_peer_id}]: {actual_message}",
                    msg_type="peer"
                )

                # FIXED: Save to history with peer_id AND looked-up name
                if self.chat_history and session.peer.peer_id:
                    msg_obj = {
                        "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                        "sender": sender_name,  # Use looked-up name, NOT session.peer.name
                        "sender_peer_id": sender_peer_id,
                        "text": actual_message,
                        "type": "peer",
                    }
                    self.chat_history.add_message(session.peer.peer_id, msg_obj)
            else:
                # Legacy format without peer_id
                print(f"[DEBUG] Received (legacy): {message}")
                # Don't use session.peer.name - might be IP!
                # Just pass it through and let GUI handle it
                self.tui.append_chat(f"[Legacy]: {message}", msg_type="peer")

        except Exception as e:
            print(f"[ERROR] Error descifrando mensaje: {e}")

    async def run(self):
        """Run the TUI and receiver loop until exit."""
        self.running = True
        recv_task = asyncio.create_task(self.message_receiver_loop())
        await self.tui.run()
        self.running = False
        recv_task.cancel()
        if self.discovery:
            await self.discovery.stop_advertising()
        self.transport.stop()
        self.identity.close()
