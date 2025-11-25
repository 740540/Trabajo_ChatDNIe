#!/usr/bin/env python3
"""
Improved Relay Server for DNI-IM with peer discovery
Handles client registration and peer list distribution
"""

import socket
import threading
import time
import struct
from typing import Dict, Tuple

class RelayServer:
    def __init__(self, port=7777):
        self.port = port
        self.clients: Dict[str, Tuple[str, int, float, str]] = {}  # fp -> (ip, port, timestamp, name)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', port))
        self.running = True
        print(f"🚀 DNI-IM Relay Server started on port {port}")
        print(f"   Listening for connections...")
    
    def run(self):
        # Start cleanup thread
        threading.Thread(target=self._cleanup, daemon=True).start()
        
        # Main receive loop
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                threading.Thread(target=self._handle, args=(data, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error: {e}")
    
    def _handle(self, data: bytes, addr: Tuple[str, int]):
        """Handle incoming packet"""
        try:
            if len(data) < 1:
                return
            
            cmd = data[0]
            
            if cmd == 0x01:  # REGISTER
                self._handle_register(data, addr)
            
            elif cmd == 0x02:  # RELAY
                self._handle_relay(data, addr)
            
            elif cmd == 0x03:  # PEER_LIST_REQUEST
                self._handle_peer_list_request(data, addr)
        
        except Exception as e:
            print(f"Handler error: {e}")
    
    def _handle_register(self, data: bytes, addr: Tuple[str, int]):
        """Handle client registration"""
        if len(data) < 17:
            return
        
        fp = data[1:17].decode('utf-8', errors='ignore')
        
        # Extract name if provided (optional)
        name = "Unknown"
        if len(data) > 17:
            try:
                name_len = data[17]
                if len(data) >= 18 + name_len:
                    name = data[18:18+name_len].decode('utf-8', errors='ignore')
            except:
                pass
        
        # Register client
        self.clients[fp] = (addr[0], addr[1], time.time(), name)
        print(f"✓ Registered: {name} ({fp[:8]}...) from {addr[0]}:{addr[1]} - Total clients: {len(self.clients)}")
        
        # Send ACK
        ack = struct.pack('!B', 0x81) + fp.encode('utf-8')
        self.socket.sendto(ack, addr)
    
    def _handle_relay(self, data: bytes, addr: Tuple[str, int]):
        """Relay message to destination"""
        if len(data) < 18:
            return
        
        dest_fp = data[1:17].decode('utf-8', errors='ignore')
        payload = data[17:]
        
        if dest_fp in self.clients:
            dest_addr = self.clients[dest_fp][:2]
            self.socket.sendto(payload, dest_addr)
            print(f"→ Relayed message to {dest_fp[:8]}...")
        else:
            print(f"✗ Destination not found: {dest_fp[:8]}...")
    
    def _handle_peer_list_request(self, data: bytes, addr: Tuple[str, int]):
        """Send list of registered peers to requester"""
        if len(data) < 17:
            return
        
        requester_fp = data[1:17].decode('utf-8', errors='ignore')
        
        # Build peer list (exclude requester)
        peers = [(fp, name) for fp, (ip, port, ts, name) in self.clients.items() 
                 if fp != requester_fp]
        
        if not peers:
            print(f"ℹ Peer list request from {requester_fp[:8]}... - No other peers")
            return
        
        # Build response: [0x82][count:1][fp1:16][name1_len:1][name1][fp2:16]...
        response = bytearray()
        response.append(0x82)  # PEER_LIST command
        response.append(min(len(peers), 255))  # Count (max 255)
        
        for fp, name in peers[:255]:  # Limit to 255 peers
            # Add fingerprint (pad to 16 bytes)
            fp_bytes = fp.encode('utf-8')[:16].ljust(16, b'\x00')
            response.extend(fp_bytes)
            
            # Add name
            name_bytes = name.encode('utf-8')[:255]
            response.append(len(name_bytes))
            response.extend(name_bytes)
        
        self.socket.sendto(bytes(response), addr)
        print(f"→ Sent peer list to {requester_fp[:8]}... ({len(peers)} peers)")
    
    def _cleanup(self):
        """Remove stale clients"""
        while self.running:
            time.sleep(30)
            now = time.time()
            stale = []
            
            for fp, (ip, port, ts, name) in list(self.clients.items()):
                if now - ts > 60:  # 60 seconds timeout
                    stale.append(fp)
            
            for fp in stale:
                name = self.clients[fp][3]
                del self.clients[fp]
                print(f"✗ Removed stale client: {name} ({fp[:8]}...)")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        self.socket.close()
        print("Server stopped")


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           DNI-IM Relay Server (Improved)                 ║
║           With Peer Discovery Support                    ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    server = RelayServer(port=7777)
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.stop()


if __name__ == '__main__':
    main()
