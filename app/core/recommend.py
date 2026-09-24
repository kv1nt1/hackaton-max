"""
Отбор мест с учётом интересов и времени в пути каждого участника.

Порядок (README, раздел 8):
  1. Жёсткие условия (filters.evaluate_place): место вмещает компанию,
     категория не исключена, цена не выше бюджета больше чем на 50%.
     Бюджет компании — минимальный из бюджетов участников.
  2. Routing для каждого участника (routing.py).
  3. Интересы: считаем, у скольких участников встречается каждый тег.
     Чем больше людей отметили теги места, тем выше его «интерес-балл».
     Место, не совпавшее ни с одним интересом компании, получает штраф.
  4. Остальные мягкие условия дают штраф (см. filters.py), время в пути
     сверх лимита — тоже (до +50% к личному лимиту).
  5. Сортировка: штраф -> интерес-балл (больше лучше) -> МАКСИМАЛЬНОЕ время
     в пути (справедливость) -> среднее время -> рейтинг.

Машинное обучение здесь не нужно: это подсчёт частот и взвешенная оценка.
"""

from collections import Counter

from app.core.filters import PENALTY_INTERESTS, evaluate_place

TRAVEL_TOLERANCE = 1.5     # до +50% к лимиту времени в пути
PENALTY_TRAVEL = 2
UNLIMITED_BUDGET = 1_000_000


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


def rank_places(graph, places, meeting, top_n=5):
    """
    Возвращает (results, stats).
    results — список dict:
        place, times {user_id: минуты}, max, avg,
        matched [(тег, сколько участников)], interest_score,
        penalty, warnings [текст], perfect (bool)
    """
    participants = list(meeting.participants.values())
    n = len(participants)

    requirements = dict(meeting.requirements)
    requirements["group_size"] = n

    freq = interest_frequencies(participants, requirements.get("required_interests") or [])
    requirements["required_interests"] = []      # интересы проверяем ниже сами

    budgets = [p.budget for p in participants if p.budget]
    if budgets:
        requirements["budget_max"] = min(budgets)
    requirements.setdefault("budget_max", UNLIMITED_BUDGET)

    stats = {
        "total": len(places),
        "participants": n,
        "top_tags": freq.most_common(5),
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

        # ---- интересы
        matched = sorted(
            ((t, freq[t]) for t in (place["interests"] or []) if t in freq),
            key=lambda x: -x[1],
        )
        interest_score = sum(count for _, count in matched)

        if freq and not matched:
            penalty += PENALTY_INTERESTS
            warnings.append("нет совпадений по интересам")

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

        values = list(times.values())
        results.append({
            "place": place,
            "times": times,
            "max": max(values),
            "avg": sum(values) / len(values),
            "matched": matched,
            "interest_score": interest_score,
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
