"""Top-down layered layout for small DAGs (up to about 8 nodes), shared by all graph generators.

Each node sits one layer below its deepest parent, so every arrow points
down. Orderings within layers are tried exhaustively (cheap at this size) to
minimise crossings and arrows passing through other nodes.
"""
from __future__ import annotations

import math
from itertools import permutations, product
from typing import Dict, Iterable, List, Optional, Tuple

from ..core import Diagram
from .dag import DAG

X_GAP, Y_GAP, MARGIN, NODE_RADIUS = 110, 100, 48, 22
MAX_COMBINATIONS = 50_000

Point = Tuple[float, float]


def layered_layout(dag: DAG) -> Tuple[Dict[str, Point], float, float]:
    depth: Dict[str, int] = {}
    for n in dag.topological_order():
        depth[n] = max((depth[p] + 1 for p in dag.parents(n)), default=0)
    layers = [sorted(n for n in dag.nodes if depth[n] == d) for d in range(max(depth.values()) + 1)]
    width_slots = max(len(layer) for layer in layers)

    def place(ordering) -> Dict[str, Point]:
        pos = {}
        for d, layer in enumerate(ordering):
            offset = (width_slots - len(layer)) / 2
            for i, n in enumerate(layer):
                pos[n] = (MARGIN + (i + offset) * X_GAP, MARGIN + d * Y_GAP)
        return pos

    choices = [list(permutations(layer)) for layer in layers]
    total = math.prod(len(c) for c in choices)
    candidates = product(*choices) if total <= MAX_COMBINATIONS else [tuple(layers)]
    best = min(candidates, key=lambda ordering: _score(dag, place(ordering)))
    pos = place(best)
    width = 2 * MARGIN + (width_slots - 1) * X_GAP
    height = 2 * MARGIN + (len(layers) - 1) * Y_GAP
    return pos, width, height


def _score(dag: DAG, pos: Dict[str, Point]) -> float:
    edges = [(pos[a], pos[b], a, b) for a, b in dag.edges]
    crossings = 0
    for i in range(len(edges)):
        for j in range(i + 1, len(edges)):
            p1, p2, a1, b1 = edges[i]
            q1, q2, a2, b2 = edges[j]
            if {a1, b1} & {a2, b2}:
                continue
            if _segments_cross(p1, p2, q1, q2):
                crossings += 1
    through_nodes = sum(
        1
        for p, q, a, b in edges
        for n, c in pos.items()
        if n not in (a, b) and _point_segment_distance(c, p, q) < NODE_RADIUS + 6
    )
    length = sum(math.dist(p, q) for p, q, _, _ in edges)
    return crossings * 100 + through_nodes * 60 + length * 0.01


def _segments_cross(p1, p2, q1, q2) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2 = orient(q1, q2, p1), orient(q1, q2, p2)
    d3, d4 = orient(p1, p2, q1), orient(p1, p2, q2)
    return d1 * d2 < 0 and d3 * d4 < 0


def _point_segment_distance(c, p, q) -> float:
    (px, py), (qx, qy), (cx, cy) = p, q, c
    dx, dy = qx - px, qy - py
    if dx == dy == 0:
        return math.dist(c, p)
    t = max(0.0, min(1.0, ((cx - px) * dx + (cy - py) * dy) / (dx * dx + dy * dy)))
    return math.dist(c, (px + t * dx, py + t * dy))


def passes_through_node(pos: Dict[str, Point], a: str, b: str) -> bool:
    return any(
        n not in (a, b) and _point_segment_distance(c, pos[a], pos[b]) < NODE_RADIUS + 6
        for n, c in pos.items()
    )


def edge_curve(pos: Dict[str, Point], a: str, b: str) -> float:
    """0 for a straight arrow; otherwise the sideways bow that keeps clearest of other nodes.

    The sign follows the SVG renderer's convention: control point = midpoint + normal * curve.
    """
    if not passes_through_node(pos, a, b):
        return 0
    (x1, y1), (x2, y2) = pos[a], pos[b]
    length = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / length, (x2 - x1) / length
    others = [c for n, c in pos.items() if n not in (a, b)]

    def clearance(curve: float) -> float:
        cx, cy = (x1 + x2) / 2 + nx * curve, (y1 + y2) / 2 + ny * curve
        best = float("inf")
        for i in range(1, 20):
            t = i / 20
            px = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t * t * x2
            py = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t * t * y2
            best = min([best] + [math.dist((px, py), o) for o in others])
        return best

    candidates = [s * m for m in (40, 60, 85) for s in (1, -1)]
    # Prefer the smallest bow that clears nodes comfortably; else the clearest one.
    for curve in candidates:
        if clearance(curve) >= NODE_RADIUS + 14:
            return curve
    return max(candidates, key=clearance)


def draw(
    dag: DAG, observed: Iterable[str] = (), query: Optional[str] = None, shapes: Optional[Dict[str, str]] = None
) -> Diagram:
    """Lay out a DAG as a Diagram: shaded observed nodes, outlined query node.

    `shapes` marks special nodes: "decision" (rectangle) or "utility" (diamond).
    """
    pos, width, height = layered_layout(dag)
    observed = set(observed)
    nodes = [
        {"id": n, "x": round(pos[n][0], 1), "y": round(pos[n][1], 1),
         "observed": n in observed, "role": "query" if n == query else None,
         "shape": (shapes or {}).get(n, "chance")}
        for n in dag.nodes
    ]
    edges = [{"from": a, "to": b, "curve": edge_curve(pos, a, b)} for a, b in dag.edges]
    return Diagram(nodes, edges, width, height)
