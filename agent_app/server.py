# C:\...\windows_agent_project\client\agent_app\server.py

import asyncio
import websockets
import threading
import json
import schedule
import time
import pytz
from functools import partial
from logger import setup_logger


class AgentClient:
    def __init__(self, gui_callback_queue, mt5_manager):
        self.logger = setup_logger()
        self.gui_callback_queue = gui_callback_queue
        self.mt5 = mt5_manager
        self.uri = None
        self.websocket = None
        self.running = False
        self.lock = threading.Lock()
        self.login_number = None
        self.background_loop = None

    def set_server_address(self, host, port_str):
        try:
            port = int(port_str)
            protocol = "wss" if port == 443 else "ws"
            self.uri = f"{protocol}://{host}" if protocol == "wss" else f"{protocol}://{host}:{port}"
            self.log_and_gui(f"Proxy address set to {self.uri}")
        except ValueError:
            self.log_and_gui("Invalid port number.")

    def log_and_gui(self, message):
        self.gui_callback_queue.put(message)

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._run_client, daemon=True).start()
        threading.Thread(target=self._run_scheduler, daemon=True).start()

    def _run_client(self):
        self.background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.background_loop)
        self.background_loop.run_until_complete(self._connect_and_listen())

    def _run_scheduler(self):
        tehran_tz = pytz.timezone("Asia/Tehran")
        job = partial(self.run_symbol_sync, "Scheduled")
        schedule.every().saturday.at("20:00", tehran_tz).do(job)
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    async def _connect_and_listen(self):
        try:
            async with websockets.connect(self.uri) as websocket:
                self.websocket = websocket
                self.log_and_gui("Proxy Status: Connected")

                if self.mt5.connect():
                    account_info = self.mt5.get_account_info()
                    if account_info:
                        self.login_number = account_info['login']
                        await self._send_async({"type": "account_info", "data": account_info})
                        # 🎯 به محض اتصال، به GUI اطلاع می‌دهیم که آماده است
                        self.gui_callback_queue.put({"type": "client_ready", "login": self.login_number})

                # 🎯 حلقه فعال برای گوش دادن به پیام‌های سرور
                async for message in websocket:
                    self.handle_message(message)

        except Exception as e:
            self.log_and_gui(f"Connection error: {e}")
        finally:
            self.stop()

    def handle_message(self, message):
        """پیام‌های دریافتی از پراکسی را مدیریت می‌کند."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "db_symbols_list":
                self.logger.info(f"Received {len(data.get('data', ))} symbols from DB.")
                self.gui_callback_queue.put(data)
            # 🎯 سایر انواع پیام را می‌توان در اینجا مدیریت کرد
            else:
                self.logger.info(f"Received message from server: {data}")

        except json.JSONDecodeError:
            self.logger.warning(f"Received non-JSON message: {message}")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    def trigger_manual_sync(self):
        if self.running and self.mt5.connected:
            self.log_and_gui("Starting manual symbol sync...")
            threading.Thread(target=self.run_symbol_sync, args=("Manual",), daemon=True).start()
        else:
            self.log_and_gui("Cannot sync: Not connected to proxy or MT5.")

    def run_symbol_sync(self, trigger_type):
        self.log_and_gui(f"Symbol sync started (Trigger: {trigger_type})")

        def progress_callback(current, total):
            self.gui_callback_queue.put({"type": "progress_update", "current": current, "total": total})

        symbol_generator = self.mt5.sync_all_symbols_in_batches(progress_callback)
        for batch_data in symbol_generator:
            if self.running and batch_data:
                self.send_message({
                    "type": "symbols_info_sync",
                    "login": self.login_number,
                    "data": batch_data
                })
        self.log_and_gui("Symbol sync finished.")

    def send_message(self, message):
        if self.running and self.background_loop:
            asyncio.run_coroutine_threadsafe(self._send_async(message), self.background_loop)

    async def _send_async(self, message):
        if not self.websocket:
            return
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            self.log_and_gui(f"Send error: {e}")

    def stop(self):
        with self.lock:
            if not self.running:
                return
            self.running = False
            if self.background_loop:
                self.background_loop.call_soon_threadsafe(self.background_loop.stop)
            self.mt5.disconnect()
            self.log_and_gui("Client stopped")

    def get_status(self):
        return "Connected" if self.running and self.websocket else "Not connected"

    # 🎯 متد جدید برای درخواست لیست نمادها از پراکسی
    def request_db_symbols(self):
        """درخواستی برای دریافت لیست نام نمادها از دیتابیس به پراکسی ارسال می‌کند."""
        if not self.login_number:
            self.log_and_gui("Cannot fetch symbols: Login number is unknown.")
            return

        self.log_and_gui("Requesting symbol list from database...")
        self.send_message({
            "type": "get_db_symbols",
            "login": self.login_number
        })