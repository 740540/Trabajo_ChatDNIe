#!/usr/bin/env python3
"""
Local testing script - runs two instances on same machine with different ports
Usage: 
  Terminal 1: python test_local.py --instance 1 [--gui]
  Terminal 2: python test_local.py --instance 2 [--gui]
"""

import sys
import os

# Parse arguments
if len(sys.argv) < 3 or sys.argv[1] != '--instance':
    print("Usage: python test_local.py --instance <1|2> [--gui]")
    sys.exit(1)

instance = sys.argv[2]
use_gui = '--gui' in sys.argv

# Set different ports and files for each instance
if instance == '1':
    os.environ['UDP_PORT'] = '6666'
    os.environ['KEYPAIR_FILE'] = 'keypair_1.bin'
    os.environ['CONTACTS_FILE'] = 'contacts_1.json'
    os.environ['QUEUE_FILE'] = 'queue_1.json'
    print("Starting Instance 1 on port 6666")
elif instance == '2':
    os.environ['UDP_PORT'] = '6667'
    os.environ['KEYPAIR_FILE'] = 'keypair_2.bin'
    os.environ['CONTACTS_FILE'] = 'contacts_2.json'
    os.environ['QUEUE_FILE'] = 'queue_2.json'
    print("Starting Instance 2 on port 6667")
else:
    print("Instance must be 1 or 2")
    sys.exit(1)

# Import and run main application
if use_gui:
    print("Starting with GUI...")
    from main_gui import main
else:
    print("Starting with TUI...")
    from main import main

main()
