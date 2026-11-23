"""Render a Diagram to a standalone SVG string.

Clients can draw the Diagram spec natively (React Flow, react-native-svg);
this SVG is the fallback that works everywhere today.
"""
from __future__ import annotations

import math
from html import escape

from ..core import Diagram

R = 22
OBSERVED_FILL = "#c7d2de"
STROKE = "#24313f"
QUERY_STROKE = "#1f6feb"
DECISION_STROKE = "#d9822b"


def diagram_to_svg(diagram: Diagram) -> str:
    pos = {n["id"]: (n["x"], n["y"]) for n in diagram.nodes}
    any_observed = any(n.get("observed") for n in diagram.nodes)
    legend_h = 28 if any_observed else 0
    w, h = diagram.width, diagram.height + legend_h
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
        f'width="{w:.0f}" height="{h:.0f}" role="img" aria-label="Bayesian network">',
        "<defs><marker id='arrow' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' "
        f"markerHeight='7' orient='auto-start-reverse'><path d='M0,0 L10,5 L0,10 z' fill='{STROKE}'/>"
        "</marker></defs>",
        f"<rect width='{w:.0f}' height='{h:.0f}' fill='#ffffff'/>",
    ]
    for e in diagram.edges:
        parts.append(_edge(pos, e["from"], e["to"], e.get("curve", 0)))
    for n in diagram.nodes:
        x, y = n["x"], n["y"]
        fill = OBSERVED_FILL if n.get("observed") else "#ffffff"
        stroke, sw = (QUERY_STROKE, 3) if n.get("role") == "query" else (STROKE, 1.6)
        shape = n.get("shape", "chance")
        if shape == "decision":
            outline = (f"<rect x='{x - R * 1.25:.1f}' y='{y - R * 0.85:.1f}' width='{R * 2.5:.1f}' "
                       f"height='{R * 1.7:.1f}' fill='{fill}' stroke='{DECISION_STROKE}' stroke-width='2'/>")
        elif shape == "utility":
            k = R * 1.2
            outline = (f"<polygon points='{x:.1f},{y - k:.1f} {x + k:.1f},{y:.1f} {x:.1f},{y + k:.1f} {x - k:.1f},{y:.1f}' "
                       f"fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>")
        else:
            outline = f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{R}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>"
        parts.append(
            outline + f"<text x='{x:.1f}' y='{y + 6:.1f}' text-anchor='middle' font-size='17' "
            f"font-family='-apple-system, Segoe UI, Helvetica, Arial, sans-serif' fill='{STROKE}'>"
            f"{escape(n['id'])}</text>"
        )
    if any_observed:
        ly = diagram.height + 8
        parts.append(
            f"<circle cx='20' cy='{ly:.0f}' r='7' fill='{OBSERVED_FILL}' stroke='{STROKE}'/>"
            f"<text x='33' y='{ly + 5:.0f}' font-size='13' fill='#4b5866' "
            "font-family='-apple-system, Segoe UI, Helvetica, Arial, sans-serif'>observed</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def _edge(pos, a, b, curve: float) -> str:
    (x1, y1), (x2, y2) = pos[a], pos[b]
    if not curve:
        ang = math.atan2(y2 - y1, x2 - x1)
        sx, sy = x1 + R * math.cos(ang), y1 + R * math.sin(ang)
        ex, ey = x2 - (R + 2) * math.cos(ang), y2 - (R + 2) * math.sin(ang)
        return (
            f"<line x1='{sx:.1f}' y1='{sy:.1f}' x2='{ex:.1f}' y2='{ey:.1f}' "
            f"stroke='{STROKE}' stroke-width='1.6' marker-end='url(#arrow)'/>"
        )
    # Quadratic curve bowed sideways, for arrows that would cross another node.
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    length = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / length, (x2 - x1) / length
    cx, cy = mx + nx * curve, my + ny * curve
    a1 = math.atan2(cy - y1, cx - x1)
    a2 = math.atan2(y2 - cy, x2 - cx)
    sx, sy = x1 + R * math.cos(a1), y1 + R * math.sin(a1)
    ex, ey = x2 - (R + 2) * math.cos(a2), y2 - (R + 2) * math.sin(a2)
    return (
        f"<path d='M{sx:.1f},{sy:.1f} Q{cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}' fill='none' "
        f"stroke='{STROKE}' stroke-width='1.6' marker-end='url(#arrow)'/>"
    )
