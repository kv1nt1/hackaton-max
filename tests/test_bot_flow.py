"""Сценарий целиком: организатор + друзья по приглашению -> поиск с маршрутами."""

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


def create_meeting(bot):
    bot.handle_update({"update_type": "bot_started", "user": {"user_id": 1, "first_name": "Аня"}})
    for p in ["budget:pick:1500", "interests:done:", "excluded_categories:done:",
              "indoor:pick:in", "food:pick:no", "noise:pick:any",
              "p:district:pick:downtown", "p:transport:pick:car", "p:minutes:pick:30"]:
        press(bot, 1, p, "Аня")
    return list(bot.meetings._meetings)[0]


def test_invite_join_and_search(bot):
    code = create_meeting(bot)
    assert f"start={code}" in [t for u, t in bot.client.sent if u == 1 and "start=" in t][0]

    # друг по deep-link, второй — командой /join
    bot.handle_update({"update_type": "bot_started", "payload": code,
                       "user": {"user_id": 2, "first_name": "Борис"}})
    for p in ["p:district:pick:south", "p:transport:pick:walk", "p:minutes:pick:60"]:
        press(bot, 2, p, "Борис")
    say(bot, 3, f"/join {code.lower()}", "Вика")
    for p in ["p:district:pick:university", "p:transport:pick:car", "p:minutes:pick:30"]:
        press(bot, 3, p, "Вика")

    assert len(bot.meetings.get(code).participants) == 3
    assert "присоединил" in last_to(bot, 1)

    press(bot, 2, f"m:find:{code}", "Борис")       # искать может только организатор
    assert not any("Лучшие" in t or "Места для" in t for _, t in bot.client.sent)

    press(bot, 1, f"m:find:{code}", "Аня")
    for user in (1, 2, 3):                          # результат получают все
        assert "Места для встречи" in last_to(bot, user)


def test_results_are_russian(bot):
    code = create_meeting(bot)
    press(bot, 1, f"m:find:{code}", "Аня")
    text = last_to(bot, 1)
    without_names = re.sub(r"\d+\. \S+ — ", "N. — ", text).replace(code, "")
    assert re.findall(r"[A-Za-z]{3,}", without_names) == []


def test_edit_requirements_keeps_meeting(bot):
    code = create_meeting(bot)
    press(bot, 1, f"m:reqs:{code}", "Аня")
    press(bot, 1, "menu:edit:budget", "Аня")
    press(bot, 1, "budget:pick:5000", "Аня")
    press(bot, 1, "menu:done:", "Аня")

    assert list(bot.meetings._meetings) == [code]
    assert bot.meetings.get(code).requirements["budget_max"] == 5000


def test_only_organizer_can_edit_and_unknown_code(bot):
    code = create_meeting(bot)
    bot.handle_update({"update_type": "bot_started", "payload": code,
                       "user": {"user_id": 2, "first_name": "Борис"}})
    for p in ["p:district:pick:south", "p:transport:pick:walk", "p:minutes:pick:60"]:
        press(bot, 2, p, "Борис")

    press(bot, 2, f"m:reqs:{code}", "Борис")
    assert "только организатор" in bot.client.sent[-1][1]

    say(bot, 9, "/join ZZZZZZ", "X")
    assert "не найдена" in last_to(bot, 9)


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
