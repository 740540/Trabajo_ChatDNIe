#!/usr/bin/env python3
"""DNIe Instant Messenger - Entry point"""

import asyncio
import getpass
from messenger import DNIeMessenger


async def main():
    """Application entry point with PIN prompt"""
    print("=" * 60)
    print("DNIe Instant Messenger - Peer-to-Peer Chat")
    print("=" * 60)
    
    username = input("Nombre de usuario: ").strip() or "Usuario"
    pin = getpass.getpass("PIN del DNIe: ")
    
    messenger = DNIeMessenger(username)
    
    try:
        await messenger.initialize(pin)
        await messenger.run()
    except KeyboardInterrupt:
        print("\n👋 Cerrando...")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
