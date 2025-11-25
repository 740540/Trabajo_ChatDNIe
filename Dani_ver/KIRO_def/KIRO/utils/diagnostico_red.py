#!/usr/bin/env python3
"""
Script de diagnóstico para problemas de descubrimiento de peers
"""

import socket
import sys
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
import time

print("=" * 60)
print("DIAGNÓSTICO DE RED - DNI-IM")
print("=" * 60)
print()

# 1. Verificar IP local
print("1. INFORMACIÓN DE RED")
print("-" * 60)
hostname = socket.gethostname()
print(f"Hostname: {hostname}")

try:
    # Obtener IP conectándose a internet
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    print(f"IP Local (método 1): {local_ip}")
except Exception as e:
    print(f"Error obteniendo IP (método 1): {e}")
    local_ip = None

try:
    # Método alternativo
    local_ip_alt = socket.gethostbyname(hostname)
    print(f"IP Local (método 2): {local_ip_alt}")
except Exception as e:
    print(f"Error obteniendo IP (método 2): {e}")

print()

# 2. Verificar puerto UDP
print("2. VERIFICACIÓN DE PUERTO UDP")
print("-" * 60)
try:
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    test_socket.bind(('0.0.0.0', 6666))
    print("✓ Puerto 6666 disponible")
    test_socket.close()
except Exception as e:
    print(f"✗ Error con puerto 6666: {e}")
    print("  Puede que otra instancia esté corriendo")

print()

# 3. Verificar mDNS/Zeroconf
print("3. VERIFICACIÓN DE mDNS")
print("-" * 60)

class DiagnosticListener(ServiceListener):
    def __init__(self):
        self.services_found = []
    
    def add_service(self, zc, type_, name):
        print(f"✓ Servicio encontrado: {name}")
        info = zc.get_service_info(type_, name)
        if info:
            self.services_found.append(name)
            addr = socket.inet_ntoa(info.addresses[0]) if info.addresses else "N/A"
            print(f"  Dirección: {addr}:{info.port}")
            if info.properties:
                if b'fingerprint' in info.properties:
                    fp = info.properties[b'fingerprint'].decode()
                    print(f"  Fingerprint: {fp}")
                if b'name' in info.properties:
                    name = info.properties[b'name'].decode()
                    print(f"  Nombre: {name}")
    
    def remove_service(self, zc, type_, name):
        print(f"✗ Servicio eliminado: {name}")
    
    def update_service(self, zc, type_, name):
        print(f"↻ Servicio actualizado: {name}")

try:
    print("Iniciando búsqueda de servicios _dni-im._udp.local. ...")
    print("Esperando 10 segundos...")
    print()
    
    zeroconf = Zeroconf()
    listener = DiagnosticListener()
    browser = ServiceBrowser(zeroconf, "_dni-im._udp.local.", listener)
    
    time.sleep(10)
    
    print()
    print(f"Total de servicios DNI-IM encontrados: {len(listener.services_found)}")
    
    zeroconf.close()
    
except Exception as e:
    print(f"✗ Error con mDNS: {e}")
    print("  Posibles causas:")
    print("  - Firewall bloqueando puerto 5353 (mDNS)")
    print("  - Problema con la red")

print()

# 4. Verificar dependencias
print("4. VERIFICACIÓN DE DEPENDENCIAS")
print("-" * 60)

dependencies = [
    'cryptography',
    'zeroconf',
    'pyscard'
]

for dep in dependencies:
    try:
        __import__(dep)
        print(f"✓ {dep} instalado")
    except ImportError:
        print(f"✗ {dep} NO instalado")

print()

# 5. Recomendaciones
print("5. RECOMENDACIONES")
print("-" * 60)

if local_ip:
    print(f"Tu IP es: {local_ip}")
    print(f"La otra máquina debe estar en la misma red (ejemplo: {'.'.join(local_ip.split('.')[:-1])}.X)")
    print()

print("Si no se encuentran peers automáticamente:")
print()
print("1. Verifica que ambas máquinas están en la misma WiFi")
print("2. Verifica el firewall:")
print("   macOS: Sistema > Seguridad > Firewall")
print("   Permite conexiones entrantes para Python")
print()
print("3. Prueba añadir el peer manualmente:")
print("   - Anota el fingerprint de la otra máquina")
print("   - En la GUI: Click '➕ Add Peer Manually'")
print("   - Introduce: fingerprint, IP, puerto 6666")
print()
print("4. Si nada funciona, ejecuta este script en AMBAS máquinas")
print("   y compara los resultados")

print()
print("=" * 60)
print("FIN DEL DIAGNÓSTICO")
print("=" * 60)
