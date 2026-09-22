import random

import psycopg2


# ============================================================
# CONFIG
# ============================================================

SEED = 42
USERS_COUNT = 150

random.seed(SEED)


DB_CONFIG = {
    "dbname": "DataBase",
    "user": "postgres",
    "password": "12345",
    "host": "localhost",
    "port": 12345,
}


# ============================================================
# NAMES
# ============================================================

FIRST_NAMES = [
    "Александр",
    "Алексей",
    "Андрей",
    "Антон",
    "Артём",
    "Борис",
    "Вадим",
    "Виктор",
    "Даниил",
    "Денис",
    "Дмитрий",
    "Егор",
    "Иван",
    "Илья",
    "Кирилл",
    "Максим",
    "Михаил",
    "Никита",
    "Олег",
    "Павел",
    "Роман",
    "Сергей",
    "Тимур",
    "Фёдор",

    "Алина",
    "Анастасия",
    "Анна",
    "Валерия",
    "Вера",
    "Виктория",
    "Дарья",
    "Диана",
    "Екатерина",
    "Елена",
    "Ирина",
    "Ксения",
    "Мария",
    "Марина",
    "Наталья",
    "Ольга",
    "Полина",
    "Светлана",
    "София",
    "Татьяна",
    "Юлия",
]


LAST_NAMES = [
    "Иванов",
    "Петров",
    "Смирнов",
    "Кузнецов",
    "Попов",
    "Соколов",
    "Лебедев",
    "Козлов",
    "Новиков",
    "Морозов",
    "Волков",
    "Соловьёв",
    "Васильев",
    "Зайцев",
    "Павлов",
    "Семёнов",
    "Голубев",
    "Виноградов",
    "Богданов",
    "Воробьёв",
]


used_names = set()


def generate_name():

    while True:

        first_name = random.choice(
            FIRST_NAMES
        )

        last_name = random.choice(
            LAST_NAMES
        )

        name = (
            f"{first_name} "
            f"{last_name}"
        )

        if name not in used_names:

            used_names.add(name)

            return name


# ============================================================
# INTEREST PROFILES
# ============================================================
#
# Вместо независимого random по каждому interest
# создаём несколько архетипов.
#
# Пользователь может получить 1-2 профиля.
#
# ============================================================

INTEREST_PROFILES = {

    "foodie": [
        "food",
        "coffee",
        "desserts",
        "conversation",
    ],

    "gamer": [
        "games",
        "gaming",
        "board_games",
        "competitive",
    ],

    "culture": [
        "art",
        "culture",
        "learning",
        "creative",
    ],

    "active": [
        "active",
        "competitive",
        "adrenaline",
        "walking",
    ],

    "nightlife": [
        "nightlife",
        "music",
        "drinks",
        "social",
    ],

    "relaxed": [
        "relax",
        "conversation",
        "coffee",
        "nature",
    ],

    "movie_fan": [
        "movies",
        "culture",
        "relax",
    ],

    "outdoor": [
        "outdoor",
        "nature",
        "walking",
        "active",
    ],
}


PROFILE_WEIGHTS = {
    "foodie": 20,
    "gamer": 15,
    "culture": 10,
    "active": 13,
    "nightlife": 12,
    "relaxed": 15,
    "movie_fan": 8,
    "outdoor": 7,
}


# ============================================================
# INTEREST -> PLACE CATEGORY
# ============================================================

INTEREST_TO_CATEGORIES = {

    "food": [
        "restaurant",
        "cafe",
    ],

    "coffee": [
        "cafe",
    ],

    "desserts": [
        "cafe",
        "restaurant",
    ],

    "conversation": [
        "cafe",
        "restaurant",
        "bar",
        "board_game_club",
        "billiards",
    ],

    "games": [
        "board_game_club",
        "escape_room",
        "bowling",
        "arcade",
        "billiards",
    ],

    "gaming": [
        "arcade",
        "board_game_club",
    ],

    "board_games": [
        "board_game_club",
    ],

    "competitive": [
        "bowling",
        "karting",
        "billiards",
        "arcade",
        "escape_room",
        "board_game_club",
    ],

    "art": [
        "museum",
        "gallery",
    ],

    "culture": [
        "museum",
        "gallery",
        "cinema",
    ],

    "learning": [
        "museum",
        "gallery",
    ],

    "creative": [
        "gallery",
        "museum",
        "karaoke",
    ],

    "active": [
        "karting",
        "bowling",
        "park_activity",
    ],

    "adrenaline": [
        "karting",
        "escape_room",
    ],

    "walking": [
        "park_activity",
    ],

    "nightlife": [
        "bar",
        "karaoke",
        "billiards",
    ],

    "music": [
        "karaoke",
        "bar",
    ],

    "drinks": [
        "bar",
        "billiards",
        "karaoke",
    ],

    "social": [
        "bar",
        "karaoke",
        "bowling",
        "restaurant",
    ],

    "relax": [
        "cafe",
        "cinema",
        "park_activity",
    ],

    "nature": [
        "park_activity",
    ],

    "movies": [
        "cinema",
    ],

    "outdoor": [
        "park_activity",
    ],
}


# ============================================================
# LOAD EDGES
# ============================================================

def load_edges(cursor):

    cursor.execute("""
        SELECT
            e.id,
            e.road_type,

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

        WHERE e.road_type <> 'pedestrian'

        ORDER BY e.id;
    """)

    rows = cursor.fetchall()

    edges = []

    for row in rows:

        edges.append({
            "id": row[0],

            "road_type": row[1],

            "x1": row[2],
            "y1": row[3],
            "district1": row[4],

            "x2": row[5],
            "y2": row[6],
            "district2": row[7],
        })

    return edges


# ============================================================
# HOME DISTRICT DISTRIBUTION
# ============================================================

HOME_DISTRICT_WEIGHTS = {
    "south": 30,
    "university": 20,
    "north": 15,
    "downtown": 15,
    "mall": 10,
    "park": 10,
}


def choose_home_district():

    districts = list(
        HOME_DISTRICT_WEIGHTS.keys()
    )

    weights = list(
        HOME_DISTRICT_WEIGHTS.values()
    )

    return random.choices(
        districts,
        weights=weights,
        k=1,
    )[0]


# ============================================================
# HOME EDGE
# ============================================================

def choose_home_edge(
    edges,
    desired_district
):

    candidates = []

    for edge in edges:

        if desired_district in {
            edge["district1"],
            edge["district2"],
        }:

            candidates.append(
                edge
            )

    if candidates:

        return random.choice(
            candidates
        )

    return random.choice(
        edges
    )


# ============================================================
# HOME POSITION
# ============================================================

def generate_home_position(edge):

    # Не размещаем пользователя непосредственно
    # на intersection.

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

    return (
        round(position, 5),
        round(x, 2),
        round(y, 2),
    )


# ============================================================
# INTEREST GENERATION
# ============================================================

def choose_profile():

    profiles = list(
        PROFILE_WEIGHTS.keys()
    )

    weights = list(
        PROFILE_WEIGHTS.values()
    )

    return random.choices(
        profiles,
        weights=weights,
        k=1,
    )[0]


def generate_interests():

    # Большинство получает один основной профиль.
    # Часть пользователей — два.

    profile_count = random.choices(
        [1, 2],
        weights=[70, 30],
        k=1,
    )[0]

    selected_profiles = set()

    while (
        len(selected_profiles)
        <
        profile_count
    ):

        selected_profiles.add(
            choose_profile()
        )

    interests = set()

    for profile in selected_profiles:

        profile_interests = (
            INTEREST_PROFILES[
                profile
            ]
        )

        # Не обязательно брать абсолютно
        # все интересы архетипа.

        count = random.randint(
            max(
                2,
                len(
                    profile_interests
                ) - 1
            ),
            len(
                profile_interests
            )
        )

        selected = random.sample(
            profile_interests,
            count
        )

        interests.update(
            selected
        )

    return sorted(
        interests
    )


# ============================================================
# PREFERRED CATEGORIES
# ============================================================

def generate_preferred_categories(
    interests
):

    category_scores = {}

    for interest in interests:

        categories = (
            INTEREST_TO_CATEGORIES.get(
                interest,
                []
            )
        )

        for category in categories:

            category_scores[
                category
            ] = (
                category_scores.get(
                    category,
                    0
                )
                + 1
            )

    if not category_scores:

        return [
            "cafe",
            "restaurant",
        ]

    # ------------------------------------------
    # Добавляем немного случайности.
    # ------------------------------------------

    scored = []

    for (
        category,
        score
    ) in category_scores.items():

        noisy_score = (
            score
            +
            random.uniform(
                0,
                1.5
            )
        )

        scored.append(
            (
                category,
                noisy_score
            )
        )

    scored.sort(
        key=lambda item:
            item[1],
        reverse=True
    )

    max_count = min(
        5,
        len(scored)
    )

    min_count = min(
        2,
        max_count
    )

    count = random.randint(
        min_count,
        max_count
    )

    return [
        category
        for (
            category,
            _
        ) in scored[:count]
    ]


# ============================================================
# NOISE
# ============================================================

def generate_noise_preference(
    interests
):

    # Nightlife люди чаще терпимы к шуму.

    if (
        "nightlife" in interests
        or
        "music" in interests
    ):

        return random.choices(
            [
                "medium",
                "loud",
                "any",
                "quiet",
            ],
            weights=[
                40,
                30,
                25,
                5,
            ],
            k=1,
        )[0]

    # Relax / culture чаще предпочитают
    # спокойные места.

    if (
        "relax" in interests
        or
        "art" in interests
        or
        "learning" in interests
    ):

        return random.choices(
            [
                "quiet",
                "medium",
                "any",
                "loud",
            ],
            weights=[
                50,
                30,
                18,
                2,
            ],
            k=1,
        )[0]

    return random.choices(
        [
            "quiet",
            "medium",
            "loud",
            "any",
        ],
        weights=[
            25,
            40,
            10,
            25,
        ],
        k=1,
    )[0]


# ============================================================
# ALCOHOL
# ============================================================

def generate_alcohol_ok(
    interests
):

    if (
        "drinks" in interests
        or
        "nightlife" in interests
    ):

        return random.random() < 0.95

    return random.random() < 0.70


# ============================================================
# TRANSPORT
# ============================================================

def generate_transport(
    district,
    interests
):

    # Downtown / university:
    # больше пеших пользователей.

    if district in {
        "downtown",
        "university",
    }:

        walk_probability = 0.75

    elif district == "south":

        walk_probability = 0.45

    elif district == "north":

        walk_probability = 0.50

    elif district == "mall":

        walk_probability = 0.40

    else:

        walk_probability = 0.60

    # Outdoor/walking немного увеличивает
    # вероятность пешего транспорта.

    if (
        "walking" in interests
        or
        "outdoor" in interests
    ):

        walk_probability += 0.15

    walk_probability = min(
        walk_probability,
        0.90
    )

    if (
        random.random()
        <
        walk_probability
    ):
        return "walk"

    return "car"


# ============================================================
# USER GENERATOR
# ============================================================

def generate_user(edges):

    name = generate_name()

    desired_district = (
        choose_home_district()
    )

    edge = choose_home_edge(
        edges,
        desired_district
    )

    (
        edge_position,
        home_x,
        home_y,
    ) = generate_home_position(
        edge
    )

    # Если edge соединяет два района,
    # оставляем выбранный район, если он
    # действительно относится к edge.

    if desired_district in {
        edge["district1"],
        edge["district2"],
    }:

        home_district = (
            desired_district
        )

    else:

        home_district = (
            edge["district1"]
        )

    interests = (
        generate_interests()
    )

    preferred_categories = (
        generate_preferred_categories(
            interests
        )
    )

    noise_preference = (
        generate_noise_preference(
            interests
        )
    )

    alcohol_ok = (
        generate_alcohol_ok(
            interests
        )
    )

    default_transport = (
        generate_transport(
            home_district,
            interests
        )
    )

    return {
        "name":
            name,

        "home_edge_id":
            edge["id"],

        "home_edge_position":
            edge_position,

        "home_x":
            home_x,

        "home_y":
            home_y,

        "home_district":
            home_district,

        "interests":
            interests,

        "preferred_categories":
            preferred_categories,

        "noise_preference":
            noise_preference,

        "alcohol_ok":
            alcohol_ok,

        "default_transport":
            default_transport,

        "active":
            True,
    }


# ============================================================
# INSERT
# ============================================================

INSERT_SQL = """
INSERT INTO users (
    name,

    home_edge_id,
    home_edge_position,

    home_x,
    home_y,

    home_district,

    interests,
    preferred_categories,

    noise_preference,
    alcohol_ok,

    default_transport,

    active
)
VALUES (
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s,
    %s
);
"""


def insert_user(
    cursor,
    user
):

    cursor.execute(
        INSERT_SQL,
        (
            user["name"],

            user["home_edge_id"],
            user["home_edge_position"],

            user["home_x"],
            user["home_y"],

            user["home_district"],

            user["interests"],

            user[
                "preferred_categories"
            ],

            user[
                "noise_preference"
            ],

            user[
                "alcohol_ok"
            ],

            user[
                "default_transport"
            ],

            user["active"],
        )
    )


# ============================================================
# STATISTICS
# ============================================================

def print_statistics(users):

    print()
    print(
        "================================"
    )

    print(
        "       USERS STATISTICS"
    )

    print(
        "================================"
    )

    print(
        f"Total: {len(users)}"
    )

    # ------------------------------------------
    # Districts
    # ------------------------------------------

    district_counts = {}

    for user in users:

        district = user[
            "home_district"
        ]

        district_counts[
            district
        ] = (
            district_counts.get(
                district,
                0
            )
            + 1
        )

    print()
    print("BY DISTRICT")

    for (
        district,
        count
    ) in sorted(
        district_counts.items(),
        key=lambda item:
            item[1],
        reverse=True
    ):

        print(
            f"{district:15}"
            f"{count:4}"
        )

    # ------------------------------------------
    # Transport
    # ------------------------------------------

    transport_counts = {}

    for user in users:

        transport = user[
            "default_transport"
        ]

        transport_counts[
            transport
        ] = (
            transport_counts.get(
                transport,
                0
            )
            + 1
        )

    print()
    print("BY TRANSPORT")

    for (
        transport,
        count
    ) in sorted(
        transport_counts.items()
    ):

        print(
            f"{transport:15}"
            f"{count:4}"
        )

    # ------------------------------------------
    # Noise
    # ------------------------------------------

    noise_counts = {}

    for user in users:

        noise = user[
            "noise_preference"
        ]

        noise_counts[
            noise
        ] = (
            noise_counts.get(
                noise,
                0
            )
            + 1
        )

    print()
    print("BY NOISE PREFERENCE")

    for (
        noise,
        count
    ) in sorted(
        noise_counts.items()
    ):

        print(
            f"{noise:15}"
            f"{count:4}"
        )

    # ------------------------------------------
    # Top interests
    # ------------------------------------------

    interest_counts = {}

    for user in users:

        for interest in user[
            "interests"
        ]:

            interest_counts[
                interest
            ] = (
                interest_counts.get(
                    interest,
                    0
                )
                + 1
            )

    print()
    print("TOP INTERESTS")

    for (
        interest,
        count
    ) in sorted(
        interest_counts.items(),
        key=lambda item:
            item[1],
        reverse=True
    )[:15]:

        print(
            f"{interest:20}"
            f"{count:4}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Генерируем synthetic users..."
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
        # Graph
        # --------------------------------------

        edges = load_edges(
            cursor
        )

        if not edges:

            raise RuntimeError(
                "Нет доступных city_edges. "
                "Сначала запусти "
                "generate_city.py."
            )

        print(
            f"Загружено edges: "
            f"{len(edges)}"
        )

        # --------------------------------------
        # Generate
        # --------------------------------------

        users = [
            generate_user(
                edges
            )

            for _ in range(
                USERS_COUNT
            )
        ]

        print_statistics(
            users
        )

        # --------------------------------------
        # Clear old users
        # --------------------------------------

        cursor.execute("""
            TRUNCATE TABLE users
            RESTART IDENTITY CASCADE;
        """)

        # --------------------------------------
        # Insert
        # --------------------------------------

        for user in users:

            insert_user(
                cursor,
                user
            )

        connection.commit()

        print()
        print(
            f"Успешно сохранено "
            f"{USERS_COUNT} users."
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