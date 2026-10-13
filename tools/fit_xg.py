"""Fit the shot-quality model used for feeds without expected goals (Wyscout) on the public Wyscout shots.

Logistic regression on shot geometry: distance, visible goal angle, header and free-kick flags. Penalties use their observed rate.
Data: Pappalardo et al. (2019), CC BY 4.0, read from data/external/wyscout/ (run tools/fetch_wyscout.py first).
Only the fitted coefficients are kept in gamepulse/feed/xg.py. Run:  python tools/fit_xg.py
"""
from __future__ import annotations

import json
import math
import zipfile
from pathlib import Path

import numpy as np

ZIP = Path(__file__).resolve().parents[1] / "data" / "external" / "wyscout" / "events.zip"
LEAGUES = ("England", "France", "Germany", "Italy", "Spain")


def features(x: float, y: float, header: bool, freekick: bool) -> list[float]:
    dx, dy = (100 - x) * 1.05, abs(50 - y) * 0.68
    dist = max(3.0, math.hypot(dx, dy))
    ang = math.atan2(7.32 * dx, dx * dx + dy * dy - 3.66 ** 2 + 1e-9)
    ang = ang if ang > 0 else ang + math.pi
    return [1.0, dist / 10, ang, float(header), float(freekick)]


def load() -> dict[str, tuple[np.ndarray, np.ndarray]]:
    z = zipfile.ZipFile(ZIP)
    out = {}
    for lg in LEAGUES:
        X, Y, pen = [], [], []
        for e in json.loads(z.read(f"events_{lg}.json")):
            n, sub = e["eventName"], e["subEventName"]
            if n == "Shot" or (n == "Free Kick" and sub in ("Free kick shot", "Penalty")):
                if sub == "Penalty":
                    pen.append(101 in {t["id"] for t in e["tags"]})
                    continue
                tg = {t["id"] for t in e["tags"]}
                p = e["positions"][0]
                X.append(features(p["x"], p["y"], 403 in tg, sub == "Free kick shot"))
                Y.append(101 in tg)
        out[lg] = (np.array(X), np.array(Y, float), np.array(pen, float))
    return out


def fit(X: np.ndarray, y: np.ndarray, iters: int = 50) -> np.ndarray:
    w = np.zeros(X.shape[1])
    for _ in range(iters):  # Newton-Raphson / IRLS
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (y - p)
        H = (X * (p * (1 - p))[:, None]).T @ X + 1e-6 * np.eye(X.shape[1])
        w += np.linalg.solve(H, g)
    return w


def logloss(w, X, y) -> float:
    p = np.clip(1 / (1 + np.exp(-X @ w)), 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def main() -> None:
    data = load()
    train = [lg for lg in LEAGUES if lg != "Spain"]
    Xtr, ytr = np.vstack([data[l][0] for l in train]), np.concatenate([data[l][1] for l in train])
    Xte, yte = data["Spain"][0], data["Spain"][1]
    w = fit(Xtr, ytr)
    base = np.full(len(yte), ytr.mean())
    print(f"held-out Spain: log-loss {logloss(w, Xte, yte):.4f} vs constant {-np.mean(yte*np.log(ytr.mean())+(1-yte)*np.log(1-ytr.mean())):.4f}")
    p = 1 / (1 + np.exp(-Xte @ w))
    print(f"held-out Spain: predicted goals {p.sum():.0f}, actual {yte.sum():.0f}")
    Xall, yall = np.vstack([data[l][0] for l in LEAGUES]), np.concatenate([data[l][1] for l in LEAGUES])
    w = fit(Xall, yall)
    pen = np.concatenate([data[l][2] for l in LEAGUES])
    print("FINAL coefficients [1, dist/10, angle, header, free kick]:", [round(float(v), 4) for v in w])
    print(f"penalty conversion: {pen.mean():.3f} over {len(pen)}")


if __name__ == "__main__":
    main()
