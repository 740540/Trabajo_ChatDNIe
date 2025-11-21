# dnie.py - Gestión multiplataforma del DNIe con funciones de firma
import base64
import platform
import os
import hashlib
import json
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

# Detectar sistema operativo y cargar la librería adecuada
system = platform.system()
if system == "Windows":
    # Windows usa python-pkcs11
    try:
        import pkcs11
        from pkcs11 import Mechanism, ObjectClass
        PKCS11_LIB = "pkcs11"
    except ImportError:
        raise ImportError("Para Windows, instala: pip install python-pkcs11")
elif system == "Darwin":  # macOS
    # macOS usa PyKCS11
    try:
        import PyKCS11 as pkcs11
        PKCS11_LIB = "pykcs11"
    except ImportError:
        raise ImportError("Para macOS, instala: pip install PyKCS11")
else:  # Linux
    try:
        import pkcs11
        from pkcs11 import Mechanism, ObjectClass
        PKCS11_LIB = "pkcs11"
    except ImportError:
        raise ImportError("Para Linux, instala: pip install python-pkcs11")

class DNIeManager:
    def __init__(self):
        # Configurar ruta de librería según el sistema operativo
        if system == "Windows":
            self.lib_path = r"C:\Program Files\OpenSC Project\OpenSC\pkcs11\opensc-pkcs11.dll"
        elif system == "Darwin":  # macOS
            self.lib_path = "/usr/lib/opensc-pkcs11.so"
        else:  # Linux
            self.lib_path = "/usr/lib/opensc-pkcs11.so"
        
        self.session = None
        self._lib = None
        self.pkcs11_lib = PKCS11_LIB
    
    def authenticate(self, pin: str) -> bytes:
        """Authenticate with DNIe and return derived key"""
        try:
            print(f"🔍 Buscando DNIe con {self.pkcs11_lib}...")
            
            if self.pkcs11_lib == "pkcs11":
                # Windows/Linux con python-pkcs11
                self._lib = pkcs11.lib(self.lib_path)
                slots = self._lib.get_slots(token_present=True)
                
                if not slots:
                    raise Exception(f"❌ No se detectó ningún DNIe. Por favor, inserte su DNIe en el lector.")
                
                token = slots[0].get_token()
                print("✅ DNIe detectado, iniciando autenticación...")
                
                self.session = token.open(user_pin=pin)
                
                # Buscar clave privada para firmar
                priv_key = self._find_private_key()
                
                # Create and sign challenge
                challenge = os.urandom(32)
                signature = priv_key.sign(challenge, mechanism=Mechanism.SHA256_RSA_PKCS)
                
            else:  # macOS con PyKCS11
                # Inicializar PyKCS11
                self._lib = pkcs11.PyKCS11Lib()
                self._lib.load(self.lib_path)
                
                # Obtener slots
                slots = self._lib.getSlotList(tokenPresent=True)
                
                if not slots:
                    raise Exception(f"❌ No se detectó ningún DNIe. Por favor, inserte su DNIe en el lector.")
                
                print("✅ DNIe detectado, iniciando autenticación...")
                
                # Abrir sesión
                self.session = self._lib.openSession(slots[0])
                self.session.login(pin)
                
                # Buscar clave privada para firmar
                priv_key = self._find_private_key_pykcs11()
                
                # Create and sign challenge
                challenge = os.urandom(32)
                mechanism = pkcs11.Mechanism(pkcs11.CKM_SHA256_RSA_PKCS, None)
                signature = self.session.sign(priv_key, challenge, mechanism)
            
            print("✅ Autenticación completada, generando clave de cifrado...")
            
        except Exception as e:
            error_msg = str(e)
            if "CKR_PIN_INCORRECT" in error_msg:
                raise Exception("❌ PIN incorrecto. Por favor, verifique su PIN del DNIe.")
            elif "CKR_PIN_LOCKED" in error_msg:
                raise Exception("❌ DNIe bloqueado. Ha introducido el PIN incorrecto demasiadas veces.")
            elif "CKR_TOKEN_NOT_RECOGNIZED" in error_msg:
                raise Exception("❌ Token no reconocido. Asegúrese de que el DNIe esté correctamente insertado.")
            else:
                raise Exception(f"❌ Error de autenticación DNIe: {error_msg}")
    
    def _find_private_key(self):
        """Encontrar clave privada para python-pkcs11 (Windows/Linux)"""
        keys = self.session.get_objects({
            pkcs11.Attribute.CLASS: ObjectClass.PRIVATE_KEY,
            pkcs11.Attribute.SIGN: True
        })
        
        # Intentar encontrar clave específica
        for key in keys:
            try:
                label = key[pkcs11.Attribute.LABEL] if hasattr(key, '__getitem__') else None
                if label and any(auth_word in label.lower() for auth_word in ['autenticacion', 'auth', 'firma']):
                    return key
            except:
                continue
        
        # Si no encontramos clave específica, usar la primera
        keys = list(self.session.get_objects({
            pkcs11.Attribute.CLASS: ObjectClass.PRIVATE_KEY,
            pkcs11.Attribute.SIGN: True
        }))
        if keys:
            return keys[0]
        
        raise Exception("No se encontró ninguna clave privada de firma en el DNIe")
    
    def _find_private_key_pykcs11(self):
        """Encontrar clave privada para PyKCS11 (macOS)"""
        template = [
            (pkcs11.CKA_CLASS, pkcs11.CKO_PRIVATE_KEY),
            (pkcs11.CKA_SIGN, True)
        ]
        
        priv_keys = self.session.findObjects(template)
        if not priv_keys:
            raise Exception("No se encontró ninguna clave privada de firma en el DNIe")
        
        return priv_keys[0]
    
    def get_certificate(self) -> bytes:
        """Extraer certificado del DNIe"""
        if not self.session:
            raise Exception("No hay sesión activa con el DNIe")
        
        if self.pkcs11_lib == "pkcs11":
            # Windows/Linux
            certs = self.session.get_objects({pkcs11.Attribute.CLASS: ObjectClass.CERTIFICATE})
            cert = next(certs, None)
            return bytes(cert[pkcs11.Attribute.VALUE]) if cert else None
        else:
            # macOS
            template = [
                (pkcs11.CKA_CLASS, pkcs11.CKO_CERTIFICATE)
            ]
            certs = self.session.findObjects(template)
            if certs:
                cert = certs[0]
                value = self.session.getAttributeValue(cert, [pkcs11.CKA_VALUE])[0]
                return bytes(value)
            return None
    
    def sign_data(self, data: bytes) -> bytes:
        """Firmar datos con la clave privada del DNIe"""
        if not self.session:
            raise Exception("No hay sesión activa con el DNIe")
        
        if self.pkcs11_lib == "pkcs11":
            # Windows/Linux
            priv_key = self._find_private_key()
            return bytes(priv_key.sign(data, mechanism=Mechanism.SHA256_RSA_PKCS))
        else:
            # macOS
            priv_key = self._find_private_key_pykcs11()
            mechanism = pkcs11.Mechanism(pkcs11.CKM_SHA256_RSA_PKCS, None)
            signature = self.session.sign(priv_key, data, mechanism)
            return bytes(signature)
    
    def sign_file(self, file_path: str, pin: str) -> dict:
        """Firmar un archivo y retornar paquete de firma"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        if not self.session:
            # En caso de que se use la función stand-alone
            self.authenticate(pin)
        
        # Calcular hash del archivo
        file_hash = self._calculate_file_hash(file_path)
        
        # Leer contenido del archivo
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Firmar los datos
        signature = self.sign_data(file_data)
        
        # Obtener certificado
        certificate = self.get_certificate()
        
        if not certificate:
            raise Exception("No se pudo obtener el certificado del DNIe")
        
        # Crear paquete de firma
        signature_package = {
            'file_path': str(Path(file_path).absolute()),
            'file_name': Path(file_path).name,
            'file_hash': file_hash,
            'hash_algorithm': 'sha256',
            'signature': base64.b64encode(signature).decode('utf-8'),
            'certificate': base64.b64encode(certificate).decode('utf-8'),
            'timestamp': self._get_timestamp()
        }
        
        return signature_package
    
    def verify_signature(self, file_path: str, signature_path: str) -> bool:
        """Verificar firma de un archivo"""
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
        if not Path(signature_path).exists():
            raise FileNotFoundError(f"Archivo de firma no encontrado: {signature_path}")
        
        try:
            # Cargar paquete de firma
            with open(signature_path, 'r') as f:
                signature_package = json.load(f)
            
            # Verificar integridad del archivo
            current_hash = self._calculate_file_hash(file_path)
            if current_hash != signature_package['file_hash']:
                print("❌ El archivo ha sido modificado desde la firma!")
                return False
            
            # Decodificar firma y certificado
            signature = base64.b64decode(signature_package['signature'])
            certificate_data = base64.b64decode(signature_package['certificate'])
            
            # Cargar certificado
            cert = x509.load_der_x509_certificate(certificate_data)
            public_key = cert.public_key()
            
            # Leer archivo para verificación
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Verificar firma
            public_key.verify(
                signature,
                file_data,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            return True
            
        except Exception as e:
            print(f"❌ Error en verificación: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: str, algorithm: str = 'sha256') -> str:
        """Calcular hash de un archivo"""
        hash_func = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    
    def _get_timestamp(self):
        """Obtener timestamp actual"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def close(self):
        """Close DNIe session"""
        if self.session:
            if self.pkcs11_lib == "pykcs11":
                # macOS - cerrar sesión PyKCS11
                try:
                    self.session.logout()
                    self.session.closeSession()
                except:
                    pass
            else:
                # Windows/Linux - cerrar sesión pkcs11
                self.session.close()
            
            self.session = None
            self._lib = None

# Función de utilidad para verificar el estado del DNIe
def verificar_estado_dnie():
    """Verifica el estado del DNIe sin autenticar"""
    try:
        dnie = DNIeManager()
        system = platform.system()
        
        if system == "Windows" or system == "Linux":
            # Windows/Linux con python-pkcs11
            dnie._lib = pkcs11.lib(dnie.lib_path)
            slots = dnie._lib.get_slots(token_present=True)
        else:
            # macOS con PyKCS11
            dnie._lib = pkcs11.PyKCS11Lib()
            dnie._lib.load(dnie.lib_path)
            slots = dnie._lib.getSlotList(tokenPresent=True)
        
        if slots:
            print("✅ DNIe detectado y listo para usar")
            return True
        else:
            print("❌ No se detectó ningún DNIe")
            return False
            
    except Exception as e:
        print(f"❌ Error al verificar DNIe: {e}")
        return False