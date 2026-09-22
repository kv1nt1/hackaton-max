import random
from datetime import date, timedelta, time

import psycopg2


# ============================================================
# CONFIG
# ============================================================

SEED = 42

MEETINGS_COUNT = 120

random.seed(SEED)


DB_CONFIG = {
    "dbname": "DataBase",
    "user": "postgres",
    "password": "12345",
    "host": "localhost",
    "port": 12345,
}


# ============================================================
# CATEGORY LIST
# ============================================================

ALL_CATEGORIES = [
    "restaurant",
    "cafe",
    "bar",
    "cinema",
    "bowling",
    "karaoke",
    "board_game_club",
    "escape_room",
    "museum",
    "gallery",
    "karting",
    "billiards",
    "arcade",
    "park_activity",
]


# ============================================================
# LOAD GROUPS
# ============================================================

def load_groups(cursor):

    cursor.execute("""
        SELECT
            g.id,
            g.name,
            gm.user_id,

            u.home_edge_id,
            u.home_edge_position,
            u.home_x,
            u.home_y,

            u.home_district,

            u.interests,
            u.preferred_categories,

            u.noise_preference,
            u.alcohol_ok,
            u.default_transport

        FROM friend_groups g

        JOIN friend_group_members gm
            ON gm.group_id = g.id

        JOIN users u
            ON u.id = gm.user_id

        WHERE u.active = TRUE

        ORDER BY
            g.id,
            gm.user_id;
    """)

    rows = cursor.fetchall()

    groups = {}

    for row in rows:

        group_id = row[0]

        if group_id not in groups:

            groups[group_id] = {
                "id": group_id,
                "name": row[1],
                "members": [],
            }

        groups[group_id][
            "members"
        ].append({
            "id": row[2],

            "home_edge_id":
                row[3],

            "home_edge_position":
                row[4],

            "home_x":
                row[5],

            "home_y":
                row[6],

            "home_district":
                row[7],

            "interests":
                list(
                    row[8] or []
                ),

            "preferred_categories":
                list(
                    row[9] or []
                ),

            "noise_preference":
                row[10],

            "alcohol_ok":
                row[11],

            "default_transport":
                row[12],
        })

    return list(
        groups.values()
    )


# ============================================================
# LOAD EDGES
# ============================================================

def load_edges(cursor):

    cursor.execute("""
        SELECT
            e.id,
            e.road_type,
            e.car_allowed,
            e.walk_allowed,

            n1.x,
            n1.y,
            n1.district,

            n2.x,
            n2.y,
            n2.district

        FROM city_edges e

        JOIN city_nodes n1
            ON n1.id = e.node_from

        JOIN city_nodes n2
            ON n2.id = e.node_to

        ORDER BY e.id;
    """)

    rows = cursor.fetchall()

    edges = []

    for row in rows:

        edges.append({
            "id": row[0],

            "road_type":
                row[1],

            "car_allowed":
                row[2],

            "walk_allowed":
                row[3],

            "x1":
                row[4],

            "y1":
                row[5],

            "district1":
                row[6],

            "x2":
                row[7],

            "y2":
                row[8],

            "district2":
                row[9],
        })

    return edges


# ============================================================
# MEETING DATE
# ============================================================

def generate_meeting_date():

    # Не привязываемся к текущей реальной дате.
    # Это synthetic dataset.

    base_date = date(
        2026,
        10,
        1
    )

    offset = random.randint(
        0,
        89
    )

    return (
        base_date
        +
        timedelta(
            days=offset
        )
    )


# ============================================================
# MEETING TIME
# ============================================================

TIME_WINDOWS = [
    # from, until, weight

    (
        time(10, 0),
        time(13, 0),
        5
    ),

    (
        time(12, 0),
        time(15, 0),
        10
    ),

    (
        time(14, 0),
        time(18, 0),
        12
    ),

    (
        time(17, 0),
        time(20, 0),
        18
    ),

    (
        time(18, 0),
        time(21, 0),
        25
    ),

    (
        time(19, 0),
        time(22, 0),
        25
    ),

    (
        time(20, 0),
        time(23, 0),
        15
    ),
]


def generate_time_window():

    selected = random.choices(
        TIME_WINDOWS,
        weights=[
            item[2]
            for item
            in TIME_WINDOWS
        ],
        k=1
    )[0]

    return (
        selected[0],
        selected[1],
    )


# ============================================================
# TRANSPORT
# ============================================================

def generate_transport(user):

    default_transport = (
        user[
            "default_transport"
        ]
    )

    # 80% случаев человек использует
    # обычный транспорт.

    if random.random() < 0.80:

        return default_transport

    # Иногда поведение меняется.

    if default_transport == "walk":
        return "car"

    return "walk"


# ============================================================
# START LOCATION
# ============================================================

def choose_start_location(
    user,
    transport,
    edges
):

    # ------------------------------------------
    # 65% — человек начинает из дома.
    # ------------------------------------------

    if random.random() < 0.65:

        return {
            "edge_id":
                user[
                    "home_edge_id"
                ],

            "edge_position":
                user[
                    "home_edge_position"
                ],

            "x":
                user[
                    "home_x"
                ],

            "y":
                user[
                    "home_y"
                ],
        }

    # ------------------------------------------
    # В остальных случаях человек может быть
    # в другом месте города.
    # ------------------------------------------

    candidates = []

    for edge in edges:

        if (
            transport == "car"
            and
            not edge["car_allowed"]
        ):
            continue

        if (
            transport == "walk"
            and
            not edge["walk_allowed"]
        ):
            continue

        candidates.append(
            edge
        )

    if not candidates:

        raise RuntimeError(
            "Нет подходящих edges "
            f"для transport={transport}"
        )

    edge = random.choice(
        candidates
    )

    position = random.uniform(
        0.10,
        0.90
    )

    x = (
        edge["x1"]
        +
        (
            edge["x2"]
            -
            edge["x1"]
        )
        * position
    )

    y = (
        edge["y1"]
        +
        (
            edge["y2"]
            -
            edge["y1"]
        )
        * position
    )

    return {
        "edge_id":
            edge["id"],

        "edge_position":
            round(
                position,
                5
            ),

        "x":
            round(
                x,
                2
            ),

        "y":
            round(
                y,
                2
            ),
    }


# ============================================================
# BUDGET
# ============================================================

BUDGET_OPTIONS = [
    500,
    700,
    1000,
    1200,
    1500,
    1800,
    2000,
    2500,
    3000,
    4000,
]


BUDGET_WEIGHTS = [
    5,
    8,
    15,
    12,
    20,
    8,
    15,
    8,
    6,
    3,
]


def generate_budget():

    return random.choices(
        BUDGET_OPTIONS,
        weights=BUDGET_WEIGHTS,
        k=1
    )[0]


# ============================================================
# MAX TRAVEL TIME
# ============================================================

def generate_max_travel_minutes(
    transport
):

    if transport == "walk":

        options = [
            10,
            15,
            20,
            25,
            30,
            40,
            45,
        ]

        weights = [
            5,
            12,
            22,
            22,
            20,
            10,
            9,
        ]

    else:

        options = [
            10,
            15,
            20,
            25,
            30,
            40,
            45,
            60,
        ]

        weights = [
            3,
            8,
            15,
            18,
            22,
            15,
            10,
            9,
        ]

    return random.choices(
        options,
        weights=weights,
        k=1
    )[0]


# ============================================================
# INDIVIDUAL TIME WINDOW
# ============================================================

def time_to_minutes(value):

    return (
        value.hour * 60
        +
        value.minute
    )


def minutes_to_time(minutes):

    return time(
        minutes // 60,
        minutes % 60
    )


def generate_participant_window(
    meeting_from,
    meeting_until
):

    start_minutes = (
        time_to_minutes(
            meeting_from
        )
    )

    end_minutes = (
        time_to_minutes(
            meeting_until
        )
    )

    # ------------------------------------------
    # 65% доступны всё окно.
    # ------------------------------------------

    if random.random() < 0.65:

        return (
            meeting_from,
            meeting_until,
        )

    # ------------------------------------------
    # Остальные могут прийти позже
    # или уйти раньше.
    # ------------------------------------------

    possible_shift = [
        0,
        15,
        30,
        45,
        60,
    ]

    start_shift = random.choice(
        possible_shift
    )

    end_shift = random.choice(
        possible_shift
    )

    participant_start = (
        start_minutes
        +
        start_shift
    )

    participant_end = (
        end_minutes
        -
        end_shift
    )

    # Не создаём бессмысленное окно.
    # Минимум 90 минут.

    if (
        participant_end
        -
        participant_start
        <
        90
    ):

        return (
            meeting_from,
            meeting_until,
        )

    return (
        minutes_to_time(
            participant_start
        ),
        minutes_to_time(
            participant_end
        ),
    )


# ============================================================
# REQUIRED INTERESTS
# ============================================================

def generate_required_interests(
    user
):

    interests = user[
        "interests"
    ]

    if not interests:
        return []

    # В большинстве случаев пользователь
    # ничего жёстко не требует.

    count = random.choices(
        [0, 1, 2],
        weights=[
            70,
            25,
            5,
        ],
        k=1
    )[0]

    count = min(
        count,
        len(interests)
    )

    if count == 0:
        return []

    return random.sample(
        interests,
        count
    )


# ============================================================
# EXCLUDED CATEGORIES
# ============================================================

def generate_excluded_categories(
    user
):

    excluded = set()

    # ------------------------------------------
    # Если алкоголь не ок,
    # бар часто исключается полностью.
    # ------------------------------------------

    if not user[
        "alcohol_ok"
    ]:

        if random.random() < 0.80:

            excluded.add(
                "bar"
            )

    preferred = set(
        user[
            "preferred_categories"
        ]
    )

    # Иногда человек явно исключает
    # одну категорию, которую обычно
    # не предпочитает.

    if random.random() < 0.25:

        candidates = [
            category
            for category
            in ALL_CATEGORIES

            if category
            not in preferred
        ]

        if candidates:

            excluded.add(
                random.choice(
                    candidates
                )
            )

    # Очень редко — ещё одно исключение.

    if random.random() < 0.08:

        candidates = [
            category
            for category
            in ALL_CATEGORIES

            if category
            not in preferred

            and category
            not in excluded
        ]

        if candidates:

            excluded.add(
                random.choice(
                    candidates
                )
            )

    return sorted(
        excluded
    )


# ============================================================
# GENERATE PARTICIPANT
# ============================================================

def generate_participant(
    user,
    meeting_from,
    meeting_until,
    edges
):

    transport = (
        generate_transport(
            user
        )
    )

    start_location = (
        choose_start_location(
            user,
            transport,
            edges
        )
    )

    (
        participant_from,
        participant_until,
    ) = generate_participant_window(
        meeting_from,
        meeting_until
    )

    return {
        "user_id":
            user["id"],

        "start_edge_id":
            start_location[
                "edge_id"
            ],

        "start_edge_position":
            start_location[
                "edge_position"
            ],

        "start_x":
            start_location[
                "x"
            ],

        "start_y":
            start_location[
                "y"
            ],

        "transport":
            transport,

        "budget_max":
            generate_budget(),

        "max_travel_minutes":
            generate_max_travel_minutes(
                transport
            ),

        "available_from":
            participant_from,

        "available_until":
            participant_until,

        "required_interests":
            generate_required_interests(
                user
            ),

        "excluded_categories":
            generate_excluded_categories(
                user
            ),
    }


# ============================================================
# GENERATE MEETING
# ============================================================

def generate_meeting(
    group,
    edges
):

    meeting_date = (
        generate_meeting_date()
    )

    (
        meeting_from,
        meeting_until,
    ) = generate_time_window()

    participants = []

    for user in group[
        "members"
    ]:

        participant = (
            generate_participant(
                user,
                meeting_from,
                meeting_until,
                edges
            )
        )

        participants.append(
            participant
        )

    return {
        "group_id":
            group["id"],

        "group_name":
            group["name"],

        "meeting_date":
            meeting_date,

        "available_from":
            meeting_from,

        "available_until":
            meeting_until,

        "status":
            "planning",

        "participants":
            participants,
    }


# ============================================================
# GENERATE ALL MEETINGS
# ============================================================

def generate_meetings(
    groups,
    edges
):

    meetings = []

    # ------------------------------------------
    # Сначала каждой группе гарантируем
    # хотя бы одну встречу.
    # ------------------------------------------

    shuffled_groups = list(
        groups
    )

    random.shuffle(
        shuffled_groups
    )

    for group in shuffled_groups:

        if (
            len(meetings)
            >=
            MEETINGS_COUNT
        ):
            break

        meetings.append(
            generate_meeting(
                group,
                edges
            )
        )

    # ------------------------------------------
    # Остальные meetings распределяем
    # случайно.
    # ------------------------------------------

    while (
        len(meetings)
        <
        MEETINGS_COUNT
    ):

        group = random.choice(
            groups
        )

        meetings.append(
            generate_meeting(
                group,
                edges
            )
        )

    return meetings


# ============================================================
# STATISTICS
# ============================================================

def print_statistics(
    meetings
):

    print()
    print(
        "================================"
    )

    print(
        "      MEETING STATISTICS"
    )

    print(
        "================================"
    )

    print(
        f"Meetings: "
        f"{len(meetings)}"
    )

    participants = [
        participant

        for meeting
        in meetings

        for participant
        in meeting[
            "participants"
        ]
    ]

    print(
        f"Participant rows: "
        f"{len(participants)}"
    )

    # ------------------------------------------
    # Average group size
    # ------------------------------------------

    average_size = (
        sum(
            len(
                meeting[
                    "participants"
                ]
            )
            for meeting
            in meetings
        )
        /
        len(meetings)
    )

    print(
        "Average meeting size:",
        round(
            average_size,
            2
        )
    )

    # ------------------------------------------
    # Budget
    # ------------------------------------------

    average_budget = (
        sum(
            participant[
                "budget_max"
            ]
            for participant
            in participants
        )
        /
        len(participants)
    )

    print(
        "Average budget:",
        round(
            average_budget
        ),
        "RUB"
    )

    # ------------------------------------------
    # Transport
    # ------------------------------------------

    walk_count = sum(
        1
        for participant
        in participants

        if (
            participant[
                "transport"
            ]
            ==
            "walk"
        )
    )

    car_count = (
        len(participants)
        -
        walk_count
    )

    print(
        "Walk:",
        walk_count
    )

    print(
        "Car:",
        car_count
    )

    # ------------------------------------------
    # Example
    # ------------------------------------------

    print()
    print("EXAMPLE MEETINGS")

    for meeting in meetings[:3]:

        print()

        print(
            meeting[
                "group_name"
            ],
            "|",
            meeting[
                "meeting_date"
            ],
            "|",
            meeting[
                "available_from"
            ],
            "-",
            meeting[
                "available_until"
            ]
        )

        for participant in meeting[
            "participants"
        ]:

            print(
                "  user:",
                participant[
                    "user_id"
                ],

                "|",
                participant[
                    "transport"
                ],

                "| budget:",
                participant[
                    "budget_max"
                ],

                "| travel:",
                participant[
                    "max_travel_minutes"
                ],

                "| interests:",
                participant[
                    "required_interests"
                ],

                "| excluded:",
                participant[
                    "excluded_categories"
                ]
            )


# ============================================================
# SAVE DATABASE
# ============================================================

def save_meetings(
    cursor,
    meetings
):

    cursor.execute("""
        TRUNCATE TABLE
            meeting_participants,
            meetings
        RESTART IDENTITY CASCADE;
    """)

    for meeting in meetings:

        # ======================================
        # MEETING
        # ======================================

        cursor.execute(
            """
            INSERT INTO meetings (
                group_id,
                meeting_date,
                available_from,
                available_until,
                status
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING id;
            """,
            (
                meeting[
                    "group_id"
                ],

                meeting[
                    "meeting_date"
                ],

                meeting[
                    "available_from"
                ],

                meeting[
                    "available_until"
                ],

                meeting[
                    "status"
                ],
            )
        )

        meeting_id = (
            cursor.fetchone()[0]
        )

        # ======================================
        # PARTICIPANTS
        # ======================================

        for participant in meeting[
            "participants"
        ]:

            cursor.execute(
                """
                INSERT INTO
                    meeting_participants (
                        meeting_id,
                        user_id,

                        start_edge_id,
                        start_edge_position,

                        start_x,
                        start_y,

                        transport,

                        budget_max,
                        max_travel_minutes,

                        available_from,
                        available_until,

                        required_interests,
                        excluded_categories
                    )
                VALUES (
                    %s, %s,
                    %s, %s,
                    %s, %s,
                    %s,
                    %s, %s,
                    %s, %s,
                    %s, %s
                );
                """,
                (
                    meeting_id,

                    participant[
                        "user_id"
                    ],

                    participant[
                        "start_edge_id"
                    ],

                    participant[
                        "start_edge_position"
                    ],

                    participant[
                        "start_x"
                    ],

                    participant[
                        "start_y"
                    ],

                    participant[
                        "transport"
                    ],

                    participant[
                        "budget_max"
                    ],

                    participant[
                        "max_travel_minutes"
                    ],

                    participant[
                        "available_from"
                    ],

                    participant[
                        "available_until"
                    ],

                    participant[
                        "required_interests"
                    ],

                    participant[
                        "excluded_categories"
                    ],
                )
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Генерируем meetings..."
    )

    connection = None
    cursor = None

    try:

        connection = (
            psycopg2.connect(
                **DB_CONFIG
            )
        )

        cursor = (
            connection.cursor()
        )

        # --------------------------------------
        # Load groups
        # --------------------------------------

        groups = load_groups(
            cursor
        )

        if not groups:

            raise RuntimeError(
                "friend_groups пуст. "
                "Сначала запусти "
                "generate_friend_groups.py."
            )

        print(
            f"Загружено groups: "
            f"{len(groups)}"
        )

        # --------------------------------------
        # Load city
        # --------------------------------------

        edges = load_edges(
            cursor
        )

        if not edges:

            raise RuntimeError(
                "city_edges пуст."
            )

        print(
            f"Загружено edges: "
            f"{len(edges)}"
        )

        # --------------------------------------
        # Generate
        # --------------------------------------

        meetings = (
            generate_meetings(
                groups,
                edges
            )
        )

        print_statistics(
            meetings
        )

        # --------------------------------------
        # Save
        # --------------------------------------

        save_meetings(
            cursor,
            meetings
        )

        connection.commit()

        print()
        print(
            f"Успешно сохранено "
            f"{len(meetings)} meetings."
        )

    except Exception as error:

        if connection:

            connection.rollback()

        print()
        print("ОШИБКА:")
        print(error)

        raise

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


if __name__ == "__main__":
    main()