# ==================================================================
# File: Mani_FAI_Client/agent_app/server.py
# Description: نسخه کامل و نهایی کلاینت ایجنت با تمام قابلیت‌ها.
# ==================================================================
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
            # افزایش حداکثر سایز پیام برای جلوگیری از قطع شدن اتصال
            async with websockets.connect(self.uri, max_size=2**24) as websocket:
                self.websocket = websocket
                self.log_and_gui("Proxy Status: Connected")

                if self.mt5.connect():
                    account_info = self.mt5.get_account_info()
                    if account_info:
                        self.login_number = account_info['login']
                        await self._send_async({"type": "account_info", "data": account_info})
                        self.gui_callback_queue.put({"type": "client_ready", "login": self.login_number})

                async for message in self.websocket:
                    self.handle_message(message)
        except Exception as e:
            self.log_and_gui(f"Connection error: {e}")
        finally:
            self.stop()

    def handle_message(self, message):
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            if msg_type == "db_symbols_list":
                self.logger.info(f"Received {len(data.get('data', []))} symbols from DB.")
                self.gui_callback_queue.put(data)
            else:
                self.logger.info(f"Received message from server: {data}")
        except json.JSONDecodeError:
            self.logger.warning(f"Received non-JSON message: {message}")
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    def run_symbol_sync(self, trigger_type):
        """
        منطق اصلاح شده برای همگام‌سازی زمان‌بندی شده که از ارسال دسته‌ای پشتیبانی می‌کند.
        """
        self.log_and_gui(f"Symbol sync started (Trigger: {trigger_type})")
        def progress_callback(current, total):
            # برای همگام‌سازی زمان‌بندی شده، فقط در لاگ می‌نویسیم و UI را درگیر نمی‌کنیم
            self.logger.info(f"Scheduled sync progress: {current}/{total}")

        # FIX: اصلاح نام متد فراخوانی شده
        symbol_generator = self.mt5.get_all_symbols_in_batches(progress_callback)
        for batch_data in symbol_generator:
            if self.running and batch_data:
                self.send_message({
                    "type": "symbols_info_sync",
                    "login": self.login_number,
                    "symbols": batch_data
                })
        self.log_and_gui("Symbol sync finished.")

    def send_message(self, message):
        if self.running and self.background_loop:
            asyncio.run_coroutine_threadsafe(self._send_async(message), self.background_loop)

    async def _send_async(self, message):
        if not self.websocket:
            return
        try:
            message_to_send = json.dumps(message) if isinstance(message, dict) else message
            await self.websocket.send(message_to_send)
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

    def request_db_symbols(self):
        if not self.login_number:
            self.log_and_gui("Cannot fetch symbols: Login number is unknown.")
            return
        self.log_and_gui("Requesting symbol list from database...")
        self.send_message({
            "type": "get_db_symbols",
            "login": self.login_number
        })

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
        self.logger.info(f"Sent batch of {len(rates_data)} rates for {symbol_name} to the server.")
