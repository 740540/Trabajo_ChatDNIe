"""Protocol handler for multiplexed UDP sessions"""

import struct
from enum import IntEnum
from typing import Dict, Optional, Tuple
from crypto_engine import NoiseIKSession, CryptoEngine
from contact_manager import ContactManager


class MessageType(IntEnum):
    """Message types for protocol"""
    HANDSHAKE_INIT = 1
    HANDSHAKE_RESP = 2
    DATA = 3
    ACK = 4


class Session:
    """Represents a secure session with a peer"""
    def __init__(self, cid: int, noise_session: NoiseIKSession, 
                 remote_fingerprint: str):
        self.cid = cid
        self.noise_session = noise_session
        self.remote_fingerprint = remote_fingerprint
        self.streams: Dict[int, list] = {}  # stream_id -> messages
        self.established = False


class ProtocolHandler:
    """Handles protocol multiplexing with CIDs and Stream IDs"""
    
    def __init__(self, crypto_engine: CryptoEngine, contact_manager: ContactManager):
        self.crypto = crypto_engine
        self.contacts = contact_manager
        self.sessions: Dict[int, Session] = {}  # cid -> Session
        self.next_cid = 1
        self.fingerprint_to_cid: Dict[str, int] = {}
    
    def create_handshake_init(self, remote_fingerprint: str) -> Tuple[int, bytes]:
        """
        Create handshake initiation message
        Returns: (cid, packet)
        """
        # Get remote public key from contacts
        remote_pubkey = self.contacts.get_public_key(remote_fingerprint)
        if not remote_pubkey:
            raise ValueError(f"No public key for {remote_fingerprint}")
        
        # Create session
        cid = self.next_cid
        self.next_cid += 1
        
        noise_session = self.crypto.create_session(remote_pubkey)
        handshake_payload = noise_session.create_initiator_message()
        
        session = Session(cid, noise_session, remote_fingerprint)
        self.sessions[cid] = session
        self.fingerprint_to_cid[remote_fingerprint] = cid
        
        # Build packet: [type:1][cid:4][payload]
        packet = struct.pack('!BI', MessageType.HANDSHAKE_INIT, cid) + handshake_payload
        return cid, packet
    
    def process_handshake_init(self, packet: bytes, sender_addr: Tuple[str, int], sender_name: Optional[str] = None) -> Optional[bytes]:
        """
        Process handshake initiation and create response
        Returns: response packet or None
        """
        try:
            msg_type, cid = struct.unpack('!BI', packet[:5])
            handshake_payload = packet[5:]
            
            # Create responder session
            noise_session = self.crypto.create_session()
            success = noise_session.process_initiator_message(handshake_payload)
            
            if not success:
                return None
            
            # Get remote fingerprint from public key
            remote_pubkey = noise_session.remote_static_public.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Verify with TOFU - use sender_name if provided
            remote_fingerprint = remote_pubkey.hex()[:16]
            friendly_name = sender_name if sender_name else None
            is_trusted, msg = self.contacts.verify_or_add(remote_fingerprint, remote_pubkey, friendly_name)
            
            if not is_trusted:
                print(f"TOFU verification failed: {msg}")
                return None
            
            # Store session
            session = Session(cid, noise_session, remote_fingerprint)
            session.established = True
            self.sessions[cid] = session
            self.fingerprint_to_cid[remote_fingerprint] = cid
            
            # Send ACK
            response = struct.pack('!BI', MessageType.HANDSHAKE_RESP, cid)
            return response
            
        except Exception as e:
            print(f"Handshake processing error: {e}")
            return None
    
    def process_handshake_resp(self, packet: bytes):
        """Process handshake response"""
        try:
            msg_type, cid = struct.unpack('!BI', packet[:5])
            if cid in self.sessions:
                self.sessions[cid].established = True
                print(f"Session {cid} established")
        except Exception as e:
            print(f"Handshake response error: {e}")
    
    def create_data_message(self, remote_fingerprint: str, stream_id: int, 
                           message: str) -> Optional[bytes]:
        """
        Create encrypted data message
        Returns: packet or None if no session
        """
        cid = self.fingerprint_to_cid.get(remote_fingerprint)
        if not cid or cid not in self.sessions:
            return None
        
        session = self.sessions[cid]
        if not session.established:
            return None
        
        # Encrypt message
        plaintext = message.encode('utf-8')
        ciphertext = session.noise_session.encrypt_message(plaintext)
        
        # Build packet: [type:1][cid:4][stream_id:2][ciphertext]
        packet = struct.pack('!BIH', MessageType.DATA, cid, stream_id) + ciphertext
        return packet
    
    def process_data_message(self, packet: bytes) -> Optional[Tuple[str, int, str]]:
        """
        Process encrypted data message
        Returns: (remote_fingerprint, stream_id, message) or None
        """
        try:
            msg_type, cid, stream_id = struct.unpack('!BIH', packet[:7])
            ciphertext = packet[7:]
            
            if cid not in self.sessions:
                return None
            
            session = self.sessions[cid]
            plaintext = session.noise_session.decrypt_message(ciphertext)
            message = plaintext.decode('utf-8')
            
            return (session.remote_fingerprint, stream_id, message)
            
        except Exception as e:
            print(f"Data message processing error: {e}")
            return None
    
    def get_or_create_session(self, remote_fingerprint: str) -> Optional[int]:
        """Get existing CID or return None if needs handshake"""
        return self.fingerprint_to_cid.get(remote_fingerprint)
    
    def has_established_session(self, remote_fingerprint: str) -> bool:
        """Check if there's an established session"""
        cid = self.fingerprint_to_cid.get(remote_fingerprint)
        if cid and cid in self.sessions:
            return self.sessions[cid].established
        return False


from cryptography.hazmat.primitives import serialization
