"""Timestamped overlay export: the whole match as one JSON a broadcast renderer can place on a video.

    python -m gamepulse.overlay --source sim --seed 42 --lang fr --out overlay.json

`t` is the match clock in seconds (kickoff = 0; the second half starts at 45:00 or later, as in the event
feed). A video player adds its own kickoff offset (and the half-time gap) to place the card.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Optional

from .agents.pipeline import Orchestrator, Viewer
from .feed import SimulatorFeed
from .feed.sportec import SportecFeed
from .feed.wyscout import WyscoutFeed

SCHEMA = "gamepulse.overlay/1"


def build_feed(source: str = "sim", seed: int = 42, league: str = "Spain", home: str = "Possession 4-3-3",
               away: str = "Counter-attack 4-4-2"):
    if source == "sportec":
        return SportecFeed(None, seed)
    if source == "wyscout":
        return WyscoutFeed(league, seed)
    return SimulatorFeed(seed=seed, home_tactic=home, away_tactic=away)


def export_overlay(feed, viewer: Optional[Viewer] = None, threshold: float = 0.55) -> dict[str, Any]:
    """Run the full agent chain over a feed and return {meta, overlays} (overlays sorted by time)."""
    viewer = viewer or Viewer()
    orch = Orchestrator(*feed.teams)
    cards: list[dict[str, Any]] = []
    for tk in feed.ticks():
        for o in orch.process_tick(tk, viewer, threshold):
            cards.append(o.to_dict())
    cards.sort(key=lambda c: (c["t"], -c["importance"]))
    for i, c in enumerate(cards, 1):
        c["id"] = i
    home, away = feed.teams
    return {"schema": SCHEMA, "source": feed.name, "label": getattr(feed, "label", feed.name),
            "lang": viewer.lang, "mode": viewer.mode, "clock": "match seconds since kickoff",
            "teams": {t.id: t.name for t in (home, away)}, "score": orch.state.snapshot().get("score"),
            "overlays": cards}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default="sim", choices=["sim", "wyscout", "sportec"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--league", default="Spain")
    ap.add_argument("--lang", default="en", choices=["en", "fr", "es", "ar"])
    ap.add_argument("--mode", default="casual", choices=["casual", "analyst"])
    ap.add_argument("--out", default="-")
    a = ap.parse_args()
    res = export_overlay(build_feed(a.source, a.seed, a.league), Viewer(mode=a.mode, lang=a.lang))
    txt = json.dumps(res, indent=2, ensure_ascii=False)
    if a.out == "-":
        print(txt)
    else:
        open(a.out, "w").write(txt)
        print(f"{len(res['overlays'])} overlays -> {a.out}")


if __name__ == "__main__":
    main()
