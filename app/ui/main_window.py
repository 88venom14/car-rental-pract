import csv
import logging
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from app.repositories import CarRepository, RentalRepository, ReportRepository, Repository
from app.services import RentalService
from app.validators import (date_range, email, iso_date, passport, phone, plate,
                            positive_number, production_year, required)

LOGGER = logging.getLogger(__name__)

FIELDS = {
    "Автомобили": ("cars", ["category_id", "brand", "model", "year", "plate", "color", "mileage", "status"]),
    "Клиенты": ("clients", ["last_name", "first_name", "patronymic", "passport", "driver_license", "phone", "email"]),
    "Категории": ("car_categories", ["name", "daily_rate", "description"]),
    "Договоры": ("rentals", ["car_id", "client_id", "start_date", "end_date_planned", "return_date", "daily_rate", "total_cost", "status"]),
}
COLUMNS = {
    "cars": ["id", "category_id", "category_name", "brand", "model", "year", "plate", "color", "mileage", "status"],
    "clients": ["id", "last_name", "first_name", "patronymic", "passport", "driver_license", "phone", "email", "registered_at"],
    "car_categories": ["id", "name", "daily_rate", "description"],
    "rentals": ["id", "car_id", "client_id", "client_name", "plate", "start_date", "end_date_planned", "return_date", "daily_rate", "total_cost", "status", "created_at"],
}
FIELD_LABELS = {
    "id": "№", "category_id": "Категория №", "brand": "Марка", "model": "Модель",
    "year": "Год выпуска", "plate": "Госномер", "color": "Цвет", "mileage": "Пробег, км",
    "status": "Статус", "last_name": "Фамилия", "first_name": "Имя", "patronymic": "Отчество",
    "passport": "Паспорт", "driver_license": "Водительское удостоверение", "phone": "Телефон",
    "email": "Электронная почта", "registered_at": "Зарегистрирован", "name": "Название",
    "daily_rate": "Тариф в сутки", "description": "Описание", "car_id": "Автомобиль №",
    "client_id": "Клиент №", "start_date": "Начало аренды", "end_date_planned": "Плановый возврат",
    "return_date": "Фактический возврат", "total_cost": "Стоимость, руб.", "created_at": "Создан",
    "client_name": "Клиент", "plate": "Госномер", "category_name": "Категория",
}
STATUS_LABELS = {"available": "доступен", "rented": "в аренде", "maintenance": "обслуживание",
                 "active": "действует", "closed": "закрыт", "cancelled": "отменён"}
STATUS_VALUES = {"доступен": "available", "в аренде": "rented", "обслуживание": "maintenance"}


class MainWindow(ttk.Frame):
    def __init__(self, root, db):
        super().__init__(root, padding=8)
        self.root, self.db = root, db
        self.car_repo = CarRepository(db)
        self.rental_repo = RentalRepository(db)
        self.report_repo = ReportRepository(db)
        self.service = RentalService(self.rental_repo, self.car_repo)
        self.pack(fill="both", expand=True)
        root.title("Прокат автомобилей")
        root.minsize(900, 560)
        self.status = tk.StringVar(value="Подключение к базе данных…")
        self._build()
        self.refresh_all()

    def _build(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True)
        self.views = {}
        for title in FIELDS:
            frame = ttk.Frame(self.tabs, padding=8)
            self.tabs.add(frame, text=title)
            self.views[title] = self._make_table(frame, title)
        self._build_report()
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", pady=(6, 0))

    def _make_table(self, parent, title):
        table, columns = FIELDS[title]
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(0, 6))
        search = tk.StringVar()
        ttk.Label(bar, text="Поиск:").pack(side="left")
        entry = ttk.Entry(bar, textvariable=search, width=35)
        entry.pack(side="left", padx=5)
        date_start = date_end = None
        if title == "Договоры":
            ttk.Label(bar, text="Начало с:").pack(side="left", padx=(8, 2))
            date_start = ttk.Entry(bar, width=12)
            date_start.pack(side="left")
            ttk.Label(bar, text="по:").pack(side="left", padx=2)
            date_end = ttk.Entry(bar, width=12)
            date_end.pack(side="left")
            ttk.Button(bar, text="Фильтровать", command=lambda: self.load_table(title, search.get(), date_start.get(), date_end.get())).pack(side="left", padx=4)
        tree = ttk.Treeview(parent, show="headings", selectmode="browse")
        tree.pack(fill="both", expand=True)
        vs = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vs.set)
        vs.place(relx=1, rely=0.10, relheight=0.90, anchor="ne")
        buttons = ttk.Frame(parent)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Добавить", command=lambda: self.edit_record(title)).pack(side="left")
        ttk.Button(buttons, text="Изменить", command=lambda: self.edit_record(title, self.selected_id(tree))).pack(side="left", padx=4)
        ttk.Button(buttons, text="Удалить", command=lambda: self.delete_record(title, self.selected_id(tree))).pack(side="left")
        if title == "Договоры":
            ttk.Button(buttons, text="Оформить аренду", command=self.new_rental).pack(side="left", padx=(18, 4))
            ttk.Button(buttons, text="Возврат", command=self.return_rental).pack(side="left")
            ttk.Button(buttons, text="Отменить договор", command=self.cancel_rental).pack(side="left", padx=4)
        self._configure_columns(tree, table)
        search.trace_add("write", lambda *_: self.load_table(
            title, search.get(), date_start.get() if date_start else "",
            date_end.get() if date_end else ""))
        return {"tree": tree, "search": search, "date_start": date_start, "date_end": date_end}

    def _configure_columns(self, tree, table):
        names = COLUMNS[table]
        tree["columns"] = names
        for name in names:
            tree.heading(name, text=FIELD_LABELS.get(name, name), command=lambda col=name: self.sort_column(tree, col, False))
            tree.column(name, width=120, minwidth=70, stretch=True)

    @staticmethod
    def sort_column(tree, column, reverse):
        items = [(tree.set(item, column), item) for item in tree.get_children("")]
        items.sort(reverse=reverse)
        for index, (_, item) in enumerate(items):
            tree.move(item, "", index)
        tree.heading(column, command=lambda: MainWindow.sort_column(tree, column, not reverse))

    @staticmethod
    def selected_id(tree):
        selection = tree.selection()
        return int(tree.item(selection[0], "values")[0]) if selection else None

    def refresh_all(self):
        self.status.set("Данные обновлены")
        for title in FIELDS:
            view = self.views[title]
            self.load_table(title, view["search"].get(),
                            view["date_start"].get() if view["date_start"] else "",
                            view["date_end"].get() if view["date_end"] else "")

    def load_table(self, title, query="", start_value="", end_value=""):
        tree = self.views[title]["tree"]
        try:
            table = FIELDS[title][0]
            if title == "Договоры":
                start = iso_date(start_value, "дату начала фильтра") if start_value.strip() else None
                end = iso_date(end_value, "дату окончания фильтра") if end_value.strip() else None
                if start and end:
                    date_range(start, end)
                rows = self.rental_repo.list_for_display(query, start, end)
            elif title == "Автомобили":
                rows = self.car_repo.list_for_display(query)
            else:
                rows = Repository(self.db, table).all()
            tree.delete(*tree.get_children())
            if rows:
                names = list(rows[0])
                if tuple(tree["columns"]) != tuple(names):
                    tree["columns"] = names
                    for name in names:
                        tree.heading(name, text=FIELD_LABELS.get(name, name), command=lambda col=name: self.sort_column(tree, col, False))
                        tree.column(name, width=125, minwidth=70, stretch=True)
                for row in rows:
                    values = [STATUS_LABELS.get(row[name], row[name]) if name == "status" else row[name]
                              for name in names]
                    if query and query.casefold() not in " ".join(map(str, values)).casefold():
                        continue
                    tree.insert("", "end", values=values)
        except Exception as exc:
            LOGGER.exception("Не удалось загрузить раздел %s", title)
            self.status.set(f"Ошибка загрузки: {exc}")

    def edit_record(self, title, record_id=None):
        table, fields = FIELDS[title]
        if title == "Договоры":
            if not record_id:
                self.new_rental()
            else:
                self.edit_rental(record_id)
            return
        repo = Repository(self.db, table)
        try:
            old = repo.get(record_id) if record_id else {}
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{'Изменение' if record_id else 'Новая запись'}: {title.lower()}")
        dialog.transient(self.root)
        entries = {}
        for row, field in enumerate(fields):
            ttk.Label(dialog, text=FIELD_LABELS.get(field, field)).grid(row=row, column=0, sticky="w", padx=10, pady=4)
            if table == "cars" and field == "status":
                entry = ttk.Combobox(dialog, width=33, state="readonly",
                                     values=("доступен", "в аренде", "обслуживание"))
            else:
                entry = ttk.Entry(dialog, width=36)
            entry.grid(row=row, column=1, padx=10, pady=4)
            old_value = STATUS_LABELS.get(old.get(field), old.get(field)) if field == "status" else old.get(field)
            if isinstance(entry, ttk.Combobox):
                entry.set(str(old_value or "доступен"))
            else:
                entry.insert(0, str(old_value or ""))
            entries[field] = entry

        def save():
            try:
                data = {name: widget.get().strip() for name, widget in entries.items()}
                data = {key: value for key, value in data.items() if value != ""}
                if table == "cars":
                    data["status"] = STATUS_VALUES.get(data.get("status", "доступен"), "available")
                    data["brand"] = required(data.get("brand", ""), "марка")
                    data["model"] = required(data.get("model", ""), "модель")
                    data["plate"] = plate(data.get("plate", ""))
                    data["year"] = production_year(data.get("year", ""))
                    data["mileage"] = int(positive_number(data.get("mileage", "0"), "пробег", True))
                    data["category_id"] = int(data["category_id"])
                elif table == "car_categories":
                    data["name"] = required(data.get("name", ""), "название")
                    data["daily_rate"] = positive_number(data.get("daily_rate", ""), "тариф")
                elif table == "rentals":
                    data["car_id"], data["client_id"] = int(data["car_id"]), int(data["client_id"])
                    data["start_date"] = iso_date(data["start_date"])
                    data["end_date_planned"] = iso_date(data["end_date_planned"])
                    date_range(data["start_date"], data["end_date_planned"])
                    data["daily_rate"] = positive_number(data["daily_rate"], "тариф")
                    data["total_cost"] = positive_number(data["total_cost"], "стоимость")
                else:
                    for name in ("last_name", "first_name", "passport", "driver_license", "phone"):
                        data[name] = required(data.get(name, ""), name)
                    data["passport"] = passport(data["passport"])
                    data["phone"] = phone(data["phone"])
                    data["email"] = email(data.get("email", ""))
                if record_id:
                    repo.update(record_id, data)
                else:
                    repo.insert(data)
                dialog.destroy()
                self.refresh_all()
            except Exception as exc:
                messagebox.showerror("Проверьте данные", str(exc), parent=dialog)
        ttk.Button(dialog, text="Сохранить", command=save).grid(row=len(fields), column=0, columnspan=2, pady=10)
        dialog.grab_set()

    def delete_record(self, title, record_id):
        if not record_id:
            messagebox.showinfo("Удаление", "Выберите запись.", parent=self.root)
            return
        if not messagebox.askyesno("Подтверждение", "Удалить выбранную запись?", parent=self.root):
            return
        try:
            Repository(self.db, FIELDS[title][0]).delete(record_id)
            self.refresh_all()
        except Exception as exc:
            LOGGER.exception("Ошибка удаления")
            messagebox.showerror("Удаление невозможно", "Запись используется другими данными или произошла ошибка.\n" + str(exc), parent=self.root)

    def new_rental(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Оформление аренды")
        labels = ["Номер автомобиля", "Номер клиента", "Дата начала (ГГГГ-ММ-ДД)", "Плановый возврат (ГГГГ-ММ-ДД)"]
        fields = [ttk.Entry(dialog, width=32) for _ in labels]
        for i, (label, entry) in enumerate(zip(labels, fields)):
            ttk.Label(dialog, text=label).grid(row=i, column=0, padx=8, pady=5, sticky="w")
            entry.grid(row=i, column=1, padx=8, pady=5)

        def create():
            try:
                car, client = int(fields[0].get()), int(fields[1].get())
                start, end = iso_date(fields[2].get(), "дату начала"), iso_date(fields[3].get(), "дату окончания")
                self.service.create(car, client, start, end)
                dialog.destroy()
                self.refresh_all()
            except Exception as exc:
                messagebox.showerror("Не удалось оформить аренду", str(exc), parent=dialog)
        ttk.Button(dialog, text="Оформить", command=create).grid(row=4, column=0, columnspan=2, pady=10)
        dialog.grab_set()

    def edit_rental(self, rental_id):
        try:
            old = self.rental_repo.get(rental_id)
            if old["status"] != "active":
                raise ValueError("Изменять можно только действующий договор.")
        except Exception as exc:
            messagebox.showerror("Изменение договора", str(exc), parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Изменение договора")
        labels = ["Номер автомобиля", "Номер клиента", "Дата начала (ГГГГ-ММ-ДД)",
                  "Плановый возврат (ГГГГ-ММ-ДД)"]
        values = [old["car_id"], old["client_id"], old["start_date"], old["end_date_planned"]]
        fields = [ttk.Entry(dialog, width=32) for _ in labels]
        for i, (label, entry, value) in enumerate(zip(labels, fields, values)):
            ttk.Label(dialog, text=label).grid(row=i, column=0, padx=8, pady=5, sticky="w")
            entry.grid(row=i, column=1, padx=8, pady=5)
            entry.insert(0, str(value))

        def save():
            try:
                car, client = int(fields[0].get()), int(fields[1].get())
                start = iso_date(fields[2].get(), "дату начала")
                end = iso_date(fields[3].get(), "дату окончания")
                date_range(start, end)
                self.service.update(rental_id, car, client, start, end)
                dialog.destroy()
                self.refresh_all()
            except Exception as exc:
                messagebox.showerror("Не удалось изменить договор", str(exc), parent=dialog)
        ttk.Button(dialog, text="Сохранить", command=save).grid(row=4, column=0, columnspan=2, pady=10)
        dialog.grab_set()

    def return_rental(self):
        self._rental_action("Возврат", "Дата возврата (ГГГГ-ММ-ДД)",
                            lambda rid, value: self.service.return_car(rid, iso_date(value, "дату возврата")))

    def cancel_rental(self):
        self._rental_action("Отмена договора", None, lambda rid, _value: self.service.cancel(rid))

    def _rental_action(self, title, field_label, callback):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        ttk.Label(dialog, text="Номер договора").grid(row=0, column=0, padx=8, pady=6)
        rental = ttk.Entry(dialog)
        rental.grid(row=0, column=1, padx=8, pady=6)
        value = ttk.Entry(dialog)
        if field_label:
            ttk.Label(dialog, text=field_label).grid(row=1, column=0, padx=8, pady=6)
            value.grid(row=1, column=1, padx=8, pady=6)

        def submit():
            try:
                amount = callback(int(rental.get()), value.get())
                if amount is not None:
                    messagebox.showinfo("Возврат оформлен", f"Итоговая стоимость: {amount:.2f} руб.", parent=dialog)
                dialog.destroy()
                self.refresh_all()
            except Exception as exc:
                messagebox.showerror("Операция не выполнена", str(exc), parent=dialog)
        ttk.Button(dialog, text="Выполнить", command=submit).grid(row=2, column=0, columnspan=2, pady=8)
        dialog.grab_set()

    def _build_report(self):
        frame = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(frame, text="Отчёты")
        filters = ttk.Frame(frame)
        filters.pack(fill="x")
        ttk.Label(filters, text="С:").pack(side="left")
        self.report_start = ttk.Entry(filters, width=14)
        self.report_start.insert(0, date.today().replace(day=1).isoformat())
        self.report_start.pack(side="left", padx=4)
        ttk.Label(filters, text="По:").pack(side="left")
        self.report_end = ttk.Entry(filters, width=14)
        self.report_end.insert(0, date.today().isoformat())
        self.report_end.pack(side="left", padx=4)
        ttk.Button(filters, text="Сформировать", command=self.load_report).pack(side="left", padx=4)
        ttk.Button(filters, text="Экспорт CSV", command=self.export_report).pack(side="left")
        self.report_summary = tk.StringVar(value="Укажите период отчёта")
        ttk.Label(frame, textvariable=self.report_summary, font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=8)
        self.report_tree = ttk.Treeview(frame, columns=("category", "revenue"), show="headings")
        self.report_tree.heading("category", text="Категория / автомобиль")
        self.report_tree.heading("revenue", text="Выручка, руб.")
        self.report_tree.pack(fill="both", expand=True)

    def load_report(self):
        try:
            start, end = iso_date(self.report_start.get()), iso_date(self.report_end.get())
            date_range(start, end)
            totals, cats, top = self.report_repo.for_period(start, end)
            self.report_data = [(row["label"], row["revenue"]) for row in cats]
            self.report_data += [("ТОП: " + row["label"], row["revenue"]) for row in top]
            self.report_summary.set(f"Выручка: {totals['revenue']} руб.   Договоров: {totals['contracts']}   "
                                    f"Средний чек: {totals['average']} руб.")
            self.report_tree.delete(*self.report_tree.get_children())
            for label, amount in self.report_data:
                self.report_tree.insert("", "end", values=(label, amount))
            self.status.set("Отчёт сформирован")
        except Exception as exc:
            LOGGER.exception("Ошибка отчёта")
            messagebox.showerror("Ошибка отчёта", str(exc), parent=self.root)

    def export_report(self):
        if not hasattr(self, "report_data"):
            self.load_report()
        if not hasattr(self, "report_data"):
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream, delimiter=";")
                writer.writerow(["Категория / автомобиль", "Выручка, руб."])
                writer.writerows(self.report_data)
            messagebox.showinfo("Экспорт", "Отчёт сохранён.", parent=self.root)
