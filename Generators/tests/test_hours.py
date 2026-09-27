from datetime import date, datetime, time

from app.core.hours import is_open_at_all, latest_start, opening_windows


def test_regular_window_within_one_day():
    hours = {"thu": ["18:30", "22:00"]}
    day = date(2026, 10, 1)  # четверг
    windows = opening_windows(hours, day)
    assert windows == [(datetime(2026, 10, 1, 18, 30), datetime(2026, 10, 1, 22, 0))]


def test_overnight_window_spans_two_calendar_days():
    hours = {"wed": ["20:00", "02:00"], "thu": []}
    day = date(2026, 10, 1)  # четверг; смена началась в среду вечером
    windows = opening_windows(hours, day)
    assert windows == [(datetime(2026, 9, 30, 20, 0), datetime(2026, 10, 1, 2, 0))]


def test_closed_day_returns_no_windows():
    hours = {"thu": None}
    assert opening_windows(hours, date(2026, 10, 1)) == []


def test_latest_start_fits_all_three_limits():
    hours = {"thu": ["18:30", "22:00"]}
    day = date(2026, 10, 1)
    window_start = datetime(2026, 10, 1, 18, 0)
    window_end = datetime(2026, 10, 1, 23, 0)

    # ограничивает закрытие места (22:00 - 60 мин)
    assert latest_start(hours, day, window_start, window_end, 60) == datetime(2026, 10, 1, 21, 0)

    # ограничивает конец свободного окна компании
    tight_window_end = datetime(2026, 10, 1, 19, 30)
    assert latest_start(hours, day, window_start, tight_window_end, 60) == datetime(2026, 10, 1, 18, 30)


def test_too_short_window_gives_none():
    hours = {"thu": ["18:30", "19:00"]}
    day = date(2026, 10, 1)
    assert latest_start(hours, day, datetime(2026, 10, 1, 18, 0),
                        datetime(2026, 10, 1, 23, 0), 60) is None


def test_is_open_at_all_checks_overnight_arrival():
    hours = {"wed": ["20:00", "02:00"], "thu": []}
    day = date(2026, 10, 1)
    assert is_open_at_all(hours, day, datetime(2026, 10, 1, 0, 30),
                          datetime(2026, 10, 1, 2, 0), 30)
    assert not is_open_at_all(hours, day, datetime(2026, 10, 1, 3, 0),
                              datetime(2026, 10, 1, 5, 0), 30)


def test_find_free_start_skips_busy_slot():
    from app.core.hours import find_free_start
    hours = {"thu": ["18:00", "23:00"]}
    day = date(2026, 10, 1)
    busy = [(datetime(2026, 10, 1, 18, 0), datetime(2026, 10, 1, 19, 0))]

    start = find_free_start(hours, day, datetime(2026, 10, 1, 18, 0),
                            datetime(2026, 10, 1, 23, 0), 60, busy=busy, step_minutes=30)
    assert start == datetime(2026, 10, 1, 19, 0)


def test_find_free_start_none_when_fully_booked():
    from app.core.hours import find_free_start
    hours = {"thu": ["18:00", "20:00"]}
    day = date(2026, 10, 1)
    busy = [(datetime(2026, 10, 1, 18, 0), datetime(2026, 10, 1, 20, 0))]

    assert find_free_start(hours, day, datetime(2026, 10, 1, 18, 0),
                           datetime(2026, 10, 1, 20, 0), 60, busy=busy) is None
