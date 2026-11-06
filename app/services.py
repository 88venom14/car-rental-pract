from datetime import date
from decimal import Decimal

from config import LATE_RETURN_RATE


def rental_days(start: date, end: date) -> int:
    if end < start:
        raise ValueError("Дата окончания раньше даты начала.")
    return max(1, (end - start).days)


def rental_cost(start: date, end: date, daily_rate: Decimal) -> Decimal:
    return (daily_rate * rental_days(start, end)).quantize(Decimal("0.01"))


def final_cost(start: date, planned_end: date, actual_return: date,
               daily_rate: Decimal) -> Decimal:
    if actual_return < start:
        raise ValueError("Дата возврата не может быть раньше начала аренды.")
    planned_days = rental_days(start, planned_end)
    actual_days = rental_days(start, actual_return)
    regular_days = min(planned_days, actual_days)
    overdue_days = max(0, actual_days - planned_days)
    amount = daily_rate * regular_days
    amount += daily_rate * Decimal(str(LATE_RETURN_RATE)) * overdue_days
    return amount.quantize(Decimal("0.01"))


def overlaps(start: date, end: date, other_start: date, other_end: date) -> bool:
    if end == start:
        end = start.fromordinal(start.toordinal() + 1)
    if other_end == other_start:
        other_end = other_start.fromordinal(other_start.toordinal() + 1)
    return start < other_end and other_start < end


class RentalService:
    def __init__(self, rentals, cars):
        self.rentals = rentals
        self.cars = cars

    def create(self, car_id, client_id, start, end):
        if end < start:
            raise ValueError("Дата окончания не может быть раньше начала.")
        car = self.cars.get(car_id)
        if car["status"] == "maintenance":
            raise ValueError("Автомобиль находится на обслуживании.")
        if not self.rentals.is_available(car_id, start, end):
            raise ValueError("Автомобиль уже занят в выбранный период.")
        rate = Decimal(str(car["daily_rate"]))
        return self.rentals.create(car_id, client_id, start, end, rate,
                                   rental_cost(start, end, rate))

    def update(self, rental_id, car_id, client_id, start, end):
        if end < start:
            raise ValueError("Дата окончания не может быть раньше начала.")
        return self.rentals.update_active(rental_id, car_id, client_id, start, end)

    def return_car(self, rental_id, actual_date):
        rental = self.rentals.get(rental_id)
        if rental["status"] != "active":
            raise ValueError("Вернуть можно только действующий договор.")
        amount = final_cost(rental["start_date"], rental["end_date_planned"],
                            actual_date, Decimal(str(rental["daily_rate"])))
        self.rentals.close(rental_id, actual_date, amount)
        return amount

    def cancel(self, rental_id):
        rental = self.rentals.get(rental_id)
        if rental["status"] != "active":
            raise ValueError("Отменить можно только действующий договор.")
        self.rentals.cancel(rental_id)
