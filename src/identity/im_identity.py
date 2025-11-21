"""IM-specific identity management using DNIe"""

import hashlib
import base64
from typing import Optional
from cryptography import x509
from datetime import datetime

from identity.dnie import DNIeManager


class IMIdentity:
    """Manages user identity based on DNIe certificate"""
    
    def __init__(self):
        self.dnie_manager = DNIeManager()
        self.certificate = None
        self.certificate_fingerprint = None
        self.peer_id = None
        self.authenticated = False
    
    def authenticate_with_pin(self, pin: str) -> bool:
        """Authenticate with DNIe and derive identity"""
        try:
            self.dnie_manager.authenticate(pin)
            self.certificate = self.dnie_manager.get_certificate()
            
            if not self.certificate:
                raise Exception("No se pudo obtener el certificado")
            
            # Generate fingerprint
            cert_hash = hashlib.sha256(self.certificate).hexdigest()
            self.certificate_fingerprint = cert_hash
            self.peer_id = cert_hash[:16]
            
            self.authenticated = True
            print(f"✅ Identidad establecida: {self.peer_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error de autenticación: {e}")
            return False
    
    def get_certificate_info(self) -> dict:
        """Parse certificate and extract human-readable info"""
        if not self.certificate:
            return {}
        
        try:
            cert = x509.load_der_x509_certificate(self.certificate)
            subject = cert.subject
            cn = subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
            
            return {
                'common_name': cn[0].value if cn else "Unknown",
                'fingerprint': self.certificate_fingerprint,
                'peer_id': self.peer_id,
                'issuer': cert.issuer.rfc4514_string(),
                'valid_from': cert.not_valid_before_utc,
                'valid_until': cert.not_valid_after_utc
            }
        except Exception as e:
            return {'peer_id': self.peer_id}
    
    def sign_challenge(self, challenge: bytes) -> bytes:
        """Sign authentication challenge"""
        if not self.authenticated:
            raise Exception("No autenticado")
        return self.dnie_manager.sign_data(challenge)
    
    def close(self):
        """Close DNIe session"""
        self.dnie_manager.close()
        self.authenticated = False
