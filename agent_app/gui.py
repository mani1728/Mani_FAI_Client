import tkinter as tk
from tkinter import ttk, font
import sv_ttk
import threading
import queue
import json
from server import AgentClient
from mt5_manager import MT5Manager


# ==============================================================================
# بخش ۱: کامپوننت سفارشی SearchableCombobox
# ==============================================================================
class SearchableCombobox(ttk.Combobox):
    """
    یک ویجت ttk.Combobox که قابلیت جستجوی زنده و case-insensitive را اضافه می‌کند.
    """

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
        """
        لیست اصلی داده‌ها را برای جستجو تنظیم می‌کند.
        """
        self._master_list = sorted(data_list) if data_list else []
        self['values'] = self._master_list

    def _on_text_change(self, *args):
        """
        با هر تغییر در متن ورودی، جستجو را با تاخیر (debounce) اجرا می‌کند.
        """
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(200, self._perform_search)

    def _perform_search(self):
        """
        منطق اصلی فیلتر کردن و به‌روزرسانی لیست را اجرا می‌کند.
        """
        if not isinstance(self._master_list, (list, tuple)):
            return
        search_term = self._string_var.get().lower()
        if not search_term:
            filtered_list = self._master_list
        else:
            filtered_list = [
                item for item in self._master_list
                if search_term in item.lower()
            ]
        self['values'] = filtered_list
        if filtered_list:
            pass

    def _on_selection(self, event):
        """
        پس از انتخاب یک آیتم، جستجوی بیشتر را متوقف می‌کند.
        """
        if self._search_job:
            self.after_cancel(self._search_job)
            self._search_job = None


# ==============================================================================
# بخش ۲: کلاس اصلی برنامه GUI
# ==============================================================================
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

        # --- بخش تنظیمات پراکسی ---
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

        # --- بخش کنترل‌ها ---
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=(15, 10))
        control_frame.pack(fill="x", pady=(0, 15))
        button_container = ttk.Frame(control_frame)
        button_container.pack(fill="x", expand=True)
        button_container.columnconfigure((0, 1, 2), weight=1)
        self.start_button = ttk.Button(button_container, text="Connect", command=self.start_client, state="disabled")
        self.start_button.grid(row=0, column=0, padx=5, sticky="ew")
        self.stop_button = ttk.Button(button_container, text="Disconnect", command=self.stop_client, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.sync_button = ttk.Button(button_container, text="Sync Symbols", command=self.start_sync_thread,
                                      state="disabled")
        self.sync_button.grid(row=0, column=2, padx=5, sticky="ew")

        # --- بخش جستجوی نماد ---
        search_frame = ttk.LabelFrame(main_frame, text="Symbol Search", padding=(15, 10))
        search_frame.pack(fill="x", pady=(0, 15))
        self.symbol_combobox = SearchableCombobox(search_frame, width=40)
        self.symbol_combobox.pack(pady=5, fill="x", expand=True)
        self.symbol_combobox.set("Connect to proxy to load symbols...")
        self.symbol_combobox.state(['disabled'])

        # --- بخش همگام‌سازی ---
        sync_frame = ttk.LabelFrame(main_frame, text="Symbol Synchronization", padding=(15, 10))
        sync_frame.pack(fill="x", pady=(0, 15))
        self.progress_label = ttk.Label(sync_frame, text="Status: Idle", anchor="center")
        self.progress_label.pack(pady=5, fill="x", expand=True)
        self.progress_bar = ttk.Progressbar(sync_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(pady=(5, 10), padx=10, fill="x", expand=True)

        # --- بخش وضعیت کلی ---
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
                    if msg_type == "progress_update":
                        self.handle_progress_update(msg)
                    elif msg_type == "client_ready":
                        self.login_number = msg.get("login")
                        self.root.title(f"Agent Control Panel v3.1 - Account: {self.login_number}")
                        self.start_symbol_fetching()
                    elif msg_type == "db_symbols_list":
                        self.handle_db_symbols(msg.get("data", []))
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
            self.symbol_combobox.set_master_list(symbols)
            self.symbol_combobox.state(['!disabled'])
            self.symbol_combobox.set("Search for a symbol...")
        else:
            self.symbol_combobox.set("No symbols found or error loading.")

    def handle_status_message(self, msg, level="info"):
        """
        نمایش پیام‌ها در رابط کاربری با سطح اهمیت (info, warning, error).
        """
        log_entry = f"[{level.upper()}] {msg}"
        if "Proxy Status:" in msg:
            self.proxy_status_label.config(text=msg)
        elif "MT5 Status:" in msg:
            self.mt5_status_label.config(text=msg)
        else:
            self.progress_label.config(text=log_entry)

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
        """
        برای جلوگیری از فریز شدن رابط کاربری، عملیات همگام‌سازی را در یک ترد جدید اجرا می‌کند.
        """
        self.progress_label.config(text="Manual sync requested...")
        self.progress_bar["value"] = 0
        self.sync_button.config(state="disabled")
        sync_thread = threading.Thread(target=self.on_sync_symbols_click, daemon=True)
        sync_thread.start()

    def on_sync_symbols_click(self):
        """
        این تابع زمانی اجرا می‌شود که کاربر روی دکمه Sync Symbols کلیک می‌کند.
        این تابع مسئول جمع‌آوری تمام نمادها و ارسال آن‌ها در یک درخواست واحد است.
        """
        self.handle_status_message("Starting symbol synchronization...")

        # 1. دریافت اطلاعات کامل تمام نمادها از متاتریدر
        all_symbols = self.mt5.get_all_symbols()
        if not all_symbols:
            self.handle_status_message("No symbols found in MT5 to sync.", "warning")
            return

        # 2. دریافت اطلاعات حساب برای به دست آوردن login_id
        account_info = self.mt5.get_account_info()
        if not account_info:
            self.handle_status_message("Could not get account info. Cannot sync.", "error")
            return

        login_id = account_info.get('login')

        # 3. ساختاردهی داده‌ها در فرمت صحیح مورد انتظار سرور
        payload = {
            "type": "symbols_info_sync",
            "login": login_id,
            "symbols": all_symbols
        }

        # 4. ارسال بسته کامل به پراکسی سرور
        try:
            message_str = json.dumps(payload)
            self.client.send_message(message_str)
            self.handle_status_message(
                f"Successfully sent {len(all_symbols)} symbols to the server for synchronization.")
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