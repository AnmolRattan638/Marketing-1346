"""Import the Locomotion template pack (zip contents) into template/src/locomotion with the website's colours only.

    python scripts/import_locomotion.py /path/to/locomotion-main

Every colour literal in the pack is mapped to a THEME token (brand palette), so a template can never show a colour that is not the brand's.
The pack is a LIGHT design: it is inverted onto the brand's dark palette (white surfaces -> navy card, near-black text -> light text, any bright
accent -> gold). Re-run after adding/updating templates; the output is committed."""
from __future__ import annotations

import colorsys
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "template" / "src" / "locomotion"
HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGBA = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([0-9.]+)\s*)?\)")
GOLDS = ["accent", "accent2", "hot"]


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    h = "".join(c * 2 for c in h) if len(h) == 3 else h
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


DARK = False      # set per template: a template whose own background is dark keeps its polarity (dark stays dark) instead of being inverted


def is_dark_native(src: str) -> bool:
    """True when the template's first background literal (default bgColor or backgroundColor) is near-black."""
    for m in re.finditer(r"(?:bgColor\s*=\s*|backgroundColor:\s*)['\"](#[0-9a-fA-F]{3,6})['\"]", src):
        r, g, b = _rgb(m.group(1))
        return colorsys.rgb_to_hls(r / 255, g / 255, b / 255)[1] < 0.25
    return False


def token(r: int, g: int, b: int) -> str:
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if s > 0.35 and 0.2 < l < 0.85:                         # a bright accent -> gold family, by hue so two accents stay distinct
        return GOLDS[int(h * 6) % 3]
    if DARK:
        if l < 0.1:
            return "bgTop"
        if l < 0.2:
            return "card"
        if l < 0.3:
            return "cardEdge"
        return "muted" if l < 0.8 else "text"
    if l >= 0.995:
        return "card"
    if l >= 0.94:
        return "bgBottom"
    if l >= 0.8:
        return "cardEdge"
    if l >= 0.3:
        return "muted"
    return "text"


def _sub_in_string(body: str, in_template: bool) -> tuple[str, bool]:
    """Replace colours in the inside of a string literal. Returns (new body with ${THEME.x} placeholders, changed)."""
    changed = False

    def hexrep(m):
        nonlocal changed
        changed = True
        return "${THEME.%s}" % token(*_rgb(m.group(0)))

    def rgbarep(m):
        nonlocal changed
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        a = m.group(4)
        if (r, g, b) == (0, 0, 0):
            rgb = "6,8,13"                                   # brand black
        elif (r, g, b) == (255, 255, 255):
            rgb = "232,235,242"                              # brand text
        else:
            rgb = "240,192,64"
        changed = True
        return f"rgba({rgb},{a if a is not None else 1})"
    body = RGBA.sub(rgbarep, body)
    body = HEX.sub(hexrep, body)
    return body, changed


STR = re.compile(r"""(?P<q>['"`])(?P<b>(?:\\.|(?!(?P=q)).)*?)(?P=q)""", re.S)


def recolor(src: str) -> str:
    def rep(m):
        q, body = m.group("q"), m.group("b")
        if not (HEX.search(body) or RGBA.search(body)):
            return m.group(0)
        new, changed = _sub_in_string(body, q == "`")
        if not changed:
            return m.group(0)
        attr = m.start() > 0 and m.string[m.start() - 1] == "=" and m.string[m.start() - 2:m.start()] != "=="      # JSX attribute: stroke="#fff" -> stroke={THEME.x}
        whole = re.fullmatch(r"\$\{THEME\.(\w+)\}", new)
        if whole and q != "`":
            out = f"THEME.{whole.group(1)}"
        else:
            if q != "`":
                new = new.replace("\\'", "'")
            out = "`" + new.replace("`", "\\`") + "`" if q != "`" else "`" + new + "`"
        return "{" + out + "}" if attr and q != "`" else out
    out = STR.sub(rep, src)
    out = re.sub(r"(['\"])\$\{THEME\.(\w+)\}\1", r"THEME.\2", out)          # a string literal nested inside a ${...} of a template literal
    out = out.replace("rgba(0,0,0,${", "rgba(6,8,13,${")           # backdrop with a computed alpha
    # a computed purple rgba in one template -> gold
    out = re.sub(r"rgba\(\$\{trackColor \* 147\}, \$\{trackColor \* 51\}, \$\{trackColor \* 234\}, ", "rgba(240,192,64, ", out)
    return out


def main(root: str) -> None:
    src = Path(root) / "src"
    (OUT / "templates").mkdir(parents=True, exist_ok=True)
    ids = []
    for d in sorted((src / "templates").iterdir()):
        f = d / "Composition.tsx"
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        text = text.replace("from '@/lib/useStyle'", "from '../useStyle'")
        global DARK
        DARK = is_dark_native(text)
        text = recolor(text)
        DARK = False
        text = "// Imported from the Locomotion pack by scripts/import_locomotion.py (colours remapped to the brand THEME). Do not edit by hand.\n" \
               "import React from 'react'\nimport { THEME } from '../../graphics/theme'\n" + text
        (OUT / "templates" / f"{d.name}.tsx").write_text(text, encoding="utf-8")
        ids.append(d.name)
    # style variants: computed lazily so THEME (mutated per run by applyTheme) is read at render time
    styles = (src / "lib" / "styles.ts").read_text(encoding="utf-8")
    styles = recolor(styles).replace("export const styleVariants: StyleVariant[] = [", "export const makeVariants = (): StyleVariant[] => [")
    styles = styles.replace("return styleVariants.find((s) => s.id === id) ?? styleVariants[0]", "const all = makeVariants()\n  return all.find((s) => s.id === id) ?? all[0]")
    (OUT / "styles.ts").write_text("import { THEME } from '../graphics/theme'\n" + styles, encoding="utf-8")
    use = (src / "lib" / "useStyle.ts").read_text(encoding="utf-8").replace("from './styles'", "from './styles'")
    (OUT / "useStyle.ts").write_text(use, encoding="utf-8")
    comps = {d: "".join(p.capitalize() for p in d.split("-")) for d in ids}
    reg = ["// generated by scripts/import_locomotion.py", "import type React from 'react'"]
    reg += [f"import {{ {c} }} from './templates/{d}'" for d, c in comps.items()]
    reg += ["", "// eslint-disable-next-line @typescript-eslint/no-explicit-any", "export const LOCOMOTION: Record<string, React.FC<any>> = {"]
    reg += [f"  '{d}': {c}," for d, c in comps.items()] + ["}", ""]
    (OUT / "registry.ts").write_text("\n".join(reg), encoding="utf-8")
    print(f"imported {len(ids)} templates -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
