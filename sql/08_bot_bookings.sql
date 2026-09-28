-- Бронирования, которые создаёт бот.
--
-- Существующая таблица `bookings` (07_bookings.sql) ссылается на
-- `meetings`, а те — на `friend_groups`: это модель для другого сценария
-- (заранее известная компания друзей). У бота своя, более лёгкая модель
-- встречи (комната по коду или разовый подбор без комнаты), которая в
-- основные таблицы не пишется. Поэтому бронирования бота хранятся в
-- отдельной таблице и соединяются с общими данными только через
-- place_id -> places(id). Это отдельная сущность, а не дубликат
-- `bookings`: при необходимости строки отсюда можно перенести в
-- `bookings`, создав перед этим настоящую запись в `meetings`.

BEGIN;

CREATE TABLE bot_bookings (
    id SERIAL PRIMARY KEY,

    place_id INTEGER NOT NULL
        REFERENCES places(id)
        ON DELETE RESTRICT,

    -- Комната бота ("SOLO", если бронь сделана в режиме «самостоятельно»)
    -- и MAX-id организатора, который подтвердил бронь.
    room_code VARCHAR(20) NOT NULL,
    organizer_max_id BIGINT NOT NULL,

    starts_at TIMESTAMP NOT NULL,
    ends_at TIMESTAMP NOT NULL,

    group_size INTEGER NOT NULL
        CHECK (group_size > 0),

    status VARCHAR(20) NOT NULL DEFAULT 'confirmed'
        CHECK (status IN ('confirmed', 'cancelled')),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (starts_at < ends_at)
);

CREATE INDEX idx_bot_bookings_place_time
    ON bot_bookings(place_id, starts_at, ends_at)
    WHERE status = 'confirmed';

COMMIT;
