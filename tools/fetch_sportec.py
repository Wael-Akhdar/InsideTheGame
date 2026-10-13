"""Download ONE match of the Sportec Open DFL dataset into data/external/sportec/.

Dataset: Bassek, Rein, Weber, Memmert (2025), "An integrated dataset of spatiotemporal and event data in elite soccer",
Scientific Data. Licence CC BY 4.0, released with the authorization of the DFL (figshare record 28196177).
Credit the paper and the DFL if you publish anything derived from it. The files contain real player and team names:
never publish them. data/external/ is git-ignored.

    python tools/fetch_sportec.py            # first match (J03WMX)
    python tools/fetch_sportec.py J03WN1     # another match id
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / "data" / "external" / "sportec"
API = "https://api.figshare.com/v2/articles/28196177"


def fetch(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError("refusing non-https url")
    with urllib.request.urlopen(url, timeout=600) as r:  # noqa: S310 (https only)
        return r.read()


def main() -> int:
    match = sys.argv[1] if len(sys.argv) > 1 else "J03WMX"
    meta = json.loads(fetch(API))
    lic = meta["license"]
    if lic["name"] != "CC BY" or "by/4.0" not in lic["url"]:
        print(f"unexpected licence {lic}: stopping", file=sys.stderr)
        return 1
    DEST.mkdir(parents=True, exist_ok=True)
    files = [f for f in meta["files"] if match in f["name"]]
    if not files:
        print(f"no files for match {match}", file=sys.stderr)
        return 1
    for f in files:
        out = DEST / f["name"]
        if out.exists() and out.stat().st_size == f["size"]:
            print(f"{f['name']}: already downloaded")
            continue
        print(f"{f['name']}: downloading {f['size'] / 1e6:.1f} MB ...", flush=True)
        out.write_bytes(fetch(f["download_url"]))
    print(f"Done: {DEST}. Licence: {lic['name']} ({lic['url']}). Cite Bassek et al. (2025) and credit the DFL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
