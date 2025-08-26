# ==================================================================
# File: agent_app/mt5_manager.py
# Description: این فایل مسئول تمام تعاملات با MetaTrader 5 است.
# ==================================================================
import MetaTrader5 as mt5
import logging


class MT5Manager:
    def __init__(self):
        self.logger = logging.getLogger("AgentApp")
        if not mt5.initialize():
            self.logger.error(f"initialize() failed, error code = {mt5.last_error()}")
            return
        self.logger.info("MetaTrader 5 initialized successfully.")

    def connect(self):
        if not mt5.terminal_info():
            if not mt5.initialize():
                self.logger.error(f"initialize() failed, error code = {mt5.last_error()}")
                return False
        return True

    def get_account_info(self):
        if not self.connect():
            return None
        return mt5.account_info()._asdict()

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
        mt5.shutdown()
        self.logger.info("Disconnected from MetaTrader 5.")


# ==================================================================
# File: agent_app/gui.py (بخش‌های مرتبط)
# Description: این بخش از کد GUI مسئول مدیریت رویداد کلیک دکمه Sync Symbols است.
# شما باید این منطق را در کلاس GUI خود ادغام کنید.
# ==================================================================
# فرض می‌کنیم شما یک کلاس به نام App یا GUI دارید
# و متدهای websocket_client و mt5_manager به عنوان property در دسترس هستند.

class YourApp:
    # ... (بقیه کدهای GUI شما مثل __init__, setup_ui, etc.)

    def on_sync_symbols_click(self):
        """
        این تابع زمانی اجرا می‌شود که کاربر روی دکمه Sync Symbols کلیک می‌کند.
        این تابع مسئول جمع‌آوری تمام نمادها و ارسال آن‌ها در یک درخواست واحد است.
        """
        self.log_message("Starting symbol synchronization...")

        # 1. دریافت اطلاعات کامل تمام نمادها از متاتریدر
        all_symbols = self.mt5_manager.get_all_symbols()

        if not all_symbols:
            self.log_message("No symbols to sync.", "warning")
            return

        # 2. دریافت اطلاعات حساب برای به دست آوردن login_id
        account_info = self.mt5_manager.get_account_info()
        if not account_info:
            self.log_message("Could not get account info. Cannot sync.", "error")
            return

        login_id = account_info.get('login')

        # 3. ساختاردهی داده‌ها در فرمت صحیح مورد انتظار سرور
        #    یک دیکشنری واحد که شامل login و لیست symbols است.
        payload = {
            "type": "symbols_info_sync",
            "login": login_id,
            "symbols": all_symbols  # <--- کل لیست نمادها اینجا قرار می‌گیرد
        }

        # 4. ارسال بسته کامل به پراکسی سرور
        try:
            # فرض می‌کنیم شما یک متد برای ارسال پیام از طریق وب‌ساکت دارید
            self.websocket_client.send_message(payload)
            self.log_message(f"Successfully sent {len(all_symbols)} symbols to the server for synchronization.")
        except Exception as e:
            self.log_message(f"Failed to send symbols to server: {e}", "error")

    def log_message(self, message, level="info"):
        # یک تابع کمکی برای نمایش پیام در GUI
        print(f"[{level.upper()}] {message}")
        # شما باید این را به ویجت لاگ خود متصل کنید
        # self.log_text_widget.append(f"[{level.upper()}] {message}")
