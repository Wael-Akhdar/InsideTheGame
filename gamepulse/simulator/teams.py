"""Fictional clubs and players (no real Premier League data is used)."""
from __future__ import annotations

import random

from ..models import Player, Team
from ..tactics import FORMATIONS, ROLES, Tactic, resolve_tactic

_NAMES = {
    "RVR": ["Tomas Reyes", "Callum Frost", "Idris Okoye", "Marek Dolan", "Jules Varga",
            "Nico Alvarez", "Sami Haddad", "Leo Brandt", "Kofi Mensah", "Rafa Duarte", "Eli Novak"],
    "NTH": ["Owen Pryce", "Dario Costa", "Femi Adeyemi", "Luca Moretti", "Hugo Lindqvist",
            "Theo Marsh", "Amir Zaki", "Jonas Keller", "Dani Ortega", "Ravi Menon", "Cole Whitaker"],
}

# base attribute profile per line (0-100), tweaked by role
_BASE = {
    "GK": dict(passing=55, dribbling=35, shooting=25, tackling=40, pace=55, vision=55, stamina=70, keeping=76),
    "DF": dict(passing=66, dribbling=58, shooting=45, tackling=76, pace=68, vision=62, stamina=74, keeping=0),
    "MF": dict(passing=76, dribbling=70, shooting=64, tackling=66, pace=70, vision=74, stamina=80, keeping=0),
    "FW": dict(passing=66, dribbling=76, shooting=78, tackling=42, pace=80, vision=66, stamina=72, keeping=0),
}
_ROLE_BONUS = {
    "regista": dict(passing=8, vision=8), "playmaker": dict(passing=6, vision=7), "ball_playing": dict(passing=8, vision=5),
    "box_to_box": dict(stamina=6, tackling=3), "anchor": dict(tackling=8, stamina=3), "poacher": dict(shooting=6),
    "winger": dict(pace=5, dribbling=5), "inside_forward": dict(shooting=3, dribbling=5), "target_man": dict(shooting=2, pace=-6),
    "stopper": dict(tackling=5), "wingback": dict(stamina=6, pace=4), "pressing_forward": dict(stamina=6),
    "sweeper_keeper": dict(passing=10, keeping=-2),
}

_TEAM_INFO = {"RVR": ("Riverside FC", "RVR"), "NTH": ("Northgate United", "NTH")}


def build_team(tid: str, tactic, seed: int = 0, quality: float = 1.0) -> Team:
    """Create a squad for a tactic: one player per formation slot, attributes from slot line + role."""
    tactic = resolve_tactic(tactic)
    name, short = _TEAM_INFO.get(tid, (tid, tid))
    rng = random.Random(f"{tid}-{seed}")
    team = Team(id=tid, name=name, short=short, tactic=tactic)
    for i, (slot, x, y, line, _) in enumerate(FORMATIONS[tactic.formation]):
        role = tactic.roles[i]
        attrs = dict(_BASE[line])
        for k, v in _ROLE_BONUS.get(role, {}).items():
            attrs[k] += v
        for k in attrs:
            if attrs[k]:
                attrs[k] = round(max(30.0, min(95.0, 70 + (attrs[k] - 70) + (quality - 1) * 40 + rng.gauss(0, 3.5))), 1)
        names = _NAMES.get(tid) or [f"Player {n}" for n in range(1, 12)]
        team.players.append(Player(id=f"{tid}{i}", name=names[i % len(names)], team=tid, number=i + 1,
                                   position=line, slot=slot, role=role, attrs=attrs))
    return team


def default_teams(home_tactic="Possession 4-3-3", away_tactic="Counter-attack 4-4-2") -> tuple[Team, Team]:
    return build_team("RVR", home_tactic), build_team("NTH", away_tactic)
