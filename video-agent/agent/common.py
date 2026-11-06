"""Shared helpers: paths, config, subprocess and ffprobe wrappers."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "template"
SKILLS = ROOT / "skills"
# Everything the Remotion manifest points at is staged here, so staticFile()
# paths in the manifest look like "assets/run/narration/s1.mp3".
WORK = TEMPLATE / "public" / "assets" / "run"


def load_config() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def log(msg: str) -> None:
    print(f"[agent] {msg}", flush=True)


def run(cmd, cwd=None, capture=False) -> subprocess.CompletedProcess:
    cmd = [str(c) for c in cmd]
    log("$ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture)
    if p.returncode != 0:
        tail = ((p.stderr or "") + (p.stdout or ""))[-1500:] if capture else ""
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{tail}")
    return p


def media_duration(path: Path) -> float:
    p = run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture=True,
    )
    return float(p.stdout.strip())
