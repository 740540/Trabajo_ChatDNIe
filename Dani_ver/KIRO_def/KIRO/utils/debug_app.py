#!/usr/bin/env python3
"""
Versión de debug de la aplicación que muestra más información
"""

import sys
import os

# Habilitar modo debug
os.environ['DEBUG'] = '1'

print("=" * 60)
print("MODO DEBUG ACTIVADO")
print("=" * 60)
print()
print("Esta versión mostrará información detallada de:")
print("- Paquetes UDP enviados y recibidos")
print("- Handshakes")
print("- Errores de red")
print()
print("=" * 60)
print()

# Monkey-patch para añadir debug a network_manager
import network_manager
original_send = network_manager.NetworkManager.send

def debug_send(self, data, address, port):
    print(f"[DEBUG] 📤 Enviando {len(data)} bytes a {address}:{port}")
    print(f"[DEBUG]    Tipo de mensaje: {data[0] if len(data) > 0 else 'N/A'}")
    return original_send(self, data, address, port)

network_manager.NetworkManager.send = debug_send

# Monkey-patch para añadir debug al callback de recepción
original_on_packet = None

def debug_on_packet_wrapper(original_func):
    def wrapper(data, addr):
        print(f"[DEBUG] 📥 Recibido {len(data)} bytes de {addr[0]}:{addr[1]}")
        print(f"[DEBUG]    Tipo de mensaje: {data[0] if len(data) > 0 else 'N/A'}")
        return original_func(data, addr)
    return wrapper

# Importar y ejecutar main_gui
from main_gui import DNIIMApplication, main

# Patch el método _on_packet_received
original_on_packet = DNIIMApplication._on_packet_received

def debug_on_packet_received(self, data, addr):
    print(f"[DEBUG] 📥 Procesando paquete de {addr[0]}:{addr[1]}")
    try:
        result = original_on_packet(self, data, addr)
        print(f"[DEBUG] ✅ Paquete procesado correctamente")
        return result
    except Exception as e:
        print(f"[DEBUG] ❌ Error procesando paquete: {e}")
        import traceback
        traceback.print_exc()
        raise

DNIIMApplication._on_packet_received = debug_on_packet_received

# Ejecutar
print("Iniciando aplicación en modo debug...")
print()
main()
