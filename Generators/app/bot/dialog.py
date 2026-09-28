"""
Диалог сбора требований встречи (с кнопками).

Вопросы: budget -> interests -> excluded_categories -> indoor -> food -> noise.

Два режима:
  * создание встречи — вопросы идут по порядку, есть «⬅️ Назад»;
  * редактирование готовой встречи — DialogSession(requirements): бот
    показывает меню со всеми пунктами и текущими значениями, можно
    поменять любой один пункт и вернуться, не создавая встречу заново.

Формат payload кнопок:
    "<шаг>:<действие>:<значение>"   pick / toggle / done
    "back:<шаг>"                    назад (в режиме правки пункта — отмена)
    "menu:edit:<шаг>"               меню: изменить пункт
    "menu:done:" / "menu:cancel:"   меню: сохранить / отменить изменения
    "restart"                       начать заново
Шаг внутри payload нужен, чтобы игнорировать старые кнопки.
"""

from app.dictionaries import CATEGORIES, INTERESTS, category_name, interest_name

STEP_BUDGET = "budget"
STEP_INTERESTS = "interests"
STEP_EXCLUDED = "excluded_categories"
STEP_INDOOR = "indoor"
STEP_FOOD = "food"
STEP_NOISE = "noise"
STEP_DONE = "done"

_STEP_ORDER = [
    STEP_BUDGET,
    STEP_INTERESTS,
    STEP_EXCLUDED,
    STEP_INDOOR,
    STEP_FOOD,
    STEP_NOISE,
]

_STEP_TITLES = {
    STEP_BUDGET: "Бюджет",
    STEP_INTERESTS: "Интересы",
    STEP_EXCLUDED: "Исключить",
    STEP_INDOOR: "Где",
    STEP_FOOD: "Еда",
    STEP_NOISE: "Шум",
}

_STEP_ICONS = {
    STEP_BUDGET: "💰",
    STEP_INTERESTS: "🎯",
    STEP_EXCLUDED: "🚫",
    STEP_INDOOR: "🏠",
    STEP_FOOD: "🍽",
    STEP_NOISE: "🔊",
}

_PROMPTS = {
    STEP_BUDGET: (
        "💰 Максимальный бюджет на человека?\n"
        "Выбери кнопкой или напиши своё число в рублях."
    ),
    STEP_INTERESTS: (
        "🎯 Что вам интересно? Отметь один или несколько вариантов "
        "и нажми «Готово»."
    ),
    STEP_EXCLUDED: (
        "🚫 Какие типы мест точно не подходят? Отметь и нажми «Готово», "
        "или пропусти."
    ),
    STEP_INDOOR: "🏠 Где хотите провести время?",
    STEP_FOOD: "🍽 Еда обязательна?",
    STEP_NOISE: "🔊 Какой уровень шума допустим?",
}

# Общие условия комнаты (остальное каждый участник выбирает сам)
ROOM_LEVEL_STEPS = [STEP_EXCLUDED, STEP_INDOOR, STEP_FOOD, STEP_NOISE]


def default_room_requirements():
    """Общие условия новой комнаты: пока ничего не ограничиваем."""
    return {
        "excluded_categories": [],
        "indoor": None,
        "food_required": False,
        "max_noise_level": None,
    }


UNLIMITED_BUDGET = 1_000_000
BUDGET_OPTIONS = [500, 1000, 1500, 2000, 3000, 5000]

INDOOR_OPTIONS = [
    ("in", "🏠 В помещении", True),
    ("out", "🌤 На улице", False),
    ("any", "🤷 Не важно", None),
]

FOOD_OPTIONS = [
    ("yes", "🍴 Да, нужна", True),
    ("no", "➖ Не обязательно", False),
]

NOISE_OPTIONS = [
    ("quiet", "🤫 Только тихо", "quiet"),
    ("medium", "🙂 Умеренно", "medium"),
    ("any", "🔊 Не важно", None),
]

_OPTIONS = {
    STEP_INDOOR: INDOOR_OPTIONS,
    STEP_FOOD: FOOD_OPTIONS,
    STEP_NOISE: NOISE_OPTIONS,
}

_REQUIREMENT_KEYS = {
    STEP_BUDGET: "budget_max",
    STEP_INTERESTS: "required_interests",
    STEP_EXCLUDED: "excluded_categories",
    STEP_INDOOR: "indoor",
    STEP_FOOD: "food_required",
    STEP_NOISE: "max_noise_level",
}

_MULTI_CATALOGS = {
    STEP_INTERESTS: INTERESTS,
    STEP_EXCLUDED: CATEGORIES,
}

_MULTI_NAME = {
    STEP_INTERESTS: interest_name,
    STEP_EXCLUDED: category_name,
}


# ---------------------------------------------------------------- текст

def describe(step, value):
    """Значение требования словами для сводки."""
    if step == STEP_BUDGET:
        if value is None:
            return "не задан"
        return "без ограничений" if value >= UNLIMITED_BUDGET else f"до {value} ₽"

    if step in _MULTI_NAME:
        names = ", ".join(_MULTI_NAME[step](c) for c in (value or []))
        if names:
            return names
        return "любые" if step == STEP_INTERESTS else "нет ограничений"

    if step == STEP_INDOOR:
        return {True: "в помещении", False: "на улице"}.get(value, "не важно")

    if step == STEP_FOOD:
        return "нужна" if value else "не обязательна"

    if step == STEP_NOISE:
        return {"quiet": "только тихо", "medium": "умеренно"}.get(value, "не важно")

    return str(value)


def requirement_lines(requirements):
    """Строки «Название: значение» для карточки встречи."""
    return [
        f"{_STEP_ICONS[s]} {_STEP_TITLES[s]}: "
        f"{describe(s, requirements.get(_REQUIREMENT_KEYS[s]))}"
        for s in _STEP_ORDER
        if _REQUIREMENT_KEYS[s] in requirements
    ]


def _parse_codes(text, catalog):
    """Принимает коды или русские названия через запятую -> список кодов."""
    by_name = {name.lower(): code for code, (_, name) in catalog.items()}
    result = []

    for item in text.split(","):
        item = item.strip()
        if not item or item == "-":
            continue
        low = item.lower()
        if low in catalog:
            result.append(low)
        elif low in by_name:
            result.append(by_name[low])
        else:
            result.append(item)

    return result


def _parse_indoor(text):
    t = text.strip().lower()
    if t in ("да", "yes", "y", "помещение", "в помещении"):
        return True
    if t in ("нет", "no", "n", "улица", "на улице"):
        return False
    return None


def _parse_noise(text):
    t = text.strip().lower()
    return {"quiet": "quiet", "тихо": "quiet", "medium": "medium",
            "умеренно": "medium"}.get(t)


def _button(text, payload, intent="default"):
    return {"type": "callback", "text": text, "payload": payload, "intent": intent}


def _chunk(buttons, size):
    return [buttons[i:i + size] for i in range(0, len(buttons), size)]


# ---------------------------------------------------------------- сессия

class DialogSession:
    """Состояние диалога требований (создание или редактирование)."""

    def __init__(self, requirements=None, meeting_code=None, steps=None):
        self.order = list(steps or _STEP_ORDER)   # какие вопросы задаём
        self.step_index = 0
        self.requirements = {}
        self.answers = {}
        self.selected = {STEP_INTERESTS: [], STEP_EXCLUDED: []}
        self.meeting_code = meeting_code   # не None — правим готовую встречу
        self.menu = False                  # режим меню редактирования
        self.editing = None                # какой пункт правим сейчас

        if requirements is not None:
            self._load(requirements)

    def _load(self, requirements):
        self.requirements = dict(requirements)

        for step in self.order:
            key = _REQUIREMENT_KEYS[step]
            if key in self.requirements:
                self.answers[step] = describe(step, self.requirements[key])
                if step in self.selected:
                    self.selected[step] = list(self.requirements[key] or [])

        self.step_index = len(self.order)
        self.menu = True

    # ---- состояние

    @property
    def current_step(self):
        if self.editing:
            return self.editing
        if self.step_index >= len(self.order):
            return STEP_DONE
        return self.order[self.step_index]

    def is_done(self):
        """Все вопросы созданной встречи пройдены (меню редактирования — нет)."""
        return (
            not self.menu
            and not self.editing
            and self.step_index >= len(self.order)
        )

    def _advance(self, step, value):
        self.requirements[_REQUIREMENT_KEYS[step]] = value
        self.answers[step] = describe(step, value)

        if self.editing:
            self.editing = None      # после правки пункта — назад в меню
        else:
            self.step_index += 1

    def go_back(self):
        if self.menu or self.step_index == 0:
            return False
        self.step_index -= 1
        step = self.order[self.step_index]
        self.requirements.pop(_REQUIREMENT_KEYS[step], None)
        self.answers.pop(step, None)
        return True

    # ---- вывод

    def summary_lines(self):
        return [
            f"• {_STEP_TITLES[s]}: {self.answers[s]}"
            for s in self.order
            if s in self.answers
        ]

    def summary_text(self):
        return "Твои ответы:\n" + "\n".join(self.summary_lines())

    def render(self):
        """(текст, строки кнопок) для текущего состояния."""
        if self.menu and not self.editing:
            return self._render_menu()

        step = self.current_step
        parts = []

        if self.editing:
            parts.append(f"Изменяем: {_STEP_TITLES[step]}")
            parts.append(_PROMPTS[step])
        else:
            summary = self.summary_lines()
            if summary:
                parts.append("Твои ответы:\n" + "\n".join(summary))
            parts.append(
                f"Шаг {self.step_index + 1} из {len(self.order)}\n{_PROMPTS[step]}"
            )

        return "\n\n".join(parts), self._keyboard(step)

    def _render_menu(self):
        text = (
            "⚙️ Требования встречи\n"
            "Нажми на пункт, чтобы изменить. Когда закончишь — «Сохранить»."
        )
        rows = []

        for step in self.order:
            label = f"{_STEP_ICONS[step]} {_STEP_TITLES[step]}: {self.answers.get(step, '—')}"
            if len(label) > 60:
                label = label[:57] + "…"
            rows.append([_button(label, f"menu:edit:{step}")])

        rows.append([
            _button("✅ Сохранить", "menu:done:", "positive"),
            _button("✖️ Отмена", "menu:cancel:"),
        ])
        return text, rows

    def _keyboard(self, step):
        rows = []

        if step == STEP_BUDGET:
            btns = [_button(f"до {v} ₽", f"{step}:pick:{v}") for v in BUDGET_OPTIONS]
            rows += _chunk(btns, 3)
            rows.append([_button("♾ Без ограничений", f"{step}:pick:{UNLIMITED_BUDGET}")])

        elif step in _MULTI_CATALOGS:
            catalog = _MULTI_CATALOGS[step]
            chosen = self.selected[step]
            btns = []
            for code, (emoji, name) in catalog.items():
                mark = "✅ " if code in chosen else f"{emoji} "
                btns.append(_button(f"{mark}{name}", f"{step}:toggle:{code}"))
            rows += _chunk(btns, 2)

            if chosen:
                rows.append([_button(f"Готово ({len(chosen)})", f"{step}:done:", "positive")])
            else:
                rows.append([_button("Пропустить ➡️", f"{step}:done:")])

        elif step in _OPTIONS:
            rows.append([_button(t, f"{step}:pick:{k}") for k, t, _ in _OPTIONS[step]])

        if self.editing:
            rows.append([_button("⬅️ Отмена", f"back:{step}")])
        elif self.step_index > 0:
            rows.append([_button("⬅️ Назад", f"back:{step}")])

        return rows

    # ---- нажатия кнопок

    def press(self, payload):
        """
        Возвращает: "stale" — кнопка устарела; "redraw" — перерисовать;
        "done" — все вопросы созданной встречи пройдены;
        "menu_done" / "cancel" — выход из меню редактирования.
        """
        parts = (payload or "").split(":", 2)

        if parts[0] == "menu":
            return self._press_menu(parts)

        if parts[0] == "back":
            if len(parts) < 2 or parts[1] != self.current_step:
                return "stale"
            if self.editing:
                self.editing = None
                return "redraw"
            return "redraw" if self.go_back() else "stale"

        if len(parts) < 3 or parts[0] != self.current_step:
            return "stale"

        step, action, value = parts

        if action == "toggle" and step in _MULTI_CATALOGS:
            if value not in _MULTI_CATALOGS[step]:
                return "stale"
            chosen = self.selected[step]
            if value in chosen:
                chosen.remove(value)
            else:
                chosen.append(value)
            return "redraw"

        if action == "done" and step in _MULTI_CATALOGS:
            self._advance(step, list(self.selected[step]))

        elif action == "pick":
            if not self._apply_pick(step, value):
                return "stale"

        else:
            return "stale"

        return "done" if self.is_done() else "redraw"

    def _press_menu(self, parts):
        if not self.menu or self.editing or len(parts) < 2:
            return "stale"

        action = parts[1]

        if action == "edit" and len(parts) == 3 and parts[2] in self.order:
            self.editing = parts[2]
            return "redraw"
        if action == "done":
            return "menu_done"
        if action == "cancel":
            return "cancel"

        return "stale"

    def _apply_pick(self, step, value):
        if step == STEP_BUDGET:
            try:
                amount = int(value)
            except ValueError:
                return False
            self._advance(step, amount)
            return True

        for key, _label, req_value in _OPTIONS.get(step, ()):
            if key == value:
                self._advance(step, req_value)
                return True

        return False

    # ---- ввод текстом (запасной вариант)

    def submit(self, text):
        """Ответ текстом на текущий шаг. Возвращает (ok, error_message)."""
        if self.menu and not self.editing:
            return False, "Выбери пункт кнопкой под сообщением."

        step = self.current_step
        text = text.strip()

        if step == STEP_BUDGET:
            try:
                value = int(text)
                if value < 0:
                    raise ValueError
            except ValueError:
                return False, "Выбери кнопку или напиши бюджет целым числом, например 1500."
            self._advance(step, value)

        elif step in _MULTI_CATALOGS:
            codes = _parse_codes(text, _MULTI_CATALOGS[step])
            self.selected[step] = codes
            self._advance(step, codes)

        elif step == STEP_INDOOR:
            self._advance(step, _parse_indoor(text))

        elif step == STEP_FOOD:
            self._advance(step, text.lower() in ("да", "yes", "y", "нужна"))

        elif step == STEP_NOISE:
            self._advance(step, _parse_noise(text))

        return True, None
