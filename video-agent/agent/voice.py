"""Voice: Kokoro (CPU) first, edge-tts as fallback, silence only for offline tests."""
from __future__ import annotations

import asyncio
from pathlib import Path

from .common import log, media_duration, run


def _wav_to_mp3(wav: Path, mp3: Path) -> None:
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-b:a", "128k", mp3])


def _kokoro(text: str, mp3: Path, vcfg: dict) -> None:
    import numpy as np  # imported lazily: only needed when Kokoro is installed
    import soundfile as sf
    from kokoro import KPipeline

    pipe = KPipeline(lang_code=vcfg["kokoro"]["lang"])
    chunks = [audio for _, _, audio in pipe(text, voice=vcfg["kokoro"]["voice"])]
    wav = mp3.with_suffix(".wav")
    sf.write(str(wav), np.concatenate(chunks), 24000)
    _wav_to_mp3(wav, mp3)
    wav.unlink()


def _edge(text: str, mp3: Path, vcfg: dict) -> None:
    import edge_tts

    asyncio.run(edge_tts.Communicate(text, vcfg["edge"]).save(str(mp3)))


def _silent(text: str, mp3: Path, vcfg: dict) -> None:
    seconds = max(2.0, len(text.split()) / 2.6)
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
         "anullsrc=r=24000:cl=mono", "-t", f"{seconds:.2f}", "-b:a", "64k", mp3])


ENGINES = {"kokoro": _kokoro, "edge": _edge, "silent": _silent}


def synth(text: str, mp3: Path, cfg: dict, offline: bool) -> float:
    """Write narration to mp3 and return its length in seconds."""
    vcfg = cfg["voices"][cfg["language"]]
    order = [cfg["voice_engine"], "edge"]
    if offline:
        order = ["silent"]
    last_err = None
    for name in dict.fromkeys(order):
        try:
            ENGINES[name](text, mp3, vcfg)
            if mp3.exists() and mp3.stat().st_size > 0:
                return media_duration(mp3)
        except Exception as e:
            last_err = e
            log(f"voice engine '{name}' failed: {e}")
    raise RuntimeError(f"all voice engines failed, last error: {last_err}")
