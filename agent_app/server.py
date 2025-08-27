# ==================================================================
# File: Mani_FAI_Client/agent_app/server.py
# Description: کد کامل و نهایی کلاینت ایجنت.
# تغییر اصلی: افزودن متد sync_rates_data برای ارسال داده‌های کندل.
# ==================================================================
import asyncio
import websockets
import threading
import json
# ... (بقیه import ها)

class AgentClient:
    # ... (متدهای __init__, set_server_address, log_and_gui, start, _run_client, _run_scheduler, _connect_and_listen, handle_message, trigger_manual_sync, run_symbol_sync, send_message, _send_async, stop, get_status, request_db_symbols بدون تغییر)
    def __init__(self, gui_callback_queue, mt5_manager):
        # ...
        pass
    def set_server_address(self, host, port_str):
        # ...
        pass
    def log_and_gui(self, message):
        # ...
        pass
    def start(self):
        # ...
        pass
    def _run_client(self):
        # ...
        pass
    def _run_scheduler(self):
        # ...
        pass
    async def _connect_and_listen(self):
        # ...
        pass
    def handle_message(self, message):
        # ...
        pass
    def trigger_manual_sync(self):
        # ...
        pass
    def run_symbol_sync(self, trigger_type):
        # ...
        pass
    def send_message(self, message):
        # ...
        pass
    async def _send_async(self, message):
        # ...
        pass
    def stop(self):
        # ...
        pass
    def get_status(self):
        # ...
        pass
    def request_db_symbols(self):
        # ...
        pass

    def sync_rates_data(self, symbol_name, rates_data):
        """
        بسته اطلاعاتی داده‌های کندل را ساخته و برای ارسال به سرور آماده می‌کند.
        """
        if not self.login_number:
            self.log_and_gui("Cannot sync rates data: Login number is unknown.")
            return

        payload = {
            "type": "sync_rates_data",
            "login": self.login_number,
            "symbol": symbol_name,
            "data": rates_data
        }
        self.send_message(payload)
        self.log_and_gui(f"Sent {len(rates_data)} rates for {symbol_name} to the server.")
