"""Whisper heard only the last word of the hook: captions must not fast-forward to it."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import captions as c

script = "Kya aapko lagta hai ki aapko sare customers Google se mil jayenge?"
spans = [(0.1, 4.0)]
heard = [{"text": "जाएंगे", "start": 3.1, "end": 3.9}]                 # the only word Whisper kept
old = c.align_script(script, heard)                                    # the old behaviour: everything squeezed in at/after 3.1 s
assert old[0]["start"] >= 3.0
filled = c.fill_gaps(heard, spans)
assert filled[0].get("ghost") and filled[0]["start"] == 0.1 and filled[0]["end"] == 3.1
new = c.align_script(script, filled)
assert new[0]["start"] < 0.4 and [w["text"] for w in new][-1] == "jayenge?"
assert all(a["start"] <= b["start"] for a, b in zip(new, new[1:])) and new[-1]["start"] >= 3.0
assert new[5]["start"] > 1.0 and new[8]["start"] < 3.2                   # the middle words are spread over the real time

# complete transcripts are left alone, silence is not filled, a mid-clip hole is filled
full = [{"text": "abc", "start": 0.2 + i * 0.5, "end": 0.6 + i * 0.5} for i in range(8)]
assert c.fill_gaps(full, [(0.1, 4.2)]) == full
assert c.fill_gaps(heard, [(3.0, 4.0)]) == heard                       # nothing audible before 3 s: no ghost
mid = [full[0], full[1], {"text": "abc", "start": 3.0, "end": 3.4}]
assert sum(1 for w in c.fill_gaps(mid, [(0.1, 3.5)]) if w.get("ghost")) == 1
print("video caption gap ok")
