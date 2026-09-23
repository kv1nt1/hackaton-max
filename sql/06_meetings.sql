DROP TABLE IF EXISTS meeting_participants CASCADE;
DROP TABLE IF EXISTS meetings CASCADE;

CREATE TABLE meetings (
    id SERIAL PRIMARY KEY,

    group_id INTEGER NOT NULL
        REFERENCES friend_groups(id)
        ON DELETE CASCADE,

    meeting_date DATE NOT NULL,

    available_from TIME NOT NULL,
    available_until TIME NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'planning'
        CHECK (
            status IN (
                'planning',
                'completed',
                'cancelled'
            )
        ),

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (available_from < available_until)
);


CREATE TABLE meeting_participants (
    meeting_id INTEGER NOT NULL
        REFERENCES meetings(id)
        ON DELETE CASCADE,

    user_id INTEGER NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    -- Откуда человек начинает путь именно сегодня
    start_edge_id INTEGER NOT NULL
        REFERENCES city_edges(id)
        ON DELETE RESTRICT,

    start_edge_position DOUBLE PRECISION NOT NULL
        CHECK (
            start_edge_position >= 0
            AND start_edge_position <= 1
        ),

    start_x DOUBLE PRECISION NOT NULL,
    start_y DOUBLE PRECISION NOT NULL,

    transport VARCHAR(20) NOT NULL
        CHECK (
            transport IN (
                'walk',
                'car'
            )
        ),

    -- RUB на человека
    budget_max INTEGER NOT NULL
        CHECK (budget_max >= 0),

    max_travel_minutes INTEGER NOT NULL
        CHECK (max_travel_minutes > 0),

    -- Индивидуальное окно может быть уже,
    -- чем общее окно meeting
    available_from TIME NOT NULL,
    available_until TIME NOT NULL,

    required_interests TEXT[] NOT NULL DEFAULT '{}',
    excluded_categories TEXT[] NOT NULL DEFAULT '{}',

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (meeting_id, user_id),

    CHECK (available_from < available_until)
);


CREATE INDEX idx_meetings_group_id
    ON meetings(group_id);

CREATE INDEX idx_meeting_participants_user_id
    ON meeting_participants(user_id);

CREATE INDEX idx_meeting_participants_start_edge
    ON meeting_participants(start_edge_id);