# C:\...\windows_agent_project\client\agent_app\mt5_manager.py

import MetaTrader5 as mt5
from logger import setup_logger


class MT5Manager:
    def __init__(self, gui_callback):
        self.logger = setup_logger()
        self.gui_callback = gui_callback
        self.connected = False

    def connect(self):
        """به پلتفرم MetaTrader 5 متصل می‌شود."""
        try:
            if not mt5.initialize():
                error_msg = f"Error: Failed to initialize MT5: {mt5.last_error()}"
                self.logger.error(error_msg)
                self.gui_callback(error_msg)
                return False
            self.connected = True
            self.logger.info("Successfully connected to MetaTrader 5 terminal.")
            self.gui_callback("MT5 Status: Connected")
            return True
        except Exception as e:
            error_msg = f"Error: MT5 connection error: {e}"
            self.logger.error(error_msg)
            self.gui_callback(error_msg)
            return False

    def disconnect(self):
        """ارتباط با MetaTrader 5 را قطع می‌کند."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.logger.info("Disconnected from MetaTrader 5.")
            self.gui_callback("MT5 Status: Disconnected")

    def get_status(self):
        """وضعیت اتصال به MT5 را برمی‌گرداند."""
        return "Connected" if self.connected else "Not connected"

    def get_account_info(self):
        """اطلاعات حساب کاربری لاگین شده را دریافت می‌کند."""
        if not self.connected:
            return None
        try:
            account_info = mt5.account_info()
            if account_info:
                return account_info._asdict()
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving account info: {e}")
            return None

    def sync_all_symbols_in_batches(self, progress_callback, batch_size=50):
        """تمام نمادها را به صورت دسته‌ای پردازش کرده و دیتا را yield می‌کند."""
        if not self.connected:
            return
        try:
            symbols = mt5.symbols_get()
            if not symbols:
                self.logger.warning("sync_all_symbols_in_batches: No symbols found to sync.")
                return

            total_symbols = len(symbols)
            processed_count = 0

            for i in range(0, total_symbols, batch_size):
                batch = symbols[i:i + batch_size]
                batch_names = [s.name for s in batch]

                # 🎯 اصلاح کلیدی: مقداردهی اولیه صحیح batch_data به عنوان لیست خالی
                batch_data =[]

                for name in batch_names:
                    mt5.symbol_select(name, True)

                for name in batch_names:
                    info = mt5.symbol_info(name)
                    if info:
                        batch_data.append(info._asdict())
                    processed_count += 1

                for name in batch_names:
                    mt5.symbol_select(name, False)

                progress_callback(processed_count, total_symbols)
                yield batch_data

        except Exception as e:
            # 🎯 بهبود لاگ خطا برای ارائه جزئیات بیشتر
            self.logger.error(f"Error during batch symbol sync: {e}", exc_info=True)