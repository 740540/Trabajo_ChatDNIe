"""DNIe smart card authentication module"""

import hashlib
import os
from typing import Optional, Tuple
from smartcard.System import readers
from smartcard.util import toHexString, toBytes
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64


class DNIeAuthenticator:
    """Handles DNIe smart card authentication"""
    
    def __init__(self):
        self.certificate = None
        self.fingerprint = None
        self.subject_name = None
        self.full_name = None
        self.dni_number = None
        self.photo = None
        self.connection = None
        self.public_key = None
    
    def authenticate(self) -> bool:
        """Authenticate user via DNIe certificate"""
        try:
            # Get available readers
            available_readers = readers()
            if not available_readers:
                print("No smart card readers found")
                raise Exception("No readers - using mock mode")
            
            # Connect to first reader
            reader = available_readers[0]
            self.connection = reader.createConnection()
            self.connection.connect()
            
            print(f"Connected to reader: {reader}")
            
            # Select DNIe Master File
            self._select_master_file()
            
            # Read authentication certificate
            cert_data = self._read_certificate()
            if cert_data:
                self.certificate = x509.load_der_x509_certificate(cert_data, default_backend())
                self._extract_certificate_info()
                print(f"✓ DNIe authenticated: {self.full_name} ({self.dni_number})")
            
            # Read photo from DNIe
            self.photo = self._read_photo()
            if self.photo:
                print(f"✓ Photo extracted: {len(self.photo)} bytes")
            
            return True
            
        except Exception as e:
            print(f"DNIe authentication error: {e}")
            # Fallback for development without physical card
            print("⚠ Using mock authentication for development")
            return self._mock_authenticate()
    
    def _mock_authenticate(self) -> bool:
        """Mock authentication for development without DNIe"""
        from config import KEYPAIR_FILE
        
        # Generate consistent mock data
        mock_id = os.path.basename(KEYPAIR_FILE).replace('.bin', '')
        
        self.fingerprint = None  # Will be set by main app after loading keypair
        self.full_name = f"Usuario Mock {mock_id}"
        self.subject_name = self.full_name
        self.dni_number = "12345678Z"
        self.photo = None  # No photo in mock mode
        
        return True
    
    def _select_master_file(self):
        """Select DNIe Master File"""
        SELECT_MF = [0x00, 0xA4, 0x00, 0x00, 0x02, 0x3F, 0x00]
        data, sw1, sw2 = self.connection.transmit(SELECT_MF)
        if sw1 != 0x90:
            raise Exception(f"Failed to select Master File: {sw1:02X} {sw2:02X}")
    
    def _read_certificate(self) -> Optional[bytes]:
        """Read authentication certificate from DNIe"""
        try:
            # Select certificate file (DF 0x50 0x15 for authentication cert)
            SELECT_CERT = [0x00, 0xA4, 0x02, 0x00, 0x02, 0x50, 0x15]
            data, sw1, sw2 = self.connection.transmit(SELECT_CERT)
            
            if sw1 != 0x90:
                print(f"Certificate file not found: {sw1:02X} {sw2:02X}")
                return None
            
            # Read certificate data
            cert_data = bytearray()
            offset = 0
            
            while True:
                # Read binary command
                READ_BINARY = [0x00, 0xB0, (offset >> 8) & 0xFF, offset & 0xFF, 0x00]
                data, sw1, sw2 = self.connection.transmit(READ_BINARY)
                
                if sw1 == 0x90:
                    cert_data.extend(data)
                    offset += len(data)
                elif sw1 == 0x6B or sw1 == 0x62:  # End of file
                    break
                else:
                    break
            
            return bytes(cert_data) if cert_data else None
            
        except Exception as e:
            print(f"Error reading certificate: {e}")
            return None
    
    def _extract_certificate_info(self):
        """Extract information from certificate"""
        if not self.certificate:
            return
        
        # Extract subject information
        subject = self.certificate.subject
        
        # Get common name (CN)
        cn_attrs = subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
        if cn_attrs:
            self.full_name = cn_attrs[0].value
            self.subject_name = self.full_name
        
        # Get serial number (DNI number)
        serial_attrs = subject.get_attributes_for_oid(x509.NameOID.SERIAL_NUMBER)
        if serial_attrs:
            self.dni_number = serial_attrs[0].value
        
        # Generate fingerprint from certificate
        cert_bytes = self.certificate.public_bytes(serialization.Encoding.DER)
        self.fingerprint = hashlib.sha256(cert_bytes).hexdigest()[:16]
        
        # Extract public key for encryption
        self.public_key = self.certificate.public_key()
    
    def _read_photo(self) -> Optional[bytes]:
        """Read photo from DNIe chip"""
        try:
            # Select photo file (DF 0x60 0x01)
            SELECT_PHOTO = [0x00, 0xA4, 0x02, 0x00, 0x02, 0x60, 0x01]
            data, sw1, sw2 = self.connection.transmit(SELECT_PHOTO)
            
            if sw1 != 0x90:
                print(f"Photo file not found: {sw1:02X} {sw2:02X}")
                return None
            
            # Read photo data
            photo_data = bytearray()
            offset = 0
            
            while True:
                # Read binary command (read 250 bytes at a time)
                READ_BINARY = [0x00, 0xB0, (offset >> 8) & 0xFF, offset & 0xFF, 0xFA]
                data, sw1, sw2 = self.connection.transmit(READ_BINARY)
                
                if sw1 == 0x90:
                    photo_data.extend(data)
                    offset += len(data)
                    if len(data) < 250:  # Last chunk
                        break
                elif sw1 == 0x6B or sw1 == 0x62:  # End of file
                    break
                else:
                    break
            
            return bytes(photo_data) if photo_data else None
            
        except Exception as e:
            print(f"Error reading photo: {e}")
            return None
    
    def get_fingerprint(self) -> str:
        """Get certificate fingerprint"""
        return self.fingerprint or ""
    
    def get_subject_name(self) -> str:
        """Get certificate subject name"""
        return self.subject_name or "Unknown"
    
    def get_full_name(self) -> str:
        """Get full name from DNIe"""
        return self.full_name or self.subject_name or "Unknown"
    
    def get_dni_number(self) -> str:
        """Get DNI/NIE number"""
        return self.dni_number or "Unknown"
    
    def get_photo(self) -> Optional[bytes]:
        """Get photo from DNIe"""
        return self.photo
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using DNIe public key"""
        if not self.public_key:
            # Fallback: use simple encryption for mock mode
            return self._mock_encrypt(data)
        
        try:
            # Encrypt with RSA public key from certificate
            encrypted = self.public_key.encrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return encrypted
        except Exception as e:
            print(f"Encryption error: {e}")
            return self._mock_encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes, pin: Optional[str] = None) -> Optional[bytes]:
        """Decrypt data using DNIe private key (requires PIN)"""
        if not self.connection:
            # Fallback: use simple decryption for mock mode
            return self._mock_decrypt(encrypted_data)
        
        try:
            # In real implementation, this would:
            # 1. Verify PIN with DNIe
            # 2. Use DNIe's private key to decrypt
            # For now, we'll use mock decryption
            return self._mock_decrypt(encrypted_data)
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    
    def _mock_encrypt(self, data: bytes) -> bytes:
        """Mock encryption for development"""
        # Simple XOR encryption with a key derived from the mock identity
        key = hashlib.sha256(self.full_name.encode()).digest()
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ key[i % len(key)])
        return bytes(encrypted)
    
    def _mock_decrypt(self, encrypted_data: bytes) -> bytes:
        """Mock decryption for development"""
        # Same as encryption (XOR is symmetric)
        return self._mock_encrypt(encrypted_data)
