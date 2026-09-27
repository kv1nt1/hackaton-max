"""
Отбор мест: интересы компании, время в пути, часы работы, брони.

Порядок:
  1. Жёсткие условия (filters.evaluate_place): место вмещает компанию,
     категория не исключена, цена не выше бюджета больше чем на 50%.
     Бюджет компании — минимальный из бюджетов участников.
  2. Интересы: считаем, у скольких участников встречается каждый тег.
     Вместо того чтобы искать сразу по ВСЕМ тегам компании (когда людей
     много, это может быть 15-20 разных интересов, и почти любое место
     хоть чем-то да зацепится), берём только TOP_K самых частых — то,
     что реально объединяет компанию, — и ищем по ним.
  3. Routing для каждого участника (routing.py) — жёсткое отсечение,
     если до места не добраться выбранным транспортом.
  4. Часы работы (hours.py): смотрим общее свободное окно компании
     (пересечение окон участников) в выбранный день и считаем, влезает
     ли туда визит средней длительности. Не влезает — штраф.
  5. Существующие брони (bot_bookings): если на весь пересчитанный слот
     нет свободного времени — штраф «часто занято».
  6. Остальные мягкие условия (indoor/food/noise/бюджет/дорога) —
     штрафы, как раньше.
  7. Сортировка: штраф -> интерес-балл (больше лучше) -> максимальное
     время в пути (справедливость) -> среднее время -> рейтинг.

Машинное обучение здесь не нужно: это подсчёт частот и взвешенная оценка.
"""

from collections import Counter
from datetime import datetime, time

from app.core.filters import PENALTY_INTERESTS, evaluate_place
from app.core.hours import find_free_start, is_open_at_all

TRAVEL_TOLERANCE = 1.5     # до +50% к лимиту времени в пути
PENALTY_TRAVEL = 2
PENALTY_HOURS = 3          # место не работает в общее окно компании
PENALTY_BOOKED = 4         # в это время место, скорее всего, занято
UNLIMITED_BUDGET = 1_000_000

TOP_K_INTERESTS = 3        # сколько самых частых тегов реально ищем


def interest_frequencies(participants, shared_interests=()):
    """
    Сколько участников отметили каждый интерес. Если у участника свои
    интересы не заданы, берутся общие (режим «самостоятельно»).
    """
    freq = Counter()

    for p in participants:
        tags = set(p.interests) or set(shared_interests)
        freq.update(tags)

    return freq


def top_interests(freq, top_k=TOP_K_INTERESTS):
    """
    Самые частые теги компании (не более top_k). Тег должен встречаться
    хотя бы у двух участников, если такие вообще есть, — единичные
    случайные предпочтения в общий поиск не берём (при 1-2 участниках
    порог не действует, иначе не искали бы вообще ничего).
    """
    if not freq:
        return set()

    popular = {t: c for t, c in freq.items() if c >= 2}
    pool = popular or dict(freq)

    ranked = sorted(pool.items(), key=lambda x: (-x[1], x[0]))
    return {t for t, _ in ranked[:top_k]}


def common_availability_window(participants, meeting_date):
    """
    Пересечение личных окон участников (available_from/until) на
    meeting_date. Если пересечения нет — компания расходится в свободном
    времени; тогда берём объединение (шире), чтобы не остаться совсем
    без вариантов, и просим уточнить время отдельно.
    """
    starts = [p.available_from for p in participants]
    ends = [p.available_until for p in participants]

    common_from, common_until = max(starts), min(ends)
    has_overlap = common_from < common_until

    if not has_overlap:
        common_from, common_until = min(starts), max(ends)

    window_start = datetime.combine(meeting_date, common_from)
    window_end = datetime.combine(meeting_date, common_until)
    return window_start, window_end, has_overlap


def rank_places(graph, places, meeting, top_n=5, bookings_by_place=None):
    """
    Возвращает (results, stats).

    bookings_by_place: {place_id: [(starts_at, ends_at), ...]} — уже
    существующие подтверждённые брони. Если не передано, проверка
    занятости не выполняется (например, нет подключения к БД).

    results — список dict:
        place, times {user_id: минуты}, max, avg,
        matched [(тег, сколько участников)], interest_score,
        suggested_start (datetime | None),
        penalty, warnings [текст], perfect (bool)
    """
    participants = list(meeting.participants.values())
    n = len(participants)
    bookings_by_place = bookings_by_place or {}

    requirements = dict(meeting.requirements)
    requirements["group_size"] = n

    all_freq = interest_frequencies(participants, requirements.get("required_interests") or [])
    focus = top_interests(all_freq)
    requirements["required_interests"] = []      # интересы проверяем сами, ниже

    budgets = [p.budget for p in participants if p.budget]
    if budgets:
        requirements["budget_max"] = min(budgets)
    requirements.setdefault("budget_max", UNLIMITED_BUDGET)

    window_start, window_end, has_common_window = common_availability_window(
        participants, meeting.date
    )

    stats = {
        "total": len(places),
        "participants": n,
        "top_tags": sorted(((t, all_freq[t]) for t in focus), key=lambda x: -x[1]),
        "all_tags": all_freq.most_common(),
        "date": meeting.date,
        "window": (window_start, window_end),
        "has_common_window": has_common_window,
        "hard_excluded": 0,
        "unreachable": 0,
        "too_far": 0,
        "perfect": 0,
        "relaxed": 0,
    }

    # один Dijkstra на участника
    distances = {}
    for p in participants:
        home = graph.district_home_point(p.district)
        distances[p.user_id] = (
            graph.distances_from(*home, p.transport) if home else None
        )

    results = []

    for place in places:
        violations = evaluate_place(place, requirements)

        if violations is None:
            stats["hard_excluded"] += 1
            continue

        warnings = [text for _, _, text in violations]
        penalty = sum(weight for _, weight, _ in violations)

        # ---- интересы (только по самым частым тегам компании)
        place_tags = set(place["interests"] or [])
        matched = sorted(
            ((t, all_freq[t]) for t in place_tags if t in focus),
            key=lambda x: -x[1],
        )
        interest_score = sum(count for _, count in matched)

        if focus and not matched:
            penalty += PENALTY_INTERESTS
            warnings.append("не входит в самые частые интересы компании")

        # ---- дорога
        times = {}
        skip = None

        for p in participants:
            dist = distances[p.user_id]
            minutes = (
                dist.minutes_to(place["edge_id"], place["edge_position"])
                if dist else None
            )

            if minutes is None:
                skip = "unreachable"
                break

            if minutes > p.max_minutes * TRAVEL_TOLERANCE:
                skip = "too_far"
                break

            if minutes > p.max_minutes:
                penalty += PENALTY_TRAVEL
                warnings.append(
                    f"{p.name}: дорога {round(minutes)} мин (лимит {p.max_minutes})"
                )

            times[p.user_id] = minutes

        if skip:
            stats[skip] += 1
            continue

        # ---- часы работы и брони
        suggested_start = None
        duration = place.get("avg_duration_minutes") or 60
        opening_hours = place.get("opening_hours") or {}

        if not is_open_at_all(opening_hours, meeting.date, window_start, window_end, duration):
            penalty += PENALTY_HOURS
            warnings.append("не работает в общее свободное время компании")
        else:
            busy = bookings_by_place.get(place["id"], [])
            suggested_start = find_free_start(
                opening_hours, meeting.date, window_start, window_end, duration, busy=busy,
            )
            if suggested_start is None:
                penalty += PENALTY_BOOKED
                warnings.append("похоже, в это время уже занято другой компанией")

        if not has_common_window:
            warnings.append("у участников нет общего свободного времени — уточните отдельно")

        values = list(times.values())
        results.append({
            "place": place,
            "times": times,
            "max": max(values),
            "avg": sum(values) / len(values),
            "matched": matched,
            "interest_score": interest_score,
            "suggested_start": suggested_start,
            "duration_minutes": duration,
            "penalty": penalty,
            "warnings": warnings,
            "perfect": penalty == 0,
        })

    results.sort(key=lambda r: (
        r["penalty"], -r["interest_score"], r["max"], r["avg"],
        -float(r["place"].get("rating") or 0),
    ))

    stats["perfect"] = sum(1 for r in results if r["perfect"])
    stats["relaxed"] = len(results) - stats["perfect"]

    return results[:top_n], stats
