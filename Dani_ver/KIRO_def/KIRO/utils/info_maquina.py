#!/usr/bin/env python3
"""
Script simple para obtener la información de esta máquina
Ejecuta esto en cada máquina para obtener el fingerprint e IP
"""

import socket
import hashlib
import os

print("=" * 60)
print("INFORMACIÓN DE ESTA MÁQUINA")
print("=" * 60)
print()

# Obtener IP
hostname = socket.gethostname()
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
except:
    local_ip = socket.gethostbyname(hostname)

print(f"📍 IP Local: {local_ip}")
print(f"🖥️  Hostname: {hostname}")

# Generar fingerprint (simulando lo que hace la app)
keypair_file = 'keypair.bin'
if os.path.exists(keypair_file):
    with open(keypair_file, 'rb') as f:
        data = f.read()
    fingerprint = hashlib.sha256(data).hexdigest()[:16]
    print(f"🔑 Fingerprint: {fingerprint}")
    print()
    print("✓ Este es el fingerprint que debes usar")
else:
    print(f"⚠️  Archivo {keypair_file} no existe todavía")
    print("   Ejecuta primero: python3 main_gui.py")
    print("   Luego vuelve a ejecutar este script")

print()
print("=" * 60)
print("PARA AÑADIR ESTA MÁQUINA EN LA OTRA:")
print("=" * 60)
print()
print("En la otra máquina, en la GUI:")
print("1. Click en '➕ Add Peer Manually'")
print("2. Introduce:")
print(f"   Fingerprint: {fingerprint if os.path.exists(keypair_file) else '<ejecuta la app primero>'}")
print(f"   IP: {local_ip}")
print(f"   Port: 6666")
print("3. Click 'Add Peer'")
print()
