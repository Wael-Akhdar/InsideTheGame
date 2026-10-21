"""Split the Wyscout event files into one compressed file per match (data/external/wyscout/by_match/<league>/<id>.json.gz).

Loading a real match then needs a few MB instead of a whole season (about 1.7 GB of memory), which keeps the cloud
container small. Run after tools/fetch_wyscout.py.
"""
from __future__ import annotations

import gzip
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gamepulse.feed.wyscout import DATA, LEAGUES  # noqa: E402


def main() -> None:
    with zipfile.ZipFile(DATA / "events.zip") as z:
        for lg in LEAGUES:
            name = f"events_{lg}.json"
            if name not in z.namelist():
                continue
            grouped: dict[int, list] = {}
            for e in json.loads(z.read(name)):
                if e["matchPeriod"] in ("1H", "2H"):
                    grouped.setdefault(e["matchId"], []).append(e)
            out = DATA / "by_match" / lg
            out.mkdir(parents=True, exist_ok=True)
            for mid, evs in grouped.items():
                (out / f"{mid}.json.gz").write_bytes(gzip.compress(json.dumps(evs, separators=(",", ":")).encode()))
            print(f"{lg}: {len(grouped)} matches")


if __name__ == "__main__":
    main()
