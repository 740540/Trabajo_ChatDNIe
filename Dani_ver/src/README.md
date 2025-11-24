# DNI-IM: Secure Peer-to-Peer Instant Messaging

A secure instant messaging platform with DNIe smart card authentication, automatic peer discovery, and end-to-end encryption using the Noise IK protocol.

## 🎯 Features

- 🔐 **DNIe Authentication**: User identity tied to Spanish DNIe smart card certificate
- 🌐 **Internet Support**: Works on same network OR over the Internet with relay server
- 🔒 **End-to-End Encryption**: Noise IK protocol with X25519, BLAKE2s, and ChaCha20-Poly1305
- 🎨 **Modern Dark UI**: WhatsApp/Telegram-style interface
- 👥 **Automatic Discovery**: Find peers automatically on local network
- ✅ **TOFU Verification**: Trust On First Use contact verification
- 📬 **Message Queueing**: Offline message delivery
- 💬 **Multiple Chats**: Manage multiple conversations simultaneously

---

## 📋 Table of Contents

1. [Quick Start](#-quick-start)
2. [Installation](#-installation)
3. [Usage](#-usage)
4. [Internet Setup (Relay Server)](#-internet-setup-relay-server)
5. [Testing](#-testing)
6. [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start

### Same Network (Easiest)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run on both laptops
python main_gui.py

# 3. Peers discover each other automatically!
# 4. Double-click peer to chat
```

### Over Internet (With Relay Server)

```bash
# 1. Set up free relay server (see below)
# 2. Configure relay IP in config.py
# 3. Run on both laptops
python main_gui.py

# 4. Chat from anywhere in the world!
```

---

## 💻 Installation

### Prerequisites

- **Python 3.8+**
- **DNIe smart card reader** (optional, has mock mode for testing)
- **Windows/Linux/macOS**

### Step 1: Clone or Download

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/dni-im.git
cd dni-im

# Or download and extract ZIP
```

### Step 2: Install Python Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

**What gets installed:**
- `cryptography` - Encryption and certificate handling
- `zeroconf` - mDNS peer discovery
- `pyscard` - Smart card reader support (for DNIe)

### Step 3: Verify Installation

```bash
# Test that everything is installed
python -c "import cryptography, zeroconf; print('✓ All dependencies installed!')"
```

### Step 4: Test Smart Card Reader (Optional)

```bash
# Check if card reader is detected
python -c "from smartcard.System import readers; print('Readers:', readers())"
```

**If no reader found:** App will use mock authentication (perfect for testing!)

---

## 🎮 Usage

### Option 1: Modern GUI (Recommended)

```bash
python main_gui.py
```

**Features:**
- Dark-themed WhatsApp-style interface
- Multiple chat windows
- Real-time peer discovery
- System log viewer
- Contact management

### Option 2: Text UI (Terminal)

```bash
python main.py
```

**Commands:**
- `/list` - List discovered peers
- `/chat <number>` - Start chat with peer
- `/contacts` - Show contact book
- `/quit` - Exit

---

## 🌐 Internet Setup (Relay Server)

To chat over the Internet (different networks), you need a relay server.

### Step 1: Create Free Cloud Server

#### **Google Cloud (Free Forever)**

1. **Go to**: https://console.cloud.google.com/
2. **Create new project**: "dni-im-relay"
3. **Go to**: Compute Engine → VM Instances
4. **Click**: "Create Instance"
5. **Configure**:
   - Name: `dni-im-relay`
   - Region: Choose closest to you (e.g., `europe-west1`)
   - Machine type: `e2-micro` (FREE)
   - Boot disk: Ubuntu 22.04 LTS
   - Firewall: ✅ Allow HTTP traffic
6. **Click**: "Create"

#### **Configure Firewall Rule**

1. **Go to**: VPC Network → Firewall
2. **Click**: "Create Firewall Rule"
3. **Configure**:
   - Name: `allow-dni-im`
   - Direction: Ingress
   - Targets: All instances
   - Source IP ranges: `0.0.0.0/0`
   - Protocols and ports: `udp:7777`
4. **Click**: "Create"

### Step 2: Install Relay Server

1. **Connect to VM** (click "SSH" button in Google Cloud console)

2. **Upload relay server**:
```bash
# Create file
nano relay_server.py
```

3. **Copy-paste this code**:
```python
#!/usr/bin/env python3
import socket, threading, time, struct
from typing import Dict, Tuple

class RelayServer:
    def __init__(self, port=7777):
        self.port = port
        self.clients = {}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', port))
        self.running = True
        print(f"🚀 Relay server started on port {port}")
    
    def run(self):
        threading.Thread(target=self._cleanup, daemon=True).start()
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                threading.Thread(target=self._handle, args=(data, addr), daemon=True).start()
            except: pass
    
    def _handle(self, data, addr):
        if len(data) < 2: return
        cmd = data[0]
        if cmd == 0x01:  # REGISTER
            fp = data[1:17].decode('utf-8')
            self.clients[fp] = (addr[0], addr[1], time.time())
            print(f"✅ Registered: {fp[:8]}... from {addr[0]}")
            self.socket.sendto(bytes([0x81]) + fp.encode(), addr)
        elif cmd == 0x02:  # RELAY
            dest = data[1:17].decode('utf-8')
            if dest in self.clients:
                self.socket.sendto(data[17:], self.clients[dest][:2])
    
    def _cleanup(self):
        while self.running:
            time.sleep(60)
            now = time.time()
            for fp in list(self.clients.keys()):
                if now - self.clients[fp][2] > 120:
                    del self.clients[fp]

if __name__ == '__main__':
    RelayServer().run()
```

4. **Save**: Press `Ctrl+X`, then `Y`, then `Enter`

5. **Run relay server**:
```bash
python3 relay_server.py
```

**Output:**
```
🚀 Relay server started on port 7777
```

6. **Keep it running** (optional - run as service):
```bash
# Press Ctrl+C to stop
# Then create systemd service:
sudo nano /etc/systemd/system/dni-im-relay.service
```

**Paste:**
```ini
[Unit]
Description=DNI-IM Relay Server
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME
ExecStart=/usr/bin/python3 /home/YOUR_USERNAME/relay_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl enable dni-im-relay
sudo systemctl start dni-im-relay
sudo systemctl status dni-im-relay
```

### Step 3: Get Relay Server IP

In Google Cloud console, find your VM's **External IP**:
```
Example: 34.123.45.67
```

### Step 4: Configure Clients

**On BOTH laptops**, edit `config.py`:

```python
# Add these lines at the end of config.py
RELAY_SERVER = "34.123.45.67"  # Your relay server IP
RELAY_PORT = 7777
USE_RELAY = True
```

### Step 5: Run and Chat!

```bash
# On both laptops
python main_gui.py
```

**You'll see:**
```
✓ Registered with relay server
✓ Discovered peer: [Name] ([fingerprint])
```

**Double-click peer to chat from anywhere in the world!**

---

## 🧪 Testing

### Test on Same Machine (2 Instances)

```bash
# Terminal 1
python test_local.py --instance 1 --gui

# Terminal 2
python test_local.py --instance 2 --gui
```

**Then:**
1. Note fingerprints from both consoles
2. In Instance 1: Click "➕ Add Peer Manually"
   - Fingerprint: (Instance 2's fingerprint)
   - IP: `127.0.0.1`
   - Port: `6667`
3. In Instance 2: Click "➕ Add Peer Manually"
   - Fingerprint: (Instance 1's fingerprint)
   - IP: `127.0.0.1`
   - Port: `6666`
4. Double-click peers to chat!

### Test on Same Network (2 Laptops)

```bash
# On both laptops
python main_gui.py

# Wait 5-10 seconds
# Peers appear automatically!
# Double-click to chat
```

### Test Over Internet (2 Laptops, Different Networks)

```bash
# 1. Set up relay server (see above)
# 2. Configure relay IP in config.py on both laptops
# 3. Run on both laptops
python main_gui.py

# 4. Peers discover each other through relay
# 5. Double-click to chat!
```

---

## 🔧 Troubleshooting

### "No smart card readers found"

**Solution:** App will use mock authentication automatically. Perfect for testing!

**For production:** Install card reader drivers and insert DNIe card.

### "Peers not discovering"

**Solution 1 - Same Network:**
```bash
# Check firewall allows UDP 6666
# Windows:
netsh advfirewall firewall add rule name="DNI-IM" dir=in action=allow protocol=UDP localport=6666

# Linux:
sudo ufw allow 6666/udp
```

**Solution 2 - Manual Addition:**
1. Click "➕ Add Peer Manually"
2. Enter peer's fingerprint and IP
3. Click "Add Peer"

### "Can't connect to relay server"

**Check:**
```bash
# Test connectivity
nc -u YOUR_RELAY_IP 7777

# Check relay server is running
# On relay server:
sudo systemctl status dni-im-relay
```

### "Handshake failed"

**Solution:**
- Verify fingerprints are correct
- Check both machines can reach each other
- Restart both applications

### "Import errors"

**Solution:**
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Or install individually:
pip install cryptography zeroconf pyscard
```

---

## 📁 Project Structure

```
dni-im/
├── main_gui.py              # Main GUI application
├── main.py                  # TUI application
├── gui_modern.py            # Modern dark-themed GUI
├── tui.py                   # Text user interface
├── crypto_engine.py         # Noise protocol implementation
├── dnie_auth.py             # DNIe authentication (with mock)
├── dnie_auth_real.py        # Real DNIe authentication
├── network_manager.py       # UDP and mDNS networking
├── protocol.py              # Session multiplexing
├── contact_manager.py       # Contact book & TOFU
├── message_queue.py         # Offline message queue
├── config.py                # Configuration
├── relay_server.py          # Relay server for Internet
├── test_local.py            # Local testing script
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

---

## 🔐 Security

### End-to-End Encryption
- **Noise IK Protocol**: Industry-standard cryptographic protocol
- **X25519**: Elliptic curve key exchange
- **ChaCha20-Poly1305**: Authenticated encryption
- **Perfect Forward Secrecy**: Each session has unique keys

### Authentication
- **DNIe Certificate**: Government-issued identity
- **TOFU Verification**: Trust on first use
- **Public Key Pinning**: Detects MITM attacks

### Privacy
- **Local Network**: Full privacy, no relay
- **Relay Server**: Can see metadata (IPs, fingerprints) but NOT message content
- **No Central Server**: Peer-to-peer architecture

---

## 🌍 Network Options

| Scenario | Solution | Setup Time |
|----------|----------|------------|
| Same WiFi | Automatic discovery | 1 minute |
| Same office LAN | Automatic discovery | 1 minute |
| Different networks | Relay server | 15 minutes |
| Over Internet | Relay server | 15 minutes |
| Maximum security | VPN + automatic | 30 minutes |

---

## 💡 Tips

### For Best Performance
- Use same network when possible (lowest latency)
- Deploy relay server close to users
- Use wired connection for stability

### For Maximum Security
- Use real DNIe authentication (not mock)
- Verify contact fingerprints manually
- Use VPN instead of relay for sensitive communications

### For Testing
- Use mock authentication (no DNIe card needed)
- Test on same machine with `test_local.py`
- Use relay server for Internet testing

---

## 📚 Additional Documentation

- **`PRODUCTION_TESTING.md`** - Testing with real DNIe cards
- **`INTERNET_SETUP.md`** - Detailed Internet setup options
- **`RELAY_DEPLOYMENT.md`** - Advanced relay server deployment
- **`NETWORK_OPTIONS.md`** - Complete network configuration guide
- **`GUI_GUIDE.md`** - GUI usage guide
- **`DNIE_SETUP.md`** - Real DNIe authentication setup

---

## 🎓 Quick Command Reference

```bash
# Install dependencies
pip install -r requirements.txt

# Run GUI (recommended)
python main_gui.py

# Run TUI (terminal)
python main.py

# Test locally (2 instances)
python test_local.py --instance 1 --gui
python test_local.py --instance 2 --gui

# Run relay server
python3 relay_server.py

# Check dependencies
python -c "import cryptography, zeroconf; print('OK')"

# Check card reader
python -c "from smartcard.System import readers; print(readers())"
```

---

## ❓ FAQ

**Q: Do I need a DNIe card?**
A: No! The app has mock authentication for testing. For production, use real DNIe.

**Q: Can I use it over the Internet?**
A: Yes! Set up a free relay server (15 minutes) or use port forwarding.

**Q: Is it secure?**
A: Yes! End-to-end encryption with Noise protocol. Even relay server can't read messages.

**Q: How much does it cost?**
A: Free! Use Google Cloud free tier for relay server.

**Q: Can I use it on mobile?**
A: Currently desktop only (Windows/Linux/macOS). Mobile version possible in future.

**Q: How many people can use one relay server?**
A: 50-100 users on free tier, thousands on paid plans.

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Mobile app (Android/iOS)
- File transfer support
- Group chats
- Voice/video calls
- Better UI/UX

---

## 📄 License

Educational project for cryptography and secure communications course.

---

## 🎉 You're Ready!

**To start chatting:**

1. **Install**: `pip install -r requirements.txt`
2. **Run**: `python main_gui.py`
3. **Chat**: Double-click peer in list

**For Internet use:**
1. **Set up relay**: Follow "Internet Setup" section
2. **Configure**: Add relay IP to `config.py`
3. **Run**: `python main_gui.py`
4. **Chat**: From anywhere in the world!

**Need help?** Check the troubleshooting section or additional documentation files.

**Happy secure chatting! 🔒💬**

## Architecture

### Cryptographic Protocol

- **Key Exchange**: X25519 Elliptic Curve Diffie-Hellman
- **Hashing**: BLAKE2s with HKDF key derivation
- **Encryption**: ChaCha20-Poly1305 AEAD
- **Handshake**: Noise IK pattern (initiator knows responder's static key)

### Network Protocol

```
Packet Format:
[MessageType:1][CID:4][StreamID:2][Payload:variable]

MessageType:
  1 = HANDSHAKE_INIT
  2 = HANDSHAKE_RESP
  3 = DATA
  4 = ACK
```

### Components

- `dnie_auth.py`: DNIe smart card authentication
- `crypto_engine.py`: Noise protocol implementation
- `network_manager.py`: UDP socket and mDNS discovery
- `protocol.py`: Session multiplexing with CIDs/Stream IDs
- `contact_manager.py`: TOFU verification and contact book
- `message_queue.py`: Offline message queueing
- `tui.py`: Text user interface
- `main.py`: Application coordinator

## Installation

```bash
pip install -r requirements.txt
```

### Requirements

- Python 3.8+
- DNIe smart card reader (or mock mode for development)
- cryptography library
- zeroconf library
- pyscard library

## Usage

### GUI Mode (Recommended)

```bash
python main_gui.py
```

Features:
- Modern graphical interface
- Multiple chat windows
- Real-time peer discovery
- System log viewer
- Contact management
- Manual peer addition dialog

### TUI Mode (Terminal)

```bash
python main.py
```

Commands:
- `/list` - List discovered peers
- `/chat <number>` - Start chat with peer (use number from /list)
- `/contacts` - Show contact book
- `/switch <fingerprint>` - Switch active chat
- `/quit` - Exit application

### First Run

1. Insert DNIe card (or use mock authentication)
2. Application authenticates and generates X25519 keypair
3. Starts mDNS advertising and UDP listener
4. Use `/list` to see discovered peers
5. Use `/chat 1` to start secure session with first peer
6. Type messages directly (no prefix needed)

## Security Features

### Trust On First Use (TOFU)

On first contact with a peer:
- Public key fingerprint is stored in `contacts.json`
- Subsequent connections verify against stored fingerprint
- Warns if public key changes (possible MITM attack)

### Session Security

- Perfect Forward Secrecy via ephemeral keys
- Replay protection with nonce counters
- Authentication via static keys tied to DNIe certificates

### Message Queueing

- Messages to offline peers stored in `message_queue.json`
- Automatically delivered when peer comes online
- Encrypted with established session keys

## File Structure

```
.
├── main.py                 # Application entry point
├── dnie_auth.py           # DNIe authentication
├── crypto_engine.py       # Noise protocol crypto
├── network_manager.py     # UDP and mDNS
├── protocol.py            # Session multiplexing
├── contact_manager.py     # Contact book & TOFU
├── message_queue.py       # Offline messages
├── tui.py                 # Text UI
├── config.py              # Configuration
├── requirements.txt       # Dependencies
├── keypair.bin           # X25519 keypair (generated)
├── contacts.json         # Contact book (generated)
└── message_queue.json    # Queued messages (generated)
```

## Development Notes

### Mock DNIe Authentication

For development without physical DNIe card, the application falls back to mock authentication mode. In production, implement proper APDU commands for certificate extraction.

### Testing

Run multiple instances on same machine:
1. Modify UDP_PORT in config.py for each instance
2. Each instance will discover others via mDNS
3. Test handshake and encrypted messaging

### Extending

- Add file transfer support
- Implement group chats with multiple Stream IDs
- Add message persistence/history
- Implement proper certificate chain validation
- Add GUI with Qt or similar

## Protocol Details

### Noise IK Handshake

```
Initiator                    Responder
---------                    ---------
e, es, s, ss  ---------->
              <----------    (implicit ACK)

Where:
  e  = ephemeral key
  es = ephemeral-static DH
  s  = static key (encrypted)
  ss = static-static DH
```

### Session Establishment

1. Initiator discovers responder via mDNS
2. Initiator retrieves responder's public key from contact book
3. Initiator sends HANDSHAKE_INIT with Noise IK message
4. Responder processes handshake, verifies with TOFU
5. Responder sends HANDSHAKE_RESP (ACK)
6. Both parties derive send/recv keys
7. DATA messages encrypted with ChaCha20-Poly1305

## License

Educational project for cryptography and secure communications course.
