"""The event contract: every feed (simulator or real match) must satisfy it, and the pipeline must run on any of them."""
import re

import pytest

from gamepulse.agents.pipeline import Orchestrator, Viewer
from gamepulse.feed import ContractError, SimulatorFeed, validate_event, validate_stream
from gamepulse.feed.wyscout import DATA, WyscoutFeed, clear_cache
from gamepulse.models import Event

needs_data = pytest.mark.skipif(not (DATA / "events.zip").exists(), reason="run tools/fetch_wyscout.py first")


def test_simulator_feed_satisfies_the_contract():
    validate_stream(SimulatorFeed(seed=3, record_frames=False))


def test_contract_rejects_bad_events():
    ok = Event(id=1, minute=10, second=0, type="pass", team="H", player="p", x=10, y=20, end_x=30, end_y=40, outcome="success")
    assert validate_event(ok) == []
    assert validate_event(Event(id=2, minute=10, second=0, type="teleport", team="H"))
    assert validate_event(Event(id=3, minute=10, second=0, type="pass", team="H", player="p", x=140, y=20, outcome="success"))
    assert validate_event(Event(id=4, minute=10, second=0, type="shot", team="H", player="p", x=90, y=50, outcome="scored"))
    assert validate_event(Event(id=5, minute=10, second=0, type="shot", team="H", x=90, y=50, outcome="goal"))  # no player


def test_contract_catches_unordered_streams():
    feed = SimulatorFeed(seed=1, record_frames=False)
    ticks = list(feed.ticks())
    ticks[5].events[:0] = [Event(id=1, minute=0, second=0, type="foul", team="RVR", player="RVR3")]  # id goes backwards
    with pytest.raises(ContractError):
        validate_stream(feed, ticks)


@needs_data
def test_real_matches_satisfy_the_contract_and_reproduce_the_official_score():
    try:
        for i in (0, 37, 120, 250, 379):
            feed = WyscoutFeed("Spain", i, cache=True)
            validate_stream(feed)
            goals = {"HOM": 0, "AWY": 0}
            for tk in feed.ticks():
                for e in tk.events:
                    goals[e.team] += e.type == "goal"
            assert goals == feed.official_score, (i, goals, feed.official_score)
    finally:
        clear_cache()


@needs_data
def test_real_matches_are_pseudonymised():
    feed = WyscoutFeed("Italy", 40)
    names = [p.name for t in feed.teams for p in t.players] + [t.name for t in feed.teams]
    assert all(re.fullmatch(r"(Home|Away) (Team|#\d+)", n) for n in names), names[:5]


@needs_data
def test_the_same_pipeline_runs_on_a_real_match():
    feed = WyscoutFeed("Italy", 40)
    orch = Orchestrator(*feed.teams)  # no tactic, no positions: only what a real feed provides
    overlays = []
    for tk in feed.ticks():
        overlays += orch.process_tick(tk, Viewer(mode="analyst"))
    assert orch.state.score == feed.official_score
    assert overlays and all(o.evidence and o.explanation for o in overlays)
    assert abs(sum(orch.state.possession().values()) - 100) < 0.5
