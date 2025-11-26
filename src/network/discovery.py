"""mDNS service discovery for peer detection"""

import socket
from typing import Dict, Callable, Optional
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceStateChange
from zeroconf.asyncio import AsyncZeroconf

from session.session import Peer


class ServiceDiscovery:
    """
    Advertises and discovers peers using mDNS on UDP/5353.
    Service type: _dni-im._udp.local.
    """
    
    def __init__(self, identity, port: int = 443):
        self.identity = identity
        self.port = port
        self.aiozc: Optional[AsyncZeroconf] = None
        self.service_info: Optional[ServiceInfo] = None
        self.discovered_peers: Dict[str, Peer] = {}
        self.on_peer_discovered_callback: Optional[Callable[[Peer], None]] = None
        self.on_peer_disconnected_callback = None
    
    async def start_advertising(self, username: str):
        """Advertise presence on local network with DNIe identity"""
        self.aiozc = AsyncZeroconf()
        
        # Get local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        # Create service info with DNIe peer ID
        cert_info = self.identity.get_certificate_info()
        
        self.service_info = ServiceInfo(
            type_="_dni-im._udp.local.",
            name=f"{username}._dni-im._udp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties={
                'version': '1.0',
                'peer_id': self.identity.peer_id or 'unknown',
                'user': username
            }
        )
        
        await self.aiozc.async_register_service(self.service_info)
        print(f"✅ Anunciando presencia como '{username}' (Peer ID: {self.identity.peer_id})")
        
        # Start browser to discover other peers
        self.browser = ServiceBrowser(
            self.aiozc.zeroconf,
            "_dni-im._udp.local.",
            handlers=[self._on_service_state_change]
        )
    
    def _on_service_state_change(self, zeroconf: Zeroconf, service_type: str, 
                                  name: str, state_change: ServiceStateChange):
        """Callback for service discovery events"""
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                # Don't add ourselves
                if name == self.service_info.name:
                    return
                
                address = socket.inet_ntoa(info.addresses[0])
                port = info.port
                peer_id = info.properties.get(b'peer_id', b'').decode('utf-8')
                username = info.properties.get(b'user', b'').decode('utf-8')
                
                peer = Peer(
                    name=username,
                    address=address,
                    port=port,
                    peer_id=peer_id
                )
                
                self.discovered_peers[name] = peer
                
                if self.on_peer_discovered_callback:
                    self.on_peer_discovered_callback(peer)
                
                print(f"🔍 Peer descubierto: {username} @ {address}:{port} (ID: {peer_id})")
        
        elif state_change is ServiceStateChange.Removed:
            if name in self.discovered_peers:
                removed_peer = self.discovered_peers[name]
                print(f"👋 Peer desconectado: {removed_peer.name}")
                
                # Notify messenger about disconnection (NEW)
                if self.on_peer_disconnected_callback:
                    self.on_peer_disconnected_callback(removed_peer)

                del self.discovered_peers[name]
            
    async def stop_advertising(self):
        """Stop advertising and cleanup"""
        if self.aiozc and self.service_info:
            await self.aiozc.async_unregister_service(self.service_info)
            await self.aiozc.async_close()
