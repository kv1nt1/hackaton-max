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
                    booking_required,
                    avg_duration_minutes,
                    opening_hours,
                    edge_id,
                    edge_position
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

def get_city_rows():
    """Узлы и рёбра графа города для routing.CityGraph."""
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, x, y, district FROM city_nodes;")
            nodes = [
                dict(zip(("id", "x", "y", "district"), row))
                for row in cursor.fetchall()
            ]

            cursor.execute("""
                SELECT id, node_from, node_to, length_m,
                       car_speed_kmh, walk_speed_kmh,
                       car_allowed, walk_allowed
                FROM city_edges;
            """)
            columns = [d[0] for d in cursor.description]
            edges = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return nodes, edges

    finally:
        connection.close()


_graph = None


def get_city_graph():
    """Граф строится один раз и переиспользуется (город не меняется)."""
    global _graph

    if _graph is None:
        from app.core.routing import CityGraph

        nodes, edges = get_city_rows()
        _graph = CityGraph(nodes, edges)

    return _graph


# ---------------------------------------------------------------- бронирования

def _bot_bookings_table_exists(cursor):
    cursor.execute("SELECT to_regclass('public.bot_bookings');")
    return cursor.fetchone()[0] is not None


class BookingsTableMissing(Exception):
    """Таблица bot_bookings ещё не создана (не выполнена sql/08_bot_bookings.sql)."""


def get_bookings_for_places(place_ids, day_from, day_to):
    """
    Активные брони мест из place_ids, пересекающие календарный диапазон
    [day_from, day_to] (включительно). Возвращает
    {place_id: [(starts_at, ends_at), ...]}.
    """
    if not place_ids:
        return {}

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            if not _bot_bookings_table_exists(cursor):
                raise BookingsTableMissing(
                    "Таблица bot_bookings не найдена. Выполните sql/08_bot_bookings.sql "
                    "на вашей БД (см. README)."
                )
            cursor.execute("""
                SELECT place_id, starts_at, ends_at
                FROM bot_bookings
                WHERE status = 'confirmed'
                  AND place_id = ANY(%s)
                  AND starts_at < %s
                  AND ends_at > %s
                ORDER BY place_id, starts_at;
            """, (list(place_ids), day_to, day_from))

            result = {}
            for place_id, starts_at, ends_at in cursor.fetchall():
                result.setdefault(place_id, []).append((starts_at, ends_at))
            return result

    finally:
        connection.close()


def create_booking(place_id, room_code, organizer_max_id, starts_at, ends_at, group_size):
    """Записывает бронь. Возвращает id новой строки."""
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            if not _bot_bookings_table_exists(cursor):
                raise BookingsTableMissing(
                    "Таблица bot_bookings не найдена. Выполните sql/08_bot_bookings.sql "
                    "на вашей БД (см. README)."
                )
            cursor.execute("""
                INSERT INTO bot_bookings
                    (place_id, room_code, organizer_max_id, starts_at, ends_at, group_size)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
            """, (place_id, room_code, organizer_max_id, starts_at, ends_at, group_size))
            booking_id = cursor.fetchone()[0]
        connection.commit()
        return booking_id

    finally:
        connection.close()
