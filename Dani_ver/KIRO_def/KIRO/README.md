# DNI-IM: Mensajería Instantánea Segura P2P

Sistema de mensajería instantánea peer-to-peer con autenticación DNIe, descubrimiento automático de peers y cifrado de extremo a extremo usando el protocolo Noise IK.

---

## 🎯 Características

- 🔐 **Autenticación DNIe**: Identidad vinculada al certificado del DNI electrónico español (con modo mock para pruebas)
- 🌐 **Soporte Internet**: Funciona en la misma red O por Internet con servidor relay
- 🔒 **Cifrado E2E**: Protocolo Noise IK con X25519, BLAKE2s y ChaCha20-Poly1305
- 🎨 **Interfaz Moderna**: Estilo WhatsApp/Telegram con tema oscuro
- 👥 **Descubrimiento Automático**: Encuentra peers automáticamente en red local o por relay
- ✅ **Verificación TOFU**: Trust On First Use para verificación de contactos
- 📬 **Cola de Mensajes**: Entrega de mensajes cuando el destinatario está offline
- 💬 **Múltiples Chats**: Gestiona varias conversaciones simultáneamente

---

## 📋 Tabla de Contenidos

1. [Instalación](#-instalación)
2. [Uso Rápido](#-uso-rápido)
3. [Configuración del Relay](#-configuración-del-relay)
4. [Pruebas](#-pruebas)
5. [Solución de Problemas](#-solución-de-problemas)
6. [Arquitectura](#-arquitectura)
7. [Seguridad](#-seguridad)

---

## 💻 Instalación

### Requisitos
- Python 3.8 o superior
- Lector de tarjetas DNIe (opcional, tiene modo mock)
- Windows, Linux o macOS

### Paso 1: Instalar Dependencias

```bash
cd KIRO
pip install -r requirements.txt
```

**Dependencias instaladas:**
- `cryptography` - Cifrado y manejo de certificados
- `pynoise` - Implementación del protocolo Noise
- `zeroconf` - Descubrimiento mDNS
- `asn1crypto` - Manejo de certificados ASN.1
- `pyscard` - Soporte para lectores de tarjetas inteligentes

### Paso 2: Verificar Instalación

```bash
python -c "import cryptography, zeroconf; print('✓ Dependencias instaladas correctamente')"
```

---

## 🚀 Uso Rápido

### Opción 1: Interfaz Gráfica (Recomendado)

```bash
python run_gui.py
```

**Características de la GUI:**
- Interfaz oscura moderna
- Múltiples ventanas de chat
- Descubrimiento de peers en tiempo real
- Visor de logs del sistema
- Gestión de contactos

### Opción 2: Interfaz de Texto (Terminal)

```bash
python run_tui.py
```

**Comandos disponibles:**
- `/list` - Listar peers descubiertos
- `/chat <número>` - Iniciar chat con un peer
- `/contacts` - Mostrar libreta de contactos
- `/quit` - Salir

---

## 🌐 Configuración del Relay

El proyecto ya está configurado con un servidor relay en Google Cloud para comunicación por Internet.

### Configuración Actual (config.py)

```python
RELAY_SERVER = "34.175.248.84"
RELAY_PORT = 7777
USE_RELAY = True
```

### Verificar Conexión al Relay

```bash
python tests/test_relay.py
```

**Resultado esperado:**
```
✅ Tu servidor relay está funcionando perfectamente!
   Puedes usar la aplicación con confianza.
```

### ¿Cómo Funciona?

1. **Misma Red Local**: Los peers se descubren automáticamente usando mDNS (como AirDrop)
2. **Redes Diferentes**: Los peers se registran en el relay y se descubren a través de él
3. **Mensajes**: Siempre cifrados de extremo a extremo, el relay NO puede leerlos

---

## 🧪 Pruebas

### Probar en el Mismo Ordenador (2 Instancias)

**Terminal 1:**
```bash
python tests/test_local_auto.py --instance 1 --gui
```

**Terminal 2:**
```bash
python tests/test_local_auto.py --instance 2 --gui
```

**Resultado:**
- Las instancias se descubren automáticamente en 5-10 segundos
- Haz doble clic en el peer para abrir el chat
- Escribe mensajes y verás que se reciben en la otra ventana

### Probar en Dos Ordenadores (Misma Red o Internet)

**En ambos ordenadores:**
```bash
python run_gui.py
```

**Resultado:**
- **Misma red WiFi**: Descubrimiento automático en 5-10 segundos
- **Redes diferentes**: Descubrimiento vía relay en 10-20 segundos
- Verás en consola: `✓ Registered with relay server at 34.175.248.84:7777`
- El peer aparecerá en la lista de la GUI
- Doble clic para chatear

---

## 🔧 Solución de Problemas

### "No smart card readers found"

**Solución:** La aplicación usa autenticación mock automáticamente. Perfecto para pruebas.

**Para producción:** Instala drivers del lector de tarjetas e inserta el DNIe.

### "No se descubren los peers"

**En la misma red:**
```bash
# Verificar que el firewall permite UDP 6666
# Windows:
netsh advfirewall firewall add rule name="DNI-IM" dir=in action=allow protocol=UDP localport=6666

# Linux:
sudo ufw allow 6666/udp
```

**Por Internet:**
1. Verifica el relay: `python test_relay.py`
2. Espera 20-30 segundos para el descubrimiento
3. Verifica que ambos muestran: `✓ Registered with relay server`

### "No se pueden enviar mensajes"

**Solución:**
1. Verifica que ambos peers están conectados
2. Revisa la consola para ver errores
3. Cierra y reabre ambas aplicaciones
4. Verifica la conexión a Internet

### "Error al instalar dependencias"

```bash
# Intenta con pip3
pip3 install -r requirements.txt

# O actualiza pip primero
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🏗️ Arquitectura

### Protocolo Criptográfico

- **Intercambio de Claves**: X25519 Elliptic Curve Diffie-Hellman
- **Hashing**: BLAKE2s con derivación de claves HKDF
- **Cifrado**: ChaCha20-Poly1305 AEAD
- **Handshake**: Patrón Noise IK (el iniciador conoce la clave estática del receptor)

### Protocolo de Red

```
Formato de Paquete:
[MessageType:1][CID:4][StreamID:2][Payload:variable]

MessageType:
  1 = HANDSHAKE_INIT
  2 = HANDSHAKE_RESP
  3 = DATA
  4 = ACK
```

### Componentes Principales

```
KIRO/
├── run_gui.py           - Lanzador de la aplicación GUI
├── run_tui.py           - Lanzador de la aplicación TUI
├── requirements.txt     - Dependencias Python
│
├── src/                 - Código fuente principal
│   ├── main_gui.py      - Aplicación con GUI
│   ├── main.py          - Aplicación con TUI
│   ├── config.py        - Configuración
│   ├── crypto_engine.py - Motor de cifrado Noise
│   ├── dnie_auth.py     - Autenticación DNIe
│   ├── network_manager.py - Gestión de red
│   ├── protocol.py      - Protocolo de comunicación
│   ├── contact_manager.py - Gestión de contactos
│   ├── message_queue.py - Cola de mensajes
│   ├── gui_modern.py    - Interfaz gráfica
│   └── tui.py           - Interfaz de texto
│
├── tests/               - Scripts de prueba
│   ├── test_relay.py
│   ├── test_local_auto.py
│   └── ...
│
├── utils/               - Utilidades opcionales
│   ├── dnie_auth_real.py
│   ├── debug_app.py
│   └── ...
│
└── program_files/       - Archivos generados
    ├── keypair.bin
    ├── contacts.json
    └── message_queue.json
```

### Archivos Generados

Los siguientes archivos se crean automáticamente en `program_files/`:

- `keypair.bin` - Par de claves X25519 del usuario
- `contacts.json` - Libreta de contactos con claves públicas
- `message_queue.json` - Mensajes pendientes de entrega

---

## 🔐 Seguridad

### Cifrado de Extremo a Extremo

- **Protocolo Noise IK**: Protocolo criptográfico estándar de la industria
- **X25519**: Intercambio de claves con curva elíptica
- **ChaCha20-Poly1305**: Cifrado autenticado
- **Perfect Forward Secrecy**: Cada sesión tiene claves únicas

### Autenticación y Protección de Claves

- **Certificado DNIe**: Identidad emitida por el gobierno español
- **Keypair cifrado con DNIe**: Tu clave privada se cifra con el certificado del DNIe
- **Protección física**: Aunque roben tu `keypair.bin`, es inútil sin tu DNIe físico + PIN
- **Verificación TOFU**: Confianza en el primer uso
- **Pinning de Clave Pública**: Detecta ataques MITM

### Identidad Real

- **Nombre del DNIe**: Tu nombre real aparece en la aplicación
- **Foto del DNIe**: Tu foto oficial como avatar
- **Número de DNI**: Identificación verificable

### Privacidad

- **Red Local**: Privacidad total, sin relay
- **Servidor Relay**: Puede ver metadatos (IPs, fingerprints) pero NO el contenido de los mensajes
- **Sin Servidor Central**: Arquitectura peer-to-peer
- **Claves protegidas**: keypair.bin cifrado con DNIe, inútil si es robado

### ¿Qué ve el Relay?

**SÍ ve:**
- Direcciones IP de los clientes
- Fingerprints (identificadores de clave pública)
- Metadatos de conexión (timestamps)

**NO ve:**
- Contenido de los mensajes (cifrados E2E)
- Nombres de usuarios
- Datos personales
- Contactos

---

## 📊 Opciones de Red

| Escenario | Solución | Tiempo de Setup | Latencia |
|-----------|----------|-----------------|----------|
| Misma WiFi | mDNS automático | 1 minuto | Muy baja |
| Misma LAN de oficina | mDNS automático | 1 minuto | Muy baja |
| Redes diferentes | Relay server | Ya configurado | Media |
| Por Internet | Relay server | Ya configurado | Media |
| Máxima seguridad | VPN + mDNS | 30 minutos | Baja |

---

## 🧪 Scripts de Prueba

### `tests/test_relay.py`
Verifica la conexión con el servidor relay.
```bash
python tests/test_relay.py
```

### `tests/test_local_auto.py`
Prueba dos instancias en el mismo ordenador con descubrimiento automático.
```bash
# Terminal 1
python tests/test_local_auto.py --instance 1 --gui

# Terminal 2
python tests/test_local_auto.py --instance 2 --gui
```

### `tests/test_udp.py`
Pruebas básicas de comunicación UDP.

---

## 💡 Consejos de Uso

### Para Mejor Rendimiento
- Usa la misma red cuando sea posible (menor latencia)
- Conexión por cable para mayor estabilidad
- El relay está optimizado pero añade latencia

### Para Máxima Seguridad
- Usa autenticación DNIe real (no mock)
- Verifica los fingerprints de contactos manualmente
- Usa VPN en lugar de relay para comunicaciones sensibles

### Para Desarrollo/Pruebas
- Usa autenticación mock (no necesitas tarjeta DNIe)
- Prueba en el mismo ordenador con `test_local_auto.py`
- Usa `test_relay.py` para verificar conectividad

---

## 📁 Estructura de Archivos

### Archivos Esenciales (12)
```
main_gui.py          - Aplicación principal ⭐
main.py              - Versión terminal
config.py            - Configuración
crypto_engine.py     - Motor de cifrado
dnie_auth.py         - Autenticación
network_manager.py   - Gestión de red
protocol.py          - Protocolo de comunicación
contact_manager.py   - Gestión de contactos
message_queue.py     - Cola de mensajes
gui_modern.py        - Interfaz gráfica
tui.py               - Interfaz de texto
requirements.txt     - Dependencias
```

### Archivos de Prueba (Opcionales)
```
test_relay.py        - Verificar relay
test_local_auto.py   - Pruebas locales
test_local.py        - Pruebas locales (versión antigua)
test_udp.py          - Pruebas UDP
```

### Archivos Generados (Automáticos)
```
program_files/
├── keypair.bin         - Claves del usuario
├── contacts.json       - Libreta de contactos
└── message_queue.json  - Mensajes pendientes
```

---

## 🚀 Inicio Rápido - Resumen

### Para Probar AHORA (1 ordenador):
```bash
# Terminal 1
python tests/test_local_auto.py --instance 1 --gui

# Terminal 2
python tests/test_local_auto.py --instance 2 --gui

# Espera 5 segundos → Doble clic en peer → ¡Chatea!
```

### Para Usar en Producción (2 ordenadores):
```bash
# En ambos ordenadores
python run_gui.py

# Espera 10-20 segundos → Doble clic en peer → ¡Chatea!
```

### Para Verificar el Relay:
```bash
python tests/test_relay.py
```

---

## ❓ Preguntas Frecuentes

**¿Necesito una tarjeta DNIe?**
No. La aplicación tiene modo mock para pruebas. Para producción, usa DNIe real.

**¿Puedo usarlo por Internet?**
Sí. El relay ya está configurado y funcionando en Google Cloud.

**¿Es seguro?**
Sí. Cifrado de extremo a extremo con protocolo Noise. Ni siquiera el relay puede leer los mensajes.

**¿Cuánto cuesta?**
Gratis. El relay usa el tier gratuito de Google Cloud.

**¿Funciona en móviles?**
Actualmente solo en escritorio (Windows/Linux/macOS). Versión móvil posible en el futuro.

**¿Cuántos usuarios soporta el relay?**
50-100 usuarios en el tier gratuito, miles en planes de pago.

---

## 📄 Licencia

Proyecto educativo para curso de criptografía y comunicaciones seguras.

---

## 🎉 ¡Listo para Chatear!

**Inicio más rápido:**
```bash
pip install -r requirements.txt
python run_gui.py
```

**¿Necesitas ayuda?** Revisa la sección de [Solución de Problemas](#-solución-de-problemas).

**¡Chatea de forma segura! 🔒💬**
