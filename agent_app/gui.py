# ==================================================================
# File: Mani_FAI_Client/agent_app/gui.py
# Description: کد کامل و نهایی رابط کاربری.
# تغییر اصلی: پیاده‌سازی منطق برای رویداد انتخاب از کامبوباکس.
# ==================================================================
import tkinter as tk
from tkinter import ttk, font
import sv_ttk
import threading
import queue
import json
from server import AgentClient
from mt5_manager import MT5Manager


# (کلاس SearchableCombobox بدون تغییر باقی می‌ماند، به جز یک تغییر کوچک)
class SearchableCombobox(ttk.Combobox):
    def __init__(self, master=None, on_select_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self._master_list = []
        self._string_var = self['textvariable']
        if not self._string_var:
            self._string_var = tk.StringVar()
            self['textvariable'] = self._string_var
        self._string_var.trace_add('write', self._on_text_change)
        self.bind('<<ComboboxSelected>>', self._on_selection)
        self._search_job = None
        # *** FIX: یک callback برای رویداد انتخاب اضافه می‌کنیم ***
        self.on_select_callback = on_select_callback

    # ... (متدهای set_master_list, _on_text_change, _perform_search بدون تغییر)
    def set_master_list(self, data_list):
        # ...
        pass

    def _on_text_change(self, *args):
        # ...
        pass

    def _perform_search(self):
        # ...
        pass

    def _on_selection(self, event):
        """
        پس از انتخاب یک آیتم، تابع callback را با مقدار انتخاب شده فراخوانی می‌کند.
        """
        if self._search_job:
            self.after_cancel(self._search_job)
            self._search_job = None

        selected_value = self._string_var.get()
        if self.on_select_callback:
            self.on_select_callback(selected_value)


class AgentGUI:
    def __init__(self, root):
        # ... (بخش __init__ بدون تغییر)
        pass

    def create_widgets(self):
        # ... (بخش create_widgets بدون تغییر، به جز ساخت کامبوباکس)
        search_frame = ttk.LabelFrame(main_frame, text="Symbol Search", padding=(15, 10))
        search_frame.pack(fill="x", pady=(0, 15))

        # *** FIX: کامبوباکس حالا متد on_symbol_selected را به عنوان callback دریافت می‌کند ***
        self.symbol_combobox = SearchableCombobox(search_frame, width=40, on_select_callback=self.on_symbol_selected)

        self.symbol_combobox.pack(pady=5, fill="x", expand=True)
        self.symbol_combobox.set("Connect to proxy to load symbols...")
        self.symbol_combobox.state(['disabled'])
        # ... (بقیه ویجت‌ها)

    # ... (بقیه متدهای GUI بدون تغییر)
    def process_queue(self):
        # ...
        pass

    def handle_progress_update(self, msg):
        # ...
        pass

    def handle_db_symbols(self, symbols):
        # ...
        pass

    def handle_status_message(self, msg, level="info"):
        # ...
        pass

    def set_proxy_address(self):
        # ...
        pass

    def start_client(self):
        # ...
        pass

    def stop_client(self):
        # ...
        pass

    def start_sync_thread(self):
        # ...
        pass

    def on_sync_symbols_click(self):
        # ...
        pass

    def start_symbol_fetching(self):
        # ...
        pass

    def on_symbol_selected(self, symbol_name):
        """
        این متد زمانی فراخوانی می‌شود که کاربر یک نماد را از کامبوباکس انتخاب کند.
        """
        if not symbol_name or "Search for" in symbol_name:
            return

        self.handle_status_message(f"Symbol '{symbol_name}' selected. Fetching historical rates...", "info")
        # اجرای فرآیند در یک ترد جدید برای جلوگیری از فریز شدن UI
        threading.Thread(target=self._fetch_and_sync_rates_data, args=(symbol_name,), daemon=True).start()

    def _fetch_and_sync_rates_data(self, symbol_name):
        """
        منطق واکشی و ارسال داده‌های کندل را در یک ترد پس‌زمینه اجرا می‌کند.
        """
        # 1. واکشی و پردازش داده‌ها از متاتریدر
        rates_data = self.mt5.get_rates_for_symbol(symbol_name)

        if rates_data is None:  # None یعنی خطای جدی رخ داده است
            self.handle_status_message(f"Failed to fetch historical rates for {symbol_name}.", "error")
            return

        if not rates_data:  # لیست خالی یعنی کندلی پیدا نشده است
            self.handle_status_message(f"No historical rates found for {symbol_name}.", "warning")
            return

        # 2. ارسال داده‌ها به سرور از طریق کلاینت
        self.client.sync_rates_data(symbol_name, rates_data)


if __name__ == "__main__":
    root = tk.Tk()
    app = AgentGUI(root)
    root.mainloop()
