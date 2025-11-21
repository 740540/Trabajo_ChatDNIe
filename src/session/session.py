"""Session and peer data models"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Peer:
    """Represents a discovered peer"""
    name: str
    address: str
    port: int
    peer_id: Optional[str] = None
    certificate_fingerprint: Optional[str] = None
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class Session:
    """Represents an encrypted session with a peer"""
    connection_id: bytes
    peer: Peer
    send_key: bytes
    recv_key: bytes
    send_nonce: int = 0
    recv_nonce: int = 0
    messages: List[dict] = field(default_factory=list)
    authenticated: bool = False
