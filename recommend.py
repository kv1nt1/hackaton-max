"""
Отбор мест с учётом времени в пути каждого участника.

Порядок (README, раздел 8): hard-фильтры (filters.filter_places) ->
routing для каждого участника -> отсев тех, кому ехать дольше его
лимита -> сортировка по справедливости: сначала минимальное МАКСИМАЛЬНОЕ
время в пути (10/10/60 хуже, чем 25/25/25), затем среднее, затем рейтинг.
"""

from filters import filter_places


def rank_places(graph, places, meeting, top_n=5):
    """
    Возвращает (results, stats).
    results — список dict {place, times: {user_id: минуты}, max, avg}.
    stats — сколько мест отсеялось на каждом этапе (для объяснений).
    """
    participants = list(meeting.participants.values())

    requirements = dict(meeting.requirements)
    requirements["group_size"] = len(participants)

    candidates = filter_places(places, requirements)
    stats = {
        "total": len(places),
        "after_filters": len(candidates),
        "too_far": 0,
        "unreachable": 0,
    }

    # один Dijkstra на участника
    distances = {}
    unreachable_people = set()

    for p in participants:
        home = graph.district_home_point(p.district)
        dist = graph.distances_from(*home, p.transport) if home else None

        if dist is None:
            unreachable_people.add(p.user_id)
        distances[p.user_id] = dist

    results = []

    for place in candidates:
        times = {}
        ok = True

        for p in participants:
            dist = distances[p.user_id]
            minutes = (
                dist.minutes_to(place["edge_id"], place["edge_position"])
                if dist else None
            )

            if minutes is None:
                stats["unreachable"] += 1
                ok = False
                break

            if minutes > p.max_minutes:
                stats["too_far"] += 1
                ok = False
                break

            times[p.user_id] = minutes

        if not ok:
            continue

        values = list(times.values())
        results.append({
            "place": place,
            "times": times,
            "max": max(values),
            "avg": sum(values) / len(values),
        })

    results.sort(key=lambda r: (
        r["max"], r["avg"], -float(r["place"].get("rating") or 0)
    ))

    stats["found"] = len(results)
    return results[:top_n], stats
