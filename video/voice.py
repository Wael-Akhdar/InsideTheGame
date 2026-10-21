"""Voice-over of the demo video: one line per shot, synthesized with a Microsoft neural voice (edge-tts).

    python video/voice.py        -> video/voice/<key>.mp3 and video/voice/durations.json (read by record.py)
"""
import asyncio, json, subprocess
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
OUT = HERE / "voice"
VOICE, RATE = "en-GB-RyanNeural", "+6%"

LINES = {
    "title": "GamePulse. Feel the match, understand the moment.",
    "problem": "Football stories don't end with the scoreline. TV shows the goal, not why it happened, or what a coach should do next.",
    "live": "Synthetic match events stream in live. Our agents interpret them: possession, expected goals, pressing, momentum, "
            "and detect the moments that matter.",
    "insight": "Each insight explains why it matters, cites the events behind it, and is exported as timestamped overlay JSON "
               "for broadcast graphics.",
    "lang": "And every fan gets their own match. Switch to French mid-match: the whole app and the AI follow. Spanish and Arabic too.",
    "analyst": "Ask the match analyst. A Microsoft Agent Framework agent calls the engine's tools, "
               "and a fact-checker verifies every number before you see it.",
    "coachlive": "Coaches can act live. Describe the situation in plain words: our fine-tuned model turns it into rules the simulator applies.",
    "lab": "In the Tactic Lab, test a tactic against every style, at your level and your opponent's, over many simulated matches.",
    "coach": "Or ask the tactics coach. It answers by running the simulations itself, with the numbers to prove it.",
    "realism": "And you can trust it. The simulator is validated against more than a thousand real matches and real tracking data.",
    "strength": "A stronger team plays like a stronger team, as in real leagues.",
    "arch": "Built on Microsoft Agent Framework, a model fine-tuned in Microsoft Foundry, an MCP server, and Azure Container Apps.",
    "end": "GamePulse. Try it live, today.",
}


def duration(f: Path) -> float:
    out = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", str(f)], capture_output=True, text=True).stderr
    h, m, s = out.split("Duration: ")[1].split(",")[0].split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


async def main():
    import edge_tts

    OUT.mkdir(exist_ok=True)
    for k, text in LINES.items():
        await edge_tts.Communicate(text, VOICE, rate=RATE).save(str(OUT / f"{k}.mp3"))
    durs = {k: round(duration(OUT / f"{k}.mp3"), 2) for k in LINES}
    (OUT / "durations.json").write_text(json.dumps(durs, indent=1))
    print(durs, "total", round(sum(durs.values()), 1))


if __name__ == "__main__":
    asyncio.run(main())
