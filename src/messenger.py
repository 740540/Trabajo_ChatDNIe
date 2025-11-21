"""Main application coordinator"""

import asyncio
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
        
        self.tui.message_send_callback = self.on_message_send
    
    async def initialize(self, pin: str):
        """Initialize with DNIe authentication"""
        print("🚀 Inicializando...")
        
        if not self.identity.authenticate_with_pin(pin):
            raise Exception("Autenticación fallida")
        
        cert_info = self.identity.get_certificate_info()
        print(f"👤 Usuario: {cert_info.get('common_name')}")
        print(f"🔑 Peer ID: {cert_info.get('peer_id')}")
        
        await self.transport.start()
        
        self.discovery = ServiceDiscovery(self.identity)
        self.discovery.on_peer_discovered_callback = self.on_peer_discovered
        await self.discovery.start_advertising(self.username)
        
        self.tui.append_chat(f"✅ Conectado como {self.username}")
    
    def on_peer_discovered(self, peer: Peer):
        """Handle discovered peer"""
        self.tui.append_chat(f"🔍 Nuevo: {peer.name} ({peer.peer_id})")
        self.update_peer_list()
    
    def update_peer_list(self):
        """Update UI with peers"""
        peers = list(self.discovery.discovered_peers.values())
        self.tui.update_contacts(peers)
    
    def on_message_send(self, text: str):
        """Handle outgoing message"""
        self.tui.append_chat(f"[Tú]: {text}")
    
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
        """Decrypt and display message"""
        session = self.transport.get_session(cid)
        if not session:
            return
        
        try:
            cipher = ChaCha20Poly1305(session.recv_key)
            nonce = struct.pack("<Q", session.recv_nonce) + b"\x00" * 4
            plaintext = cipher.decrypt(nonce, encrypted_payload, None)
            session.recv_nonce += 1
            
            message = plaintext.decode('utf-8')
            self.tui.append_chat(f"[{session.peer.name}]: {message}")
        except Exception as e:
            print(f"⚠️ Decrypt error: {e}")
    
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
