from gamepulse.overlay import build_feed, export_overlay


def test_overlay_is_timestamped_and_sorted():
    res = export_overlay(build_feed("sim", 7))
    cards = res["overlays"]
    assert res["schema"] == "gamepulse.overlay/1" and cards
    ts = [c["t"] for c in cards]
    assert ts == sorted(ts) and all(0 <= t <= 7200 for t in ts)
    assert [c["id"] for c in cards] == list(range(1, len(cards) + 1))
    assert all(c["duration"] > 0 and c["headline"] and c["evidence"] for c in cards)


def test_overlay_deterministic():
    assert export_overlay(build_feed("sim", 3)) == export_overlay(build_feed("sim", 3))
