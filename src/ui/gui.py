# dnie_im/ui/gui.py - COLOR FIX

"""
TUI-styled GUI for DNIe Instant Messenger.
FIXED: Proper message color coding for sent/received/queued.
"""

import tkinter as tk
from tkinter import font as tkfont
from typing import List, Callable, Optional
from datetime import datetime

from session.session import Peer


class ChatGUI:
    """
    Terminal-styled GUI for the DNIe instant messenger with mouse support.
    """

    def __init__(self, chat_history_manager=None):
        self.root = tk.Tk()
        self.root.title("DNIe Instant Messenger")
        self.root.geometry("1000x650")

        # Terminal color scheme
        self.bg_color = "#1e1e1e"
        self.fg_color = "#d4d4d4"
        self.select_bg = "#264f78"
        self.border_color = "#3c3c3c"
        self.system_color = "#608b4e"
        self.user_color = "#4ec9b0"  # Cyan for sent messages
        self.peer_color = "#ce9178"  # Orange for received messages
        self.warning_color = "#d7ba7d"
        self.error_color = "#f48771"
        self.queued_color = "#9cdcfe"  # Blue for queued messages

        self.root.configure(bg=self.bg_color)

        self.font_family = "Consolas" if tk.sys.platform == "win32" else "Courier New"
        self.text_font = (self.font_family, 10)
        self.bold_font = (self.font_family, 10, "bold")
        self.small_font = (self.font_family, 9)

        # Data
        self.peers: List[Peer] = []
        self.current_peer_index: int = -1

        # Store current username
        self.username = "Tú"

        # Integrated chat history manager
        self.chat_history_manager = chat_history_manager

        # Callbacks
        self.message_send_callback: Optional[Callable[[str], None]] = None
        self.handshake_callback: Optional[Callable[[], None]] = None

        # Proper close flag
        self.is_closing = False
        self.close_requested = False

        self._create_widgets()

        self.system_window = None

        # Proper window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self._request_close)

    def _request_close(self):
        """Handle window close request."""
        print("[DEBUG] Close requested, setting close_requested flag to True")
        self.close_requested = True
        self.is_closing = True

    def _create_widgets(self):
        """Create all GUI widgets with terminal styling."""

        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title bar
        title_frame = tk.Frame(main_frame, bg=self.border_color, height=40)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="╔══════════════════════════════════════════════════════════════════╗\n║           DNIe Instant Messenger - Terminal Interface            ║\n╚══════════════════════════════════════════════════════════════════╝",
            bg=self.border_color,
            fg=self.fg_color,
            font=self.small_font,
            justify=tk.LEFT
        )
        title_label.pack(pady=5, padx=10)

        content_frame = tk.Frame(main_frame, bg=self.bg_color)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # LEFT: Peers List
        peers_frame = tk.Frame(content_frame, bg=self.border_color, width=300)
        peers_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        peers_frame.pack_propagate(False)

        peers_header = tk.Label(
            peers_frame,
            text="┌─ 🌐 PEERS DISPONIBLES ─────────────────┐",
            bg=self.border_color,
            fg=self.system_color,
            font=self.bold_font,
            anchor=tk.W
        )
        peers_header.pack(fill=tk.X, padx=5, pady=(5, 0))

        peers_container = tk.Frame(peers_frame, bg=self.bg_color)
        peers_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        peers_scroll = tk.Scrollbar(peers_container, bg=self.bg_color)
        peers_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.peers_listbox = tk.Listbox(
            peers_container,
            yscrollcommand=peers_scroll.set,
            font=self.small_font,
            bg=self.bg_color,
            fg=self.fg_color,
            selectbackground=self.select_bg,
            selectforeground=self.fg_color,
            highlightthickness=0,
            borderwidth=0,
            activestyle='none',
            selectmode=tk.SINGLE
        )
        self.peers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        peers_scroll.config(command=self.peers_listbox.yview)

        self.peers_listbox.bind('<<ListboxSelect>>', self._on_peer_selected)

        peers_footer = tk.Frame(peers_frame, bg=self.border_color)
        peers_footer.pack(fill=tk.X, padx=5, pady=(0, 5))

        controls_text = tk.Label(
            peers_footer,
            text="[Click]=Select  [Ctrl+H]=Handshake\n[Ctrl+S]=System Log  [Ctrl+Q]=Exit",
            bg=self.border_color,
            fg=self.warning_color,
            font=self.small_font,
            justify=tk.LEFT
        )
        controls_text.pack(pady=5)

        # RIGHT: Chat Area
        right_frame = tk.Frame(content_frame, bg=self.bg_color)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.chat_header_frame = tk.Frame(right_frame, bg=self.border_color)
        self.chat_header_frame.pack(fill=tk.X, pady=(0, 5))

        self.chat_header = tk.Label(
            self.chat_header_frame,
            text="┌─ 💬 CHAT ──────────────────────────────────────────────────────────────┐",
            bg=self.border_color,
            fg=self.user_color,
            font=self.bold_font,
            anchor=tk.W
        )
        self.chat_header.pack(fill=tk.X, padx=5, pady=5)

        messages_frame = tk.Frame(right_frame, bg=self.bg_color)
        messages_frame.pack(fill=tk.BOTH, expand=True)

        messages_scroll = tk.Scrollbar(messages_frame, bg=self.bg_color)
        messages_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.messages_text = tk.Text(
            messages_frame,
            wrap=tk.WORD,
            font=self.text_font,
            bg=self.bg_color,
            fg=self.fg_color,
            yscrollcommand=messages_scroll.set,
            insertbackground=self.fg_color,
            selectbackground=self.select_bg,
            highlightthickness=0,
            borderwidth=0,
            state=tk.DISABLED
        )
        self.messages_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        messages_scroll.config(command=self.messages_text.yview)

        self.messages_text.tag_config("user", foreground=self.user_color, font=self.bold_font)
        self.messages_text.tag_config("peer", foreground=self.peer_color, font=self.bold_font)
        self.messages_text.tag_config("system", foreground=self.system_color, font=self.text_font)
        self.messages_text.tag_config("warning", foreground=self.warning_color)
        self.messages_text.tag_config("error", foreground=self.error_color)
        self.messages_text.tag_config("timestamp", foreground="#808080")
        self.messages_text.tag_config("queued", foreground=self.queued_color)

        input_frame = tk.Frame(right_frame, bg=self.border_color)
        input_frame.pack(fill=tk.X, pady=(5, 0))

        input_label = tk.Label(
            input_frame,
            text=">>> ",
            bg=self.border_color,
            fg=self.system_color,
            font=self.bold_font
        )
        input_label.pack(side=tk.LEFT, padx=(5, 0))

        self.input_entry = tk.Entry(
            input_frame,
            font=self.text_font,
            bg=self.bg_color,
            fg=self.fg_color,
            insertbackground=self.fg_color,
            selectbackground=self.select_bg,
            highlightthickness=0,
            borderwidth=0
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)
        self.input_entry.bind('<Return>', self._on_send_message)

        send_label = tk.Label(
            input_frame,
            text="[Enter]",
            bg=self.border_color,
            fg=self.warning_color,
            font=self.small_font
        )
        send_label.pack(side=tk.RIGHT, padx=5)

        self.status_bar = tk.Label(
            main_frame,
            text="└─ Estado: Iniciando...",
            bg=self.border_color,
            fg=self.system_color,
            font=self.small_font,
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, pady=(5, 0))

        self.root.bind('<Control-h>', lambda e: self._on_handshake_button())
        self.root.bind('<Control-s>', lambda e: self._show_system_window())
        self.root.bind('<Control-q>', lambda e: self._request_close())
        self.root.bind('<Control-c>', lambda e: self._request_close())

    def set_username(self, username: str):
        """Set the current username for message detection."""
        self.username = username
        print(f"[DEBUG] GUI username set to: {username}")

    def _create_system_window(self):
        """Create the system messages window with terminal styling."""
        self.system_window = tk.Toplevel(self.root)
        self.system_window.title("System Messages")
        self.system_window.geometry("700x500")
        self.system_window.configure(bg=self.bg_color)

        header = tk.Label(
            self.system_window,
            text="╔═══════════════════════════════════════════════════════════╗\n║              📋 MENSAJES DEL SISTEMA                      ║\n╚═══════════════════════════════════════════════════════════╝",
            bg=self.border_color,
            fg=self.system_color,
            font=self.small_font,
            justify=tk.LEFT
        )
        header.pack(fill=tk.X, padx=10, pady=10)

        text_frame = tk.Frame(self.system_window, bg=self.bg_color)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        scroll = tk.Scrollbar(text_frame, bg=self.bg_color)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.system_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=self.text_font,
            bg=self.bg_color,
            fg=self.fg_color,
            yscrollcommand=scroll.set,
            selectbackground=self.select_bg,
            highlightthickness=0,
            borderwidth=0,
            state=tk.DISABLED
        )
        self.system_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.system_text.yview)

        self.system_text.tag_config("info", foreground=self.user_color)
        self.system_text.tag_config("success", foreground=self.system_color)
        self.system_text.tag_config("warning", foreground=self.warning_color)
        self.system_text.tag_config("error", foreground=self.error_color)
        self.system_text.tag_config("timestamp", foreground="#808080")

        footer = tk.Label(
            self.system_window,
            text="[Ctrl+C]=Clear  [Esc]=Close",
            bg=self.border_color,
            fg=self.warning_color,
            font=self.small_font
        )
        footer.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.system_window.bind('<Control-c>', lambda e: self._clear_system_messages())
        self.system_window.bind('<Escape>', lambda e: self._hide_system_window())
        self.system_window.protocol("WM_DELETE_WINDOW", self._hide_system_window)

    def _show_system_window(self):
        """Show the system messages window."""
        if self.system_window is None or not self.system_window.winfo_exists():
            self._create_system_window()
        self.system_window.deiconify()
        self.system_window.lift()

    def _hide_system_window(self):
        """Hide the system messages window."""
        if self.system_window and self.system_window.winfo_exists():
            self.system_window.withdraw()

    def _clear_system_messages(self):
        """Clear system messages."""
        if self.system_text:
            self.system_text.config(state=tk.NORMAL)
            self.system_text.delete(1.0, tk.END)
            self.system_text.insert(1.0, "System log cleared.\n", "info")
            self.system_text.config(state=tk.DISABLED)

    def _on_peer_selected(self, event):
        """Handle peer selection - load encrypted chat history."""
        selection = self.peers_listbox.curselection()
        if not selection:
            return

        self.current_peer_index = selection[0]

        if self.current_peer_index >= len(self.peers):
            return

        peer = self.peers[self.current_peer_index]

        header_text = f"┌─ 💬 CHAT CON {peer.name.upper()} ({peer.peer_id or 'unknown'}) "
        header_text += "─" * (80 - len(header_text)) + "┐"
        self.chat_header.config(text=header_text)

        # LOAD ENCRYPTED HISTORY
        self._load_chat_history(peer)

        # Auto-focus input when peer selected
        self.input_entry.focus()

    def _load_chat_history(self, peer: Peer):
        """Load and display encrypted chat history for a peer."""
        peer_id = peer.peer_id or f"{peer.address}:{peer.port}"

        self.messages_text.config(state=tk.NORMAL)
        self.messages_text.delete(1.0, tk.END)

        # LOAD FROM ENCRYPTED STORAGE
        if self.chat_history_manager:
            try:
                messages = self.chat_history_manager.get_messages(peer_id, limit=100)

                if messages:
                    for msg in messages:
                        sender = msg.get('sender', 'Unknown')
                        text = msg.get('text', '')
                        timestamp = msg.get('timestamp', '')
                        msg_type = msg.get('type', 'user')

                        # Check if this is our message
                        is_our_message = (sender == self.username or 
                                        sender.lower() == self.username.lower() or
                                        msg_type == 'queued')

                        if is_our_message:
                            sender = "Tú"

                        self._display_message(sender, text, timestamp, msg_type)
                else:
                    self.messages_text.insert(tk.END, "No hay mensajes previos con este peer.\n", "system")
            except Exception as e:
                self.messages_text.insert(tk.END, f"Error cargando historial: {e}\n", "error")
                print(f"[ERROR] Loading history: {e}")
        else:
            self.messages_text.insert(tk.END, "Historial de chat no disponible.\n", "system")

        self.messages_text.config(state=tk.DISABLED)
        self.messages_text.see(tk.END)

    def _display_message(self, sender: str, text: str, timestamp: str = "", msg_type: str = "user"):
        """Display a message in the chat area with appropriate color."""
        # Don't change state if already enabled
        was_disabled = str(self.messages_text.cget("state")) == "disabled"
        if was_disabled:
            self.messages_text.config(state=tk.NORMAL)

        if timestamp:
            # Format timestamp if it's ISO format
            try:
                if 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%H:%M:%S")
            except:
                pass
            self.messages_text.insert(tk.END, f"[{timestamp}] ", "timestamp")

        print(f"[DEBUG GUI] _display_message: sender='{sender}', type='{msg_type}'")

        # FIXED: Better message type detection and coloring
        if sender == "Tú" or sender == self.username or sender.lower() == "you":
            # Our message
            if msg_type == "queued":
                # Queued message - BLUE
                self.messages_text.insert(tk.END, f"► {sender}: ", "queued")
                self.messages_text.insert(tk.END, f"{text} ", "queued")
                self.messages_text.insert(tk.END, "[📬 Encolado]\n", "warning")
                print(f"[DEBUG GUI] Displayed as QUEUED (blue)")
            else:
                # Sent message - CYAN
                self.messages_text.insert(tk.END, f"► {sender}: ", "user")
                self.messages_text.insert(tk.END, f"{text}\n", "user")
                print(f"[DEBUG GUI] Displayed as USER (cyan)")
        elif sender == "System" or sender == "system" or msg_type in ["disconnect", "connect", "system"]:
            # System message - GREEN
            self.messages_text.insert(tk.END, f"● {text}\n", "system")
            print(f"[DEBUG GUI] Displayed as SYSTEM (green)")
        else:
            # Peer message - ORANGE
            self.messages_text.insert(tk.END, f"◄ {sender}: ", "peer")
            self.messages_text.insert(tk.END, f"{text}\n", "peer")
            print(f"[DEBUG GUI] Displayed as PEER (orange)")

        # Restore state only if it was disabled
        if was_disabled:
            self.messages_text.config(state=tk.DISABLED)
        self.messages_text.see(tk.END)

    def _on_send_message(self, event):
        """Handle send message."""
        text = self.input_entry.get().strip()
        if not text:
            return

        if self.current_peer_index < 0:
            self.append_system("⚠ No hay ningún peer seleccionado", "warning")
            return

        self.input_entry.delete(0, tk.END)

        if self.message_send_callback:
            self.message_send_callback(text)

    def _on_handshake_button(self):
        """Handle manual handshake."""
        if self.current_peer_index < 0:
            self.append_system("⚠ No hay peer seleccionado para handshake", "warning")
            return

        if self.handshake_callback:
            self.handshake_callback()

    # ========== Public API ==========

    def append_chat(self, text: str, msg_type: str = "user"):
        """Append a message (called by messenger)."""
        if self.is_closing:
            return

        print(f"[DEBUG GUI] append_chat: text='{text}', type='{msg_type}'")

        # System messages go to system log
        is_system_msg = (msg_type in ["disconnect", "connect", "system"] or
                        any(text.startswith(emoji) for emoji in 
                            ["🚀", "👤", "🔑", "📡", "🔍", "🤝", "🔐", "📝", "✅"]))

        # Warning/error messages
        is_warning_or_error = text.startswith("⚠") or text.startswith("❌") or text.startswith("📬")

        if is_system_msg or is_warning_or_error:
            # Log to system window
            self.append_system(text)

            # ALSO show disconnect/connect in chat if applicable
            if msg_type in ["disconnect", "connect"]:
                current_peer = self.get_current_peer()
                if current_peer and self.current_peer_index >= 0:
                    self._display_message("System", text, datetime.now().strftime("%H:%M:%S"), msg_type)
        else:
            # FIXED: Regular chat message - parse and display with correct type
            if ": " in text:
                # Format: [Sender]: Message or [Sender → Recipient]: Message
                parts = text.split(": ", 1)
                sender_part = parts[0].strip("[]")
                message = parts[1]

                # Extract sender name (handle "Tú → PeerName" format)
                if " → " in sender_part:
                    sender = sender_part.split(" → ")[0]
                else:
                    sender = sender_part

                timestamp = datetime.now().strftime("%H:%M:%S")

                print(f"[DEBUG GUI] Parsed: sender='{sender}', message='{message}', type={msg_type}")

                # Display if peer is selected and message is from/to current peer
                if self.current_peer_index >= 0:
                    current_peer = self.get_current_peer()
                    # Check if message is from/to current peer
                    if current_peer and (sender == current_peer.name or 
                                        sender == "Tú" or 
                                        sender == self.username):
                        print(f"[DEBUG GUI] Displaying with type: {msg_type}")
                        # PASS THE TYPE TO _display_message!
                        self._display_message(sender, message, timestamp, msg_type)
                    else:
                        print(f"[DEBUG GUI] Not displaying - wrong peer")
                else:
                    print(f"[DEBUG GUI] Not displaying - no peer selected")
            else:
                print(f"[DEBUG GUI] Unknown message format: {text}")

    def append_system(self, text: str, tag: str = "info"):
        """Append system message."""
        if self.is_closing:
            return

        if "❌" in text or "Error" in text:
            tag = "error"
        elif "⚠" in text:
            tag = "warning"
        elif "✅" in text or "🤝" in text or "🔐" in text or "👋" in text:
            tag = "success"

        if self.system_window is None or not self.system_window.winfo_exists():
            self._create_system_window()
            self.system_window.withdraw()

        try:
            self.system_text.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.system_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.system_text.insert(tk.END, f"{text}\n", tag)
            self.system_text.config(state=tk.DISABLED)
            self.system_text.see(tk.END)
        except:
            pass

        try:
            clean_text = text.replace("🚀", "").replace("📡", "").replace("🔍", "").replace("🤝", "").replace("⚠", "").replace("✅", "").replace("👋", "").strip()
            self.status_bar.config(text=f"└─ {clean_text[:70]}...")
        except:
            pass

    def update_contacts(self, peers: List[Peer]):
        """Update the peers list."""
        if self.is_closing:
            return

        self.peers = peers

        current_peer = self.get_current_peer()

        self.peers_listbox.delete(0, tk.END)

        for i, peer in enumerate(peers):
            is_selected = (current_peer and peer.peer_id == current_peer.peer_id)
            marker = "👉" if is_selected else "  "

            name = peer.name[:12] if len(peer.name) > 12 else peer.name
            peer_id_short = (peer.peer_id[:8] + "...") if peer.peer_id and len(peer.peer_id) > 11 else (peer.peer_id or "unknown")

            display = f"{marker} {name:<12} │ {peer_id_short:<11} │ {peer.address}"

            self.peers_listbox.insert(tk.END, display)

            if is_selected:
                self.peers_listbox.selection_set(i)
                self.current_peer_index = i

        peer_count = len(peers)
        try:
            if peer_count == 0:
                self.status_bar.config(text="└─ Estado: No hay peers disponibles")
            else:
                self.status_bar.config(text=f"└─ Estado: {peer_count} peer(s) detectado(s)")
        except:
            pass

    def get_current_peer(self) -> Optional[Peer]:
        """Return currently selected peer."""
        if self.current_peer_index < 0 or self.current_peer_index >= len(self.peers):
            return None
        return self.peers[self.current_peer_index]

    def run(self):
        """Run the GUI."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self._request_close()

    async def run_async(self):
        """Run asynchronously."""
        import asyncio

        def update():
            if not self.is_closing and not self.close_requested:
                try:
                    self.root.update()
                    self.root.after(10, update)
                except:
                    self.close_requested = True

        update()

        try:
            while not self.close_requested:
                await asyncio.sleep(0.01)
        except:
            pass
