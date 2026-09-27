"""
Анкета участника (participant.py).

Два варианта:
  * ROOM_STEPS — участник комнаты сам выбирает интересы, бюджет, район,
    транспорт и лимит времени в пути;
  * SOLO_STEPS — режим «самостоятельно»: интересы и бюджет общие, для
    каждого человека спрашиваем только район, транспорт и лимит пути.

Формат payload:
    "p:<шаг>:pick:<значение>"     выбор варианта
    "p:interests:toggle:<код>"    отметить/снять интерес
    "p:interests:done:"           интересы выбраны
    "p:back:<шаг>"                назад
"""

from datetime import time as time_cls

from app.bot.dialog import BUDGET_OPTIONS, UNLIMITED_BUDGET
from app.dictionaries import DISTRICTS as _DISTRICTS
from app.dictionaries import INTERESTS
from app.dictionaries import TRANSPORT as _TRANSPORT
from app.dictionaries import interest_names

STEP_INTERESTS = "interests"
STEP_BUDGET = "budget"
STEP_DISTRICT = "district"
STEP_TRANSPORT = "transport"
STEP_MINUTES = "minutes"
STEP_AVAILABLE_FROM = "available_from"
STEP_AVAILABLE_UNTIL = "available_until"

ROOM_STEPS = [
    STEP_INTERESTS, STEP_BUDGET, STEP_DISTRICT, STEP_TRANSPORT, STEP_MINUTES,
    STEP_AVAILABLE_FROM, STEP_AVAILABLE_UNTIL,
]
SOLO_STEPS = [
    STEP_DISTRICT, STEP_TRANSPORT, STEP_MINUTES,
    STEP_AVAILABLE_FROM, STEP_AVAILABLE_UNTIL,
]

# на выбор для «с какого часа свободен»; «до какого» показывает те же
# отметки, но только позже уже выбранного начала
TIME_OPTIONS = [time_cls(h, 0) for h in (9, 11, 13, 15, 17, 19, 21, 23)]

DISTRICTS = [(code, f"{emoji} {name}") for code, (emoji, name) in _DISTRICTS.items()]
TRANSPORT = [(code, f"{emoji} {name}") for code, (emoji, name) in _TRANSPORT.items()]

MINUTES_OPTIONS = [10, 15, 20, 30, 45, 60]

DISTRICT_NAMES = {code: name for code, (_, name) in _DISTRICTS.items()}
TRANSPORT_ICONS = {code: emoji for code, (emoji, _) in _TRANSPORT.items()}

# формулировки: (от первого лица для комнаты, про другого человека для «самостоятельно»)
_PROMPTS = {
    STEP_INTERESTS: (
        "🎯 Что тебе интересно? Отметь один или несколько вариантов и "
        "нажми «Готово» (можно пропустить).",
        None,
    ),
    STEP_BUDGET: (
        "💰 Твой максимальный бюджет на человека?\n"
        "Выбери кнопкой или напиши число в рублях.",
        None,
    ),
    STEP_DISTRICT: (
        "📍 В каком районе ты находишься? Отсюда бот посчитает дорогу до мест.",
        "📍 В каком районе находится этот человек?",
    ),
    STEP_TRANSPORT: (
        "🚦 Как будешь добираться?",
        "🚦 Как он будет добираться?",
    ),
    STEP_MINUTES: (
        "⏱ Сколько минут в пути максимум?\nВыбери кнопкой или напиши число.",
        "⏱ Сколько минут в пути максимум для него?\nВыбери кнопкой или напиши число.",
    ),
    STEP_AVAILABLE_FROM: (
        "🕐 С какого времени ты свободен?",
        "🕐 С какого времени свободен этот человек?",
    ),
    STEP_AVAILABLE_UNTIL: (
        "🕐 До какого времени ты свободен?",
        "🕐 До какого времени свободен этот человек?",
    ),
}


def _button(text, payload, intent="default"):
    return {"type": "callback", "text": text, "payload": payload, "intent": intent}


class ProfileSession:
    """Анкета одного участника."""

    def __init__(self, meeting_code=None, steps=None, solo_index=None, solo_total=None):
        self.meeting_code = meeting_code
        self.order = list(steps or ROOM_STEPS)
        self.solo_index = solo_index      # номер участника в режиме «самостоятельно»
        self.solo_total = solo_total
        self.step_index = 0
        self.values = {}
        self.selected = []                # отмеченные интересы

    @property
    def solo(self):
        return self.solo_index is not None

    @property
    def current_step(self):
        return self.order[self.step_index] if self.step_index < len(self.order) else "done"

    def is_done(self):
        return self.current_step == "done"

    # ---- вывод

    def render(self, title):
        step = self.current_step
        prompt = _PROMPTS[step][1 if self.solo and _PROMPTS[step][1] else 0]
        parts = [title, f"Шаг {self.step_index + 1} из {len(self.order)}\n{prompt}"]
        return "\n\n".join(parts), self._keyboard(step)

    def _keyboard(self, step):
        rows = []

        if step == STEP_INTERESTS:
            btns = []
            for code, (emoji, name) in INTERESTS.items():
                mark = "✅ " if code in self.selected else f"{emoji} "
                btns.append(_button(f"{mark}{name}", f"p:{step}:toggle:{code}"))
            rows += [btns[i:i + 2] for i in range(0, len(btns), 2)]
            if self.selected:
                rows.append([_button(f"Готово ({len(self.selected)})", f"p:{step}:done:", "positive")])
            else:
                rows.append([_button("Пропустить ➡️", f"p:{step}:done:")])

        elif step == STEP_BUDGET:
            btns = [_button(f"до {v} ₽", f"p:{step}:pick:{v}") for v in BUDGET_OPTIONS]
            rows += [btns[i:i + 3] for i in range(0, len(btns), 3)]
            rows.append([_button("♾ Без ограничений", f"p:{step}:pick:{UNLIMITED_BUDGET}")])

        elif step == STEP_DISTRICT:
            btns = [_button(t, f"p:{step}:pick:{c}") for c, t in DISTRICTS]
            rows += [btns[i:i + 2] for i in range(0, len(btns), 2)]

        elif step == STEP_TRANSPORT:
            rows.append([_button(t, f"p:{step}:pick:{c}") for c, t in TRANSPORT])

        elif step == STEP_MINUTES:
            btns = [_button(f"{m} мин", f"p:{step}:pick:{m}") for m in MINUTES_OPTIONS]
            rows += [btns[i:i + 3] for i in range(0, len(btns), 3)]

        elif step == STEP_AVAILABLE_FROM:
            btns = [_button(t.strftime("%H:%M"), f"p:{step}:pick:{t.strftime('%H:%M')}")
                    for t in TIME_OPTIONS]
            rows += [btns[i:i + 4] for i in range(0, len(btns), 4)]

        elif step == STEP_AVAILABLE_UNTIL:
            start = self.values.get(STEP_AVAILABLE_FROM, time_cls(0, 0))
            options = [t for t in TIME_OPTIONS if t > start] or [time_cls(23, 59)]
            btns = [_button(t.strftime("%H:%M"), f"p:{step}:pick:{t.strftime('%H:%M')}")
                    for t in options]
            rows += [btns[i:i + 4] for i in range(0, len(btns), 4)]

        if self.step_index > 0:
            rows.append([_button("⬅️ Назад", f"p:back:{step}")])

        return rows

    def summary(self):
        v = self.values
        parts = []

        if STEP_INTERESTS in v:
            parts.append(interest_names(v[STEP_INTERESTS]) or "интересы не указаны")
        if STEP_BUDGET in v:
            b = v[STEP_BUDGET]
            parts.append("без лимита бюджета" if b >= UNLIMITED_BUDGET else f"до {b} ₽")

        parts.append(DISTRICT_NAMES[v[STEP_DISTRICT]])
        parts.append(TRANSPORT_ICONS[v[STEP_TRANSPORT]])
        parts.append(f"до {v[STEP_MINUTES]} мин")

        if STEP_AVAILABLE_FROM in v and STEP_AVAILABLE_UNTIL in v:
            parts.append(
                f"🕐 {v[STEP_AVAILABLE_FROM].strftime('%H:%M')}–"
                f"{v[STEP_AVAILABLE_UNTIL].strftime('%H:%M')}"
            )

        return " · ".join(parts)

    # ---- нажатия

    def press(self, payload):
        """Возвращает "stale", "redraw" или "done"."""
        parts = (payload or "").split(":")

        if len(parts) < 3 or parts[0] != "p":
            return "stale"

        if parts[1] == "back":
            if parts[2] != self.current_step or self.step_index == 0:
                return "stale"
            self.step_index -= 1
            self.values.pop(self.order[self.step_index], None)
            return "redraw"

        step, action = parts[1], parts[2]
        value = parts[3] if len(parts) > 3 else ""

        if step != self.current_step:
            return "stale"

        if step == STEP_INTERESTS:
            if action == "toggle" and value in INTERESTS:
                if value in self.selected:
                    self.selected.remove(value)
                else:
                    self.selected.append(value)
                return "redraw"
            if action == "done":
                self.values[step] = list(self.selected)
                self.step_index += 1
                return "done" if self.is_done() else "redraw"
            return "stale"

        if action != "pick" or not self._apply(step, value):
            return "stale"

        return "done" if self.is_done() else "redraw"

    def _apply(self, step, value):
        if step == STEP_BUDGET and value.isdigit():
            self.values[step] = int(value)
        elif step == STEP_DISTRICT and value in DISTRICT_NAMES:
            self.values[step] = value
        elif step == STEP_TRANSPORT and value in TRANSPORT_ICONS:
            self.values[step] = value
        elif step == STEP_MINUTES and value.isdigit() and int(value) > 0:
            self.values[step] = int(value)
        elif step in (STEP_AVAILABLE_FROM, STEP_AVAILABLE_UNTIL):
            try:
                parsed = time_cls.fromisoformat(value)
            except ValueError:
                return False
            if step == STEP_AVAILABLE_UNTIL and parsed <= self.values.get(STEP_AVAILABLE_FROM, time_cls(0, 0)):
                return False
            self.values[step] = parsed
        else:
            return False

        self.step_index += 1
        return True

    def submit(self, text):
        """Ответ текстом (бюджет и минуты). Возвращает (ok, error)."""
        step, text = self.current_step, text.strip()

        if step == STEP_BUDGET:
            if text.isdigit() and int(text) > 0:
                self._apply(step, text)
                return True, None
            return False, "Выбери кнопку или напиши бюджет числом, например 1500."

        if step == STEP_MINUTES:
            if text.isdigit() and 0 < int(text) <= 600:
                self._apply(step, text)
                return True, None
            return False, "Выбери кнопку или напиши число минут, например 25."

        if step in (STEP_AVAILABLE_FROM, STEP_AVAILABLE_UNTIL):
            if self._apply(step, text):
                return True, None
            if step == STEP_AVAILABLE_UNTIL:
                return False, "Время должно быть позже начала и в формате ЧЧ:ММ, например 21:00."
            return False, "Напиши время в формате ЧЧ:ММ, например 18:00."

        return False, "Выбери вариант кнопкой под сообщением."
