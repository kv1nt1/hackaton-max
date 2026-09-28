BEGIN;

CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,

    meeting_id INTEGER NOT NULL
        REFERENCES meetings(id)
        ON DELETE RESTRICT,

    place_id INTEGER NOT NULL
        REFERENCES places(id)
        ON DELETE RESTRICT,

    -- Полные дата и время позволяют посещению закончиться на следующие сутки.
    starts_at TIMESTAMP NOT NULL,
    ends_at TIMESTAMP NOT NULL,

    -- Снимок размера компании на момент бронирования.
    group_size INTEGER NOT NULL
        CHECK (group_size > 0),

    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (
            status IN (
                'pending',
                'confirmed',
                'completed',
                'cancelled'
            )
        ),

    notes TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (starts_at < ends_at)
);

CREATE INDEX idx_bookings_meeting_id
    ON bookings(meeting_id);

CREATE INDEX idx_bookings_place_starts_at
    ON bookings(place_id, starts_at);

COMMIT;
