import os
import json
import base64
import hashlib
from cryptography.fernet import Fernet


def derive_key_from_certificate(certificate: bytes) -> bytes:
    """
    Derive a Fernet key from the DNIe certificate.
    Based on the pattern used in crypto.py.
    """
    derived = hashlib.pbkdf2_hmac(
        'sha256',
        certificate,
        b'dnie_vault_salt',
        100000,
        32
    )
    return base64.urlsafe_b64encode(derived)


class ChatHistoryManager:
    """
    Manages per-peer encrypted chat history using a key bound to the DNIe certificate.
    One encrypted file per peer_id:
      ~/.dniim_chats/vault_dnie_<user_id>/chat_<peer_id>.enc
    """

    def __init__(self, user_id: str, certificate: bytes):
        self.fernet = Fernet(derive_key_from_certificate(certificate))
        self.chat_dir = os.path.expanduser(f"~/.dniim_chats/vault_dnie_{user_id}")
        os.makedirs(self.chat_dir, exist_ok=True)

    def get_chat_file(self, peer_id: str) -> str:
        """Return path to the encrypted history file for a given peer_id."""
        safe_peer_id = peer_id.replace("/", "_")
        return os.path.join(self.chat_dir, f"chat_{safe_peer_id}.enc")

    def load_history(self, peer_id: str):
        """Load and decrypt the full message list for a peer. Returns a list of dicts."""
        path = self.get_chat_file(peer_id)
        if not os.path.exists(path):
            return []
        with open(path, "rb") as f:
            ciphertext = f.read()
        plaintext = self.fernet.decrypt(ciphertext)
        return json.loads(plaintext.decode("utf-8"))

    def save_history(self, peer_id: str, messages: list):
        """Encrypt and save the full message list for a peer."""
        path = self.get_chat_file(peer_id)
        data = json.dumps(messages, ensure_ascii=False).encode("utf-8")
        ciphertext = self.fernet.encrypt(data)
        with open(path, "wb") as f:
            f.write(ciphertext)

    def add_message(self, peer_id: str, msg_obj: dict):
        """
        Append a message object to the history of a peer and save.
        msg_obj example:
          {
            "timestamp": "2025-11-25T23:45:12",
            "sender": "alice",
            "text": "hello",
            "type": "user"  # or "system"
          }
        """
        history = self.load_history(peer_id)
        history.append(msg_obj)
        self.save_history(peer_id, history)
