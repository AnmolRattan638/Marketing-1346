import pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import scriptlessons as SL
SL.STATE = pathlib.Path(tempfile.mkdtemp()) / "l.json"
from src.agents import scriptwriter as sw
from src import marketingskills as ms
# hedged hype passes, unhedged still flagged
assert not sw.GENERIC.search("Ye chatbot aapke business ke liye game changer ban sakta hai")
assert sw.GENERIC.search("Ye chatbot game changer banega")
assert not ms.STOCK.search("ye game changer ban sakta hai") and ms.STOCK.search("ye game changer banega")
sheet = {"facts": [{"id": "f1", "claim": "53% of visits are abandoned if a page takes over 3 seconds", "figure": "53%"}], "keyword": "SITE"}
focus = {"name": "Website"}
style = {"id": "x", "beats": ["pain", "payoff"]}
def sc(hook, body): return {"beats": [{"beat": "pain", "line": hook, "facts": []}, {"beat": "payoff", "line": body, "facts": ["f1"]}]}
hook_bad = [x for x in sw.problems(sc("73 percent dukaan wale raat ko customer kho dete hain 87 baar", "Dhyan rakho 53% log slow page chhod dete hain kyunki 3 second bahut hote hain"), sheet, style, focus) if "not backed" in x]
assert not hook_bad, hook_bad                          # invented hook number is allowed
body_bad = [x for x in sw.problems(sc("Raat ko message aaya", "Dhyan rakho 91% log slow page chhod dete hain kyunki 3 second bahut hote hain"), sheet, style, focus) if "not backed" in x]
assert body_bad and body_bad[0].startswith("payoff"), body_bad   # an invented number in the body is still rejected
n = sw.finish(sc("87 baar message aaya", "x"), sheet, focus)["notes"]
assert n and "invented number" in n[0]
assert not sw.finish(sc("Raat ko message aaya", "x"), sheet, focus)["notes"]
print("open hook test passed")

# style-only remarks never block a script; real problems still do
assert sw.is_soft("lines are bare statements; use helping words") and sw.is_soft("meaning: payoff: x") and sw.is_soft("pain: too abstract; name a moment")
assert not sw.is_soft("payoff: number(s) ['91'] not backed by a cited fact") and not sw.is_soft("cta: must contain the keyword SITE")
print("soft style test passed")

# the cta must ask for a public comment of the keyword
focus_bot = {"id": "chatbot", "name": "WhatsApp chatbot", "dm_keyword": "BOT"}
mk = lambda cta: {"beats": [{"beat": "pain", "line": "Raat ko message aaya"}, {"beat": "cta", "line": cta}]}
assert any("comment" in x for x in ms.script_problems(mk("DM BOT likho, main checklist bhejunga"), focus_bot))
assert not any("ask the viewer to comment" in x for x in ms.script_problems(mk("Comment BOT likho, main checklist DM mein bhejunga"), focus_bot))
import pathlib as _p
assert all((_p.Path(__file__).resolve().parent.parent / "freebies" / f"{k}.md").exists() for k in ("website", "chatbot", "animated_ads", "lead_gen", "reel_scripts", "seo_blogs"))
print("comment cta test passed")
