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
assert "1.2.3" in _st.clean("version 1.2.3")
print("decimals ok")

# dates are read as dates, not decimals or ranges
assert _st.clean("Date 12.05.2026") == "Date twelve May twenty twenty six."
assert "twelve May twenty twenty six" in _st.clean("12/05/2026") and "thirty one December twenty twenty five" in _st.clean("31.12.25")
assert "twenty two November" in _st.clean("Aaj 22.11 ko") and "fifteen August" in _st.clean("15.08 ko")
assert "ten point one two" in _st.clean("10.12 ka offer"), "a day of 12 or less is ambiguous: stays a decimal"
assert "32.13.2026" in _st.clean("32.13.2026") and "10 to 15" in _st.clean("10-15 din")
print("dates ok")
