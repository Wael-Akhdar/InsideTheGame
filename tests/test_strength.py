"""Team level must matter the way it does in real leagues (gamepulse/strength.py)."""
from gamepulse.lab import evaluate
from gamepulse.strength import LEVELS, quality_for


def test_quality_mapping():
    assert quality_for(None) == 1.0 and quality_for("mid") == 1.0
    assert quality_for("title") > quality_for("europe") > 1.0 > quality_for("lower") > quality_for("relegation")
    assert quality_for("nonsense") == 1.0 and quality_for(9) == quality_for(1.5)
    assert set(LEVELS) >= {"title", "mid", "relegation"}


def test_a_title_contender_beats_a_relegation_side():
    r = evaluate("Balanced 4-3-3", ["Balanced 4-3-3"], n=40, workers=4, level="title", opponent_level="relegation")["matchups"][0]
    # real: a strength gap of about 1.6 log-goals -> roughly 75-80% wins and about 1.5 goals of margin
    assert r["win"] >= 60, r
    assert r["gf"] - r["ga"] > 0.9, r
    assert r["shots_for"] > r["shots_against"], r
