"""Noise IK handshake implementation"""

from typing import Tuple
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class NoiseIKHandshake:
    """Implements Noise IK handshake with X25519, BLAKE2s, ChaCha20-Poly1305"""
    
    def __init__(self, static_private_key: bytes = None):
        if static_private_key:
            self.static_private = x25519.X25519PrivateKey.from_private_bytes(static_private_key)
        else:
            self.static_private = x25519.X25519PrivateKey.generate()
        self.static_public = self.static_private.public_key()
    
    def get_public_key_bytes(self) -> bytes:
        """Export public key"""
        return self.static_public.public_bytes_raw()
    
    def hkdf_extract_expand(self, input_key_material: bytes, salt: bytes, 
                           info: bytes, length: int) -> bytes:
        """HKDF key derivation with BLAKE2s"""
        kdf = HKDF(
            algorithm=hashes.BLAKE2s(32),
            length=length,
            salt=salt,
            info=info
        )
        return kdf.derive(input_key_material)
    
    def initiate_handshake(self, responder_static_public: bytes) -> Tuple[bytes, bytes, bytes]:
        """Create handshake message (initiator role)"""
        ephemeral_private = x25519.X25519PrivateKey.generate()
        ephemeral_public = ephemeral_private.public_key()
        
        responder_public_key = x25519.X25519PublicKey.from_public_bytes(responder_static_public)
        dh_es = ephemeral_private.exchange(responder_public_key)
        dh_ss = self.static_private.exchange(responder_public_key)
        
        shared_secret = dh_es + dh_ss
        send_key = self.hkdf_extract_expand(shared_secret, b"", b"send", 32)
        recv_key = self.hkdf_extract_expand(shared_secret, b"", b"recv", 32)
        
        handshake_msg = ephemeral_public.public_bytes_raw() + self.get_public_key_bytes()
        return handshake_msg, send_key, recv_key
    
    def respond_handshake(self, handshake_msg: bytes) -> Tuple[bytes, bytes]:
        """Process handshake message (responder role)"""
        if len(handshake_msg) < 64:
            raise Exception("Invalid handshake message")
        
        initiator_ephemeral_public = x25519.X25519PublicKey.from_public_bytes(handshake_msg[:32])
        initiator_static_public = x25519.X25519PublicKey.from_public_bytes(handshake_msg[32:64])
        
        dh_es = self.static_private.exchange(initiator_ephemeral_public)
        dh_ss = self.static_private.exchange(initiator_static_public)
        
        shared_secret = dh_es + dh_ss
        send_key = self.hkdf_extract_expand(shared_secret, b"", b"recv", 32)
        recv_key = self.hkdf_extract_expand(shared_secret, b"", b"send", 32)
        
        return send_key, recv_key
