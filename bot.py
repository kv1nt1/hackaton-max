"""
Бот для мессенджера MAX: подбор места для встречи компании.

Запуск:
    python bot.py

Переменные окружения (.env): MAX_BOT_TOKEN, DB_HOST, DB_PORT, DB_NAME,
DB_USER, DB_PASSWORD.

Сценарий:
  1. Организатор пишет /start, отвечает на вопросы (бюджет, интересы, ...),
     затем указывает свой район, транспорт и лимит времени в пути.
  2. Бот создаёт встречу с кодом и ссылкой-приглашением.
  3. Друзья переходят по ссылке (или пишут боту /join КОД), каждый
     указывает свой район, транспорт и лимит времени в пути.
  4. Организатор нажимает «Найти место»: бот фильтрует места по
     требованиям, считает дорогу для КАЖДОГО участника по графу города и
     присылает всем топ мест (справедливее — там, где максимум дороги
     меньше).

Встречи хранятся в памяти (meetings.py) — при перезапуске бота теряются.
"""

import logging
import re
import time

from database import get_city_graph, get_places
from dialog import DialogSession
from max_client import MaxApiError, MaxClient
from meetings import MAX_PARTICIPANTS, MeetingStore, Participant
from participant import DISTRICT_NAMES, TRANSPORT_ICONS, ProfileSession
from recommend import rank_places

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("max-bot")

RESTART_COMMANDS = {"/start", "начать", "заново", "/restart"}

SESSION_IDLE_SECONDS = 24 * 3600      # диалоги без активности чистим через сутки
CLEANUP_EVERY_SECONDS = 600
TOP_N = 5


def _btn(text, payload, intent="default"):
    return {"type": "callback", "text": text, "payload": payload, "intent": intent}


class Bot:
    def __init__(self, client: MaxClient):
        self.client = client
        self.meetings = MeetingStore()

        self.dialogs = {}        # user_id -> DialogSession (требования встречи)
        self.profiles = {}       # user_id -> ProfileSession (анкета участника)
        self.names = {}          # user_id -> имя
        self.last_seen = {}      # user_id -> время последней активности

        self.bot_username = None
        self._last_cleanup = time.time()

    # ------------------------------------------------------------ отправка

    def reply(self, user_id, text, keyboard=None):
        try:
            attachments = [self.client.inline_keyboard(keyboard)] if keyboard else None
            self.client.send_message(text=text, user_id=user_id, attachments=attachments)
        except MaxApiError as error:
            log.error("Не удалось отправить сообщение user_id=%s: %s", user_id, error)

    def answer_safe(self, callback_id, **kwargs):
        try:
            self.client.answer_callback(callback_id, **kwargs)
            return True
        except MaxApiError as error:
            log.error("Не удалось ответить на callback: %s", error)
            return False

    def edit_or_send(self, callback_id, user_id, text, keyboard):
        """Заменяет сообщение с кнопкой; если не вышло — шлёт новое."""
        ok = self.answer_safe(
            callback_id, text=text,
            attachments=[self.client.inline_keyboard(keyboard)] if keyboard else [],
        )
        if not ok:
            self.reply(user_id, text, keyboard)

    def name_of(self, user_id):
        return self.names.get(user_id) or f"Участник {str(user_id)[-4:]}"

    # ------------------------------------------------------------ старт

    def start_meeting_dialog(self, user_id):
        """Организатор: сначала требования к встрече."""
        self.profiles.pop(user_id, None)
        session = DialogSession()
        self.dialogs[user_id] = session

        self.reply(
            user_id,
            "=== Подбор места для встречи ===\n\n"
            "Сначала общие требования, потом пригласишь друзей — "
            "каждый укажет, откуда поедет. Отвечай кнопками. "
            "/start — начать заново.",
        )
        text, keyboard = session.render()
        self.reply(user_id, text, keyboard)

    def start_join(self, user_id, code):
        meeting = self.meetings.get(code)

        if meeting is None:
            self.reply(
                user_id,
                "Встреча с таким кодом не найдена или уже закрыта 😕\n"
                "Проверь код или попроси организатора прислать новый.",
            )
            return

        if user_id in meeting.participants:
            self.reply(user_id, "Ты уже участвуешь в этой встрече 👍",
                       self.card_keyboard(meeting, user_id))
            return

        if self.meetings.is_full(meeting):
            self.reply(user_id, f"В этой встрече уже максимум участников ({MAX_PARTICIPANTS}).")
            return

        self.dialogs.pop(user_id, None)
        self.begin_profile(user_id, meeting, "Ты приглашён на встречу — осталось указать, откуда ты поедешь.")

    def begin_profile(self, user_id, meeting, title):
        session = ProfileSession(meeting.code)
        self.profiles[user_id] = session
        text, keyboard = session.render(title)
        self.reply(user_id, text, keyboard)

    # ------------------------------------------------------------ текст

    def handle_text(self, user_id, text):
        text = (text or "").strip()

        if not text:
            return

        low = text.lower()

        # /join КОД  или  /start КОД (deep-link)
        m = re.match(r"^/(join|start)\s+([A-Za-z0-9_-]{4,32})$", text)
        if m:
            self.start_join(user_id, m.group(2))
            return

        if low in RESTART_COMMANDS:
            self.start_meeting_dialog(user_id)
            return

        profile = self.profiles.get(user_id)
        if profile is not None and not profile.is_done():
            ok, error = profile.submit(text)
            if not ok:
                self.reply(user_id, error)
            elif profile.is_done():
                self.finish_profile(user_id, profile, callback_id=None)
            else:
                t, kb = profile.render("Анкета участника")
                self.reply(user_id, t, kb)
            return

        dialog = self.dialogs.get(user_id)
        if dialog is None or dialog.is_done():
            self.start_meeting_dialog(user_id)
            return

        ok, error = dialog.submit(text)
        if not ok:
            self.reply(user_id, error)
        elif dialog.is_done():
            self.finish_dialog(user_id, dialog, callback_id=None)
        else:
            t, kb = dialog.render()
            self.reply(user_id, t, kb)

    # ------------------------------------------------------------ кнопки

    def handle_callback(self, user_id, callback_id, payload):
        payload = payload or ""

        if payload == "restart":
            self.answer_safe(callback_id, attachments=[])
            self.start_meeting_dialog(user_id)
        elif payload.startswith("p:"):
            self.handle_profile_callback(user_id, callback_id, payload)
        elif payload.startswith("m:"):
            self.handle_meeting_callback(user_id, callback_id, payload)
        else:
            self.handle_dialog_callback(user_id, callback_id, payload)

    def handle_dialog_callback(self, user_id, callback_id, payload):
        session = self.dialogs.get(user_id)

        if session is None:
            self.answer_safe(callback_id, notification="Диалог устарел, начинаем заново")
            self.start_meeting_dialog(user_id)
            return

        status = session.press(payload)

        if status == "stale":
            self.answer_safe(callback_id, notification="Эта кнопка уже неактуальна")
        elif status == "redraw":
            text, keyboard = session.render()
            self.edit_or_send(callback_id, user_id, text, keyboard)
        elif status == "done":
            self.finish_dialog(user_id, session, callback_id)

    def handle_profile_callback(self, user_id, callback_id, payload):
        session = self.profiles.get(user_id)

        if session is None:
            self.answer_safe(callback_id, notification="Анкета устарела. Открой приглашение заново.")
            return

        status = session.press(payload)

        if status == "stale":
            self.answer_safe(callback_id, notification="Эта кнопка уже неактуальна")
        elif status == "redraw":
            text, keyboard = session.render("Анкета участника")
            self.edit_or_send(callback_id, user_id, text, keyboard)
        elif status == "done":
            self.finish_profile(user_id, session, callback_id)

    def handle_meeting_callback(self, user_id, callback_id, payload):
        parts = payload.split(":")
        if len(parts) != 3:
            self.answer_safe(callback_id, notification="Неизвестное действие")
            return

        _, action, code = parts
        meeting = self.meetings.get(code)

        if meeting is None:
            self.answer_safe(callback_id, notification="Встреча уже закрыта")
            return

        if user_id not in meeting.participants:
            self.answer_safe(callback_id, notification="Ты не участник этой встречи")
            return

        meeting.touch()

        if action == "find":
            if user_id != meeting.organizer_id:
                self.answer_safe(callback_id, notification="Искать может только организатор")
                return
            self.answer_safe(callback_id, notification="Ищу места, считаю дорогу…")
            self.run_search(meeting)

        elif action == "invite":
            self.answer_safe(callback_id)
            self.send_invite(user_id, meeting)

        elif action == "list":
            self.answer_safe(callback_id, text=self.card_text(meeting),
                             attachments=[self.client.inline_keyboard(
                                 self.card_keyboard(meeting, user_id))])

        elif action == "edit":
            self.answer_safe(callback_id)
            self.begin_profile(user_id, meeting, "Обновим твои данные для этой встречи.")

        else:
            self.answer_safe(callback_id, notification="Неизвестное действие")

    # ------------------------------------------------------------ завершение шагов

    def finish_dialog(self, user_id, session, callback_id):
        """Требования собраны -> создаём встречу и просим анкету организатора."""
        if callback_id:
            self.answer_safe(callback_id, text=session.summary_text(), attachments=[])

        meeting = self.meetings.create(user_id, session.requirements)
        self.dialogs.pop(user_id, None)

        self.begin_profile(
            user_id, meeting,
            "Требования сохранены ✅ Теперь укажи, откуда поедешь ты.",
        )

    def finish_profile(self, user_id, session, callback_id):
        meeting = self.meetings.get(session.meeting_code)
        self.profiles.pop(user_id, None)

        if callback_id:
            self.answer_safe(callback_id, text=f"Твои данные: {session.summary()}", attachments=[])
        else:
            self.reply(user_id, f"Твои данные: {session.summary()}")

        if meeting is None:
            self.reply(user_id, "Встреча уже закрыта, начни новую: /start")
            return

        v = session.values
        was_member = user_id in meeting.participants
        participant = Participant(
            user_id=user_id, name=self.name_of(user_id),
            district=v["district"], transport=v["transport"], max_minutes=v["minutes"],
        )

        if not self.meetings.upsert_participant(meeting, participant):
            self.reply(user_id, f"Встреча уже заполнена (максимум {MAX_PARTICIPANTS}).")
            return

        if user_id == meeting.organizer_id:
            if not was_member:
                self.reply(user_id, "Встреча создана 🎉")
                self.send_invite(user_id, meeting)
            self.reply(user_id, self.card_text(meeting), self.card_keyboard(meeting, user_id))
            return

        # приглашённый участник
        self.reply(
            user_id,
            "Ты в встрече ✅ Организатор запустит поиск, и я пришлю результат сюда.",
            self.card_keyboard(meeting, user_id),
        )

        if not was_member:
            self.reply(
                meeting.organizer_id,
                f"🔔 {participant.name} присоединился(ась). "
                f"Участников: {len(meeting.participants)}",
                self.card_keyboard(meeting, meeting.organizer_id),
            )

    # ------------------------------------------------------------ карточка встречи

    def card_text(self, meeting):
        req = meeting.requirements
        lines = [f"👥 Встреча {meeting.code}", ""]

        budget = req.get("budget_max")
        if budget is not None:
            lines.append("💰 Бюджет: " + ("без ограничений" if budget >= 1_000_000 else f"до {budget} ₽"))

        lines.append(f"Участники ({len(meeting.participants)}/{MAX_PARTICIPANTS}):")

        for p in meeting.participants.values():
            role = " (организатор)" if p.user_id == meeting.organizer_id else ""
            lines.append(
                f"• {p.name}{role} — {DISTRICT_NAMES.get(p.district, p.district)} · "
                f"{TRANSPORT_ICONS.get(p.transport, '')} · до {p.max_minutes} мин"
            )

        return "\n".join(lines)

    def card_keyboard(self, meeting, viewer_id):
        rows = []

        if viewer_id == meeting.organizer_id:
            rows.append([_btn("🔍 Найти место", f"m:find:{meeting.code}", "positive")])

        rows.append([
            _btn("🔗 Пригласить", f"m:invite:{meeting.code}"),
            _btn("👥 Участники", f"m:list:{meeting.code}"),
        ])
        rows.append([_btn("✏️ Мои данные", f"m:edit:{meeting.code}")])
        return rows

    def send_invite(self, user_id, meeting):
        lines = ["🔗 Пригласи друзей — перешли им это сообщение:", ""]

        if self.bot_username:
            lines.append(f"https://max.ru/{self.bot_username}?start={meeting.code}")
            lines.append("")

        lines.append(f"Если ссылка не сработала, пусть напишут боту: /join {meeting.code}")
        self.reply(user_id, "\n".join(lines))

    # ------------------------------------------------------------ поиск

    def run_search(self, meeting):
        organizer = meeting.organizer_id
        recipients = list(meeting.participants)

        try:
            places = get_places()
            graph = get_city_graph()
        except Exception as error:
            log.exception("Ошибка загрузки данных из БД")
            self.reply(organizer, f"Не получилось получить данные из базы: {error}")
            return

        results, stats = rank_places(graph, places, meeting, top_n=TOP_N)

        if not results:
            message = self.no_results_text(stats)
        else:
            message = self.results_text(meeting, results, stats)

        for uid in recipients:
            self.reply(uid, message, self.card_keyboard(meeting, uid))

    def results_text(self, meeting, results, stats):
        lines = [f"🎯 Лучшие места для встречи {meeting.code}",
                 f"Подходит: {stats['found']} из {stats['total']}", ""]

        for i, r in enumerate(results, start=1):
            pl = r["place"]
            lines.append(f"{i}. {pl['name']} — {pl['category']}, {pl['district']}")
            lines.append(f"   💰 {pl['price_min']}–{pl['price_max']} ₽ · ⭐ {pl['rating']}")

            way = []
            for uid, minutes in r["times"].items():
                p = meeting.participants[uid]
                way.append(f"{p.name} {TRANSPORT_ICONS[p.transport]} {round(minutes)} мин")
            lines.append("   🚦 " + "; ".join(way))
            lines.append("")

        lines.append("Порядок: сначала те, где самая долгая дорога короче всего.")
        return "\n".join(lines)

    def no_results_text(self, stats):
        if stats["after_filters"] == 0:
            reason = ("Ни одно место не подошло по требованиям "
                      "(бюджет, интересы, размер компании и т. д.).")
        elif stats["too_far"] >= stats["unreachable"]:
            reason = (f"По требованиям подошло {stats['after_filters']} мест, "
                      "но всем они слишком далеко для чьего-то лимита времени в пути.")
        else:
            reason = (f"По требованиям подошло {stats['after_filters']} мест, "
                      "но до них нельзя добраться выбранным транспортом "
                      "(например, пешеходная зона для машины).")

        return (f"Подходящих мест не нашлось 😔\n{reason}\n\n"
                "Что можно ослабить: увеличить лимит времени в пути "
                "(«✏️ Мои данные») или начать заново с другими требованиями (/start).")

    # ------------------------------------------------------------ события

    def remember_user(self, user):
        if not user:
            return
        uid = user.get("user_id")
        name = user.get("first_name") or user.get("name")
        if uid is not None:
            self.last_seen[uid] = time.time()
            if name:
                self.names[uid] = name

    def handle_update(self, update):
        update_type = update.get("update_type")

        if update_type == "message_created":
            message = update.get("message", {})
            sender = message.get("sender", {})
            self.remember_user(sender)
            user_id = sender.get("user_id")
            body = message.get("body", {}) or {}

            if user_id is not None:
                self.handle_text(user_id, body.get("text"))

        elif update_type == "message_callback":
            callback = update.get("callback", {}) or {}
            user = callback.get("user") or {}
            self.remember_user(user)
            user_id = user.get("user_id")
            callback_id = callback.get("callback_id")

            if user_id is not None and callback_id:
                self.handle_callback(user_id, callback_id, callback.get("payload"))

        elif update_type == "bot_started":
            user = update.get("user") or {}
            self.remember_user(user)
            user_id = user.get("user_id")
            payload = update.get("payload")

            if user_id is None:
                return
            if payload:
                self.start_join(user_id, payload)   # пришёл по ссылке-приглашению
            else:
                self.start_meeting_dialog(user_id)

    # ------------------------------------------------------------ уборка

    def cleanup(self):
        now = time.time()
        if now - self._last_cleanup < CLEANUP_EVERY_SECONDS:
            return
        self._last_cleanup = now

        removed = self.meetings.cleanup()

        idle = [u for u, t in self.last_seen.items() if now - t > SESSION_IDLE_SECONDS]
        for uid in idle:
            self.dialogs.pop(uid, None)
            self.profiles.pop(uid, None)
            self.last_seen.pop(uid, None)
            self.names.pop(uid, None)

        if removed or idle:
            log.info("Очистка: встреч %s, неактивных пользователей %s", removed, len(idle))

    # ------------------------------------------------------------ polling

    def run_polling(self):
        me = self.client.get_me()
        self.bot_username = me.get("username")
        log.info("Бот запущен: %s (id=%s, username=%s)",
                 me.get("name"), me.get("user_id"), self.bot_username)

        marker = None

        while True:
            try:
                response = self.client.get_updates(
                    marker=marker,
                    timeout=30,
                    types=["message_created", "message_callback", "bot_started"],
                )
            except MaxApiError as error:
                log.error("Ошибка long polling: %s", error)
                time.sleep(3)
                continue
            except Exception as error:
                log.exception("Неожиданная ошибка long polling: %s", error)
                time.sleep(3)
                continue

            for update in response.get("updates", []):
                try:
                    self.handle_update(update)
                except Exception:
                    log.exception("Ошибка обработки апдейта: %s", update)

            new_marker = response.get("marker")
            if new_marker is not None:
                marker = new_marker

            self.cleanup()


def main():
    client = MaxClient()
    bot = Bot(client)
    bot.run_polling()


if __name__ == "__main__":
    main()
