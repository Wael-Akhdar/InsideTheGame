"""Different tactics must give different games (real teams: 43 to 58% of the passes of a match, accuracy 78 to 86%)."""
import numpy as np

from gamepulse.simulator.match import MatchSimulator
from gamepulse.tactics import Tactic

PATIENT = Tactic(name="patient", formation="4-3-3", line_height=0.8, pressing=0.7, width=0.6, tempo=0.4, directness=0.1)
DIRECT = Tactic(name="direct", formation="4-3-3", line_height=0.25, pressing=0.3, width=0.5, tempo=0.8, directness=0.95)


def _profile(tac, n=10):
    passes, share, shots, acc = [], [], [], []
    for s in range(n):
        sim = MatchSimulator(seed=300 + s, home_tactic=tac, away_tactic="Balanced 4-3-3", record_frames=False)
        mine = other = sh = ok = 0
        for e in sim.events():
            if e.type == "pass":
                mine += e.team == sim.home.id
                other += e.team != sim.home.id
                ok += e.team == sim.home.id and e.outcome == "success"
            elif e.type == "shot" and e.team == sim.home.id:
                sh += 1
        passes.append(mine)
        share.append(100 * mine / (mine + other))
        shots.append(sh)
        acc.append(100 * ok / mine)
    return float(np.mean(passes)), float(np.mean(share)), float(np.mean(shots)), float(np.mean(acc))


def test_patient_and_direct_styles_play_different_games():
    p, d = _profile(PATIENT), _profile(DIRECT)
    assert p[1] - d[1] > 10, (p, d)  # real: 58% vs 43% of the passes of the match
    assert p[3] - d[3] > 4, (p, d)  # real: 86% vs 78% pass accuracy
    assert d[2] > 5 and p[2] > 5  # both still create chances
