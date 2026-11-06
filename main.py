import logging
import tkinter as tk
from tkinter import messagebox

from config import DB_CONFIG
from app.db import Database
from app.ui.main_window import MainWindow


def main():
    logging.basicConfig(filename="app.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = tk.Tk()
    try:
        MainWindow(root, Database(DB_CONFIG))
    except Exception as exc:
        logging.exception("Не удалось запустить окно приложения")
        messagebox.showerror("Ошибка запуска", f"Не удалось открыть приложение: {exc}", parent=root)
    root.mainloop()


if __name__ == "__main__":
    main()
