"""UDP transport with connection multiplexing"""

import socket
import asyncio
from typing import Dict, Tuple, Optional
from session.session import Session


class UDPTransport:
    """Manages UDP socket on port 443 with CID-based multiplexing"""
    
    def __init__(self, port: int = 443):
        self.port = port
        self.socket = None
        self.sessions: Dict[bytes, Session] = {}
        self.running = False
    
    async def start(self):
        """Initialize UDP listener"""
        loop = asyncio.get_event_loop()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.setblocking(False)
        self.running = True
        print(f"✅ UDP transport on port {self.port}")
    
    async def send_frame(self, address: Tuple[str, int], frame: bytes):
        """Send frame to peer"""
        if self.socket:
            loop = asyncio.get_event_loop()
            await loop.sock_sendto(self.socket, frame, address)
    
    async def recv_frame(self) -> Tuple[bytes, Tuple[str, int]]:
        """Receive frame"""
        loop = asyncio.get_event_loop()
        return await loop.sock_recvfrom(self.socket, 65536)
    
    def register_session(self, cid: bytes, session: Session):
        """Register session for multiplexing"""
        self.sessions[cid] = session
    
    def get_session(self, cid: bytes) -> Optional[Session]:
        """Lookup session by CID"""
        return self.sessions.get(cid)
    
    def stop(self):
        """Stop transport"""
        self.running = False
        if self.socket:
            self.socket.close()
