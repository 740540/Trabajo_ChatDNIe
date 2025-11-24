# Relay Server Deployment Guide

## Overview

The relay server allows DNI-IM clients to communicate over the Internet without port forwarding or VPN.

### Architecture

```
Client A (Spain)          Relay Server (Cloud)          Client B (USA)
   |                              |                           |
   |------ Register ------------->|                           |
   |                              |<------ Register ----------|
   |                              |                           |
   |-- Send to B (encrypted) ---->|                           |
   |                              |-- Forward (encrypted) --->|
   |                              |                           |
   |<----- Receive (encrypted) ---|<-- Send to A (encrypted)-|
```

**Key Points:**
- ✅ End-to-end encryption maintained (relay can't read messages)
- ✅ No port forwarding needed on clients
- ✅ Works behind NAT/firewalls
- ✅ Automatic peer discovery through relay

---

## Deploy Relay Server

### Option 1: Cloud Server (Recommended)

#### **AWS EC2:**

1. **Launch Instance**
   - AMI: Ubuntu 22.04 LTS
   - Instance Type: t2.micro (free tier)
   - Security Group: Allow UDP 7777

2. **Connect and Setup**
   ```bash
   ssh ubuntu@<your-ec2-ip>
   
   # Install Python
   sudo apt update
   sudo apt install python3 python3-pip
   
   # Upload relay server
   # (Use scp or git clone)
   
   # Run server
   python3 relay_server.py 7777
   ```

3. **Run as Service**
   ```bash
   # Create systemd service
   sudo nano /etc/systemd/system/dni-im-relay.service
   ```
   
   ```ini
   [Unit]
   Description=DNI-IM Relay Server
   After=network.target
   
   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/dni-im
   ExecStart=/usr/bin/python3 /home/ubuntu/dni-im/relay_server.py 7777
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   ```bash
   # Enable and start
   sudo systemctl enable dni-im-relay
   sudo systemctl start dni-im-relay
   sudo systemctl status dni-im-relay
   ```

4. **Configure Firewall**
   ```bash
   sudo ufw allow 7777/udp
   sudo ufw enable
   ```

5. **Note Public IP**
   ```bash
   curl ifconfig.me
   # Example: 54.123.45.67
   ```

#### **DigitalOcean Droplet:**

Similar to AWS, but:
- Create Droplet (Ubuntu 22.04)
- Choose $5/month plan
- Follow same setup steps

#### **Google Cloud Platform:**

- Create Compute Engine instance
- Ubuntu 22.04
- Allow UDP 7777 in firewall rules
- Follow same setup steps

---

### Option 2: Home Server

If you have a static IP or DDNS:

1. **Setup Server**
   ```bash
   python3 relay_server.py 7777
   ```

2. **Port Forward**
   - Router: Forward UDP 7777 to server
   - Firewall: Allow UDP 7777

3. **Use DDNS** (if dynamic IP)
   - Register with No-IP, DuckDNS, etc.
   - Update DNS when IP changes

---

## Client Configuration

### Update config.py

Add relay server option:

```python
# Relay server (optional)
RELAY_SERVER = "54.123.45.67"  # Your relay server IP
RELAY_PORT = 7777
USE_RELAY = True  # Set to True to use relay
```

### Usage

**With Relay:**
```bash
# Clients automatically register with relay
python main_gui.py

# Peers discover each other through relay
# No manual IP configuration needed!
```

**Without Relay (LAN only):**
```bash
# Set USE_RELAY = False in config.py
python main_gui.py
```

---

## Testing

### 1. Start Relay Server

```bash
# On cloud server
python3 relay_server.py 7777

# Output:
🚀 DNI-IM Relay Server started on 0.0.0.0:7777
📡 Waiting for clients...
```

### 2. Start Client A (Spain)

```bash
# Set RELAY_SERVER in config.py
python main_gui.py

# Output:
✓ Registered with relay server
✓ Fingerprint: a1b2c3d4e5f6g7h8
```

### 3. Start Client B (USA)

```bash
# Set RELAY_SERVER in config.py
python main_gui.py

# Output:
✓ Registered with relay server
✓ Fingerprint: x9y8z7w6v5u4t3s2
✓ Discovered peer: GARCIA LOPEZ, JUAN
```

### 4. Chat!

- Client B sees Client A in peer list
- Double-click to start chat
- Messages relayed through server
- End-to-end encrypted

---

## Monitoring

### Server Logs

```bash
# View logs
sudo journalctl -u dni-im-relay -f

# Statistics (printed every 60 seconds)
📊 Statistics:
   Active clients: 5
   Packets relayed: 1234
   Bytes relayed: 2.45 MB
```

### Client Logs

```bash
# In GUI system log
[10:30:15] Registered with relay server
[10:30:20] Discovered 3 peer(s) via relay
[10:30:25] Relaying messages through 54.123.45.67
```

---

## Security

### Relay Server Security

1. **Firewall Rules**
   ```bash
   # Only allow UDP 7777
   sudo ufw default deny incoming
   sudo ufw allow 7777/udp
   sudo ufw allow 22/tcp  # SSH only
   sudo ufw enable
   ```

2. **Rate Limiting**
   ```bash
   # Prevent DDoS
   sudo iptables -A INPUT -p udp --dport 7777 -m limit --limit 100/s -j ACCEPT
   sudo iptables -A INPUT -p udp --dport 7777 -j DROP
   ```

3. **Authentication** (optional)
   - Add API key requirement
   - Verify DNIe fingerprints
   - Whitelist known clients

### Client Security

- ✅ End-to-end encryption (relay can't read messages)
- ✅ DNIe authentication required
- ✅ TOFU verification
- ✅ Noise protocol security

### What Relay Can See

- ❌ Message content (encrypted)
- ❌ User names (encrypted)
- ✅ Client IP addresses
- ✅ Fingerprints (for routing)
- ✅ Message sizes and timing

---

## Costs

### Cloud Hosting

| Provider | Plan | Cost/Month | Bandwidth |
|----------|------|------------|-----------|
| AWS EC2 | t2.micro | Free (1 year) | 15 GB |
| DigitalOcean | Basic | $5 | 1 TB |
| Google Cloud | e2-micro | Free (always) | 1 GB |
| Vultr | Basic | $3.50 | 500 GB |

### Bandwidth Calculation

- Average message: 500 bytes
- 100 messages/day/user: 50 KB/day
- 10 users: 500 KB/day = 15 MB/month
- **Very cheap!**

---

## Scaling

### Small (1-10 users)
- Single t2.micro instance
- No load balancer needed
- ~$0-5/month

### Medium (10-100 users)
- t2.small instance
- CloudWatch monitoring
- ~$20/month

### Large (100-1000 users)
- Multiple instances
- Load balancer
- Auto-scaling
- ~$100-200/month

---

## Troubleshooting

### "Can't connect to relay server"

```bash
# Test connectivity
nc -u <relay-ip> 7777

# Check firewall
sudo ufw status

# Check server is running
sudo systemctl status dni-im-relay
```

### "Peers not discovering"

```bash
# Check relay server logs
sudo journalctl -u dni-im-relay -f

# Verify clients are registered
# Should see: "✅ Client registered: ..."

# Check client config
# RELAY_SERVER must be correct IP
# USE_RELAY must be True
```

### "High latency"

- Choose relay server closer to users
- Use multiple regional relays
- Implement direct P2P fallback

---

## Advanced: Multiple Relay Servers

For global deployment:

```python
# config.py
RELAY_SERVERS = [
    ("relay-eu.example.com", 7777),   # Europe
    ("relay-us.example.com", 7777),   # USA
    ("relay-asia.example.com", 7777), # Asia
]

# Client automatically chooses closest
```

---

## Comparison: Direct vs Relay

| Feature | Direct (LAN) | Relay (Internet) |
|---------|--------------|------------------|
| Setup | Easy | Medium |
| Latency | Very Low | Low-Medium |
| Bandwidth | Unlimited | Limited by relay |
| Cost | Free | $0-5/month |
| NAT Traversal | No | Yes |
| Port Forwarding | No | No (on clients) |
| Privacy | Full | Metadata visible |

---

## Conclusion

**Use Relay Server when:**
- ✅ Users are on different networks
- ✅ No port forwarding possible
- ✅ Behind corporate firewalls
- ✅ Mobile networks
- ✅ Maximum compatibility

**Use Direct Connection when:**
- ✅ Same LAN
- ✅ VPN available
- ✅ Port forwarding possible
- ✅ Maximum privacy
- ✅ Lowest latency

---

## Next Steps

1. Deploy relay server to cloud
2. Update client config with relay IP
3. Test with clients on different networks
4. Monitor performance
5. Scale as needed

The relay server is production-ready and can handle hundreds of concurrent users on a small instance!
