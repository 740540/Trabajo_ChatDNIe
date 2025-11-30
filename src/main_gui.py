# main_gui.py - FINAL FIX

"""
Entry point for DNIe Instant Messenger with GUI.
FIXED: Proper window close detection.
"""

import asyncio
import getpass
import tkinter as tk

from messenger import DNIeMessenger


async def main():
    print("=== DNIe Instant Messenger (GUI) ===")
    username = input("Nombre de usuario: ").strip() or "Usuario"
    pin = getpass.getpass("PIN del DNIe: ")

    # Import GUI
    from ui.gui import ChatGUI

    messenger = DNIeMessenger(username)

    # Store loop reference
    loop = asyncio.get_running_loop()
    messenger.loop = loop

    # Initialize messenger (creates chat_history_manager and message_queue)
    await messenger.initialize(pin)

    # Pass chat_history_manager to GUI
    messenger.tui = ChatGUI(chat_history_manager=messenger.chat_history)
    messenger.tui.message_send_callback = messenger.on_message_send
    messenger.tui.handshake_callback = messenger.manual_handshake

    # Show initial system messages
    messenger.tui.append_system("🚀 DNIe Instant Messenger iniciado")
    messenger.tui.append_system(f"👤 Usuario: {username}")
    messenger.tui.append_system("📡 Buscando peers en la red local...")

    # Get chat history statistics
    if messenger.chat_history:
        stats = messenger.chat_history.get_statistics()
        messenger.tui.append_system(
            f"📊 Historial: {stats['total_peers']} peer(s), {stats['total_messages']} mensaje(s)"
        )

    # Get message queue statistics
    if messenger.message_queue:
        queue_stats = messenger.message_queue.get_statistics()
        if queue_stats['total_queued_messages'] > 0:
            messenger.tui.append_system(
                f"📬 Mensajes pendientes: {queue_stats['total_queued_messages']} en cola para {queue_stats['total_peers_with_queue']} peer(s)"
            )
            messenger.tui.append_system("💡 Se enviarán automáticamente cuando los peers se conecten")

    # Run GUI with asyncio integration
    await run_gui_async(messenger)


async def run_gui_async(messenger):
    """Run the GUI with proper asyncio integration."""
    import asyncio

    # Start the receiver loop
    messenger.running = True
    recv_task = asyncio.create_task(messenger.message_receiver_loop())

    try:
        # Run GUI update loop
        gui = messenger.tui

        # FIXED: Check close_requested flag instead of winfo_exists
        while not gui.close_requested:
            try:
                gui.root.update()
                await asyncio.sleep(0.01)
            except tk.TclError:
                # Window destroyed
                break
            except Exception as e:
                print(f"\n[DEBUG] GUI update error: {e}")
                break

    except KeyboardInterrupt:
        print("\n[DEBUG] KeyboardInterrupt recibido")
        gui.close_requested = True
    finally:
        print("\n[DEBUG] Iniciando cierre limpio...")

        # ============================================
        # Send GOODBYE before cleanup
        # ============================================
        print("👋 Notificando a peers...")

        try:
            # Send GOODBYE (with timeout protection)
            goodbye_task = asyncio.create_task(messenger.send_goodbye_to_all())

            # Wait max 1 second for GOODBYE to send
            try:
                await asyncio.wait_for(goodbye_task, timeout=1.0)
                print("[DEBUG] GOODBYE sent successfully")
            except asyncio.TimeoutError:
                print("[WARNING] GOODBYE timeout")
                goodbye_task.cancel()
                try:
                    await goodbye_task
                except:
                    pass
        except Exception as e:
            print(f"⚠️ Error enviando GOODBYE: {e}")

        # Cleanup
        print("Limpiando recursos...")
        messenger.running = False

        # Cancel receiver task
        try:
            recv_task.cancel()
            try:
                await asyncio.wait_for(recv_task, timeout=0.5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass
        except Exception as e:
            print(f"[DEBUG] Error canceling recv_task: {e}")

        # Stop discovery
        if messenger.discovery:
            try:
                await messenger.discovery.stop_advertising()
            except Exception as e:
                print(f"[DEBUG] Error stopping discovery: {e}")

        # Stop transport
        try:
            messenger.transport.stop()
        except Exception as e:
            print(f"[DEBUG] Error stopping transport: {e}")

        # Close identity
        try:
            messenger.identity.close()
        except Exception as e:
            print(f"[DEBUG] Error closing identity: {e}")

        # Show final statistics
        print(f"\n📊 Sesión finalizada:")

        try:
            if messenger.chat_history:
                stats = messenger.chat_history.get_statistics()
                print(f"   💬 Chat: {stats['total_peers']} peer(s), {stats['total_messages']} mensaje(s)")
                print(f"   📁 Ubicación: {stats['storage_directory']}")
        except Exception as e:
            print(f"   ⚠️ Error obteniendo estadísticas de chat: {e}")

        try:
            if messenger.message_queue:
                queue_stats = messenger.message_queue.get_statistics()
                if queue_stats['total_queued_messages'] > 0:
                    print(f"   📬 Cola: {queue_stats['total_queued_messages']} mensaje(s) pendiente(s)")
                    print(f"   💡 Se enviarán la próxima vez que los peers se conecten")
                else:
                    print(f"   ✅ Cola: Sin mensajes pendientes")
        except Exception as e:
            print(f"   ⚠️ Error obteniendo estadísticas de cola: {e}")

        # Ensure GUI is properly destroyed
        try:
            if hasattr(gui, 'root'):
                try:
                    gui.root.quit()
                    gui.root.destroy()
                except:
                    pass
        except:
            pass

        print("[DEBUG] Cierre completado")

        # Wipe all session keys
        for session in messenger.peer_sessions.values():
            session.send_key = b'\x00' * 32
            session.recv_key = b'\x00' * 32
        messenger.peer_sessions.clear()

        # Clear GUI
        try:
            gui.messagestext.delete('1.0', 'end')
        except:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[DEBUG] KeyboardInterrupt en main")
        pass
