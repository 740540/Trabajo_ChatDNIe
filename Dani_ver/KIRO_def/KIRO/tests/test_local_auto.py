#!/usr/bin/env python3
"""
Enhanced local testing script with automatic peer discovery for localhost
Usage: 
  Terminal 1: python3 test_local_auto.py --instance 1 [--gui]
  Terminal 2: python3 test_local_auto.py --instance 2 [--gui]

This version automatically discovers the other instance on localhost!
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import time
import threading

# Parse arguments
if len(sys.argv) < 3 or sys.argv[1] != '--instance':
    print("Usage: python3 test_local_auto.py --instance <1|2> [--gui]")
    sys.exit(1)

instance = sys.argv[2]
use_gui = '--gui' in sys.argv

# Set different ports and files for each instance
data_dir = os.path.join(os.path.dirname(__file__), '..', 'program_files')
os.makedirs(data_dir, exist_ok=True)

if instance == '1':
    os.environ['UDP_PORT'] = '6666'
    os.environ['DATA_DIR'] = data_dir
    os.environ['KEYPAIR_FILE'] = os.path.join(data_dir, 'keypair_1.bin')
    os.environ['CONTACTS_FILE'] = os.path.join(data_dir, 'contacts_1.json')
    os.environ['QUEUE_FILE'] = os.path.join(data_dir, 'queue_1.json')
    peer_port = 6667
    peer_file = os.path.join(data_dir, 'keypair_2.bin')
    state_file = os.path.join(data_dir, '.instance1_state.json')
    peer_state_file = os.path.join(data_dir, '.instance2_state.json')
    print("Starting Instance 1 on port 6666")
elif instance == '2':
    os.environ['UDP_PORT'] = '6667'
    os.environ['DATA_DIR'] = data_dir
    os.environ['KEYPAIR_FILE'] = os.path.join(data_dir, 'keypair_2.bin')
    os.environ['CONTACTS_FILE'] = os.path.join(data_dir, 'contacts_2.json')
    os.environ['QUEUE_FILE'] = os.path.join(data_dir, 'queue_2.json')
    peer_port = 6666
    peer_file = os.path.join(data_dir, 'keypair_1.bin')
    state_file = os.path.join(data_dir, '.instance2_state.json')
    peer_state_file = os.path.join(data_dir, '.instance1_state.json')
    print("Starting Instance 2 on port 6667")
else:
    print("Instance must be 1 or 2")
    sys.exit(1)

print("🔍 Auto-discovery enabled for localhost testing")

# Function to write our state
def write_state(fingerprint):
    """Write our fingerprint to state file"""
    with open(state_file, 'w') as f:
        json.dump({
            'fingerprint': fingerprint,
            'port': int(os.environ['UDP_PORT']),
            'timestamp': time.time()
        }, f)

# Function to read peer state
def read_peer_state():
    """Read peer's fingerprint from their state file"""
    try:
        if os.path.exists(peer_state_file):
            with open(peer_state_file, 'r') as f:
                data = json.load(f)
                # Check if state is recent (within last 60 seconds)
                if time.time() - data.get('timestamp', 0) < 60:
                    return data.get('fingerprint'), data.get('port')
    except:
        pass
    return None, None

# Function to auto-add peer
def auto_add_peer(app):
    """Automatically add peer when they come online"""
    print("🔄 Watching for peer instance...")
    attempts = 0
    max_attempts = 30  # 30 seconds
    
    while attempts < max_attempts:
        peer_fp, peer_port_found = read_peer_state()
        if peer_fp and peer_port_found:
            print(f"✓ Found peer instance!")
            print(f"  Fingerprint: {peer_fp}")
            print(f"  Port: {peer_port_found}")
            
            # Add peer to network manager
            if hasattr(app, 'network') and app.network:
                app.network.add_peer_manually(peer_fp, '127.0.0.1', peer_port_found, f"Instance {3-int(instance)}")
                print(f"✓ Automatically added peer to your peers list!")
                print(f"  You can now double-click to start chatting!")
                
                # Update GUI if available
                if hasattr(app, 'gui') and app.gui:
                    peers = app.network.list_peers()
                    app.gui.update_peers(peers)
                    app.gui.log(f"Auto-discovered peer on localhost!", 'success')
            
            return
        
        time.sleep(1)
        attempts += 1
    
    print("⚠ Peer instance not found after 30 seconds")
    print("  Make sure the other instance is running!")

# Monkey-patch the application to add auto-discovery
original_initialize = None

def patched_initialize(self):
    """Patched initialize that adds auto-discovery"""
    result = original_initialize(self)
    
    if result:
        # Write our state
        my_fp = self.dnie_auth.get_fingerprint()
        write_state(my_fp)
        
        # Start auto-discovery thread
        threading.Thread(target=auto_add_peer, args=(self,), daemon=True).start()
    
    return result

# Import and patch
if use_gui:
    print("Starting with GUI...")
    from main_gui import DNIIMApplication, main
else:
    print("Starting with TUI...")
    from main import DNIIMApplication, main

# Apply patch
original_initialize = DNIIMApplication.initialize
DNIIMApplication.initialize = patched_initialize

# Run
main()

# Cleanup state file on exit
try:
    if os.path.exists(state_file):
        os.remove(state_file)
except:
    pass
