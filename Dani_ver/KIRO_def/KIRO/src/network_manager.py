"""Network manager for UDP communication and mDNS discovery"""

import socket
import struct
import threading
from typing import Dict, Callable, Optional, Tuple
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
from config import UDP_PORT, SERVICE_TYPE, BUFFER_SIZE, RELAY_SERVER, RELAY_PORT, USE_RELAY
import time


class PeerInfo:
    """Information about a discovered peer"""
    def __init__(self, name: str, address: str, port: int):
        self.name = name
        self.address = address
        self.port = port
        self.last_seen = time.time()


class MDNSListener(ServiceListener):
    """Listener for mDNS service discovery"""
    
    def __init__(self, callback: Callable):
        self.callback = callback
    
    def add_service(self, zc: Zeroconf, type_: str, name: str):
        info = zc.get_service_info(type_, name)
        if info:
            self.callback('add', info)
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str):
        self.callback('remove', name)
    
    def update_service(self, zc: Zeroconf, type_: str, name: str):
        info = zc.get_service_info(type_, name)
        if info:
            self.callback('update', info)


class NetworkManager:
    """Manages UDP socket and mDNS discovery"""
    
    def __init__(self, my_fingerprint: str, my_public_key: bytes, my_name: str = "Unknown"):
        self.my_fingerprint = my_fingerprint
        self.my_public_key = my_public_key
        self.my_name = my_name
        self.socket = None
        self.zeroconf = None
        self.service_info = None
        self.use_relay = USE_RELAY
        self.relay_registered = False
        self.relay_peers = {}  # Peers discovered via relay
        self.peers: Dict[str, PeerInfo] = {}
        self.running = False
        self.receive_callback = None
        self.use_relay = USE_RELAY
        self.relay_registered = False
        
    def start(self, receive_callback: Callable):
        """Start UDP socket and mDNS advertising"""
        self.receive_callback = receive_callback
        
        # Create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', UDP_PORT))
        
        # Get all local IP addresses
        hostname = socket.gethostname()
        try:
            # Try to get actual network IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            # Fallback to hostname resolution
            local_ip = socket.gethostbyname(hostname)
        
        print(f"Local IP: {local_ip}")
        print(f"Fingerprint: {self.my_fingerprint}")
        
        # Start mDNS advertising
        self.zeroconf = Zeroconf()
        
        # Create unique service name
        service_name = f"dni-im-{self.my_fingerprint[:8]}.{SERVICE_TYPE}"
        
        self.service_info = ServiceInfo(
            SERVICE_TYPE,
            service_name,
            addresses=[socket.inet_aton(local_ip)],
            port=UDP_PORT,
            properties={
                b'fingerprint': self.my_fingerprint.encode('utf-8'),
                b'pubkey': self.my_public_key.hex().encode('utf-8'),
                b'name': self.my_name.encode('utf-8')
            },
            server=f"{hostname}.local."
        )
        
        print(f"Registering mDNS service: {service_name}")
        self.zeroconf.register_service(self.service_info)
        
        # Start service browser
        print(f"Browsing for {SERVICE_TYPE} services...")
        self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, 
                                      MDNSListener(self._on_service_change))
        
        # Start receive thread
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receive_thread.start()
        
        # Register with relay server if enabled
        if self.use_relay:
            self._register_with_relay()
            # Start relay heartbeat thread
            self.relay_thread = threading.Thread(target=self._relay_heartbeat, daemon=True)
            self.relay_thread.start()
        
        print(f"Network started on UDP port {UDP_PORT}")
        print("Waiting for peer discovery...")
    
    def stop(self):
        """Stop network services"""
        self.running = False
        if self.zeroconf:
            self.zeroconf.unregister_service(self.service_info)
            self.zeroconf.close()
        if self.socket:
            self.socket.close()
    
    def _on_service_change(self, action: str, data):
        """Handle mDNS service changes"""
        try:
            if action == 'add' or action == 'update':
                if isinstance(data, ServiceInfo):
                    print(f"[mDNS] Service {action}: {data.name}")
                    
                    if not data.addresses:
                        print(f"[mDNS] No addresses for service")
                        return
                    
                    name = data.server
                    address = socket.inet_ntoa(data.addresses[0])
                    port = data.port
                    
                    print(f"[mDNS] Address: {address}:{port}")
                    
                    # Extract fingerprint and name from properties
                    props = data.properties
                    if b'fingerprint' in props:
                        fingerprint = props[b'fingerprint'].decode()
                        peer_name = props.get(b'name', b'Unknown').decode('utf-8')
                        print(f"[mDNS] Fingerprint: {fingerprint[:8]}, Name: {peer_name}")
                        
                        if fingerprint != self.my_fingerprint:
                            self.peers[fingerprint] = PeerInfo(peer_name, address, port)
                            print(f"✓ Discovered peer: {peer_name} ({fingerprint[:8]}) at {address}:{port}")
                        else:
                            print(f"[mDNS] Ignoring self")
                    else:
                        print(f"[mDNS] No fingerprint in properties")
            
            elif action == 'remove':
                print(f"[mDNS] Service removed: {data}")
                # Remove peer by service name
                for fp, peer in list(self.peers.items()):
                    if peer.name == data:
                        del self.peers[fp]
                        print(f"✗ Peer left: {fp[:8]}")
        except Exception as e:
            print(f"[mDNS] Error processing service change: {e}")
    
    def _receive_loop(self):
        """Receive loop for UDP packets"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(BUFFER_SIZE)
                
                # Check if it's a relay message
                if addr[0] == RELAY_SERVER and len(data) > 1:
                    self._handle_relay_message(data)
                elif self.receive_callback:
                    self.receive_callback(data, addr)
            except Exception as e:
                if self.running:
                    print(f"Receive error: {e}")
    
    def _handle_relay_message(self, data: bytes):
        """Handle messages from relay server"""
        try:
            if len(data) < 1:
                return
            
            cmd = data[0]
            
            if cmd == 0x81:  # REGISTER_ACK
                if len(data) >= 17:
                    fp = data[1:17].decode('utf-8', errors='ignore')
                    print(f"[Relay] Registration confirmed: {fp[:8]}")
            
            elif cmd == 0x82:  # PEER_LIST
                # Format: [0x82][count:1][fp:16][name_len:1][name][pubkey_len:1][pubkey]...
                if len(data) < 2:
                    return
                
                count = data[1]
                offset = 2
                
                print(f"[Relay] Received peer list: {count} peers")
                
                for i in range(count):
                    if offset + 16 > len(data):
                        break
                    
                    # Read fingerprint
                    fp = data[offset:offset+16].decode('utf-8', errors='ignore').rstrip('\x00')
                    offset += 16
                    
                    if offset >= len(data):
                        break
                    
                    # Read name
                    name_len = data[offset]
                    offset += 1
                    
                    if offset + name_len > len(data):
                        break
                    
                    name = data[offset:offset+name_len].decode('utf-8', errors='ignore')
                    offset += name_len
                    
                    # Read public key
                    pubkey = None
                    if offset < len(data):
                        pubkey_len = data[offset]
                        offset += 1
                        
                        if pubkey_len > 0 and offset + pubkey_len <= len(data):
                            pubkey = data[offset:offset+pubkey_len]
                            offset += pubkey_len
                    
                    if fp and fp != self.my_fingerprint:
                        # Add peer discovered via relay
                        self.peers[fp] = PeerInfo(name, RELAY_SERVER, RELAY_PORT)
                        print(f"✓ Discovered peer via relay: {name} ({fp[:8]})")
                        
                        # Store public key in contacts if available
                        if pubkey and len(pubkey) == 32:
                            # Import contact_manager to store the public key
                            if hasattr(self, 'contact_manager'):
                                self.contact_manager.add_or_update_contact(fp, name, pubkey)
                                print(f"  Stored public key for {name}")
                            else:
                                print(f"  Received public key: {len(pubkey)} bytes")
                    else:
                        print(f"[Relay] Skipping self: '{fp}'")
        
        except Exception as e:
            print(f"[Relay] Error handling message: {e}")
    
    def send(self, data: bytes, address: str, port: int):
        """Send UDP packet"""
        try:
            self.socket.sendto(data, (address, port))
        except Exception as e:
            print(f"Send error: {e}")
    
    def _register_with_relay(self):
        """Register with relay server (with public key)"""
        try:
            # Send REGISTER command: [0x01][fingerprint:16][name_len:1][name][pubkey_len:1][pubkey:32]
            fp_bytes = self.my_fingerprint[:16].encode('utf-8')
            name_bytes = self.my_name.encode('utf-8')[:255]
            
            packet = bytearray()
            packet.append(0x01)  # REGISTER command
            packet.extend(fp_bytes)  # Fingerprint
            packet.append(len(name_bytes))  # Name length
            packet.extend(name_bytes)  # Name
            packet.append(len(self.my_public_key))  # Pubkey length
            packet.extend(self.my_public_key)  # Public key (32 bytes)
            
            self.socket.sendto(bytes(packet), (RELAY_SERVER, RELAY_PORT))
            self.relay_registered = True
            print(f"✓ Registered with relay server at {RELAY_SERVER}:{RELAY_PORT}")
            print(f"  Sent public key: {len(self.my_public_key)} bytes")
            
            # Request peer list immediately after registration
            time.sleep(0.5)
            self._request_peer_list()
        except Exception as e:
            print(f"✗ Failed to register with relay: {e}")
    
    def _relay_heartbeat(self):
        """Send periodic heartbeat and request peer list from relay server"""
        while self.running:
            time.sleep(10)  # Every 10 seconds
            if self.relay_registered:
                try:
                    # Send heartbeat (REGISTER)
                    packet = struct.pack('!B', 0x01) + self.my_fingerprint[:16].encode('utf-8')
                    self.socket.sendto(packet, (RELAY_SERVER, RELAY_PORT))
                    
                    # Request peer list
                    time.sleep(1)
                    self._request_peer_list()
                except Exception as e:
                    print(f"Relay heartbeat error: {e}")
    
    def _request_peer_list(self):
        """Request list of peers from relay server"""
        try:
            # Send PEER_LIST_REQUEST: [0x03][my_fingerprint:16]
            packet = struct.pack('!B', 0x03) + self.my_fingerprint[:16].encode('utf-8')
            self.socket.sendto(packet, (RELAY_SERVER, RELAY_PORT))
        except Exception as e:
            print(f"Error requesting peer list: {e}")
    
    def send_via_relay(self, data: bytes, dest_fingerprint: str):
        """Send packet via relay server"""
        try:
            # Send RELAY command: [0x02][dest_fingerprint:16][data]
            packet = struct.pack('!B', 0x02) + dest_fingerprint[:16].encode('utf-8') + data
            self.socket.sendto(packet, (RELAY_SERVER, RELAY_PORT))
        except Exception as e:
            print(f"Relay send error: {e}")
    
    def get_peer_address(self, fingerprint: str) -> Optional[Tuple[str, int]]:
        """Get address for peer by fingerprint"""
        if fingerprint in self.peers:
            peer = self.peers[fingerprint]
            return (peer.address, peer.port)
        return None
    
    def list_peers(self) -> list:
        """List all discovered peers"""
        return [(fp, peer.address) for fp, peer in self.peers.items()]
    
    def add_peer_manually(self, fingerprint: str, address: str, port: int, name: str = "Manual"):
        """Manually add a peer (for testing when mDNS fails)"""
        self.peers[fingerprint] = PeerInfo(name, address, port)
        print(f"✓ Manually added peer: {fingerprint[:8]} at {address}:{port}")
    
    def delete_peer(self, fingerprint: str):
        """Delete a peer from the list"""
        if fingerprint in self.peers:
            del self.peers[fingerprint]
            print(f"✓ Deleted peer: {fingerprint[:8]}")
