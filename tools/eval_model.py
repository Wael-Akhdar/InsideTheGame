"""Evaluate the configured model (Azure OpenAI deployment, e.g. the fine-tuned GamePulse model) on grounded answers.

- commentator: overlay sentences for moments of simulated matches, in English, French, Spanish and Arabic; a sentence passes when every
  number in it is in the facts it was given (the app's fact-checker), and it is in the requested language (script check for Arabic);
- agents: analyst and coach questions answered with tool calls; an answer passes when every number comes from a tool result.

    python tools/eval_model.py --n 40       # needs AZURE_OPENAI_* in .env
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def commentator(n: int, rng: random.Random) -> dict:
    from gamepulse.agents.llm import LLM
    from gamepulse.agents.pipeline import ExplainerAgent, NarratorAgent, Viewer
    from gamepulse.agents.team import fact_check
    from gamepulse.engine.state import MatchState
    from gamepulse.feed import SimulatorFeed

    llm = LLM()
    rows, done = [], 0
    for s in range(50):
        feed = SimulatorFeed(seed=9100 + s)
        home, away = feed.teams
        teams = {home.id: home, away.id: away}
        state = MatchState(home.id, away.id)
        ex, na = ExplainerAgent(llm, teams), NarratorAgent(llm, teams)
        for tk in feed.ticks():
            if tk.frame:
                state.observe_frame(tk.t, tk.frame["poss"])
            for ev in tk.events:
                for m in state.ingest(ev):
                    if done >= n:
                        break
                    lang, mode = rng.choice(("en", "fr", "es", "ar")), rng.choice(("casual", "analyst"))
                    system, facts = na.prompt(m, ex.run(m, state), Viewer(mode=mode, lang=lang), state)
                    t0 = time.time()
                    out = llm.complete(system, facts)
                    if out is None:
                        continue
                    done += 1
                    chk = fact_check(out, [("facts", facts)], "")
                    lang_ok = bool(re.search(r"[؀-ۿ]", out)) if lang == "ar" else not re.search(r"[؀-ۿ]", out)
                    rows.append({"kind": m.kind, "lang": lang, "mode": mode, "grounded": chk["grounded"], "lang_ok": lang_ok,
                                 "seconds": round(time.time() - t0, 2), "text": out, "unsupported": chk["unsupported"]})
            if done >= n:
                break
        if done >= n:
            break
    return {"rows": rows}


async def agents(rng: random.Random) -> dict:
    from gamepulse.agents.pipeline import Orchestrator, Viewer
    from gamepulse.agents.team import ask
    from gamepulse.agents.tools import MatchContext
    from gamepulse.feed import SimulatorFeed

    feed = SimulatorFeed(seed=9300)
    orch = Orchestrator(*feed.teams)
    for tk in feed.ticks():
        orch.process_tick(tk, Viewer())
        if tk.t > 70 * 60:
            break
    ctx = MatchContext(orch.state, *feed.teams)
    qs = [("Who is on top right now?", ctx, "en"), ("Quels ont été les moments clés ?", ctx, "fr"), ("¿Quién ha dado más pases?", ctx, "es"),
          ("How does Low block 5-3-2 do against Possession 4-3-3 of a title contender?", None, "en"),
          ("Que donne Gegenpress 4-2-3-1 contre Direct 4-4-2 ?", None, "fr"), ("How realistic is the simulator?", None, "en")]
    rows = []
    for q, c, lang in qs:
        t0 = time.time()
        r = await ask(q, c, {}, lang)
        rows.append({"question": q, "lang": lang, "backend": r["backend"], "tools": [t["tool"] for t in r["tools"]], "grounded": r["grounded"],
                     "unsupported": r["unsupported"], "seconds": round(time.time() - t0, 1), "answer": r["answer"]})
    return {"rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    a = ap.parse_args()
    import gamepulse  # loads .env
    from gamepulse.agents.clients import backend

    rng = random.Random(1)
    com = commentator(a.n, rng)["rows"]
    ag = asyncio.run(agents(rng))["rows"]
    rate = lambda rows, k: f"{sum(r[k] for r in rows)}/{len(rows)}" if rows else "0/0"
    print(f"model backend: {backend()}")
    print(f"commentator: grounded {rate(com, 'grounded')}, right language {rate(com, 'lang_ok')}")
    for lang in ("en", "fr", "es", "ar"):
        sub = [r for r in com if r["lang"] == lang]
        print(f"  {lang}: grounded {rate(sub, 'grounded')}, right language {rate(sub, 'lang_ok')}")
    print(f"agents: grounded {rate(ag, 'grounded')}, called tools in {sum(bool(r['tools']) for r in ag)}/{len(ag)}")
    out = ROOT / "docs" / "MODEL_EVAL.json"
    out.write_text(json.dumps({"backend": backend(), "commentator": com, "agents": ag}, ensure_ascii=False, indent=1))
    print(f"details in {out}")


if __name__ == "__main__":
    main()
