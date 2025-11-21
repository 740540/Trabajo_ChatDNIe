"""Text-based user interface using prompt_toolkit"""

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
        
        # Layout: Sidebar on left, chat and input on right
        self.layout = Layout(
            VSplit([
                Frame(
                    self.contacts_area,
                    title="🌐 Red Local"
                ),
                HSplit([
                    Frame(
                        self.chat_area,
                        title="💬 Conversación"
                    ),
                    Frame(
                        self.input_field,
                        title="✍️ Mensaje (Enter=enviar, Ctrl+C=salir, Ctrl+L=limpiar)"
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
        """
        Append text to chat area.
        Automatically scrolls to bottom.
        """
        self.chat_area.text += text
        if not text.endswith('\n'):
            self.chat_area.text += '\n'
        
        # Move cursor to end (auto-scroll)
        self.chat_area.buffer.cursor_position = len(self.chat_area.text)
    
    def update_contacts(self, peers: List[Peer]):
        """Update contacts/peers list in sidebar"""
        contact_text = "📡 Peers Disponibles:\n"
        contact_text += "=" * 28 + "\n\n"
        
        if not peers:
            contact_text += "  (ningún peer detectado)\n"
        else:
            for p in peers:
                contact_text += f"👤 {p.name}\n"
                contact_text += f"   ID: {p.peer_id or 'unknown'}\n"
                contact_text += f"   📍 {p.address}:{p.port}\n"
                contact_text += "\n"
        
        contact_text += "-" * 28 + "\n"
        contact_text += f"Total: {len(peers)} peer(s)\n"
        
        self.contacts_area.text = contact_text
    
    def set_status(self, status: str):
        """Display status message in chat"""
        self.append_chat(f"ℹ️  {status}")
    
    def show_error(self, error: str):
        """Display error message in chat"""
        self.append_chat(f"❌ ERROR: {error}")
    
    def show_success(self, message: str):
        """Display success message in chat"""
        self.append_chat(f"✅ {message}")
    
    async def run(self):
        """Run the TUI application (blocking)"""
        await self.app.run_async()
