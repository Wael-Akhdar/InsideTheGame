"""Shot quality from geometry only, for feeds that do not provide expected goals (e.g. Wyscout).

Logistic model fitted on 43,000 real shots of the public Wyscout dataset (Pappalardo et al., 2019, CC BY 4.0) with
tools/fit_xg.py. Features: distance to the goal, angle of the goal seen from the shot, header, free-kick shot.
On a league that was held out of the fit it predicts 876 goals for 912 real ones. Penalties use their observed conversion (72.6%).
It is a geometry-only model (no defenders, no assist type), so individual values are rough; totals and ranking are reliable.
"""
from __future__ import annotations

import math

# [intercept, distance/10 m, goal angle (rad), header, free-kick shot]
COEF = (-1.0659, -1.0705, 1.5772, -0.9948, 0.8727)
PENALTY_XG = 0.73


def estimate_xg(x: float, y: float, penalty: bool = False, header: bool = False, freekick: bool = False) -> float:
    """x, y on the 0-100 pitch in the shooting team's frame (goal at x=100, y=50)."""
    if penalty:
        return PENALTY_XG
    dx, dy = (100 - x) * 1.05, abs(50 - y) * 0.68
    dist = max(3.0, math.hypot(dx, dy))
    ang = math.atan2(7.32 * dx, dx * dx + dy * dy - 3.66 ** 2 + 1e-9)
    ang = ang if ang > 0 else ang + math.pi
    z = COEF[0] + COEF[1] * dist / 10 + COEF[2] * ang + COEF[3] * header + COEF[4] * freekick
    return round(1 / (1 + math.exp(-z)), 3)
