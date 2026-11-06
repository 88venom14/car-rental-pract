import logging

import mysql.connector
from mysql.connector import Error

LOGGER = logging.getLogger(__name__)


class Database:
    def __init__(self, config):
        self.config = config

    def connect(self):
        return mysql.connector.connect(**self.config)

    def query(self, sql, params=(), fetch=False, commit=False):
        connection = None
        try:
            connection = self.connect()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            result = cursor.fetchall() if fetch else cursor.lastrowid
            if commit:
                connection.commit()
            return result
        except Error as exc:
            if connection and connection.is_connected():
                connection.rollback()
            LOGGER.exception("Ошибка базы данных: %s", exc)
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
