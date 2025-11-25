#!/usr/bin/env python3
"""
DNI-IM Relay Server v2 - With Public Key Exchange
"""

import socket, threading, time, struct
from typing import Dict, Tuple

class RelayServer:
    def __init__(self, port=7777):
        self.port = port
        # fp -> (ip, port, timestamp, name, pubkey)
        self.clients: Dict[str, Tuple[str, int, float, str, bytes]] = {}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', port))
        self.running = True
        print(f"🚀 DNI-IM Relay Server v2 started on port {port}")
        print(f"   With public key exchange support")
    
    def run(self):
        threading.Thread(target=self._cleanup, daemon=True).start()
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                threading.Thread(target=self._handle, args=(data, addr), daemon=True).start()
            except: pass
    
    def _handle(self, data: bytes, addr: Tuple[str, int]):
        try:
            if len(data) < 1: return
            cmd = data[0]
            if cmd == 0x01: self._handle_register(data, addr)
            elif cmd == 0x02: self._handle_relay(data, addr)
            elif cmd == 0x03: self._handle_peer_list_request(data, addr)
        except Exception as e:
            print(f"Error: {e}")
    
    def _handle_register(self, data: bytes, addr: Tuple[str, int]):
        # Format: [0x01][fp:16][name_len:1][name][pubkey_len:1][pubkey:32]
        if len(data) < 17: return
        fp = data[1:17].decode('utf-8', errors='ignore')
        offset = 17
        
        # Extract name
        name = "Unknown"
        if offset < len(data):
            try:
                name_len = data[offset]
                offset += 1
                if offset + name_len <= len(data):
                    name = data[offset:offset+name_len].decode('utf-8', errors='ignore')
                    offset += name_len
            except: pass
        
        # Extract public key
        pubkey = b''
        if offset < len(data):
            try:
                pubkey_len = data[offset]
                offset += 1
                if offset + pubkey_len <= len(data):
                    pubkey = data[offset:offset+pubkey_len]
            except: pass
        
        self.clients[fp] = (addr[0], addr[1], time.time(), name, pubkey)
        print(f"✓ {name} ({fp[:8]}) from {addr[0]} - Pubkey: {len(pubkey)} bytes - Total: {len(self.clients)}")
        
        # Send ACK
        ack = struct.pack('!B', 0x81) + fp.encode('utf-8')
        self.socket.sendto(ack, addr)
    
    def _handle_relay(self, data: bytes, addr: Tuple[str, int]):
        if len(data) < 18: return
        dest_fp = data[1:17].decode('utf-8', errors='ignore')
        if dest_fp in self.clients:
            dest_addr = (self.clients[dest_fp][0], self.clients[dest_fp][1])
            self.socket.sendto(data[17:], dest_addr)
    
    def _handle_peer_list_request(self, data: bytes, addr: Tuple[str, int]):
        # Response: [0x82][count:1][fp:16][name_len:1][name][pubkey_len:1][pubkey]...
        if len(data) < 17: return
        requester_fp = data[1:17].decode('utf-8', errors='ignore')
        
        # Get all peers except requester
        peers = [(fp, name, pubkey) for fp, (ip, port, ts, name, pubkey) 
                 in self.clients.items() if fp != requester_fp]
        
        if not peers: return
        
        response = bytearray([0x82, min(len(peers), 255)])
        
        for fp, name, pubkey in peers[:255]:
            # Add fingerprint (pad to 16 bytes)
            fp_bytes = fp.encode('utf-8')[:16].ljust(16, b'\x00')
            response.extend(fp_bytes)
            
            # Add name
            name_bytes = name.encode('utf-8')[:255]
            response.append(len(name_bytes))
            response.extend(name_bytes)
            
            # Add public key
            response.append(len(pubkey) if pubkey else 0)
            if pubkey:
                response.extend(pubkey)
        
        self.socket.sendto(bytes(response), addr)
        print(f"→ Sent {len(peers)} peers (with pubkeys) to {requester_fp[:8]}")
    
    def _cleanup(self):
        while self.running:
            time.sleep(30)
            now = time.time()
            stale = []
            
            for fp, (ip, port, ts, name, pubkey) in list(self.clients.items()):
                if now - ts > 60:
                    stale.append((fp, name))
            
            for fp, name in stale:
                del self.clients[fp]
                print(f"✗ Removed stale client: {name} ({fp[:8]})")

if __name__ == '__main__':
    print("DNI-IM Relay Server v2")
    RelayServer().run()
