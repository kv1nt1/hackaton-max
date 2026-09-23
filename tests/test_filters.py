import random

from app.core.filters import evaluate_place, filter_places


def test_soft_mode_without_violations_equals_strict_filter():
    rnd = random.Random(5)
    cats = ["cafe", "bar", "bowling", "park_activity"]
    ints = ["food", "games", "outdoor", "music", "coffee"]

    places = [dict(
        id=i, category=rnd.choice(cats), price_max=rnd.choice([200, 600, 1200, 2500]),
        min_group_size=rnd.choice([1, 2, 4]), max_group_size=rnd.choice([4, 8, 12]),
        interests=rnd.sample(ints, 2), indoor=rnd.random() < 0.6,
        food_available=rnd.random() < 0.5, noise_level=rnd.choice(["quiet", "medium", "loud"]),
    ) for i in range(1500)]

    for _ in range(200):
        req = dict(
            budget_max=rnd.choice([300, 800, 1500, 100000]),
            group_size=rnd.randint(1, 10),
            required_interests=rnd.sample(ints, rnd.randint(0, 2)),
            excluded_categories=rnd.sample(cats, rnd.randint(0, 1)),
            indoor=rnd.choice([True, False, None]),
            food_required=rnd.random() < 0.4,
            max_noise_level=rnd.choice(["quiet", "medium", None]),
        )
        strict = {p["id"] for p in filter_places(places, req)}
        soft = {p["id"] for p in places if evaluate_place(p, req) == []}
        assert strict == soft


def test_hard_constraints_are_never_relaxed():
    place = dict(category="bar", price_max=5000, min_group_size=1, max_group_size=4,
                 interests=[], indoor=True, food_available=False, noise_level="loud")
    base = dict(budget_max=1000, group_size=3, excluded_categories=[])

    assert evaluate_place(place, base) is None                             # слишком дорого
    assert evaluate_place({**place, "price_max": 800}, {**base, "group_size": 9}) is None
    assert evaluate_place({**place, "price_max": 800},
                          {**base, "excluded_categories": ["bar"]}) is None
