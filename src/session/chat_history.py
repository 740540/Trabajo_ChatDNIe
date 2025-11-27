# dnie_im/session/chat_history.py

"""
Encrypted chat history manager using Fernet encryption.
Similar approach to the password manager - derives key from DNIe certificate.
Each user has their own encrypted chat history directory.
"""

import os
import json
import hashlib
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from cryptography.fernet import Fernet


class ChatHistoryManager:
    """
    Manages encrypted chat history using Fernet encryption.
    Each peer's chat is stored in a separate encrypted file.
    """

    def __init__(self, user_id: str, certificate: bytes):
        """
        Initialize chat history manager.

        Args:
            user_id: Unique identifier for this user (from DNIe)
            certificate: DNIe certificate bytes (used to derive encryption key)
        """
        self.user_id = user_id
        self.certificate = certificate

        # Derive Fernet key from certificate (same method as password manager)
        self.fernet_key = self._derive_key_from_certificate(certificate)
        self.fernet = Fernet(self.fernet_key)

        # Setup chat history directory
        self._setup_directories()

    def _derive_key_from_certificate(self, certificate: bytes) -> bytes:
        """
        Derive Fernet encryption key from DNIe certificate.
        Uses PBKDF2 with SHA256 (same as password manager).
        """
        derived = hashlib.pbkdf2_hmac(
            'sha256',
            certificate,
            b'dnie_chat_history_salt',  # Different salt than password manager
            100000,  # 100k iterations
            32  # 32 bytes
        )
        return base64.urlsafe_b64encode(derived)

    def _setup_directories(self):
        """Create chat history directory structure."""
        # Get project root directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))

        # Create .ChatHistory directory in project root
        self.base_dir = os.path.join(project_root, ".ChatHistory")
        os.makedirs(self.base_dir, exist_ok=True)

        # Create user-specific directory (based on user_id hash)
        user_hash = hashlib.sha256(self.user_id.encode()).hexdigest()[:16]
        self.user_dir = os.path.join(self.base_dir, f"user_{user_hash}")
        os.makedirs(self.user_dir, exist_ok=True)

    def _get_peer_file(self, peer_id: str) -> str:
        """Get encrypted file path for a specific peer."""
        # Sanitize peer_id for filename
        safe_peer_id = hashlib.sha256(peer_id.encode()).hexdigest()[:16]
        return os.path.join(self.user_dir, f"chat_{safe_peer_id}.enc")

    def _load_peer_history(self, peer_id: str) -> List[Dict]:
        """Load and decrypt chat history for a peer."""
        file_path = self._get_peer_file(peer_id)

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
            print(f"⚠️ Error loading chat history for {peer_id}: {e}")
            return []

    def _save_peer_history(self, peer_id: str, messages: List[Dict]):
        """Encrypt and save chat history for a peer."""
        file_path = self._get_peer_file(peer_id)

        try:
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
            print(f"❌ Error saving chat history for {peer_id}: {e}")

    def add_message(self, peer_id: str, message: Dict):
        """
        Add a message to peer's chat history.

        Args:
            peer_id: Unique identifier for the peer
            message: Dict with keys: timestamp, sender, text, type
        """
        if not peer_id:
            return

        # Load existing history
        messages = self._load_peer_history(peer_id)

        # Add timestamp if not present
        if 'timestamp' not in message:
            message['timestamp'] = datetime.now().isoformat()

        # Append new message
        messages.append(message)

        # Save updated history
        self._save_peer_history(peer_id, messages)

    def get_messages(self, peer_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Get chat history with a peer.

        Args:
            peer_id: Unique identifier for the peer
            limit: Optional limit on number of messages to return

        Returns:
            List of message dicts, newest last
        """
        messages = self._load_peer_history(peer_id)

        if limit:
            return messages[-limit:]

        return messages

    def get_recent_peers(self, limit: int = 10) -> List[str]:
        """
        Get list of peers with recent chat history.

        Args:
            limit: Maximum number of peers to return

        Returns:
            List of peer_ids, sorted by most recent activity
        """
        peer_files = []

        try:
            for filename in os.listdir(self.user_dir):
                if filename.startswith('chat_') and filename.endswith('.enc'):
                    file_path = os.path.join(self.user_dir, filename)
                    mtime = os.path.getmtime(file_path)
                    peer_files.append((filename, mtime))

            # Sort by modification time (newest first)
            peer_files.sort(key=lambda x: x[1], reverse=True)

            # Extract peer IDs from filenames
            peer_ids = []
            for filename, _ in peer_files[:limit]:
                # Decrypt file to get real peer_id
                file_path = os.path.join(self.user_dir, filename)
                try:
                    with open(file_path, 'rb') as f:
                        ciphertext = f.read()
                    plaintext = self.fernet.decrypt(ciphertext)
                    data = json.loads(plaintext.decode('utf-8'))
                    peer_ids.append(data.get('peer_id'))
                except:
                    continue

            return [p for p in peer_ids if p]

        except Exception as e:
            print(f"⚠️ Error getting recent peers: {e}")
            return []

    def delete_peer_history(self, peer_id: str) -> bool:
        """
        Delete all chat history with a peer.

        Args:
            peer_id: Unique identifier for the peer

        Returns:
            True if deleted successfully
        """
        file_path = self._get_peer_file(peer_id)

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"❌ Error deleting chat history for {peer_id}: {e}")
            return False

    def clear_all_history(self) -> bool:
        """
        Delete all chat history for this user.
        WARNING: This is irreversible!

        Returns:
            True if successful
        """
        try:
            for filename in os.listdir(self.user_dir):
                if filename.startswith('chat_') and filename.endswith('.enc'):
                    file_path = os.path.join(self.user_dir, filename)
                    os.remove(file_path)
            return True
        except Exception as e:
            print(f"❌ Error clearing all history: {e}")
            return False

    def export_peer_history(self, peer_id: str, output_file: str) -> bool:
        """
        Export chat history with a peer to plain text file.
        WARNING: Exported file is NOT encrypted!

        Args:
            peer_id: Unique identifier for the peer
            output_file: Path to output file

        Returns:
            True if exported successfully
        """
        try:
            messages = self._load_peer_history(peer_id)

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Chat History Export\n")
                f.write(f"Peer ID: {peer_id}\n")
                f.write(f"Exported: {datetime.now().isoformat()}\n")
                f.write(f"Total Messages: {len(messages)}\n")
                f.write("="*60 + "\n\n")

                for msg in messages:
                    timestamp = msg.get('timestamp', 'Unknown')
                    sender = msg.get('sender', 'Unknown')
                    text = msg.get('text', '')
                    msg_type = msg.get('type', 'user')

                    f.write(f"[{timestamp}] {sender} ({msg_type}):\n")
                    f.write(f"  {text}\n\n")

            return True

        except Exception as e:
            print(f"❌ Error exporting chat history: {e}")
            return False

    def get_statistics(self) -> Dict:
        """
        Get statistics about chat history.

        Returns:
            Dict with statistics (total_peers, total_messages, etc.)
        """
        try:
            total_peers = 0
            total_messages = 0

            for filename in os.listdir(self.user_dir):
                if filename.startswith('chat_') and filename.endswith('.enc'):
                    total_peers += 1
                    file_path = os.path.join(self.user_dir, filename)

                    try:
                        with open(file_path, 'rb') as f:
                            ciphertext = f.read()
                        plaintext = self.fernet.decrypt(ciphertext)
                        data = json.loads(plaintext.decode('utf-8'))
                        total_messages += len(data.get('messages', []))
                    except:
                        continue

            return {
                'total_peers': total_peers,
                'total_messages': total_messages,
                'storage_directory': self.user_dir
            }

        except Exception as e:
            print(f"⚠️ Error getting statistics: {e}")
            return {
                'total_peers': 0,
                'total_messages': 0,
                'storage_directory': self.user_dir
            }
