"""Persistent contact storage"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime


class ContactBook:
    """
    Persistent contact storage mapping friendly names to certificate fingerprints.
    Stored as JSON in user's home directory.
    """
    
    def __init__(self):
        self.contacts_file = os.path.expanduser("~/.dnie_im_contacts.json")
        self.contacts: Dict[str, dict] = {}
        self.load_contacts()
    
    def load_contacts(self):
        """Load contacts from disk"""
        try:
            if os.path.exists(self.contacts_file):
                with open(self.contacts_file, 'r', encoding='utf-8') as f:
                    self.contacts = json.load(f)
                print(f"📖 Cargados {len(self.contacts)} contactos")
        except Exception as e:
            print(f"⚠️ Error cargando contactos: {e}")
            self.contacts = {}
    
    def save_contacts(self):
        """Save contacts to disk"""
        try:
            with open(self.contacts_file, 'w', encoding='utf-8') as f:
                json.dump(self.contacts, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando contactos: {e}")
    
    def add_contact(self, name: str, peer_id: str, fingerprint: str):
        """Add or update contact"""
        self.contacts[name] = {
            'peer_id': peer_id,
            'fingerprint': fingerprint,
            'added': datetime.now().isoformat()
        }
        self.save_contacts()
        print(f"✅ Contacto añadido: {name}")
    
    def get_contact(self, name: str) -> Optional[dict]:
        """Get contact by name"""
        return self.contacts.get(name)
    
    def find_by_fingerprint(self, fingerprint: str) -> Optional[str]:
        """Find contact name by fingerprint"""
        for name, info in self.contacts.items():
            if info['fingerprint'] == fingerprint:
                return name
        return None
    
    def find_by_peer_id(self, peer_id: str) -> Optional[str]:
        """Find contact name by peer ID"""
        for name, info in self.contacts.items():
            if info['peer_id'] == peer_id:
                return name
        return None
    
    def list_contacts(self) -> List[dict]:
        """List all contacts"""
        return [{'name': name, **info} for name, info in self.contacts.items()]
    
    def remove_contact(self, name: str) -> bool:
        """Remove contact by name"""
        if name in self.contacts:
            del self.contacts[name]
            self.save_contacts()
            print(f"🗑️ Contacto eliminado: {name}")
            return True
        return False
    
    def is_trusted(self, peer_id: str) -> bool:
        """Check if peer ID is in contact book (trusted)"""
        return self.find_by_peer_id(peer_id) is not None
