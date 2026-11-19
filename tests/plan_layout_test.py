import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import plan
p = {"scenes": [{"graphic": {"type": "punch", "heading": "Raat 11 baje"}}, {"graphic": {"heading": "Dekho", "kicker": "k"}},
                {"graphic": {"items": ["a", "b"]}}, {"graphic": {"mock": {"type": "checklist", "items": ["x"]}}}, {"graphic": {}}, {"graphic": {"layout": "title", "heading": "ok"}}]}
out = plan.tidy_plan(p)["scenes"]
assert [s.get("graphic", {}).get("layout") for s in out] == ["punch", "title", "strike", "step", None, "title"], out
print("plan layout test passed")
