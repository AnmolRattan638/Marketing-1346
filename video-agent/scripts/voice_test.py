"""Voice test: speaks three lines in YOUR cloned voice, times each, and sends the clips to Telegram so you can listen and choose.
Run from video-agent/ with VOICE_REF_B64 (or VOICE_REF) set."""
import time
from pathlib import Path

from agent import notify, voice
from agent.common import log, media_duration

LINES = {
    "1-hindi": ("hi", "नमस्ते! मैं अनमोल हूँ, और मैं छोटे बिज़नेस के लिए वेबसाइट बनाता हूँ।"),
    "2-hinglish-roman": ("hi", "Namaste! Main Anmol hoon, aur main chhote business ke liye website banata hoon."),
    "3-english": ("en", "Most small businesses lose customers because their website is slow on a phone."),
}
out = Path("runs/voice_test"); out.mkdir(parents=True, exist_ok=True)
report = []
for name, (lang, text) in LINES.items():
    mp3 = out / f"{name}.mp3"
    t0 = time.time()
    try:
        voice._chatterbox(text, mp3, {"chatterbox": {"language_id": lang}})
        took, secs = time.time() - t0, media_duration(mp3)
        report.append(f"{name}: {secs:.1f}s of audio in {took:.0f}s")
        log(report[-1])
        notify.send_audio(mp3, f"{name}  ({took:.0f}s to make)")
    except Exception as e:
        report.append(f"{name}: FAILED {str(e)[:200]}")
        log(report[-1])
notify.send_message("Voice test finished.\n" + "\n".join(report))
