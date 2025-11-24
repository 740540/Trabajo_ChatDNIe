"""Contact book and TOFU verification"""

import json
import os
from typing import Dict, Optional, Tuple


class ContactManager:
    """Manages contacts with TOFU verification"""
    
    def __init__(self, contacts_file: str):
        self.contacts_file = contacts_file
        self.contacts: Dict[str, dict] = {}
        self.load_contacts()
    
    def load_contacts(self):
        """Load contacts from file"""
        if os.path.exists(self.contacts_file):
            with open(self.contacts_file, 'r') as f:
                self.contacts = json.load(f)
    
    def save_contacts(self):
        """Save contacts to file"""
        with open(self.contacts_file, 'w') as f:
            json.dump(self.contacts, f, indent=2)
    
    def verify_or_add(self, fingerprint: str, public_key: bytes, 
                      friendly_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Verify contact using TOFU or add new contact
        Returns: (is_trusted, status_message)
        """
        pub_key_hex = public_key.hex()
        
        if fingerprint in self.contacts:
            # Known contact - verify public key matches
            stored_key = self.contacts[fingerprint]['public_key']
            if stored_key == pub_key_hex:
                return True, f"Verified: {self.contacts[fingerprint]['name']}"
            else:
                return False, "WARNING: Public key mismatch! Possible MITM attack!"
        else:
            # New contact - TOFU
            name = friendly_name or f"User_{fingerprint[:8]}"
            self.contacts[fingerprint] = {
                'name': name,
                'public_key': pub_key_hex,
                'first_seen': str(os.times())
            }
            self.save_contacts()
            return True, f"New contact added: {name}"
    
    def get_contact_name(self, fingerprint: str) -> str:
        """Get friendly name for contact"""
        if fingerprint in self.contacts:
            return self.contacts[fingerprint]['name']
        return f"Unknown_{fingerprint[:8]}"
    
    def get_public_key(self, fingerprint: str) -> Optional[bytes]:
        """Get stored public key for contact"""
        if fingerprint in self.contacts:
            return bytes.fromhex(self.contacts[fingerprint]['public_key'])
        return None
    
    def update_name(self, fingerprint: str, new_name: str):
        """Update contact friendly name"""
        if fingerprint in self.contacts:
            self.contacts[fingerprint]['name'] = new_name
            self.save_contacts()
    
    def list_contacts(self) -> list:
        """List all contacts"""
        return [(fp, data['name']) for fp, data in self.contacts.items()]
