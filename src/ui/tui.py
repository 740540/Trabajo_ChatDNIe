# dnie_im/ui/tui.py

"""
Text User Interface using prompt_toolkit.

Layout:
- Left column: peers and their info.
- Right top: chat messages and system info.
- Right bottom: input box to write messages.
"""

from typing import List, Callable, Optional

from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, VSplit
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.key_binding import KeyBindings

from session.session import Peer


class ChatTUI:
    """
    TUI for the DNIe instant messenger.
    """

    def __init__(self):
        # Current peers and selection state
        self.peers: List[Peer] = []
        self.current_peer_index: int = -1

        # Main chat area
        self.chat_area = TextArea(
            text="=== DNIe Instant Messenger ===\n",
            multiline=True,
            read_only=True,
            scrollbar=True,
            focusable=False,
        )

        # Input box
        self.input_field = TextArea(
            height=3,
            prompt=">>> ",
            multiline=False,
            wrap_lines=False,
        )

        # Peers list
        self.contacts_area = TextArea(
            text="📡 Peers:\n" + "-" * 28 + "\n",
            multiline=True,
            read_only=True,
            width=32,
            focusable=False,
            scrollbar=True,
        )

        # Callbacks (to be set by messenger)
        self.message_send_callback: Optional[Callable[[str], None]] = None
        self.handshake_callback: Optional[Callable[[], None]] = None

        # Key bindings
        self.kb = KeyBindings()

        @self.kb.add("c-c")
        @self.kb.add("c-q")
        def exit_app(event):
            event.app.exit()

        @self.kb.add("enter")
        def send_message(event):
            # FIXED: Read text before clearing to avoid race condition
            text = self.input_field.text.strip()
            if text and self.message_send_callback:
                self.message_send_callback(text)
            # Clear after callback
            self.input_field.text = ""

        @self.kb.add("c-l")
        def clear_screen(event):
            self.chat_area.text = "=== DNIe Instant Messenger ===\n"

        @self.kb.add("c-n")
        def next_peer(event):
            self.select_next_peer()

        @self.kb.add("c-h")
        def manual_handshake(event):
            if self.handshake_callback:
                self.handshake_callback()

        # Layout
        right_column = HSplit(
            [
                Frame(self.chat_area, title="💬 Chat"),
                Frame(
                    self.input_field,
                    title="✍️ Mensaje (Enter=enviar, Ctrl+N=cambiar peer, Ctrl+H=handshake)",
                ),
            ]
        )

        root_container = VSplit(
            [
                Frame(self.contacts_area, title="🌐 Peers"),
                right_column,
            ]
        )

        self.layout = Layout(root_container)
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,
        )

    # ---------- Helpers ----------

    def append_chat(self, text: str):
        """Append text to chat area and scroll."""
        # FIXED: Simplified concatenation
        self.chat_area.text += text + '\n'
        self.chat_area.buffer.cursor_position = len(self.chat_area.text)

    def update_contacts(self, peers: List[Peer]):
        """Update peers list in the left panel."""
        self.peers = peers

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
                contact_text += f"   📍 {p.address}:{p.port}\n\n"

        contact_text += "-" * 28 + "\n"
        contact_text += f"Total: {len(self.peers)} peer(s)\n"

        self.contacts_area.text = contact_text

    def select_next_peer(self):
        """Cycle to the next peer (Ctrl+N)."""
        if not self.peers:
            self.current_peer_index = -1
            return

        self.current_peer_index = (self.current_peer_index + 1) % len(self.peers)
        self.update_contacts(self.peers)

        current = self.get_current_peer()
        if current:
            self.append_chat(
                f"ℹ️ Ahora estás chateando con: {current.name} ({current.peer_id})"
            )

    def get_current_peer(self) -> Optional[Peer]:
        """Return currently selected peer, or None."""
        if self.current_peer_index < 0 or self.current_peer_index >= len(self.peers):
            return None
        return self.peers[self.current_peer_index]

    async def run(self):
        """Run the TUI (blocking until exit)."""
        await self.app.run_async()
