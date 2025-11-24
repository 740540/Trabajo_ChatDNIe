"""Configuration constants for DNI-IM"""

import os

# Network settings
UDP_PORT = int(os.environ.get('UDP_PORT', '6666'))
SERVICE_TYPE = "_dni-im._udp.local."
BUFFER_SIZE = 65535

# Cryptographic settings
NOISE_PROTOCOL = "Noise_IK_25519_ChaChaPoly_BLAKE2s"

# File paths
CONTACTS_FILE = os.environ.get('CONTACTS_FILE', 'contacts.json')
QUEUE_FILE = os.environ.get('QUEUE_FILE', 'message_queue.json')
KEYPAIR_FILE = os.environ.get('KEYPAIR_FILE', 'keypair.bin')
