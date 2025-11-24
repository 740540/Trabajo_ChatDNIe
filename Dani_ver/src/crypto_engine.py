"""Cryptographic engine using Noise IK protocol"""

import os
import struct
from typing import Optional, Tuple
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.backends import default_backend
import hashlib


class NoiseIKSession:
    """Implements Noise IK handshake pattern"""
    
    def __init__(self, static_private: X25519PrivateKey, static_public: X25519PublicKey,
                 remote_static_public: Optional[X25519PublicKey] = None):
        self.static_private = static_private
        self.static_public = static_public
        self.remote_static_public = remote_static_public
        self.ephemeral_private = None
        self.ephemeral_public = None
        
        # Session keys
        self.send_key = None
        self.recv_key = None
        self.send_nonce = 0
        self.recv_nonce = 0
        
        # Handshake state
        self.h = hashlib.blake2s(b"Noise_IK_25519_ChaChaPoly_BLAKE2s").digest()
        self.ck = self.h
    
    def mix_hash(self, data: bytes):
        """Mix data into handshake hash"""
        self.h = hashlib.blake2s(self.h + data).digest()
    
    def mix_key(self, input_key_material: bytes):
        """Mix key material into chaining key"""
        hkdf = HKDF(
            algorithm=hashes.BLAKE2s(32),
            length=64,
            salt=self.ck,
            info=b"",
            backend=default_backend()
        )
        output = hkdf.derive(input_key_material)
        self.ck = output[:32]
        return output[32:]
    
    def encrypt_and_hash(self, plaintext: bytes, key: bytes) -> bytes:
        """Encrypt plaintext and mix into hash"""
        cipher = ChaCha20Poly1305(key)
        nonce = b'\x00' * 12
        ciphertext = cipher.encrypt(nonce, plaintext, self.h)
        self.mix_hash(ciphertext)
        return ciphertext
    
    def decrypt_and_hash(self, ciphertext: bytes, key: bytes) -> bytes:
        """Decrypt ciphertext and mix into hash"""
        cipher = ChaCha20Poly1305(key)
        nonce = b'\x00' * 12
        plaintext = cipher.decrypt(nonce, ciphertext, self.h)
        self.mix_hash(ciphertext)
        return plaintext
    
    def create_initiator_message(self) -> bytes:
        """Create Noise IK initiator message (-> e, es, s, ss)"""
        # Generate ephemeral keypair
        self.ephemeral_private = X25519PrivateKey.generate()
        self.ephemeral_public = self.ephemeral_private.public_key()
        
        # -> e
        e_bytes = self.ephemeral_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        self.mix_hash(e_bytes)
        
        # -> es
        es = self.ephemeral_private.exchange(self.remote_static_public)
        temp_key = self.mix_key(es)
        
        # -> s
        s_bytes = self.static_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        encrypted_s = self.encrypt_and_hash(s_bytes, temp_key)
        
        # -> ss
        ss = self.static_private.exchange(self.remote_static_public)
        temp_key2 = self.mix_key(ss)
        
        # Finalize keys
        self.send_key = self.ck[:32]
        self.recv_key = hashlib.blake2s(self.ck + b"recv").digest()[:32]
        
        return e_bytes + encrypted_s
    
    def process_initiator_message(self, message: bytes) -> bool:
        """Process Noise IK initiator message as responder"""
        try:
            # Parse message
            e_bytes = message[:32]
            encrypted_s = message[32:]
            
            remote_ephemeral = X25519PublicKey.from_public_bytes(e_bytes)
            self.mix_hash(e_bytes)
            
            # <- es
            es = self.static_private.exchange(remote_ephemeral)
            temp_key = self.mix_key(es)
            
            # <- s
            s_bytes = self.decrypt_and_hash(encrypted_s, temp_key)
            self.remote_static_public = X25519PublicKey.from_public_bytes(s_bytes)
            
            # <- ss
            ss = self.static_private.exchange(self.remote_static_public)
            temp_key2 = self.mix_key(ss)
            
            # Finalize keys (reversed for responder)
            self.recv_key = self.ck[:32]
            self.send_key = hashlib.blake2s(self.ck + b"recv").digest()[:32]
            
            return True
        except Exception as e:
            print(f"Handshake error: {e}")
            return False
    
    def encrypt_message(self, plaintext: bytes) -> bytes:
        """Encrypt application message"""
        cipher = ChaCha20Poly1305(self.send_key)
        nonce = struct.pack('<Q', self.send_nonce) + b'\x00\x00\x00\x00'
        ciphertext = cipher.encrypt(nonce, plaintext, b'')
        self.send_nonce += 1
        return ciphertext
    
    def decrypt_message(self, ciphertext: bytes) -> bytes:
        """Decrypt application message"""
        cipher = ChaCha20Poly1305(self.recv_key)
        nonce = struct.pack('<Q', self.recv_nonce) + b'\x00\x00\x00\x00'
        plaintext = cipher.decrypt(nonce, ciphertext, b'')
        self.recv_nonce += 1
        return plaintext


class CryptoEngine:
    """Manages cryptographic operations and key storage"""
    
    def __init__(self, keypair_file: str):
        self.keypair_file = keypair_file
        self.static_private = None
        self.static_public = None
        self.load_or_generate_keypair()
    
    def load_or_generate_keypair(self):
        """Load existing keypair or generate new one"""
        if os.path.exists(self.keypair_file):
            with open(self.keypair_file, 'rb') as f:
                private_bytes = f.read(32)
                self.static_private = X25519PrivateKey.from_private_bytes(private_bytes)
                self.static_public = self.static_private.public_key()
        else:
            self.static_private = X25519PrivateKey.generate()
            self.static_public = self.static_private.public_key()
            private_bytes = self.static_private.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(self.keypair_file, 'wb') as f:
                f.write(private_bytes)
    
    def get_public_key_bytes(self) -> bytes:
        """Get public key as bytes"""
        return self.static_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def create_session(self, remote_public_key: Optional[bytes] = None) -> NoiseIKSession:
        """Create new Noise IK session"""
        remote_pub = None
        if remote_public_key:
            remote_pub = X25519PublicKey.from_public_bytes(remote_public_key)
        return NoiseIKSession(self.static_private, self.static_public, remote_pub)
