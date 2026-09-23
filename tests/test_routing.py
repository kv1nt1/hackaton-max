"""Routing сверяется с независимым «эталонным» Dijkstra на графе со вставленными точками."""

import heapq
import random

from app.core.routing import CityGraph


def reference_minutes(edges, a, b, mode):
    adj = {}

    def add(u, v, w):
        adj.setdefault(u, []).append((v, w))
        adj.setdefault(v, []).append((u, w))

    points = {"A": a, "B": b}

    for e in edges:
        full = CityGraph._full_edge_minutes(e, mode)
        if full is None:
            continue
        on = sorted((p[1], k) for k, p in points.items() if p[0] == e["id"])
        chain = [(0, e["node_from"])] + on + [(1, e["node_to"])]
        for (p1, n1), (p2, n2) in zip(chain, chain[1:]):
            add(n1, n2, (p2 - p1) * full)

    dist, heap = {"A": 0}, [(0, "A")]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, 1e18):
            continue
        for v, w in adj.get(u, []):
            if d + w < dist.get(v, 1e18):
                dist[v] = d + w
                heapq.heappush(heap, (d + w, v))
    return dist.get("B")


def test_matches_reference(graph, city):
    _, edges = city
    rnd = random.Random(1)
    ids = [e["id"] for e in edges]

    for _ in range(150):
        mode = rnd.choice(["walk", "car"])
        a = (rnd.choice(ids), rnd.random())
        b = (a[0], rnd.random()) if rnd.random() < 0.2 else (rnd.choice(ids), rnd.random())

        pd = graph.distances_from(a[0], a[1], mode)
        got = pd.minutes_to(*b) if pd else None
        ref = reference_minutes(edges, a, b, mode) if pd else None

        assert (got is None) == (ref is None)
        if got is not None:
            assert abs(got - ref) < 1e-6


def test_river_forces_detour_over_bridge(graph):
    south = graph.district_home_point("south")
    downtown = graph.district_home_point("downtown")

    car = graph.distances_from(*south, "car").minutes_to(*downtown)
    walk = graph.distances_from(*south, "walk").minutes_to(*downtown)

    assert car is not None and walk is not None
    assert walk > car * 3          # пешком заметно дольше, чем на машине


def test_every_district_has_home_point(graph):
    for district in ("university", "downtown", "mall", "south", "park", "north"):
        assert graph.district_home_point(district) is not None
