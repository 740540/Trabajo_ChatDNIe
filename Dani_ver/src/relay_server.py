#!/usr/bin/env python3
"""
DNI-IM Relay Server
Allows peers to communicate over the Internet without port forwarding
"""

import socket
import threading
import time
from typing import Dict, Tuple
import struct


class RelayServer:
    """Relay server for Internet communication"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 7777):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        
        # fingerprint -> (address, port, last_seen)
        self.clients: Dict[str, Tuple[str, int, float]] = {}
        
        # Statistics
        self.packets_relayed = 0
        self.bytes_relayed = 0
    
    def start(self):
        """Start relay server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        
        self.running = True
        
        print(f"🚀 DNI-IM Relay Server started on {self.host}:{self.port}")
        print(f"📡 Waiting for clients...")
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()
        
        # Start stats thread
        stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
        stats_thread.start()
        
        # Main receive loop
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                threading.Thread(target=self._handle_packet, args=(data, addr), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"❌ Error: {e}")
    
    def _handle_packet(self, data: bytes, addr: Tuple[str, int]):
        """Handle received packet"""
        try:
            if len(data) < 2:
                return
            
            # Packet format: [CMD:1][FINGERPRINT:16][PAYLOAD]
            cmd = data[0]
            
            if cmd == 0x01:  # REGISTER
                # Register client
                fingerprint = data[1:17].decode('utf-8')
                self.clients[fingerprint] = (addr[0], addr[1], time.time())
                print(f"✅ Client registered: {fingerprint[:8]}... from {addr[0]}:{addr[1]}")
                
                # Send ACK
                response = bytes([0x81]) + fingerprint.encode('utf-8')
                self.socket.sendto(response, addr)
            
            elif cmd == 0x02:  # RELAY
                # Relay packet to destination
                if len(data) < 18:
                    return
                
                dest_fingerprint = data[1:17].decode('utf-8')
                payload = data[17:]
                
                if dest_fingerprint in self.clients:
                    dest_addr = self.clients[dest_fingerprint][:2]
                    
                    # Forward packet
                    self.socket.sendto(payload, dest_addr)
                    
                    self.packets_relayed += 1
                    self.bytes_relayed += len(payload)
                else:
                    # Destination not registered
                    print(f"⚠️  Destination not found: {dest_fingerprint[:8]}...")
            
            elif cmd == 0x03:  # LIST_PEERS
                # Send list of registered peers
                peer_list = b''
                for fp in self.clients.keys():
                    peer_list += fp.encode('utf-8')
                
                response = bytes([0x83]) + struct.pack('!H', len(self.clients)) + peer_list
                self.socket.sendto(response, addr)
            
            elif cmd == 0x04:  # KEEPALIVE
                # Update last seen time
                fingerprint = data[1:17].decode('utf-8')
                if fingerprint in self.clients:
                    addr_info = self.clients[fingerprint]
                    self.clients[fingerprint] = (addr_info[0], addr_info[1], time.time())
        
        except Exception as e:
            print(f"❌ Packet handling error: {e}")
    
    def _cleanup_loop(self):
        """Remove inactive clients"""
        while self.running:
            time.sleep(30)
            
            now = time.time()
            timeout = 120  # 2 minutes
            
            inactive = []
            for fp, (ip, port, last_seen) in self.clients.items():
                if now - last_seen > timeout:
                    inactive.append(fp)
            
            for fp in inactive:
                del self.clients[fp]
                print(f"🗑️  Removed inactive client: {fp[:8]}...")
    
    def _stats_loop(self):
        """Print statistics"""
        while self.running:
            time.sleep(60)
            
            print(f"\n📊 Statistics:")
            print(f"   Active clients: {len(self.clients)}")
            print(f"   Packets relayed: {self.packets_relayed}")
            print(f"   Bytes relayed: {self.bytes_relayed / 1024 / 1024:.2f} MB")
            print()
    
    def stop(self):
        """Stop relay server"""
        self.running = False
        if self.socket:
            self.socket.close()
        print("👋 Relay server stopped")


def main():
    """Run relay server"""
    import sys
    
    host = '0.0.0.0'
    port = 7777
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    server = RelayServer(host, port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down...")
        server.stop()


if __name__ == '__main__':
    main()
