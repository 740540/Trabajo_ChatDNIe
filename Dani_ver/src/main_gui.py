#!/usr/bin/env python3
"""DNI-IM: Secure peer-to-peer instant messaging with GUI"""

import sys
import time
import threading
from typing import Tuple
from dnie_auth import DNIeAuthenticator
from crypto_engine import CryptoEngine
from contact_manager import ContactManager
from message_queue import MessageQueue
from network_manager import NetworkManager
from protocol import ProtocolHandler, MessageType
from gui_modern import DNIGUI
from config import CONTACTS_FILE, QUEUE_FILE, KEYPAIR_FILE
import struct


class DNIIMApplication:
    """Main application coordinator with GUI"""
    
    def __init__(self):
        self.dnie_auth = None
        self.crypto = None
        self.contacts = None
        self.queue = None
        self.network = None
        self.protocol = None
        self.gui = None
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
        
        my_fingerprint = self.dnie_auth.get_fingerprint()
        my_name = self.dnie_auth.get_subject_name()
        print(f"   Authenticated as: {my_name}")
        print(f"   Fingerprint: {my_fingerprint}")
        
        # Initialize crypto engine
        print("\n2. Loading cryptographic keys...")
        self.crypto = CryptoEngine(KEYPAIR_FILE)
        my_public_key = self.crypto.get_public_key_bytes()
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
        self.network = NetworkManager(my_fingerprint, my_public_key, my_name)
        self.network.start(self._on_packet_received)
        print("   mDNS advertising started")
        print("   UDP socket listening")
        
        # Initialize GUI
        print("\n6. Starting GUI...")
        self.gui = DNIGUI(my_name)
        self.gui.set_fingerprint(my_fingerprint)
        self.gui.start(self._on_gui_command)
        
        # Auto-refresh peers
        threading.Thread(target=self._auto_refresh_peers, daemon=True).start()
        
        return True
    
    def _auto_refresh_peers(self):
        """Auto-refresh peers list every 5 seconds"""
        while self.running:
            time.sleep(5)
            if self.gui and self.gui.running:
                peers = self.network.list_peers()
                self.gui.update_peers(peers)
    
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
                    self.gui.log(f"Handshake completed with {addr[0]}", 'success')
            
            elif msg_type == MessageType.HANDSHAKE_RESP:
                # Process handshake response
                self.protocol.process_handshake_resp(data)
                self.gui.log("Secure session established", 'success')
            
            elif msg_type == MessageType.DATA:
                # Process data message
                result = self.protocol.process_data_message(data)
                if result:
                    remote_fp, stream_id, message = result
                    contact_name = self.contacts.get_contact_name(remote_fp)
                    
                    # Add to chat window
                    self.gui.add_message(remote_fp, contact_name, message, is_me=False)
        
        except Exception as e:
            self.gui.log(f"Packet error: {e}", 'error')
    
    def _on_gui_command(self, command: str, data):
        """Handle GUI commands"""
        try:
            if command == 'list_peers':
                peers = self.network.list_peers()
                self.gui.update_peers(peers)
            
            elif command == 'list_contacts':
                contacts = self.contacts.list_contacts()
                self.gui.show_contacts_dialog(contacts)
            
            elif command == 'start_chat':
                fingerprint = data
                contact_name = self.contacts.get_contact_name(fingerprint)
                
                # Create chat window
                chat = self.gui.create_or_get_chat(fingerprint, contact_name)
                
                # Initiate handshake if needed
                if not self.protocol.has_established_session(fingerprint):
                    self.gui.log(f"Establishing secure session with {contact_name}...", 'info')
                    chat.add_system_message("Establishing secure connection...")
                    
                    try:
                        cid, packet = self.protocol.create_handshake_init(fingerprint)
                        peer_addr = self.network.get_peer_address(fingerprint)
                        if peer_addr:
                            self.network.send(packet, peer_addr[0], peer_addr[1])
                            chat.add_system_message("Handshake sent, waiting for response...")
                        else:
                            chat.add_system_message("ERROR: Peer not reachable")
                            self.gui.log(f"Peer {contact_name} not reachable", 'error')
                    except Exception as e:
                        chat.add_system_message(f"ERROR: {e}")
                        self.gui.log(f"Handshake error: {e}", 'error')
                else:
                    chat.add_system_message("Secure connection established ✓")
                
                # Deliver queued messages
                if self.queue.has_messages(fingerprint):
                    queued = self.queue.dequeue(fingerprint)
                    self.gui.log(f"Delivering {len(queued)} queued messages...", 'info')
                    for msg_data in queued:
                        self._send_message_internal(
                            fingerprint, 
                            msg_data['stream_id'], 
                            msg_data['message']
                        )
            
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
                    self.gui.log(f"Peer added: {fp[:8]} @ {ip}:{port}", 'success')
                    # Refresh peers list
                    peers = self.network.list_peers()
                    self.gui.update_peers(peers)
                else:
                    self.gui.log("Invalid peer format", 'error')
            
            elif command == 'delete_peer':
                fingerprint = data
                self.network.delete_peer(fingerprint)
                self.gui.log(f"Peer deleted: {fingerprint[:8]}", 'success')
                # Refresh peers list
                peers = self.network.list_peers()
                self.gui.update_peers(peers)
        
        except Exception as e:
            self.gui.log(f"Command error: {e}", 'error')
    
    def _send_message_internal(self, fingerprint: str, stream_id: int, message: str):
        """Send message to peer"""
        # Check if session is established
        if not self.protocol.has_established_session(fingerprint):
            # Queue message for later delivery
            self.queue.enqueue(fingerprint, message, stream_id)
            self.gui.add_system_message(fingerprint, "Message queued - peer offline")
            self.gui.log(f"Message queued for {fingerprint[:8]}", 'warning')
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
                self.gui.add_system_message(fingerprint, "Message queued - peer unreachable")
                self.gui.log(f"Peer unreachable, message queued", 'warning')
    
    def run(self):
        """Main application loop"""
        self.running = True
        try:
            self.gui.run()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown"""
        print("Cleaning up...")
        self.running = False
        if self.network:
            self.network.stop()
        if self.gui:
            self.gui.stop()
        print("Goodbye!")


def main():
    """Application entry point"""
    app = DNIIMApplication()
    
    if not app.initialize():
        print("Initialization failed")
        sys.exit(1)
    
    print("\nDNI-IM GUI ready!")
    print("Close the main window to exit.\n")
    app.run()


if __name__ == '__main__':
    main()
