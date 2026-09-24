"""Сценарии бота целиком: стартовое меню, комната с приглашениями, режим «самостоятельно»."""

import re

import pytest

from app.bot.bot import Bot
from app.max_api import client as max_client


class FakeClient(max_client.MaxClient):
    def __init__(self):
        super().__init__()
        self.sent = []          # (user_id, text)

    def _request(self, method, path, params=None, json_body=None, timeout=None):
        if path == "/messages":
            self.sent.append((params["user_id"], json_body["text"]))
        elif path == "/answers":
            message = (json_body or {}).get("message")
            self.sent.append((None, (message or {}).get("text") or (json_body or {}).get("notification")))
        return {}

    def _throttle(self, target_id):
        pass


@pytest.fixture
def bot(graph, places, monkeypatch):
    import app.bot.bot as bot_module

    monkeypatch.setattr(bot_module, "get_places", lambda: places)
    monkeypatch.setattr(bot_module, "get_city_graph", lambda: graph)
    b = Bot(FakeClient())
    b.bot_username = "testbot"
    return b


def press(bot, user, payload, name="U"):
    bot.handle_update({"update_type": "message_callback", "callback": {
        "callback_id": "c", "payload": payload, "user": {"user_id": user, "first_name": name}}})


def say(bot, user, text, name="U"):
    bot.handle_update({"update_type": "message_created", "message": {
        "sender": {"user_id": user, "first_name": name}, "body": {"text": text}}})


def last_to(bot, user):
    return [t for u, t in bot.client.sent if u == user][-1]


def fill_room_profile(bot, user, name, interests, budget, district, transport, minutes):
    for tag in interests:
        press(bot, user, f"p:interests:toggle:{tag}", name)
    for p in ["p:interests:done:", f"p:budget:pick:{budget}", f"p:district:pick:{district}",
              f"p:transport:pick:{transport}", f"p:minutes:pick:{minutes}"]:
        press(bot, user, p, name)


def create_room(bot):
    say(bot, 1, "/start", "Аня")
    assert "Создать комнату" in str(bot.client.sent[-1]) or "Комната" in last_to(bot, 1)
    press(bot, 1, "home:room", "Аня")
    fill_room_profile(bot, 1, "Аня", ["coffee", "food"], 1500, "downtown", "car", 30)
    return list(bot.meetings._meetings)[0]


# ------------------------------------------------------------------ старт

def test_start_shows_two_modes(bot):
    say(bot, 1, "/start", "Аня")
    text = last_to(bot, 1)
    assert "Комната" in text and "Самостоятельно" in text


# ------------------------------------------------------------------ комната

def test_room_invite_join_and_search_by_frequent_interests(bot):
    code = create_room(bot)
    assert any(f"start={code}" in t for u, t in bot.client.sent if u == 1)

    bot.handle_update({"update_type": "bot_started", "payload": code,
                       "user": {"user_id": 2, "first_name": "Борис"}})
    fill_room_profile(bot, 2, "Борис", ["coffee", "games"], 1000, "south", "walk", 60)

    say(bot, 3, f"/join {code.lower()}", "Вика")
    fill_room_profile(bot, 3, "Вика", ["coffee"], 2000, "university", "car", 30)

    meeting = bot.meetings.get(code)
    assert len(meeting.participants) == 3
    assert "присоединил" in last_to(bot, 1)
    assert "Популярные интересы: Кофе (3)" in bot.card_text(meeting)

    press(bot, 2, f"m:find:{code}", "Борис")          # искать может только организатор
    assert not any("Места для комнаты" in t for _, t in bot.client.sent)

    press(bot, 1, f"m:find:{code}", "Аня")
    for user in (1, 2, 3):                             # результат получают все
        text = last_to(bot, user)
        assert "Места для комнаты" in text
        assert "Кофе (3 из 3)" in text                 # самый частый тег
        assert "Совпало" in text


def test_room_results_are_russian(bot):
    code = create_room(bot)
    press(bot, 1, f"m:find:{code}", "Аня")
    text = last_to(bot, 1)
    without_names = re.sub(r"\d+\. \S+ — ", "N. — ", text).replace(code, "")
    assert re.findall(r"[A-Za-z]{3,}", without_names) == []


def test_edit_room_conditions_keeps_room(bot):
    code = create_room(bot)
    press(bot, 1, f"m:reqs:{code}", "Аня")
    press(bot, 1, "menu:edit:indoor", "Аня")
    press(bot, 1, "indoor:pick:in", "Аня")
    press(bot, 1, "menu:done:", "Аня")

    assert list(bot.meetings._meetings) == [code]
    assert bot.meetings.get(code).requirements["indoor"] is True


def test_only_organizer_controls_room_and_unknown_code(bot):
    code = create_room(bot)
    bot.handle_update({"update_type": "bot_started", "payload": code,
                       "user": {"user_id": 2, "first_name": "Борис"}})
    fill_room_profile(bot, 2, "Борис", [], 1000, "south", "walk", 60)

    press(bot, 2, f"m:reqs:{code}", "Борис")
    assert "только организатор" in bot.client.sent[-1][1]

    say(bot, 9, "/join ZZZZZZ", "X")
    assert "не найдена" in last_to(bot, 9)


def test_room_budget_is_minimum_of_participants(bot):
    from app.core.recommend import rank_places
    code = create_room(bot)                       # бюджет Ани 1500
    bot.handle_update({"update_type": "bot_started", "payload": code,
                       "user": {"user_id": 2, "first_name": "Борис"}})
    fill_room_profile(bot, 2, "Борис", [], 500, "south", "walk", 60)   # бюджет Бориса 500

    press(bot, 1, f"m:find:{code}", "Аня")
    text = last_to(bot, 1)
    prices = [int(m) for m in re.findall(r"💰 \d+–(\d+) ₽", text)]
    assert prices and all(p <= 500 * 1.5 for p in prices)   # ориентир — самый скромный бюджет


# ------------------------------------------------------------------ самостоятельно

def test_solo_flow_without_room(bot):
    say(bot, 1, "/start", "Аня")
    press(bot, 1, "home:solo", "Аня")
    for p in ["budget:pick:1500", "interests:toggle:coffee", "interests:done:",
              "excluded_categories:done:", "indoor:pick:any", "food:pick:no", "noise:pick:any"]:
        press(bot, 1, p, "Аня")

    assert "Сколько человек" in last_to(bot, 1)
    press(bot, 1, "solo:size:2", "Аня")

    assert "Участник 1 из 2" in last_to(bot, 1)
    for p in ["p:district:pick:downtown", "p:transport:pick:car", "p:minutes:pick:30"]:
        press(bot, 1, p, "Аня")
    assert "Участник 2 из 2" in last_to(bot, 1)
    for p in ["p:district:pick:south", "p:transport:pick:walk", "p:minutes:pick:60"]:
        press(bot, 1, p, "Аня")

    text = last_to(bot, 1)
    assert "Подбор мест" in text
    assert bot.meetings._meetings == {}            # комната не создавалась
    assert "Участник 1" in text and "Участник 2" in text


def test_solo_group_size_by_text_and_validation(bot):
    say(bot, 1, "/start", "Аня")
    press(bot, 1, "home:solo", "Аня")
    for p in ["budget:pick:1500", "interests:done:", "excluded_categories:done:",
              "indoor:pick:any", "food:pick:no", "noise:pick:any"]:
        press(bot, 1, p, "Аня")

    say(bot, 1, "много", "Аня")
    assert "число" in last_to(bot, 1)
    say(bot, 1, "3", "Аня")
    assert "Участник 1 из 3" in last_to(bot, 1)


def test_network_error_becomes_short_api_error():
    import requests

    class Broken(requests.Session):
        def request(self, *a, **k):
            raise requests.exceptions.ProxyError("boom")

    c = max_client.MaxClient()
    c.session = Broken()
    with pytest.raises(max_client.MaxApiError) as info:
        c.get_updates()
    assert info.value.status_code == 0
