"""Render with Remotion. (An editly fallback is planned, not built yet. See README.)"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .common import TEMPLATE, run


def render(manifest: dict, out_mp4: Path) -> None:
    (TEMPLATE / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    cmd = ["npx", "remotion", "render", "src/index.ts", "Main", out_mp4,
           "--overwrite", "--codec", "h264", "--crf", "24"]
    # Optional: point Remotion at an existing Chrome instead of downloading its own.
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        cmd += ["--browser-executable", os.environ["REMOTION_BROWSER_EXECUTABLE"]]
    run(cmd, cwd=TEMPLATE)
