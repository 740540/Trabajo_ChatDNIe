# dnie_im/messenger.py - FIXED: Reliable reconnection handling

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
        self.discovery = None
        self.tui = ChatTUI()
        self.contact_book = ContactBook()
        self.chat_history: ChatHistoryManager = None
        self.message_queue: MessageQueue = None
        self.running = False
        self.loop: asyncio.AbstractEventLoop = None

        # Peer-to-session mapping (always uses address:port as key)
        self.peer_sessions = {}
        # Track online peers (uses peer_id when available, else address:port)
        self.online_peers = set()
        # Track handshake state to prevent loops
        self.handshake_initiated = set()

        # Wire TUI callbacks
        self.tui.message_send_callback = self.on_message_send
        self.tui.handshake_callback = self.manual_handshake

    async def initialize(self, pin: str):
        """Initialize DNIe identity, transport, mDNS, and chat history."""
        self.tui.append_chat("🔧 Inicializando DNIe Instant Messenger...")

        if not self.identity.authenticate_with_pin(pin):
            raise Exception("Autenticación DNIe fallida")

        cert_info = self.identity.get_certificate_info()
        self.tui.append_chat(f"👤 Usuario: {cert_info.get('common_name', 'Unknown')}")
        self.tui.append_chat(f"🆔 Peer ID: {cert_info.get('peer_id', 'Unknown')}")

        certificate = self.identity.certificate
        user_id = self.identity.peer_id or "unknown"

        # Encrypted history manager
        self.chat_history = ChatHistoryManager(user_id=user_id, certificate=certificate)
        # Encrypted message queue manager
        self.message_queue = MessageQueue(user_id=user_id, certificate=certificate)

        # Pass username to GUI for proper message detection
        if hasattr(self.tui, 'set_username'):
            self.tui.set_username(self.username)

        # Start UDP transport
        await self.transport.start()

        # Start mDNS discovery & advertising
        self.discovery = ServiceDiscovery(self.identity)
        self.discovery.static_public_key = self.noise.get_static_public()
        self.discovery.on_peer_discovered_callback = self.on_peer_discovered
        self.discovery.on_peer_disconnected_callback = self.on_peer_disconnected
        self.discovery.on_peer_renamed_callback = self.on_peer_renamed
        await self.discovery.start_advertising(self.username)

        self.tui.append_chat("🔍 Buscando peers en la red local...")

    def should_initiate_to_peer(self, peer: Peer) -> bool:
        """Deterministic rule: only initiate if our peer_id is LOWER than theirs.
        This prevents crossing handshakes."""
        my_peer_id = self.identity.peer_id or ""
        their_peer_id = peer.peer_id or ""

        if not my_peer_id or not their_peer_id:
            print(f"[DEBUG] No peer IDs, using IP comparison")
            return True  # Initiate by default

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
        peer_key = f"{peer.address}:{peer.port}"

        print(f"[DEBUG] _handle_peer_discovered: {peer.name}")
        print(f"[DEBUG] - peer_key: {peer_key}")
        print(f"[DEBUG] - peer_key in handshake_initiated: {peer_key in self.handshake_initiated}")
        print(f"[DEBUG] - peer_key in peer_sessions: {peer_key in self.peer_sessions}")

        # ✅ FIX: Update existing session's peer object if it exists
        if peer_key in self.peer_sessions:
            existing_session = self.peer_sessions[peer_key]
            if not existing_session.peer.peer_id and peer.peer_id:
                print(f"[DEBUG] Updating session peer_id for {peer.name}: {peer.peer_id}")
                existing_session.peer.peer_id = peer.peer_id
                existing_session.peer.name = peer.name
                existing_session.peer.static_public_key = peer.static_public_key

                # Update online_peers with proper peer_id
                old_id = f"{peer.address}:{peer.port}"
                if old_id in self.online_peers:
                    self.online_peers.discard(old_id)
                    self.online_peers.add(peer.peer_id)
                    print(f"[DEBUG] Updated online_peers: {old_id} -> {peer.peer_id}")

        # Show discovery notification
        self.tui.append_chat(f"👀 Peer descubierto: {peer.name} ({peer.peer_id})")
        self.update_peer_list()

        needs_handshake = peer_key not in self.handshake_initiated and peer_key not in self.peer_sessions
        print(f"[DEBUG] - needs_handshake: {needs_handshake}")

        if needs_handshake:
            # Only initiate handshake if we should (deterministic rule)
            if self.should_initiate_to_peer(peer):
                print(f"[DEBUG] ✅ We should initiate to {peer.name}, initiating handshake")
                await self.initiate_handshake(peer)
            else:
                print(f"[DEBUG] ⏳ They should initiate to us, waiting for handshake from {peer.name}")
        else:
            print(f"[DEBUG] ⏭️ Skipping handshake (already done or in progress)")

    async def _check_and_send_queued_messages(self, peer: Peer):
        """Check if we have queued messages for this peer and send them."""
        if not self.message_queue:
            return

        peer_id = peer.peer_id or f"{peer.address}:{peer.port}"
        peer_key = f"{peer.address}:{peer.port}"

        # Check if we have a session
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

        # Get queued messages and clear queue
        queued = self.message_queue.get_queued_messages(peer_id, clear=True)
        if not queued:
            print(f"[DEBUG] No queued messages for {peer.name}")
            return

        print(f"[DEBUG] Attempting to send {len(queued)} queued messages to {peer.name}")

        peer_key = f"{peer.address}:{peer.port}"
        session = self.peer_sessions.get(peer_key)

        if not session:
            print(f"[WARNING] No session for {peer.name}, re-queueing messages")
            self.tui.append_chat(f"⚠️ No se pudo enviar mensajes encolados - sin sesión")
            # Re-queue messages
            for msg in queued:
                self.message_queue.enqueue_message(peer_id, msg["text"], msg.get("metadata"))
            return

        print(f"[DEBUG] Session found for {peer.name}, sending {len(queued)} messages")

        sent_count = 0
        for msg in queued:
            try:
                text = msg["text"]

                # Encrypt and send
                cipher = ChaCha20Poly1305(session.send_key)
                nonce = b"\x00" * 4 + struct.pack("Q", session.send_nonce)
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
                print(f"[DEBUG] Queued message {sent_count}/{len(queued)} sent to {peer.name}")

                # Small delay between messages
                await asyncio.sleep(0.15)

            except Exception as e:
                print(f"[ERROR] Error enviando mensaje encolado: {e}")

        if sent_count > 0:
            self.tui.append_chat(f"✅ {sent_count} mensaje(s) encolado(s) enviado(s) a {peer.name}")
            print(f"[DEBUG] Successfully sent {sent_count} queued messages")

    def on_peer_disconnected(self, peer: Peer):
        """Called (in zeroconf thread) when a peer disappears."""
        print(f"[DEBUG] on_peer_disconnected called for {peer.name} ({peer.peer_id})")
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._handle_peer_disconnected(peer), self.loop)

    async def _handle_peer_disconnected(self, peer: Peer):
        peer_id = peer.peer_id or f"{peer.address}:{peer.port}"
        peer_key = f"{peer.address}:{peer.port}"

        # Mark peer as offline IMMEDIATELY
        was_online = peer_id in self.online_peers
        self.online_peers.discard(peer_id)

        # Also remove address:port version if it exists
        addr_port_id = f"{peer.address}:{peer.port}"
        self.online_peers.discard(addr_port_id)

        print(f"[DEBUG] Peer {peer.name} marked as OFFLINE. Total online: {len(self.online_peers)}")

        if not was_online:
            print(f"[WARNING] Peer {peer.name} wasn't marked as online!")

        ts = datetime.now().replace(microsecond=0).isoformat()
        msg_text = f"{peer.name} se ha desconectado"

        # Show in both system logs AND current chat
        self.tui.append_chat(f"⚠️ {msg_text}", msg_type="disconnect")

        if self.chat_history and peer.peer_id:
            msg_obj = {
                "timestamp": ts,
                "sender": "system",
                "text": msg_text,
                "type": "disconnect",
            }
            self.chat_history.add_message(peer.peer_id, msg_obj)

        # Remove from peer_sessions mapping and handshake tracking
        if peer_key in self.peer_sessions:
            del self.peer_sessions[peer_key]
            print(f"[DEBUG] Removed session for {peer.name}")

        # ✅ FIX: Clear handshake tracking to allow reconnection
        self.handshake_initiated.discard(peer_key)
        print(f"[DEBUG] Cleared handshake_initiated for {peer_key}")

        # Check if we're currently chatting with this peer
        current_peer = self.tui.get_current_peer()
        if current_peer and current_peer.peer_id == peer_id:
            # Show additional disconnect notification in current chat
            disconnect_msg = f"⚠️ {peer.name} está desconectado. Los mensajes se guardarán hasta que vuelva."
            self.tui.append_chat(disconnect_msg, msg_type="disconnect")

        self.update_peer_list()

    def on_peer_renamed(self, peer: Peer, old_name: str, new_name: str):
        """Called (in zeroconf thread) when a peer changes its name."""
        if self.loop:
            asyncio.run_coroutine_threadsafe(
                self._handle_peer_renamed(peer, old_name, new_name), self.loop
            )

    async def _handle_peer_renamed(self, peer: Peer, old_name: str, new_name: str):
        """Handle peer name change in the main event loop."""
        self.tui.append_chat(
            f"📝 {old_name} ha cambiado su nombre a {new_name} (ID: {peer.peer_id})"
        )
        self.update_peer_list()

        # Update session peer name if session exists
        peer_key = f"{peer.address}:{peer.port}"
        if peer_key in self.peer_sessions:
            self.peer_sessions[peer_key].peer.name = new_name

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

            # Check if already initiated or session exists
            if peer_key in self.handshake_initiated or peer_key in self.peer_sessions:
                print(f"[DEBUG] Handshake already done with {peer.name}, skipping")
                return

            # Mark as initiated
            self.handshake_initiated.add(peer_key)
            print(f"[DEBUG] Added {peer_key} to handshake_initiated")

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

            # Add to peer_sessions mapping
            self.peer_sessions[peer_key] = session

            # ✅ Mark as online ONLY after session is established
            peer_id = peer.peer_id or f"{peer.address}:{peer.port}"
            was_offline = peer_id not in self.online_peers
            self.online_peers.add(peer_id)
            print(f"[DEBUG] Peer {peer.name} marked as ONLINE after handshake. Total online: {len(self.online_peers)}")

            frame = ProtocolFrame.pack_frame(
                cid=cid,
                stream_id=0,
                frame_type=ProtocolFrame.FRAME_HANDSHAKE,
                payload=msg,
            )

            await self.transport.send_frame(peer.address, peer.port, frame)
            print(f"[DEBUG] Handshake INITIATED to {peer.name}")
            print(f"[DEBUG] CID: {cid.hex()}")
            print(f"[DEBUG] Peer: {peer.address}:{peer.port}")

            if was_offline:
                self.tui.append_chat(f"✓ Peer conectado: {peer.name}")

            self.tui.append_chat(f"🤝 Handshake iniciado con {peer.name}")

            # Check for queued messages after handshake completes
            await asyncio.sleep(0.5)
            await self._check_and_send_queued_messages(peer)

        except Exception as e:
            self.tui.append_chat(f"⚠️ Error iniciando handshake con {peer.name}: {e}")
            print(f"[ERROR] Handshake initiation failed: {e}")
            import traceback
            traceback.print_exc()
            # Remove from initiated on error
            peer_key = f"{peer.address}:{peer.port}"
            self.handshake_initiated.discard(peer_key)

    async def handle_handshake(self, cid: bytes, payload: bytes, addr: Tuple[str, int]):
        """Responder side: derive keys from initiator's IK message."""
        try:
            print(f"[DEBUG] Handshake RECEIVED from {addr[0]}:{addr[1]}")
            print(f"[DEBUG] CID from initiator: {cid.hex()}")

            k_send, k_recv = self.noise.respond(payload)
            print(f"[DEBUG] Noise handshake successful, keys derived")

            # Try to find the peer in discovered_peers
            peer = None
            if self.discovery:
                for p in self.discovery.discovered_peers.values():
                    if p.address == addr[0]:
                        peer = p
                        print(f"[DEBUG] Found peer in discovered_peers: {p.name}")
                        break

            # If not found, create temporary peer (will be updated when discovered)
            if not peer:
                print(f"[DEBUG] Peer not in discovered_peers, creating temporary peer")
                peer = Peer(name=f"{addr[0]}", address=addr[0], port=addr[1])

            peer_key = f"{peer.address}:{peer.port}"

            # Always create session for responder side, even if we already have one
            # (This handles crossing handshakes - we replace our initiated session with theirs)
            if peer_key in self.peer_sessions:
                print(f"[DEBUG] Replacing existing session with {peer.address}:{peer.port}")
                # Unregister old session
                old_session = self.peer_sessions[peer_key]
                self.transport.sessions.pop(old_session.connection_id, None)

            # Use the CID from the initiator
            session = Session(
                connection_id=cid,
                peer=peer,
                send_key=k_send,
                recv_key=k_recv,
            )
            self.transport.register_session(cid, session)

            # Add to peer_sessions mapping
            self.peer_sessions[peer_key] = session

            # ✅ Mark as online ONLY after session is established
            peer_id = peer.peer_id or f"{peer.address}:{peer.port}"
            was_offline = peer_id not in self.online_peers
            self.online_peers.add(peer_id)
            print(f"[DEBUG] Peer {peer.name} marked as ONLINE after handshake. Total online: {len(self.online_peers)}")

            print(f"[DEBUG] Handshake COMPLETED with {peer.address}:{peer.port}")
            print(f"[DEBUG] CID registered: {cid.hex()}")
            print(f"[DEBUG] Peer key: {peer_key}")

            if was_offline:
                self.tui.append_chat(f"✓ Peer conectado: {peer.name}")

            self.tui.append_chat(f"🔐 Handshake completado con {peer.name}")
            self.update_peer_list()

            # Mark as initiated to prevent loops
            self.handshake_initiated.add(peer_key)
            print(f"[DEBUG] Added {peer_key} to handshake_initiated (responder)")

            # Check for queued messages AFTER session is created
            await self._check_and_send_queued_messages(peer)

        except Exception as e:
            self.tui.append_chat(f"⚠️ Handshake error: {e}")
            print(f"[ERROR] Handshake handling failed: {e}")
            import traceback
            traceback.print_exc()

    def manual_handshake(self):
        """Triggered from TUI (Ctrl+H) to start handshake with selected peer."""
        peer = self.tui.get_current_peer()
        if not peer:
            self.tui.append_chat(
                "⚠️ No hay peer seleccionado para handshake."
            )
            return

        if not self.loop:
            self.tui.append_chat("⚠️ No hay event loop disponible.")
            return

        asyncio.run_coroutine_threadsafe(self.initiate_handshake(peer), self.loop)

    # ---------- Send GOODBYE to all peers ----------
    async def send_goodbye_to_all(self):
        """Send GOODBYE frame to all connected peers before shutdown."""
        print("[DEBUG] Sending GOODBYE to all peers...")
        goodbye_count = 0
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
                goodbye_count += 1
                print(f"[DEBUG] GOODBYE queued for {session.peer.name}")

            except Exception as e:
                print(f"[ERROR] Failed to queue GOODBYE for {session.peer.name}: {e}")

        # Send all GOODBYEs in parallel with timeout
        if goodbye_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*goodbye_tasks, return_exceptions=True),
                    timeout=1.0
                )
                print(f"[DEBUG] Sent GOODBYE to {goodbye_count} peer(s)")
            except asyncio.TimeoutError:
                print(f"[WARNING] GOODBYE timeout - some may not have been sent")

    # ---------- Handle incoming GOODBYE ----------
    async def handle_goodbye(self, cid: bytes, addr: Tuple[str, int]):
        """Handle GOODBYE frame from peer (explicit disconnect)."""
        session = self.transport.get_session(cid)
        if not session:
            print(f"[DEBUG] GOODBYE from unknown session")
            return

        peer_id = session.peer.peer_id or f"{session.peer.address}:{session.peer.port}"
        peer_name = session.peer.name
        print(f"[DEBUG] GOODBYE received from {peer_name}")

        # Mark as offline (both peer_id and address:port versions)
        self.online_peers.discard(peer_id)
        self.online_peers.discard(f"{session.peer.address}:{session.peer.port}")

        # Show notification in chat too
        self.tui.append_chat(f"👋 {peer_name} ha cerrado la sesión", msg_type="disconnect")

        # Save to history
        if self.chat_history and session.peer.peer_id:
            msg_obj = {
                "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                "sender": "system",
                "text": f"{peer_name} cerró sesión",
                "type": "disconnect",
            }
            self.chat_history.add_message(session.peer.peer_id, msg_obj)

        # Check if we're chatting with this peer
        current_peer = self.tui.get_current_peer()
        if current_peer and current_peer.peer_id == peer_id:
            self.tui.append_chat(
                f"⚠️ {peer_name} está desconectado. Los mensajes se guardarán hasta que vuelva.",
                msg_type="disconnect"
            )

        # Remove session and handshake tracking
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
            self.tui.append_chat(
                "⚠️ No hay ningún peer seleccionado."
            )
            return

        peer_id = current_peer.peer_id or f"{current_peer.address}:{current_peer.port}"
        peer_key = f"{current_peer.address}:{current_peer.port}"

        # Check if peer is online BEFORE trying to send
        is_online = peer_id in self.online_peers
        has_session = peer_key in self.peer_sessions

        print(f"[DEBUG] Sending message to {current_peer.name}")
        print(f"[DEBUG] - Peer ID: {peer_id}")
        print(f"[DEBUG] - Is online: {is_online}")
        print(f"[DEBUG] - Has session: {has_session}")

        # Different UI for online vs offline messages
        if not is_online or not has_session:
            # Peer is offline - queue the message
            # Show with different color
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
                print(f"[DEBUG] Message queued for {current_peer.name} using ID: {peer_id}")

            # Save queued message to history with "queued" type
            if self.chat_history and current_peer.peer_id:
                msg_obj = {
                    "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                    "sender": self.username,
                    "text": text,
                    "type": "queued",
                }
                self.chat_history.add_message(current_peer.peer_id, msg_obj)
            else:
                self.tui.append_chat(
                    "⚠️ No hay sesión establecida con este peer."
                )
            return

        # Peer is online - send immediately
        # Show with normal color
        self.tui.append_chat(f"[Tú → {current_peer.name}]: {text}", msg_type="user")

        # Save to history
        if self.chat_history and current_peer.peer_id:
            msg_obj = {
                "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                "sender": self.username,
                "text": text,
                "type": "user",
            }
            self.chat_history.add_message(current_peer.peer_id, msg_obj)

        session = self.peer_sessions[peer_key]
        try:
            cipher = ChaCha20Poly1305(session.send_key)
            nonce = b"\x00" * 4 + struct.pack("Q", session.send_nonce)
            ciphertext = cipher.encrypt(nonce, text.encode("utf-8"), None)
            session.send_nonce += 1

            frame = ProtocolFrame.pack_frame(
                cid=session.connection_id,
                stream_id=0,
                frame_type=ProtocolFrame.FRAME_DATA,
                payload=ciphertext,
            )

            print(f"[DEBUG] Sending DATA frame with CID: {session.connection_id.hex()}")
            if self.loop:
                asyncio.run_coroutine_threadsafe(
                    self.transport.send_frame(
                        current_peer.address,
                        current_peer.port,
                        frame,
                    ),
                    self.loop,
                )
            print(f"[DEBUG] Message sent to {current_peer.name}")

        except Exception as e:
            self.tui.append_chat(f"⚠️ Error enviando mensaje: {e}")
            print(f"[ERROR] Failed to send message: {e}")

    async def message_receiver_loop(self):
        """Main loop to receive and process frames."""
        while self.running:
            try:
                frame_data, (addr, port) = await self.transport.recv_frame()
                if not frame_data:
                    continue

                cid, stream_id, frame_type, payload = ProtocolFrame.unpack_frame(frame_data)

                if frame_type == ProtocolFrame.FRAME_HANDSHAKE:
                    await self.handle_handshake(cid, payload, (addr, port))

                elif frame_type == ProtocolFrame.FRAME_DATA:
                    await self.handle_data_frame(cid, payload, (addr, port))

                elif frame_type == ProtocolFrame.FRAME_GOODBYE:
                    await self.handle_goodbye(cid, (addr, port))

                else:
                    print(f"[WARNING] Unknown frame type: {frame_type}")

            except asyncio.CancelledError:
                print("[DEBUG] Receiver loop cancelled")
                break
            except Exception as e:
                print(f"[ERROR] Receiver loop error: {e}")
                import traceback
                traceback.print_exc()

    async def handle_data_frame(self, cid: bytes, payload: bytes, addr: Tuple[str, int]):
        """Decrypt and display a received DATA frame."""
        session = self.transport.get_session(cid)
        if not session:
            print(f"[WARNING] DATA frame from unknown CID: {cid.hex()}")
            return

        try:
            cipher = ChaCha20Poly1305(session.recv_key)
            nonce = b"\x00" * 4 + struct.pack("Q", session.recv_nonce)
            plaintext = cipher.decrypt(nonce, payload, None)
            session.recv_nonce += 1

            text = plaintext.decode("utf-8")
            peer_name = session.peer.name

            print(f"[DEBUG] Received message from {peer_name}: {text}")

            # Save to chat history
            if self.chat_history and session.peer.peer_id:
                msg_obj = {
                    "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                    "sender": peer_name,
                    "text": text,
                    "type": "peer",
                }
                self.chat_history.add_message(session.peer.peer_id, msg_obj)

            # Display in TUI
            self.tui.append_chat(f"[{peer_name} → Tú]: {text}", msg_type="peer")

        except Exception as e:
            print(f"[ERROR] Failed to decrypt DATA frame: {e}")
