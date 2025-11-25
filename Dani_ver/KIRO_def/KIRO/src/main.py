#!/usr/bin/env python3
"""DNI-IM: Secure peer-to-peer instant messaging with DNIe authentication"""

import sys
import time
from typing import Tuple
from dnie_auth import DNIeAuthenticator
from crypto_engine import CryptoEngine
from contact_manager import ContactManager
from message_queue import MessageQueue
from network_manager import NetworkManager
from protocol import ProtocolHandler, MessageType
from tui import SimpleTUI
from config import CONTACTS_FILE, QUEUE_FILE, KEYPAIR_FILE
import struct


class DNIIMApplication:
    """Main application coordinator"""
    
    def __init__(self):
        self.dnie_auth = None
        self.crypto = None
        self.contacts = None
        self.queue = None
        self.network = None
        self.protocol = None
        self.tui = None
        self.running = False
    
    def initialize(self) -> bool:
        """Initialize all components"""
        print("Initializing DNI-IM...")
        
        # Authenticate with DNIe
        print("\n1. Authenticating with DNIe smart card...")
        self.dnie_auth = DNIeAuthenticator()
        if not self.dnie_auth.authenticate():
            print("ERROR: DNIe authentication failed")
            return False
        
        my_name = self.dnie_auth.get_subject_name()
        
        # Initialize crypto engine (with DNIe for encryption)
        print("\n2. Loading cryptographic keys...")
        self.crypto = CryptoEngine(KEYPAIR_FILE, self.dnie_auth)
        my_public_key = self.crypto.get_public_key_bytes()
        
        # Calculate fingerprint from public key (consistent across sessions)
        import hashlib
        my_fingerprint = hashlib.sha256(my_public_key).hexdigest()[:16]
        
        # Update DNIe auth with correct fingerprint if not set
        if not self.dnie_auth.fingerprint:
            self.dnie_auth.fingerprint = my_fingerprint
        
        # Get full name and DNI from DNIe
        my_name = self.dnie_auth.get_full_name()
        my_dni = self.dnie_auth.get_dni_number()
        
        print(f"   Authenticated as: {my_name}")
        print(f"   DNI: {my_dni}")
        print(f"   Fingerprint: {my_fingerprint}")
        print(f"   Public key: {my_public_key.hex()[:32]}...")
        
        # Initialize contact manager
        print("\n3. Loading contact book...")
        self.contacts = ContactManager(CONTACTS_FILE)
        print(f"   Loaded {len(self.contacts.contacts)} contacts")
        
        # Initialize message queue
        print("\n4. Loading message queue...")
        self.queue = MessageQueue(QUEUE_FILE)
        total_queued = sum(len(msgs) for msgs in self.queue.queue.values())
        print(f"   {total_queued} queued messages")
        
        # Initialize protocol handler
        self.protocol = ProtocolHandler(self.crypto, self.contacts)
        
        # Initialize network manager
        print("\n5. Starting network services...")
        self.network = NetworkManager(my_fingerprint, my_public_key)
        self.network.start(self._on_packet_received)
        print("   mDNS advertising started")
        print("   UDP socket listening on port 6666")
        
        # Initialize TUI
        print("\n6. Starting user interface...")
        self.tui = SimpleTUI(my_name)
        self.tui.start(self._on_tui_command)
        
        return True
    
    def _on_packet_received(self, data: bytes, addr: Tuple[str, int]):
        """Handle received UDP packet"""
        try:
            if len(data) < 5:
                return
            
            msg_type = struct.unpack('!B', data[:1])[0]
            
            if msg_type == MessageType.HANDSHAKE_INIT:
                # Process handshake initiation
                response = self.protocol.process_handshake_init(data, addr)
                if response:
                    self.network.send(response, addr[0], addr[1])
            
            elif msg_type == MessageType.HANDSHAKE_RESP:
                # Process handshake response
                self.protocol.process_handshake_resp(data)
            
            elif msg_type == MessageType.DATA:
                # Process data message
                result = self.protocol.process_data_message(data)
                if result:
                    remote_fp, stream_id, message = result
                    contact_name = self.contacts.get_contact_name(remote_fp)
                    
                    # Add to chat
                    chat = self.tui.create_or_get_chat(remote_fp, contact_name)
                    self.tui.add_message(remote_fp, f"[{contact_name}]: {message}")
        
        except Exception as e:
            print(f"Packet processing error: {e}")
    
    def _on_tui_command(self, command: str, data):
        """Handle TUI commands"""
        try:
            if command == 'list_peers':
                peers = self.network.list_peers()
                self.tui.show_peers(peers)
            
            elif command == 'list_contacts':
                contacts = self.contacts.list_contacts()
                self.tui.show_contacts(contacts)
            
            elif command == 'start_chat':
                # Parse peer selection
                try:
                    peer_idx = int(data) - 1
                    peers = self.network.list_peers()
                    if 0 <= peer_idx < len(peers):
                        fingerprint, addr = peers[peer_idx]
                        contact_name = self.contacts.get_contact_name(fingerprint)
                        
                        # Create chat window
                        chat = self.tui.create_or_get_chat(fingerprint, contact_name)
                        self.tui.active_chat = fingerprint
                        
                        # Initiate handshake if needed
                        if not self.protocol.has_established_session(fingerprint):
                            print(f"Establishing secure session with {contact_name}...")
                            cid, packet = self.protocol.create_handshake_init(fingerprint)
                            peer_addr = self.network.get_peer_address(fingerprint)
                            if peer_addr:
                                self.network.send(packet, peer_addr[0], peer_addr[1])
                        
                        print(f"Chat started with {contact_name}")
                        
                        # Deliver queued messages
                        if self.queue.has_messages(fingerprint):
                            queued = self.queue.dequeue(fingerprint)
                            print(f"Delivering {len(queued)} queued messages...")
                            for msg_data in queued:
                                self._send_message_internal(
                                    fingerprint, 
                                    msg_data['stream_id'], 
                                    msg_data['message']
                                )
                    else:
                        print("Invalid peer number")
                except ValueError:
                    print("Please provide a peer number from /list")
            
            elif command == 'send_message':
                fingerprint = data['fingerprint']
                stream_id = data['stream_id']
                message = data['message']
                self._send_message_internal(fingerprint, stream_id, message)
            
            elif command == 'add_peer':
                # Parse: fingerprint ip port
                parts = data.split()
                if len(parts) >= 3:
                    fp, ip, port = parts[0], parts[1], int(parts[2])
                    self.network.add_peer_manually(fp, ip, port)
                    print(f"Peer added. Use /list to see it.")
                else:
                    print("Usage: /addpeer <fingerprint> <ip> <port>")
        
        except Exception as e:
            print(f"Command error: {e}")
    
    def _send_message_internal(self, fingerprint: str, stream_id: int, message: str):
        """Send message to peer"""
        # Check if session is established
        if not self.protocol.has_established_session(fingerprint):
            # Queue message for later delivery
            self.queue.enqueue(fingerprint, message, stream_id)
            print(f"Peer offline - message queued for delivery")
            return
        
        # Create and send encrypted message
        packet = self.protocol.create_data_message(fingerprint, stream_id, message)
        if packet:
            peer_addr = self.network.get_peer_address(fingerprint)
            if peer_addr:
                self.network.send(packet, peer_addr[0], peer_addr[1])
            else:
                # Peer not reachable - queue message
                self.queue.enqueue(fingerprint, message, stream_id)
                print(f"Peer unreachable - message queued")
    
    def run(self):
        """Main application loop"""
        self.running = True
        try:
            while self.running and self.tui.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown"""
        print("Cleaning up...")
        if self.network:
            self.network.stop()
        if self.tui:
            self.tui.stop()
        print("Goodbye!")


def main():
    """Application entry point"""
    app = DNIIMApplication()
    
    if not app.initialize():
        print("Initialization failed")
        sys.exit(1)
    
    print("\nDNI-IM ready!")
    app.run()


if __name__ == '__main__':
    main()
