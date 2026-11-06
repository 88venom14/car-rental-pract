import re
from datetime import date


def required(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"Поле «{label}» обязательно для заполнения.")
    return value


def phone(value: str) -> str:
    cleaned = re.sub(r"[\s()\-]", "", value)
    if not re.fullmatch(r"\+?\d{10,15}", cleaned):
        raise ValueError("Телефон должен содержать от 10 до 15 цифр.")
    return cleaned


def email(value: str) -> str:
    value = value.strip()
    if value and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError("Укажите корректный адрес электронной почты.")
    return value


def plate(value: str) -> str:
    value = value.strip().upper().replace(" ", "")
    if not re.fullmatch(r"[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}", value):
        raise ValueError("Введите номер в формате А123ВС77.")
    return value


def passport(value: str) -> str:
    value = re.sub(r"\s+", " ", value.strip())
    if not re.fullmatch(r"\d{4} \d{6}", value):
        raise ValueError("Паспорт указывается в формате 1234 123456.")
    return value


def production_year(value: str) -> int:
    try:
        year = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Год выпуска должен быть целым числом.") from exc
    if not 1990 <= year <= date.today().year:
        raise ValueError(f"Год выпуска должен быть от 1990 до {date.today().year}.")
    return year


def positive_number(value: str, label: str, allow_zero: bool = False) -> float:
    try:
        number = float(value.replace(",", "."))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Поле «{label}» должно быть числом.") from exc
    if number < 0 or (number == 0 and not allow_zero):
        raise ValueError(f"Поле «{label}» должно быть положительным.")
    return number


def iso_date(value: str, label: str = "дата") -> date:
    try:
        return date.fromisoformat(value.strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Укажите {label} в формате ГГГГ-ММ-ДД.") from exc


def date_range(start: date, end: date) -> None:
    if end < start:
        raise ValueError("Дата окончания не может быть раньше даты начала.")
