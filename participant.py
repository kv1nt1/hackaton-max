"""
Анкета участника встречи (participant.py): район -> транспорт -> сколько готов ехать.

Формат payload: "p:<шаг>:pick:<значение>" и "p:back:<шаг>".
"""

STEP_DISTRICT = "district"
STEP_TRANSPORT = "transport"
STEP_MINUTES = "minutes"

_ORDER = [STEP_DISTRICT, STEP_TRANSPORT, STEP_MINUTES]

from dictionaries import DISTRICTS as _DISTRICTS
from dictionaries import TRANSPORT as _TRANSPORT

DISTRICTS = [(code, f"{emoji} {name}") for code, (emoji, name) in _DISTRICTS.items()]
TRANSPORT = [(code, f"{emoji} {name}") for code, (emoji, name) in _TRANSPORT.items()]

MINUTES_OPTIONS = [10, 15, 20, 30, 45, 60]

DISTRICT_NAMES = {code: name for code, (_, name) in _DISTRICTS.items()}
TRANSPORT_ICONS = {code: emoji for code, (emoji, _) in _TRANSPORT.items()}

_PROMPTS = {
    STEP_DISTRICT: "📍 В каком районе ты находишься? Отсюда бот посчитает дорогу до мест.",
    STEP_TRANSPORT: "🚦 Как будешь добираться?",
    STEP_MINUTES: (
        "⏱ Сколько минут в пути максимум?\n"
        "Выбери кнопкой или напиши число."
    ),
}


def _button(text, payload):
    return {"type": "callback", "text": text, "payload": payload, "intent": "default"}


class ProfileSession:
    """Анкета одного участника для конкретной встречи."""

    def __init__(self, meeting_code):
        self.meeting_code = meeting_code
        self.step_index = 0
        self.values = {}

    @property
    def current_step(self):
        return _ORDER[self.step_index] if self.step_index < len(_ORDER) else "done"

    def is_done(self):
        return self.current_step == "done"

    # ---- вывод

    def render(self, title):
        step = self.current_step
        parts = [title, f"Шаг {self.step_index + 1} из {len(_ORDER)}\n{_PROMPTS[step]}"]
        return "\n\n".join(parts), self._keyboard(step)

    def _keyboard(self, step):
        rows = []

        if step == STEP_DISTRICT:
            btns = [_button(t, f"p:{step}:pick:{c}") for c, t in DISTRICTS]
            rows += [btns[i:i + 2] for i in range(0, len(btns), 2)]
        elif step == STEP_TRANSPORT:
            rows.append([_button(t, f"p:{step}:pick:{c}") for c, t in TRANSPORT])
        elif step == STEP_MINUTES:
            btns = [_button(f"{m} мин", f"p:{step}:pick:{m}") for m in MINUTES_OPTIONS]
            rows += [btns[i:i + 3] for i in range(0, len(btns), 3)]

        if self.step_index > 0:
            rows.append([_button("⬅️ Назад", f"p:back:{step}")])

        return rows

    def summary(self):
        v = self.values
        return (
            f"{DISTRICT_NAMES[v['district']]} · "
            f"{TRANSPORT_ICONS[v['transport']]} · до {v['minutes']} мин"
        )

    # ---- ввод

    def press(self, payload):
        """Возвращает "stale", "redraw" или "done"."""
        parts = (payload or "").split(":")

        if len(parts) < 2 or parts[0] != "p":
            return "stale"

        if parts[1] == "back":
            if len(parts) < 3 or parts[2] != self.current_step or self.step_index == 0:
                return "stale"
            self.step_index -= 1
            self.values.pop(_ORDER[self.step_index], None)
            return "redraw"

        if len(parts) != 4 or parts[1] != self.current_step or parts[2] != "pick":
            return "stale"

        if not self._apply(parts[1], parts[3]):
            return "stale"

        return "done" if self.is_done() else "redraw"

    def _apply(self, step, value):
        if step == STEP_DISTRICT and value in DISTRICT_NAMES:
            self.values[step] = value
        elif step == STEP_TRANSPORT and value in TRANSPORT_ICONS:
            self.values[step] = value
        elif step == STEP_MINUTES and value.isdigit() and int(value) > 0:
            self.values[step] = int(value)
        else:
            return False

        self.step_index += 1
        return True

    def submit(self, text):
        """Ответ текстом (только для минут). Возвращает (ok, error)."""
        if self.current_step == STEP_MINUTES:
            text = text.strip()
            if text.isdigit() and 0 < int(text) <= 600:
                self._apply(STEP_MINUTES, text)
                return True, None
            return False, "Выбери кнопку или напиши число минут, например 25."

        return False, "Выбери вариант кнопкой под сообщением."
