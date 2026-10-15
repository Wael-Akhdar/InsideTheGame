"""Build web/realism.json: every real-vs-simulated comparison in one file, shown in the app's Realism tab.

Only aggregated numbers are written. Sources: Wyscout public dataset (CC BY 4.0, Pappalardo et al. 2019), Sportec Open DFL tracking
(CC BY 4.0, Bassek et al. 2025).

    python tools/realism_report.py          # a few minutes
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "web" / "realism.json"


def _r(x, d=1):
    return round(float(x), d)


def main() -> None:
    from gamepulse import calibration as cal
    from gamepulse import spatial, strength, styles, validation as V
    from gamepulse.simulator.match import QUALITY_PER_GAP

    t0 = time.time()
    rep: dict = {"generated": time.strftime("%Y-%m-%d"), "sources": [
        "Wyscout public soccer match event dataset, CC BY 4.0. Pappalardo et al. (2019), Scientific Data 6:236. 1,446 league matches (France, Germany, Italy, Spain 2017/18).",
        "Sportec Open DFL dataset, CC BY 4.0, with the authorization of the DFL. Bassek, Rein, Weber, Memmert (2025). 7 Bundesliga matches with full tracking.",
        "Formations read from the starting line-ups (number of defenders, midfielders and forwards as filed by Wyscout), effect measured once the strength gap is accounted for."]}

    R, S = cal.real_stats(), cal.sim_stats(n=100)
    labels = {"passes": "Passes per team", "pass_acc": "Pass accuracy %", "pass_len": "Mean pass length (m)", "fwd_share": "Forward passes %",
              "shots": "Shots per team", "goals": "Goals per team", "conv": "Shot conversion %", "fouls": "Fouls per team"}
    rep["totals"] = [{"label": labels[k], "real": _r(R[k], 2), "sim": _r(S[k], 2), "ok": abs(S[k] - R[k]) <= cal.TOL[k] * abs(R[k])} for k in cal.KEYS]
    print("totals", time.time() - t0, flush=True)

    Rs, Ss = spatial.real_spatial(), spatial.sim_spatial(n=60)
    rep["spatial"] = [{"label": lab, "real": _r(Rs[k]), "sim": _r(Ss[k]), "ok": abs(Ss[k] - Rs[k]) <= tol} for k, lab, tol in spatial.ROWS]
    print("spatial", time.time() - t0, flush=True)

    Ry, Sy = styles.real_styles(), styles.sim_styles(48, 5)
    rep["styles"] = [{"label": lab, "real": [_r(np.percentile(Ry[k], 10)), _r(np.percentile(Ry[k], 90))],
                      "sim": [_r(np.percentile(Sy[k], 10)), _r(np.percentile(Sy[k], 90))]} for k, lab in styles.METRICS]
    print("styles", time.time() - t0, flush=True)

    rr = strength.real_rows()
    real_c = strength.curves(rr["rows"])
    gaps = [b["gap"] for b in real_c]
    sim_rows = strength.sim_gap_rows([g * QUALITY_PER_GAP for g in gaps], n=120)
    rep["strength"] = []
    for b, g in zip(real_c, gaps):
        s = strength._summ([dict(r, gap=g) for r in sim_rows[g * QUALITY_PER_GAP]])
        rep["strength"].append({"gap": _r(g, 2), **{k: {"real": _r(b[k], 2), "sim": _r(s[k], 2)} for k in ("win", "draw", "gf", "ga", "pass_share", "shot_share", "pass_acc")}})
    rep["levels"] = {k: {"strength": v[0], "label": v[1]} for k, v in strength.LEVELS.items()}
    print("strength", time.time() - t0, flush=True)

    tracks = V.load_tracks()
    fixed = V.evaluate(tracks, V.SHAPE, use_ball=False)["all"]
    model = V.evaluate(tracks, V.SHAPE)["all"]
    rep["placement"] = {"fixed": _r(fixed, 2), "model": _r(model, 2), "matches": len({t.match for t in tracks}),
                        "note": "Mean distance between each real player and the position the model predicts from the formation and the ball only."}
    rg, sg = V.real_goal_side(tracks), V.sim_goal_side(4)
    rep["defending"] = [{"depth": k, "real": _r(rg[k], 2), "sim": _r(sg[k], 2)} for k in rg]
    print("tracking", time.time() - t0, flush=True)

    real_f, sim_f = strength.real_formation_effects(), strength.sim_formation_effects(n=40)
    rep["formations"] = [{"formation": f, "real": _r(real_f[f]["effect"]), "se": _r(real_f[f]["se"]), "n": real_f[f]["n"], "sim": _r(sim_f[f])}
                         for f in strength.FORMATIONS if f in real_f]
    print("formations", time.time() - t0, flush=True)

    OUT.write_text(json.dumps(rep, indent=1))
    print(f"wrote {OUT} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
