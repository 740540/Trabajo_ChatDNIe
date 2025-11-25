#!/usr/bin/env python3
"""
Script de diagnóstico para verificar la conexión con el servidor relay
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import socket
import struct
import time
from config import RELAY_SERVER, RELAY_PORT

def test_relay_connection():
    """Prueba la conexión con el servidor relay"""
    print("=" * 60)
    print("DIAGNÓSTICO DEL SERVIDOR RELAY")
    print("=" * 60)
    print(f"\nServidor: {RELAY_SERVER}:{RELAY_PORT}")
    
    # Test 1: Verificar conectividad básica
    print("\n[Test 1] Verificando conectividad de red...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5)
        print(f"✓ Socket UDP creado correctamente")
    except Exception as e:
        print(f"✗ Error creando socket: {e}")
        return False
    
    # Test 2: Enviar paquete de registro
    print("\n[Test 2] Enviando paquete de registro al relay...")
    try:
        test_fingerprint = "test12345678abcd"
        packet = struct.pack('!B', 0x01) + test_fingerprint.encode('utf-8')
        sock.sendto(packet, (RELAY_SERVER, RELAY_PORT))
        print(f"✓ Paquete enviado: REGISTER con fingerprint '{test_fingerprint}'")
    except Exception as e:
        print(f"✗ Error enviando paquete: {e}")
        sock.close()
        return False
    
    # Test 3: Esperar respuesta del relay
    print("\n[Test 3] Esperando respuesta del relay (timeout: 5s)...")
    try:
        data, addr = sock.recvfrom(1024)
        print(f"✓ Respuesta recibida desde {addr}")
        print(f"  Datos: {data.hex()}")
        
        if len(data) > 0:
            cmd = data[0]
            if cmd == 0x81:  # REGISTER_ACK
                print(f"✓ Registro confirmado por el relay!")
                print(f"  El servidor relay está funcionando correctamente")
                return True
            else:
                print(f"⚠ Respuesta inesperada: comando {cmd:#x}")
                return False
    except socket.timeout:
        print(f"✗ Timeout: No se recibió respuesta del relay")
        print(f"  Posibles causas:")
        print(f"  - El servidor relay no está ejecutándose")
        print(f"  - El firewall está bloqueando el puerto UDP {RELAY_PORT}")
        print(f"  - La IP del relay es incorrecta")
        return False
    except Exception as e:
        print(f"✗ Error recibiendo respuesta: {e}")
        return False
    finally:
        sock.close()

def test_relay_with_two_clients():
    """Simula dos clientes registrándose en el relay"""
    print("\n" + "=" * 60)
    print("TEST DE COMUNICACIÓN ENTRE DOS CLIENTES")
    print("=" * 60)
    
    # Cliente 1
    print("\n[Cliente 1] Registrándose...")
    sock1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock1.settimeout(5)
    fp1 = "client1_fp123456"
    packet1 = struct.pack('!B', 0x01) + fp1.encode('utf-8')
    sock1.sendto(packet1, (RELAY_SERVER, RELAY_PORT))
    
    try:
        data, _ = sock1.recvfrom(1024)
        if data[0] == 0x81:
            print(f"✓ Cliente 1 registrado: {fp1}")
    except:
        print(f"✗ Cliente 1 no pudo registrarse")
        sock1.close()
        return False
    
    # Cliente 2
    print("\n[Cliente 2] Registrándose...")
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock2.settimeout(5)
    fp2 = "client2_fp789abc"
    packet2 = struct.pack('!B', 0x01) + fp2.encode('utf-8')
    sock2.sendto(packet2, (RELAY_SERVER, RELAY_PORT))
    
    try:
        data, _ = sock2.recvfrom(1024)
        if data[0] == 0x81:
            print(f"✓ Cliente 2 registrado: {fp2}")
    except:
        print(f"✗ Cliente 2 no pudo registrarse")
        sock1.close()
        sock2.close()
        return False
    
    # Cliente 1 envía mensaje a Cliente 2 a través del relay
    print("\n[Cliente 1] Enviando mensaje a Cliente 2 vía relay...")
    test_message = b"Hello from Client 1!"
    relay_packet = struct.pack('!B', 0x02) + fp2.encode('utf-8') + test_message
    sock1.sendto(relay_packet, (RELAY_SERVER, RELAY_PORT))
    print(f"✓ Mensaje enviado: '{test_message.decode()}'")
    
    # Cliente 2 intenta recibir
    print("\n[Cliente 2] Esperando mensaje...")
    try:
        data, _ = sock2.recvfrom(1024)
        if data == test_message:
            print(f"✓ Mensaje recibido correctamente: '{data.decode()}'")
            print(f"✓ El relay está funcionando perfectamente!")
            sock1.close()
            sock2.close()
            return True
        else:
            print(f"⚠ Mensaje recibido pero no coincide")
            print(f"  Esperado: {test_message}")
            print(f"  Recibido: {data}")
    except socket.timeout:
        print(f"✗ No se recibió el mensaje")
        print(f"  El relay puede no estar reenviando correctamente")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    sock1.close()
    sock2.close()
    return False

def main():
    print("\n🔍 Iniciando diagnóstico del servidor relay...\n")
    
    # Test básico de conexión
    if test_relay_connection():
        print("\n" + "=" * 60)
        print("✓ CONEXIÓN AL RELAY: OK")
        print("=" * 60)
        
        # Test avanzado de comunicación
        time.sleep(1)
        if test_relay_with_two_clients():
            print("\n" + "=" * 60)
            print("✓ RELAY COMPLETAMENTE FUNCIONAL")
            print("=" * 60)
            print("\n✅ Tu servidor relay está funcionando perfectamente!")
            print("   Puedes usar la aplicación con confianza.\n")
        else:
            print("\n" + "=" * 60)
            print("⚠ RELAY PARCIALMENTE FUNCIONAL")
            print("=" * 60)
            print("\n⚠ El relay acepta conexiones pero puede tener problemas")
            print("  reenviando mensajes entre clientes.\n")
    else:
        print("\n" + "=" * 60)
        print("✗ CONEXIÓN AL RELAY: FALLO")
        print("=" * 60)
        print("\n❌ No se pudo conectar al servidor relay.")
        print("\nVerifica:")
        print("  1. El servidor relay está ejecutándose en Google Cloud")
        print("  2. La IP en config.py es correcta: " + RELAY_SERVER)
        print("  3. El firewall permite tráfico UDP en el puerto " + str(RELAY_PORT))
        print("  4. Ejecuta en el servidor: sudo systemctl status dni-im-relay\n")

if __name__ == '__main__':
    main()
