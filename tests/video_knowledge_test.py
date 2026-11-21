"""Offline test: the knowledge base is complete, licensed and indexed, and the planner prompt stays inside its token budget."""
import os, pathlib, sys
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "video-agent"))
os.chdir(REPO / "video-agent")
K = REPO / "video-agent" / "knowledge"
index = (K / "INDEX.md").read_text(encoding="utf-8")
skills = sorted(d.name for d in (K / "video-editing-skills" / "skills").iterdir())
assert len(skills) >= 26 and all((K / "video-editing-skills" / "skills" / n / "SKILL.md").exists() and f"`{n}`" in index for n in skills), "every skill is copied and indexed"
base = K / "ultimate-video-editor" / "ultimate-video-editor"
assert (base / "SKILL.md").exists() and len(list(base.rglob("*.md"))) == 32
assert all(f"`{f.relative_to(base).as_posix()}`" in index for f in base.rglob("*.md") if f.name != "SKILL.md"), "every Ultimate document is indexed"
for lic in ("video-editing-skills/LICENSE", "ultimate-video-editor/LICENSE.md", "sfx-kit/LICENSE", "../assets/sfxkit/LICENSE.txt"):
    assert (K / lic).exists(), lic
assert "MIT" in (K / "video-editing-skills/LICENSE").read_text(encoding="utf-8") and "CC0" in (K / "sfx-kit/LICENSE").read_text(encoding="utf-8")
assert not [p for p in K.rglob("*") if p.is_file() and p.suffix not in (".md", "") and p.name not in ("LICENSE",)], "documents only: no third-party scripts are copied"
for must in ("sound-design", "sfx-guide.md", "IN CODE", "IN THE PLANNER PROMPT", "reference only"):
    assert must in index
# the planner prompt stays small: 3 skills, and the SFX notes name only kinds and moments the planner can actually use
from agent import plan
from agent.common import load_config
prompt = plan.build_system_prompt(load_config())
assert len(prompt) < 12000, len(prompt)
notes = (REPO / "video-agent" / "skills" / "sfx-notes.md").read_text(encoding="utf-8")
assert all(k in notes for k in ("whoosh", "pop", "click", "riser", "impact", "at_word", "-14 LUFS")) and len(notes) < 2500
print("video knowledge test passed: 26+ skills and 32 Ultimate documents copied and indexed, licences present, documents only, planner prompt within budget")
