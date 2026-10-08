"""Tactics must move the numbers in the direction football logic says they should.

These are sanity checks on the simulator, not proof of realism against real matches: they guard against the
failure mode where the instructions a coach sets have no measurable effect.
"""
from gamepulse.lab import evaluate
from gamepulse.tactics import PRESETS, Tactic

N = 30


def _row(tactic, opponent, n=N):
    return evaluate(tactic, [opponent], n=n, workers=1)["matchups"][0]


def test_possession_style_keeps_the_ball_against_a_low_block():
    r = _row("Possession 4-3-3", "Low block 5-3-2", n=40)
    assert r["possession"] > 55, r  # was ~50% when tactics did not drive ball retention
    assert r["pass_acc"] > 80


def test_possession_turns_into_chances_against_a_low_block():
    r = _row("Possession 4-3-3", "Low block 5-3-2", n=40)
    assert r["xgf"] > r["xga"], r  # was sterile: 62% of the ball but fewer shots than the opponent
    assert r["shots_for"] >= r["shots_against"], r


def test_balanced_mirror_is_balanced():
    r = _row("Balanced 4-3-3", "Balanced 4-3-3")
    assert 46 < r["possession"] < 54


def test_directness_trades_accuracy_for_territory():
    short = Tactic(name="short", formation="4-3-3", directness=0.1)
    direct = Tactic(name="direct", formation="4-3-3", directness=0.9)
    base = PRESETS["Balanced 4-3-3"]
    assert _row(short, base)["pass_acc"] > _row(direct, base)["pass_acc"] + 5
    assert _row(short, base)["possession"] > _row(direct, base)["possession"]


def test_pressing_lowers_opponent_freedom():
    high = Tactic(name="press", formation="4-3-3", pressing=0.95)
    low = Tactic(name="no press", formation="4-3-3", pressing=0.05)
    base = PRESETS["Balanced 4-3-3"]
    assert _row(high, base)["ppda"] < _row(low, base)["ppda"]
