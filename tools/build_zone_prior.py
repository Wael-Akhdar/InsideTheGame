"""Build the zone prior used by the simulator: where real passes go from each zone of the pitch, and how often an action ends in a shot.

Source: Wyscout public dataset (Pappalardo et al., 2019), CC BY 4.0, four leagues (England left out), read from data/external/wyscout/.
Only aggregated frequencies are written (gamepulse/simulator/zone_prior.json): no event, player or club leaves the data folder.
The pitch is cut in NX x NY zones in the team frame (own goal at x = 0, attacking towards x = 100).

    python tools/build_zone_prior.py
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / "data" / "external" / "wyscout" / "events.zip"
OUT = ROOT / "gamepulse" / "simulator" / "zone_prior.json"  # aggregated frequencies only
NX, NY = 10, 6
LEAGUES = ("France", "Germany", "Italy", "Spain")


def zone(x: float, y: float) -> int:
    return min(NX - 1, int(x / 100 * NX)) * NY + min(NY - 1, int(y / 100 * NY))


def main() -> int:
    z = zipfile.ZipFile(ZIP)
    n = NX * NY
    trans = np.zeros((n, n))
    actions = np.zeros(n)
    shots = np.zeros(n)
    attempts = np.zeros(n)
    accurate = np.zeros(n)
    for lg in LEAGUES:
        for e in json.loads(z.read(f"events_{lg}.json")):
            name, sub, pos = e["eventName"], e["subEventName"], e["positions"]
            if not pos:
                continue
            zs = zone(pos[0]["x"], pos[0]["y"])
            if name == "Pass":
                actions[zs] += 1
                attempts[zs] += 1
                accurate[zs] += any(t["id"] == 1801 for t in e["tags"])
                if len(pos) == 2 and pos[1] and any(t["id"] == 1801 for t in e["tags"]):
                    trans[zs, zone(pos[1]["x"], pos[1]["y"])] += 1
            elif name == "Shot" or (name == "Free Kick" and sub in ("Free kick shot", "Penalty")):
                actions[zs] += 1
                shots[zs] += 1
    rows = trans + 0.5  # a little smoothing so that no destination is impossible
    rows = rows / rows.sum(1, keepdims=True)
    shot_rate = shots / np.maximum(actions, 1)
    mean_acc = accurate.sum() / attempts.sum()
    acc = (accurate + 30 * mean_acc) / (attempts + 30)  # zones with few passes are pulled towards the overall accuracy
    OUT.write_text(json.dumps({"nx": NX, "ny": NY, "trans": np.round(rows, 5).tolist(), "shot_rate": np.round(shot_rate, 5).tolist(),
                               "acc_start": np.round(acc, 4).tolist(), "acc_mean": round(float(mean_acc), 4),
                               "source": "Wyscout public dataset, Pappalardo et al. 2019, CC BY 4.0 (aggregated frequencies)"}))
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e3:.0f} kB); shots per action in the six central zones near the goal: "
          f"{[round(float(shot_rate[(NX - 1) * NY + j]), 3) for j in range(NY)]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
