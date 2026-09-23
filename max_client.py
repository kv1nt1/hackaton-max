"""
Минималистичный клиент MAX Bot API поверх requests.

Работает напрямую с REST API (https://dev.max.ru/docs-api), без
сторонних SDK — только long polling (GET /updates) и отправка
сообщений (POST /messages). Этого достаточно для диалогового бота
из main.py.

Для продакшена документация MAX рекомендует Webhook вместо
long polling (см. use case "event-notifications"), но для
локальной разработки/хакатона long polling — самый простой вариант
запуска без публичного URL.
"""

import glob
import os
import ssl
import time

import certifi
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter

load_dotenv()

BASE_URL = os.getenv("MAX_BASE_URL", "https://platform-api2.max.ru")
BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")

# Папка с сертификатами Минцифры (russian_trusted_root_ca_pem.crt и
# russian_trusted_sub_ca_pem.crt). Можно переопределить через MAX_CA_DIR.
CA_DIR = os.getenv(
    "MAX_CA_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "certs")
)


def _build_ssl_context():
    """Стандартные корневые сертификаты (certifi) + сертификаты Минцифры."""
    ctx = ssl.create_default_context(cafile=certifi.where())

    files = []
    for pattern in ("*.crt", "*.cer", "*.pem"):
        files += glob.glob(os.path.join(CA_DIR, pattern))

    for path in sorted(files):
        with open(path, "rb") as f:
            data = f.read()
        # PEM — текст, иначе считаем, что это DER (.cer)
        if b"BEGIN CERTIFICATE" in data:
            ctx.load_verify_locations(cadata=data.decode("ascii", "ignore"))
        else:
            ctx.load_verify_locations(cadata=data)

    return ctx


class _CAAdapter(HTTPAdapter):
    def __init__(self, ssl_context, *args, **kwargs):
        self._ssl_context = ssl_context
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        kwargs["ssl_context"] = self._ssl_context
        return super().proxy_manager_for(*args, **kwargs)


# лимит MAX: не больше 2 сообщений в секунду в один чат
_MIN_SEND_INTERVAL = 0.55


class MaxApiError(RuntimeError):
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload
        if status_code == 0:
            super().__init__(f"Сетевая ошибка: {payload}")
        else:
            super().__init__(f"MAX API error {status_code}: {payload}")


class MaxClient:
    def __init__(self, token=None, base_url=None, timeout=35):
        self.token = token or BOT_TOKEN
        if not self.token:
            raise RuntimeError(
                "Не задан MAX_BOT_TOKEN (переменная окружения или .env)"
            )

        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

        # MAX_NO_PROXY=1 в .env — не использовать системный прокси
        # (Windows / HTTP_PROXY / HTTPS_PROXY), ходить в MAX напрямую
        if os.getenv("MAX_NO_PROXY", "").strip().lower() in ("1", "true", "yes"):
            self.session.trust_env = False
        self.session.headers.update({"Authorization": self.token})
        self.session.mount("https://", _CAAdapter(_build_ssl_context()))
        self._last_sent_at = {}

    def _request(self, method, path, params=None, json_body=None, timeout=None):
        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(
                method,
                url,
                params=params,
                json=json_body,
                timeout=timeout or self.timeout,
            )
        except requests.exceptions.ProxyError:
            raise MaxApiError(0, "прокси оборвал соединение") from None
        except requests.exceptions.Timeout:
            raise MaxApiError(0, "таймаут запроса") from None
        except requests.exceptions.SSLError as error:
            raise MaxApiError(0, f"ошибка сертификата: {error}") from None
        except requests.exceptions.RequestException as error:
            raise MaxApiError(0, f"нет соединения: {type(error).__name__}") from None

        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = response.text
            raise MaxApiError(response.status_code, payload)

        if not response.content:
            return {}

        return response.json()

    def get_me(self):
        return self._request("GET", "/me")

    def get_updates(self, marker=None, limit=100, timeout=30, types=None):
        params = {"limit": limit, "timeout": timeout}

        if marker is not None:
            params["marker"] = marker

        if types:
            params["types"] = ",".join(types)

        # добавляем небольшой запас к HTTP-таймауту сверх long-poll таймаута
        return self._request(
            "GET", "/updates", params=params, timeout=timeout + 10
        )

    def send_message(
        self,
        text,
        user_id=None,
        chat_id=None,
        attachments=None,
        notify=True,
        format=None,
        disable_link_preview=None,
    ):
        if not user_id and not chat_id:
            raise ValueError("Нужно указать user_id или chat_id")

        params = {}
        if user_id:
            params["user_id"] = user_id
        if chat_id:
            params["chat_id"] = chat_id
        if disable_link_preview is not None:
            params["disable_link_preview"] = disable_link_preview

        body = {"text": text[:4000], "notify": notify}

        if attachments:
            body["attachments"] = attachments
        if format:
            body["format"] = format

        target = user_id or chat_id
        self._throttle(target)

        return self._request(
            "POST", "/messages", params=params, json_body=body
        )

    @staticmethod
    def inline_keyboard(rows):
        """Вложение с inline-клавиатурой из строк кнопок."""
        return {"type": "inline_keyboard", "payload": {"buttons": rows}}

    def answer_callback(self, callback_id, text=None, attachments=None, notification=None):
        """
        Ответ на нажатие кнопки (POST /answers). Если передан text —
        исходное сообщение с кнопкой заменяется на новое (attachments=[]
        убирает клавиатуру). notification — всплывающее уведомление.
        """
        body = {}

        if text is not None:
            message = {"text": text[:4000]}
            if attachments is not None:
                message["attachments"] = attachments
            body["message"] = message

        if notification:
            body["notification"] = notification

        return self._request(
            "POST", "/answers", params={"callback_id": callback_id}, json_body=body
        )

    def _throttle(self, target_id):
        last = self._last_sent_at.get(target_id, 0)
        wait = _MIN_SEND_INTERVAL - (time.time() - last)

        if wait > 0:
            time.sleep(wait)

        self._last_sent_at[target_id] = time.time()