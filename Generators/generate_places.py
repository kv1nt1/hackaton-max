import json
import random

import psycopg2


# ============================================================
# CONFIG
# ============================================================

SEED = 42
PLACES_COUNT = 500

random.seed(SEED)


from db_config import DB_CONFIG


# ============================================================
# DISTRICT PRICE FACTORS
# ============================================================

DISTRICT_PRICE_FACTOR = {
    "downtown": 1.25,
    "mall": 1.15,
    "north": 1.05,
    "university": 0.85,
    "south": 0.90,
    "park": 0.85,
}


# ============================================================
# CONCEPTS
# ============================================================

CONCEPTS = {
    "budget": {
        "price_factor": 0.75,
        "rating_shift": -0.1,
    },

    "standard": {
        "price_factor": 1.00,
        "rating_shift": 0.0,
    },

    "premium": {
        "price_factor": 1.45,
        "rating_shift": 0.2,
    },

    "cozy": {
        "price_factor": 1.05,
        "rating_shift": 0.1,
    },

    "party": {
        "price_factor": 1.15,
        "rating_shift": 0.0,
    },

    "family": {
        "price_factor": 0.95,
        "rating_shift": 0.1,
    },

    "competitive": {
        "price_factor": 1.10,
        "rating_shift": 0.0,
    },
}


# ============================================================
# CATEGORY CONFIG
# ============================================================

CATEGORIES = {

    "restaurant": {
        "weight": 16,

        "price": (900, 3000),

        "duration": (60, 150),
        "group_size": (1, 12),

        "district_weights": {
            "downtown": 35,
            "mall": 20,
            "north": 10,
            "university": 10,
            "south": 20,
            "park": 5,
        },

        "road_weights": {
            "avenue": 45,
            "street": 40,
            "local": 15,
        },

        "concepts": [
            "budget",
            "standard",
            "premium",
            "cozy",
            "family",
        ],

        "interests": [
            "food",
            "conversation",
            "social",
        ],

        "tags": [
            "food",
            "dinner",
            "indoor",
        ],

        "indoor": True,
        "food": True,

        "alcohol_probability": 0.65,
        "booking_probability": 0.35,

        "noise": [
            "quiet",
            "medium",
            "medium",
        ],
    },


    "cafe": {
        "weight": 14,

        "price": (350, 1200),

        "duration": (30, 120),
        "group_size": (1, 8),

        "district_weights": {
            "downtown": 30,
            "university": 25,
            "mall": 15,
            "north": 10,
            "south": 15,
            "park": 5,
        },

        "road_weights": {
            "avenue": 20,
            "street": 45,
            "local": 35,
        },

        "concepts": [
            "budget",
            "standard",
            "premium",
            "cozy",
            "family",
        ],

        "interests": [
            "coffee",
            "desserts",
            "conversation",
            "relax",
        ],

        "tags": [
            "coffee",
            "desserts",
            "indoor",
        ],

        "indoor": True,
        "food": True,

        "alcohol_probability": 0.05,
        "booking_probability": 0.05,

        "noise": [
            "quiet",
            "quiet",
            "medium",
        ],
    },


    "bar": {
        "weight": 8,

        "price": (1000, 3000),

        "duration": (90, 240),
        "group_size": (1, 12),

        "district_weights": {
            "downtown": 55,
            "mall": 20,
            "university": 10,
            "north": 5,
            "south": 10,
        },

        "road_weights": {
            "avenue": 45,
            "street": 45,
            "local": 10,
        },

        "concepts": [
            "standard",
            "premium",
            "cozy",
            "party",
        ],

        "interests": [
            "drinks",
            "conversation",
            "nightlife",
            "social",
        ],

        "tags": [
            "drinks",
            "nightlife",
            "indoor",
        ],

        "indoor": True,
        "food": True,

        "alcohol_probability": 1.0,
        "booking_probability": 0.25,

        "noise": [
            "medium",
            "loud",
            "loud",
        ],
    },


    "cinema": {
        "weight": 8,

        "price": (350, 1000),

        "duration": (90, 180),
        "group_size": (1, 15),

        "district_weights": {
            "downtown": 30,
            "mall": 45,
            "north": 5,
            "university": 5,
            "south": 15,
        },

        "road_weights": {
            "avenue": 70,
            "street": 30,
        },

        "concepts": [
            "budget",
            "standard",
            "premium",
        ],

        "interests": [
            "movies",
            "relax",
            "culture",
        ],

        "tags": [
            "movies",
            "indoor",
            "entertainment",
        ],

        "indoor": True,
        "food": True,

        "alcohol_probability": 0.05,
        "booking_probability": 0.25,

        "noise": [
            "quiet",
            "medium",
        ],
    },


    "bowling": {
        "weight": 7,

        "price": (700, 2000),

        "duration": (60, 180),
        "group_size": (2, 12),

        "district_weights": {
            "downtown": 25,
            "mall": 40,
            "north": 5,
            "south": 20,
            "university": 10,
        },

        "road_weights": {
            "avenue": 60,
            "street": 40,
        },

        "concepts": [
            "standard",
            "premium",
            "family",
            "competitive",
        ],

        "interests": [
            "active",
            "games",
            "competitive",
            "social",
        ],

        "tags": [
            "bowling",
            "games",
            "indoor",
        ],

        "indoor": True,
        "food": True,

        "alcohol_probability": 0.40,
        "booking_probability": 0.55,

        "noise": [
            "medium",
            "loud",
        ],
    },


    "karaoke": {
        "weight": 6,

        "price": (1000, 3000),

        "duration": (120, 300),
        "group_size": (2, 15),

        "district_weights": {
            "downtown": 55,
            "mall": 25,
            "south": 10,
            "university": 10,
        },

        "road_weights": {
            "avenue": 40,
            "street": 55,
            "local": 5,
        },

        "concepts": [
            "standard",
            "premium",
            "party",
        ],

        "interests": [
            "music",
            "nightlife",
            "social",
        ],

        "tags": [
            "music",
            "karaoke",
            "nightlife",
            "indoor",
        ],

        "indoor": True,
        "food": True,

        "alcohol_probability": 0.85,
        "booking_probability": 0.55,

        "noise": [
            "loud",
        ],
    },


    "board_game_club": {
        "weight": 7,

        "price": (300, 1000),

        "duration": (90, 240),
        "group_size": (2, 10),

        "district_weights": {
            "downtown": 25,
            "university": 40,
            "south": 15,
            "north": 10,
            "mall": 10,
        },

        "road_weights": {
            "street": 45,
            "local": 50,
            "avenue": 5,
        },

        "concepts": [
            "budget",
            "standard",
            "cozy",
            "competitive",
        ],

        "interests": [
            "games",
            "board_games",
            "conversation",
            "social",
        ],

        "tags": [
            "games",
            "board_games",
            "indoor",
        ],

        "indoor": True,
        "food": True,

        "alcohol_probability": 0.10,
        "booking_probability": 0.15,

        "noise": [
            "quiet",
            "medium",
        ],
    },


    "escape_room": {
        "weight": 6,

        "price": (700, 1700),

        "duration": (60, 120),
        "group_size": (2, 8),

        "district_weights": {
            "downtown": 35,
            "university": 25,
            "mall": 25,
            "south": 15,
        },

        "road_weights": {
            "street": 50,
            "avenue": 30,
            "local": 20,
        },

        "concepts": [
            "standard",
            "competitive",
        ],

        "interests": [
            "games",
            "competitive",
            "adrenaline",
        ],

        "tags": [
            "quest",
            "games",
            "indoor",
        ],

        "indoor": True,
        "food": False,

        "alcohol_probability": 0.0,
        "booking_probability": 0.95,

        "noise": [
            "quiet",
            "medium",
        ],
    },


    "museum": {
        "weight": 5,

        "price": (200, 900),

        "duration": (60, 180),
        "group_size": (1, 20),

        "district_weights": {
            "downtown": 60,
            "university": 30,
            "north": 10,
        },

        "road_weights": {
            "avenue": 55,
            "street": 40,
            "local": 5,
        },

        "concepts": [
            "budget",
            "standard",
            "premium",
        ],

        "interests": [
            "art",
            "culture",
            "learning",
        ],

        "tags": [
            "museum",
            "culture",
            "indoor",
        ],

        "indoor": True,
        "food": False,

        "alcohol_probability": 0.0,
        "booking_probability": 0.05,

        "noise": [
            "quiet",
        ],
    },


    "gallery": {
        "weight": 4,

        "price": (0, 800),

        "duration": (45, 150),
        "group_size": (1, 15),

        "district_weights": {
            "downtown": 55,
            "university": 35,
            "north": 10,
        },

        "road_weights": {
            "street": 55,
            "local": 30,
            "avenue": 15,
        },

        "concepts": [
            "budget",
            "standard",
            "premium",
            "cozy",
        ],

        "interests": [
            "art",
            "culture",
            "creative",
        ],

        "tags": [
            "art",
            "culture",
            "indoor",
        ],

        "indoor": True,
        "food": False,

        "alcohol_probability": 0.05,
        "booking_probability": 0.05,

        "noise": [
            "quiet",
        ],
    },


    "karting": {
        "weight": 5,

        "price": (1000, 2800),

        "duration": (30, 120),
        "group_size": (1, 10),

        "district_weights": {
            "mall": 35,
            "south": 30,
            "north": 15,
            "downtown": 10,
            "park": 10,
        },

        "road_weights": {
            "avenue": 80,
            "street": 20,
        },

        "concepts": [
            "standard",
            "premium",
            "competitive",
        ],

        "interests": [
            "active",
            "competitive",
            "adrenaline",
        ],

        "tags": [
            "karting",
            "racing",
            "active",
        ],

        "indoor": True,
        "food": False,

        "alcohol_probability": 0.0,
        "booking_probability": 0.50,

        "noise": [
            "loud",
        ],
    },


    "billiards": {
        "weight": 5,

        "price": (500, 1600),

        "duration": (60, 180),
        "group_size": (2, 8),

        "district_weights": {
            "downtown": 35,
            "mall": 20,
            "south": 20,
            "university": 15,
            "north": 10,
        },

        "road_weights": {
            "street": 50,
            "avenue": 30,
            "local": 20,
        },

        "concepts": [
            "budget",
            "standard",
            "premium",
            "cozy",
            "competitive",
        ],

        "interests": [
            "games",
            "competitive",
            "conversation",
        ],

        "tags": [
            "billiards",
            "games",
            "indoor",
        ],

        "indoor": True,
        "food": True,

        "alcohol_probability": 0.50,
        "booking_probability": 0.20,

        "noise": [
            "quiet",
            "medium",
        ],
    },


    "arcade": {
        "weight": 5,

        "price": (500, 1800),

        "duration": (60, 180),
        "group_size": (1, 10),

        "district_weights": {
            "mall": 45,
            "downtown": 20,
            "university": 20,
            "south": 10,
            "north": 5,
        },

        "road_weights": {
            "avenue": 45,
            "street": 50,
            "local": 5,
        },

        "concepts": [
            "budget",
            "standard",
            "competitive",
            "family",
        ],

        "interests": [
            "games",
            "gaming",
            "competitive",
            "social",
        ],

        "tags": [
            "arcade",
            "gaming",
            "indoor",
        ],

        "indoor": True,
        "food": False,

        "alcohol_probability": 0.0,
        "booking_probability": 0.0,

        "noise": [
            "medium",
            "loud",
        ],
    },


    "park_activity": {
        "weight": 4,

        "price": (0, 700),

        "duration": (30, 180),
        "group_size": (1, 20),

        "district_weights": {
            "park": 80,
            "south": 10,
            "north": 10,
        },

        "road_weights": {
            "pedestrian": 70,
            "local": 20,
            "street": 10,
        },

        "concepts": [
            "budget",
            "family",
            "standard",
        ],

        "interests": [
            "outdoor",
            "nature",
            "walking",
            "relax",
        ],

        "tags": [
            "outdoor",
            "nature",
            "walking",
        ],

        "indoor": False,
        "food": False,

        "alcohol_probability": 0.0,
        "booking_probability": 0.0,

        "noise": [
            "quiet",
        ],
    },
}


# ============================================================
# NAMES
# ============================================================

ADJECTIVES = [
    "Urban",
    "Golden",
    "Green",
    "Lucky",
    "Secret",
    "Central",
    "Northern",
    "Southern",
    "Happy",
    "Cozy",
    "Bright",
    "Local",
    "Grand",
    "Smart",
    "Silver",
    "Royal",
    "New",
    "Blue",
    "Red",
    "White",
]


NOUNS = [
    "Fox",
    "Bear",
    "Moon",
    "Corner",
    "House",
    "Point",
    "Space",
    "Garden",
    "Station",
    "Lab",
    "Place",
    "Room",
    "City",
    "Loft",
    "Wave",
    "Orbit",
    "Pixel",
    "Rocket",
    "Friends",
    "Street",
    "Square",
    "Story",
    "Spot",
    "Planet",
    "Time",
]


NAME_SUFFIXES = {
    "restaurant": [
        "Kitchen",
        "Restaurant",
        "Table",
        "Bistro",
    ],

    "cafe": [
        "Coffee",
        "Cafe",
        "Coffee House",
    ],

    "bar": [
        "Bar",
        "Pub",
        "Lounge",
    ],

    "cinema": [
        "Cinema",
        "Movies",
    ],

    "bowling": [
        "Bowling",
        "Lanes",
    ],

    "karaoke": [
        "Karaoke",
        "Voice",
    ],

    "board_game_club": [
        "Games",
        "Game Club",
    ],

    "escape_room": [
        "Quest",
        "Escape",
    ],

    "museum": [
        "Museum",
    ],

    "gallery": [
        "Gallery",
        "Art Space",
    ],

    "karting": [
        "Karting",
        "Racing",
    ],

    "billiards": [
        "Billiards",
        "Pool Club",
    ],

    "arcade": [
        "Arcade",
        "Game Zone",
    ],

    "park_activity": [
        "Park",
        "Garden",
        "Outdoor",
    ],
}


used_names = set()


def generate_name(category):

    while True:

        adjective = random.choice(
            ADJECTIVES
        )

        noun = random.choice(
            NOUNS
        )

        suffix = random.choice(
            NAME_SUFFIXES[category]
        )

        pattern = random.choice([
            "{adjective} {noun} {suffix}",
            "{noun} {suffix}",
            "{adjective} {suffix}",
        ])

        name = pattern.format(
            adjective=adjective,
            noun=noun,
            suffix=suffix,
        )

        if name not in used_names:

            used_names.add(name)

            return name


# ============================================================
# DESCRIPTIONS
# ============================================================

CATEGORY_LABELS = {
    "restaurant": "Ресторан",
    "cafe": "Кафе",
    "bar": "Бар",
    "cinema": "Кинотеатр",
    "bowling": "Боулинг-клуб",
    "karaoke": "Караоке-клуб",
    "board_game_club": "Клуб настольных игр",
    "escape_room": "Квест-пространство",
    "museum": "Музей",
    "gallery": "Галерея",
    "karting": "Картинг-центр",
    "billiards": "Бильярдный клуб",
    "arcade": "Игровой центр",
    "park_activity": "Открытая площадка",
}


CONCEPT_TEXT = {
    "budget":
        "с доступными ценами",

    "standard":
        "для встреч с друзьями",

    "premium":
        "с повышенным уровнем комфорта",

    "cozy":
        "со спокойной и уютной атмосферой",

    "party":
        "для шумных компаний и вечернего отдыха",

    "family":
        "подходящее для спокойного отдыха и компаний",

    "competitive":
        "для любителей соревнований и активного отдыха",
}


def generate_description(
    category,
    concept
):

    return (
        f"{CATEGORY_LABELS[category]} "
        f"{CONCEPT_TEXT[concept]}."
    )


# ============================================================
# OPENING HOURS
# ============================================================

def generate_opening_hours(
    category
):

    if category == "bar":

        weekday = [
            "16:00",
            "01:00"
        ]

        weekend = [
            "14:00",
            "03:00"
        ]

    elif category == "karaoke":

        weekday = [
            "18:00",
            "02:00"
        ]

        weekend = [
            "16:00",
            "04:00"
        ]

    elif category in [
        "museum",
        "gallery",
    ]:

        weekday = [
            "10:00",
            "19:00"
        ]

        weekend = [
            "10:00",
            "20:00"
        ]

    elif category == "cafe":

        weekday = [
            "08:00",
            "22:00"
        ]

        weekend = [
            "09:00",
            "23:00"
        ]

    elif category == "restaurant":

        weekday = [
            "11:00",
            "23:00"
        ]

        weekend = [
            "11:00",
            "01:00"
        ]

    elif category == "park_activity":

        weekday = [
            "07:00",
            "22:00"
        ]

        weekend = [
            "07:00",
            "22:00"
        ]

    else:

        weekday = [
            "10:00",
            "23:00"
        ]

        weekend = [
            "10:00",
            "00:00"
        ]

    return {
        "mon": weekday,
        "tue": weekday,
        "wed": weekday,
        "thu": weekday,
        "fri": weekend,
        "sat": weekend,
        "sun": weekend,
    }


# ============================================================
# WEIGHTED RANDOM
# ============================================================

def weighted_choice(
    weights_dict
):

    values = list(
        weights_dict.keys()
    )

    weights = list(
        weights_dict.values()
    )

    return random.choices(
        values,
        weights=weights,
        k=1,
    )[0]


# ============================================================
# CATEGORY
# ============================================================

def choose_category():

    categories = list(
        CATEGORIES.keys()
    )

    weights = [
        CATEGORIES[category][
            "weight"
        ]
        for category in categories
    ]

    return random.choices(
        categories,
        weights=weights,
        k=1,
    )[0]


# ============================================================
# PRICE
# ============================================================

def round_price(value):

    if value <= 0:
        return 0

    return int(
        round(value / 50.0)
        * 50
    )


def generate_prices(
    category,
    district,
    concept
):

    config = CATEGORIES[
        category
    ]

    low, high = config[
        "price"
    ]

    # Бесплатные активности.

    if low == 0:

        if random.random() < 0.35:

            return 0, 0, 0

    base = random.uniform(
        low,
        high
    )

    district_factor = (
        DISTRICT_PRICE_FACTOR[
            district
        ]
    )

    concept_factor = (
        CONCEPTS[
            concept
        ]["price_factor"]
    )

    avg_price = (
        base
        * district_factor
        * concept_factor
        * random.uniform(
            0.90,
            1.10
        )
    )

    avg_price = round_price(
        avg_price
    )

    min_price = round_price(
        avg_price
        * random.uniform(
            0.65,
            0.85
        )
    )

    max_price = round_price(
        avg_price
        * random.uniform(
            1.20,
            1.55
        )
    )

    return (
        min_price,
        avg_price,
        max_price,
    )


# ============================================================
# LOAD CITY GRAPH
# ============================================================

def load_city_graph(
    cursor
):

    cursor.execute("""
        SELECT
            e.id,
            e.node_from,
            e.node_to,
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

        ORDER BY e.id;
    """)

    rows = cursor.fetchall()

    edges = []

    for row in rows:

        edges.append({
            "id": row[0],

            "node_from": row[1],
            "node_to": row[2],

            "road_type": row[3],

            "x1": row[4],
            "y1": row[5],
            "district1": row[6],

            "x2": row[7],
            "y2": row[8],
            "district2": row[9],
        })

    return edges


# ============================================================
# EDGE DISTRICT
# ============================================================

def get_edge_district(edge):

    # Большинство наших edges находится
    # внутри одного района.

    if (
        edge["district1"]
        ==
        edge["district2"]
    ):

        return edge[
            "district1"
        ]

    # Если edge соединяет два района,
    # выбираем один из них.

    return random.choice([
        edge["district1"],
        edge["district2"],
    ])


# ============================================================
# CHOOSE EDGE
# ============================================================

def choose_edge_for_place(
    category,
    edges
):

    config = CATEGORIES[
        category
    ]

    desired_district = (
        weighted_choice(
            config[
                "district_weights"
            ]
        )
    )

    desired_road = (
        weighted_choice(
            config[
                "road_weights"
            ]
        )
    )

    # ------------------------------------------
    # Попытка №1:
    # district + road_type
    # ------------------------------------------

    candidates = []

    for edge in edges:

        edge_districts = {
            edge["district1"],
            edge["district2"],
        }

        if (
            desired_district
            in edge_districts

            and

            edge["road_type"]
            ==
            desired_road
        ):

            candidates.append(
                edge
            )

    if candidates:

        edge = random.choice(
            candidates
        )

        return (
            edge,
            desired_district
        )

    # ------------------------------------------
    # Попытка №2:
    # только district
    # ------------------------------------------

    candidates = []

    for edge in edges:

        if (
            desired_district
            in {
                edge["district1"],
                edge["district2"],
            }
        ):

            # Не сажаем обычное заведение
            # на pedestrian road.

            if (
                category
                !=
                "park_activity"

                and

                edge["road_type"]
                ==
                "pedestrian"
            ):
                continue

            candidates.append(
                edge
            )

    if candidates:

        edge = random.choice(
            candidates
        )

        return (
            edge,
            desired_district
        )

    # ------------------------------------------
    # Последний fallback
    # ------------------------------------------

    allowed_edges = [
        edge
        for edge in edges

        if (
            category
            ==
            "park_activity"

            or

            edge["road_type"]
            !=
            "pedestrian"
        )
    ]

    edge = random.choice(
        allowed_edges
    )

    district = get_edge_district(
        edge
    )

    return (
        edge,
        district
    )


# ============================================================
# POSITION ON EDGE
# ============================================================

def generate_position_on_edge(
    edge,
    district
):

    # Не ставим заведение прямо
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
            - edge["x1"]
        )
        * position
    )

    y = (
        edge["y1"]
        +
        (
            edge["y2"]
            - edge["y1"]
        )
        * position
    )

    return (
        round(position, 5),
        round(x, 2),
        round(y, 2),
    )


# ============================================================
# RATING
# ============================================================

def generate_rating(
    concept
):

    rating = random.triangular(
        3.0,
        5.0,
        4.3
    )

    rating += (
        CONCEPTS[
            concept
        ]["rating_shift"]
    )

    rating = max(
        1.0,
        min(
            5.0,
            rating
        )
    )

    return round(
        rating,
        1
    )


# ============================================================
# TAGS
# ============================================================

def generate_tags(
    category,
    concept
):

    tags = list(
        CATEGORIES[
            category
        ]["tags"]
    )

    tags.append(
        concept
    )

    return list(
        dict.fromkeys(tags)
    )


# ============================================================
# PLACE GENERATOR
# ============================================================

def generate_place(
    edges
):

    category = (
        choose_category()
    )

    config = CATEGORIES[
        category
    ]

    concept = random.choice(
        config["concepts"]
    )

    # ------------------------------------------
    # Graph position
    # ------------------------------------------

    edge, district = (
        choose_edge_for_place(
            category,
            edges
        )
    )

    (
        edge_position,
        x,
        y,
    ) = generate_position_on_edge(
        edge,
        district
    )

    # ------------------------------------------
    # Prices
    # ------------------------------------------

    (
        price_min,
        price_avg,
        price_max,
    ) = generate_prices(
        category,
        district,
        concept
    )

    # ------------------------------------------
    # Group
    # ------------------------------------------

    min_group = (
        config[
            "group_size"
        ][0]
    )

    configured_max = (
        config[
            "group_size"
        ][1]
    )

    max_group = random.randint(
        max(
            min_group,
            configured_max // 2
        ),
        configured_max
    )

    # ------------------------------------------
    # Duration
    # ------------------------------------------

    duration_min = (
        config[
            "duration"
        ][0]
    )

    duration_max = (
        config[
            "duration"
        ][1]
    )

    duration = random.randrange(
        duration_min,
        duration_max + 1,
        15
    )

    # ------------------------------------------
    # Boolean properties
    # ------------------------------------------

    alcohol = (
        random.random()
        <
        config[
            "alcohol_probability"
        ]
    )

    booking = (
        random.random()
        <
        config[
            "booking_probability"
        ]
    )

    # ------------------------------------------
    # Result
    # ------------------------------------------

    return {

        "name":
            generate_name(
                category
            ),

        "category":
            category,

        "description":
            generate_description(
                category,
                concept
            ),

        "district":
            district,

        "edge_id":
            edge["id"],

        "edge_position":
            edge_position,

        "x":
            x,

        "y":
            y,

        "price_min":
            price_min,

        "price_avg":
            price_avg,

        "price_max":
            price_max,

        "currency":
            "RUB",

        "interests":
            list(
                config[
                    "interests"
                ]
            ),

        "tags":
            generate_tags(
                category,
                concept
            ),

        "opening_hours":
            generate_opening_hours(
                category
            ),

        "min_group_size":
            min_group,

        "max_group_size":
            max_group,

        "avg_duration_minutes":
            duration,

        "indoor":
            config[
                "indoor"
            ],

        "food_available":
            config[
                "food"
            ],

        "alcohol_available":
            alcohol,

        "noise_level":
            random.choice(
                config[
                    "noise"
                ]
            ),

        "rating":
            generate_rating(
                concept
            ),

        "reviews_count":
            int(
                random.triangular(
                    0,
                    2000,
                    150
                )
            ),

        "booking_required":
            booking,

        "active":
            True,
    }


# ============================================================
# INSERT
# ============================================================

INSERT_SQL = """
INSERT INTO places (
    name,
    category,
    description,
    district,

    edge_id,
    edge_position,

    x,
    y,

    price_min,
    price_avg,
    price_max,
    currency,

    interests,
    tags,

    opening_hours,

    min_group_size,
    max_group_size,

    avg_duration_minutes,

    indoor,
    food_available,
    alcohol_available,

    noise_level,

    rating,
    reviews_count,

    booking_required,
    active
)
VALUES (
    %s, %s, %s, %s,
    %s, %s,
    %s, %s,
    %s, %s, %s, %s,
    %s, %s,
    %s,
    %s, %s,
    %s,
    %s, %s, %s,
    %s,
    %s, %s,
    %s, %s
);
"""


def insert_place(
    cursor,
    place
):

    cursor.execute(
        INSERT_SQL,
        (
            place["name"],
            place["category"],
            place["description"],
            place["district"],

            place["edge_id"],
            place["edge_position"],

            place["x"],
            place["y"],

            place["price_min"],
            place["price_avg"],
            place["price_max"],
            place["currency"],

            place["interests"],
            place["tags"],

            json.dumps(
                place[
                    "opening_hours"
                ]
            ),

            place[
                "min_group_size"
            ],

            place[
                "max_group_size"
            ],

            place[
                "avg_duration_minutes"
            ],

            place["indoor"],

            place[
                "food_available"
            ],

            place[
                "alcohol_available"
            ],

            place[
                "noise_level"
            ],

            place["rating"],

            place[
                "reviews_count"
            ],

            place[
                "booking_required"
            ],

            place["active"],
        )
    )


# ============================================================
# STATISTICS
# ============================================================

def print_statistics(
    places
):

    print()
    print(
        "================================"
    )

    print(
        "       PLACES STATISTICS"
    )

    print(
        "================================"
    )

    print(
        f"Total: {len(places)}"
    )

    print()
    print("BY CATEGORY")

    category_counts = {}

    for place in places:

        category = place[
            "category"
        ]

        category_counts[
            category
        ] = (
            category_counts.get(
                category,
                0
            )
            + 1
        )

    for (
        category,
        count
    ) in sorted(
        category_counts.items(),
        key=lambda item:
            item[1],
        reverse=True
    ):

        print(
            f"{category:20}"
            f"{count:4}"
        )

    print()
    print("BY DISTRICT")

    district_counts = {}

    for place in places:

        district = place[
            "district"
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
            f"{district:20}"
            f"{count:4}"
        )

    print()
    print("BY ROAD TYPE")

    # Для статистики edge road type
    # добавим отдельно в main.


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Подключаемся к PostgreSQL..."
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
        # Load graph
        # --------------------------------------

        edges = load_city_graph(
            cursor
        )

        if not edges:

            raise RuntimeError(
                "city_edges пуст. "
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

        print(
            f"Генерируем "
            f"{PLACES_COUNT} заведений..."
        )

        places = [
            generate_place(
                edges
            )
            for _ in range(
                PLACES_COUNT
            )
        ]

        print_statistics(
            places
        )

        # --------------------------------------
        # Clear old places
        # --------------------------------------

        cursor.execute("""
            TRUNCATE TABLE places
            RESTART IDENTITY;
        """)

        # --------------------------------------
        # Insert
        # --------------------------------------

        for place in places:

            insert_place(
                cursor,
                place
            )

        connection.commit()

        print()
        print(
            f"Успешно сохранено "
            f"{PLACES_COUNT} places."
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