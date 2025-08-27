# ==================================================================
# File: Mani_FAI_Client/agent_app/mt5_manager.py
# Description: کد کامل و نهایی مدیر متاتریدر با تمام قابلیت‌ها.
# ==================================================================
import MetaTrader5 as mt5
import logging
import pandas as pd
import numpy as np


class MT5Manager:
    """
    کلاسی برای مدیریت تمام عملیات مربوط به MetaTrader 5.
    """

    def __init__(self, gui_callback=None):
        """
        سازنده کلاس که حالا یک تابع callback برای ارسال پیام به GUI دریافت می‌کند.
        """
        self.logger = logging.getLogger("AgentApp")
        self.gui_callback = gui_callback
        try:
            if not mt5.initialize():
                self.logger.error(f"initialize() failed, error code = {mt5.last_error()}")
                raise ConnectionError("Failed to initialize MetaTrader 5")
            self.logger.info("MetaTrader 5 initialized successfully.")
        except Exception as e:
            self.log_message(f"Initialization failed: {e}", "critical")
            raise

    def log_message(self, message, level="info"):
        """
        یک تابع کمکی برای لاگ کردن و ارسال پیام به صف GUI.
        """
        log_method = getattr(self.logger, level, self.logger.info)
        log_method(message)

        if self.gui_callback:
            self.gui_callback({"type": "log", "level": level, "message": message})

    def connect(self):
        """
        اطمینان حاصل می‌کند که یک اتصال فعال با ترمینال متاتریدر وجود دارد.
        """
        if not mt5.terminal_info():
            self.log_message("No active terminal connection, trying to re-initialize...", "warning")
            if not mt5.initialize():
                self.log_message(f"re-initialize() failed, error code = {mt5.last_error()}", "error")
                return False
        return True

    def get_account_info(self):
        """
        اطلاعات حساب جاری را به صورت یک دیکشنری برمی‌گرداند.
        """
        if not self.connect():
            return None
        account_info = mt5.account_info()
        if account_info:
            return account_info._asdict()
        self.log_message("Could not retrieve account info.", "error")
        return None

    def get_all_symbols(self):
        """
        تمام نمادهای موجود در Market Watch را به صورت لیستی از دیکشنری‌ها برمی‌گرداند.
        """
        if not self.connect():
            return []
        symbols = mt5.symbols_get()
        if not symbols:
            self.log_message("No symbols found in Market Watch.", "warning")
            return []
        symbols_data = [s._asdict() for s in symbols]
        self.log_message(f"Retrieved {len(symbols_data)} symbols from MT5.", "info")
        return symbols_data

    def get_rates_for_symbol(self, symbol_name, timeframe=mt5.TIMEFRAME_M1, count=100000):
        """
        داده‌های کندل (rates) را برای یک نماد خاص واکشی کرده، پردازش می‌کند و به صورت لیستی از دیکشنری‌ها برمی‌گرداند.
        """
        if not self.connect():
            return None

        try:
            rates = mt5.copy_rates_from_pos(symbol_name, timeframe, 0, count)
            if rates is None or len(rates) == 0:
                self.log_message(f"Could not retrieve rates for {symbol_name}, error: {mt5.last_error()}", "warning")
                return []

            rates_frame = pd.DataFrame(rates)
            rates_frame['time_real'] = pd.to_datetime(rates_frame['time'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')

            for col in ['open', 'high', 'low', 'close']:
                rates_frame[col] = rates_frame[col].astype(float)

            for col in ['tick_volume', 'spread', 'real_volume']:
                rates_frame[col] = rates_frame[col].astype(int)

            rates_data = rates_frame.to_dict('records')

            self.log_message(f"Retrieved and processed {len(rates_data)} rates for symbol {symbol_name}", "info")
            return rates_data

        except Exception as e:
            self.log_message(f"An exception occurred while fetching rates for {symbol_name}: {e}", "error")
            return None

    def disconnect(self):
        """
        اتصال با ترمینال متاتریدر را قطع می‌کند.
        """
        mt5.shutdown()
        self.log_message("Disconnected from MetaTrader 5.", "info")