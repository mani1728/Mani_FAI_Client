# C:\...\windows_agent_project\client\agent_app\main.py

import tkinter as tk
from gui import AgentGUI

def main():
    """نقطه ورود اصلی برنامه."""
    try:
        root = tk.Tk()
        app = AgentGUI(root)
        root.mainloop()
    except Exception as e:
        # در صورت بروز خطای پیش‌بینی نشده، آن را لاگ می‌کنیم
        # این کار به دیباگ کردن نسخه‌های اجرایی کمک می‌کند
        try:
            from logger import setup_logger
            logger = setup_logger()
            logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)
        except:
            # اگر حتی لاگر هم کار نکرد، در کنسول چاپ می‌کنیم
            print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    main()