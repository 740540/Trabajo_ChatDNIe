# dnie_im/network/transport.py

"""
UDP transport layer:
- Single UDP socket bound on port 443
- Multiplexes all sessions with 8-byte Connection IDs (CID)
"""

import socket
import asyncio
from typing import Dict, Tuple, Optional

from session.session import Session


class UDPTransport:
    """Manages UDP socket and maps Connection IDs to Session objects."""

    def __init__(self, port: int = 443):
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.sessions: Dict[bytes, Session] = {}
        self.running: bool = False

    async def start(self):
        """Create and bind the UDP socket, set non-blocking mode."""
        loop = asyncio.get_event_loop()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("0.0.0.0", self.port))
        self.socket.setblocking(False)
        self.running = True
        print(f"✅ UDP transport listening on port {self.port}")

    # FIXED: Changed signature to accept host and port separately
    async def send_frame(self, host: str, port: int, frame: bytes):
        """Send a raw frame to the given (ip, port)."""
        if not self.socket:
            return
        loop = asyncio.get_event_loop()
        await loop.sock_sendto(self.socket, frame, (host, port))

    async def recv_frame(self) -> Tuple[bytes, Tuple[str, int]]:
        """
        Receive a raw datagram from the network.
        Returns (data, (ip, port)).
        """
        if not self.socket:
            raise RuntimeError("Socket not started")
        loop = asyncio.get_event_loop()
        data, addr = await loop.sock_recvfrom(self.socket, 65536)
        return data, addr

    def register_session(self, cid: bytes, session: Session):
        """Register a new session under a given CID."""
        self.sessions[cid] = session

    def get_session(self, cid: bytes) -> Optional[Session]:
        """Look up a Session by CID."""
        return self.sessions.get(cid)

    def stop(self):
        """Close the UDP socket."""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
