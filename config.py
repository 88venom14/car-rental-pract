import os


DB_CONFIG = {
    "host": os.getenv("CAR_RENTAL_DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("CAR_RENTAL_DB_PORT", "3306")),
    "user": os.getenv("CAR_RENTAL_DB_USER", "root"),
    "password": os.getenv("CAR_RENTAL_DB_PASSWORD", ""),
    "database": os.getenv("CAR_RENTAL_DB_NAME", "car_rental"),
    "connection_timeout": 5,
}

LATE_RETURN_RATE = 1.5
