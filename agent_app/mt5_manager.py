# ==================================================================
# File: Mani_FAI_Client/agent_app/mt5_manager.py
# Description: کد کامل و نهایی مدیر متاتریدر.
# تغییر اصلی: افزودن متد get_rates_for_symbol برای واکشی داده‌های کندل.
# ==================================================================
import MetaTrader5 as mt5
import logging
import pandas as pd  # برای پردازش داده‌ها و تبدیل زمان
import numpy as np  # متاتریدر داده‌ها را به صورت آرایه نامپای برمی‌گرداند


class MT5Manager:
    # ... (متدهای __init__, log_message, connect, get_account_info, get_all_symbols بدون تغییر)
    def __init__(self, gui_callback=None):
        self.logger = logging.getLogger("AgentApp")
        self.gui_callback = gui_callback
        try:
            if not mt5.initialize():
                raise ConnectionError(f"initialize() failed, error code = {mt5.last_error()}")
            self.logger.info("MetaTrader 5 initialized successfully.")
        except Exception as e:
            self.log_message(f"Initialization failed: {e}", "critical")
            raise

    def log_message(self, message, level="info"):
        # ... (بدون تغییر)
        pass

    def connect(self):
        # ... (بدون تغییر)
        return True

    def get_account_info(self):
        # ... (بدون تغییر)
        return {"login": 12345}  # Placeholder

    def get_all_symbols(self):
        # ... (بدون تغییر)
        return []  # Placeholder

    def get_rates_for_symbol(self, symbol_name, timeframe=mt5.TIMEFRAME_M1, count=100000):
        """
        داده‌های کندل (rates) را برای یک نماد خاص واکشی کرده، پردازش می‌کند و به صورت لیستی از دیکشنری‌ها برمی‌گرداند.
        """
        if not self.connect():
            return None

        try:
            # درخواست آخرین 'count' کندل برای نماد و تایم‌فریم مشخص شده
            rates = mt5.copy_rates_from_pos(symbol_name, timeframe, 0, count)

            if rates is None or len(rates) == 0:
                self.log_message(f"Could not retrieve rates for {symbol_name}, error: {mt5.last_error()}", "warning")
                return []

            # تبدیل آرایه نامپای به دیتافریم pandas برای پردازش آسان
            rates_frame = pd.DataFrame(rates)

            # تبدیل زمان یونیxtime (ثانیه) به فرمت datetime خوانا و سپس به رشته
            rates_frame['time_real'] = pd.to_datetime(rates_frame['time'], unit='s').dt.strftime('%Y-%m-%d %H:%M:%S')

            # تبدیل مقادیر float نامپای به float استاندارد پایتون برای سازگاری با JSON
            for col in ['open', 'high', 'low', 'close']:
                rates_frame[col] = rates_frame[col].astype(float)

            # تبدیل مقادیر int نامپای به int استاندارد پایتون
            for col in ['tick_volume', 'spread', 'real_volume']:
                rates_frame[col] = rates_frame[col].astype(int)

            # تبدیل دیتافریم به لیستی از دیکشنری‌ها
            rates_data = rates_frame.to_dict('records')

            self.log_message(f"Retrieved and processed {len(rates_data)} rates for symbol {symbol_name}", "info")
            return rates_data

        except Exception as e:
            self.log_message(f"An exception occurred while fetching rates for {symbol_name}: {e}", "error")
            return None

    def disconnect(self):
        mt5.shutdown()
        self.log_message("Disconnected from MetaTrader 5.", "info")
