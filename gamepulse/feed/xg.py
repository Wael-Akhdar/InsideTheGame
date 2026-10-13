"""Shot quality from geometry only (for feeds that do not provide expected goals, e.g. Wyscout)."""
from __future__ import annotations

import math


def estimate_xg(x: float, y: float, penalty: bool = False, header: bool = False) -> float:
    """x, y on the 0-100 pitch in the shooting team's frame (goal at x=100, y=50)."""
    if penalty:
        return 0.76
    dist = max(4.0, math.hypot((100 - x) * 1.05, (50 - y) * 0.68))
    lateral = abs(y - 50) * 0.68
    angle = math.atan2(7.32 * (100 - x) * 1.05, ((100 - x) * 1.05) ** 2 + lateral ** 2 - 3.66 ** 2 + 1e-9)
    angle = angle if angle > 0 else angle + math.pi
    xg = 0.9 * math.exp(-dist / 9.5) * (0.35 + 0.65 * min(1.0, angle / 0.55))
    return round(max(0.01, min(0.8, xg * (0.7 if header else 1.0))), 3)
