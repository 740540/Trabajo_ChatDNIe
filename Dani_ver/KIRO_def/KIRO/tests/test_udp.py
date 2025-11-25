#!/usr/bin/env python3
"""
Test de conectividad UDP entre dos máquinas
Ejecuta en modo servidor en una máquina y cliente en la otra
"""

import socket
import sys
import time

def servidor(port=6666):
    """Modo servidor - escucha mensajes"""
    print(f"🎧 Modo SERVIDOR - Escuchando en puerto {port}")
    print("Esperando mensajes...")
    print()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('0.0.0.0', port))
    
    # Obtener IP local
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"📍 Tu IP es: {local_ip}")
        print(f"📍 Dile a la otra máquina que use esta IP: {local_ip}")
        print()
    except:
        pass
    
    try:
        while True:
            data, addr = sock.recvfrom(1024)
            print(f"✅ Mensaje recibido de {addr[0]}:{addr[1]}")
            print(f"   Contenido: {data.decode()}")
            print()
            
            # Responder
            response = f"Recibido: {data.decode()}"
            sock.sendto(response.encode(), addr)
            print(f"📤 Respuesta enviada a {addr[0]}:{addr[1]}")
            print()
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")
        sock.close()

def cliente(ip_destino, port=6666):
    """Modo cliente - envía mensajes"""
    print(f"📡 Modo CLIENTE - Enviando a {ip_destino}:{port}")
    print()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Obtener IP local
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        print(f"📍 Tu IP es: {local_ip}")
        print()
    except:
        pass
    
    for i in range(5):
        mensaje = f"Test {i+1} desde cliente"
        print(f"📤 Enviando: {mensaje}")
        
        try:
            sock.sendto(mensaje.encode(), (ip_destino, port))
            
            # Esperar respuesta (timeout 2 segundos)
            sock.settimeout(2)
            try:
                data, addr = sock.recvfrom(1024)
                print(f"✅ Respuesta recibida: {data.decode()}")
                print(f"   Desde: {addr[0]}:{addr[1]}")
            except socket.timeout:
                print(f"❌ No se recibió respuesta (timeout)")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
        time.sleep(1)
    
    print("👋 Test completado")
    sock.close()

def main():
    print("=" * 60)
    print("TEST DE CONECTIVIDAD UDP")
    print("=" * 60)
    print()
    
    if len(sys.argv) < 2:
        print("Uso:")
        print()
        print("  MÁQUINA 1 (servidor):")
        print("    python3 test_udp.py servidor [puerto]")
        print()
        print("  MÁQUINA 2 (cliente):")
        print("    python3 test_udp.py cliente <IP_de_maquina_1> [puerto]")
        print()
        print("Ejemplo:")
        print("  Máquina 1: python3 test_udp.py servidor")
        print("  Máquina 2: python3 test_udp.py cliente 192.168.0.21")
        print()
        print("Con puerto personalizado:")
        print("  Máquina 1: python3 test_udp.py servidor 7777")
        print("  Máquina 2: python3 test_udp.py cliente 192.168.0.21 7777")
        print()
        sys.exit(1)
    
    modo = sys.argv[1].lower()
    
    if modo == 'servidor' or modo == 'server':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 6666
        servidor(port)
    elif modo == 'cliente' or modo == 'client':
        if len(sys.argv) < 3:
            print("❌ Error: Debes especificar la IP del servidor")
            print("   Ejemplo: python3 test_udp.py cliente 192.168.0.21")
            sys.exit(1)
        ip_destino = sys.argv[2]
        port = int(sys.argv[3]) if len(sys.argv) > 3 else 6666
        cliente(ip_destino, port)
    else:
        print(f"❌ Modo desconocido: {modo}")
        print("   Usa: servidor o cliente")
        sys.exit(1)

if __name__ == '__main__':
    main()
