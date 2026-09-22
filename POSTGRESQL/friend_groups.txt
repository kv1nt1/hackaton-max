DROP TABLE IF EXISTS friend_group_members CASCADE;
DROP TABLE IF EXISTS friend_groups CASCADE;

CREATE TABLE friend_groups (
    id SERIAL PRIMARY KEY,

    name VARCHAR(150) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE friend_group_members (
    group_id INTEGER NOT NULL
        REFERENCES friend_groups(id)
        ON DELETE CASCADE,

    user_id INTEGER NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (group_id, user_id)
);


CREATE INDEX idx_friend_group_members_user_id
    ON friend_group_members(user_id);