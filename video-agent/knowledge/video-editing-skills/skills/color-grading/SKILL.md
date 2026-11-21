---
name: color-grading
description: Color correction and color grading for video - correction vs grade order, ASC CDL (slope/offset/power), white balance, exposure, contrast curves, log and HDR transforms (Apple Log, S-Log3, HLG), LUTs, named looks (teal and orange, film emulation, day for night, warm golden hour, bleach bypass, moody desaturated, pastel, vintage), skin tone protection, shot matching, grain, halation, vignette, done with ffmpeg or DaVinci Resolve. Use whenever footage needs a look, a fix, or consistency across clips.
---

# Color grading

Script: `scripts/grade.py IN OUT --look NAME [--strength 0.8] [--lut file.cube] [--compare grid.png]`
Lists looks with `--list`. Applies a look as an ffmpeg filter chain; `--compare` renders before/after stills of several looks so you (and the user) can choose by eye.

## 1. Order of operations (always)

1. **Input transform**: rotation/HDR/log → Rec.709 (Color Space Transform in Resolve, LUT or tonemap in ffmpeg). Never grade log footage directly by eye.
2. **Correction** (make it neutral and consistent): white balance → exposure → contrast → saturation. Goal: whites white, blacks black, skin natural, every shot matching.
3. **Look / creative grade**: hue shifts, split toning, curves, LUT at reduced strength.
4. **Finishing**: vignette, grain, halation, sharpening last.

Grade **per segment before concat** so you encode once. Same look for every clip in a sequence unless a change is a story beat (e.g. calm warm A → chaotic cold B).

## 2. Mental model: ASC CDL

Per channel: `out = (in × slope + offset) ^ power`, then saturation.
- slope → highlights/gain, offset → shadows/lift, power → midtones/gamma.
- Warm highlights: raise R slope, lower B slope slightly. Teal shadows: offset B and G up, R down.
- ffmpeg equivalents: `colorbalance` (shadows/mids/highs per RGB), `colorlevels`, `curves`, `eq` (contrast/brightness/saturation/gamma), `colortemperature`, `lut3d`, `colorchannelmixer`.

## 3. Looks (starting points — judge on frames, then adjust)

| Look | Feel | Key moves |
|---|---|---|
| `neutral-punch` | clean, social-ready | small S-curve, +8% sat, no hue shift |
| `teal-orange` | blockbuster, travel | teal shadows, warm highlights, protect skin (orange is skin's hue) |
| `warm-golden` | nostalgic, food, lifestyle | WB +300-600 K, lifted warm shadows, soft contrast |
| `cool-moody` | tech, night, drama | cooler WB, desaturated mids, deep but not crushed blacks |
| `film-kodak` | 2383/Portra-style print | rolled-off highlights, slight green-cyan shadows, warm mids, grain 4-8% |
| `bleach-bypass` | gritty, war, sport | high contrast, -40% saturation, silvery highlights |
| `pastel-matte` | aesthetic, minimal, fashion | lifted blacks (matte), lower contrast, -15% sat, pink/peach highs |
| `day-for-night` | fake night from day footage | -1.5 to -2 stops, blue cast, sat 0.3-0.5, crush sky, keep practical lights warm |
| `vintage-faded` | home video, 90s | faded blacks, yellow-green highs, chroma noise, softness |
| `bw-contrast` | timeless, documentary | luminance mix (R heavy for skin), strong S-curve, grain |
| `cyberpunk-neon` | night city, gaming | magenta-cyan split, high sat in highs, bloom on lights |

**Day for night reference**: DaVinci Resolve's "LMT Day for Night" works in ACES AP1 linear as `power 0.5 → slope (0.3, 0.5, 0.8) → power 2.2 → saturation 0.3`. To use it on Rec.709 footage, convert Rec.709 → linear AP1, apply, convert back, and bake it into a 33-point `.cube`. Lift very dark sources a little before the LUT.

## 4. LUTs

- Apply with `lut3d=file.cube:interp=tetrahedral`. Use at reduced strength by blending: `split[a][b];[b]lut3d=x.cube[g];[a][g]blend=all_expr='A*(1-0.7)+B*0.7'`.
- Technical LUTs (log→709) are exact, use 100%. Creative LUTs are seasoning, usually 40-80%.
- Never read a `.cube` file into context (tens of thousands of numbers). Look at its effect on a frame.
- Generate custom LUTs in Python: build a 33³ grid, apply your colour function with numpy, write `LUT_3D_SIZE 33` + rows (R fastest).

## 5. Skin tones

- Skin lies on the **skin-tone line** (~123° on a vectorscope, I-line) regardless of ethnicity; only luminance and saturation change.
- When pushing teal/cool looks, isolate skin (HSL key hue 0-50°, mid saturation) and hold it, or the face goes grey/green.
- Check every face shot in the grade at full size.

## 6. Matching shots

- Match exposure first (waveform/average luma), then WB (neutral object or white), then saturation.
- Quick numeric match: compare per-channel mean and std of a neutral region between shots; adjust slope/offset until within ~2-3%.
- Mixed cameras (phone + action cam + DSLR): convert all to Rec.709 first, then match to the hero camera.

## 7. Finishing touches

- **Grain**: `noise=alls=6:allf=t` (temporal). Add after scaling to the final size. 4K reels: grain survives compression better at slightly stronger values.
- **Vignette**: `vignette=PI/5` subtle. Avoid on content with text near edges.
- **Halation / bloom**: blur a highlight-only copy (threshold, gblur 20-40), tint red-orange, screen at 15-30%.
- **Sharpen**: `unsharp=5:5:0.6` once, at the end, at final size.
- **HDR to SDR**: see `ffmpeg-pipeline` tone-mapping.

## 8. In DaVinci Resolve

Node tree baseline: `CST in → WB/exposure → contrast/sat → secondary (skin) → look/LUT → CST out → grain/vignette`. Use Color Space Transform with input = camera log (e.g. Apple Log) and output = Rec.709 Gamma 2.4. Copy grades with stills or Color Groups (pre/post-clip). See `davinci-resolve`.

## 9. Verify

Before/after stills of 3+ shots (brightest, darkest, a face) side by side. Check: no clipped highlights on skin, blacks not crushed where detail matters, text overlays still readable, consistent look across cuts.
