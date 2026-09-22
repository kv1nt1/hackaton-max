import math
import psycopg2


# ============================================================
# CONFIG
# ============================================================

DB_CONFIG = {
    "dbname": "DataBase",
    "user": "postgres",
    "password": "12345",
    "host": "localhost",
    "port": 12345,
}

CITY_WIDTH = 20_000
CITY_HEIGHT = 20_000


# ============================================================
# RIVER
# ============================================================
#
# Река проходит горизонтально через город.
#
# 20 km  ┌──────────────────────────────────────┐
#        │                NORTH                 │
#        │                                      │
#        │ UNIVERSITY   DOWNTOWN      MALL      │
# 10.4km │======================================│
#  9.6km │=============== RIVER ================│
#        │                                      │
#        │          SOUTH          PARK         │
# 0 km   └──────────────────────────────────────┘
#
# Обычные вертикальные улицы реку НЕ пересекают.
# Через неё проходят только специально заданные мосты.
# ============================================================

RIVER_Y_MIN = 9_600
RIVER_Y_MAX = 10_400


# X-координаты мостов
BRIDGE_X = [
    3_500,
    8_000,
    12_000,
    16_500,
]


# ============================================================
# DISTRICTS
# ============================================================

DISTRICTS = {

    "university": {
        "x_min": 1_000,
        "x_max": 7_000,
        "y_min": 11_000,
        "y_max": 17_000,
    },

    "downtown": {
        "x_min": 7_000,
        "x_max": 13_000,
        "y_min": 11_000,
        "y_max": 17_000,
    },

    "mall": {
        "x_min": 13_000,
        "x_max": 19_000,
        "y_min": 11_000,
        "y_max": 17_000,
    },

    "south": {
        "x_min": 5_000,
        "x_max": 13_000,
        "y_min": 1_500,
        "y_max": 9_000,
    },

    "park": {
        "x_min": 13_000,
        "x_max": 19_000,
        "y_min": 1_500,
        "y_max": 9_000,
    },

    "north": {
        "x_min": 7_000,
        "x_max": 13_000,
        "y_min": 17_000,
        "y_max": 19_500,
    },
}


# ============================================================
# ROAD TYPES
# ============================================================

ROAD_PRIORITY = {
    "pedestrian": 0,
    "local": 1,
    "street": 2,
    "avenue": 3,
}


ROAD_CONFIG = {

    "pedestrian": {
        "car_speed": None,
        "walk_speed": 5,
        "car_allowed": False,
        "walk_allowed": True,
    },

    "local": {
        "car_speed": 25,
        "walk_speed": 5,
        "car_allowed": True,
        "walk_allowed": True,
    },

    "street": {
        "car_speed": 40,
        "walk_speed": 5,
        "car_allowed": True,
        "walk_allowed": True,
    },

    "avenue": {
        "car_speed": 60,
        "walk_speed": 5,
        "car_allowed": True,
        "walk_allowed": True,
    },
}


# ============================================================
# ROADS
# ============================================================
#
# Дорога пока представляет собой прямой горизонтальный
# или вертикальный сегмент.
#
# {
#     "orientation": "horizontal",
#     "coordinate": 12000,
#     "start": 1000,
#     "end": 19000,
#     "road_type": "street"
# }
#
# ============================================================

roads = []


def add_horizontal(
    y,
    x_start,
    x_end,
    road_type
):
    roads.append({
        "orientation": "horizontal",
        "coordinate": y,
        "start": x_start,
        "end": x_end,
        "road_type": road_type,
    })


def add_vertical(
    x,
    y_start,
    y_end,
    road_type
):
    roads.append({
        "orientation": "vertical",
        "coordinate": x,
        "start": y_start,
        "end": y_end,
        "road_type": road_type,
    })


# ============================================================
# AVENUES
# ============================================================

def generate_avenues():

    # ------------------------------------------
    # Горизонтальные магистрали
    # ------------------------------------------

    avenue_y = [
        3_500,
        7_000,
        12_000,
        15_000,
        18_000,
    ]

    for y in avenue_y:

        add_horizontal(
            y=y,
            x_start=500,
            x_end=19_500,
            road_type="avenue"
        )

    # ------------------------------------------
    # Мосты
    # ------------------------------------------
    #
    # Эти avenue проходят через весь город,
    # поэтому именно они позволяют пересечь реку.
    # ------------------------------------------

    for x in BRIDGE_X:

        add_vertical(
            x=x,
            y_start=500,
            y_end=19_500,
            road_type="avenue"
        )


# ============================================================
# STREETS
# ============================================================

def generate_streets():

    # ------------------------------------------
    # Горизонтальные улицы
    # ------------------------------------------

    street_y = [
        2_000,
        5_000,
        8_500,

        11_000,
        13_500,
        16_500,
        19_000,
    ]

    for y in street_y:

        add_horizontal(
            y=y,
            x_start=1_000,
            x_end=19_000,
            road_type="street"
        )

    # ------------------------------------------
    # Вертикальные улицы
    # ------------------------------------------
    #
    # Они доходят до реки, но не пересекают её.
    # ------------------------------------------

    street_x = [
        2_000,
        5_500,
        10_000,
        14_500,
        18_000,
    ]

    for x in street_x:

        # Южная часть
        add_vertical(
            x=x,
            y_start=1_000,
            y_end=RIVER_Y_MIN,
            road_type="street"
        )

        # Северная часть
        add_vertical(
            x=x,
            y_start=RIVER_Y_MAX,
            y_end=19_000,
            road_type="street"
        )


# ============================================================
# LOCAL ROADS
# ============================================================

def generate_local_roads():

    # ------------------------------------------
    # Вертикальные local roads
    # ------------------------------------------

    local_x = [
        1_500,
        2_750,
        4_250,
        6_250,
        7_250,
        8_750,
        9_250,
        10_750,
        11_250,
        12_750,
        13_750,
        15_250,
        16_000,
        17_250,
        18_500,
    ]

    for x in local_x:

        # South
        add_vertical(
            x=x,
            y_start=1_500,
            y_end=RIVER_Y_MIN,
            road_type="local"
        )

        # North
        add_vertical(
            x=x,
            y_start=RIVER_Y_MAX,
            y_end=18_500,
            road_type="local"
        )

    # ------------------------------------------
    # Горизонтальные local roads
    # ------------------------------------------

    local_y = [
        2_750,
        4_250,
        5_750,
        7_750,

        11_500,
        12_750,
        14_250,
        15_750,
        17_250,
        18_500,
    ]

    for y in local_y:

        add_horizontal(
            y=y,
            x_start=1_500,
            x_end=18_500,
            road_type="local"
        )


# ============================================================
# PEDESTRIAN NETWORK
# ============================================================

def generate_pedestrian_roads():

    # Пешеходная сеть находится преимущественно
    # в районе park.

    pedestrian_y = [
        3_000,
        4_000,
        5_000,
        6_000,
        7_000,
        8_000,
    ]

    for y in pedestrian_y:

        add_horizontal(
            y=y,
            x_start=13_000,
            x_end=19_000,
            road_type="pedestrian"
        )

    pedestrian_x = [
        14_000,
        15_500,
        17_000,
        18_500,
    ]

    for x in pedestrian_x:

        add_vertical(
            x=x,
            y_start=2_000,
            y_end=9_000,
            road_type="pedestrian"
        )


# ============================================================
# INTERSECTION GEOMETRY
# ============================================================

def roads_intersect(road_a, road_b):

    # Две параллельные дороги в этой версии
    # intersection не образуют.

    if (
        road_a["orientation"]
        ==
        road_b["orientation"]
    ):
        return None

    if road_a["orientation"] == "horizontal":
        horizontal = road_a
        vertical = road_b
    else:
        horizontal = road_b
        vertical = road_a

    x = vertical["coordinate"]
    y = horizontal["coordinate"]

    # Проверяем попадание X в горизонтальный segment.

    if not (
        horizontal["start"]
        <= x
        <= horizontal["end"]
    ):
        return None

    # Проверяем попадание Y в вертикальный segment.

    if not (
        vertical["start"]
        <= y
        <= vertical["end"]
    ):
        return None

    return (
        round(x, 2),
        round(y, 2)
    )


# ============================================================
# DISTRICT LOOKUP
# ============================================================

def get_district(x, y):

    # Сначала ищем точное попадание
    # в bounding box района.

    for name, district in DISTRICTS.items():

        if (
            district["x_min"]
            <= x
            <= district["x_max"]

            and

            district["y_min"]
            <= y
            <= district["y_max"]
        ):
            return name

    # ------------------------------------------
    # Если точка лежит между районами,
    # назначаем ближайший район.
    # ------------------------------------------

    best_name = None
    best_distance = float("inf")

    for name, district in DISTRICTS.items():

        center_x = (
            district["x_min"]
            +
            district["x_max"]
        ) / 2

        center_y = (
            district["y_min"]
            +
            district["y_max"]
        ) / 2

        d = math.hypot(
            x - center_x,
            y - center_y
        )

        if d < best_distance:

            best_distance = d
            best_name = name

    return best_name


# ============================================================
# GENERATE NODES
# ============================================================

def generate_nodes():

    intersections = {}

    # ------------------------------------------
    # Находим все intersections
    # ------------------------------------------

    for i in range(len(roads)):

        for j in range(
            i + 1,
            len(roads)
        ):

            intersection = roads_intersect(
                roads[i],
                roads[j]
            )

            if intersection is None:
                continue

            x, y = intersection

            key = (x, y)

            if key not in intersections:

                intersections[key] = {
                    "road_types": set()
                }

            intersections[key][
                "road_types"
            ].add(
                roads[i]["road_type"]
            )

            intersections[key][
                "road_types"
            ].add(
                roads[j]["road_type"]
            )

    # ------------------------------------------
    # Создаём nodes
    # ------------------------------------------

    nodes = []

    sorted_intersections = sorted(
        intersections.items(),
        key=lambda item: (
            item[0][1],
            item[0][0]
        )
    )

    for node_id, (
        coordinate,
        data
    ) in enumerate(
        sorted_intersections,
        start=1
    ):

        x, y = coordinate

        # Если здесь пересекаются разные
        # road types, node получает наиболее
        # высокий тип.

        node_type = max(
            data["road_types"],
            key=lambda road_type:
                ROAD_PRIORITY[road_type]
        )

        nodes.append({
            "id": node_id,

            "x": x,
            "y": y,

            "district":
                get_district(x, y),

            "node_type":
                node_type,
        })

    return nodes


# ============================================================
# CHECK IF NODE IS ON ROAD
# ============================================================

def point_on_road(
    node,
    road
):

    x = node["x"]
    y = node["y"]

    tolerance = 0.001

    if road["orientation"] == "horizontal":

        return (
            abs(
                y - road["coordinate"]
            ) < tolerance

            and

            road["start"]
            <= x
            <= road["end"]
        )

    return (
        abs(
            x - road["coordinate"]
        ) < tolerance

        and

        road["start"]
        <= y
        <= road["end"]
    )


# ============================================================
# GENERATE EDGES
# ============================================================

def generate_edges(nodes):

    # key:
    # (min_node_id, max_node_id)
    #
    # value:
    # edge data

    edge_map = {}

    for road in roads:

        # --------------------------------------
        # Все intersections на этой дороге
        # --------------------------------------

        road_nodes = [
            node
            for node in nodes
            if point_on_road(
                node,
                road
            )
        ]

        # --------------------------------------
        # Сортировка вдоль дороги
        # --------------------------------------

        if (
            road["orientation"]
            ==
            "horizontal"
        ):

            road_nodes.sort(
                key=lambda node:
                    node["x"]
            )

        else:

            road_nodes.sort(
                key=lambda node:
                    node["y"]
            )

        # --------------------------------------
        # Edge только между соседними nodes
        # --------------------------------------

        for i in range(
            len(road_nodes) - 1
        ):

            node_a = road_nodes[i]
            node_b = road_nodes[i + 1]

            if (
                node_a["id"]
                ==
                node_b["id"]
            ):
                continue

            node_from = min(
                node_a["id"],
                node_b["id"]
            )

            node_to = max(
                node_a["id"],
                node_b["id"]
            )

            edge_key = (
                node_from,
                node_to
            )

            length_m = math.hypot(
                node_a["x"]
                - node_b["x"],

                node_a["y"]
                - node_b["y"]
            )

            if length_m < 1:
                continue

            road_type = road[
                "road_type"
            ]

            config = ROAD_CONFIG[
                road_type
            ]

            new_edge = {
                "node_from":
                    node_from,

                "node_to":
                    node_to,

                "length_m":
                    round(length_m, 2),

                "road_type":
                    road_type,

                "car_speed_kmh":
                    config["car_speed"],

                "walk_speed_kmh":
                    config["walk_speed"],

                "car_allowed":
                    config["car_allowed"],

                "walk_allowed":
                    config["walk_allowed"],
            }

            # ----------------------------------
            # Одно геометрическое ребро может
            # принадлежать двум road definitions.
            #
            # Оставляем более высокий road type.
            # ----------------------------------

            if edge_key in edge_map:

                existing = edge_map[
                    edge_key
                ]

                if (
                    ROAD_PRIORITY[
                        road_type
                    ]
                    >
                    ROAD_PRIORITY[
                        existing["road_type"]
                    ]
                ):
                    edge_map[
                        edge_key
                    ] = new_edge

            else:

                edge_map[
                    edge_key
                ] = new_edge

    return list(
        edge_map.values()
    )


# ============================================================
# GRAPH REACHABILITY
# ============================================================

def reachable_nodes(
    nodes,
    edges,
    mode=None
):

    adjacency = {
        node["id"]: []
        for node in nodes
    }

    for edge in edges:

        if mode == "car":

            if not edge[
                "car_allowed"
            ]:
                continue

        elif mode == "walk":

            if not edge[
                "walk_allowed"
            ]:
                continue

        node_a = edge[
            "node_from"
        ]

        node_b = edge[
            "node_to"
        ]

        adjacency[
            node_a
        ].append(
            node_b
        )

        adjacency[
            node_b
        ].append(
            node_a
        )

    # ------------------------------------------
    # Для car нельзя просто брать nodes[0].
    # Он теоретически может оказаться
    # pedestrian-only.
    # ------------------------------------------

    start = None

    for node in nodes:

        if adjacency[node["id"]]:

            start = node["id"]
            break

    if start is None:
        return set()

    visited = set()

    stack = [start]

    while stack:

        current = stack.pop()

        if current in visited:
            continue

        visited.add(current)

        for neighbor in adjacency[
            current
        ]:

            if neighbor not in visited:

                stack.append(
                    neighbor
                )

    return visited


# ============================================================
# FIND ISOLATED NODES
# ============================================================

def get_unreachable_nodes(
    nodes,
    reachable
):

    return [
        node
        for node in nodes
        if node["id"] not in reachable
    ]


# ============================================================
# STATISTICS
# ============================================================

def print_statistics(
    nodes,
    edges
):

    print()
    print(
        "===================================="
    )

    print(
        "       SYNTHETIC CITY V2"
    )

    print(
        "===================================="
    )

    print(
        f"City size: "
        f"{CITY_WIDTH / 1000:.0f} x "
        f"{CITY_HEIGHT / 1000:.0f} km"
    )

    print(
        f"Road definitions: {len(roads)}"
    )

    print(
        f"Nodes: {len(nodes)}"
    )

    print(
        f"Edges: {len(edges)}"
    )

    print()

    # ------------------------------------------
    # Road statistics
    # ------------------------------------------

    print("EDGES BY TYPE")

    for road_type in ROAD_CONFIG:

        type_edges = [
            edge
            for edge in edges
            if (
                edge["road_type"]
                ==
                road_type
            )
        ]

        count = len(
            type_edges
        )

        total_length = sum(
            edge["length_m"]
            for edge in type_edges
        )

        print(
            f"{road_type:12}"
            f"{count:5} edges | "
            f"{total_length / 1000:7.1f} km"
        )

    print()

    # ------------------------------------------
    # District statistics
    # ------------------------------------------

    print("NODES BY DISTRICT")

    for district in DISTRICTS:

        count = sum(
            1
            for node in nodes
            if (
                node["district"]
                ==
                district
            )
        )

        print(
            f"{district:12}"
            f"{count:5}"
        )

    print()

    # ------------------------------------------
    # Connectivity
    # ------------------------------------------

    general_reachable = (
        reachable_nodes(
            nodes,
            edges
        )
    )

    walking_reachable = (
        reachable_nodes(
            nodes,
            edges,
            mode="walk"
        )
    )

    car_reachable = (
        reachable_nodes(
            nodes,
            edges,
            mode="car"
        )
    )

    print("CONNECTIVITY")

    print(
        "General:",
        f"{len(general_reachable)}"
        f"/{len(nodes)}"
    )

    print(
        "Walking:",
        f"{len(walking_reachable)}"
        f"/{len(nodes)}"
    )

    print(
        "Car:",
        f"{len(car_reachable)}"
        f"/{len(nodes)}"
    )

    # ------------------------------------------
    # Walking unreachable
    # ------------------------------------------

    walking_unreachable = (
        get_unreachable_nodes(
            nodes,
            walking_reachable
        )
    )

    if walking_unreachable:

        print()
        print(
            "WARNING: "
            "walking unreachable nodes:"
        )

        for node in walking_unreachable:

            print(
                f"  id={node['id']} "
                f"x={node['x']} "
                f"y={node['y']} "
                f"type={node['node_type']} "
                f"district={node['district']}"
            )

    # ------------------------------------------
    # Car unreachable
    # ------------------------------------------

    car_unreachable = (
        get_unreachable_nodes(
            nodes,
            car_reachable
        )
    )

    if car_unreachable:

        print()

        print(
            "Car unreachable nodes "
            "(может быть нормально для park):"
        )

        for node in car_unreachable[:20]:

            print(
                f"  id={node['id']} "
                f"x={node['x']} "
                f"y={node['y']} "
                f"type={node['node_type']} "
                f"district={node['district']}"
            )

        if len(
            car_unreachable
        ) > 20:

            print(
                f"  ... и ещё "
                f"{len(car_unreachable) - 20}"
            )


# ============================================================
# VALIDATION
# ============================================================

def validate_graph(
    nodes,
    edges
):

    if not nodes:

        raise RuntimeError(
            "Граф не содержит nodes."
        )

    if not edges:

        raise RuntimeError(
            "Граф не содержит edges."
        )

    # ------------------------------------------
    # Общий граф
    # ------------------------------------------

    general = reachable_nodes(
        nodes,
        edges
    )

    if len(general) != len(nodes):

        unreachable = (
            len(nodes)
            - len(general)
        )

        raise RuntimeError(
            "Общий граф несвязный. "
            f"Недоступных nodes: "
            f"{unreachable}"
        )

    # ------------------------------------------
    # Walking
    # ------------------------------------------
    #
    # В нашей модели весь город должен быть
    # доступен пешком.
    # ------------------------------------------

    walking = reachable_nodes(
        nodes,
        edges,
        mode="walk"
    )

    if len(walking) != len(nodes):

        unreachable_nodes = (
            get_unreachable_nodes(
                nodes,
                walking
            )
        )

        print()
        print(
            "Walking graph НЕ полностью "
            "связный."
        )

        for node in unreachable_nodes:

            print(node)

        raise RuntimeError(
            "Walking graph должен быть "
            "полностью связным."
        )

    # ------------------------------------------
    # Edge validation
    # ------------------------------------------

    valid_node_ids = {
        node["id"]
        for node in nodes
    }

    for edge in edges:

        if (
            edge["node_from"]
            not in valid_node_ids
        ):
            raise RuntimeError(
                "Edge содержит "
                "несуществующий node_from."
            )

        if (
            edge["node_to"]
            not in valid_node_ids
        ):
            raise RuntimeError(
                "Edge содержит "
                "несуществующий node_to."
            )

        if edge["length_m"] <= 0:

            raise RuntimeError(
                "Обнаружено edge "
                "с length <= 0."
            )


# ============================================================
# DATABASE
# ============================================================

def save_to_database(
    nodes,
    edges
):

    connection = None
    cursor = None

    try:

        print()
        print(
            "Подключаемся к PostgreSQL..."
        )

        connection = psycopg2.connect(
            **DB_CONFIG
        )

        cursor = connection.cursor()

        # --------------------------------------
        # Старые places привязаны к старым edges,
        # поэтому удаляем весь synthetic city.
        # --------------------------------------

        cursor.execute("""
            TRUNCATE TABLE
                places,
                city_edges,
                city_nodes
            RESTART IDENTITY CASCADE;
        """)

        # ======================================
        # NODES
        # ======================================

        node_sql = """
        INSERT INTO city_nodes (
            id,
            x,
            y,
            district,
            node_type
        )
        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s
        );
        """

        for node in nodes:

            cursor.execute(
                node_sql,
                (
                    node["id"],
                    node["x"],
                    node["y"],
                    node["district"],
                    node["node_type"],
                )
            )

        # ======================================
        # EDGES
        # ======================================

        edge_sql = """
        INSERT INTO city_edges (
            node_from,
            node_to,
            length_m,
            road_type,
            car_speed_kmh,
            walk_speed_kmh,
            car_allowed,
            walk_allowed
        )
        VALUES (
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

        for edge in edges:

            cursor.execute(
                edge_sql,
                (
                    edge["node_from"],
                    edge["node_to"],
                    edge["length_m"],
                    edge["road_type"],
                    edge["car_speed_kmh"],
                    edge["walk_speed_kmh"],
                    edge["car_allowed"],
                    edge["walk_allowed"],
                )
            )

        # --------------------------------------
        # Мы вручную задавали city_nodes.id,
        # поэтому синхронизируем sequence.
        # --------------------------------------

        cursor.execute("""
            SELECT setval(
                pg_get_serial_sequence(
                    'city_nodes',
                    'id'
                ),
                (
                    SELECT MAX(id)
                    FROM city_nodes
                )
            );
        """)

        connection.commit()

        print(
            "Город успешно сохранён "
            "в PostgreSQL."
        )

    except Exception as error:

        if connection:

            connection.rollback()

        print()
        print(
            "Ошибка PostgreSQL:"
        )

        print(error)

        raise

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Генерируем Synthetic City V2..."
    )

    # Важно при повторном вызове main()
    roads.clear()

    # ------------------------------------------
    # 1. Геометрия дорог
    # ------------------------------------------

    generate_avenues()

    generate_streets()

    generate_local_roads()

    generate_pedestrian_roads()

    print(
        f"Создано road definitions: "
        f"{len(roads)}"
    )

    # ------------------------------------------
    # 2. Перекрёстки -> nodes
    # ------------------------------------------

    nodes = generate_nodes()

    print(
        f"Создано nodes: "
        f"{len(nodes)}"
    )

    # ------------------------------------------
    # 3. Участки дорог -> edges
    # ------------------------------------------

    edges = generate_edges(
        nodes
    )

    print(
        f"Создано edges: "
        f"{len(edges)}"
    )

    # ------------------------------------------
    # 4. Проверка графа
    # ------------------------------------------

    print_statistics(
        nodes,
        edges
    )

    print()
    print(
        "Проверяем граф..."
    )

    validate_graph(
        nodes,
        edges
    )

    print(
        "Граф корректен."
    )

    # ------------------------------------------
    # 5. PostgreSQL
    # ------------------------------------------

    save_to_database(
        nodes,
        edges
    )

    print()
    print(
        "Готово."
    )


if __name__ == "__main__":
    main()