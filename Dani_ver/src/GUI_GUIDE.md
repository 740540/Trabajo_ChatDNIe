# DNI-IM GUI Guide

## Starting the GUI

### Single Machine Testing

**Terminal 1:**
```bash
python test_local.py --instance 1 --gui
```

**Terminal 2:**
```bash
python test_local.py --instance 2 --gui
```

### Production (Two Machines)

```bash
python main_gui.py
```

---

## GUI Overview

### Main Window

The main window has two panels:

**Left Panel - Contacts & Peers:**
- Your identity (name and fingerprint)
- List of discovered peers
- Buttons for peer management

**Right Panel - System Log:**
- Real-time system events
- Connection status
- Error messages
- Color-coded messages (green=success, red=error, yellow=warning)

---

## How to Use

### 1. Discover Peers

Peers are automatically discovered via mDNS and appear in the "Discovered Peers" list.

- Click **"Refresh Peers"** to manually update the list
- Peers show as: `abc12345... @ 192.168.1.100`

### 2. Start a Chat

**Option A: Double-click a peer** in the list

**Option B: Manual peer addition**
1. Click **"Add Peer Manually"**
2. Enter:
   - Fingerprint (from other instance)
   - IP address (e.g., `127.0.0.1` for local testing)
   - Port (e.g., `6667` for instance 2)
3. Click **"Add"**
4. Double-click the peer in the list

### 3. Chat Window

A new window opens for each conversation:

**Features:**
- Message history with timestamps
- Color-coded messages (blue=you, pink=them)
- System messages (gray, italic)
- Multi-line input (Shift+Enter for newline)
- Send button or press Enter

**Security:**
- First message triggers Noise IK handshake
- System message shows "Establishing secure connection..."
- When ready: "Secure connection established ✓"
- All messages are end-to-end encrypted

### 4. Multiple Chats

- Open multiple chat windows simultaneously
- Each conversation has its own Stream ID
- Windows can be minimized/restored independently
- Closing a chat window doesn't end the session

### 5. View Contacts

Click **"View Contacts"** to see your contact book:
- Friendly names
- Full fingerprints
- TOFU verification status

---

## Testing Workflow

### Instance 1 Setup:

1. Start: `python test_local.py --instance 1 --gui`
2. Note your fingerprint in the GUI (e.g., `a1b2c3d4e5f6`)
3. Click "Add Peer Manually"
4. Enter Instance 2's fingerprint, `127.0.0.1`, port `6667`
5. Click "Add"
6. Double-click the peer to open chat
7. Wait for "Secure connection established ✓"
8. Type message and press Enter

### Instance 2 Setup:

1. Start: `python test_local.py --instance 2 --gui`
2. Note your fingerprint (e.g., `x9y8z7w6v5u4`)
3. Click "Add Peer Manually"
4. Enter Instance 1's fingerprint, `127.0.0.1`, port `6666`
5. Click "Add"
6. Double-click the peer to open chat
7. You should see Instance 1's message appear!
8. Reply and chat!

---

## Features Explained

### Automatic Discovery (mDNS)

- Peers on the same network are auto-discovered
- No manual configuration needed in production
- Updates every 5 seconds
- Works across different machines on same LAN

### Manual Peer Addition

- Fallback when mDNS doesn't work (Windows localhost)
- Useful for testing on same machine
- Required for cross-network communication
- Peers persist until application restart

### Message Queueing

- Messages to offline peers are queued
- Automatically delivered when peer comes online
- System message shows "Message queued - peer offline"
- Queue persists across restarts

### TOFU Verification

- First contact: public key is saved
- Subsequent contacts: key is verified
- Warning if key changes (possible MITM attack)
- Contact book shows verified contacts

### Session Management

- One secure session per peer
- Multiple conversations (Stream IDs) per session
- Sessions persist until application closes
- Automatic reconnection on peer return

---

## Keyboard Shortcuts

**Chat Window:**
- `Enter` - Send message
- `Shift+Enter` - New line in message
- `Alt+F4` / `Cmd+W` - Close window

**Main Window:**
- `Alt+F4` / `Cmd+Q` - Quit application

---

## Troubleshooting

### "No peers found"

**Solution 1:** Click "Refresh Peers"

**Solution 2:** Use "Add Peer Manually"
- Get fingerprint from other instance's GUI
- Use `127.0.0.1` for local testing
- Use actual IP for different machines

### "Peer not reachable"

- Check firewall settings
- Verify IP address and port
- Ensure other instance is running
- Try refreshing peers list

### "Handshake failed"

- Verify fingerprint is correct
- Check network connectivity
- Ensure ports are not blocked
- Try restarting both instances

### Chat window doesn't open

- Check system log for errors
- Verify peer is in the list
- Try manual peer addition
- Restart application

### Messages not appearing

- Check "Secure connection established ✓" appears
- Look for system messages in chat
- Check system log for errors
- Verify handshake completed

---

## System Log Messages

**Green (Success):**
- `DNI-IM started`
- `Handshake completed`
- `Secure session established`
- `Chat opened with...`

**Yellow (Warning):**
- `Message queued`
- `Peer unreachable`

**Red (Error):**
- `Handshake error`
- `Packet error`
- `Command error`

**Cyan (Info):**
- `Logged in as...`
- `Found X peer(s)`
- `Establishing secure session...`

---

## Advanced Features

### Multiple Conversations

Open multiple chat windows with the same peer:
- Each has a unique Stream ID
- Messages are multiplexed over one secure session
- Useful for separating topics

### Contact Renaming

Edit `contacts.json` to change friendly names:
```json
{
  "abc123def456": {
    "name": "Alice",
    "public_key": "...",
    "first_seen": "..."
  }
}
```

### Message History

Currently in-memory only. To add persistence:
- Messages are stored per chat window
- Cleared when window closes
- Can be extended to save to disk

---

## Production Deployment

### Two Machines on Same Network:

1. **Machine A:**
   ```bash
   python main_gui.py
   ```

2. **Machine B:**
   ```bash
   python main_gui.py
   ```

3. Both should auto-discover via mDNS
4. Double-click peer to start chatting
5. No manual configuration needed!

### Firewall Configuration:

**Windows:**
```powershell
netsh advfirewall firewall add rule name="DNI-IM" dir=in action=allow protocol=UDP localport=6666
netsh advfirewall firewall add rule name="mDNS" dir=in action=allow protocol=UDP localport=5353
```

**Linux:**
```bash
sudo ufw allow 6666/udp
sudo ufw allow 5353/udp
```

---

## Tips

1. **Keep system log visible** - Shows connection status and errors
2. **Use manual peer addition** for reliable local testing
3. **Wait for handshake** - Don't send messages until "✓" appears
4. **Check fingerprints** - Verify you're connecting to the right peer
5. **Multiple windows** - Open chats with multiple peers simultaneously
6. **Message queueing** - Send messages even when peer is offline

---

## Screenshots Description

### Main Window:
- Clean, modern interface
- Two-panel layout
- Real-time peer list
- Color-coded system log

### Chat Window:
- Timestamp on each message
- Color-coded senders
- System notifications
- Multi-line input area
- Send button

### Dialogs:
- Add Peer: Simple form with fingerprint, IP, port
- Contacts: Table view with names and fingerprints

---

## Comparison: GUI vs TUI

| Feature | GUI | TUI |
|---------|-----|-----|
| Multiple chats | Separate windows | Switch with `/switch` |
| Peer discovery | Visual list | `/list` command |
| Message history | Scrollable | Last 20 messages |
| System log | Always visible | Mixed with chat |
| Ease of use | Click & type | Commands |
| Resource usage | Higher | Lower |
| Remote access | Requires X11/RDP | SSH-friendly |

**Recommendation:** Use GUI for local use, TUI for servers/remote access.
