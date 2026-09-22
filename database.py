import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    connection = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    connection.set_client_encoding("UTF8")

    print("ENCODING:", connection.encoding)

    return connection


def get_places():
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    id,
                    name,
                    category,
                    district,
                    price_min,
                    price_avg,
                    price_max,
                    interests,
                    tags,
                    min_group_size,
                    max_group_size,
                    indoor,
                    food_available,
                    alcohol_available,
                    noise_level,
                    rating,
                    reviews_count,
                    booking_required
                FROM places
                WHERE active = TRUE
                ORDER BY id;
            """)

            columns = [description[0] for description in cursor.description]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

    finally:
        connection.close()