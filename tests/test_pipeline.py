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


# ----------------------------------------------------------------- coach features
def test_all_formations_are_playable():
    from gamepulse.tactics import all_formation_names, get_formation
    names = all_formation_names()
    assert len(names) >= 60 and "4-1-2-1-2" in names and "3-4-1-2" in names
    for n in names:
        slots = get_formation(n)
        assert len(slots) == 11 and slots[0][0] == "GK", n
    assert get_formation("9-9-9") is None and get_formation("4-4-3") is None


def test_custom_role_is_clamped_and_used():
    t = Tactic(formation="4-3-3", roles=["keeper", "c1"], custom_roles={"c1": {"label": "Overlapper", "ax": 999, "sh": -5}})
    assert t.roles[1] == "c1" and t.custom_roles["c1"]["ax"] == 25 and t.custom_roles["c1"]["sh"] == 0
    assert len(list(MatchSimulator(seed=1, home_tactic=t, record_frames=False).events())) > 300


def test_role_and_scenario_interpreter_fallback():
    from gamepulse.agents.interpreter import interpret_role, interpret_scenario
    wide = interpret_role("stay wide and cross", "FW")
    deep = interpret_role("stay back and protect the defence, simple passes", "DF")
    assert wide["spread"] > deep["spread"] and deep["ax"] < wide["ax"]
    scn = interpret_scenario("red card for the opponent at 55 and we are down 0-2")
    kinds = {(r["action"]["type"], r["action"]["team"]) for r in scn["rules"]}
    assert ("red_card", "away") in kinds and ("goal", "away") in kinds


def test_scenario_rules_fire_and_are_sanitized():
    from gamepulse.scenario import sanitize
    scn = sanitize({"rules": [{"trigger": {"minute": 20}, "action": {"type": "red_card", "team": "home"}},
                              {"trigger": {"minute": 30}, "action": {"type": "nuke", "team": "home"}}]})
    assert len(scn["rules"]) == 1  # unknown action dropped
    sim = MatchSimulator(seed=4, scenario=scn, record_frames=False)
    cards = [e for e in sim.events() if e.type == "card"]
    assert cards and cards[0].team == "RVR" and cards[0].minute >= 20


def test_live_tactic_change_and_what_if():
    from gamepulse.lab import what_if
    sim = MatchSimulator(seed=9, record_frames=False)
    evs = []
    for i, tk in enumerate(sim.ticks()):
        evs += tk.events
        if i == 200:
            sim.set_tactic("RVR", {"formation": "5-4-1", "pressing": 0.1}, announce=True)
    assert sim.home.tactic.formation == "5-4-1" and any(e.type == "tactic_change" for e in evs)
    r = what_if("Balanced 4-3-3", {"rules": [{"trigger": {"minute": 30}, "action": {"type": "red_card", "team": "home"}}]},
                ["Balanced 4-3-3"], n=24)
    assert r["delta_ppg"] < 0 and r["verdict"] in ("hurts", "makes little difference")
