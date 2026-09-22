DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    -- Домашняя точка пользователя на графе
    home_edge_id INTEGER NOT NULL
        REFERENCES city_edges(id)
        ON DELETE RESTRICT,

    home_edge_position DOUBLE PRECISION NOT NULL
        CHECK (
            home_edge_position >= 0
            AND home_edge_position <= 1
        ),

    home_x DOUBLE PRECISION NOT NULL,
    home_y DOUBLE PRECISION NOT NULL,

    home_district VARCHAR(50) NOT NULL,

    -- Постоянные интересы пользователя
    interests TEXT[] NOT NULL DEFAULT '{}',

    -- Предпочитаемые категории заведений
    preferred_categories TEXT[] NOT NULL DEFAULT '{}',

    -- Что пользователь обычно предпочитает по шуму
    noise_preference VARCHAR(20) NOT NULL
        CHECK (
            noise_preference IN (
                'quiet',
                'medium',
                'loud',
                'any'
            )
        ),

    -- Допустим ли алкоголь в заведении
    alcohol_ok BOOLEAN NOT NULL DEFAULT TRUE,

    -- Предпочитаемый способ передвижения
    default_transport VARCHAR(20) NOT NULL
        CHECK (
            default_transport IN (
                'walk',
                'car'
            )
        ),

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);