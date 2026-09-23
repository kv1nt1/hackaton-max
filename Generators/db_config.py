"""
Подключение генераторов к БД. Берёт настройки из .env в корне проекта
(те же DB_* переменные, что и у бота) — пароли в коде не хранятся.
"""

import os

from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
}
