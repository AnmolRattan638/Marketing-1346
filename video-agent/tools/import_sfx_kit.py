"""One-off importer: SFX Kit (CC0, https://github.com/... sfx-kit) -> video-agent/assets/sfxkit/.

    python tools/import_sfx_kit.py /path/to/sfx-kit-main

Converts every WAV (48 kHz, 24-bit) to a small MP3 WITHOUT changing its level (the kit's loudness scale is the point: soft stays quieter than hard)
and writes catalog.json with the fields the agent needs: sync point, loudness, how far to duck under speech, whether it masks a voice, length range
it fits. Re-running overwrites the output. The agent never reads the WAVs or the kit's own sounds.json; only catalog.json and the MP3s.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "sfxkit"


def main(kit: Path) -> None:
    data = json.loads((kit / "sounds.json").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = {}
    for s in data["sounds"]:
        src, dst = kit / s["file"], OUT / f"{s['id']}.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-c:a", "libmp3lame", "-q:a", "2", "-ar", "48000", str(dst)], check=True)
        avoid = [str(a) for a in s.get("avoid_for") or []]
        catalog[s["id"]] = {
            "category": s["category"],
            "duration": s["duration"],
            "channels": s.get("channels", 1),
            "sync_at": s["sync"]["at"],
            "meets": s["sync"]["meets"],
            "lufs": s["level"]["lufs"],
            "peak_dbtp": s["level"]["true_peak_dbtp"],
            "tier": s["level"].get("tier"),
            "under_voice_db": s.get("under_voiceover_db", -3),
            "avoid_voice": any(a.lower().startswith("on top of speech") for a in avoid),
            "intensity": (s.get("variant") or {}).get("intensity"),
            "fits": s.get("fits_seconds"),
            "tags": (s.get("tags") or [])[:6],
        }
    (OUT / "catalog.json").write_text(json.dumps({"source": "SFX Kit (CC0 1.0), converted to MP3, levels unchanged", "sounds": catalog}, separators=(",", ":")), encoding="utf-8")
    shutil.copyfile(kit / "LICENSE", OUT / "LICENSE.txt")
    total = sum(p.stat().st_size for p in OUT.glob("*.mp3"))
    print(f"{len(catalog)} sounds, {total / 1e6:.1f} MB of MP3 (the WAVs were {sum((kit / s['file']).stat().st_size for s in data['sounds']) / 1e6:.0f} MB)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
