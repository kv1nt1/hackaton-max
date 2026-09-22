import psycopg2


DB_CONFIG = {
    "dbname": "DataBase",
    "user": "postgres",
    "password": "12345",
    "host": "localhost",
    "port": 12345,
}


try:
    connection = psycopg2.connect(**DB_CONFIG)

    cursor = connection.cursor()

    cursor.execute("SELECT version();")
    version = cursor.fetchone()

    print("Подключение успешно!")
    print(version[0])

    cursor.execute("SELECT COUNT(*) FROM places;")
    count = cursor.fetchone()[0]

    print(f"Places в базе: {count}")

except Exception as error:
    print("Ошибка подключения:")
    print(error)

finally:
    if "cursor" in locals():
        cursor.close()

    if "connection" in locals():
        connection.close()