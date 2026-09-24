"""
Встречи и участники (хранение в памяти процесса).

ВАЖНО: пока новых таблиц в БД нет, всё лежит в оперативной памяти —
при перезапуске бота встречи пропадут. Когда появится БД, достаточно
заменить реализацию MeetingStore (create / get / add_participant /
cleanup), остальной код бота от хранилища не зависит.
"""

import secrets
import time
from dataclasses import dataclass, field

MAX_PARTICIPANTS = 10
MEETING_TTL_SECONDS = 48 * 3600  # встреча без активности живёт 48 часов

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # без похожих 0/O, 1/I


@dataclass
class Participant:
    user_id: int
    name: str
    district: str
    transport: str        # "walk" | "car"
    max_minutes: int
    interests: list = field(default_factory=list)   # коды интересов (пусто — без предпочтений)
    budget: int = None                              # максимум на человека, ₽


@dataclass
class Meeting:
    code: str
    organizer_id: int
    requirements: dict
    participants: dict = field(default_factory=dict)   # user_id -> Participant
    last_activity: float = field(default_factory=time.time)

    def touch(self):
        self.last_activity = time.time()


class MeetingStore:
    def __init__(self):
        self._meetings = {}

    @staticmethod
    def normalize(code):
        return (code or "").strip().upper()

    def create(self, organizer_id, requirements):
        while True:
            code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
            if code not in self._meetings:
                break

        meeting = Meeting(code=code, organizer_id=organizer_id,
                          requirements=dict(requirements))
        self._meetings[code] = meeting
        return meeting

    def get(self, code):
        return self._meetings.get(self.normalize(code))

    def is_full(self, meeting):
        return len(meeting.participants) >= MAX_PARTICIPANTS

    def upsert_participant(self, meeting, participant):
        """Добавляет или обновляет участника. False — если встреча полна."""
        is_new = participant.user_id not in meeting.participants

        if is_new and self.is_full(meeting):
            return False

        meeting.participants[participant.user_id] = participant
        meeting.touch()
        return True

    def cleanup(self):
        """Удаляет встречи без активности дольше TTL. Возвращает число."""
        now = time.time()
        stale = [c for c, m in self._meetings.items()
                 if now - m.last_activity > MEETING_TTL_SECONDS]

        for code in stale:
            del self._meetings[code]

        return len(stale)
