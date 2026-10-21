"""Assemble the demo: the recording (raw/*.webm) + the voice lines placed at the offsets of raw/timeline.json -> GamePulse_demo.mp4"""
import json, subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np

from record import H, W, mark_value

HERE = Path(__file__).resolve().parent
LEAD = 0.25  # the voice starts just after the shot appears

video = next((HERE / "raw").glob("*.webm"))
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def find_marks(keys: list[str]) -> dict[str, float]:
    """When each voice line's colour mark first shows in the recording (the recorder's frames can lag the clock under load)."""
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(video), "-vf", f"fps=30,crop=8:8:{W - 12}:{H - 12}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    px = np.frombuffer(raw, np.uint8).reshape(-1, 64, 3).mean(axis=1)
    found = {}
    for i, key in enumerate(keys, start=1):
        hit = np.where((np.abs(px[:, 0] - mark_value(i)) < 7) & (px[:, 1] < 40) & (px[:, 2] > 210))[0]
        if len(hit):
            found[key] = round(hit[0] / 30, 2)
    return found


clock = json.loads((HERE / "raw" / "timeline.json").read_text())
marks = find_marks(list(clock))
timeline = {k: marks.get(k, t) for k, t in clock.items()}
print({k: (clock[k], marks.get(k)) for k in clock})
cmd, parts = [FFMPEG, "-y", "-i", str(video)], []
for i, (key, t) in enumerate(timeline.items(), start=1):
    cmd += ["-i", str(HERE / "voice" / f"{key}.mp3")]
    ms = int((t + LEAD) * 1000)
    parts.append(f"[{i}:a]adelay={ms}|{ms}[a{i}]")
n = len(timeline)
mix = ";".join(parts) + ";" + "".join(f"[a{i}]" for i in range(1, n + 1)) + f"amix=inputs={n}:normalize=0,loudnorm=I=-16:TP=-1.5[a]"
cmd += ["-filter_complex", f"[0:v]drawbox=x={W - 16}:y={H - 16}:w=16:h=16:color=0x0b0614:t=fill,scale=1920:1080:flags=lanczos,fps=30[v];{mix}", "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest",
        "-movflags", "+faststart", str(HERE / "GamePulse_demo.mp4")]
subprocess.run(cmd, check=True, capture_output=True)
print("ok")
