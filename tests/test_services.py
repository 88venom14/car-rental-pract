import unittest
from datetime import date
from decimal import Decimal

from app.services import final_cost, overlaps, rental_cost, rental_days
from app.validators import (date_range, email, iso_date, passport, phone, plate,
                            positive_number, production_year, required)


class ServiceTests(unittest.TestCase):
    def test_rental_days_minimum_is_one(self):
        self.assertEqual(rental_days(date(2026, 1, 1), date(2026, 1, 1)), 1)

    def test_cost_for_four_days(self):
        self.assertEqual(rental_cost(date(2026, 1, 1), date(2026, 1, 5), Decimal("1000")), Decimal("4000.00"))

    def test_overdue_rate_is_one_and_half(self):
        self.assertEqual(final_cost(date(2026, 1, 1), date(2026, 1, 3), date(2026, 1, 5), Decimal("1000")), Decimal("5000.00"))

    def test_early_return_cost_uses_actual_days(self):
        self.assertEqual(final_cost(date(2026, 1, 1), date(2026, 1, 6), date(2026, 1, 3), Decimal("1000")), Decimal("2000.00"))

    def test_overlapping_periods(self):
        self.assertTrue(overlaps(date(2026, 1, 1), date(2026, 1, 5), date(2026, 1, 4), date(2026, 1, 7)))

    def test_adjacent_periods_do_not_overlap(self):
        self.assertFalse(overlaps(date(2026, 1, 1), date(2026, 1, 5), date(2026, 1, 5), date(2026, 1, 7)))

    def test_single_day_rentals_overlap_on_same_day(self):
        self.assertTrue(overlaps(date(2026, 1, 5), date(2026, 1, 5), date(2026, 1, 5), date(2026, 1, 5)))

    def test_invalid_cost_date_order(self):
        with self.assertRaises(ValueError): rental_cost(date(2026, 1, 2), date(2026, 1, 1), Decimal("10"))


class ValidatorTests(unittest.TestCase):
    def test_required(self): self.assertEqual(required(" Иванов ", "Фамилия"), "Иванов")
    def test_required_rejects_empty(self):
        with self.assertRaises(ValueError): required(" ", "Фамилия")
    def test_phone(self): self.assertEqual(phone("+7 (900) 123-45-67"), "+79001234567")
    def test_phone_rejects_letters(self):
        with self.assertRaises(ValueError): phone("abc")
    def test_email(self): self.assertEqual(email("user@example.ru"), "user@example.ru")
    def test_email_rejects_bad_address(self):
        with self.assertRaises(ValueError): email("not-an-email")
    def test_plate(self): self.assertEqual(plate("а123вс77"), "А123ВС77")
    def test_plate_rejects_bad_format(self):
        with self.assertRaises(ValueError): plate("ABC123")
    def test_passport(self): self.assertEqual(passport("1234 123456"), "1234 123456")
    def test_passport_rejects_bad_format(self):
        with self.assertRaises(ValueError): passport("123456")
    def test_year(self): self.assertEqual(production_year("2020"), 2020)
    def test_year_rejects_out_of_range(self):
        with self.assertRaises(ValueError): production_year("1980")
    def test_positive_number(self): self.assertEqual(positive_number("12,5", "Тариф"), 12.5)
    def test_positive_number_rejects_zero(self):
        with self.assertRaises(ValueError): positive_number("0", "Тариф")
    def test_iso_date(self): self.assertEqual(iso_date("2026-05-01"), date(2026, 5, 1))
    def test_iso_date_rejects_bad_format(self):
        with self.assertRaises(ValueError): iso_date("01.05.2026")
    def test_date_range_rejects_reverse(self):
        with self.assertRaises(ValueError): date_range(date(2026, 5, 2), date(2026, 5, 1))


if __name__ == "__main__":
    unittest.main()
