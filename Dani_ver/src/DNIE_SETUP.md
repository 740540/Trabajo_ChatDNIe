# DNIe Real Authentication Setup

## Prerequisites

### 1. Hardware
- Spanish DNIe card (DNI electrónico 3.0 or later)
- PC/SC compatible smart card reader (USB)
- Card reader drivers installed

### 2. Software Dependencies

```bash
# Windows
# Install PC/SC service (usually pre-installed)
# Download drivers from your card reader manufacturer

# Install Python dependencies
pip install pyscard cryptography asn1crypto

# Test card reader detection
python -c "from smartcard.System import readers; print(readers())"
```

## Implementation Steps

### Step 1: Update `dnie_auth.py`

Replace the mock fallback with proper DNIe certificate extraction:

```python
def authenticate(self) -> bool:
    """Authenticate user via DNIe certificate"""
    try:
        # Get available readers
        available_readers = readers()
        if not available_readers:
            raise Exception("No smart card readers found")
        
        # Connect to first reader with card
        reader = None
        for r in available_readers:
            try:
                connection = r.createConnection()
                connection.connect()
                reader = r
                break
            except:
                continue
        
        if not reader:
            raise Exception("No card detected in any reader")
        
        connection = reader.createConnection()
        connection.connect()
        
        # Select DNIe Master File
        SELECT_MF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00]
        data, sw1, sw2 = connection.transmit(SELECT_MF)
        if sw1 != 0x90:
            raise Exception(f"Failed to select Master File: {sw1:02X}{sw2:02X}")
        
        # Select DNIe application (DF 0x50 0x15)
        SELECT_DF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x50, 0x15]
        data, sw1, sw2 = connection.transmit(SELECT_DF)
        if sw1 != 0x90:
            raise Exception(f"Failed to select DNIe DF: {sw1:02X}{sw2:02X}")
        
        # Select authentication certificate file (0x60 0x04)
        SELECT_CERT = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x60, 0x04]
        data, sw1, sw2 = connection.transmit(SELECT_CERT)
        if sw1 != 0x90:
            raise Exception(f"Failed to select certificate: {sw1:02X}{sw2:02X}")
        
        # Read certificate (may need multiple READ BINARY commands)
        cert_data = []
        offset = 0
        while True:
            READ_BINARY = [0x00, 0xB0, (offset >> 8) & 0xFF, offset & 0xFF, 0x00]
            data, sw1, sw2 = connection.transmit(READ_BINARY)
            if sw1 == 0x90:
                cert_data.extend(data)
                offset += len(data)
            elif sw1 == 0x6B or sw1 == 0x6C:
                break  # End of file
            else:
                break
        
        if not cert_data:
            raise Exception("Failed to read certificate data")
        
        # Parse X.509 certificate
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        
        cert_bytes = bytes(cert_data)
        self.certificate = x509.load_der_x509_certificate(cert_bytes, default_backend())
        
        # Extract subject information
        subject = self.certificate.subject
        self.subject_name = subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        
        # Generate fingerprint from certificate
        import hashlib
        self.fingerprint = hashlib.sha256(cert_bytes).hexdigest()[:16]
        
        print(f"✓ DNIe authenticated: {self.subject_name}")
        print(f"✓ Certificate fingerprint: {self.fingerprint}")
        
        return True
        
    except Exception as e:
        print(f"✗ DNIe authentication failed: {e}")
        return False
```

### Step 2: Remove Mock Fallback

In `dnie_auth.py`, remove these lines:

```python
# DELETE THIS SECTION:
except Exception as e:
    print(f"DNIe authentication error: {e}")
    # Fallback for development without physical card
    print("Using mock authentication for development")
    self.fingerprint = hashlib.sha256(b"mock_dnie").hexdigest()[:16]
    self.subject_name = "Mock DNIe User"
    return True
```

Replace with:

```python
except Exception as e:
    print(f"✗ DNIe authentication failed: {e}")
    print("Please ensure:")
    print("  1. DNIe card is inserted in reader")
    print("  2. Card reader is connected and drivers installed")
    print("  3. Card is not locked or damaged")
    return False
```

### Step 3: Test Card Reader

```bash
# Test if card reader is detected
python -c "from smartcard.System import readers; print('Readers:', readers())"

# Test card connection
python -c "
from smartcard.System import readers
r = readers()[0]
conn = r.createConnection()
conn.connect()
print('Card connected successfully')
"
```

### Step 4: Run Application

```bash
python main.py
```

The application will now:
1. Prompt you to insert DNIe card
2. Read the certificate from the card
3. Extract your real identity and fingerprint
4. Use this for authentication in the network

## Troubleshooting

### "No smart card readers found"
- Check USB connection
- Install card reader drivers
- Restart PC/SC service: `net stop SCardSvr && net start SCardSvr` (Windows)

### "Failed to select DNIe DF"
- Card may be DNIe 2.0 (older version) - different file structure
- Try different APDU commands for older cards

### "Failed to read certificate"
- Certificate may be in different location
- Some DNIe cards require PIN verification first
- Check card is not locked

## Security Notes

- Real DNIe authentication provides cryptographic proof of identity
- Certificate is signed by Spanish government CA
- Private key never leaves the smart card
- Can implement challenge-response authentication for stronger security

## Optional: PIN Verification

For enhanced security, verify PIN before reading certificate:

```python
# Verify PIN (usually 4-6 digits)
VERIFY_PIN = [0x00, 0x20, 0x00, 0x00, 0x04] + [0x31, 0x32, 0x33, 0x34]  # PIN: 1234
data, sw1, sw2 = connection.transmit(VERIFY_PIN)
if sw1 != 0x90:
    raise Exception("PIN verification failed")
```

## References

- DNIe Technical Specification: https://www.dnielectronico.es/
- PC/SC Workgroup: https://pcscworkgroup.com/
- ISO 7816-4: Smart card APDU commands
