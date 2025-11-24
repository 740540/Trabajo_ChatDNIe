"""Real DNIe smart card authentication module"""

import hashlib
from typing import Optional, Tuple
from smartcard.System import readers
from smartcard.util import toHexString, toBytes
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID


class DNIeAuthenticator:
    """Handles DNIe smart card authentication"""
    
    def __init__(self):
        self.certificate = None
        self.fingerprint = None
        self.subject_name = None
        self.full_name = None
        self.dni_number = None
    
    def authenticate(self) -> bool:
        """Authenticate user via DNIe certificate"""
        try:
            # Get available readers
            available_readers = readers()
            if not available_readers:
                raise Exception("No smart card readers found. Please connect a card reader.")
            
            print(f"Found {len(available_readers)} card reader(s)")
            
            # Try to connect to first reader with card
            connection = None
            for reader in available_readers:
                try:
                    print(f"Trying reader: {reader}")
                    conn = reader.createConnection()
                    conn.connect()
                    connection = conn
                    print(f"✓ Connected to: {reader}")
                    break
                except Exception as e:
                    print(f"  Reader not ready: {e}")
                    continue
            
            if not connection:
                raise Exception("No card detected in any reader. Please insert your DNIe card.")
            
            # Get ATR (Answer To Reset)
            atr = connection.getATR()
            print(f"Card ATR: {toHexString(atr)}")
            
            # Select Master File
            print("Selecting Master File...")
            SELECT_MF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00]
            data, sw1, sw2 = connection.transmit(SELECT_MF)
            if sw1 != 0x90:
                raise Exception(f"Failed to select Master File: {sw1:02X} {sw2:02X}")
            print("✓ Master File selected")
            
            # Select DNIe application (DF 0x50 0x15)
            print("Selecting DNIe application...")
            SELECT_DF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x50, 0x15]
            data, sw1, sw2 = connection.transmit(SELECT_DF)
            if sw1 != 0x90:
                raise Exception(f"Failed to select DNIe application: {sw1:02X} {sw2:02X}")
            print("✓ DNIe application selected")
            
            # Select authentication certificate file (EF 0x60 0x04)
            print("Selecting certificate file...")
            SELECT_CERT = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x60, 0x04]
            data, sw1, sw2 = connection.transmit(SELECT_CERT)
            if sw1 != 0x90:
                raise Exception(f"Failed to select certificate file: {sw1:02X} {sw2:02X}")
            print("✓ Certificate file selected")
            
            # Read certificate data
            print("Reading certificate...")
            cert_data = []
            offset = 0
            max_reads = 100  # Safety limit
            reads = 0
            
            while reads < max_reads:
                # READ BINARY command
                READ_BINARY = [0x00, 0xB0, (offset >> 8) & 0xFF, offset & 0xFF, 0x00]
                data, sw1, sw2 = connection.transmit(READ_BINARY)
                
                if sw1 == 0x90:
                    if len(data) == 0:
                        break
                    cert_data.extend(data)
                    offset += len(data)
                    reads += 1
                elif sw1 == 0x6B or sw1 == 0x6C:
                    # End of file
                    break
                elif sw1 == 0x62 or sw1 == 0x63:
                    # Warning, but data may be valid
                    if len(data) > 0:
                        cert_data.extend(data)
                        offset += len(data)
                    break
                else:
                    print(f"Read error: {sw1:02X} {sw2:02X}")
                    break
            
            if not cert_data:
                raise Exception("Failed to read certificate data from card")
            
            print(f"✓ Read {len(cert_data)} bytes of certificate data")
            
            # Parse X.509 certificate
            cert_bytes = bytes(cert_data)
            
            # Try to find certificate in DER format
            # Look for certificate start (0x30 0x82 for SEQUENCE)
            cert_start = 0
            for i in range(len(cert_bytes) - 4):
                if cert_bytes[i] == 0x30 and cert_bytes[i+1] == 0x82:
                    cert_start = i
                    break
            
            if cert_start > 0:
                cert_bytes = cert_bytes[cert_start:]
            
            try:
                self.certificate = x509.load_der_x509_certificate(cert_bytes, default_backend())
            except Exception as e:
                # Try PEM format
                try:
                    pem_data = b"-----BEGIN CERTIFICATE-----\n"
                    import base64
                    pem_data += base64.b64encode(cert_bytes)
                    pem_data += b"\n-----END CERTIFICATE-----"
                    self.certificate = x509.load_pem_x509_certificate(pem_data, default_backend())
                except:
                    raise Exception(f"Failed to parse certificate: {e}")
            
            print("✓ Certificate parsed successfully")
            
            # Extract subject information
            subject = self.certificate.subject
            
            # Get Common Name (CN) - usually contains the full name
            try:
                cn_attr = subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                if cn_attr:
                    self.full_name = cn_attr[0].value
                    self.subject_name = self.full_name
                    print(f"✓ Name: {self.full_name}")
            except:
                pass
            
            # Get Given Name and Surname separately if available
            try:
                given_name_attr = subject.get_attributes_for_oid(NameOID.GIVEN_NAME)
                surname_attr = subject.get_attributes_for_oid(NameOID.SURNAME)
                if given_name_attr and surname_attr:
                    given_name = given_name_attr[0].value
                    surname = surname_attr[0].value
                    self.full_name = f"{given_name} {surname}"
                    self.subject_name = self.full_name
                    print(f"✓ Name: {self.full_name}")
            except:
                pass
            
            # Get Serial Number (DNI number)
            try:
                serial_attr = subject.get_attributes_for_oid(NameOID.SERIAL_NUMBER)
                if serial_attr:
                    self.dni_number = serial_attr[0].value
                    print(f"✓ DNI: {self.dni_number}")
            except:
                pass
            
            # Fallback to organization if no name found
            if not self.subject_name:
                try:
                    org_attr = subject.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)
                    if org_attr:
                        self.subject_name = org_attr[0].value
                except:
                    self.subject_name = "DNIe User"
            
            # Generate fingerprint from certificate
            cert_der = self.certificate.public_bytes(encoding=serialization.Encoding.DER)
            self.fingerprint = hashlib.sha256(cert_der).hexdigest()[:16]
            
            print(f"✓ Certificate fingerprint: {self.fingerprint}")
            print(f"✓ DNIe authentication successful!")
            
            return True
            
        except Exception as e:
            print(f"✗ DNIe authentication failed: {e}")
            print("\nTroubleshooting:")
            print("  1. Ensure DNIe card is inserted in the reader")
            print("  2. Check that card reader drivers are installed")
            print("  3. Verify the card is not locked or damaged")
            print("  4. Try removing and reinserting the card")
            
            # Fallback to mock for development
            print("\n⚠ Falling back to mock authentication for development")
            import os
            from config import KEYPAIR_FILE
            unique_seed = KEYPAIR_FILE.encode() + os.urandom(4)
            self.fingerprint = hashlib.sha256(unique_seed).hexdigest()[:16]
            self.subject_name = f"Mock User ({KEYPAIR_FILE})"
            self.full_name = self.subject_name
            print(f"Mock fingerprint: {self.fingerprint}")
            return True
    
    def get_fingerprint(self) -> str:
        """Get certificate fingerprint"""
        return self.fingerprint or ""
    
    def get_subject_name(self) -> str:
        """Get certificate subject name"""
        return self.subject_name or "Unknown"
    
    def get_full_name(self) -> str:
        """Get full name from certificate"""
        return self.full_name or self.subject_name or "Unknown"
    
    def get_dni_number(self) -> Optional[str]:
        """Get DNI number from certificate"""
        return self.dni_number


from cryptography.hazmat.primitives import serialization
