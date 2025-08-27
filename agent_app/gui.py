# ==================================================================
# File: agent_app/gui.py
# Description: کد کامل و اصلاح شده.
# تغییر اصلی: on_sync_symbols_click حالا دیکشنری خام را به کلاینت ارسال می‌کند.
# ==================================================================
import tkinter as tk
from tkinter import ttk, font
import sv_ttk
import threading
import queue
import json
from server import AgentClient
from mt5_manager import MT5Manager

# (کلاس SearchableCombobox بدون تغییر باقی می‌ماند)
class SearchableCombobox(ttk.Combobox):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._master_list = []
        self._string_var = self['textvariable']
        if not self._string_var:
            self._string_var = tk.StringVar()
            self['textvariable'] = self._string_var
        self._string_var.trace_add('write', self._on_text_change)
        self.bind('<<ComboboxSelected>>', self._on_selection)
        self._search_job = None
    def set_master_list(self, data_list):
        self._master_list = sorted(data_list) if data_list else []
        self['values'] = self._master_list
    def _on_text_change(self, *args):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(200, self._perform_search)
    def _perform_search(self):
        if not isinstance(self._master_list, (list, tuple)): return
        search_term = self._string_var.get().lower()
        if not search_term:
            filtered_list = self._master_list
        else:
            filtered_list = [item for item in self._master_list if search_term in item.lower()]
        self['values'] = filtered_list
    def _on_selection(self, event):
        if self._search_job:
            self.after_cancel(self._search_job)
            self._search_job = None

class AgentGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Agent Control Panel v3.1")
        self.root.geometry("550x550")
        self.root.resizable(False, False)
        sv_ttk.set_theme("dark")

        self.default_font = font.nametofont("TkDefaultFont")
        self.default_font.configure(family="Segoe UI", size=10)

        self.gui_queue = queue.Queue()
        self.mt5 = MT5Manager(self.gui_queue.put)
        self.client = AgentClient(self.gui_queue, self.mt5)
        self.login_number = None

        self.create_widgets()
        self.process_queue()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)
        address_frame = ttk.LabelFrame(main_frame, text="Proxy Settings", padding=(15, 10))
        address_frame.pack(fill="x", pady=(0, 15))
        address_frame.columnconfigure(1, weight=1)
        ttk.Label(address_frame, text="Proxy IP:").grid(row=0, column=0, padx=(0, 10), pady=5, sticky="w")
        self.ip_entry = ttk.Entry(address_frame, width=30)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.ip_entry.insert(0, "project-proxy.liara.run")
        ttk.Label(address_frame, text="Proxy Port:").grid(row=1, column=0, padx=(0, 10), pady=5, sticky="w")
        self.port_entry = ttk.Entry(address_frame)
        self.port_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.port_entry.insert(0, "443")
        self.set_address_button = ttk.Button(address_frame, text="Set Proxy Address", command=self.set_proxy_address)
        self.set_address_button.grid(row=2, column=0, columnspan=2, pady=(10, 5))
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=(15, 10))
        control_frame.pack(fill="x", pady=(0, 15))
        button_container = ttk.Frame(control_frame)
        button_container.pack(fill="x", expand=True)
        button_container.columnconfigure((0, 1, 2), weight=1)
        self.start_button = ttk.Button(button_container, text="Connect", command=self.start_client, state="disabled")
        self.start_button.grid(row=0, column=0, padx=5, sticky="ew")
        self.stop_button = ttk.Button(button_container, text="Disconnect", command=self.stop_client, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.sync_button = ttk.Button(button_container, text="Sync Symbols", command=self.start_sync_thread, state="disabled")
        self.sync_button.grid(row=0, column=2, padx=5, sticky="ew")
        search_frame = ttk.LabelFrame(main_frame, text="Symbol Search", padding=(15, 10))
        search_frame.pack(fill="x", pady=(0, 15))
        self.symbol_combobox = SearchableCombobox(search_frame, width=40)
        self.symbol_combobox.pack(pady=5, fill="x", expand=True)
        self.symbol_combobox.set("Connect to proxy to load symbols...")
        self.symbol_combobox.state(['disabled'])
        sync_frame = ttk.LabelFrame(main_frame, text="Symbol Synchronization", padding=(15, 10))
        sync_frame.pack(fill="x", pady=(0, 15))
        self.progress_label = ttk.Label(sync_frame, text="Status: Idle", anchor="center")
        self.progress_label.pack(pady=5, fill="x", expand=True)
        self.progress_bar = ttk.Progressbar(sync_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(pady=(5, 10), padx=10, fill="x", expand=True)
        status_frame = ttk.LabelFrame(main_frame, text="System Status", padding=(15, 10))
        status_frame.pack(fill="x")
        self.proxy_status_label = ttk.Label(status_frame, text="Proxy Status: Not connected")
        self.proxy_status_label.pack(anchor="w", padx=5, pady=2)
        self.mt5_status_label = ttk.Label(status_frame, text="MT5 Status: Not connected")
        self.mt5_status_label.pack(anchor="w", padx=5, pady=2)

    def process_queue(self):
        try:
            while not self.gui_queue.empty():
                msg = self.gui_queue.get_nowait()
                if isinstance(msg, dict):
                    msg_type = msg.get("type")
                    if msg_type == "progress_update": self.handle_progress_update(msg)
                    elif msg_type == "client_ready":
                        self.login_number = msg.get("login")
                        self.root.title(f"Agent Control Panel v3.1 - Account: {self.login_number}")
                        self.start_symbol_fetching()
                    elif msg_type == "db_symbols_list": self.handle_db_symbols(msg.get("data", []))
                else:
                    self.handle_status_message(str(msg))
        finally:
            self.root.after(100, self.process_queue)

    def handle_progress_update(self, msg):
        current, total = msg.get("current", 0), msg.get("total", 1)
        if total > 0:
            percentage = (current / total) * 100
            self.progress_bar["value"] = percentage
            self.progress_label.config(text=f"Processing: {current}/{total} symbols ({percentage:.2f}%)")
        if current >= total:
            self.progress_label.config(text=f"Synchronization complete! {total} symbols processed.")
            self.sync_button.config(state="normal")

    def handle_db_symbols(self, symbols):
        if symbols:
            # استخراج فقط نام نمادها برای نمایش در کامبوباکس
            symbol_names = [s.get('name') for s in symbols if s.get('name')]
            self.symbol_combobox.set_master_list(symbol_names)
            self.symbol_combobox.state(['!disabled'])
            self.symbol_combobox.set("Search for a symbol...")
        else:
            self.symbol_combobox.set("No symbols found or error loading.")

    def handle_status_message(self, msg, level="info"):
        log_entry = f"[{level.upper()}] {msg}"
        if "Proxy Status:" in msg: self.proxy_status_label.config(text=msg)
        elif "MT5 Status:" in msg: self.mt5_status_label.config(text=msg)
        else: self.progress_label.config(text=log_entry)

    def set_proxy_address(self):
        self.client.set_server_address(self.ip_entry.get(), self.port_entry.get())
        self.start_button.config(state="normal")
        self.progress_label.config(text="Proxy address set. Ready to connect.")

    def start_client(self):
        self.client.start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.sync_button.config(state="normal")

    def stop_client(self):
        self.client.stop()
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.sync_button.config(state="disabled")
        self.symbol_combobox.set("Connect to proxy to load symbols...")
        self.symbol_combobox.state(['disabled'])
        self.symbol_combobox.set_master_list([])

    def start_sync_thread(self):
        self.progress_label.config(text="Manual sync requested...")
        self.progress_bar["value"] = 0
        self.sync_button.config(state="disabled")
        sync_thread = threading.Thread(target=self.on_sync_symbols_click, daemon=True)
        sync_thread.start()

    def on_sync_symbols_click(self):
        self.handle_status_message("Starting symbol synchronization...")
        all_symbols = self.mt5.get_all_symbols()
        if not all_symbols:
            self.handle_status_message("No symbols found in MT5 to sync.", "warning")
            return
        account_info = self.mt5.get_account_info()
        if not account_info:
            self.handle_status_message("Could not get account info. Cannot sync.", "error")
            return
        login_id = account_info.get('login')
        payload = {
            "type": "symbols_info_sync",
            "login": login_id,
            "symbols": all_symbols
        }
        try:
            # FIX: Send the dictionary directly. The client will handle JSON conversion.
            self.client.send_message(payload)
            self.handle_status_message(f"Successfully sent {len(all_symbols)} symbols to the server.")
        except Exception as e:
            self.handle_status_message(f"Failed to send symbols to server: {e}", "error")

    def start_symbol_fetching(self):
        self.symbol_combobox.set("Loading symbol list from database...")
        fetch_thread = threading.Thread(target=self.client.request_db_symbols, daemon=True)
        fetch_thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = AgentGUI(root)
    root.mainloop()
