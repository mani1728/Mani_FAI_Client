# ==================================================================
# File: agent_app/mt5_manager.py
# Description: کد کامل و اصلاح شده.
# تغییر اصلی: تابع __init__ حالا یک ورودی به نام gui_callback می‌پذیرد.
# ==================================================================
import MetaTrader5 as mt5
import logging


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
                # اگر اتصال اولیه ناموفق بود، یک استثنا ایجاد می‌کنیم
                raise ConnectionError("Failed to initialize MetaTrader 5")
            self.logger.info("MetaTrader 5 initialized successfully.")
        except Exception as e:
            self.log_message(f"Initialization failed: {e}", "critical")
            raise

    def log_message(self, message, level="info"):
        """
        یک تابع کمکی برای لاگ کردن و ارسال پیام به صف GUI.
        """
        if level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        elif level == "critical":
            self.logger.critical(message)

        if self.gui_callback:
            # ارسال پیام به صف GUI برای نمایش در رابط کاربری
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

    def disconnect(self):
        """
        اتصال با ترمینال متاتریدر را قطع می‌کند.
        """
        mt5.shutdown()
        self.log_message("Disconnected from MetaTrader 5.", "info")