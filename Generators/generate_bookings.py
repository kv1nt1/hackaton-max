"""Синтетические бронирования существующих встреч и мест.

Запуск: python Generators/generate_bookings.py [--dry-run] [--replace]
"""

import argparse
from collections import Counter
from datetime import datetime, time, timedelta
from pathlib import Path
import random

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor, execute_values

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
if __package__:
    from .db_config import DB_CONFIG
else:
    from db_config import DB_CONFIG

SEED = 42
MAX_BOOKINGS_PER_MEETING = 3
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def load_meetings(cursor):
    cursor.execute("""
        SELECT m.id, m.meeting_date, m.status,
               GREATEST(m.available_from, MAX(mp.available_from)) AS available_from,
               LEAST(m.available_until, MIN(mp.available_until)) AS available_until,
               COUNT(mp.user_id)::INTEGER AS group_size
        FROM meetings m
        JOIN meeting_participants mp ON mp.meeting_id = m.id
        GROUP BY m.id
        ORDER BY m.id;
    """)
    return [dict(row) for row in cursor.fetchall()]


def load_places(cursor):
    cursor.execute("""
        SELECT id, min_group_size, max_group_size,
               avg_duration_minutes, opening_hours
        FROM places
        WHERE active = TRUE
        ORDER BY id;
    """)
    return [dict(row) for row in cursor.fetchall()]


def opening_windows(place, day):
    """Учитываем и ночное расписание предыдущего дня."""
    for opening_day in (day - timedelta(days=1), day):
        hours = place["opening_hours"].get(WEEKDAYS[opening_day.weekday()])
        if not hours:
            continue
        opens, closes = (time.fromisoformat(value) for value in hours)
        start = datetime.combine(opening_day, opens)
        end = datetime.combine(opening_day, closes)
        if closes < opens:
            end += timedelta(days=1)
        yield start, end


def booking_candidates(meeting, places, not_before):
    available_until = datetime.combine(meeting["meeting_date"], meeting["available_until"])
    for place in places:
        if not place["min_group_size"] <= meeting["group_size"] <= place["max_group_size"]:
            continue
        duration = timedelta(minutes=place["avg_duration_minutes"])
        for opens, closes in opening_windows(place, meeting["meeting_date"]):
            earliest = max(not_before, opens)
            latest = min(available_until, closes) - duration
            if earliest <= latest:
                yield place, earliest, latest, duration


def generate_bookings(meetings, places, seed=SEED, max_per_meeting=MAX_BOOKINGS_PER_MEETING):
    if max_per_meeting < 1:
        raise ValueError("max_per_meeting должен быть положительным")
    rng = random.Random(seed)
    bookings = []
    ordered_places = sorted(places, key=lambda item: item["id"])
    for meeting in sorted(meetings, key=lambda item: item["id"]):
        start = datetime.combine(meeting["meeting_date"], meeting["available_from"])
        for _ in range(rng.randint(1, max_per_meeting)):
            candidates = list(booking_candidates(meeting, ordered_places, start))
            if not candidates:
                break
            place, earliest, latest, duration = rng.choice(candidates)
            # Начало с шагом 15 минут относительно доступного окна.
            starts_at = earliest + timedelta(minutes=15 * rng.randint(0, int((latest - earliest).total_seconds() // 900)))
            ends_at = starts_at + duration
            if meeting["status"] == "cancelled":
                status = "cancelled"
            elif meeting["status"] == "completed":
                status = "completed"
            else:
                status = rng.choices(["pending", "confirmed", "cancelled"], weights=[25, 65, 10])[0]
            bookings.append({
                "meeting_id": meeting["id"],
                "place_id": place["id"],
                "starts_at": starts_at,
                "ends_at": ends_at,
                "group_size": meeting["group_size"],
                "status": status,
                "notes": "Синтетическое групповое бронирование",
            })
            # Несколько посещений одной встречи идут последовательно.
            start = ends_at + timedelta(minutes=15)
    return bookings


def save_bookings(cursor, bookings, replace=False):
    if replace:
        cursor.execute("TRUNCATE TABLE bookings RESTART IDENTITY;")
    execute_values(cursor, """
        INSERT INTO bookings (
            meeting_id, place_id, starts_at, ends_at, group_size, status, notes
        ) VALUES %s;
    """, [tuple(booking[key] for key in (
        "meeting_id", "place_id", "starts_at", "ends_at", "group_size", "status", "notes"
    )) for booking in bookings])


def print_statistics(bookings, meetings_count):
    print(f"Бронирований: {len(bookings)}")
    print(f"Встреч с бронированиями: {len({b['meeting_id'] for b in bookings})} из {meetings_count}")
    print("Статусы:", dict(Counter(b["status"] for b in bookings)))
    for booking in bookings[:3]:
        print(f"  Встреча {booking['meeting_id']}, место {booking['place_id']}: "
              f"{booking['starts_at']} — {booking['ends_at']}, "
              f"{booking['group_size']} чел., {booking['status']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED, help="Seed генератора (по умолчанию 42)")
    parser.add_argument("--max-per-meeting", type=int, default=MAX_BOOKINGS_PER_MEETING,
                        help="Максимум бронирований на встречу (по умолчанию 3)")
    parser.add_argument("--dry-run", action="store_true", help="Показать результат без записи в БД")
    parser.add_argument("--replace", action="store_true", help="Заменить ВСЕ записи bookings новым набором")
    args = parser.parse_args()
    if args.max_per_meeting < 1:
        parser.error("--max-per-meeting должен быть положительным")
    if not DB_CONFIG["dbname"]:
        parser.error("Задай DB_NAME и остальные DB_* в .env в корне проекта")

    connection = psycopg2.connect(**DB_CONFIG)
    try:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT to_regclass('bookings') AS table_name")
            if cursor.fetchone()["table_name"] is None:
                raise RuntimeError("Сначала примени sql/07_bookings.sql")
            meetings = load_meetings(cursor)
            places = load_places(cursor)
            if not meetings:
                raise RuntimeError("Нет встреч с участниками. Сначала запусти generate_meetings.py")
            if not places:
                raise RuntimeError("Нет активных мест. Сначала запусти generate_places.py")
            bookings = generate_bookings(meetings, places, args.seed, args.max_per_meeting)
            if not bookings:
                raise RuntimeError("Нет мест, подходящих по размеру группы, расписанию и времени встречи")
            print_statistics(bookings, len(meetings))
            if args.dry_run:
                print("Проверочный запуск: записи в БД не изменены")
                connection.rollback()
            else:
                save_bookings(cursor, bookings, args.replace)
                connection.commit()
                print(f"Успешно сохранено {len(bookings)} бронирований")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
