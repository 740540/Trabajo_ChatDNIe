"""Text User Interface for chat application"""

import sys
import threading
from typing import Dict, List, Callable


class ChatWindow:
    """Represents a chat conversation"""
    def __init__(self, fingerprint: str, name: str, stream_id: int):
        self.fingerprint = fingerprint
        self.name = name
        self.stream_id = stream_id
        self.messages: List[str] = []
        self.unread_count = 0


class SimpleTUI:
    """Simple text-based UI for multiple chats"""
    
    def __init__(self, my_name: str):
        self.my_name = my_name
        self.chats: Dict[str, ChatWindow] = {}  # fingerprint -> ChatWindow
        self.active_chat: Optional[str] = None
        self.send_callback: Optional[Callable] = None
        self.running = False
        self.next_stream_id = 1
    
    def start(self, send_callback: Callable):
        """Start the TUI"""
        self.send_callback = send_callback
        self.running = True
        
        print("\n" + "="*60)
        print("DNI-IM Secure Chat")
        print("="*60)
        print(f"Logged in as: {self.my_name}")
        print("\nCommands:")
        print("  /list          - List discovered peers")
        print("  /chat <id>     - Open chat with peer (use number from /list)")
        print("  /contacts      - Show contact book")
        print("  /switch <id>   - Switch to different chat")
        print("  /addpeer <fp> <ip> <port> - Manually add peer (for testing)")
        print("  /quit          - Exit application")
        print("="*60 + "\n")
        
        # Start input thread
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
    
    def stop(self):
        """Stop the TUI"""
        self.running = False
    
    def _input_loop(self):
        """Handle user input"""
        while self.running:
            try:
                line = input()
                if line.startswith('/'):
                    self._handle_command(line)
                else:
                    self._send_message(line)
            except EOFError:
                break
            except Exception as e:
                print(f"Input error: {e}")
    
    def _handle_command(self, command: str):
        """Handle slash commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if cmd == '/quit':
            print("Exiting...")
            self.running = False
            sys.exit(0)
        
        elif cmd == '/list':
            if self.send_callback:
                self.send_callback('list_peers', None)
        
        elif cmd == '/chat':
            if arg and self.send_callback:
                self.send_callback('start_chat', arg)
        
        elif cmd == '/contacts':
            if self.send_callback:
                self.send_callback('list_contacts', None)
        
        elif cmd == '/switch':
            if arg:
                self.active_chat = arg
                print(f"Switched to chat with {arg}")
                self._display_chat()
        
        elif cmd == '/addpeer':
            if arg and self.send_callback:
                self.send_callback('add_peer', arg)
        
        else:
            print(f"Unknown command: {cmd}")
    
    def _send_message(self, message: str):
        """Send message in active chat"""
        if not self.active_chat:
            print("No active chat. Use /chat <id> to start a conversation.")
            return
        
        if not message.strip():
            return
        
        if self.send_callback:
            chat = self.chats.get(self.active_chat)
            if chat:
                self.send_callback('send_message', {
                    'fingerprint': self.active_chat,
                    'stream_id': chat.stream_id,
                    'message': message
                })
                self.add_message(self.active_chat, f"[You]: {message}")
    
    def _display_chat(self):
        """Display current chat messages"""
        if not self.active_chat or self.active_chat not in self.chats:
            return
        
        chat = self.chats[self.active_chat]
        print(f"\n--- Chat with {chat.name} ---")
        for msg in chat.messages[-20:]:  # Show last 20 messages
            print(msg)
        print("---")
        chat.unread_count = 0
    
    def create_or_get_chat(self, fingerprint: str, name: str) -> ChatWindow:
        """Create new chat window or get existing"""
        if fingerprint not in self.chats:
            stream_id = self.next_stream_id
            self.next_stream_id += 1
            self.chats[fingerprint] = ChatWindow(fingerprint, name, stream_id)
        return self.chats[fingerprint]
    
    def add_message(self, fingerprint: str, message: str):
        """Add message to chat"""
        if fingerprint in self.chats:
            chat = self.chats[fingerprint]
            chat.messages.append(message)
            
            if fingerprint == self.active_chat:
                print(message)
            else:
                chat.unread_count += 1
                print(f"\n[New message from {chat.name}] (use /switch {fingerprint[:8]})")
    
    def show_peers(self, peers: list):
        """Display discovered peers"""
        print("\nDiscovered peers:")
        for i, (fp, addr) in enumerate(peers, 1):
            print(f"  {i}. {fp[:8]} @ {addr}")
        print()
    
    def show_contacts(self, contacts: list):
        """Display contact book"""
        print("\nContact book:")
        for fp, name in contacts:
            print(f"  {name} ({fp[:8]})")
        print()


from typing import Optional
