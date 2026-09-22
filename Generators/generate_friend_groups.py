import random

import psycopg2


# ============================================================
# CONFIG
# ============================================================

SEED = 42

GROUPS_COUNT = 40

MIN_GROUP_SIZE = 2
MAX_GROUP_SIZE = 8

random.seed(SEED)


DB_CONFIG = {
    "dbname": "DataBase",
    "user": "postgres",
    "password": "12345",
    "host": "localhost",
    "port": 12345,
}


# ============================================================
# GROUP NAMES
# ============================================================

GROUP_ADJECTIVES = [
    "Весёлые",
    "Старые",
    "Городские",
    "Ночные",
    "Ленивые",
    "Активные",
    "Случайные",
    "Северные",
    "Южные",
    "Уютные",
    "Большие",
    "Местные",
]


GROUP_NOUNS = [
    "Друзья",
    "Соседи",
    "Коллеги",
    "Игроки",
    "Гуляки",
    "Путешественники",
    "Исследователи",
    "Кофеманы",
    "Команда",
    "Компания",
    "Ребята",
    "Знатоки",
]


used_group_names = set()


def generate_group_name():

    while True:

        adjective = random.choice(
            GROUP_ADJECTIVES
        )

        noun = random.choice(
            GROUP_NOUNS
        )

        name = (
            f"{adjective} {noun}"
        )

        if name not in used_group_names:

            used_group_names.add(
                name
            )

            return name


# ============================================================
# LOAD USERS
# ============================================================

def load_users(cursor):

    cursor.execute("""
        SELECT
            id,
            name,
            home_district,
            interests,
            preferred_categories,
            default_transport
        FROM users
        WHERE active = TRUE
        ORDER BY id;
    """)

    rows = cursor.fetchall()

    users = []

    for row in rows:

        users.append({
            "id":
                row[0],

            "name":
                row[1],

            "home_district":
                row[2],

            "interests":
                set(
                    row[3] or []
                ),

            "preferred_categories":
                set(
                    row[4] or []
                ),

            "default_transport":
                row[5],
        })

    return users


# ============================================================
# SIMILARITY
# ============================================================
#
# Это НЕ будущий recommendation score.
#
# Он нужен только для генерации более правдоподобных
# компаний друзей.
#
# ============================================================

def jaccard_similarity(
    set_a,
    set_b
):

    if (
        not set_a
        and
        not set_b
    ):
        return 0.0

    union = (
        set_a
        |
        set_b
    )

    if not union:
        return 0.0

    intersection = (
        set_a
        &
        set_b
    )

    return (
        len(intersection)
        /
        len(union)
    )


def calculate_similarity(
    user_a,
    user_b
):

    interest_similarity = (
        jaccard_similarity(
            user_a["interests"],
            user_b["interests"]
        )
    )

    category_similarity = (
        jaccard_similarity(
            user_a[
                "preferred_categories"
            ],
            user_b[
                "preferred_categories"
            ]
        )
    )

    # Небольшой бонус людям из одного района.
    district_bonus = (
        0.15
        if (
            user_a["home_district"]
            ==
            user_b["home_district"]
        )
        else 0.0
    )

    score = (
        0.65
        * interest_similarity

        +

        0.25
        * category_similarity

        +

        district_bonus
    )

    return score


# ============================================================
# GROUP SIZE
# ============================================================
#
# Большинство компаний будет 3-5 человек.
# ============================================================

def generate_group_size():

    sizes = [
        2,
        3,
        4,
        5,
        6,
        7,
        8,
    ]

    weights = [
        10,
        22,
        27,
        20,
        11,
        6,
        4,
    ]

    return random.choices(
        sizes,
        weights=weights,
        k=1
    )[0]


# ============================================================
# SELECT MEMBER
# ============================================================

def weighted_candidate_choice(
    candidates
):

    if not candidates:
        return None

    weights = []

    for (
        user,
        score
    ) in candidates:

        # Даже человек с низким similarity
        # должен иметь шанс попасть в компанию.
        #
        # Это создаёт неоднородные группы.

        weight = (
            0.15
            +
            score
        )

        weights.append(
            weight
        )

    users = [
        user
        for user, _ in candidates
    ]

    return random.choices(
        users,
        weights=weights,
        k=1
    )[0]


# ============================================================
# GROUP GENERATION
# ============================================================

def generate_group(
    users
):

    group_size = (
        generate_group_size()
    )

    # ------------------------------------------
    # 1. Первый пользователь — seed
    # ------------------------------------------

    seed_user = random.choice(
        users
    )

    members = [
        seed_user
    ]

    member_ids = {
        seed_user["id"]
    }

    # ------------------------------------------
    # 2. Остальные пользователи
    # ------------------------------------------

    while (
        len(members)
        <
        group_size
    ):

        candidates = []

        for user in users:

            if (
                user["id"]
                in member_ids
            ):
                continue

            # ----------------------------------
            # Сходство с группой считаем
            # как среднее сходство со всеми
            # текущими участниками.
            # ----------------------------------

            similarities = [
                calculate_similarity(
                    user,
                    member
                )
                for member in members
            ]

            average_similarity = (
                sum(similarities)
                /
                len(similarities)
            )

            candidates.append(
                (
                    user,
                    average_similarity
                )
            )

        if not candidates:
            break

        # --------------------------------------
        # Иногда специально добавляем человека
        # с менее похожими интересами.
        #
        # Это важно для будущего тестирования
        # компромиссных рекомендаций.
        # --------------------------------------

        add_different_person = (
            random.random()
            <
            0.20
        )

        if add_different_person:

            candidates.sort(
                key=lambda item:
                    item[1]
            )

            # Берём кого-то из нижней трети
            # по similarity.

            bottom_count = max(
                1,
                len(candidates)
                // 3
            )

            bottom_candidates = (
                candidates[
                    :bottom_count
                ]
            )

            selected_user = (
                random.choice(
                    bottom_candidates
                )[0]
            )

        else:

            selected_user = (
                weighted_candidate_choice(
                    candidates
                )
            )

        members.append(
            selected_user
        )

        member_ids.add(
            selected_user["id"]
        )

    return members


# ============================================================
# GROUP METRICS
# ============================================================

def calculate_group_metrics(
    members
):

    # ------------------------------------------
    # Общие interests
    # ------------------------------------------

    if not members:

        return {
            "common_interests": set(),
            "all_interests": set(),
            "avg_similarity": 0.0,
        }

    common_interests = set(
        members[0]["interests"]
    )

    all_interests = set()

    for member in members:

        common_interests &= (
            member["interests"]
        )

        all_interests |= (
            member["interests"]
        )

    # ------------------------------------------
    # Average pair similarity
    # ------------------------------------------

    similarities = []

    for i in range(
        len(members)
    ):

        for j in range(
            i + 1,
            len(members)
        ):

            similarity = (
                calculate_similarity(
                    members[i],
                    members[j]
                )
            )

            similarities.append(
                similarity
            )

    if similarities:

        avg_similarity = (
            sum(similarities)
            /
            len(similarities)
        )

    else:

        avg_similarity = 0.0

    return {
        "common_interests":
            common_interests,

        "all_interests":
            all_interests,

        "avg_similarity":
            avg_similarity,
    }


# ============================================================
# GENERATE ALL GROUPS
# ============================================================

def generate_groups(
    users
):

    groups = []

    # Набор нужен, чтобы не создавать
    # две абсолютно одинаковые компании.

    existing_member_sets = set()

    attempts = 0

    max_attempts = (
        GROUPS_COUNT
        * 50
    )

    while (
        len(groups)
        <
        GROUPS_COUNT

        and

        attempts
        <
        max_attempts
    ):

        attempts += 1

        members = generate_group(
            users
        )

        member_ids = tuple(
            sorted(
                member["id"]
                for member in members
            )
        )

        if (
            member_ids
            in existing_member_sets
        ):
            continue

        existing_member_sets.add(
            member_ids
        )

        metrics = (
            calculate_group_metrics(
                members
            )
        )

        groups.append({
            "name":
                generate_group_name(),

            "members":
                members,

            "metrics":
                metrics,
        })

    if (
        len(groups)
        <
        GROUPS_COUNT
    ):

        raise RuntimeError(
            "Не удалось создать "
            f"{GROUPS_COUNT} "
            "уникальных групп."
        )

    return groups


# ============================================================
# STATISTICS
# ============================================================

def print_statistics(
    groups
):

    print()
    print(
        "================================"
    )

    print(
        "    FRIEND GROUP STATISTICS"
    )

    print(
        "================================"
    )

    print(
        f"Groups: {len(groups)}"
    )

    # ------------------------------------------
    # Sizes
    # ------------------------------------------

    size_counts = {}

    for group in groups:

        size = len(
            group["members"]
        )

        size_counts[
            size
        ] = (
            size_counts.get(
                size,
                0
            )
            + 1
        )

    print()
    print("GROUP SIZES")

    for size in sorted(
        size_counts
    ):

        print(
            f"{size} members: "
            f"{size_counts[size]}"
        )

    # ------------------------------------------
    # Average similarity
    # ------------------------------------------

    similarities = [
        group[
            "metrics"
        ][
            "avg_similarity"
        ]
        for group in groups
    ]

    avg_similarity = (
        sum(similarities)
        /
        len(similarities)
    )

    print()

    print(
        "Average group similarity:",
        round(
            avg_similarity,
            3
        )
    )

    # ------------------------------------------
    # Example groups
    # ------------------------------------------

    print()
    print("EXAMPLE GROUPS")

    for group in groups[:5]:

        print()
        print(
            group["name"]
        )

        print(
            "  similarity:",
            round(
                group[
                    "metrics"
                ][
                    "avg_similarity"
                ],
                3
            )
        )

        print(
            "  common interests:",
            sorted(
                group[
                    "metrics"
                ][
                    "common_interests"
                ]
            )
        )

        print(
            "  members:"
        )

        for member in group[
            "members"
        ]:

            print(
                "   -",
                member["name"],
                "|",
                member[
                    "home_district"
                ],
                "|",
                sorted(
                    member[
                        "interests"
                    ]
                )
            )


# ============================================================
# DATABASE INSERT
# ============================================================

def save_groups(
    cursor,
    groups
):

    cursor.execute("""
        TRUNCATE TABLE
            friend_group_members,
            friend_groups
        RESTART IDENTITY CASCADE;
    """)

    for group in groups:

        cursor.execute(
            """
            INSERT INTO friend_groups (
                name
            )
            VALUES (%s)
            RETURNING id;
            """,
            (
                group["name"],
            )
        )

        group_id = (
            cursor.fetchone()[0]
        )

        for member in group[
            "members"
        ]:

            cursor.execute(
                """
                INSERT INTO
                    friend_group_members (
                        group_id,
                        user_id
                    )
                VALUES (%s, %s);
                """,
                (
                    group_id,
                    member["id"],
                )
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Генерируем friend groups..."
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
        # Users
        # --------------------------------------

        users = load_users(
            cursor
        )

        if (
            len(users)
            <
            MAX_GROUP_SIZE
        ):

            raise RuntimeError(
                "Недостаточно пользователей. "
                "Сначала запусти "
                "generate_users.py."
            )

        print(
            f"Загружено users: "
            f"{len(users)}"
        )

        # --------------------------------------
        # Generate
        # --------------------------------------

        groups = generate_groups(
            users
        )

        print_statistics(
            groups
        )

        # --------------------------------------
        # Save
        # --------------------------------------

        save_groups(
            cursor,
            groups
        )

        connection.commit()

        print()
        print(
            f"Успешно сохранено "
            f"{len(groups)} "
            "friend groups."
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