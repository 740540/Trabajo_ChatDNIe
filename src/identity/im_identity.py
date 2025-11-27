# dnie_im/identity/im_identity.py

"""
IMIdentity: wraps DNIeManager to provide:
- DNIe authentication via PIN
- Certificate retrieval
- Stable peer_id (from certificate hash)
- Helper to sign challenges
"""

import hashlib

from cryptography import x509

from identity.dnie import DNIeManager


class IMIdentity:
    """DNIe-backed identity for the instant messenger."""

    def __init__(self):
        self.dnie_manager = DNIeManager()
        self.certificate: bytes | None = None
        self.certificate_fingerprint: str | None = None
        self.peer_id: str | None = None
        self.authenticated: bool = False

    def authenticate_with_pin(self, pin: str) -> bool:
        """
        Authenticate with DNIe and derive identity.
        Assumes DNIeManager.authenticate(pin) raises on error and
        prints its own messages (as in your old dnie.py).
        """
        try:
            # Just call authenticate; don't interpret its return value
            self.dnie_manager.authenticate(pin)
            cert = self.dnie_manager.get_certificate()

            if not cert:
                raise Exception("No se pudo obtener el certificado del DNIe")

            self.certificate = cert
            h = hashlib.sha256(cert).hexdigest()
            self.certificate_fingerprint = h
            self.peer_id = h[:16]
            self.authenticated = True
            return True

        except Exception as e:
            print(f"❌ Error de autenticación DNIe: {e}")
            self.authenticated = False
            return False

    def get_certificate_info(self) -> dict:
        """Return basic human-readable info extracted from the certificate."""
        if not self.certificate:
            return {}

        try:
            cert = x509.load_der_x509_certificate(self.certificate)
            subject = cert.subject
            cn_attr = subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
            cn = cn_attr[0].value if cn_attr else "Unknown"

            return {
                "common_name": cn,
                "fingerprint": self.certificate_fingerprint,
                "peer_id": self.peer_id,
                "issuer": cert.issuer.rfc4514_string(),
                "valid_from": cert.not_valid_before_utc,
                "valid_until": cert.not_valid_after_utc,
            }
        except Exception as e:
            print(f"⚠️ Error parseando certificado: {e}")
            return {"peer_id": self.peer_id}

    def sign_challenge(self, challenge: bytes) -> bytes:
        """Sign an arbitrary challenge using the DNIe private key."""
        if not self.authenticated:
            raise Exception("No autenticado. Llame a authenticate_with_pin primero.")
        return self.dnie_manager.sign_data(challenge)

    def close(self):
        """Close underlying DNIe session."""
        self.dnie_manager.close()
        self.authenticated = False
