# ==================================================================
# File: agent_app/mt5_manager.py
# Description: این فایل مسئول تمام تعاملات با MetaTrader 5 است.
# این کد کامل و نهایی است.
# ==================================================================
import MetaTrader5 as mt5
import logging


class MT5Manager:
    """
    کلاسی برای مدیریت تمام عملیات مربوط به MetaTrader 5،
    شامل اتصال، دریافت اطلاعات حساب و واکشی اطلاعات نمادها.
    """

    def __init__(self):
        self.logger = logging.getLogger("AgentApp")
        if not mt5.initialize():
            self.logger.error(f"initialize() failed, error code = {mt5.last_error()}")
            # در صورت عدم موفقیت در اتصال اولیه، بهتر است یک استثنا ایجاد شود
            raise ConnectionError("Failed to initialize MetaTrader 5")
        self.logger.info("MetaTrader 5 initialized successfully.")

    def connect(self):
        """
        اطمینان حاصل می‌کند که یک اتصال فعال با ترمینال متاتریدر وجود دارد.
        """
        if not mt5.terminal_info():
            self.logger.warning("No active terminal connection, trying to re-initialize...")
            if not mt5.initialize():
                self.logger.error(f"re-initialize() failed, error code = {mt5.last_error()}")
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
        self.logger.error("Could not retrieve account info.")
        return None

    def get_all_symbols(self):
        """
        این تابع تمام نمادهای موجود در Market Watch را گرفته
        و اطلاعات کامل آن‌ها را به صورت لیستی از دیکشنری‌ها برمی‌گرداند.
        """
        if not self.connect():
            return []

        symbols = mt5.symbols_get()
        if not symbols:
            self.logger.warning("No symbols found in Market Watch.")
            return []

        symbols_data = []
        for symbol in symbols:
            # ._asdict() هر آبجکت نماد را به یک دیکشنری پایتون تبدیل می‌کند
            symbols_data.append(symbol._asdict())

        self.logger.info(f"Retrieved {len(symbols_data)} symbols from MT5.")
        return symbols_data

    def disconnect(self):
        """
        اتصال با ترمینال متاتریدر را قطع می‌کند.
        """
        mt5.shutdown()
        self.logger.info("Disconnected from MetaTrader 5.")