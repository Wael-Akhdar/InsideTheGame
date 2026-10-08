from gamepulse.agents.pipeline import Orchestrator, Viewer
from gamepulse.lab import evaluate
from gamepulse.simulator.match import MatchSimulator
from gamepulse.tactics import FORMATIONS, PRESETS, Tactic


def test_simulator_is_deterministic():
    a = [e.to_dict() for e in MatchSimulator(seed=7, record_frames=False).events()]
    b = [e.to_dict() for e in MatchSimulator(seed=7, record_frames=False).events()]
    assert a == b and len(a) > 300


def test_event_types_realistic():
    evs = list(MatchSimulator(seed=1, record_frames=False).events())
    types = {e.type for e in evs}
    assert {"pass", "shot", "tackle", "pressure", "possession_change", "halftime", "fulltime"} <= types
    assert all(0 <= e.x <= 100 for e in evs)


def test_frames_have_22_players_in_bounds():
    ticks = list(MatchSimulator(seed=2).ticks())
    assert len(ticks) > 1000
    for tk in ticks[::50]:
        assert len(tk.frame["p"]) == 22
        assert all(0 <= x <= 100 and 0 <= y <= 100 for x, y in tk.frame["p"])


def test_all_presets_and_formations_valid():
    for name, tac in PRESETS.items():
        assert len(tac.roles) == 11 and tac.formation in FORMATIONS, name
    bad = Tactic(formation="9-9-9", roles=["nonsense"] * 3, pressing=5)
    assert bad.formation == "4-4-2" and bad.pressing == 1.0 and len(bad.roles) == 11


def test_tactics_change_outcomes():
    high = Tactic(name="all-out press", formation="4-3-3", pressing=1.0, line_height=1.0)
    low = Tactic(name="park the bus", formation="4-3-3", pressing=0.0, line_height=0.0)
    r = evaluate(high, [low], n=16, workers=1)
    assert r["matchups"][0]["ppda"] != 0 and r["insights"]


def test_pipeline_produces_explained_overlays():
    sim = MatchSimulator(seed=3)
    orch = Orchestrator(sim.home, sim.away)
    overlays = []
    for tk in sim.ticks():
        overlays += orch.process_tick(tk, Viewer(mode="analyst"))
    assert overlays, "expected at least one overlay"
    assert all(o.explanation and o.evidence for o in overlays)
    assert orch.state.score == sim.score
    assert abs(sum(orch.state.possession().values()) - 100) < 0.5
