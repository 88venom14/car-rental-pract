import os
import unittest
import uuid
from datetime import date, timedelta

import mysql.connector

from app.db import Database
from app.repositories import CarRepository, RentalRepository, ReportRepository, Repository
from app.services import RentalService


@unittest.skipUnless(os.getenv("CAR_RENTAL_RUN_INTEGRATION") == "1",
                     "Требуется CAR_RENTAL_RUN_INTEGRATION=1 и схема rental_test")
class DatabaseIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "host": os.getenv("CAR_RENTAL_DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("CAR_RENTAL_DB_PORT", "3306")),
            "user": os.getenv("CAR_RENTAL_DB_USER", "root"),
            "password": os.getenv("CAR_RENTAL_DB_PASSWORD", ""),
            "database": "rental_test",
            "connection_timeout": 3,
        }
        self.db = Database(self.config)
        self.token = uuid.uuid4().hex
        suffix = int(self.token[:8], 16)
        series_number = f"{suffix % 10000000000:010d}"
        passport_number = series_number[:4] + " " + series_number[4:]
        plate_number = f"А{suffix % 1000:03d}АА69"
        self.category_id = Repository(self.db, "car_categories").insert({
            "name": "Тестовая " + self.token[:10], "daily_rate": 1000, "description": "Интеграционный тест"})
        self.client_id = Repository(self.db, "clients").insert({
            "last_name": "Тестовый", "first_name": "Клиент", "patronymic": "Тестович",
            "passport": passport_number, "driver_license": self.token[:16],
            "phone": "+79000000000", "email": self.token[:8] + "@example.test"})
        self.car_id = Repository(self.db, "cars").insert({
            "category_id": self.category_id, "brand": "Тест", "model": "Модель",
            "year": 2022, "plate": plate_number, "color": "Белый", "mileage": 1,
            "status": "available"})
        self.car_repo = CarRepository(self.db)
        self.rental_repo = RentalRepository(self.db)
        self.service = RentalService(self.rental_repo, self.car_repo)

    def tearDown(self):
        connection = mysql.connector.connect(**self.config)
        try:
            cursor = connection.cursor()
            cursor.execute("DELETE FROM rentals WHERE car_id=%s", (self.car_id,))
            cursor.execute("DELETE FROM cars WHERE id=%s", (self.car_id,))
            cursor.execute("DELETE FROM clients WHERE id=%s", (self.client_id,))
            cursor.execute("DELETE FROM car_categories WHERE id=%s", (self.category_id,))
            connection.commit()
        finally:
            connection.close()

    def test_category_crud(self):
        repo = Repository(self.db, "car_categories")
        record_id = repo.insert({"name": "Удаляемая " + self.token[:10], "daily_rate": 1500})
        self.assertEqual(repo.get(record_id)["name"], "Удаляемая " + self.token[:10])
        repo.update(record_id, {"daily_rate": 1700})
        self.assertEqual(float(repo.get(record_id)["daily_rate"]), 1700.0)
        repo.delete(record_id)

    def test_rental_creation_and_overlapping_period_rejection(self):
        start, end = date.today(), date.today() + timedelta(days=2)
        self.service.create(self.car_id, self.client_id, start, end)
        with self.assertRaises(ValueError):
            self.service.create(self.car_id, self.client_id, start, end)

    def test_return_and_cancellation(self):
        start, end = date.today(), date.today() + timedelta(days=2)
        rental_id = self.service.create(self.car_id, self.client_id, start, end)
        amount = self.service.return_car(rental_id, end + timedelta(days=1))
        self.assertEqual(float(amount), 3500.0)
        self.assertEqual(self.rental_repo.get(rental_id)["status"], "closed")

        next_id = self.service.create(self.car_id, self.client_id, end, end + timedelta(days=2))
        self.service.cancel(next_id)
        self.assertEqual(self.rental_repo.get(next_id)["status"], "cancelled")

    def test_income_report_includes_closed_rental(self):
        start, end = date.today(), date.today() + timedelta(days=1)
        rental_id = self.service.create(self.car_id, self.client_id, start, end)
        self.service.return_car(rental_id, end)
        summary, categories, top_cars = ReportRepository(self.db).for_period(start, end)
        self.assertGreaterEqual(summary["contracts"], 1)
        self.assertTrue(any(row["label"] == "Тестовая " + self.token[:10] for row in categories))
        self.assertLessEqual(len(top_cars), 3)


if __name__ == "__main__":
    unittest.main()
