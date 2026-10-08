"""Coach-facing tactics: formation, per-player roles and team instructions.

Coordinates are in the *team frame*: x runs from own goal (0) to opponent goal (100),
y from the team's left touchline (0) to right touchline (100).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# slot = (name, x, y, line, default_role)
FORMATIONS: dict[str, list[tuple[str, float, float, str, str]]] = {
    "4-3-3": [
        ("GK", 5, 50, "GK", "keeper"),
        ("LB", 26, 12, "DF", "fullback"), ("LCB", 22, 37, "DF", "ball_playing"),
        ("RCB", 22, 63, "DF", "stopper"), ("RB", 26, 88, "DF", "fullback"),
        ("DM", 40, 50, "MF", "anchor"), ("LCM", 52, 30, "MF", "box_to_box"), ("RCM", 52, 70, "MF", "playmaker"),
        ("LW", 74, 14, "FW", "winger"), ("ST", 80, 50, "FW", "poacher"), ("RW", 74, 86, "FW", "inside_forward"),
    ],
    "4-4-2": [
        ("GK", 5, 50, "GK", "keeper"),
        ("LB", 26, 12, "DF", "fullback"), ("LCB", 22, 37, "DF", "stopper"),
        ("RCB", 22, 63, "DF", "cover"), ("RB", 26, 88, "DF", "fullback"),
        ("LM", 52, 12, "MF", "wide_midfielder"), ("LCM", 47, 38, "MF", "box_to_box"),
        ("RCM", 47, 62, "MF", "anchor"), ("RM", 52, 88, "MF", "wide_midfielder"),
        ("ST1", 76, 38, "FW", "poacher"), ("ST2", 76, 62, "FW", "target_man"),
    ],
    "4-2-3-1": [
        ("GK", 5, 50, "GK", "keeper"),
        ("LB", 26, 12, "DF", "fullback"), ("LCB", 22, 37, "DF", "ball_playing"),
        ("RCB", 22, 63, "DF", "stopper"), ("RB", 26, 88, "DF", "fullback"),
        ("LDM", 40, 38, "MF", "anchor"), ("RDM", 40, 62, "MF", "box_to_box"),
        ("LAM", 64, 14, "FW", "winger"), ("CAM", 62, 50, "MF", "playmaker"), ("RAM", 64, 86, "FW", "inside_forward"),
        ("ST", 82, 50, "FW", "poacher"),
    ],
    "3-5-2": [
        ("GK", 5, 50, "GK", "keeper"),
        ("LCB", 22, 26, "DF", "stopper"), ("CB", 20, 50, "DF", "cover"), ("RCB", 22, 74, "DF", "stopper"),
        ("LWB", 50, 8, "DF", "wingback"), ("LCM", 50, 35, "MF", "box_to_box"), ("DM", 38, 50, "MF", "regista"),
        ("RCM", 50, 65, "MF", "box_to_box"), ("RWB", 50, 92, "DF", "wingback"),
        ("ST1", 76, 38, "FW", "poacher"), ("ST2", 76, 62, "FW", "pressing_forward"),
    ],
    "5-3-2": [
        ("GK", 5, 50, "GK", "keeper"),
        ("LWB", 34, 8, "DF", "wingback"), ("LCB", 22, 28, "DF", "stopper"), ("CB", 19, 50, "DF", "cover"),
        ("RCB", 22, 72, "DF", "stopper"), ("RWB", 34, 92, "DF", "wingback"),
        ("LCM", 46, 30, "MF", "box_to_box"), ("CM", 42, 50, "MF", "anchor"), ("RCM", 46, 70, "MF", "box_to_box"),
        ("ST1", 74, 40, "FW", "target_man"), ("ST2", 74, 60, "FW", "poacher"),
    ],
    "3-4-3": [
        ("GK", 5, 50, "GK", "keeper"),
        ("LCB", 22, 26, "DF", "ball_playing"), ("CB", 20, 50, "DF", "cover"), ("RCB", 22, 74, "DF", "ball_playing"),
        ("LM", 50, 10, "MF", "wide_midfielder"), ("LCM", 46, 38, "MF", "playmaker"),
        ("RCM", 46, 62, "MF", "anchor"), ("RM", 50, 90, "MF", "wide_midfielder"),
        ("LW", 72, 18, "FW", "inside_forward"), ("ST", 80, 50, "FW", "false_nine"), ("RW", 72, 82, "FW", "inside_forward"),
    ],
}

# role -> modifiers.  ax/dx: x shift in/out of possession.  spread: width multiplier.
# dr: dribble tendency, sh: shooting tendency, fw: forward-pass preference, pr: pressing willingness,
# sf: safe-passing preference.
ROLES: dict[str, dict[str, Any]] = {
    "keeper":          dict(line="GK", label="Goalkeeper",         ax=0,  dx=0,  spread=1.0,  dr=0.0, sh=0.0, fw=-0.3, pr=0.0, sf=0.4),
    "sweeper_keeper":  dict(line="GK", label="Sweeper keeper",     ax=3,  dx=6,  spread=1.0,  dr=0.0, sh=0.0, fw=0.0,  pr=0.0, sf=0.1),
    "stopper":         dict(line="DF", label="Stopper CB",         ax=0,  dx=4,  spread=1.0,  dr=0.6, sh=0.2, fw=-0.1, pr=1.3, sf=0.1),
    "cover":           dict(line="DF", label="Covering CB",        ax=-4, dx=-4, spread=1.0,  dr=0.4, sh=0.1, fw=-0.2, pr=0.6, sf=0.4),
    "ball_playing":    dict(line="DF", label="Ball-playing CB",    ax=2,  dx=0,  spread=1.0,  dr=0.8, sh=0.2, fw=0.3,  pr=0.9, sf=0.0),
    "fullback":        dict(line="DF", label="Full-back",          ax=8,  dx=0,  spread=1.1,  dr=1.0, sh=0.3, fw=0.1,  pr=1.0, sf=0.1),
    "wingback":        dict(line="DF", label="Attacking wing-back", ax=22, dx=4,  spread=1.2,  dr=1.3, sh=0.5, fw=0.3,  pr=1.1, sf=-0.1),
    "defensive_fb":    dict(line="DF", label="Defensive full-back", ax=0,  dx=-2, spread=1.0,  dr=0.5, sh=0.1, fw=-0.1, pr=0.9, sf=0.3),
    "anchor":          dict(line="MF", label="Anchor man",         ax=-8, dx=-2, spread=1.0,  dr=0.5, sh=0.3, fw=-0.1, pr=1.0, sf=0.3),
    "regista":         dict(line="MF", label="Deep playmaker",     ax=-4, dx=0,  spread=1.0,  dr=0.8, sh=0.5, fw=0.4,  pr=0.7, sf=0.0),
    "box_to_box":      dict(line="MF", label="Box-to-box",         ax=12, dx=2,  spread=1.0,  dr=1.0, sh=1.0, fw=0.1,  pr=1.2, sf=0.0),
    "playmaker":       dict(line="MF", label="Advanced playmaker", ax=6,  dx=0,  spread=1.0,  dr=1.1, sh=0.8, fw=0.3,  pr=0.8, sf=0.0),
    "wide_midfielder": dict(line="MF", label="Wide midfielder",    ax=8,  dx=0,  spread=1.25, dr=1.3, sh=0.6, fw=0.2,  pr=1.0, sf=0.0),
    "shadow_striker":  dict(line="MF", label="Shadow striker",     ax=16, dx=6,  spread=1.0,  dr=1.2, sh=1.6, fw=0.3,  pr=1.0, sf=-0.1),
    "poacher":         dict(line="FW", label="Poacher",            ax=6,  dx=2,  spread=1.0,  dr=0.8, sh=1.8, fw=0.2,  pr=0.8, sf=0.0),
    "target_man":      dict(line="FW", label="Target man",         ax=2,  dx=0,  spread=1.0,  dr=0.6, sh=1.2, fw=-0.2, pr=0.9, sf=0.2),
    "false_nine":      dict(line="FW", label="False nine",         ax=-6, dx=-3, spread=1.0, dr=1.0, sh=1.1, fw=0.3,  pr=0.8, sf=0.0),
    "winger":          dict(line="FW", label="Winger",             ax=6,  dx=0,  spread=1.25, dr=1.6, sh=0.8, fw=0.3,  pr=1.0, sf=0.0),
    "inside_forward":  dict(line="FW", label="Inside forward",     ax=8,  dx=0,  spread=0.75, dr=1.4, sh=1.5, fw=0.4,  pr=1.0, sf=-0.1),
    "pressing_forward": dict(line="FW", label="Pressing forward",  ax=4,  dx=6,  spread=1.0,  dr=0.9, sh=1.1, fw=0.1,  pr=1.6, sf=0.0),
}

INSTRUCTIONS = ("line_height", "pressing", "width", "tempo", "directness")


def _clamp01(v: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return default


@dataclass
class Tactic:
    name: str = "Custom"
    formation: str = "4-3-3"
    roles: list[str] = field(default_factory=list)  # one role per formation slot
    line_height: float = 0.5  # how high the defensive line / block sits
    pressing: float = 0.5     # pressing intensity (also costs stamina)
    width: float = 0.5        # how wide the team stretches
    tempo: float = 0.5        # speed of play (more actions per minute)
    directness: float = 0.5   # short build-up (0) vs direct / vertical play (1)

    def __post_init__(self):
        if self.formation not in FORMATIONS:
            self.formation = "4-4-2"
        slots = FORMATIONS[self.formation]
        roles = list(self.roles)[: len(slots)]
        for i, slot in enumerate(slots):
            role = roles[i] if i < len(roles) else slot[4]
            if role not in ROLES or ROLES[role]["line"] != slot[3]:
                role = slot[4]  # invalid or wrong line -> slot default
            if i < len(roles):
                roles[i] = role
            else:
                roles.append(role)
        self.roles = roles
        for k in INSTRUCTIONS:
            setattr(self, k, _clamp01(getattr(self, k)))
        self.name = str(self.name)[:40] or "Custom"

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Tactic":
        allowed = {"name", "formation", "roles", *INSTRUCTIONS}
        return cls(**{k: v for k, v in d.items() if k in allowed})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _t(name, formation, roles=None, **kw) -> Tactic:
    return Tactic(name=name, formation=formation, roles=roles or [], **kw)


PRESETS: dict[str, Tactic] = {t.name: t for t in [
    _t("Possession 4-3-3", "4-3-3",
       ["keeper", "fullback", "ball_playing", "ball_playing", "fullback", "regista", "box_to_box", "playmaker",
        "winger", "false_nine", "inside_forward"],
       line_height=0.7, pressing=0.65, width=0.7, tempo=0.4, directness=0.2),
    _t("Gegenpress 4-2-3-1", "4-2-3-1",
       ["sweeper_keeper", "fullback", "stopper", "stopper", "fullback", "box_to_box", "box_to_box",
        "winger", "playmaker", "inside_forward", "pressing_forward"],
       line_height=0.85, pressing=0.9, width=0.55, tempo=0.85, directness=0.55),
    _t("Low block 5-3-2", "5-3-2",
       ["keeper", "defensive_fb", "stopper", "cover", "stopper", "defensive_fb", "box_to_box", "anchor", "box_to_box",
        "target_man", "poacher"],
       line_height=0.15, pressing=0.25, width=0.35, tempo=0.5, directness=0.85),
    _t("Direct 4-4-2", "4-4-2", None,
       line_height=0.5, pressing=0.5, width=0.6, tempo=0.65, directness=0.8),
    _t("Balanced 4-3-3", "4-3-3", None,
       line_height=0.5, pressing=0.5, width=0.5, tempo=0.5, directness=0.5),
    _t("Wing play 3-4-3", "3-4-3", None,
       line_height=0.6, pressing=0.55, width=0.95, tempo=0.6, directness=0.55),
    _t("Counter-attack 4-4-2", "4-4-2",
       ["keeper", "defensive_fb", "stopper", "cover", "defensive_fb", "wide_midfielder", "anchor", "box_to_box",
        "wide_midfielder", "poacher", "target_man"],
       line_height=0.25, pressing=0.35, width=0.55, tempo=0.8, directness=0.9),
]}


def resolve_tactic(spec: Any) -> Tactic:
    """Accept a preset name, a dict, or a Tactic; fall back to the balanced preset."""
    if isinstance(spec, Tactic):
        return spec
    if isinstance(spec, dict):
        return Tactic.from_dict(spec)
    if isinstance(spec, str) and spec in PRESETS:
        return PRESETS[spec]
    return PRESETS["Balanced 4-3-3"]


def describe_catalog() -> dict[str, Any]:
    """JSON-friendly catalog for the front-end tactic editor."""
    return {
        "formations": {
            name: [dict(slot=s[0], x=s[1], y=s[2], line=s[3], default_role=s[4]) for s in slots]
            for name, slots in FORMATIONS.items()
        },
        "roles": {k: dict(line=v["line"], label=v["label"], ax=v["ax"], spread=v["spread"]) for k, v in ROLES.items()},
        "presets": [t.to_dict() for t in PRESETS.values()],
        "instructions": list(INSTRUCTIONS),
    }
