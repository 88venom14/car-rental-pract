from datetime import timedelta
import logging

LOGGER = logging.getLogger(__name__)


class Repository:
    def __init__(self, db, table):
        if table not in {"cars", "clients", "car_categories", "rentals"}:
            raise ValueError("Недопустимая таблица.")
        self.db, self.table = db, table

    def all(self):
        return self.db.query(f"SELECT * FROM {self.table} ORDER BY id", fetch=True)

    def get(self, record_id):
        rows = self.db.query(f"SELECT * FROM {self.table} WHERE id = %s",
                             (record_id,), fetch=True)
        if not rows:
            raise ValueError("Запись не найдена.")
        return rows[0]

    def insert(self, values):
        fields = ", ".join(values)
        marks = ", ".join(["%s"] * len(values))
        return self.db.query(f"INSERT INTO {self.table} ({fields}) VALUES ({marks})",
                             tuple(values.values()), commit=True)

    def update(self, record_id, values):
        assignments = ", ".join(f"{field} = %s" for field in values)
        return self.db.query(f"UPDATE {self.table} SET {assignments} WHERE id = %s",
                             (*values.values(), record_id), commit=True)

    def delete(self, record_id):
        return self.db.query(f"DELETE FROM {self.table} WHERE id = %s",
                             (record_id,), commit=True)


class RentalRepository(Repository):
    def __init__(self, db):
        super().__init__(db, "rentals")

    def is_available(self, car_id, start, end):
        if end == start:
            end += timedelta(days=1)
        rows = self.db.query(
            "SELECT id FROM rentals WHERE car_id = %s AND status = 'active' "
            "AND start_date < %s AND end_date_planned > %s",
            (car_id, end, start), fetch=True)
        return not rows

    def list_for_display(self, query="", start=None, end=None):
        pattern = f"%{query}%"
        sql = ("SELECT r.*, CONCAT_WS(' ', cl.last_name, cl.first_name, cl.patronymic) AS client_name, "
               "c.plate FROM rentals r JOIN clients cl ON cl.id=r.client_id "
               "JOIN cars c ON c.id=r.car_id WHERE "
               "(%s='' OR CAST(r.id AS CHAR) LIKE %s OR cl.last_name LIKE %s "
               "OR cl.first_name LIKE %s OR cl.patronymic LIKE %s OR c.plate LIKE %s "
               "OR CASE r.status WHEN 'active' THEN 'действует' WHEN 'closed' THEN 'закрыт' "
               "WHEN 'cancelled' THEN 'отменён' ELSE r.status END LIKE %s) "
               "AND (%s IS NULL OR r.start_date >= %s) AND (%s IS NULL OR r.start_date <= %s) "
               "ORDER BY r.id")
        values = (query, pattern, pattern, pattern, pattern, pattern, pattern,
                  start, start, end, end)
        return self.db.query(sql, values, fetch=True)

    def create(self, car_id, client_id, start, end, rate, total):
        if end == start:
            end += timedelta(days=1)
        connection = self.db.connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT status FROM cars WHERE id = %s FOR UPDATE", (car_id,))
            row = cursor.fetchone()
            if not row or row[0] == "maintenance":
                raise ValueError("Автомобиль находится на обслуживании или не найден.")
            cursor.execute("SELECT id FROM rentals WHERE car_id = %s AND status = 'active' "
                           "AND start_date < %s AND end_date_planned > %s FOR UPDATE",
                           (car_id, end, start))
            if cursor.fetchone():
                raise ValueError("Автомобиль уже занят в выбранный период.")
            cursor.execute("INSERT INTO rentals "
                           "(car_id, client_id, start_date, end_date_planned, daily_rate, total_cost, status) "
                           "VALUES (%s, %s, %s, %s, %s, %s, 'active')",
                           (car_id, client_id, start, end, rate, total))
            rental_id = cursor.lastrowid
            cursor.execute("UPDATE cars SET status = 'rented' WHERE id = %s", (car_id,))
            connection.commit()
            return rental_id
        except Exception:
            connection.rollback()
            LOGGER.exception("Не удалось оформить договор аренды")
            raise
        finally:
            connection.close()

    def update_active(self, rental_id, car_id, client_id, start, end):
        if end == start:
            end += timedelta(days=1)
        connection = self.db.connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT car_id,status,daily_rate FROM rentals WHERE id=%s FOR UPDATE",
                           (rental_id,))
            current = cursor.fetchone()
            if not current or current[1] != "active":
                raise ValueError("Изменять можно только действующий договор.")
            old_car_id, _status, rate = current
            cursor.execute("SELECT status FROM cars WHERE id=%s FOR UPDATE", (car_id,))
            car = cursor.fetchone()
            if not car or car[0] == "maintenance":
                raise ValueError("Автомобиль находится на обслуживании или не найден.")
            cursor.execute("SELECT id FROM rentals WHERE car_id=%s AND status='active' AND id<>%s "
                           "AND start_date<%s AND end_date_planned>%s FOR UPDATE",
                           (car_id, rental_id, end, start))
            if cursor.fetchone():
                raise ValueError("Автомобиль уже занят в выбранный период.")
            from app.services import rental_cost
            total = rental_cost(start, end, rate)
            cursor.execute("UPDATE rentals SET car_id=%s,client_id=%s,start_date=%s,"
                           "end_date_planned=%s,total_cost=%s WHERE id=%s",
                           (car_id, client_id, start, end, total, rental_id))
            for affected_car in {old_car_id, car_id}:
                cursor.execute("SELECT COUNT(*) FROM rentals WHERE car_id=%s AND status='active'",
                               (affected_car,))
                active_count = cursor.fetchone()[0]
                cursor.execute("UPDATE cars SET status=%s WHERE id=%s",
                               ("rented" if active_count else "available", affected_car))
            connection.commit()
        except Exception:
            connection.rollback()
            LOGGER.exception("Не удалось изменить договор аренды")
            raise
        finally:
            connection.close()

    def delete(self, rental_id):
        self._finish(rental_id, "DELETE FROM rentals WHERE id=%s", (rental_id,), allow_closed=True)

    def close(self, rental_id, actual_date, total):
        self._finish(rental_id, "UPDATE rentals SET return_date=%s, total_cost=%s, status='closed' WHERE id=%s",
                     (actual_date, total, rental_id))

    def cancel(self, rental_id):
        self._finish(rental_id, "UPDATE rentals SET status='cancelled' WHERE id=%s", (rental_id,))

    def _finish(self, rental_id, sql, params, allow_closed=False):
        connection = self.db.connect()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT car_id, status FROM rentals WHERE id=%s FOR UPDATE", (rental_id,))
            record = cursor.fetchone()
            if not record:
                raise ValueError("Договор не найден.")
            car_id, current_status = record
            if current_status != "active" and not allow_closed:
                raise ValueError("Договор уже не действует.")
            cursor.execute(sql, params)
            cursor.execute("SELECT COUNT(*) FROM rentals WHERE car_id=%s AND status='active'", (car_id,))
            active_count = cursor.fetchone()[0]
            cursor.execute("UPDATE cars SET status=%s WHERE id=%s",
                           ("rented" if active_count else "available", car_id))
            connection.commit()
        except Exception:
            connection.rollback()
            LOGGER.exception("Не удалось закрыть или отменить договор")
            raise
        finally:
            connection.close()


class CarRepository(Repository):
    def __init__(self, db):
        super().__init__(db, "cars")

    def get(self, car_id):
        rows = self.db.query("SELECT c.*, cc.daily_rate FROM cars c "
                             "JOIN car_categories cc ON cc.id=c.category_id WHERE c.id=%s",
                             (car_id,), fetch=True)
        if not rows:
            raise ValueError("Автомобиль не найден.")
        return rows[0]

    def list_for_display(self, query=""):
        pattern = f"%{query}%"
        return self.db.query(
            "SELECT c.*, cc.name AS category_name FROM cars c "
            "JOIN car_categories cc ON cc.id=c.category_id WHERE "
            "(%s='' OR c.brand LIKE %s OR c.model LIKE %s OR cc.name LIKE %s "
            "OR CASE c.status WHEN 'available' THEN 'доступен' WHEN 'rented' THEN 'в аренде' "
            "WHEN 'maintenance' THEN 'обслуживание' ELSE c.status END LIKE %s) ORDER BY c.id",
            (query, pattern, pattern, pattern, pattern), fetch=True)

    def set_status(self, car_id, status):
        return self.db.query("UPDATE cars SET status=%s WHERE id=%s",
                             (status, car_id), commit=True)


class ReportRepository:
    def __init__(self, db):
        self.db = db

    def for_period(self, start, end):
        summary = self.db.query(
            "SELECT COUNT(*) AS contracts, COALESCE(SUM(total_cost),0) AS revenue, "
            "COALESCE(AVG(total_cost),0) AS average FROM rentals "
            "WHERE status='closed' AND return_date BETWEEN %s AND %s",
            (start, end), fetch=True)[0]
        categories = self.db.query(
            "SELECT cc.name AS label, SUM(r.total_cost) AS revenue FROM rentals r "
            "JOIN cars c ON c.id=r.car_id JOIN car_categories cc ON cc.id=c.category_id "
            "WHERE r.status='closed' AND r.return_date BETWEEN %s AND %s "
            "GROUP BY cc.id,cc.name ORDER BY revenue DESC", (start, end), fetch=True)
        top_cars = self.db.query(
            "SELECT CONCAT(c.brand,' ',c.model,' (',c.plate,')') AS label, "
            "SUM(r.total_cost) AS revenue FROM rentals r JOIN cars c ON c.id=r.car_id "
            "WHERE r.status='closed' AND r.return_date BETWEEN %s AND %s "
            "GROUP BY c.id ORDER BY revenue DESC LIMIT 3", (start, end), fetch=True)
        return summary, categories, top_cars
