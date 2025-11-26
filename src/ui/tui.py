# ui/tui.py

from typing import List, Callable, Optional
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, VSplit
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.key_binding import KeyBindings

from session.session import Peer


class ChatTUI:
    """
    Text-based user interface for managing multiple chat sessions.
    Uses prompt_toolkit for async terminal UI.
    """
    
    def __init__(self):
        # State for current peer selection
        self.peers: List[Peer] = []
        self.current_peer_index: int = -1  # -1 means "no peer selected"

        # Chat display area
        self.chat_area = TextArea(
            text="=== DNIe Instant Messenger ===\n",
            multiline=True,
            read_only=True,
            scrollbar=True,
            focusable=False
        )
        
        # Input field
        self.input_field = TextArea(
            height=3,
            prompt=">>> ",
            multiline=False,
            wrap_lines=False
        )
        
        # Contacts/peers sidebar
        self.contacts_area = TextArea(
            text="📡 Peers:\n" + "-" * 28 + "\n",
            multiline=True,
            read_only=True,
            width=30,
            focusable=False,
            scrollbar=True
        )
        
        # Callback for sending messages
        self.message_send_callback: Optional[Callable[[str], None]] = None
        
        # Key bindings
        self.kb = KeyBindings()
        
        @self.kb.add('c-c')
        @self.kb.add('c-q')
        def exit_app(event):
            """Exit application"""
            event.app.exit()
        
        @self.kb.add('enter')
        def send_message(event):
            """Send message on Enter"""
            text = self.input_field.text.strip()
            if text and self.message_send_callback:
                self.message_send_callback(text)
                self.input_field.text = ""
        
        @self.kb.add('c-l')
        def clear_screen(event):
            """Clear chat area"""
            self.chat_area.text = "=== DNIe Instant Messenger ===\n"

        @self.kb.add('c-n')
        def next_peer(event):
            """Cycle to next peer (Ctrl+N)"""
            self.select_next_peer()
        
        # Layout: Sidebar on left, chat and input on right
        self.layout = Layout(
            VSplit([
                Frame(
                    self.contacts_area,
                    title="🌐 Peers"
                ),
                HSplit([
                    Frame(
                        self.chat_area,
                        title="💬 Chat"
                    ),
                    Frame(
                        self.input_field,
                        title="✍️ Mensaje (Enter=enviar, Ctrl+N=cambiar peer)"
                    )
                ])
            ])
        )
        
        # Create application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True
        )
    
    def append_chat(self, text: str):
        """Append text to chat area and scroll."""
        if not text.endswith("\n"):
            text += "\n"
        self.chat_area.text += text
        self.chat_area.buffer.cursor_position = len(self.chat_area.text)
    
    def update_contacts(self, peers: List[Peer]):
        """
        Update contacts/peers list in sidebar.
        Keeps current selection index if possible.
        """
        self.peers = peers

        # Ensure current_peer_index is in range
        if self.peers:
            if self.current_peer_index < 0 or self.current_peer_index >= len(self.peers):
                self.current_peer_index = 0
        else:
            self.current_peer_index = -1

        contact_text = "📡 Peers Disponibles:\n"
        contact_text += "=" * 28 + "\n\n"
        
        if not self.peers:
            contact_text += "  (ningún peer detectado)\n"
        else:
            for idx, p in enumerate(self.peers):
                marker = "👉" if idx == self.current_peer_index else "  "
                contact_text += f"{marker} {p.name}\n"
                contact_text += f"   ID: {p.peer_id or 'unknown'}\n"
                contact_text += f"   📍 {p.address}:{p.port}\n"
                contact_text += "\n"
        
        contact_text += "-" * 28 + "\n"
        contact_text += f"Total: {len(self.peers)} peer(s)\n"
        
        self.contacts_area.text = contact_text
    
    def select_next_peer(self):
        """Select the next peer in the list (used by Ctrl+N)."""
        if not self.peers:
            self.current_peer_index = -1
            return
        self.current_peer_index = (self.current_peer_index + 1) % len(self.peers)
        self.update_contacts(self.peers)
        current = self.get_current_peer()
        if current:
            self.append_chat(f"ℹ️ Ahora estás chateando con: {current.name} ({current.peer_id})")
    
    def get_current_peer(self) -> Optional[Peer]:
        """Return the currently selected peer, or None."""
        if self.current_peer_index < 0 or self.current_peer_index >= len(self.peers):
            return None
        return self.peers[self.current_peer_index]
    
    async def run(self):
        """Run the TUI application (blocking)"""
        await self.app.run_async()
