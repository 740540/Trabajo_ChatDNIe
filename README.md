# 💬 Proyecto Ciberseguridad 2 – DNIe Instant Messenger

Un sistema de mensajería instantánea seguro peer-to-peer que utiliza el **DNI electrónico (DNIe)** para autenticación y el protocolo **Noise IK** para cifrado end-to-end.  
El sistema permite comunicación cifrada en redes locales mediante mDNS/Zeroconf, con historial de chat cifrado y cola de mensajes offline persistente.

---

## 🚀 Características

- 🔐 Autenticación mediante **DNIe físico** (con lector de tarjetas)
- 🔒 Cifrado end-to-end con **Noise IK** (X25519 + ChaCha20-Poly1305)
- 🌐 Descubrimiento automático de peers en red local con **mDNS/Zeroconf**
- 💾 Historial de chat **cifrado localmente** con Fernet (derivado del certificado DNIe)
- 📬 **Cola de mensajes offline** - los mensajes se guardan y envían cuando el destinatario se conecta
- 🖥️ Interfaz gráfica terminal-styled con **Tkinter**
- 🎨 Código de colores para mensajes (usuario/peer/encolados/sistema)
- ⚙️ Compatibilidad multiplataforma (Windows, macOS, Linux)
- 🔄 Reconexión automática y gestión de sesiones
- 👋 Notificaciones de conexión/desconexión en tiempo real

---

## 📦 Instalación

### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/740540/Trabajo_ChatDNIe
cd Trabajo_ChatDNIe
```

### 2️⃣ Instalar Dependencias

**En Windows/Linux:**

```bash
pip install cryptography python-pkcs11 zeroconf
```

**En macOS:**

```bash
pip install cryptography PyKCS11 zeroconf
```

### 3️⃣ Instalar OpenSC

El DNIe requiere los controladores de OpenSC:

- **Windows**: https://github.com/OpenSC/OpenSC/releases
- **macOS (Homebrew)**: `brew install opensc`
- **Linux (Debian/Ubuntu)**: `sudo apt install opensc`

---

## 🧰 Uso

### 🔹 Ejecución con Interfaz Gráfica (Programa Principal)

```bash
python main_gui.py
```

1. Inserta tu DNIe en el lector
2. Introduce tu nombre de usuario
3. Introduce el PIN del DNIe cuando se solicite
4. La aplicación buscará automáticamente peers en la red local
5. Haz clic en un peer para iniciar una conversación

### 🔹 Ejecución con Interfaz de Terminal (TUI)

```bash
python main.py
```

Proporciona una interfaz de terminal para sistemas sin entorno gráfico.

### 📡 Controles de la Interfaz

- **Click en peer**: Seleccionar conversación
- **Enter**: Enviar mensaje
- **Ctrl+H**: Iniciar handshake manual con peer seleccionado
- **Ctrl+S**: Abrir ventana de mensajes del sistema
- **Ctrl+Q**: Salir de la aplicación

---

## 🔑 Estructura del Proyecto

```
dnie_messenger/
│
├── 📁 src/                          # Directorio del código fuente
│   │
│   ├── main_gui.py                  # Punto de entrada con GUI
│   ├── main.py                      # Punto de entrada con TUI
│   ├── messenger.py                 # Coordinador principal de la aplicación
│   │
│   ├── 📁 ui/                       # Interfaces de usuario
│   │   ├── gui.py                   # Interfaz gráfica (Tkinter)
│   │   └── tui.py                   # Interfaz de terminal
│   │
│   ├── 📁 crypto/                   # Criptografía
│   │   ├── noise_ik.py              # Implementación Noise IK
│   │   └── protocol.py              # Protocolo de frames
│   │
│   ├── 📁 network/                  # Red y comunicaciones
│   │   ├── transport.py             # Transporte UDP multiplexado
│   │   └── discovery.py             # Descubrimiento mDNS/Zeroconf
│   │
│   ├── 📁 identity/                 # Gestión de identidad
│   │   ├── im_identity.py           # Identidad del messenger
│   │   └── dnie.py                  # Autenticación DNIe (PKCS#11)
│   │
│   └── 📁 session/                  # Gestión de sesiones
│       ├── session.py               # Modelos de Session y Peer
│       ├── chat_history.py          # Historial cifrado
│       ├── message_queue.py         # Cola de mensajes offline
│       └── contact_book.py          # Libreta de contactos
│
├── 📁 .ChatHistory/                 # Historial cifrado (generado)
├── 📁 .MessageQueue/                # Mensajes pendientes (generado)
└── README.md
```

---

## 🔐 Arquitectura de Seguridad

### Autenticación
- **DNIe**: Autenticación mediante certificado digital del DNI electrónico
- **Peer ID**: Identificador único derivado del hash SHA-256 del certificado

### Cifrado de Comunicaciones
- **Noise IK**: Protocolo de handshake con forward secrecy
- **X25519**: Intercambio de claves Diffie-Hellman
- **ChaCha20-Poly1305**: Cifrado simétrico AEAD para mensajes
- **BLAKE2s**: Función hash para derivación de claves (HKDF)

### Almacenamiento Local
- **Fernet (AES-128-CBC + HMAC-SHA256)**: Cifrado de historial y cola
- **PBKDF2**: Derivación de clave desde certificado DNIe (100,000 iteraciones)
- Sales diferentes para historial y cola de mensajes

### Transporte
- **UDP**: Puerto 443 (configurable)
- **Multiplexación**: Connection IDs de 8 bytes
- **Frames**: HANDSHAKE, DATA, GOODBYE

---

## 💡 Características Avanzadas

### Cola de Mensajes Offline
Los mensajes enviados a peers desconectados se:
- ✅ Cifran y almacenan localmente
- ✅ Envían automáticamente al reconectar
- ✅ Muestran con indicador visual (color azul)
- ✅ Preservan el timestamp original

### Historial de Chat
- 📝 Cifrado con clave derivada del DNIe
- 📁 Almacenado por peer (archivos `.enc` separados)
- 🔍 Carga automática al seleccionar conversación
- 🎨 Código de colores: cyan (tú), orange (peer), blue (encolado)

### Descubrimiento de Peers
- 🔍 mDNS/Zeroconf automático en red local
- 🔑 Intercambio de claves públicas Noise
- ⚡ Handshake bidireccional (evita duplicados)
- 🔄 Detección de reconexión

---

## 🛠️ Protocolo de Mensajes

### Frame Format
```
┌─────────────────┬────────────┬────────────┬─────────────┐
│ Connection ID   │ Stream ID  │ Frame Type │ Payload     │
│ (8 bytes)       │ (2 bytes)  │ (1 byte)   │ (variable)  │
└─────────────────┴────────────┴────────────┴─────────────┘
```

### Frame Types
- `0x01` - HANDSHAKE: Noise IK handshake message
- `0x02` - DATA: Mensaje cifrado con ChaCha20-Poly1305
- `0xFF` - GOODBYE: Desconexión graceful

---

## ⚠️ Limitaciones y Consideraciones

### Seguridad de Memoria
⚠️ Python no proporciona memoria segura:
- Las claves de sesión permanecen en RAM hasta garbage collection
- Sin memory locking (no mlockall/VirtualLock)
- Sin borrado seguro de memoria

**Recomendación**: Para comunicaciones altamente sensibles, considerar implementación en C/Rust.

### Red
- Solo funciona en red local (mismo segmento de red)
- Requiere puerto UDP 443 disponible
- No atraviesa NAT sin configuración adicional

### Compatibilidad
- Solo compatible entre clientes con la misma versión del protocolo
- El formato de mensajes debe coincidir entre peers

---

## 🐛 Solución de Problemas

### DNIe no detectado
```bash
# Verificar lectores conectados (Linux)
opensc-tool --list-readers

# Verificar certificados en la tarjeta
pkcs15-tool --list-certificates
```

### Peer no aparece en la lista
- Verificar que ambos dispositivos estén en la misma red
- Comprobar firewall (permitir UDP 443)
- Reiniciar la aplicación en ambos peers

### Error de handshake
- Verificar que ambos peers tienen claves públicas válidas
- Comprobar que las claves estáticas coinciden con las anunciadas
- Revisar logs de depuración con `[DEBUG]` tags

### Mensajes no se envían
- Verificar que el handshake se completó (`🔐 Handshake completado`)
- Comprobar que el peer está marcado como "online"
- Los mensajes offline se guardan automáticamente y se envían al reconectar

---

## 📊 Estadísticas

Al cerrar la aplicación, se muestran estadísticas de la sesión:
- Total de peers contactados
- Número de mensajes enviados/recibidos
- Mensajes pendientes en cola
- Ubicación del historial cifrado

---

## 🔄 Flujo de Conexión

1. **Inicio**: Autenticación con DNIe
2. **Anuncio**: Publica servicio mDNS con clave pública
3. **Descubrimiento**: Detecta otros peers en la red
4. **Handshake**: Establece canal cifrado (Noise IK)
5. **Mensajería**: Intercambio de mensajes cifrados
6. **Desconexión**: Envía GOODBYE, limpia recursos

---

## 📝 Notas de Desarrollo

### Testing
Para probar con múltiples clientes:
```bash
# Terminal 1
python main_gui.py

# Terminal 2 (en otra máquina o VM)
python main_gui.py
```

### Debug Logs
Los logs de depuración muestran:
- `[DEBUG]` - Información de desarrollo
- `[ERROR]` - Errores que requieren atención
- `[WARNING]` - Situaciones inusuales pero manejables

---

## 📚 Referencias

- **Noise Protocol**: https://noiseprotocol.org/noise.html
- **ChaCha20-Poly1305**: RFC 8439
- **mDNS/Zeroconf**: RFC 6762, RFC 6763
- **PKCS#11**: Interfaz estándar para tokens criptográficos

---

## 👨‍💻 Autor

Proyecto desarrollado para la asignatura de Ciberseguridad.

---

## 📄 Licencia

Este proyecto es con fines educativos.
