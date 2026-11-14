"""Voice: Sarvam Bulbul (Hinglish, per-beat emotion) when voice_engine is "sarvam"; otherwise your cloned voice (Chatterbox, open source, MIT) when a reference clip exists, then Kokoro (CPU), then edge-tts; silence only for offline tests."""
from __future__ import annotations

import asyncio
import base64
import json
import os
from pathlib import Path

from .common import log, media_duration, run


def _wav_to_mp3(wav: Path, mp3: Path) -> None:
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-b:a", "128k", mp3])


def reference_clip() -> Path | None:
    """Your own voice sample. It is never committed (the repo is public): the workflow decodes the secret VOICE_REF_B64 to a file, or set VOICE_REF to a path."""
    path = os.environ.get("VOICE_REF")
    if path and Path(path).exists():
        return Path(path)
    b64 = (os.environ.get("VOICE_REF_B64") or "").strip()
    if not b64:
        return None
    out = Path(os.environ.get("RUNNER_TEMP") or "/tmp") / "voice_ref.ogg"
    out.write_bytes(base64.b64decode(b64))
    return out


_CHATTERBOX = {}


def _chatterbox(text: str, mp3: Path, vcfg: dict) -> None:
    """Zero-shot clone of the reference clip. Hindi/English use the multilingual model; sentences are spoken one at a time so a failure or an odd sentence stays small."""
    import re
    import numpy as np
    import soundfile as sf
    import torch

    ref = reference_clip()
    if ref is None:
        raise RuntimeError("no reference voice (set the secret VOICE_REF_B64 or VOICE_REF)")
    lang = (vcfg.get("chatterbox") or {}).get("language_id", "en")
    if "model" not in _CHATTERBOX:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        _CHATTERBOX["model"] = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    model = _CHATTERBOX["model"]
    parts = [t.strip() for t in re.split(r"(?<=[.!?\u0964])\s+", text) if t.strip()] or [text]
    pause = np.zeros(int(model.sr * 0.18), dtype="float32")
    chunks = []
    with torch.inference_mode():
        for t in parts:
            wav = model.generate(t, language_id=lang, audio_prompt_path=str(ref))
            chunks += [wav.squeeze().cpu().numpy().astype("float32"), pause]
    wav_path = mp3.with_suffix(".wav")
    sf.write(str(wav_path), np.concatenate(chunks), model.sr)
    _wav_to_mp3(wav_path, mp3)
    wav_path.unlink()


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


def _sarvam(text: str, mp3: Path, vcfg: dict, emotion: str | None = None, beat: str | None = None) -> None:
    from . import sarvam
    sarvam.synth(text, mp3, vcfg.get("sarvam") or {}, emotion, beat)


def prepare(texts: list[str], cfg: dict) -> None:
    """Engines that want the lines in another script (Sarvam: Devanagari + English) convert them once, up front."""
    if cfg.get("voice_engine") != "sarvam" or not os.environ.get("SARVAM_API_KEY"):
        return
    from . import plan, sarvam
    sarvam.prepare(texts, lambda prompt: json.loads(plan._call_groq([{"role": "system", "content": "You prepare text for a Hindi text-to-speech engine. Reply with JSON only."},
                                                                      {"role": "user", "content": prompt}], cfg)))


ENGINES = {"sarvam": _sarvam, "chatterbox": _chatterbox, "kokoro": _kokoro, "edge": _edge, "silent": _silent}


def synth(text: str, mp3: Path, cfg: dict, offline: bool, emotion: str | None = None, beat: str | None = None) -> float:
    """Write narration to mp3 and return its length in seconds."""
    vcfg = cfg["voices"][cfg.get("voice_language") or cfg["language"]]
    order = [cfg["voice_engine"], "edge"] if cfg["voice_engine"] == "sarvam" else [cfg["voice_engine"], "kokoro", "edge"]       # the chosen voice first; if it fails the reel still gets a voice
    if offline:
        order = ["silent"]
    last_err = None
    for name in dict.fromkeys(order):
        try:
            ENGINES[name](text, mp3, vcfg, emotion, beat) if name == "sarvam" else ENGINES[name](text, mp3, vcfg)
            if mp3.exists() and mp3.stat().st_size > 0:
                return media_duration(mp3)
        except Exception as e:
            last_err = e
            log(f"voice engine '{name}' failed: {e}")
    raise RuntimeError(f"all voice engines failed, last error: {last_err}")
