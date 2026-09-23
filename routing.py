"""
Расчёт времени в пути по графу города (README, раздел 7).

Граф: city_nodes + city_edges. Человек и место лежат НА ребре в позиции
0..1 (edge_position), поэтому время считается так:

    до конца ребра A  +  кратчайший путь между концами  +  от конца ребра B

плюс особый случай «обе точки на одном ребре» (прямой путь по ребру).
На каждого участника делается ОДИН Dijkstra, после чего время до любого
из сотен мест считается за O(1).

Режимы: "walk" (пешком) и "car" (машина). Ребро с walk_allowed=False /
car_allowed=False в этом режиме не проходимо.
"""

import heapq
import math

MODES = ("walk", "car")


class CityGraph:
    def __init__(self, nodes, edges):
        """
        nodes: список dict {id, x, y, district}
        edges: список dict {id, node_from, node_to, length_m,
               car_speed_kmh, walk_speed_kmh, car_allowed, walk_allowed}
        """
        self.nodes = {n["id"]: n for n in nodes}
        self.edges = {e["id"]: e for e in edges}

        # полное время прохождения ребра, минуты (None — нельзя)
        self._edge_minutes = {}
        self._adj = {mode: {} for mode in MODES}

        for e in edges:
            for mode in MODES:
                minutes = self._full_edge_minutes(e, mode)
                self._edge_minutes[(e["id"], mode)] = minutes

                if minutes is None:
                    continue

                adj = self._adj[mode]
                adj.setdefault(e["node_from"], []).append((e["node_to"], minutes))
                adj.setdefault(e["node_to"], []).append((e["node_from"], minutes))

        self._home_cache = {}

    @staticmethod
    def _full_edge_minutes(edge, mode):
        if mode == "walk":
            allowed, speed = edge["walk_allowed"], edge["walk_speed_kmh"]
        else:
            allowed, speed = edge["car_allowed"], edge["car_speed_kmh"]

        if not allowed or not speed:
            return None

        return edge["length_m"] / (speed * 1000 / 60)

    # ------------------------------------------------------------ точки

    def distances_from(self, edge_id, position, mode):
        """
        Dijkstra от точки на ребре. Возвращает PointDistances или None,
        если из этой точки в данном режиме вообще не выйти.
        """
        full = self._edge_minutes.get((edge_id, mode))

        if full is None:
            return None

        edge = self.edges[edge_id]
        dist = {
            edge["node_from"]: position * full,
            edge["node_to"]: (1 - position) * full,
        }

        heap = [(d, n) for n, d in dist.items()]
        heapq.heapify(heap)
        adj = self._adj[mode]

        while heap:
            d, node = heapq.heappop(heap)

            if d > dist.get(node, math.inf):
                continue

            for neighbor, minutes in adj.get(node, ()):
                nd = d + minutes
                if nd < dist.get(neighbor, math.inf):
                    dist[neighbor] = nd
                    heapq.heappush(heap, (nd, neighbor))

        return PointDistances(self, mode, edge_id, position, dist)

    # ------------------------------------------------------- дом по району

    def district_home_point(self, district):
        """
        Представительная точка района: середина ребра (проходимого и
        пешком, и на машине), ближайшего к центру района.
        Возвращает (edge_id, position) или None.
        """
        if district in self._home_cache:
            return self._home_cache[district]

        pts = [n for n in self.nodes.values() if n["district"] == district]

        if not pts:
            self._home_cache[district] = None
            return None

        cx = sum(n["x"] for n in pts) / len(pts)
        cy = sum(n["y"] for n in pts) / len(pts)

        best, best_d = None, math.inf

        for e in self.edges.values():
            if not (e["walk_allowed"] and e["car_allowed"]):
                continue

            a, b = self.nodes[e["node_from"]], self.nodes[e["node_to"]]
            mx, my = (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2
            d = (mx - cx) ** 2 + (my - cy) ** 2

            if d < best_d:
                best, best_d = e["id"], d

        result = (best, 0.5) if best is not None else None
        self._home_cache[district] = result
        return result

    def districts(self):
        return sorted({n["district"] for n in self.nodes.values()})


class PointDistances:
    """Времена от одной точки до всех узлов; время до любой точки на ребре."""

    def __init__(self, graph, mode, edge_id, position, node_dist):
        self.graph = graph
        self.mode = mode
        self.edge_id = edge_id
        self.position = position
        self.node_dist = node_dist

    def minutes_to(self, edge_id, position):
        """Минуты до точки на ребре или None, если не добраться."""
        g = self.graph
        full = g._edge_minutes.get((edge_id, self.mode))

        if full is None:
            return None  # само ребро места недоступно в этом режиме

        edge = g.edges[edge_id]
        best = math.inf

        d_from = self.node_dist.get(edge["node_from"])
        d_to = self.node_dist.get(edge["node_to"])

        if d_from is not None:
            best = min(best, d_from + position * full)
        if d_to is not None:
            best = min(best, d_to + (1 - position) * full)

        # обе точки на одном ребре — идём напрямую вдоль него
        if edge_id == self.edge_id:
            best = min(best, abs(position - self.position) * full)

        return None if best == math.inf else best
