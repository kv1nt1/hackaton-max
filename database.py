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
        from routing import CityGraph

        nodes, edges = get_city_rows()
        _graph = CityGraph(nodes, edges)

    return _graph
