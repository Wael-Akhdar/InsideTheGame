from gamepulse.agents.pipeline import Orchestrator, Viewer
from gamepulse.simulator.match import MatchSimulator


def test_simulator_is_deterministic():
    a = [e.to_dict() for e in MatchSimulator(seed=7).events()]
    b = [e.to_dict() for e in MatchSimulator(seed=7).events()]
    assert a == b and len(a) > 300


def test_event_types_realistic():
    evs = list(MatchSimulator(seed=1).events())
    types = {e.type for e in evs}
    assert {"pass", "shot", "tackle", "pressure", "possession_change", "halftime", "fulltime"} <= types
    assert all(0 <= e.x <= 100 for e in evs)


def test_pipeline_produces_explained_overlays():
    sim = MatchSimulator(seed=3, scenario="red_card")
    orch = Orchestrator(sim.home, sim.away)
    overlays = []
    for ev in sim.events():
        overlays += orch.process(ev, Viewer(mode="analyst"))
    assert overlays, "expected at least one overlay"
    assert all(o.explanation and o.evidence for o in overlays)
    assert orch.state.score == sim.score
