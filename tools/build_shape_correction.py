"""Build the line-position correction of the shape model from real tracking (Sportec Open DFL data, CC BY 4.0, aggregated means only).

For each phase (team has the ball or not), line (DF / MF / FW) and band of the ball's depth, it stores how far, on average, the real
line stands from where the uncorrected model puts it (in pitch units along x). The simulator adds it to the target of every player of
that line. Lines are identified by matching real players to the formation's fixed slots.

    python tools/build_shape_correction.py            # fit on all downloaded matches and write gamepulse/simulator/shape_correction.json
    python tools/build_shape_correction.py --cv       # leave-matches-out check of the placement error with and without the correction
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "gamepulse" / "simulator" / "shape_correction.json"
NB = 10
LINES = ("DF", "MF", "FW")


def collect(tracks, params):
    """Per (phase, line, band): list of real - model x offsets of every player of the line, per frame."""
    from gamepulse import validation as V
    from gamepulse.simulator import match

    acc = {(ph, ln, b): [] for ph in ("in", "out") for ln in LINES for b in range(NB)}
    for t in tracks:
        S = V._side(t.formation)
        for pts, b, has in zip(t.real, t.ball, t.has_ball):
            if len(pts) < 10:
                continue
            pred = match.shape_targets(S, bool(has), float(b[0]), float(b[1]), params, correction=False)
            cost = np.hypot(*((pts[:, None, :] - S.base[None, :, :]) * V.KXY).transpose(2, 0, 1))
            r, c = linear_sum_assignment(cost)
            band = min(NB - 1, int(b[0] / 100 * NB))
            for i, j in zip(r, c):
                if S.line[j] != "GK":
                    acc[("in" if has else "out", S.line[j], band)].append(float(pts[i, 0] - pred[j, 0]))
    return acc


def table(acc, shrink: float = 30.0):
    """Mean offset per cell, shrunk towards 0 when the cell has few frames."""
    return {ph: {ln: [round(float(np.sum(acc[(ph, ln, b)]) / (len(acc[(ph, ln, b)]) + shrink)), 2) for b in range(NB)] for ln in LINES}
            for ph in ("in", "out")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv", action="store_true")
    a = ap.parse_args()
    from gamepulse import validation as V
    from gamepulse.simulator import match

    tracks = V.load_tracks(step_frames=3)
    if a.cv:
        matches = sorted({t.match for t in tracks})
        folds = [matches[i::3] for i in range(3)]
        base_err, corr_err = [], []
        for held in folds:
            train = [t for t in tracks if t.match not in held]
            test = [t for t in tracks if t.match in held]
            match.CORRECTION = None
            tab = table(collect(train, match.SHAPE))
            base_err.append(V.evaluate(test, match.SHAPE)["all"])
            match.CORRECTION = tab
            corr_err.append(V.evaluate(test, match.SHAPE)["all"])
            print(f"held out {held}: without {base_err[-1]:.2f} m, with correction {corr_err[-1]:.2f} m", flush=True)
        print(f"mean over folds: without {np.mean(base_err):.2f} m, with {np.mean(corr_err):.2f} m")
        return
    match.CORRECTION = None
    tab = table(collect(tracks, match.SHAPE))
    OUT.write_text(json.dumps({"bands": NB, "table": tab, "source": "Sportec Open DFL tracking (CC BY 4.0), aggregated means"}))
    print(f"wrote {OUT}")
    for ph in tab:
        for ln in LINES:
            print(ph, ln, tab[ph][ln])


if __name__ == "__main__":
    main()
