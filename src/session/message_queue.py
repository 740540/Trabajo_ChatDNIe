# dnie_im/session/message_queue.py

"""
Message queue manager for offline peers.
Stores undelivered messages and sends them when peer reconnects.
Uses Fernet encryption like chat history.
"""

import os
import json
import hashlib
import base64
from datetime import datetime
from typing import Dict, List, Optional
from cryptography.fernet import Fernet


class MessageQueue:
    """
    Manages queued messages for offline peers.
    Messages are stored encrypted and sent when peer reconnects.
    """

    def __init__(self, user_id: str, certificate: bytes):
        """
        Initialize message queue manager.

        Args:
            user_id: Unique identifier for this user
            certificate: DNIe certificate bytes (for encryption key)
        """
        self.user_id = user_id
        self.certificate = certificate

        # Derive Fernet key from certificate
        self.fernet_key = self._derive_key_from_certificate(certificate)
        self.fernet = Fernet(self.fernet_key)

        # Setup queue directory
        self._setup_directories()

    def _derive_key_from_certificate(self, certificate: bytes) -> bytes:
        """Derive Fernet encryption key from DNIe certificate."""
        derived = hashlib.pbkdf2_hmac(
            'sha256',
            certificate,
            b'dnie_message_queue_salt',  # Different salt
            100000,
            32
        )
        return base64.urlsafe_b64encode(derived)

    def _setup_directories(self):
        """Create message queue directory structure."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))

        # Create .MessageQueue directory
        self.base_dir = os.path.join(project_root, ".MessageQueue")
        os.makedirs(self.base_dir, exist_ok=True)

        # Create user-specific directory
        user_hash = hashlib.sha256(self.user_id.encode()).hexdigest()[:16]
        self.user_dir = os.path.join(self.base_dir, f"user_{user_hash}")
        os.makedirs(self.user_dir, exist_ok=True)

    def _get_queue_file(self, peer_id: str) -> str:
        """Get encrypted queue file path for a specific peer."""
        safe_peer_id = hashlib.sha256(peer_id.encode()).hexdigest()[:16]
        return os.path.join(self.user_dir, f"queue_{safe_peer_id}.enc")

    def _load_queue(self, peer_id: str) -> List[Dict]:
        """Load and decrypt message queue for a peer."""
        file_path = self._get_queue_file(peer_id)

        try:
            if not os.path.exists(file_path):
                return []

            # Read encrypted file
            with open(file_path, 'rb') as f:
                ciphertext = f.read()

            # Decrypt
            plaintext = self.fernet.decrypt(ciphertext)

            # Parse JSON
            data = json.loads(plaintext.decode('utf-8'))
            return data.get('messages', [])

        except Exception as e:
            print(f"⚠️ Error loading message queue for {peer_id}: {e}")
            return []

    def _save_queue(self, peer_id: str, messages: List[Dict]):
        """Encrypt and save message queue for a peer."""
        file_path = self._get_queue_file(peer_id)

        try:
            if not messages:
                # Delete file if queue is empty
                if os.path.exists(file_path):
                    os.remove(file_path)
                return

            # Create data structure
            data = {
                'peer_id': peer_id,
                'last_updated': datetime.now().isoformat(),
                'messages': messages
            }

            # Convert to JSON
            plaintext = json.dumps(data, indent=2).encode('utf-8')

            # Encrypt
            ciphertext = self.fernet.encrypt(plaintext)

            # Write to file
            with open(file_path, 'wb') as f:
                f.write(ciphertext)

        except Exception as e:
            print(f"❌ Error saving message queue for {peer_id}: {e}")

    def enqueue_message(self, peer_id: str, message_text: str, metadata: Optional[Dict] = None):
        """
        Add a message to the queue for an offline peer.

        Args:
            peer_id: Unique identifier for the peer
            message_text: The message text to queue
            metadata: Optional metadata (sender, timestamp, etc.)
        """
        if not peer_id or not message_text:
            return

        # Load existing queue
        queue = self._load_queue(peer_id)

        # Create message entry
        message = {
            'text': message_text,
            'queued_at': datetime.now().isoformat(),
            'metadata': metadata or {}
        }

        # Append to queue
        queue.append(message)

        # Save updated queue
        self._save_queue(peer_id, queue)

        print(f"📬 Mensaje encolado para {peer_id} (total: {len(queue)})")

    def get_queued_messages(self, peer_id: str, clear: bool = True) -> List[Dict]:
        """
        Get all queued messages for a peer.

        Args:
            peer_id: Unique identifier for the peer
            clear: If True, clear the queue after retrieving

        Returns:
            List of queued message dicts
        """
        queue = self._load_queue(peer_id)

        if clear and queue:
            # Clear the queue
            self._save_queue(peer_id, [])

        return queue

    def has_queued_messages(self, peer_id: str) -> bool:
        """
        Check if there are queued messages for a peer.

        Args:
            peer_id: Unique identifier for the peer

        Returns:
            True if there are queued messages
        """
        queue = self._load_queue(peer_id)
        return len(queue) > 0

    def get_queue_count(self, peer_id: str) -> int:
        """
        Get number of queued messages for a peer.

        Args:
            peer_id: Unique identifier for the peer

        Returns:
            Number of queued messages
        """
        queue = self._load_queue(peer_id)
        return len(queue)

    def clear_queue(self, peer_id: str) -> bool:
        """
        Clear all queued messages for a peer.

        Args:
            peer_id: Unique identifier for the peer

        Returns:
            True if cleared successfully
        """
        try:
            self._save_queue(peer_id, [])
            return True
        except Exception as e:
            print(f"❌ Error clearing queue for {peer_id}: {e}")
            return False

    def get_all_queues(self) -> Dict[str, int]:
        """
        Get count of queued messages for all peers.

        Returns:
            Dict mapping peer_id to message count
        """
        queues = {}

        try:
            for filename in os.listdir(self.user_dir):
                if filename.startswith('queue_') and filename.endswith('.enc'):
                    file_path = os.path.join(self.user_dir, filename)

                    try:
                        with open(file_path, 'rb') as f:
                            ciphertext = f.read()
                        plaintext = self.fernet.decrypt(ciphertext)
                        data = json.loads(plaintext.decode('utf-8'))

                        peer_id = data.get('peer_id')
                        message_count = len(data.get('messages', []))

                        if peer_id and message_count > 0:
                            queues[peer_id] = message_count
                    except:
                        continue

            return queues

        except Exception as e:
            print(f"⚠️ Error getting all queues: {e}")
            return {}

    def get_statistics(self) -> Dict:
        """
        Get statistics about message queues.

        Returns:
            Dict with statistics
        """
        try:
            total_peers = 0
            total_messages = 0

            for filename in os.listdir(self.user_dir):
                if filename.startswith('queue_') and filename.endswith('.enc'):
                    file_path = os.path.join(self.user_dir, filename)

                    try:
                        with open(file_path, 'rb') as f:
                            ciphertext = f.read()
                        plaintext = self.fernet.decrypt(ciphertext)
                        data = json.loads(plaintext.decode('utf-8'))

                        message_count = len(data.get('messages', []))
                        if message_count > 0:
                            total_peers += 1
                            total_messages += message_count
                    except:
                        continue

            return {
                'total_peers_with_queue': total_peers,
                'total_queued_messages': total_messages,
                'storage_directory': self.user_dir
            }

        except Exception as e:
            print(f"⚠️ Error getting statistics: {e}")
            return {
                'total_peers_with_queue': 0,
                'total_queued_messages': 0,
                'storage_directory': self.user_dir
            }
