"""Coach-facing tactics: formation, per-player roles and team instructions.

Coordinates are in the *team frame*: x runs from own goal (0) to opponent goal (100),
y from the team's left touchline (0) to right touchline (100).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

# slot = (name, x, y, line, default_role)
_HANDMADE: dict[str, list[tuple[str, float, float, str, str]]] = {
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
ROLE_PARAMS = {"ax": (-20, 25), "dx": (-10, 10), "spread": (0.6, 1.4), "dr": (0.0, 2.0), "sh": (0.0, 2.0),
               "fw": (-0.4, 0.6), "pr": (0.0, 2.0), "sf": (-0.2, 0.5)}


# ----------------------------------------------------------------------------- formations
_SPAN = {1: 0, 2: 34, 3: 64, 4: 80, 5: 88, 6: 90}
_FW_ROLES = {1: ["poacher"], 2: ["poacher", "target_man"], 3: ["winger", "poacher", "inside_forward"],
             4: ["winger", "poacher", "target_man", "inside_forward"]}


def _ys(n: int) -> list[float]:
    return [50.0] if n == 1 else [round(50 - _SPAN[n] / 2 + _SPAN[n] * i / (n - 1), 1) for i in range(n)]


def parse_formation(name: str) -> list[int] | None:
    """'4-2-3-1' -> [4, 2, 3, 1] if it is a playable shape (10 outfield players, 3-5 defenders, 1-4 forwards)."""
    if not re.fullmatch(r"\d(-\d){1,4}", name or ""):
        return None
    parts = [int(x) for x in name.split("-")]
    if sum(parts) != 10 or not 3 <= parts[0] <= 5 or not 1 <= parts[-1] <= 4 or min(parts) < 1 or max(parts) > 6:
        return None
    return parts


def _generate(name: str, parts: list[int]) -> list[tuple[str, float, float, str, str]]:
    slots: list[tuple[str, float, float, str, str]] = [("GK", 5, 50, "GK", "keeper")]
    d, mids, f = parts[0], parts[1:-1], parts[-1]
    # defenders
    dn = {3: ["LCB", "CB", "RCB"], 4: ["LB", "LCB", "RCB", "RB"], 5: ["LWB", "LCB", "CB", "RCB", "RWB"]}[d]
    cb_roles = ["ball_playing", "stopper", "cover", "stopper"]
    ci = 0
    for nm, y in zip(dn, _ys(d)):
        wide = nm in ("LB", "RB", "LWB", "RWB")
        role = ("wingback" if d == 5 else "fullback") if wide else cb_roles[ci % len(cb_roles)]
        ci += 0 if wide else 1
        x = 34 if (wide and d == 5) else 26 if wide else (20 if d % 2 and nm == "CB" else 22)
        slots.append((nm, x, y, "DF", role))
    # midfield lines
    tags = {1: ["CM"], 2: ["DM", "AM"], 3: ["DM", "CM", "AM"]}[len(mids)]
    xs = {1: [48], 2: [40, 62], 3: [38, 52, 64]}[len(mids)]
    for n, tag, x0 in zip(mids, tags, xs):
        names = {1: [tag], 2: ["L" + tag, "R" + tag], 3: ["L" + tag, tag, "R" + tag],
                 4: ["LM", "L" + tag, "R" + tag, "RM"], 5: ["LM", "L" + tag, tag, "R" + tag, "RM"],
                 6: ["LM", "L" + tag, "L" + tag + "2", "R" + tag + "2", "R" + tag, "RM"]}[n]
        for k, (nm, y) in enumerate(zip(names, _ys(n))):
            wide = nm in ("LM", "RM") or (tag == "AM" and n >= 3 and k in (0, n - 1))
            if wide and tag == "AM":
                slots.append((nm, x0, y, "FW", "winger" if k == 0 else "inside_forward"))
            elif wide:
                slots.append((nm, x0 + 4, y, "MF", "wide_midfielder"))
            else:
                if tag == "DM":
                    role = "anchor" if (n == 1 or k == 0) else "box_to_box"
                elif tag == "AM":
                    role = "playmaker" if k == 0 else "shadow_striker"
                else:
                    centre = abs(k - (n - 1) / 2) < 0.6
                    role = ("playmaker" if len(mids) == 1 and n >= 3 and centre else "anchor" if centre and n == 5
                            else "box_to_box")
                slots.append((nm, x0, y, "MF", role))
    # forwards
    fn = {1: ["ST"], 2: ["ST1", "ST2"], 3: ["LW", "ST", "RW"], 4: ["LW", "LST", "RST", "RW"]}[f]
    fx = {1: [80], 2: [76, 76], 3: [74, 80, 74], 4: [72, 78, 78, 72]}[f]
    for nm, y, x, r in zip(fn, _ys(f), fx, _FW_ROLES[f]):
        slots.append((nm, x, y, "FW", r))
    return slots


_CACHE: dict[str, list] = {}


def get_formation(name: str) -> list[tuple[str, float, float, str, str]] | None:
    """Hand-tuned shapes first, otherwise any playable 'd-m-f' pattern is generated on the fly."""
    if name in _HANDMADE:
        return _HANDMADE[name]
    if name in _CACHE:
        return _CACHE[name]
    parts = parse_formation(name)
    if parts is None:
        return None
    _CACHE[name] = _generate(name, parts)
    return _CACHE[name]


def all_formation_names() -> list[str]:
    """Every playable shape: 3-5 defenders, 1-4 forwards, up to three midfield lines."""
    names = set(_HANDMADE)

    def splits(total: int, parts: int):
        if parts == 1:
            if 1 <= total <= 5:
                yield [total]
            return
        for a in range(1, min(5, total - parts + 1) + 1):
            for rest in splits(total - a, parts - 1):
                yield [a] + rest

    for d in (3, 4, 5):
        for f in (1, 2, 3, 4):
            m = 10 - d - f
            for k in (1, 2, 3):
                for mids in splits(m, k) if m >= k else []:
                    names.add("-".join(map(str, [d, *mids, f])))
    return sorted((n for n in names if get_formation(n)), key=lambda n: ([int(x) for x in n.split("-")], n))


FORMATIONS = _HANDMADE  # kept for backwards compatibility; use get_formation()


def _clamp01(v: Any, default: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return default


def sanitize_role(params: dict[str, Any], label: str = "Custom role", text: str = "") -> dict[str, Any]:
    """Clamp a (possibly AI-written) role definition to the ranges the simulator understands."""
    out: dict[str, Any] = {"label": str(label)[:40] or "Custom role", "text": str(text)[:300], "custom": True}
    mid = {"ax": 4.0, "dx": 0.0, "spread": 1.0, "dr": 1.0, "sh": 0.6, "fw": 0.1, "pr": 1.0, "sf": 0.1}
    for k, (lo, hi) in ROLE_PARAMS.items():
        try:
            v = float(params.get(k, mid[k]))
        except (TypeError, ValueError):
            v = mid[k]
        out[k] = round(max(lo, min(hi, v)), 2)
    return out


@dataclass
class Tactic:
    name: str = "Custom"
    formation: str = "4-3-3"
    roles: list[str] = field(default_factory=list)  # one role per formation slot (preset key or custom key)
    line_height: float = 0.5  # how high the defensive line / block sits
    pressing: float = 0.5     # pressing intensity (also costs stamina)
    width: float = 0.5        # how wide the team stretches
    tempo: float = 0.5        # speed of play (more actions per minute)
    directness: float = 0.5   # short build-up (0) vs direct / vertical play (1)
    custom_roles: dict[str, dict[str, Any]] = field(default_factory=dict)  # coach-described roles

    def __post_init__(self):
        if get_formation(self.formation) is None:
            self.formation = "4-4-2"
        slots = get_formation(self.formation)
        self.custom_roles = {str(k): sanitize_role(v, v.get("label", "Custom role"), v.get("text", ""))
                             for k, v in (self.custom_roles or {}).items() if isinstance(v, dict)}
        roles = list(self.roles)[: len(slots)]
        for i, slot in enumerate(slots):
            role = roles[i] if i < len(roles) else slot[4]
            if role in self.custom_roles:
                pass  # any slot may use a coach-described role
            elif role not in ROLES or ROLES[role]["line"] != slot[3]:
                role = slot[4]  # invalid or wrong line -> slot default
            if i < len(roles):
                roles[i] = role
            else:
                roles.append(role)
        self.roles = roles
        for k in INSTRUCTIONS:
            setattr(self, k, _clamp01(getattr(self, k)))
        self.name = str(self.name)[:40] or "Custom"

    def role(self, i: int) -> dict[str, Any]:
        key = self.roles[i]
        return self.custom_roles[key] if key in self.custom_roles else ROLES[key]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Tactic":
        allowed = {"name", "formation", "roles", "custom_roles", *INSTRUCTIONS}
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
            name: [dict(slot=s[0], x=s[1], y=s[2], line=s[3], default_role=s[4]) for s in get_formation(name)]
            for name in all_formation_names()
        },
        "roles": {k: dict(line=v["line"], label=v["label"], ax=v["ax"], spread=v["spread"]) for k, v in ROLES.items()},
        "presets": [t.to_dict() for t in PRESETS.values()],
        "instructions": list(INSTRUCTIONS),
    }
