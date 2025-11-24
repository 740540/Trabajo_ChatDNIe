"""Modern GUI for DNI-IM using tkinter - Dark Theme"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Dict, Callable, Optional
import threading
from datetime import datetime


# Modern dark theme colors
COLORS = {
    'bg_dark': '#0B141A',
    'bg_secondary': '#1F2C33',
    'bg_chat': '#0B141A',
    'bg_input': '#1F2C33',
    'bg_message_me': '#005C4B',
    'bg_message_them': '#1F2C33',
    'text_primary': '#E9EDEF',
    'text_secondary': '#8696A0',
    'text_me': '#FFFFFF',
    'text_them': '#E9EDEF',
    'accent': '#00A884',
    'accent_hover': '#06CF9C',
    'border': '#2A3942',
    'system': '#667781',
}


class ChatWindow(tk.Toplevel):
    def __init__(self, parent, fingerprint: str, name: str, stream_id: int, send_callback: Callable):
        super().__init__(parent)
        self.fingerprint = fingerprint
        self.name = name
        self.stream_id = stream_id
        self.send_callback = send_callback
        self.title(f"Chat with {name}")
        self.geometry("700x600")
        self.configure(bg=COLORS['bg_dark'])
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        header = tk.Frame(self, bg=COLORS['bg_secondary'], height=60)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        tk.Label(header, text=name, font=('Segoe UI', 12, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], anchor='w'
        ).pack(side='left', padx=20, pady=10)
        tk.Label(header, text=f"🔒 {fingerprint[:16]}...", font=('Segoe UI', 8),
                bg=COLORS['bg_secondary'], fg=COLORS['text_secondary']
        ).pack(side='left', padx=5)
        
        chat_frame = tk.Frame(self, bg=COLORS['bg_chat'])
        chat_frame.grid(row=1, column=0, sticky='nsew')
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, state='disabled', font=('Segoe UI', 10),
            bg=COLORS['bg_chat'], fg=COLORS['text_primary'], padx=15, pady=15,
            borderwidth=0, highlightthickness=0, insertbackground=COLORS['text_primary']
        )
        self.chat_display.grid(row=0, column=0, sticky='nsew')
        self.chat_display.tag_config('me_bubble', background=COLORS['bg_message_me'],
            foreground=COLORS['text_me'], font=('Segoe UI', 10),
            lmargin1=200, lmargin2=200, rmargin=20, spacing1=5, spacing3=5)
        self.chat_display.tag_config('them_bubble', background=COLORS['bg_message_them'],
            foreground=COLORS['text_them'], font=('Segoe UI', 10),
            lmargin1=20, lmargin2=20, rmargin=200, spacing1=5, spacing3=5)
        self.chat_display.tag_config('system', foreground=COLORS['system'],
            font=('Segoe UI', 9, 'italic'), justify='center', spacing1=10, spacing3=10)
        
        input_container = tk.Frame(self, bg=COLORS['bg_dark'])
        input_container.grid(row=2, column=0, sticky='ew', padx=10, pady=10)
        input_container.grid_columnconfigure(0, weight=1)
        input_frame = tk.Frame(input_container, bg=COLORS['bg_input'],
                              highlightbackground=COLORS['border'], highlightthickness=1)
        input_frame.grid(row=0, column=0, sticky='ew')
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.message_input = tk.Text(input_frame, height=3, font=('Segoe UI', 10),
            wrap=tk.WORD, bg=COLORS['bg_input'], fg=COLORS['text_primary'],
            insertbackground=COLORS['text_primary'], borderwidth=0,
            highlightthickness=0, padx=10, pady=10)
        self.message_input.grid(row=0, column=0, sticky='ew')
        self.message_input.bind('<Return>', self._on_enter)
        self.message_input.bind('<Shift-Return>', lambda e: None)
        
        self.send_button = tk.Button(input_frame, text="➤", command=self._send_message,
            font=('Segoe UI', 14, 'bold'), bg=COLORS['accent'], fg='white',
            activebackground=COLORS['accent_hover'], activeforeground='white',
            borderwidth=0, padx=20, pady=10, cursor='hand2')
        self.send_button.grid(row=0, column=1, padx=5)
        
        self.message_input.focus()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.closed = False
    
    def _on_enter(self, event):
        if not event.state & 0x1:
            self._send_message()
            return 'break'
    
    def _send_message(self):
        message = self.message_input.get('1.0', 'end-1c').strip()
        if message:
            self.add_message('You', message, is_me=True)
            if self.send_callback:
                self.send_callback('send_message', {
                    'fingerprint': self.fingerprint,
                    'stream_id': self.stream_id,
                    'message': message
                })
            self.message_input.delete('1.0', tk.END)
    
    def add_message(self, sender: str, message: str, is_me: bool = False):
        if self.closed:
            return
        self.chat_display.config(state='normal')
        timestamp = datetime.now().strftime('%H:%M')
        tag = 'me_bubble' if is_me else 'them_bubble'
        self.chat_display.insert(tk.END, '\n')
        self.chat_display.insert(tk.END, f"{message}  {timestamp}\n", tag)
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def add_system_message(self, message: str):
        if self.closed:
            return
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"\n{message}\n", 'system')
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def _on_close(self):
        self.closed = True
        self.destroy()


class DNIGUI:
    def __init__(self, my_name: str):
        self.my_name = my_name
        self.root = tk.Tk()
        self.root.title("DNI-IM - Secure Messaging")
        self.root.geometry("1000x700")
        self.root.configure(bg=COLORS['bg_dark'])
        self.chat_windows: Dict[str, ChatWindow] = {}
        self.next_stream_id = 1
        self.send_callback: Optional[Callable] = None
        self._create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.running = True
    
    def _create_widgets(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        left_panel = tk.Frame(self.root, width=320, bg=COLORS['bg_secondary'])
        left_panel.grid(row=0, column=0, sticky='nsew')
        left_panel.grid_propagate(False)
        
        header = tk.Frame(left_panel, bg=COLORS['bg_secondary'], height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="DNI-IM", font=('Segoe UI', 18, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_primary']
        ).pack(side='left', padx=20, pady=20)
        
        user_card = tk.Frame(left_panel, bg=COLORS['bg_dark'],
                            highlightbackground=COLORS['border'], highlightthickness=1)
        user_card.pack(fill='x', padx=10, pady=10)
        user_inner = tk.Frame(user_card, bg=COLORS['bg_dark'])
        user_inner.pack(fill='x', padx=15, pady=15)
        tk.Label(user_inner, text="👤", font=('Segoe UI', 24),
                bg=COLORS['bg_dark'], fg=COLORS['text_primary']
        ).pack(side='left', padx=(0, 10))
        user_info = tk.Frame(user_inner, bg=COLORS['bg_dark'])
        user_info.pack(side='left', fill='x', expand=True)
        self.user_label = tk.Label(user_info, text=self.my_name,
                                   font=('Segoe UI', 11, 'bold'),
                                   bg=COLORS['bg_dark'], fg=COLORS['text_primary'], anchor='w')
        self.user_label.pack(fill='x')
        self.fingerprint_label = tk.Label(user_info, text="", font=('Segoe UI', 8),
                                          bg=COLORS['bg_dark'], fg=COLORS['text_secondary'], anchor='w')
        self.fingerprint_label.pack(fill='x')
        
        peers_header = tk.Frame(left_panel, bg=COLORS['bg_secondary'])
        peers_header.pack(fill='x', padx=10, pady=(10, 5))
        tk.Label(peers_header, text="DISCOVERED PEERS", font=('Segoe UI', 9, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_secondary']
        ).pack(side='left')
        tk.Button(peers_header, text="🔄", font=('Segoe UI', 12),
                 bg=COLORS['bg_secondary'], fg=COLORS['text_secondary'],
                 activebackground=COLORS['bg_dark'], activeforeground=COLORS['accent'],
                 borderwidth=0, cursor='hand2', command=self._refresh_peers
        ).pack(side='right')
        
        peers_container = tk.Frame(left_panel, bg=COLORS['bg_secondary'])
        peers_container.pack(fill='both', expand=True, padx=10, pady=5)
        peers_scroll = tk.Scrollbar(peers_container, bg=COLORS['bg_secondary'])
        peers_scroll.pack(side='right', fill='y')
        self.peers_listbox = tk.Listbox(peers_container, yscrollcommand=peers_scroll.set,
            font=('Segoe UI', 10), bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
            selectbackground=COLORS['accent'], selectforeground='white',
            activestyle='none', borderwidth=0, highlightthickness=0)
        self.peers_listbox.pack(fill='both', expand=True)
        peers_scroll.config(command=self.peers_listbox.yview)
        self.peers_listbox.bind('<Double-Button-1>', self._on_peer_double_click)
        
        button_frame = tk.Frame(left_panel, bg=COLORS['bg_secondary'])
        button_frame.pack(fill='x', padx=10, pady=10)
        tk.Button(button_frame, text="➕ Add Peer Manually",
                 command=self._show_add_peer_dialog, font=('Segoe UI', 10),
                 bg=COLORS['accent'], fg='white',
                 activebackground=COLORS['accent_hover'], activeforeground='white',
                 borderwidth=0, pady=12, cursor='hand2'
        ).pack(fill='x', pady=(0, 5))
        tk.Button(button_frame, text="📋 View Contacts",
                 command=self._show_contacts, font=('Segoe UI', 10),
                 bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
                 activebackground=COLORS['border'], activeforeground=COLORS['text_primary'],
                 borderwidth=0, pady=12, cursor='hand2'
        ).pack(fill='x', pady=(0, 5))
        
        tk.Button(button_frame, text="🗑️ Delete Peer",
                 command=self._delete_peer, font=('Segoe UI', 10),
                 bg='#8B0000', fg='white',
                 activebackground='#A52A2A', activeforeground='white',
                 borderwidth=0, pady=12, cursor='hand2'
        ).pack(fill='x')
        
        right_panel = tk.Frame(self.root, bg=COLORS['bg_chat'])
        right_panel.grid(row=0, column=1, sticky='nsew')
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)
        log_header = tk.Frame(right_panel, bg=COLORS['bg_secondary'], height=60)
        log_header.grid(row=0, column=0, sticky='ew')
        log_header.grid_propagate(False)
        tk.Label(log_header, text="System Log", font=('Segoe UI', 12, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_primary']
        ).pack(side='left', padx=20, pady=15)
        
        log_container = tk.Frame(right_panel, bg=COLORS['bg_chat'])
        log_container.grid(row=1, column=0, sticky='nsew', padx=20, pady=20)
        log_container.grid_rowconfigure(0, weight=1)
        log_container.grid_columnconfigure(0, weight=1)
        self.log_display = scrolledtext.ScrolledText(log_container, wrap=tk.WORD,
            state='disabled', font=('Consolas', 9), bg=COLORS['bg_dark'],
            fg=COLORS['text_primary'], padx=15, pady=15, borderwidth=0,
            highlightthickness=0, insertbackground=COLORS['text_primary'])
        self.log_display.grid(row=0, column=0, sticky='nsew')
        self.log_display.tag_config('info', foreground='#8696A0')
        self.log_display.tag_config('success', foreground='#00A884')
        self.log_display.tag_config('error', foreground='#FF6B6B')
        self.log_display.tag_config('warning', foreground='#FFD93D')
    
    def start(self, send_callback: Callable):
        self.send_callback = send_callback
        self.log("DNI-IM started", 'success')
        self.log(f"Logged in as: {self.my_name}", 'info')
    
    def run(self):
        self.root.mainloop()
    
    def stop(self):
        self.running = False
        for window in list(self.chat_windows.values()):
            if not window.closed:
                window.destroy()
        self.root.quit()
    
    def _on_close(self):
        if messagebox.askokcancel("Quit", "Do you want to quit DNI-IM?"):
            self.stop()
    
    def log(self, message: str, level: str = 'info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_display.config(state='normal')
        self.log_display.insert(tk.END, f"[{timestamp}] ", 'info')
        self.log_display.insert(tk.END, f"{message}\n", level)
        self.log_display.config(state='disabled')
        self.log_display.see(tk.END)
    
    def set_fingerprint(self, fingerprint: str):
        self.fingerprint_label.config(text=f"FP: {fingerprint[:16]}")
    
    def update_peers(self, peers: list):
        self.peers_listbox.delete(0, tk.END)
        self.peers_data = peers
        for fp, addr in peers:
            self.peers_listbox.insert(tk.END, f"{fp[:8]}... @ {addr}")
        if peers:
            self.log(f"Found {len(peers)} peer(s)", 'success')
    
    def _refresh_peers(self):
        if self.send_callback:
            self.send_callback('list_peers', None)
    
    def _on_peer_double_click(self, event):
        selection = self.peers_listbox.curselection()
        if selection and hasattr(self, 'peers_data'):
            idx = selection[0]
            if idx < len(self.peers_data):
                fingerprint, addr = self.peers_data[idx]
                self._start_chat(fingerprint)
    
    def _start_chat(self, fingerprint: str):
        if fingerprint in self.chat_windows and not self.chat_windows[fingerprint].closed:
            self.chat_windows[fingerprint].focus()
            return
        if self.send_callback:
            self.send_callback('start_chat', fingerprint)
    
    def _show_add_peer_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Peer Manually")
        dialog.geometry("450x280")
        dialog.configure(bg=COLORS['bg_dark'])
        dialog.transient(self.root)
        dialog.grab_set()
        header = tk.Frame(dialog, bg=COLORS['bg_secondary'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="➕ Add Peer Manually", font=('Segoe UI', 12, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_primary']
        ).pack(side='left', padx=20, pady=15)
        form = tk.Frame(dialog, bg=COLORS['bg_dark'])
        form.pack(fill='both', expand=True, padx=20, pady=20)
        tk.Label(form, text="Fingerprint:", font=('Segoe UI', 10),
                bg=COLORS['bg_dark'], fg=COLORS['text_secondary']).grid(row=0, column=0, sticky='w', pady=(0, 5))
        fp_entry = tk.Entry(form, width=40, font=('Segoe UI', 10),
                           bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                           insertbackground=COLORS['text_primary'], borderwidth=0)
        fp_entry.grid(row=1, column=0, sticky='ew', pady=(0, 15), ipady=8)
        tk.Label(form, text="IP Address:", font=('Segoe UI', 10),
                bg=COLORS['bg_dark'], fg=COLORS['text_secondary']).grid(row=2, column=0, sticky='w', pady=(0, 5))
        ip_entry = tk.Entry(form, width=40, font=('Segoe UI', 10),
                           bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                           insertbackground=COLORS['text_primary'], borderwidth=0)
        ip_entry.grid(row=3, column=0, sticky='ew', pady=(0, 15), ipady=8)
        ip_entry.insert(0, "127.0.0.1")
        tk.Label(form, text="Port:", font=('Segoe UI', 10),
                bg=COLORS['bg_dark'], fg=COLORS['text_secondary']).grid(row=4, column=0, sticky='w', pady=(0, 5))
        port_entry = tk.Entry(form, width=40, font=('Segoe UI', 10),
                             bg=COLORS['bg_input'], fg=COLORS['text_primary'],
                             insertbackground=COLORS['text_primary'], borderwidth=0)
        port_entry.grid(row=5, column=0, sticky='ew', pady=(0, 20), ipady=8)
        port_entry.insert(0, "6666")
        form.grid_columnconfigure(0, weight=1)
        
        def add_peer():
            fp = fp_entry.get().strip()
            ip = ip_entry.get().strip()
            port = port_entry.get().strip()
            if fp and ip and port:
                if self.send_callback:
                    self.send_callback('add_peer', f"{fp} {ip} {port}")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "All fields are required", parent=dialog)
        
        btn_frame = tk.Frame(form, bg=COLORS['bg_dark'])
        btn_frame.grid(row=6, column=0, sticky='ew')
        tk.Button(btn_frame, text="Add Peer", command=add_peer,
                 font=('Segoe UI', 10, 'bold'), bg=COLORS['accent'], fg='white',
                 activebackground=COLORS['accent_hover'], activeforeground='white',
                 borderwidth=0, pady=12, cursor='hand2'
        ).pack(side='left', fill='x', expand=True, padx=(0, 5))
        tk.Button(btn_frame, text="Cancel", command=dialog.destroy,
                 font=('Segoe UI', 10), bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                 activebackground=COLORS['border'], activeforeground=COLORS['text_primary'],
                 borderwidth=0, pady=12, cursor='hand2'
        ).pack(side='left', fill='x', expand=True, padx=(5, 0))
        fp_entry.focus()
    
    def _show_contacts(self):
        if self.send_callback:
            self.send_callback('list_contacts', None)
    
    def _delete_peer(self):
        selection = self.peers_listbox.curselection()
        if selection and hasattr(self, 'peers_data'):
            idx = selection[0]
            if idx < len(self.peers_data):
                fingerprint, addr = self.peers_data[idx]
                if messagebox.askyesno("Delete Peer", 
                    f"Delete peer {fingerprint[:8]}... from list?\n\nThis will remove the peer from discovered list but not from contacts."):
                    if self.send_callback:
                        self.send_callback('delete_peer', fingerprint)
        else:
            messagebox.showinfo("No Selection", "Please select a peer to delete.")
    
    def show_contacts_dialog(self, contacts: list):
        dialog = tk.Toplevel(self.root)
        dialog.title("Contact Book")
        dialog.geometry("600x500")
        dialog.configure(bg=COLORS['bg_dark'])
        dialog.transient(self.root)
        header = tk.Frame(dialog, bg=COLORS['bg_secondary'], height=60)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="📋 Contact Book", font=('Segoe UI', 14, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_primary']
        ).pack(side='left', padx=20, pady=15)
        frame = tk.Frame(dialog, bg=COLORS['bg_dark'])
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        style = ttk.Style()
        style.configure("Dark.Treeview", background=COLORS['bg_secondary'],
            foreground=COLORS['text_primary'], fieldbackground=COLORS['bg_secondary'], borderwidth=0)
        style.configure("Dark.Treeview.Heading", background=COLORS['bg_dark'],
            foreground=COLORS['text_primary'], borderwidth=0)
        style.map('Dark.Treeview', background=[('selected', COLORS['accent'])],
            foreground=[('selected', 'white')])
        tree = ttk.Treeview(frame, columns=('Name', 'Fingerprint'), show='headings', style="Dark.Treeview")
        tree.heading('Name', text='Name')
        tree.heading('Fingerprint', text='Fingerprint')
        tree.column('Name', width=200)
        tree.column('Fingerprint', width=320)
        for fp, name in contacts:
            tree.insert('', 'end', values=(name, fp))
        tree.pack(fill='both', expand=True)
        tk.Button(dialog, text="Close", command=dialog.destroy,
                 font=('Segoe UI', 10), bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
                 activebackground=COLORS['border'], activeforeground=COLORS['text_primary'],
                 borderwidth=0, pady=12, cursor='hand2'
        ).pack(fill='x', padx=20, pady=(0, 20))
    
    def create_or_get_chat(self, fingerprint: str, name: str) -> ChatWindow:
        if fingerprint in self.chat_windows and not self.chat_windows[fingerprint].closed:
            return self.chat_windows[fingerprint]
        stream_id = self.next_stream_id
        self.next_stream_id += 1
        chat_window = ChatWindow(self.root, fingerprint, name, stream_id, self.send_callback)
        self.chat_windows[fingerprint] = chat_window
        self.log(f"Chat opened with {name}", 'success')
        return chat_window
    
    def add_message(self, fingerprint: str, sender: str, message: str, is_me: bool = False):
        if fingerprint in self.chat_windows and not self.chat_windows[fingerprint].closed:
            self.chat_windows[fingerprint].add_message(sender, message, is_me)
        else:
            self.log(f"Message from {sender}: {message[:50]}...", 'info')
    
    def add_system_message(self, fingerprint: str, message: str):
        if fingerprint in self.chat_windows and not self.chat_windows[fingerprint].closed:
            self.chat_windows[fingerprint].add_system_message(message)
