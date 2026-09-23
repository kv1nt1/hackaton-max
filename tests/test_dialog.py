from app.bot.dialog import DialogSession


def run_all(session):
    for payload in ["budget:pick:1500", "interests:toggle:food", "interests:done:",
                    "excluded_categories:done:", "indoor:pick:in", "food:pick:no",
                    "noise:pick:quiet"]:
        status = session.press(payload)
    return status


def test_full_flow_collects_requirements():
    s = DialogSession()
    assert run_all(s) == "done"
    assert s.requirements == {
        "budget_max": 1500, "required_interests": ["food"], "excluded_categories": [],
        "indoor": True, "food_required": False, "max_noise_level": "quiet",
    }


def test_stale_buttons_are_ignored_and_back_works():
    s = DialogSession()
    s.press("budget:pick:500")
    assert s.press("budget:pick:1000") == "stale"       # старая кнопка
    assert s.press("back:interests") == "redraw"
    assert s.current_step == "budget"


def test_edit_menu_changes_one_item_and_cancel_discards():
    done = DialogSession()
    run_all(done)

    edit = DialogSession(done.requirements, meeting_code="ABC123")
    assert not edit.is_done()
    text, rows = edit.render()
    assert "Бюджет: до 1500 ₽" in str(rows)

    assert edit.press("menu:edit:budget") == "redraw"
    assert edit.press("budget:pick:3000") == "redraw"   # вернулись в меню
    assert edit.requirements["budget_max"] == 3000
    assert edit.press("menu:done:") == "menu_done"

    # исходные требования не затронуты
    assert done.requirements["budget_max"] == 1500


def test_text_input_fallback():
    s = DialogSession()
    ok, _ = s.submit("2500")
    assert ok and s.requirements["budget_max"] == 2500
    ok, error = DialogSession().submit("много")
    assert not ok and error
