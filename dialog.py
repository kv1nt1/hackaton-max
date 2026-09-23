"""
Диалог сбора требований встречи (с кнопками).

Вопросы: budget -> interests -> excluded_categories -> indoor ->
food -> noise. Каждый шаг показывается с inline-кнопками; ввод текстом
тоже работает (для бюджета можно написать своё число).

Состояние хранится в памяти процесса по user_id.

Формат payload кнопок:
    "<шаг>:<действие>:<значение>"   pick / toggle / done
    "back:<шаг>"                    вернуться на шаг назад
    "restart"                       начать заново
Шаг внутри payload нужен, чтобы игнорировать нажатия на устаревшие
кнопки из старых сообщений.
"""

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

UNLIMITED_BUDGET = 1_000_000

BUDGET_OPTIONS = [500, 1000, 1500, 2000, 3000, 5000]

# код интереса в БД -> (эмодзи, название)
INTERESTS = {
    "food": ("🍽", "Еда"),
    "coffee": ("☕", "Кофе"),
    "desserts": ("🍰", "Десерты"),
    "drinks": ("🍹", "Напитки"),
    "conversation": ("💬", "Поговорить"),
    "social": ("👥", "Большой компанией"),
    "relax": ("😌", "Расслабиться"),
    "movies": ("🎬", "Кино"),
    "culture": ("🎭", "Культура"),
    "art": ("🎨", "Искусство"),
    "learning": ("📚", "Узнать новое"),
    "creative": ("✨", "Творчество"),
    "games": ("🎲", "Игры"),
    "gaming": ("🕹", "Аркады"),
    "board_games": ("♟", "Настолки"),
    "competitive": ("🏆", "Соревнования"),
    "active": ("🏃", "Активный отдых"),
    "adrenaline": ("⚡", "Адреналин"),
    "music": ("🎤", "Музыка"),
    "nightlife": ("🌙", "Ночная жизнь"),
    "outdoor": ("🌳", "На улице"),
    "nature": ("🌿", "Природа"),
    "walking": ("🚶", "Прогулка"),
}

# код категории в БД -> (эмодзи, название)
CATEGORIES = {
    "restaurant": ("🍽", "Ресторан"),
    "cafe": ("☕", "Кафе"),
    "bar": ("🍸", "Бар"),
    "cinema": ("🎬", "Кино"),
    "bowling": ("🎳", "Боулинг"),
    "karaoke": ("🎤", "Караоке"),
    "board_game_club": ("♟", "Настолки"),
    "escape_room": ("🔐", "Квест"),
    "museum": ("🏛", "Музей"),
    "gallery": ("🖼", "Галерея"),
    "karting": ("🏎", "Картинг"),
    "billiards": ("🎱", "Бильярд"),
    "arcade": ("🕹", "Аркады"),
    "park_activity": ("🌳", "Парк"),
}

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


# ---------------------------------------------------------------- парсинг текста

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


def _parse_yes_no(text):
    return text.strip().lower() in ("да", "yes", "y", "нужна")


def _parse_noise(text):
    t = text.strip().lower()
    return {"quiet": "quiet", "тихо": "quiet", "medium": "medium",
            "умеренно": "medium", "loud": None}.get(t)


def _button(text, payload, intent="default"):
    return {"type": "callback", "text": text, "payload": payload, "intent": intent}


def _chunk(buttons, size):
    return [buttons[i:i + size] for i in range(0, len(buttons), size)]


# ---------------------------------------------------------------- сессия

class DialogSession:
    """Состояние одного диалога сбора требований."""

    def __init__(self):
        self.step_index = 0
        self.requirements = {}
        self.answers = {}  # шаг -> текст ответа для «Твои ответы»
        self.selected = {STEP_INTERESTS: [], STEP_EXCLUDED: []}

    # ---- состояние

    @property
    def current_step(self):
        if self.step_index >= len(_STEP_ORDER):
            return STEP_DONE
        return _STEP_ORDER[self.step_index]

    def is_done(self):
        return self.current_step == STEP_DONE

    def _advance(self, step, requirement_value, answer_text):
        self.requirements[_REQUIREMENT_KEYS[step]] = requirement_value
        self.answers[step] = answer_text
        self.step_index += 1

    def go_back(self):
        if self.step_index == 0:
            return False
        self.step_index -= 1
        step = _STEP_ORDER[self.step_index]
        self.requirements.pop(_REQUIREMENT_KEYS[step], None)
        self.answers.pop(step, None)
        return True

    # ---- вывод шага

    def summary_lines(self):
        lines = []
        for step in _STEP_ORDER:
            if step in self.answers:
                lines.append(f"• {_STEP_TITLES[step]}: {self.answers[step]}")
        return lines

    def render(self):
        """(текст, строки кнопок) для текущего шага."""
        step = self.current_step
        parts = []

        summary = self.summary_lines()
        if summary:
            parts.append("Твои ответы:\n" + "\n".join(summary))

        parts.append(
            f"Шаг {self.step_index + 1} из {len(_STEP_ORDER)}\n{_PROMPTS[step]}"
        )
        return "\n\n".join(parts), self._keyboard(step)

    def summary_text(self):
        return "Твои ответы:\n" + "\n".join(self.summary_lines())

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

        elif step == STEP_INDOOR:
            rows.append([_button(t, f"{step}:pick:{k}") for k, t, _ in INDOOR_OPTIONS])

        elif step == STEP_FOOD:
            rows.append([_button(t, f"{step}:pick:{k}") for k, t, _ in FOOD_OPTIONS])

        elif step == STEP_NOISE:
            rows.append([_button(t, f"{step}:pick:{k}") for k, t, _ in NOISE_OPTIONS])

        if self.step_index > 0:
            rows.append([_button("⬅️ Назад", f"back:{step}")])

        return rows

    # ---- нажатия кнопок

    def press(self, payload):
        """
        Обрабатывает нажатие кнопки.
        Возвращает: "stale" (кнопка устарела), "redraw" (перерисовать
        текущий шаг) или "done" (все ответы собраны).
        """
        parts = (payload or "").split(":", 2)

        if parts[0] == "back":
            if len(parts) < 2 or parts[1] != self.current_step:
                return "stale"
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
            catalog = _MULTI_CATALOGS[step]
            chosen = list(self.selected[step])
            names = ", ".join(catalog[c][1] for c in chosen) or "неважно"
            self._advance(step, chosen, names)

        elif action == "pick":
            if not self._apply_pick(step, value):
                return "stale"

        else:
            return "stale"

        return "done" if self.is_done() else "redraw"

    def _apply_pick(self, step, value):
        if step == STEP_BUDGET:
            try:
                amount = int(value)
            except ValueError:
                return False
            label = "без ограничений" if amount >= UNLIMITED_BUDGET else f"до {amount} ₽"
            self._advance(step, amount, label)
            return True

        options = {
            STEP_INDOOR: INDOOR_OPTIONS,
            STEP_FOOD: FOOD_OPTIONS,
            STEP_NOISE: NOISE_OPTIONS,
        }.get(step)

        if options is None:
            return False

        for key, label, req_value in options:
            if key == value:
                # у label убираем эмодзи в начале для сводки
                self._advance(step, req_value, label.split(" ", 1)[1])
                return True

        return False

    # ---- ввод текстом (запасной вариант)

    def submit(self, text):
        """
        Ответ текстом на текущий шаг. Возвращает (ok, error_message).
        """
        step = self.current_step
        text = text.strip()

        if step == STEP_BUDGET:
            try:
                value = int(text)
                if value < 0:
                    raise ValueError
            except ValueError:
                return False, "Выбери кнопку или напиши бюджет целым числом, например 1500."
            self._advance(step, value, f"до {value} ₽")

        elif step in _MULTI_CATALOGS:
            codes = _parse_codes(text, _MULTI_CATALOGS[step])
            catalog = _MULTI_CATALOGS[step]
            self.selected[step] = codes
            names = ", ".join(catalog[c][1] if c in catalog else c for c in codes)
            self._advance(step, codes, names or "неважно")

        elif step == STEP_INDOOR:
            value = _parse_indoor(text)
            names = {True: "в помещении", False: "на улице", None: "не важно"}
            self._advance(step, value, names[value])

        elif step == STEP_FOOD:
            value = _parse_yes_no(text)
            self._advance(step, value, "нужна" if value else "не обязательна")

        elif step == STEP_NOISE:
            value = _parse_noise(text)
            names = {"quiet": "только тихо", "medium": "умеренно", None: "не важно"}
            self._advance(step, value, names[value])

        else:
            return True, None

        return True, None


def format_place(place):
    return (
        f"[{place['id']}] {place['name']}\n"
        f"  Категория: {place['category']}\n"
        f"  Район: {place['district']}\n"
        f"  Цена: {place['price_min']}–{place['price_max']}\n"
        f"  Рейтинг: {place['rating']}\n"
        f"  Интересы: {', '.join(place['interests'] or [])}"
    )
