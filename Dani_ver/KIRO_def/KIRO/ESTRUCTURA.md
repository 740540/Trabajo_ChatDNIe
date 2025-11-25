# 📁 Estructura del Proyecto DNI-IM

## ✅ Cambios Realizados

1. ✅ **Eliminado `relay_server.py`** - Ya usas el relay de Google Cloud
2. ✅ **Consolidadas todas las guías** en un solo `README.md`
3. ✅ **Archivos generados** ahora van a la carpeta `program_files/`
4. ✅ **Reorganización profesional** - Código en `src/`, tests en `tests/`, utilidades en `utils/`

---

## 📂 Estructura Actual (Profesional)

```
KIRO/
│
├── 📄 README.md                    # Guía completa y única
├── � ESTHRUCTURA.md                # Este documento
├── 📄 requirements.txt             # Dependencias Python
│
├── 🚀 LANZADORES
│   ├── run_gui.py                  # Ejecutar aplicación GUI
│   └── run_tui.py                  # Ejecutar aplicación TUI
│
├── 📁 src/                         # Código fuente principal
│   ├── __init__.py
│   ├── main_gui.py                 # Aplicación con interfaz gráfica ⭐
│   ├── main.py                     # Aplicación con interfaz de texto
│   ├── config.py                   # Configuración (relay, puertos, rutas)
│   ├── crypto_engine.py            # Motor de cifrado Noise
│   ├── dnie_auth.py                # Autenticación DNIe (con mock)
│   ├── network_manager.py          # Gestión de red (UDP, mDNS, relay)
│   ├── protocol.py                 # Protocolo de comunicación
│   ├── contact_manager.py          # Gestión de contactos
│   ├── message_queue.py            # Cola de mensajes offline
│   ├── gui_modern.py               # Interfaz gráfica moderna
│   └── tui.py                      # Interfaz de texto
│
├── 📁 tests/                       # Scripts de prueba
│   ├── __init__.py
│   ├── test_relay.py               # Verificar conexión al relay
│   ├── test_local_auto.py          # Pruebas locales automáticas
│   ├── test_local.py               # Pruebas locales (versión antigua)
│   ├── test_udp.py                 # Pruebas de red UDP
│   ├── test_instance1.bat          # Script Windows instancia 1
│   ├── test_instance2.bat          # Script Windows instancia 2
│   └── test_single_device.sh       # Script Linux/Mac
│
├── 📁 utils/                       # Utilidades opcionales
│   ├── __init__.py
│   ├── dnie_auth_real.py           # Autenticación DNIe real (sin mock)
│   ├── debug_app.py                # Herramientas de depuración
│   ├── diagnostico_red.py          # Diagnóstico de red
│   └── info_maquina.py             # Información del sistema
│
└── 📁 program_files/               # Archivos generados automáticamente
    ├── keypair.bin                 # Claves del usuario
    ├── keypair_1.bin               # Claves instancia 1 (tests)
    ├── keypair_2.bin               # Claves instancia 2 (tests)
    ├── contacts.json               # Libreta de contactos
    ├── contacts_1.json             # Contactos instancia 1 (tests)
    ├── contacts_2.json             # Contactos instancia 2 (tests)
    ├── message_queue.json          # Mensajes pendientes
    ├── queue_1.json                # Cola instancia 1 (tests)
    └── queue_2.json                # Cola instancia 2 (tests)
```

---

## 🎯 Ventajas de la Nueva Estructura

### 1. **Más Profesional**
- Estructura estándar de proyectos Python
- Separación clara de responsabilidades
- Fácil de entender para otros desarrolladores

### 2. **Más Limpio**
- Código fuente en `src/`
- Tests separados en `tests/`
- Utilidades opcionales en `utils/`
- Archivos generados en `program_files/`

### 3. **Más Fácil de Mantener**
- Todo organizado por función
- Fácil encontrar archivos
- Escalable para futuras funcionalidades

### 4. **Más Fácil de Distribuir**
- Solo necesitas `src/` + `requirements.txt` + lanzadores
- Tests y utilidades son opcionales
- Estructura clara para empaquetar

---

## 🚀 Cómo Usar

### Ejecutar la Aplicación

**Interfaz Gráfica (Recomendado):**
```bash
python run_gui.py
```

**Interfaz de Texto:**
```bash
python run_tui.py
```

### Ejecutar Tests

**Verificar relay:**
```bash
python tests/test_relay.py
```

**Pruebas locales (Terminal 1):**
```bash
python tests/test_local_auto.py --instance 1 --gui
```

**Pruebas locales (Terminal 2):**
```bash
python tests/test_local_auto.py --instance 2 --gui
```

**O usar scripts batch (Windows):**
```bash
cd tests
.\test_instance1.bat    # Terminal 1
.\test_instance2.bat    # Terminal 2
```

---

## 📊 Resumen de Archivos

### Esenciales (14 archivos)
```
src/
├── main_gui.py          ⭐ Aplicación principal
├── main.py
├── config.py
├── crypto_engine.py
├── dnie_auth.py
├── network_manager.py
├── protocol.py
├── contact_manager.py
├── message_queue.py
├── gui_modern.py
└── tui.py

Raíz:
├── run_gui.py           ⭐ Lanzador GUI
├── run_tui.py           ⭐ Lanzador TUI
└── requirements.txt     ⭐ Dependencias
```

### Tests (7 archivos)
```
tests/
├── test_relay.py
├── test_local_auto.py
├── test_local.py
├── test_udp.py
├── test_instance1.bat
├── test_instance2.bat
└── test_single_device.sh
```

### Utilidades (4 archivos)
```
utils/
├── dnie_auth_real.py
├── debug_app.py
├── diagnostico_red.py
└── info_maquina.py
```

### Documentación (2 archivos)
```
├── README.md            📖 Guía completa
└── ESTRUCTURA.md        📋 Este documento
```

---

## 📦 Para Distribuir

### Mínimo necesario:
```
KIRO/
├── run_gui.py
├── requirements.txt
├── src/                 (toda la carpeta)
└── program_files/       (se crea automáticamente)
```

### Recomendado incluir:
```
KIRO/
├── run_gui.py
├── run_tui.py
├── requirements.txt
├── README.md
├── src/                 (toda la carpeta)
├── tests/               (opcional, para verificar)
└── program_files/       (se crea automáticamente)
```

---

## 🔄 Cambios en las Importaciones

Todos los archivos ahora usan rutas relativas correctas:

**Lanzadores (`run_gui.py`, `run_tui.py`):**
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
```

**Tests (`tests/*.py`):**
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
```

**Archivos en `src/`:**
```python
# Importaciones relativas funcionan automáticamente
from config import RELAY_SERVER
from crypto_engine import CryptoEngine
```

---

## ✅ Proyecto Profesional y Organizado

El proyecto ahora está:
- ✅ **Profesional**: Estructura estándar de Python
- ✅ **Limpio**: Sin archivos duplicados o redundantes
- ✅ **Organizado**: Cada cosa en su lugar
- ✅ **Documentado**: Una sola guía completa
- ✅ **Funcional**: Todos los archivos esenciales presentes
- ✅ **Escalable**: Fácil añadir nuevas funcionalidades
- ✅ **Listo**: Para usar, distribuir o empaquetar

---

## 📈 Evolución del Proyecto

| Versión | Archivos | Estructura | Estado |
|---------|----------|------------|--------|
| Inicial | ~92 | Desorganizada | ❌ |
| Limpieza | ~24 | Plana | ⚠️ |
| **Actual** | **27** | **Profesional** | ✅ |

---

¡Proyecto optimizado y con estructura profesional! 🎉
