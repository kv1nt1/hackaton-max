"""
Отбор мест с учётом времени в пути каждого участника.

Порядок (README, раздел 8):
  1. Жёсткие условия (filters.evaluate_place): место вмещает компанию,
     категория не исключена, цена не выше бюджета больше чем на 50%.
  2. Routing для каждого участника (routing.py).
  3. Мягкие условия дают штраф: бюджет, интересы, помещение/улица, еда,
     шум и время в пути (до +50% к личному лимиту).
  4. Сортировка: меньше штраф -> меньше МАКСИМАЛЬНОЕ время в пути
     (справедливость: 25/25/25 лучше, чем 10/10/60) -> среднее время ->
     рейтинг.

Места без штрафа подходят полностью; остальные «почти подходят», и для
каждого перечислено, что именно не совпало. Машинное обучение здесь не
нужно: это обычная взвешенная оценка, веса лежат в filters.py.
"""

from app.core.filters import evaluate_place

TRAVEL_TOLERANCE = 1.5     # до +50% к лимиту времени в пути
PENALTY_TRAVEL = 2


def rank_places(graph, places, meeting, top_n=5):
    """
    Возвращает (results, stats).
    results — список dict:
        place, times {user_id: минуты}, max, avg,
        penalty, warnings [текст], perfect (bool)
    """
    participants = list(meeting.participants.values())

    requirements = dict(meeting.requirements)
    requirements["group_size"] = len(participants)

    stats = {
        "total": len(places),
        "hard_excluded": 0,   # не вмещает компанию / исключённая категория / слишком дорого
        "unreachable": 0,     # нельзя добраться выбранным транспортом
        "too_far": 0,         # дальше лимита больше чем на 50%
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

        values = list(times.values())
        results.append({
            "place": place,
            "times": times,
            "max": max(values),
            "avg": sum(values) / len(values),
            "penalty": penalty,
            "warnings": warnings,
            "perfect": penalty == 0,
        })

    results.sort(key=lambda r: (
        r["penalty"], r["max"], r["avg"], -float(r["place"].get("rating") or 0)
    ))

    stats["perfect"] = sum(1 for r in results if r["perfect"])
    stats["relaxed"] = len(results) - stats["perfect"]

    return results[:top_n], stats
