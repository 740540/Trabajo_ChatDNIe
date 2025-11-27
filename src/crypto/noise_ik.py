# dnie_im/crypto/noise_ik.py

"""
Noise IK core for DNIe IM:
- X25519 for Diffie–Hellman
- BLAKE2s-based HKDF for key derivation
- Produces two 32-byte symmetric keys for ChaCha20-Poly1305:
  * Initiator: send_key = k1, recv_key = k2
  * Responder: send_key = k2, recv_key = k1
"""

from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class NoiseIKState:
    """
    Minimal, assignment-oriented Noise IK state.
    This implements only the core of the IK pattern needed here:
    - Initiator generates ephemeral key e
    - Uses long-term static key s
    - Computes DH(e, rs) and DH(s, rs)
    - Responder uses its static key s_r and initiator's e,s to derive same secrets
    - HKDF with BLAKE2s turns (DH outputs) into two symmetric keys.
    """

    def __init__(self, static_private_bytes: bytes | None = None):
        """
        If static_private_bytes is provided, use that as the long-term key.
        Otherwise, generate a new static X25519 key pair.
        """
        if static_private_bytes:
            self.s_priv = x25519.X25519PrivateKey.from_private_bytes(static_private_bytes)
        else:
            self.s_priv = x25519.X25519PrivateKey.generate()
        self.s_pub = self.s_priv.public_key()

    @staticmethod
    def _hkdf_b2s(ikm: bytes, info: bytes, length: int = 64) -> bytes:
        """
        HKDF-Extract+Expand using BLAKE2s as the underlying hash.
        Produces `length` bytes of key material.
        """
        hkdf = HKDF(
            algorithm=hashes.BLAKE2s(32),
            length=length,
            salt=None,
            info=info,
        )
        return hkdf.derive(ikm)

    def get_static_public(self) -> bytes:
        """Return static public key bytes for sending in certificates or fingerprints."""
        return self.s_pub.public_bytes_raw()

    # ---------- Initiator side ----------

    def initiate(self, rs_pub_bytes: bytes) -> Tuple[bytes, bytes, bytes]:
        """
        Perform the initiator side of a simplified IK handshake.

        Arguments:
            rs_pub_bytes: responder's static public key bytes.

        Steps:
        - Generate ephemeral e
        - Compute DH(e, rs) and DH(s, rs)
        - Concatenate DH results and feed into HKDF-BLAKE2s
        - Split into two keys k1, k2.

        Returns:
            handshake_msg: e_pub || s_pub (64 bytes)
            send_key (k1): initiator's sending key
            recv_key (k2): initiator's receiving key
        """
        # Ephemeral key pair
        e_priv = x25519.X25519PrivateKey.generate()
        e_pub = e_priv.public_key()
        rs_pub = x25519.X25519PublicKey.from_public_bytes(rs_pub_bytes)

        # DH computations
        dh_es = e_priv.exchange(rs_pub)  # es
        dh_ss = self.s_priv.exchange(rs_pub)  # ss

        # Input key material for HKDF
        ikm = dh_es + dh_ss

        # Derive 64 bytes of key material
        keys = self._hkdf_b2s(ikm, b"Noise_IK_dni_im", 64)
        k1 = keys[:32]
        k2 = keys[32:]

        # Handshake message = ephemeral public || static public
        msg = e_pub.public_bytes_raw() + self.get_static_public()
        return msg, k1, k2

    # ---------- Responder side ----------

    def respond(self, msg: bytes) -> Tuple[bytes, bytes]:
        """
        Process the initiator's IK message on the responder side.

        Message format:
            msg = e_pub (32 bytes) || s_pub_i (32 bytes)

        Responder computes:
        - DH(s_r, e_i)
        - DH(s_r, s_i)

        Returns:
            send_key: responder's sending key (matches initiator's k2)
            recv_key: responder's receiving key (matches initiator's k1)
        """
        if len(msg) != 64:
            raise ValueError("Invalid IK message length")

        e_pub_i = x25519.X25519PublicKey.from_public_bytes(msg[:32])
        s_pub_i = x25519.X25519PublicKey.from_public_bytes(msg[32:64])

        # DH computations from responder's perspective
        dh_es = self.s_priv.exchange(e_pub_i)  # s_r, e_i
        dh_ss = self.s_priv.exchange(s_pub_i)  # s_r, s_i

        ikm = dh_es + dh_ss
        keys = self._hkdf_b2s(ikm, b"Noise_IK_dni_im", 64)
        k1 = keys[:32]
        k2 = keys[32:]

        # For responder, send with k2, recv with k1
        return k2, k1
