"""
Бот для мессенджера MAX поверх существующего бэкенда
(database.get_places + filters.filter_places).

Запуск:
    python bot.py

Требует переменные окружения (.env):
    MAX_BOT_TOKEN=...      токен бота из консоли MAX
    DB_HOST=...
    DB_PORT=...
    DB_NAME=...
    DB_USER=...
    DB_PASSWORD=...

Логика: держим в памяти по одному DialogSession на каждого
пользователя (user_id из MAX). На каждое текстовое сообщение
продвигаем диалог на шаг вперёд; когда все ответы собраны —
идём в БД через database.get_places() и фильтруем через
filters.filter_places(), как это делает main.py, и присылаем
результат текстом в чат.
"""

import logging
import time

from database import get_places
from dialog import DialogSession, format_place
from filters import filter_places
from max_client import MaxApiError, MaxClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("max-bot")

RESTART_COMMANDS = {"/start", "начать", "заново", "/restart"}

MAX_RESULTS_IN_MESSAGE = 8


class Bot:
    def __init__(self, client: MaxClient):
        self.client = client
        self.sessions = {}

    def get_or_create_session(self, user_id):
        session = self.sessions.get(user_id)
        if session is None:
            session = DialogSession()
            self.sessions[user_id] = session
        return session

    def reply(self, user_id, text, keyboard=None):
        try:
            attachments = [self.client.inline_keyboard(keyboard)] if keyboard else None
            self.client.send_message(
                text=text, user_id=user_id, attachments=attachments
            )
        except MaxApiError as error:
            log.error("Не удалось отправить сообщение user_id=%s: %s", user_id, error)

    def send_step(self, user_id, session):
        """Отправляет новое сообщение с текущим вопросом и кнопками."""
        text, keyboard = session.render()
        self.reply(user_id, text, keyboard)

    def start_dialog(self, user_id):
        session = DialogSession()
        self.sessions[user_id] = session
        self.reply(
            user_id,
            "=== Поиск места ===\n\n"
            "Отвечай кнопками под сообщением. Чтобы начать заново, "
            "напиши /start.",
        )
        self.send_step(user_id, session)

    # ---------------------------------------------------------- текст

    def handle_text(self, user_id, text):
        text = (text or "").strip()

        if not text:
            return

        if text.lower() in RESTART_COMMANDS:
            self.start_dialog(user_id)
            return

        session = self.sessions.get(user_id)

        if session is None or session.is_done():
            self.start_dialog(user_id)
            return

        ok, error_message = session.submit(text)

        if not ok:
            self.reply(user_id, error_message)
            return

        if session.is_done():
            self.finish_dialog(user_id, session)
            return

        self.send_step(user_id, session)

    # ---------------------------------------------------------- кнопки

    def answer_callback_safe(self, callback_id, **kwargs):
        try:
            self.client.answer_callback(callback_id, **kwargs)
            return True
        except MaxApiError as error:
            log.error("Не удалось ответить на callback: %s", error)
            return False

    def handle_callback(self, user_id, callback_id, payload):
        if payload == "restart":
            self.answer_callback_safe(callback_id, attachments=[], notification=None)
            self.start_dialog(user_id)
            return

        session = self.sessions.get(user_id)

        if session is None:
            # бот перезапускался, состояние диалога потеряно
            self.answer_callback_safe(
                callback_id, notification="Диалог устарел, начинаем заново"
            )
            self.start_dialog(user_id)
            return

        status = session.press(payload)

        if status == "stale":
            self.answer_callback_safe(
                callback_id, notification="Эта кнопка уже неактуальна"
            )
            return

        if status == "redraw":
            text, keyboard = session.render()
            ok = self.answer_callback_safe(
                callback_id, text=text, attachments=[self.client.inline_keyboard(keyboard)]
            )
            if not ok:
                # не удалось отредактировать сообщение — шлём новым
                self.reply(user_id, text, keyboard)
            return

        if status == "done":
            # убираем кнопки и оставляем сводку ответов в сообщении
            self.answer_callback_safe(
                callback_id, text=session.summary_text(), attachments=[]
            )
            self.finish_dialog(user_id, session)

    # ---------------------------------------------------------- результат

    def finish_dialog(self, user_id, session):
        restart_keyboard = [[{
            "type": "callback",
            "text": "🔄 Искать заново",
            "payload": "restart",
            "intent": "positive",
        }]]

        self.reply(user_id, "Ищу подходящие места...")

        try:
            places = get_places()
        except Exception as error:
            log.exception("Ошибка подключения к БД")
            self.reply(
                user_id,
                "Не получилось подключиться к базе данных. "
                f"Ошибка: {error}",
                restart_keyboard,
            )
            return

        result = filter_places(places, session.requirements)

        if not result:
            self.reply(
                user_id,
                "Подходящих мест не найдено 😔\n"
                "Попробуй смягчить требования.",
                restart_keyboard,
            )
            return

        self.reply(user_id, f"Подходит мест: {len(result)}")

        shown = result[:MAX_RESULTS_IN_MESSAGE]
        for place in shown:
            self.reply(user_id, format_place(place))

        if len(result) > len(shown):
            self.reply(
                user_id,
                f"...и ещё {len(result) - len(shown)} вариантов. "
                "Уточни требования, чтобы сузить список.",
                restart_keyboard,
            )
        else:
            self.reply(user_id, "Хочешь искать заново?", restart_keyboard)

    # ---------------------------------------------------------- события

    def handle_update(self, update):
        update_type = update.get("update_type")

        if update_type == "message_created":
            message = update.get("message", {})
            sender = message.get("sender", {})
            user_id = sender.get("user_id")
            body = message.get("body", {}) or {}

            if user_id is not None:
                self.handle_text(user_id, body.get("text"))

        elif update_type == "message_callback":
            callback = update.get("callback", {}) or {}
            user_id = (callback.get("user") or {}).get("user_id")
            callback_id = callback.get("callback_id")

            if user_id is not None and callback_id:
                self.handle_callback(user_id, callback_id, callback.get("payload"))

        elif update_type == "bot_started":
            # пользователь нажал «Начать» при первом открытии бота
            user_id = (update.get("user") or {}).get("user_id")
            if user_id is not None:
                self.start_dialog(user_id)

    def run_polling(self):
        me = self.client.get_me()
        log.info("Бот запущен: %s (id=%s)", me.get("name"), me.get("user_id"))

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


def main():
    client = MaxClient()
    bot = Bot(client)
    bot.run_polling()


if __name__ == "__main__":
    main()