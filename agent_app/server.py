# ==================================================================
# File: Mani_FAI_Client/agent_app/server.py (نسخه نهایی با کافکا)
# Description: این کلاس دیگر از WebSocket استفاده نمی‌کند و مستقیماً به کافکا متصل می‌شود.
# ==================================================================
import asyncio
import threading
import json
import aiohttp
import schedule
import time
import pytz
from functools import partial
from aiokafka import AIOKafkaProducer
from logger import setup_logger


class AgentClient:
    def __init__(self, gui_callback_queue, mt5_manager):
        self.logger = setup_logger()
        self.gui_callback_queue = gui_callback_queue
        self.mt5 = mt5_manager
        self.kafka_servers = None
        self.db_handler_url = None  # برای درخواست HTTP
        self.producer = None
        self.running = False
        self.lock = threading.Lock()
        self.login_number = None
        self.background_loop = None

    def set_server_address(self, kafka_servers, db_handler_url):
        self.kafka_servers = kafka_servers
        self.db_handler_url = db_handler_url
        self.log_and_gui(f"Kafka servers set to {self.kafka_servers}")
        self.log_and_gui(f"DB Handler URL set to {self.db_handler_url}")

    def log_and_gui(self, message, level="info"):
        self.gui_callback_queue.put({"type": "log", "level": level, "message": message})

    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self._run_client, daemon=True).start()
        # Scheduler is no longer needed here as sync is manual
        # threading.Thread(target=self._run_scheduler, daemon=True).start()

    def _run_client(self):
        self.background_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.background_loop)
        self.background_loop.run_until_complete(self._connect_and_run())

    async def _connect_and_run(self):
        try:
            self.producer = AIOKafkaProducer(bootstrap_servers=self.kafka_servers)
            await self.producer.start()
            self.log_and_gui("Kafka Producer Status: Connected", "info")

            if self.mt5.connect():
                account_info = self.mt5.get_account_info()
                if account_info:
                    self.login_number = account_info['login']
                    # Send initial account info
                    await self._send_to_kafka(
                        "account_info",
                        {"type": "account_info", "login": self.login_number, "data": account_info}
                    )
                    # Notify GUI that client is ready
                    self.gui_callback_queue.put({"type": "client_ready", "login": self.login_number})

            # Keep the asyncio loop running in the background
            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            self.log_and_gui(f"Kafka connection error: {e}", "error")
        finally:
            self.stop()

    def send_message(self, topic, message):
        """Schedules a message to be sent to a Kafka topic."""
        if self.running and self.background_loop:
            asyncio.run_coroutine_threadsafe(self._send_to_kafka(topic, message), self.background_loop)

    async def _send_to_kafka(self, topic, message):
        """Sends a single message to a Kafka topic."""
        if not self.producer:
            self.log_and_gui("Cannot send message, Kafka producer is not running.", "error")
            return
        try:
            message_bytes = json.dumps(message).encode('utf-8')
            await self.producer.send_and_wait(topic, message_bytes)
        except Exception as e:
            self.log_and_gui(f"Kafka send error to topic '{topic}': {e}", "error")

    def stop(self):
        with self.lock:
            if not self.running: return
            self.running = False
            if self.producer:
                asyncio.run_coroutine_threadsafe(self.producer.stop(), self.background_loop)
            if self.background_loop:
                self.background_loop.call_soon_threadsafe(self.background_loop.stop)
            self.mt5.disconnect()
            self.log_and_gui("Client stopped", "info")

    async def _request_db_symbols_async(self):
        """Fetches the initial symbol list via HTTP."""
        if not self.login_number:
            self.log_and_gui("Cannot fetch symbols: Login number is unknown.", "error")
            return

        url = f"{self.db_handler_url}/get_symbols/{self.login_number}"
        self.log_and_gui(f"Requesting symbol list from {url}...", "info")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.logger.info(f"Received {len(data)} symbols from DB.")
                        self.gui_callback_queue.put({"type": "db_symbols_list", "data": data})
                    else:
                        self.log_and_gui(f"Error fetching symbols: HTTP {response.status}", "error")
                        self.gui_callback_queue.put({"type": "db_symbols_list", "data": []})
        except Exception as e:
            self.log_and_gui(f"HTTP connection error: {e}", "error")
            self.gui_callback_queue.put({"type": "db_symbols_list", "data": []})

    def request_db_symbols(self):
        """Triggers the async request for the symbol list."""
        if self.running and self.background_loop:
            asyncio.run_coroutine_threadsafe(self._request_db_symbols_async(), self.background_loop)

    def sync_symbols_in_batches(self, symbol_batches_generator):
        """Sends symbol data in batches to Kafka."""
        for batch in symbol_batches_generator:
            payload = {"type": "symbols_info_sync", "login": self.login_number, "symbols": batch}
            self.send_message("symbols_info_sync", payload)

    def sync_rates_data_in_batches(self, symbol_name, rates_batches_generator):
        """Sends historical rates data in batches to Kafka."""
        for batch in rates_batches_generator:
            payload = {"type": "sync_rates_data", "login": self.login_number, "symbol": symbol_name, "data": batch}
            self.send_message("sync_rates_data", payload)