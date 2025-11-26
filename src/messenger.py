"""Main application coordinator"""

import asyncio
from datetime import datetime
import struct
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from identity.im_identity import IMIdentity
from crypto.noise import NoiseIKHandshake
from crypto.protocol import ProtocolFrame
from network.transport import UDPTransport
from network.discovery import ServiceDiscovery
from session.session import Session, Peer
from session.contact_book import ContactBook
from session.chat_history import ChatHistoryManager
from ui.tui import ChatTUI



class DNIeMessenger:
    """Main application integrating all components"""
    
    def __init__(self, username: str):
        self.username = username
        self.identity = IMIdentity()
        self.noise = NoiseIKHandshake()
        self.transport = UDPTransport()
        self.discovery = None
        self.tui = ChatTUI()
        self.contact_book = ContactBook()
        self.running = False

        self.chat_history: ChatHistoryManager | None = None
        
        self.tui.message_send_callback = self.on_message_send
    
    async def initialize(self, pin: str):
        """Initialize all components with DNIe authentication"""
        print("🚀 Inicializando DNIe Instant Messenger...")

        # DNIe auth
        if not self.identity.authenticate_with_pin(pin):
            raise Exception("Autenticación DNIe fallida")

        cert_info = self.identity.get_certificate_info()
        print(f"👤 Usuario: {cert_info.get('common_name', 'Unknown')}")
        print(f"🔑 Peer ID: {cert_info.get('peer_id', 'Unknown')}")

        certificate = self.identity.certificate
        user_id = self.identity.peer_id  # short hash string

        # NEW: Initialize encrypted chat history manager
        self.chat_history = ChatHistoryManager(user_id=user_id, certificate=certificate)

        # Transport + discovery
        await self.transport.start()

        self.discovery = ServiceDiscovery(self.identity)
        self.discovery.on_peer_discovered_callback = self.on_peer_discovered
        self.discovery.on_peer_disconnected_callback = self.on_peer_disconnected  # NEW
        await self.discovery.start_advertising(self.username)

        self.tui.append_chat(f"✅ Conectado como {self.username}")
        self.tui.append_chat(f"🔑 Tu Peer ID: {self.identity.peer_id}")
        self.tui.append_chat("📡 Buscando peers en la red local...")

    
    def on_peer_discovered(self, peer: Peer):
        """Handle discovered peer"""
        self.tui.append_chat(f"🔍 Nuevo: {peer.name} ({peer.peer_id})")
        self.update_peer_list()

    def on_peer_disconnected(self, peer: Peer):
        """Called when mDNS reports that a peer has gone offline."""
        ts = datetime.now().replace(microsecond=0).isoformat()
        msg_text = f"[System] {peer.name} disconnected at {ts}"
        self.tui.append_chat(msg_text)

        if self.chat_history and peer.peer_id:
            msg_obj = {
                "timestamp": ts,
                "sender": "system",
                "text": msg_text,
                "type": "disconnect"
            }
            self.chat_history.add_message(peer.peer_id, msg_obj)

        # Update peer list in UI
        self.update_peer_list()


    
    def update_peer_list(self):
        """Update UI with peers"""
        if self.discovery:
            peers = list(self.discovery.discovered_peers.values())
            self.tui.update_contacts(peers)
    
    def on_message_send(self, text: str):
        """
        Called by TUI when the user presses Enter.
        Sends message to the currently selected peer (if any),
        shows it in UI, and stores it in encrypted history.
        """
        text = text.strip()
        if not text:
            return

        current_peer = self.tui.get_current_peer()
        if not current_peer:
            self.tui.append_chat("⚠️ No hay ningún peer seleccionado (usa Ctrl+N para seleccionar uno).")
            return

        # Show locally
        self.tui.append_chat(f"[Tú → {current_peer.name}]: {text}")

        # Store in history
        if self.chat_history and current_peer.peer_id:
            msg_obj = {
                "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                "sender": self.username,
                "text": text,
                "type": "user"
            }
            self.chat_history.add_message(current_peer.peer_id, msg_obj)

        # Send over network if session exists
        # Find or create a session for this peer
        session = None
        for s in self.transport.sessions.values():
            if s.peer.address == current_peer.address and s.peer.port == current_peer.port:
                session = s
                break

        if not session:
            self.tui.append_chat("⚠️ No hay sesión establecida aún con este peer (handshake necesario).")
            # Here you would normally trigger a handshake/initiation.
            return

        try:
            cipher = ChaCha20Poly1305(session.send_key)
            nonce = struct.pack("<Q", session.send_nonce) + b"\x00" * 4
            ciphertext = cipher.encrypt(nonce, text.encode("utf-8"), None)
            session.send_nonce += 1

            frame = ProtocolFrame.pack_frame(
                session.connection_id,
                stream_id=0,
                frame_type=ProtocolFrame.FRAME_DATA,
                payload=ciphertext
            )
            asyncio.create_task(self.transport.send_frame((current_peer.address, current_peer.port), frame))
        except Exception as e:
            self.tui.append_chat(f"❌ Error enviando mensaje: {e}")

    
    async def message_receiver_loop(self):
        """Background receiver task"""
        while self.running:
            try:
                data, addr = await self.transport.recv_frame()
                cid, stream_id, frame_type, payload = ProtocolFrame.unpack_frame(data)
                
                if frame_type == ProtocolFrame.FRAME_HANDSHAKE:
                    await self.handle_handshake(cid, payload, addr)
                elif frame_type == ProtocolFrame.FRAME_DATA:
                    await self.handle_data(cid, stream_id, payload)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
    
    async def handle_handshake(self, cid: bytes, payload: bytes, addr: Tuple[str, int]):
        """Process handshake"""
        try:
            send_key, recv_key = self.noise.respond_handshake(payload)
            peer = Peer(name="Unknown", address=addr[0], port=addr[1])
            session = Session(
                connection_id=cid,
                peer=peer,
                send_key=send_key,
                recv_key=recv_key
            )
            self.transport.register_session(cid, session)
            self.tui.append_chat(f"🔐 Handshake con {addr[0]}")
        except Exception as e:
            print(f"⚠️ Handshake error: {e}")
    
    async def handle_data(self, cid: bytes, stream_id: int, encrypted_payload: bytes):
        """Decrypt and display received message and store it in encrypted history."""
        session = self.transport.get_session(cid)
        if not session:
            return

        try:
            cipher = ChaCha20Poly1305(session.recv_key)
            nonce = struct.pack("<Q", session.recv_nonce) + b"\x00" * 4
            plaintext = cipher.decrypt(nonce, encrypted_payload, None)
            session.recv_nonce += 1

            message = plaintext.decode("utf-8")
            self.tui.append_chat(f"[{session.peer.name}]: {message}")

            if self.chat_history and session.peer.peer_id:
                msg_obj = {
                    "timestamp": datetime.now().replace(microsecond=0).isoformat(),
                    "sender": session.peer.name,
                    "text": message,
                    "type": "user"
                }
                self.chat_history.add_message(session.peer.peer_id, msg_obj)

        except Exception as e:
            print(f"⚠️ Error descifrando mensaje: {e}")


    
    async def run(self):
        """Main run loop"""
        self.running = True
        recv_task = asyncio.create_task(self.message_receiver_loop())
        
        await self.tui.run()
        
        self.running = False
        recv_task.cancel()
        await self.discovery.stop_advertising()
        self.transport.stop()
        self.identity.close()
