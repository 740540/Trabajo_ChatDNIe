"""Modern GUI for DNI-IM using tkinter - Dark Theme"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Dict, Callable, Optional
import threading
from datetime import datetime


# Modern dark theme colors - Telegram style
COLORS = {
    'bg_dark': '#0E1621',           # Fondo principal más oscuro
    'bg_secondary': '#17212B',      # Fondo secundario
    'bg_chat': '#0E1621',           # Fondo del chat
    'bg_input': '#17212B',          # Fondo del input
    'bg_message_me': '#2B5278',     # Burbujas propias (azul Telegram)
    'bg_message_them': '#182533',   # Burbujas de otros
    'text_primary': '#FFFFFF',      # Texto principal
    'text_secondary': '#707579',    # Texto secundario
    'text_me': '#FFFFFF',           # Texto en burbujas propias
    'text_them': '#FFFFFF',         # Texto en burbujas de otros
    'accent': '#5288C1',            # Azul Telegram
    'accent_hover': '#6BA3D8',      # Azul hover
    'accent_dark': '#3E6FA3',       # Azul oscuro
    'border': '#2B3843',            # Bordes
    'system': '#707579',            # Mensajes del sistema
    'online': '#4DCD5E',            # Verde online
    'hover': '#1E2A35',             # Hover en lista
}


class ChatWindow(tk.Toplevel):
    def __init__(self, parent, fingerprint: str, name: str, stream_id: int, send_callback: Callable):
        super().__init__(parent)
        self.fingerprint = fingerprint
        self.name = name
        self.stream_id = stream_id
        self.send_callback = send_callback
        self.title(f"Chat with {name}")
        self.geometry("800x650")
        self.configure(bg=COLORS['bg_dark'])
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Header con sombra
        header = tk.Frame(self, bg=COLORS['bg_secondary'], height=70)
        header.grid(row=0, column=0, sticky='ew')
        header.grid_propagate(False)
        
        # Avatar circular simulado
        avatar_frame = tk.Frame(header, bg=COLORS['accent'], width=45, height=45)
        avatar_frame.pack(side='left', padx=15, pady=12)
        avatar_frame.pack_propagate(False)
        tk.Label(avatar_frame, text=name[0].upper(), font=('Segoe UI', 18, 'bold'),
                bg=COLORS['accent'], fg='white').place(relx=0.5, rely=0.5, anchor='center')
        
        # Info del contacto
        info_frame = tk.Frame(header, bg=COLORS['bg_secondary'])
        info_frame.pack(side='left', fill='y', pady=12)
        tk.Label(info_frame, text=name, font=('Segoe UI', 13, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], anchor='w'
        ).pack(anchor='w')
        tk.Label(info_frame, text=f"🔒 {fingerprint[:16]}...", font=('Segoe UI', 9),
                bg=COLORS['bg_secondary'], fg=COLORS['text_secondary'], anchor='w'
        ).pack(anchor='w')
        
        chat_frame = tk.Frame(self, bg=COLORS['bg_chat'])
        chat_frame.grid(row=1, column=0, sticky='nsew')
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, state='disabled', font=('Segoe UI', 11),
            bg=COLORS['bg_chat'], fg=COLORS['text_primary'], padx=20, pady=20,
            borderwidth=0, highlightthickness=0, insertbackground=COLORS['text_primary']
        )
        self.chat_display.grid(row=0, column=0, sticky='nsew')
        
        # Burbujas con bordes redondeados simulados
        self.chat_display.tag_config('me_bubble', background=COLORS['bg_message_me'],
            foreground=COLORS['text_me'], font=('Segoe UI', 11),
            lmargin1=250, lmargin2=250, rmargin=30, spacing1=8, spacing3=8,
            relief='flat', borderwidth=0)
        self.chat_display.tag_config('them_bubble', background=COLORS['bg_message_them'],
            foreground=COLORS['text_them'], font=('Segoe UI', 11),
            lmargin1=30, lmargin2=30, rmargin=250, spacing1=8, spacing3=8,
            relief='flat', borderwidth=0)
        self.chat_display.tag_config('system', foreground=COLORS['system'],
            font=('Segoe UI', 9, 'italic'), justify='center', spacing1=12, spacing3=12)
        self.chat_display.tag_config('timestamp', foreground=COLORS['text_secondary'],
            font=('Segoe UI', 9))
        
        # Input con diseño moderno
        input_container = tk.Frame(self, bg=COLORS['bg_dark'])
        input_container.grid(row=2, column=0, sticky='ew', padx=15, pady=15)
        input_container.grid_columnconfigure(0, weight=1)
        
        # Frame con borde redondeado simulado
        input_outer = tk.Frame(input_container, bg=COLORS['border'])
        input_outer.grid(row=0, column=0, sticky='ew', padx=2, pady=2)
        input_outer.grid_columnconfigure(0, weight=1)
        
        input_frame = tk.Frame(input_outer, bg=COLORS['bg_input'])
        input_frame.grid(row=0, column=0, sticky='ew', padx=1, pady=1)
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.message_input = tk.Text(input_frame, height=2, font=('Segoe UI', 11),
            wrap=tk.WORD, bg=COLORS['bg_input'], fg=COLORS['text_primary'],
            insertbackground=COLORS['accent'], borderwidth=0,
            highlightthickness=0, padx=15, pady=12)
        self.message_input.grid(row=0, column=0, sticky='ew')
        self.message_input.bind('<Return>', self._on_enter)
        self.message_input.bind('<Shift-Return>', lambda e: None)
        
        # Botón de enviar circular
        btn_container = tk.Frame(input_frame, bg=COLORS['bg_input'])
        btn_container.grid(row=0, column=1, padx=8)
        self.send_button = tk.Button(btn_container, text="▶", command=self._send_message,
            font=('Segoe UI', 12, 'bold'), bg=COLORS['accent'], fg='white',
            activebackground=COLORS['accent_hover'], activeforeground='white',
            borderwidth=0, width=3, height=1, cursor='hand2', relief='flat')
        self.send_button.pack()
        
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
        
        # Añadir espacio entre mensajes
        self.chat_display.insert(tk.END, '\n')
        
        # Mensaje con timestamp en la misma línea
        full_message = f"{message}    {timestamp}"
        self.chat_display.insert(tk.END, full_message + '\n', tag)
        
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
    def __init__(self, my_name: str, my_photo: Optional[bytes] = None, my_dni: Optional[str] = None):
        self.my_name = my_name
        self.my_photo = my_photo
        self.my_dni = my_dni
        self.root = tk.Tk()
        self.root.title("DNI-IM - Secure Messaging")
        self.root.geometry("1000x700")
        self.root.configure(bg=COLORS['bg_dark'])
        self.chat_windows: Dict[str, ChatWindow] = {}
        self.next_stream_id = 1
        self.send_callback: Optional[Callable] = None
        self.photo_image = None  # Para mantener referencia a la imagen
        self._create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.running = True
    
    def _create_widgets(self):
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        
        left_panel = tk.Frame(self.root, width=360, bg=COLORS['bg_secondary'])
        left_panel.grid(row=0, column=0, sticky='nsew')
        left_panel.grid_propagate(False)
        
        # Header con gradiente simulado
        header = tk.Frame(left_panel, bg=COLORS['bg_secondary'], height=80)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        title_frame = tk.Frame(header, bg=COLORS['bg_secondary'])
        title_frame.pack(side='left', padx=20, pady=20)
        tk.Label(title_frame, text="🔐 DNI-IM", font=('Segoe UI', 20, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_primary']
        ).pack(anchor='w')
        tk.Label(title_frame, text="Secure Messaging", font=('Segoe UI', 9),
                bg=COLORS['bg_secondary'], fg=COLORS['text_secondary']
        ).pack(anchor='w')
        
        # Tarjeta de usuario con diseño moderno
        user_card = tk.Frame(left_panel, bg=COLORS['bg_dark'])
        user_card.pack(fill='x', padx=12, pady=12)
        
        user_inner = tk.Frame(user_card, bg=COLORS['bg_dark'])
        user_inner.pack(fill='x', padx=15, pady=15)
        
        # Avatar circular del usuario (foto del DNIe o inicial)
        avatar_bg = tk.Frame(user_inner, bg=COLORS['accent'], width=50, height=50)
        avatar_bg.pack(side='left', padx=(0, 12))
        avatar_bg.pack_propagate(False)
        
        if self.my_photo:
            # Mostrar foto del DNIe
            try:
                from PIL import Image, ImageTk
                import io
                
                # Cargar imagen desde bytes
                image = Image.open(io.BytesIO(self.my_photo))
                # Redimensionar a 50x50 y hacer circular
                image = image.resize((50, 50), Image.Resampling.LANCZOS)
                self.photo_image = ImageTk.PhotoImage(image)
                
                tk.Label(avatar_bg, image=self.photo_image, bg=COLORS['accent']
                ).place(relx=0.5, rely=0.5, anchor='center')
            except Exception as e:
                print(f"Error loading photo: {e}")
                # Fallback a inicial
                tk.Label(avatar_bg, text=self.my_name[0].upper() if self.my_name else "U", 
                        font=('Segoe UI', 20, 'bold'),
                        bg=COLORS['accent'], fg='white').place(relx=0.5, rely=0.5, anchor='center')
        else:
            # Mostrar inicial
            tk.Label(avatar_bg, text=self.my_name[0].upper() if self.my_name else "U", 
                    font=('Segoe UI', 20, 'bold'),
                    bg=COLORS['accent'], fg='white').place(relx=0.5, rely=0.5, anchor='center')
        
        # Info del usuario
        user_info = tk.Frame(user_inner, bg=COLORS['bg_dark'])
        user_info.pack(side='left', fill='both', expand=True)
        
        self.user_label = tk.Label(user_info, text=self.my_name,
                                   font=('Segoe UI', 12, 'bold'),
                                   bg=COLORS['bg_dark'], fg=COLORS['text_primary'], anchor='w')
        self.user_label.pack(fill='x')
        
        # Mostrar DNI si está disponible
        if self.my_dni:
            tk.Label(user_info, text=f"DNI: {self.my_dni}", font=('Segoe UI', 9),
                    bg=COLORS['bg_dark'], fg=COLORS['text_secondary'], anchor='w').pack(fill='x')
        
        status_frame = tk.Frame(user_info, bg=COLORS['bg_dark'])
        status_frame.pack(fill='x')
        tk.Label(status_frame, text="●", font=('Segoe UI', 8),
                bg=COLORS['bg_dark'], fg=COLORS['online']).pack(side='left')
        tk.Label(status_frame, text=" online", font=('Segoe UI', 9),
                bg=COLORS['bg_dark'], fg=COLORS['text_secondary']).pack(side='left')
        
        self.fingerprint_label = tk.Label(user_info, text="", font=('Segoe UI', 8),
                                          bg=COLORS['bg_dark'], fg=COLORS['text_secondary'], anchor='w')
        self.fingerprint_label.pack(fill='x', pady=(2, 0))
        
        # Separador
        tk.Frame(left_panel, bg=COLORS['border'], height=1).pack(fill='x', padx=12)
        
        peers_header = tk.Frame(left_panel, bg=COLORS['bg_secondary'])
        peers_header.pack(fill='x', padx=15, pady=(15, 8))
        tk.Label(peers_header, text="CONTACTS", font=('Segoe UI', 10, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_secondary']
        ).pack(side='left')
        
        refresh_btn = tk.Button(peers_header, text="⟳", font=('Segoe UI', 14),
                 bg=COLORS['bg_secondary'], fg=COLORS['text_secondary'],
                 activebackground=COLORS['hover'], activeforeground=COLORS['accent'],
                 borderwidth=0, cursor='hand2', command=self._refresh_peers,
                 relief='flat')
        refresh_btn.pack(side='right')
        
        # Hover effect
        def on_enter(e):
            refresh_btn.config(bg=COLORS['hover'], fg=COLORS['accent'])
        def on_leave(e):
            refresh_btn.config(bg=COLORS['bg_secondary'], fg=COLORS['text_secondary'])
        refresh_btn.bind('<Enter>', on_enter)
        refresh_btn.bind('<Leave>', on_leave)
        
        peers_container = tk.Frame(left_panel, bg=COLORS['bg_secondary'])
        peers_container.pack(fill='both', expand=True, padx=12, pady=5)
        
        peers_scroll = tk.Scrollbar(peers_container, bg=COLORS['bg_secondary'],
                                   troughcolor=COLORS['bg_secondary'])
        peers_scroll.pack(side='right', fill='y')
        
        self.peers_listbox = tk.Listbox(peers_container, yscrollcommand=peers_scroll.set,
            font=('Segoe UI', 11), bg=COLORS['bg_secondary'], fg=COLORS['text_primary'],
            selectbackground=COLORS['accent'], selectforeground='white',
            activestyle='none', borderwidth=0, highlightthickness=0,
            selectmode='single')
        self.peers_listbox.pack(fill='both', expand=True)
        peers_scroll.config(command=self.peers_listbox.yview)
        self.peers_listbox.bind('<Double-Button-1>', self._on_peer_double_click)
        
        # Hover effect en la lista
        self.peers_listbox.bind('<Motion>', self._on_peer_hover)
        
        # Botones con diseño moderno
        button_frame = tk.Frame(left_panel, bg=COLORS['bg_secondary'])
        button_frame.pack(fill='x', padx=12, pady=12)
        
        # Botón principal (Add Peer)
        add_btn = tk.Button(button_frame, text="➕  Add Peer",
                 command=self._show_add_peer_dialog, font=('Segoe UI', 11, 'bold'),
                 bg=COLORS['accent'], fg='white',
                 activebackground=COLORS['accent_hover'], activeforeground='white',
                 borderwidth=0, pady=14, cursor='hand2', relief='flat')
        add_btn.pack(fill='x', pady=(0, 8))
        
        # Botones secundarios en fila
        btn_row = tk.Frame(button_frame, bg=COLORS['bg_secondary'])
        btn_row.pack(fill='x')
        
        contacts_btn = tk.Button(btn_row, text="📋 Contacts",
                 command=self._show_contacts, font=('Segoe UI', 10),
                 bg=COLORS['bg_dark'], fg=COLORS['text_primary'],
                 activebackground=COLORS['hover'], activeforeground=COLORS['text_primary'],
                 borderwidth=0, pady=12, cursor='hand2', relief='flat')
        contacts_btn.pack(side='left', fill='x', expand=True, padx=(0, 4))
        
        delete_btn = tk.Button(btn_row, text="🗑️ Delete",
                 command=self._delete_peer, font=('Segoe UI', 10),
                 bg=COLORS['bg_dark'], fg='#FF6B6B',
                 activebackground='#8B0000', activeforeground='white',
                 borderwidth=0, pady=12, cursor='hand2', relief='flat')
        delete_btn.pack(side='left', fill='x', expand=True, padx=(4, 0))
        
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
        
        # Panel derecho con diseño mejorado
        right_panel = tk.Frame(self.root, bg=COLORS['bg_chat'])
        right_panel.grid(row=0, column=1, sticky='nsew')
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)
        
        # Header del log
        log_header = tk.Frame(right_panel, bg=COLORS['bg_secondary'], height=80)
        log_header.grid(row=0, column=0, sticky='ew')
        log_header.grid_propagate(False)
        
        header_content = tk.Frame(log_header, bg=COLORS['bg_secondary'])
        header_content.pack(side='left', padx=20, pady=20)
        tk.Label(header_content, text="📊 System Log", font=('Segoe UI', 14, 'bold'),
                bg=COLORS['bg_secondary'], fg=COLORS['text_primary']
        ).pack(anchor='w')
        tk.Label(header_content, text="Real-time activity monitor", font=('Segoe UI', 9),
                bg=COLORS['bg_secondary'], fg=COLORS['text_secondary']
        ).pack(anchor='w')
        
        # Contenedor del log con padding
        log_container = tk.Frame(right_panel, bg=COLORS['bg_chat'])
        log_container.grid(row=1, column=0, sticky='nsew', padx=20, pady=20)
        log_container.grid_rowconfigure(0, weight=1)
        log_container.grid_columnconfigure(0, weight=1)
        
        # Log display con diseño moderno
        self.log_display = scrolledtext.ScrolledText(log_container, wrap=tk.WORD,
            state='disabled', font=('Consolas', 10), bg=COLORS['bg_dark'],
            fg=COLORS['text_primary'], padx=20, pady=20, borderwidth=0,
            highlightthickness=0, insertbackground=COLORS['text_primary'])
        self.log_display.grid(row=0, column=0, sticky='nsew')
        
        # Tags con colores mejorados
        self.log_display.tag_config('info', foreground=COLORS['text_secondary'])
        self.log_display.tag_config('success', foreground='#4DCD5E', font=('Consolas', 10, 'bold'))
        self.log_display.tag_config('error', foreground='#FF6B6B', font=('Consolas', 10, 'bold'))
        self.log_display.tag_config('warning', foreground='#FFD93D', font=('Consolas', 10, 'bold'))
    
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
    
    def _on_peer_hover(self, event):
        """Efecto hover en la lista de peers"""
        pass  # El efecto se maneja con selectbackground
    
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
