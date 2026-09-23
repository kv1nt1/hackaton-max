import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "generators"))   # для generate_city

os.environ.setdefault("MAX_BOT_TOKEN", "test-token")


@pytest.fixture(scope="session")
def city():
    """Настоящий граф города из генератора (без БД)."""
    import generate_city as gc

    gc.roads.clear()
    gc.generate_avenues()
    gc.generate_streets()
    gc.generate_local_roads()
    gc.generate_pedestrian_roads()

    nodes = gc.generate_nodes()
    edges = gc.generate_edges(nodes)
    for i, edge in enumerate(edges, start=1):
        edge["id"] = i

    return nodes, edges


@pytest.fixture(scope="session")
def graph(city):
    from app.core.routing import CityGraph

    return CityGraph(*city)


@pytest.fixture(scope="session")
def places(graph):
    """Синтетические места на случайных рёбрах."""
    rnd = random.Random(3)
    cats = [
        ("cafe", ["food", "coffee"], True, "quiet"),
        ("bowling", ["games", "active"], True, "loud"),
        ("bar", ["drinks", "social"], True, "medium"),
        ("park_activity", ["outdoor", "walking"], False, "quiet"),
    ]
    edges = list(graph.edges.values())
    result = []

    for i in range(1, 150):
        cat, interests, indoor, noise = rnd.choice(cats)
        edge = rnd.choice(edges)
        result.append(dict(
            id=i, name=f"{cat}-{i}", category=cat,
            district=graph.nodes[edge["node_from"]]["district"],
            price_min=100, price_avg=300, price_max=rnd.choice([500, 900, 1500]),
            interests=interests, tags=[], min_group_size=1, max_group_size=10,
            indoor=indoor, food_available=cat in ("cafe", "bar"),
            alcohol_available=False, noise_level=noise,
            rating=round(rnd.uniform(3, 5), 1), reviews_count=5,
            booking_required=False, avg_duration_minutes=90,
            edge_id=edge["id"], edge_position=rnd.random(),
        ))

    return result
