# C:\...\windows_agent_project\client\agent_app\logger.py

import logging
import os
from config import LOG_FILE


def setup_logger():
    """لاگر را برای ثبت رویدادها در فایل و کنسول تنظیم می‌کند."""
    logger = logging.getLogger('AgentApp')

    # اگر لاگر از قبل handler داشت، دوباره اضافه نمی‌کنیم تا لاگ تکراری نشود
    if logger.hasHandlers():
        return logger

    # ایجاد دایرکتوری logs اگر وجود نداشته باشد
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    logger.setLevel(logging.INFO)  # تغییر به INFO برای لاگ‌های کمتر در حالت عادی

    # فرمت لاگ
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # هندلر برای فایل
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # هندلر برای کنسول
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger