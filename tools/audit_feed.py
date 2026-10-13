"""Audit the pipeline on many matches of one feed: how often each insight fires and how the passing hub share is distributed.

    python tools/audit_feed.py real [n_per_league]   # public Wyscout matches (needs tools/fetch_wyscout.py)
    python tools/audit_feed.py sim [n]               # simulated matches
Prints aggregates only (no names).
"""
from __future__ import annotations

import statistics as st
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gamepulse.agents.pipeline import Orchestrator, Viewer  # noqa: E402
from gamepulse.engine.insights import _in  # noqa: E402


def hub_shares(state) -> list[float]:
    """Share of passing involvement of the top outfield player of each team, every 5 minutes (15-minute windows)."""
    out = []
    for m in range(20, 90, 5):
        win = _in(state.events, m - 15, m)
        for team in (state.home, state.away):
            passes = [e for e in win if e.type == "pass" and e.team == team and e.outcome == "success"]
            if len(passes) < 40:
                continue
            inv: Counter = Counter()
            for e in passes:
                if e.player:
                    inv[e.player] += 1
                if e.meta.get("receiver"):
                    inv[e.meta["receiver"]] += 1
            top = [n for p, n in inv.most_common(3) if state.roster.get(p, {}).get("line") != "GK"]
            if top:
                out.append(100 * top[0] / (2 * len(passes)))
    return out


def run(feeds) -> None:
    kinds, shares, n = Counter(), [], 0
    for feed in feeds:
        orch = Orchestrator(*feed.teams)
        for tk in feed.ticks():
            for ov in orch.process_tick(tk, Viewer(mode="analyst")):
                kinds[ov.kind] += 1
        shares += hub_shares(orch.state)
        n += 1
    print(f"{n} matches. Insights per match:", {k: round(v / n, 2) for k, v in sorted(kinds.items())})
    if shares:
        q = st.quantiles(shares, n=100)
        print(f"top-player passing share over 15 min (n={len(shares)}): median {q[49]:.1f}%  p90 {q[89]:.1f}%  p95 {q[94]:.1f}%  p99 {q[98]:.1f}%")


def main() -> None:
    kind = sys.argv[1] if len(sys.argv) > 1 else "real"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    if kind == "sim":
        from gamepulse.feed import SimulatorFeed
        run(SimulatorFeed(seed=s, home_tactic="Balanced 4-3-3", away_tactic="Balanced 4-3-3", record_frames=False) for s in range(n))
    else:
        from gamepulse.feed.wyscout import LEAGUES, WyscoutFeed, clear_cache
        for lg in LEAGUES:
            print(lg, end=": ")
            run(WyscoutFeed(lg, i * 7, cache=True) for i in range(n))
            clear_cache()


if __name__ == "__main__":
    main()
