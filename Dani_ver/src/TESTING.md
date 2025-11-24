# Testing Guide

## Problem: mDNS Discovery Not Working on Windows Localhost

mDNS/Zeroconf can have issues on Windows when both instances run on the same machine. Here are solutions:

## Solution 1: Manual Peer Addition (Easiest)

### Step 1: Start Instance 1
```bash
python test_local.py --instance 1
```

Note the output:
```
Local IP: 192.168.1.100
Fingerprint: abc123def456
Network started on UDP port 6666
```

### Step 2: Start Instance 2
```bash
python test_local.py --instance 2
```

Note the output:
```
Local IP: 192.168.1.100
Fingerprint: 789xyz012abc
Network started on UDP port 6667
```

### Step 3: Manually Add Peers

**In Instance 1 terminal:**
```
/addpeer 789xyz012abc 127.0.0.1 6667
/list
/chat 1
```

**In Instance 2 terminal:**
```
/addpeer abc123def456 127.0.0.1 6666
/list
/chat 1
```

Now you can chat between instances!

---

## Solution 2: Test on Two Different Machines (Best)

### Machine 1:
```bash
python main.py
```
Note the fingerprint from output.

### Machine 2:
```bash
python main.py
```

Both should auto-discover via mDNS. Use `/list` to see each other.

If mDNS still doesn't work:
```
# Machine 1
/addpeer <machine2_fingerprint> <machine2_ip> 6666

# Machine 2
/addpeer <machine1_fingerprint> <machine1_ip> 6666
```

---

## Solution 3: Check Windows Firewall

mDNS uses UDP port 5353. Ensure it's not blocked:

```powershell
# Allow mDNS
netsh advfirewall firewall add rule name="mDNS" dir=in action=allow protocol=UDP localport=5353

# Allow DNI-IM UDP ports
netsh advfirewall firewall add rule name="DNI-IM-6666" dir=in action=allow protocol=UDP localport=6666
netsh advfirewall firewall add rule name="DNI-IM-6667" dir=in action=allow protocol=UDP localport=6667
```

---

## Debugging mDNS

The updated code now shows detailed mDNS debug output:

```
[mDNS] Service add: dni-im-abc123._dni-im._udp.local.
[mDNS] Address: 192.168.1.100:6666
[mDNS] Fingerprint: abc123de
✓ Discovered peer: abc123de at 192.168.1.100:6666
```

If you don't see these messages, mDNS is not working on your network.

---

## Complete Test Flow

### Terminal 1:
```bash
python test_local.py --instance 1

# Wait for startup, note fingerprint (e.g., "a1b2c3d4e5f6")
# Manually add instance 2:
/addpeer <instance2_fingerprint> 127.0.0.1 6667
/list
/chat 1
Hello from instance 1!
```

### Terminal 2:
```bash
python test_local.py --instance 2

# Wait for startup, note fingerprint (e.g., "x9y8z7w6v5u4")
# Manually add instance 1:
/addpeer <instance1_fingerprint> 127.0.0.1 6666
/list
/chat 1
Hello from instance 2!
```

You should see:
- Handshake establishment messages
- Encrypted messages being exchanged
- Messages appearing in both terminals

---

## Verifying Encryption

The messages are encrypted with ChaCha20-Poly1305. You can verify by:

1. Running Wireshark on UDP port 6666/6667
2. You'll see UDP packets but the payload is encrypted
3. Only the packet header (Type, CID, StreamID) is visible
4. Message content is ciphertext

---

## Common Issues

### "No peers found"
- Use `/addpeer` to manually add
- Check firewall settings
- Ensure both instances are running

### "Handshake failed"
- Check that fingerprints are correct
- Ensure IP addresses are reachable
- Verify ports are not blocked

### "Message not delivered"
- Ensure handshake completed (look for "Session X established")
- Check `/list` shows the peer
- Try `/addpeer` again if peer disappeared

---

## Production Testing (Two Machines)

For real-world testing:

1. **Same WiFi network**: Both machines on same WiFi
2. **Run normally**: `python main.py` on both
3. **Auto-discovery**: Should work via mDNS
4. **Manual fallback**: Use `/addpeer` if needed

Example:
```bash
# Machine 1 (IP: 192.168.1.10)
python main.py
# Note fingerprint: abc123

# Machine 2 (IP: 192.168.1.20)
python main.py
# Note fingerprint: xyz789

# If auto-discovery fails:
# On Machine 1:
/addpeer xyz789 192.168.1.20 6666

# On Machine 2:
/addpeer abc123 192.168.1.10 6666
```
