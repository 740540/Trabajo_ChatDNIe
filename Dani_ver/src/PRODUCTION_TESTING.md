# Production Testing with Real DNIe Cards

## Prerequisites

### Hardware
- 2 computers on the same network (WiFi or Ethernet)
- 2 Spanish DNIe cards (version 3.0 or later)
- 2 PC/SC compatible smart card readers (USB)

### Software Setup (Both Machines)

#### Windows:
```powershell
# Install Python dependencies
pip install cryptography zeroconf pyscard

# Install card reader drivers (if not auto-installed)
# Usually Windows installs them automatically

# Test card reader
python -c "from smartcard.System import readers; print('Readers:', readers())"
```

#### Linux:
```bash
# Install dependencies
sudo apt-get install pcscd pcsc-tools python3-pyscard
pip install cryptography zeroconf pyscard

# Start PC/SC daemon
sudo systemctl start pcscd
sudo systemctl enable pcscd

# Test card reader
pcsc_scan
```

---

## Step-by-Step Testing

### Machine 1 Setup

1. **Connect Card Reader**
   ```bash
   # Verify reader is detected
   python -c "from smartcard.System import readers; print(readers())"
   ```
   Should show: `[<Reader name>]`

2. **Insert DNIe Card**
   - Insert your DNIe card into the reader
   - Wait for Windows/Linux to recognize it

3. **Configure Firewall**
   ```powershell
   # Windows
   netsh advfirewall firewall add rule name="DNI-IM" dir=in action=allow protocol=UDP localport=6666
   netsh advfirewall firewall add rule name="mDNS" dir=in action=allow protocol=UDP localport=5353
   ```
   
   ```bash
   # Linux
   sudo ufw allow 6666/udp
   sudo ufw allow 5353/udp
   ```

4. **Start Application**
   ```bash
   python main_gui.py
   ```

5. **Expected Output**
   ```
   Initializing DNI-IM...
   1. Authenticating with DNIe smart card...
   Found 1 card reader(s)
   Trying reader: <Reader Name>
   ✓ Connected to: <Reader Name>
   Card ATR: 3B 7F 00 00 00 00 6A 44 4E 49 65 ...
   ✓ Master File selected
   ✓ DNIe application selected
   ✓ Certificate file selected
   ✓ Read XXXX bytes of certificate data
   ✓ Certificate parsed successfully
   ✓ Name: GARCIA LOPEZ, JUAN
   ✓ DNI: 12345678A
   ✓ Certificate fingerprint: a1b2c3d4e5f6g7h8
   ✓ DNIe authentication successful!
   
   2. Loading cryptographic keys...
   3. Loading contact book...
   4. Loading message queue...
   5. Starting network services...
   Local IP: 192.168.1.100
   Fingerprint: a1b2c3d4e5f6g7h8
   Registering mDNS service: dni-im-a1b2c3d4._dni-im._udp.local.
   Network started on UDP port 6666
   
   6. Starting GUI...
   DNI-IM GUI ready!
   ```

6. **Note Your Information**
   - **Name**: GARCIA LOPEZ, JUAN
   - **Fingerprint**: a1b2c3d4e5f6g7h8
   - **IP Address**: 192.168.1.100

---

### Machine 2 Setup

1. **Repeat Steps 1-4** from Machine 1
   - Use a different DNIe card
   - Different person's card

2. **Expected Output**
   ```
   ✓ Name: MARTINEZ RODRIGUEZ, MARIA
   ✓ DNI: 87654321B
   ✓ Certificate fingerprint: x9y8z7w6v5u4t3s2
   Local IP: 192.168.1.101
   ```

3. **Note Your Information**
   - **Name**: MARTINEZ RODRIGUEZ, MARIA
   - **Fingerprint**: x9y8z7w6v5u4t3s2
   - **IP Address**: 192.168.1.101

---

## Connecting the Peers

### Option A: Automatic Discovery (Recommended)

If mDNS works on your network:

1. **Wait 5-10 seconds** after both applications start
2. **Check "DISCOVERED PEERS" list** in the GUI
3. You should see:
   - Machine 1 sees: `MARTINEZ RODRIGUEZ, MARIA (x9y8z7w6...)`
   - Machine 2 sees: `GARCIA LOPEZ, JUAN (a1b2c3d4...)`
4. **Double-click the peer** to start chatting!

### Option B: Manual Connection

If mDNS doesn't work:

**On Machine 1:**
1. Click "➕ Add Peer Manually"
2. Fill in:
   - **Fingerprint**: `x9y8z7w6v5u4t3s2` (Machine 2's fingerprint)
   - **IP Address**: `192.168.1.101` (Machine 2's IP)
   - **Port**: `6666`
3. Click "Add Peer"
4. Double-click the peer in the list

**On Machine 2:**
1. Click "➕ Add Peer Manually"
2. Fill in:
   - **Fingerprint**: `a1b2c3d4e5f6g7h8` (Machine 1's fingerprint)
   - **IP Address**: `192.168.1.100` (Machine 1's IP)
   - **Port**: `6666`
3. Click "Add Peer"
4. Double-click the peer in the list

---

## Testing the Chat

### 1. Establish Secure Connection

**Machine 1:**
- Double-click on "MARTINEZ RODRIGUEZ, MARIA" in the peer list
- Chat window opens
- System message: "Establishing secure connection..."
- Wait 1-2 seconds
- System message: "Secure connection established ✓"

**Machine 2:**
- Should see the same process automatically

### 2. Send Messages

**Machine 1:**
- Type: "Hola Maria, ¿cómo estás?"
- Press Enter
- Message appears in green bubble on the right

**Machine 2:**
- Message appears in gray bubble on the left
- Shows: "GARCIA LOPEZ, JUAN: Hola Maria, ¿cómo estás?"
- Reply: "¡Hola Juan! Muy bien, gracias"
- Press Enter

**Machine 1:**
- Receives reply in gray bubble

### 3. Verify Encryption

**On either machine:**
1. Open Wireshark or tcpdump
2. Filter for UDP port 6666
3. Capture packets while sending messages
4. Inspect packet payload
5. **Verify**: Message content is encrypted (looks like random bytes)
6. Only packet headers (Type, CID, StreamID) are visible

### 4. Test Features

**Delete Peer:**
- Select a peer in the list
- Click "🗑️ Delete Peer"
- Confirm deletion
- Peer removed from list (but stays in contacts)

**View Contacts:**
- Click "📋 View Contacts"
- See all verified contacts with TOFU status
- Shows full names from DNIe certificates

**Multiple Chats:**
- Add more peers (if available)
- Open multiple chat windows
- Each conversation is independent
- All use the same secure session

---

## Troubleshooting

### "No smart card readers found"

**Solution:**
```bash
# Windows
# Check Device Manager → Smart card readers
# Reinstall drivers if needed

# Linux
sudo systemctl status pcscd
sudo systemctl restart pcscd
lsusb  # Check if reader is detected
```

### "No card detected in any reader"

**Solution:**
- Remove and reinsert the DNIe card
- Try a different USB port
- Clean the card chip with a soft cloth
- Verify card is not damaged

### "Failed to select DNIe application"

**Solution:**
- Card might be DNIe 2.0 (older version)
- Try updating card at police station
- Some old cards use different file structure

### "Certificate parsing failed"

**Solution:**
- Card might be locked or damaged
- Try reading with official DNIe software first
- Contact authorities if card is damaged

### "Peers not discovering each other"

**Solution:**
```bash
# Check firewall
# Windows
netsh advfirewall show allprofiles state

# Linux
sudo ufw status

# Test network connectivity
ping <other_machine_ip>

# Check mDNS
# Windows: Ensure "Bonjour Service" is running
# Linux: sudo systemctl status avahi-daemon

# Fallback: Use manual peer addition
```

### "Handshake failed"

**Solution:**
- Verify fingerprints are correct
- Check both machines are on same network
- Ensure UDP port 6666 is not blocked
- Try restarting both applications

---

## Security Verification

### 1. Certificate Validation

The application automatically:
- Extracts X.509 certificate from DNIe
- Verifies certificate signature (signed by Spanish government CA)
- Generates unique fingerprint from certificate
- Uses fingerprint as user identity

### 2. TOFU (Trust On First Use)

First contact:
- Public key is saved in `contacts.json`
- Associated with DNIe certificate fingerprint
- Name from DNIe is stored

Subsequent contacts:
- Public key is verified against stored key
- Warning if key changes (possible MITM attack)

### 3. End-to-End Encryption

- Noise IK protocol with X25519 key exchange
- ChaCha20-Poly1305 AEAD encryption
- Perfect Forward Secrecy via ephemeral keys
- Replay protection with nonce counters

### 4. Identity Binding

- User identity = DNIe certificate fingerprint
- Cannot be spoofed without physical card
- Private key never leaves smart card
- Government-issued certificate provides authenticity

---

## Network Requirements

### Same LAN:
- Both machines on same WiFi network, OR
- Both machines on same Ethernet network, OR
- One WiFi, one Ethernet on same router

### Firewall Rules:
- UDP port 6666 (application)
- UDP port 5353 (mDNS)
- Allow local network traffic

### Router Configuration:
- mDNS/Bonjour enabled (usually default)
- No AP isolation (on WiFi)
- Multicast enabled

---

## Expected Behavior

### Successful Connection:
```
[10:30:15] DNI-IM started
[10:30:15] Logged in as: GARCIA LOPEZ, JUAN
[10:30:20] Found 1 peer(s)
[10:30:25] Chat opened with MARTINEZ RODRIGUEZ, MARIA
[10:30:26] Handshake completed with 192.168.1.101
[10:30:26] Secure session established
```

### Message Exchange:
- Instant delivery (< 100ms on LAN)
- Message bubbles with timestamps
- System notifications for connection status
- Color-coded log messages

### Contact Management:
- Names from DNIe certificates
- Fingerprints for verification
- TOFU status tracking
- Persistent across restarts

---

## Production Deployment

### For Organizations:

1. **Deploy on all workstations**
   ```bash
   # Install on each machine
   pip install -r requirements.txt
   
   # Create desktop shortcut
   # Windows: Create .bat file
   # Linux: Create .desktop file
   ```

2. **Configure network**
   - Ensure mDNS is enabled
   - Open required firewall ports
   - Test connectivity between machines

3. **User training**
   - How to insert DNIe card
   - How to start application
   - How to verify contacts (TOFU)
   - How to send encrypted messages

4. **Security policy**
   - Require DNIe authentication
   - Regular certificate updates
   - Monitor for TOFU warnings
   - Audit contact books

---

## Comparison: Mock vs Real DNIe

| Feature | Mock Mode | Real DNIe |
|---------|-----------|-----------|
| Authentication | Random fingerprint | Certificate from card |
| Identity | "Mock User" | Real name from DNIe |
| Security | Testing only | Production-ready |
| TOFU | Works | Works |
| Encryption | Full | Full |
| Use case | Development | Production |

---

## Success Criteria

✅ Both machines authenticate with DNIe cards
✅ Real names appear in peer list
✅ Secure connection established
✅ Messages encrypted and delivered
✅ TOFU verification working
✅ Contact book shows real names
✅ Multiple chats work simultaneously
✅ Wireshark shows encrypted payloads

---

## Next Steps

After successful testing:

1. **Deploy to more users**
2. **Monitor for issues**
3. **Collect feedback**
4. **Add features** (file transfer, group chats, etc.)
5. **Security audit**
6. **Performance optimization**

---

## Support

For issues:
1. Check system log in GUI
2. Review console output
3. Verify DNIe card is working
4. Test with official DNIe software
5. Check network connectivity
6. Review firewall rules

Common issues are usually:
- Card reader drivers
- Firewall blocking ports
- mDNS not working (use manual connection)
- Old DNIe cards (version 2.0)
