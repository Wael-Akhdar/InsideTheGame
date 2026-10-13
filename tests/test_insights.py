"""The insight detectors read only events and line-ups, like a real data feed would provide."""
from gamepulse.engine.state import MatchState
from gamepulse.models import Event
from gamepulse.simulator.match import MatchSimulator


def _state() -> MatchState:
    st = MatchState("H", "A")
    st.roster = {f"H{i}": {"name": f"h{i}", "line": "GK" if i == 0 else "MF"} for i in range(11)}
    st.roster.update({f"A{i}": {"name": f"a{i}", "line": "GK" if i == 0 else "MF"} for i in range(11)})
    return st


def _ev(i, minute, type_, team, **kw) -> Event:
    return Event(id=i, minute=minute, second=0, type=type_, team=team, **kw)


def test_unlucky_dominance_is_detected_from_events_alone():
    st, found, i = _state(), [], 0
    for minute in range(1, 41):  # H keep shooting good chances, A score once from nothing
        i += 1
        found += st.ingest(_ev(i, minute, "shot", "H", player="H9", xg=0.12, outcome="saved"))
        if minute == 10:
            i += 1
            st.ingest(_ev(i, minute, "goal", "A", player="A9"))
    kinds = {m.kind for m in found}
    assert "unlucky" in kinds
    m = next(m for m in found if m.kind == "unlucky")
    assert m.team == "H" and m.facts["xg_for"] > m.facts["xg_against"] + 0.8 and m.evidence


def test_hub_player_needs_a_real_share_of_the_passing():
    st, found, i = _state(), [], 0
    for minute in range(1, 31):
        for k in range(3):  # H's passes all go through H5
            i += 1
            found += st.ingest(_ev(i, minute, "pass", "H", player="H5" if k % 2 == 0 else "H3", outcome="success", meta={"receiver": "H5"}))
    hubs = [m for m in found if m.kind == "key_player"]
    assert hubs and hubs[0].player == "H5" and hubs[0].facts["share"] >= 26


def test_goalkeepers_are_never_the_key_player():
    st, found, i = _state(), [], 0
    for minute in range(1, 31):
        for _ in range(3):
            i += 1
            found += st.ingest(_ev(i, minute, "pass", "H", player="H0", outcome="success", meta={"receiver": "H0"}))
    assert not [m for m in found if m.kind == "key_player"]


def test_turning_point_after_a_red_card():
    st, found, i = _state(), [], 0
    for minute in range(1, 30):  # balanced first half hour
        i += 1
        st.ingest(_ev(i, minute, "shot", "H" if minute % 2 else "A", player="H9", xg=0.08, outcome="off_target"))
    i += 1
    st.ingest(_ev(i, 30, "card", "H", player="H4", outcome="red"))
    for minute in range(31, 45):  # then A is much better
        i += 1
        found += st.ingest(_ev(i, minute, "shot", "A", player="A9", xg=0.15, outcome="saved"))
    tp = [m for m in found if m.kind == "turning_point"]
    assert tp and tp[0].team == "H" and tp[0].facts["after"] < tp[0].facts["before"]


def test_every_moment_cites_real_events_in_a_simulated_match():
    sim = MatchSimulator(seed=11, record_frames=False)
    st = _state()
    st.roster = {p.id: {"name": p.name, "line": p.position} for t in (sim.home, sim.away) for p in t.players}
    st.home, st.away = "RVR", "NTH"
    st.score, st.stats = {"RVR": 0, "NTH": 0}, MatchState("RVR", "NTH").stats
    st.poss_time = {"RVR": 0.0, "NTH": 0.0}
    ids, moments = set(), []
    for e in sim.events():
        ids.add(e.id)
        moments += st.ingest(e)
    assert moments
    for m in moments:
        assert m.evidence and set(m.evidence) <= ids, (m.kind, m.evidence)
