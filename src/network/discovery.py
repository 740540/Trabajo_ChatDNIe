# dnie_im/network/discovery.py

"""
mDNS / Zeroconf service discovery:
- Advertises this IM client as _dni-im._udp.local. on UDP/5353
- Discovers other peers with the same service type
"""

import socket
import base64
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
        self.on_peer_disconnected_callback: Optional[Callable[[Peer], None]] = None
        self.on_peer_renamed_callback: Optional[Callable[[Peer, str, str], None]] = None  # NEW: (peer, old_name, new_name)
        self.browser: Optional[ServiceBrowser] = None
        # FIXED: Store static_key to be set by messenger
        self.static_public_key: Optional[bytes] = None

    async def start_advertising(self, username: str):
        """Advertise presence on local network with DNIe identity."""
        self.aiozc = AsyncZeroconf()
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)

        # FIXED: Use static_public_key that was set by messenger
        if not self.static_public_key:
            raise ValueError("static_public_key must be set before advertising")

        static_key_b64 = base64.b64encode(self.static_public_key).decode('utf-8')

        self.service_info = ServiceInfo(
            type_="_dni-im._udp.local.",
            name=f"{username}._dni-im._udp.local.",
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties={
                b"version": b"1.0",
                b"peer_id": (self.identity.peer_id or "unknown").encode("utf-8"),
                b"user": username.encode("utf-8"),
                b"static_key": static_key_b64.encode("utf-8"),
            },
        )

        await self.aiozc.async_register_service(self.service_info)
        # Commented out to not clutter terminal
        # print(f"✅ Anunciando presencia como '{username}' (Peer ID: {self.identity.peer_id})")

        # Start browser to discover other peers
        self.browser = ServiceBrowser(
            self.aiozc.zeroconf,
            "_dni-im._udp.local.",
            handlers=[self._on_service_state_change],
        )

    async def stop_advertising(self):
        """Stop advertising and clean up zeroconf."""
        if self.aiozc and self.service_info:
            try:
                await self.aiozc.async_unregister_service(self.service_info)
            finally:
                await self.aiozc.async_close()
                self.aiozc = None
                self.service_info = None
                self.browser = None

    def _on_service_state_change(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
        state_change: ServiceStateChange,
    ):
        """Internal callback invoked by Zeroconf for service events."""
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if not info:
                return

            # Ignore our own service
            if self.service_info and name == self.service_info.name:
                return

            if not info.addresses:
                return

            address = socket.inet_ntoa(info.addresses[0])
            port = info.port
            peer_id = info.properties.get(b"peer_id", b"").decode("utf-8")
            username = info.properties.get(b"user", b"").decode("utf-8")

            # Extract static public key from TXT record
            static_key_b64 = info.properties.get(b"static_key", b"").decode("utf-8")
            static_key = None
            if static_key_b64:
                try:
                    static_key = base64.b64decode(static_key_b64)
                except Exception as e:
                    # Commented out to not clutter terminal
                    pass

            # NEW: Check if peer with same peer_id already exists (name change detection)
            existing_peer = None
            for service_name, peer in self.discovered_peers.items():
                if peer.peer_id == peer_id and peer.peer_id:  # Match by peer_id
                    existing_peer = peer
                    break

            if existing_peer:
                # Peer already exists - check if name changed
                if existing_peer.name != username:
                    # Name has changed!
                    old_name = existing_peer.name
                    existing_peer.name = username

                    # Update the dictionary key as well (service name changed)
                    # Remove old service name entry
                    for service_name in list(self.discovered_peers.keys()):
                        if self.discovered_peers[service_name] == existing_peer:
                            del self.discovered_peers[service_name]
                            break

                    # Add with new service name
                    self.discovered_peers[name] = existing_peer

                    # Notify about name change
                    if self.on_peer_renamed_callback:
                        self.on_peer_renamed_callback(existing_peer, old_name, username)
                else:
                    # Same peer, same name - just update service name mapping if needed
                    if name not in self.discovered_peers:
                        self.discovered_peers[name] = existing_peer
            else:
                # New peer - add normally
                peer = Peer(
                    name=username,
                    address=address,
                    port=port,
                    peer_id=peer_id,
                    static_public_key=static_key,
                )
                self.discovered_peers[name] = peer
                # Commented out to not clutter terminal
                # print(f"🔍 Peer descubierto: {username} @ {address}:{port} (ID: {peer_id})")

                if self.on_peer_discovered_callback:
                    self.on_peer_discovered_callback(peer)

        elif state_change is ServiceStateChange.Removed:
            if name in self.discovered_peers:
                removed_peer = self.discovered_peers[name]
                # Commented out to not clutter terminal
                # print(f"👋 Peer desconectado: {removed_peer.name}")

                if self.on_peer_disconnected_callback:
                    self.on_peer_disconnected_callback(removed_peer)

                del self.discovered_peers[name]
