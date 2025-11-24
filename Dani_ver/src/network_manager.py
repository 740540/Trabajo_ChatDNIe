"""Network manager for UDP communication and mDNS discovery"""

import socket
import struct
import threading
from typing import Dict, Callable, Optional, Tuple
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
from config import UDP_PORT, SERVICE_TYPE, BUFFER_SIZE
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
        self.peers: Dict[str, PeerInfo] = {}
        self.running = False
        self.receive_callback = None
        
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
                if self.receive_callback:
                    self.receive_callback(data, addr)
            except Exception as e:
                if self.running:
                    print(f"Receive error: {e}")
    
    def send(self, data: bytes, address: str, port: int):
        """Send UDP packet"""
        try:
            self.socket.sendto(data, (address, port))
        except Exception as e:
            print(f"Send error: {e}")
    
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
