"""Fictional clubs and players (no real Premier League data is used)."""
from __future__ import annotations

from ..models import Player, Team

_SQUAD = [
    ("GK", 1), ("DF", 2), ("DF", 4), ("DF", 5), ("DF", 3),
    ("MF", 6), ("MF", 8), ("MF", 10), ("FW", 7), ("FW", 9), ("FW", 11),
]

_NAMES = {
    "RVR": ["Tomas Reyes", "Callum Frost", "Idris Okoye", "Marek Dolan", "Jules Varga",
            "Nico Alvarez", "Sami Haddad", "Leo Brandt", "Kofi Mensah", "Rafa Duarte", "Eli Novak"],
    "NTH": ["Owen Pryce", "Dario Costa", "Femi Adeyemi", "Luca Moretti", "Hugo Lindqvist",
            "Theo Marsh", "Amir Zaki", "Jonas Keller", "Dani Ortega", "Ravi Menon", "Cole Whitaker"],
}


def _build(tid: str, name: str, short: str, style: dict[str, float]) -> Team:
    team = Team(id=tid, name=name, short=short, style=style)
    for i, ((pos, num), pname) in enumerate(zip(_SQUAD, _NAMES[tid])):
        team.players.append(Player(id=f"{tid}{i}", name=pname, team=tid, number=num, position=pos))
    return team


def default_teams() -> tuple[Team, Team]:
    home = _build("RVR", "Riverside FC", "RVR",
                  {"possession": 0.62, "pressing": 0.75, "directness": 0.35, "finishing": 0.55})
    away = _build("NTH", "Northgate United", "NTH",
                  {"possession": 0.42, "pressing": 0.45, "directness": 0.7, "finishing": 0.6})
    return home, away
