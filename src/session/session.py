# dnie_im/session/session.py

"""
Session and peer data models.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Peer:
    """
    Represents a discovered peer in the local network.
    """
    name: str
    address: str
    port: int
    peer_id: Optional[str] = None
    certificate_fingerprint: Optional[str] = None
    static_public_key: Optional[bytes] = None  # FIXED: Added for Noise IK
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class Session:
    """
    Represents an active encrypted session with a peer.

    Fields:
        connection_id: 8-byte Connection ID (CID) used for multiplexing.
        peer: Peer object with address and identity.
        send_key: 32-byte symmetric key for outgoing messages.
        recv_key: 32-byte symmetric key for incoming messages.
        send_nonce: Monotonic counter for AEAD nonces (sender).
        recv_nonce: Monotonic counter for AEAD nonces (receiver).
        messages: Stored message metadata, if desired.
        authenticated: Whether DNIe-based auth (if any) has been completed.
    """
    connection_id: bytes
    peer: Peer
    send_key: bytes
    recv_key: bytes
    send_nonce: int = 0
    recv_nonce: int = 0
    messages: List[dict] = field(default_factory=list)
    authenticated: bool = False
