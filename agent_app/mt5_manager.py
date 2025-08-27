# ==================================================================
# File: Mani_FAI_Client/agent_app/mt5_manager.py
# Description: نسخه کامل و نهایی مدیر متاتریدر با تمام قابلیت‌ها.
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

    def get_all_symbols_in_batches(self, progress_callback, batch_size=500):
        """
        تمام نمادها را به صورت دسته‌ای (batch) واکشی و yield می‌کند تا از ارسال پیام‌های حجیم جلوگیری شود.
        """
        if not self.connect():
            yield None  # None نشان‌دهنده خطا است
            return

        symbols = mt5.symbols_get()
        if not symbols:
            self.log_message("No symbols found in Market Watch.", "warning")
            yield []  # لیست خالی یعنی داده‌ای پیدا نشد
            return

        symbols_data = [s._asdict() for s in symbols]
        total_symbols = len(symbols_data)
        self.log_message(f"Retrieved {total_symbols} total symbols. Starting batch processing...", "info")

        for i in range(0, total_symbols, batch_size):
            batch = symbols_data[i:i + batch_size]
            progress_callback(min(i + batch_size, total_symbols), total_symbols)
            yield batch

    def get_rates_in_batches(self, symbol_name, progress_callback, timeframe=mt5.TIMEFRAME_M1, total_count=100000,
                             batch_size=5000):
        """
        داده‌های کندل را به صورت دسته‌ای (batch) واکشی، پردازش و yield می‌کند.
        """
        if not self.connect():
            yield None
            return

        try:
            rates = mt5.copy_rates_from_pos(symbol_name, timeframe, 0, total_count)
            if rates is None or len(rates) == 0:
                self.log_message(f"Could not retrieve rates for {symbol_name}, error: {mt5.last_error()}", "warning")
                yield []
                return

            rates_frame = pd.DataFrame(rates)
            rates_frame['time_real'] = pd.to_datetime(rates_frame['time'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')
            for col in ['open', 'high', 'low', 'close']:
                rates_frame[col] = rates_frame[col].astype(float)
            for col in ['tick_volume', 'spread', 'real_volume']:
                rates_frame[col] = rates_frame[col].astype(int)

            total_rates = len(rates_frame)
            self.log_message(f"Retrieved {total_rates} total rates for {symbol_name}. Starting batch processing...",
                             "info")

            for i in range(0, total_rates, batch_size):
                batch_df = rates_frame.iloc[i:i + batch_size]
                batch_data = batch_df.to_dict('records')
                progress_callback(min(i + batch_size, total_rates), total_rates)
                yield batch_data

        except Exception as e:
            self.log_message(f"An exception occurred while fetching rates for {symbol_name}: {e}", "error")
            yield None

    def disconnect(self):
        """
        اتصال با ترمینال متاتریدر را قطع می‌کند.
        """
        mt5.shutdown()
        self.log_message("Disconnected from MetaTrader 5.", "info")
