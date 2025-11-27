# main.py

"""
Entry point for DNIe Instant Messenger.
Runs the async messenger and TUI in the current terminal.
"""

import asyncio
import getpass

from messenger import DNIeMessenger


async def main():
    print("=== DNIe Instant Messenger ===")
    username = input("Nombre de usuario: ").strip() or "Usuario"
    pin = getpass.getpass("PIN del DNIe: ")

    messenger = DNIeMessenger(username)
    loop = asyncio.get_running_loop()
    messenger.loop = loop

    await messenger.initialize(pin)
    await messenger.run()


if __name__ == "__main__":
    asyncio.run(main())
