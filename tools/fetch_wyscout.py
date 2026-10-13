"""Download the public Wyscout soccer event dataset (Pappalardo et al., 2019) into data/external/wyscout/.

Licence: CC BY 4.0. If you use it, cite:
  Pappalardo et al. (2019) "A public data set of spatio-temporal match events in soccer competitions",
  Scientific Data 6:236, https://www.nature.com/articles/s41597-019-0247-7

The data is NOT part of this repository (data/external/ is git-ignored). Run:  python tools/fetch_wyscout.py
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / "data" / "external" / "wyscout"
API = "https://api.figshare.com/v2/articles/{id}"
ARTICLES = {"matches.zip": 7770422, "events.zip": 7770599}  # figshare article ids (both CC BY 4.0)


def fetch(url: str) -> bytes:
    if not url.startswith("https://"):
        raise ValueError(f"refusing non-https url {url}")
    with urllib.request.urlopen(url, timeout=300) as r:  # noqa: S310 (https only, fixed hosts)
        return r.read()


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    for name, art in ARTICLES.items():
        out = DEST / name
        meta = json.loads(fetch(API.format(id=art)))
        if meta["license"]["name"] != "CC BY 4.0":
            print(f"licence of {name} is {meta['license']['name']}, not CC BY 4.0: stopping", file=sys.stderr)
            return 1
        f = meta["files"][0]
        if out.exists() and out.stat().st_size == f["size"]:
            print(f"{name}: already downloaded")
            continue
        print(f"{name}: downloading {f['size'] / 1e6:.1f} MB ...")
        out.write_bytes(fetch(f["download_url"]))
    print(f"Done. Data in {DEST}. Remember to cite Pappalardo et al. (2019), CC BY 4.0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
