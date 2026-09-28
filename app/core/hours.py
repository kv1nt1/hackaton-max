"""
Время работы заведения (opening_hours из places) и совмещение его со
свободным окном компании.

Формат в БД: {"mon": ["10:00", "23:00"], ...}, ключи — сокращения дня
недели, значение может быть None/[]/отсутствовать (выходной). Если время
закрытия меньше времени открытия, заведение работает через полночь —
тогда его окно в день X кончается уже в день X+1.
"""

from datetime import date as date_cls
from datetime import datetime, time, timedelta

_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _parse(value):
    if not value or len(value) != 2:
        return None
    opens, closes = value
    return time.fromisoformat(opens), time.fromisoformat(closes)


def opening_windows(opening_hours, day: date_cls):
    """
    Все интервалы работы места, задевающие календарный день `day`:
    вчерашняя смена, если она заходит за полночь, и сегодняшняя.
    Возвращает список (start: datetime, end: datetime).
    """
    windows = []

    for opening_day in (day - timedelta(days=1), day):
        parsed = _parse((opening_hours or {}).get(_WEEKDAYS[opening_day.weekday()]))
        if parsed is None:
            continue

        opens, closes = parsed
        start = datetime.combine(opening_day, opens)
        end = datetime.combine(opening_day, closes)
        if closes <= opens:            # через полночь
            end += timedelta(days=1)

        if end > datetime.combine(day, time.min):
            windows.append((start, end))

    return windows


def latest_start(opening_hours, day, window_start, window_end, duration_minutes):
    """
    Самое позднее время начала визита, при котором компания успевает
    приехать (не раньше window_start), место ещё открыто, и визит
    длительностью duration_minutes заканчивается и до закрытия, и до
    конца свободного окна компании (window_end).

    Возвращает datetime или None, если в этот день попасть некуда.
    """
    duration = timedelta(minutes=duration_minutes)
    best = None

    for opens, closes in opening_windows(opening_hours, day):
        earliest = max(window_start, opens)
        latest = min(window_end, closes) - duration

        if earliest <= latest and (best is None or latest > best):
            best = latest

    return best


def is_open_at_all(opening_hours, day, window_start, window_end, duration_minutes):
    return latest_start(opening_hours, day, window_start, window_end, duration_minutes) is not None


def _overlaps(start, end, busy):
    return any(start < b_end and end > b_start for b_start, b_end in busy)


def find_free_start(opening_hours, day, window_start, window_end, duration_minutes,
                    busy=(), step_minutes=30):
    """
    Первое свободное время начала визита: место открыто, визит помещается
    в свободное окно компании и не пересекается ни с одной бронью из busy
    (список (starts_at, ends_at)). Перебор с шагом step_minutes.
    Возвращает datetime или None.
    """
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)
    candidates = []

    for opens, closes in opening_windows(opening_hours, day):
        earliest = max(window_start, opens)
        latest = min(window_end, closes) - duration
        if earliest <= latest:
            candidates.append((earliest, latest))

    for earliest, latest in sorted(candidates):
        t = earliest
        while t <= latest:
            if not _overlaps(t, t + duration, busy):
                return t
            t += step

    return None
