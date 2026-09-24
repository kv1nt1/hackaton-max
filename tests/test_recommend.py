from app.bot.meetings import Meeting, Participant
from app.core.recommend import interest_frequencies, rank_places


def make_place(pid, interests, edge_id, **extra):
    base = dict(
        id=pid, name=f"p{pid}", category="cafe", district="downtown",
        price_min=100, price_avg=300, price_max=500, interests=interests,
        tags=[], min_group_size=1, max_group_size=10, indoor=True,
        food_available=True, alcohol_available=False, noise_level="quiet",
        rating=4.0, reviews_count=5, booking_required=False,
        avg_duration_minutes=60, edge_id=edge_id, edge_position=0.5,
    )
    base.update(extra)
    return base


def meeting_of(people, requirements=None):
    return Meeting(code="T", organizer_id=1, requirements=requirements or {},
                   participants={p.user_id: p for p in people})


def person(uid, interests, budget=1500, district="downtown"):
    return Participant(user_id=uid, name=f"P{uid}", district=district,
                       transport="car", max_minutes=60, interests=interests, budget=budget)


def test_frequency_counts_people_not_tags():
    people = [person(1, ["coffee", "games"]), person(2, ["coffee"]), person(3, ["food"])]
    freq = interest_frequencies(people)
    assert freq["coffee"] == 2 and freq["games"] == 1 and freq["food"] == 1


def test_shared_interests_apply_to_everyone_when_personal_empty():
    people = [person(1, []), person(2, [])]
    freq = interest_frequencies(people, shared_interests=["coffee"])
    assert freq["coffee"] == 2


def test_more_popular_tags_rank_higher(graph):
    eid = graph.district_home_point("downtown")[0]
    places = [
        make_place(1, ["games"], eid),                  # 1 человек
        make_place(2, ["coffee"], eid),                 # 3 человека
        make_place(3, ["coffee", "games"], eid),        # 3 + 1
        make_place(4, ["music"], eid),                  # никто — штраф
    ]
    people = [person(1, ["coffee", "games"]), person(2, ["coffee"]), person(3, ["coffee"])]

    results, stats = rank_places(graph, places, meeting_of(people), top_n=10)
    order = [r["place"]["id"] for r in results]

    assert order[:3] == [3, 2, 1]
    assert order[-1] == 4 and not results[-1]["perfect"]
    assert stats["top_tags"][0] == ("coffee", 3)


def test_budget_is_minimum_of_participants(graph):
    eid = graph.district_home_point("downtown")[0]
    places = [make_place(1, ["coffee"], eid, price_max=400),
              make_place(2, ["coffee"], eid, price_max=1400)]
    people = [person(1, ["coffee"], budget=2000), person(2, ["coffee"], budget=500)]

    results, _ = rank_places(graph, places, meeting_of(people), top_n=10)
    ids = {r["place"]["id"]: r for r in results}

    assert ids[1]["perfect"]        # 400 укладывается в самый скромный бюджет (500)
    assert 2 not in ids             # 1400 > 500 * 1.5 — отсечено жёстко


def test_slightly_over_budget_is_shown_with_warning(graph):
    eid = graph.district_home_point("downtown")[0]
    places = [make_place(1, ["coffee"], eid, price_max=700)]      # 500 < 700 <= 750
    people = [person(1, ["coffee"], budget=500)]

    results, _ = rank_places(graph, places, meeting_of(people), top_n=5)

    assert len(results) == 1 and not results[0]["perfect"]
    assert any("бюджет" in w for w in results[0]["warnings"])
