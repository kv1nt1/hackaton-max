CREATE TABLE city_nodes (
    id SERIAL PRIMARY KEY,

    -- Local city coordinates in meters
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,

    -- Synthetic district
    district VARCHAR(50) NOT NULL,

    -- Highest road type connected to this node
    node_type VARCHAR(30) NOT NULL DEFAULT 'local'
        CHECK (
            node_type IN (
                'pedestrian',
                'local',
                'street',
                'avenue'
            )
        ),

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);