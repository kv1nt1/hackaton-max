CREATE TABLE city_edges (
    id SERIAL PRIMARY KEY,

    -- Start node
    node_from INTEGER NOT NULL
        REFERENCES city_nodes(id)
        ON DELETE CASCADE,

    -- End node
    node_to INTEGER NOT NULL
        REFERENCES city_nodes(id)
        ON DELETE CASCADE,

    -- Edge length in meters
    length_m DOUBLE PRECISION NOT NULL
        CHECK (
            length_m > 0
        ),

    -- Road hierarchy
    road_type VARCHAR(30) NOT NULL
        CHECK (
            road_type IN (
                'pedestrian',
                'local',
                'street',
                'avenue'
            )
        ),

    -- NULL for pedestrian-only roads
    car_speed_kmh INTEGER
        CHECK (
            car_speed_kmh IS NULL
            OR car_speed_kmh > 0
        ),

    walk_speed_kmh INTEGER NOT NULL
        DEFAULT 5
        CHECK (
            walk_speed_kmh > 0
        ),

    car_allowed BOOLEAN NOT NULL
        DEFAULT TRUE,

    walk_allowed BOOLEAN NOT NULL
        DEFAULT TRUE,

    created_at TIMESTAMP NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    -- Edge cannot connect node to itself
    CHECK (
        node_from <> node_to
    ),

    -- Our graph stores one undirected connection
    -- between a pair of nodes.
    UNIQUE (
        node_from,
        node_to
    )
);
