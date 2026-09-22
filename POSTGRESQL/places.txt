CREATE TABLE places (
    id SERIAL PRIMARY KEY,

    -- Основная информация
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    description TEXT,

    district VARCHAR(50) NOT NULL,

    -- Положение на графе города
    edge_id INTEGER NOT NULL
        REFERENCES city_edges(id)
        ON DELETE CASCADE,

    -- 0 = node_from
    -- 1 = node_to
    edge_position DOUBLE PRECISION NOT NULL
        CHECK (
            edge_position >= 0
            AND edge_position <= 1
        ),

    -- Координаты в метрах
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,

    -- Цены в RUB
    price_min INTEGER NOT NULL
        CHECK (price_min >= 0),

    price_avg INTEGER NOT NULL
        CHECK (price_avg >= 0),

    price_max INTEGER NOT NULL
        CHECK (price_max >= 0),

    currency VARCHAR(3) NOT NULL
        DEFAULT 'RUB',

    -- Интересы и теги
    interests TEXT[] NOT NULL
        DEFAULT '{}',

    tags TEXT[] NOT NULL
        DEFAULT '{}',

    -- Расписание
    opening_hours JSONB NOT NULL,

    -- Размер компании
    min_group_size INTEGER NOT NULL
        DEFAULT 1
        CHECK (min_group_size > 0),

    max_group_size INTEGER NOT NULL
        CHECK (max_group_size > 0),

    -- Средняя продолжительность посещения
    avg_duration_minutes INTEGER NOT NULL
        CHECK (avg_duration_minutes > 0),

    -- Характеристики места
    indoor BOOLEAN NOT NULL,

    food_available BOOLEAN NOT NULL
        DEFAULT FALSE,

    alcohol_available BOOLEAN NOT NULL
        DEFAULT FALSE,

    noise_level VARCHAR(20) NOT NULL
        CHECK (
            noise_level IN (
                'quiet',
                'medium',
                'loud'
            )
        ),

    -- Рейтинг
    rating NUMERIC(2,1)
        CHECK (
            rating >= 0
            AND rating <= 5
        ),

    reviews_count INTEGER NOT NULL
        DEFAULT 0
        CHECK (reviews_count >= 0),

    -- Бронирование
    booking_required BOOLEAN NOT NULL
        DEFAULT FALSE,

    -- Активно ли место
    active BOOLEAN NOT NULL
        DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    -- Логические проверки
    CHECK (
        price_min <= price_avg
    ),

    CHECK (
        price_avg <= price_max
    ),

    CHECK (
        min_group_size <= max_group_size
    )
);
