"""Configuration constants for DNI-IM"""

import os

# Network settings
UDP_PORT = int(os.environ.get('UDP_PORT', '6666'))
SERVICE_TYPE = "_dni-im._udp.local."
BUFFER_SIZE = 65535

# Cryptographic settings
NOISE_PROTOCOL = "Noise_IK_25519_ChaChaPoly_BLAKE2s"

# Data directory
DATA_DIR = os.environ.get('DATA_DIR', 'program_files')
os.makedirs(DATA_DIR, exist_ok=True)

# File paths
CONTACTS_FILE = os.environ.get('CONTACTS_FILE', os.path.join(DATA_DIR, 'contacts.json'))
QUEUE_FILE = os.environ.get('QUEUE_FILE', os.path.join(DATA_DIR, 'message_queue.json'))
KEYPAIR_FILE = os.environ.get('KEYPAIR_FILE', os.path.join(DATA_DIR, 'keypair.bin'))

# Configuración del servidor relay
RELAY_SERVER = "34.175.248.84"
RELAY_PORT = 7777
USE_RELAY = True