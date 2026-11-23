"""Offline test: decimals are spoken as English words (2.5 -> two point five)."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
# decimals: "2.5" is read "two point five", never "do point panch"
from agent import speech_text as _st
assert _st.clean("2.5 lakh").startswith("two point five lakh"), _st.clean("2.5 lakh")
assert "zero point five" in _st.clean("Take 0.5 sec")
assert "one point two five" in _st.clean("1.25 crore")
assert "three point five times" in _st.clean("3.5x")
assert "two point five percent" in _st.clean("2.5%")
assert "12.05.2026" in _st.clean("Date 12.05.2026") and "1.2.3" in _st.clean("version 1.2.3")
print("decimals ok")
