"""Sarvam voice test: speaks one line per emotion (hook, pain, payoff, CTA) through the same path the reel uses, and sends the clips to Telegram.
Run from video-agent/ with SARVAM_API_KEY (+ a Groq key for the Devanagari conversion; without it the Roman text is spoken)."""
import json
from pathlib import Path

from agent import notify, voice
from agent.common import load_config, log, media_duration

LINES = [
    ("1-hook-curious", "curious", "pain", "Raat 11 baje customer ne WhatsApp kiya, aur jawab subah mila. Tab tak woh dusri dukaan chala gaya."),
    ("2-pain-empathetic", "empathetic", "poke", "Aap din bhar kaam mein busy rehte ho, aur enquiries chhoot jaati hain."),
    ("3-payoff-excited", "excited", "payoff", "Ek chhota sa bot pehle paanch minute mein reply kare, toh leads ka pura khel badal jaata hai!"),
    ("4-cta-warm", "warm", "cta", "Comment BOT karo, main aapko 3-step setup bhejunga."),
]
cfg = load_config()
out = Path("runs/sarvam_test"); out.mkdir(parents=True, exist_ok=True)
voice.prepare([t for _, _, _, t in LINES], cfg)
report = []
for name, emotion, beat, text in LINES:
    mp3 = out / f"{name}.mp3"
    try:
        secs = voice.synth(text, mp3, cfg, False, emotion, beat)
        report.append(f"{name}: {secs:.1f}s")
        notify.send_audio(mp3, f"{name} ({emotion})")
    except Exception as e:
        report.append(f"{name}: FAILED {str(e)[:200]}")
    log(report[-1])
notify.send_message("Sarvam voice test finished.\n" + "\n".join(report))
