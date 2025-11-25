#!/bin/bash
# Single device testing script for DNI-IM
# This script helps you test the app on one machine with two instances

echo "==================================="
echo "DNI-IM Single Device Test"
echo "==================================="
echo ""
echo "This will start two instances of DNI-IM on your machine."
echo "You'll need to manually connect them using their fingerprints."
echo ""
echo "Instructions:"
echo "1. Wait for both instances to start"
echo "2. Note the fingerprints from each terminal"
echo "3. In Instance 1 GUI: Click '➕ Add Peer Manually'"
echo "   - Fingerprint: <Instance 2's fingerprint>"
echo "   - IP: 127.0.0.1"
echo "   - Port: 6667"
echo "4. In Instance 2 GUI: Click '➕ Add Peer Manually'"
echo "   - Fingerprint: <Instance 1's fingerprint>"
echo "   - IP: 127.0.0.1"
echo "   - Port: 6666"
echo "5. Double-click the peer to start chatting!"
echo ""
echo "==================================="
echo ""

# Check if dependencies are installed
if ! python3 -c "import cryptography, zeroconf" 2>/dev/null; then
    echo "❌ Dependencies not installed!"
    echo "Run: pip3 install -r requirements.txt"
    exit 1
fi

echo "✓ Dependencies installed"
echo ""

# Start instance 1
echo "Starting Instance 1 (port 6666)..."
echo "Run this in Terminal 1:"
echo "  python3 test_local.py --instance 1 --gui"
echo ""

# Start instance 2
echo "Starting Instance 2 (port 6667)..."
echo "Run this in Terminal 2:"
echo "  python3 test_local.py --instance 2 --gui"
echo ""

echo "==================================="
echo "Quick Reference:"
echo "==================================="
echo "Instance 1: localhost:6666"
echo "Instance 2: localhost:6667"
echo ""
echo "To add peers manually, use the GUI button or TUI command:"
echo "  /addpeer <fingerprint> 127.0.0.1 <port>"
echo ""
