---
name: ffmpeg-pipeline
description: Production-correct ffmpeg pipeline for scripted video editing - probing, rotation and VFR fixes, HDR/HLG/Dolby Vision to SDR tone mapping, Apple Log, per-segment extraction, lossless concat, xfade transitions, overlay timing, PNG/alpha overlays, burning subtitles, speed changes, upscaling, and export presets for Instagram, TikTok, YouTube, and masters. Use whenever an edit is rendered with ffmpeg or a Python build script.
---

# ffmpeg pipeline

Helper scripts live in `scripts/` next to this file. Run them with `python <skill_dir>/scripts/<name>.py`.

- `probe.py IN...` — one-line summary per file (size, fps, rotation, HDR, duration, audio).
- `export.py IN OUT --preset instagram|tiktok|shorts|youtube|master|preview` — final encode with the right settings.
- `frames.py IN OUTDIR --times 0.5,3,7.2` or `--every 1` — grab check frames.

## 1. Probe and normalise first

Phone footage traps:
- **Rotation**: iPhone stores landscape pixels + a rotation flag. ffmpeg auto-rotates on decode (`-noautorotate` disables). OpenCV `VideoCapture` may **not** — check `frame.shape` and rotate yourself.
- **VFR**: phones record variable frame rate. Convert to CFR on extract: `-vf fps=30` (or `-r 30` output) so frame math is exact.
- **HDR**: `color_transfer=arib-std-b67` (HLG) or `smpte2084` (PQ). Untouched, it looks washed out/grey in SDR. Tone-map:

```bash
# HDR (HLG or PQ) -> SDR Rec.709, CPU zscale path
-vf "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
```
`hable` = filmic; `mobius` keeps more saturation. If zscale is missing, use `libplacebo` (`-vf libplacebo=tonemapping=bt.2390:colorspace=bt709:color_primaries=bt709:color_trc=bt709`).

- **Apple Log / camera log**: apply the manufacturer's Log → Rec.709 LUT first (`lut3d=AppleLog_to_Rec709.cube`), then grade.
- **10-bit sources**: keep 10-bit through intermediates (`-pix_fmt yuv422p10le` ProRes or `yuv420p10le` x265) when grading heavily; convert to 8-bit `yuv420p` only at final export for social.

## 2. Architecture of a build script

```
sources/ (never modified)
edit/
  build.py          # regenerates everything from sources + data files
  edl.json          # [{src, in, out, speed, grade, transition}]
  segments/         # one graded, normalised file per EDL entry (lossless-ish)
  overlays/         # PNG / PNG-sequence / ProRes 4444 / WebM alpha
  preview.mp4, final.mp4
```

Rules:
1. **Per-segment extract** with all per-clip work (trim, speed, scale/crop, grade, fps) in one pass → intermediate at `-crf 10` (x264) or ProRes 422 HQ.
2. **Concat** segments with the concat demuxer and `-c copy` when no transitions are needed (all segments must share codec, resolution, fps, pix_fmt, timebase).
3. **Overlays and text** in one final pass over the concatenated video, then encode once to the delivery spec.
4. Audio is built separately (music + SFX + dialogue → one WAV), then muxed in the final pass.

### Accurate trim

```bash
# -ss before -i is fast and frame-accurate when re-encoding (ffmpeg >= 2.1)
ffmpeg -ss 12.40 -i IN.mov -t 2.333 -vf "fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920" \
  -c:v libx264 -crf 10 -preset medium -pix_fmt yuv420p -an seg_003.mp4
```
Never use `-c copy` for trims that must be frame-accurate (it snaps to keyframes).

### Fill 9:16 from 16:9

- **Crop** (cover): `scale=-2:1920,crop=1080:1920:(iw-1080)*X:0` with X 0..1 to choose the subject position (track it if the subject moves).
- **Blurred background** (contain): `split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:2[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2`

### Concat

```bash
# list.txt:  file 'segments/seg_001.mp4'  (one per line)
ffmpeg -f concat -safe 0 -i list.txt -c copy joined.mp4
```

### Transitions with xfade

```bash
ffmpeg -i a.mp4 -i b.mp4 -filter_complex \
 "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=4.5,format=yuv420p[v]; \
  [0:a][1:a]acrossfade=d=0.5[a]" -map "[v]" -map "[a]" out.mp4
```
`offset` = first clip duration − transition duration. Types: fade, fadeblack, fadewhite, wipeleft, slideup, smoothleft, circleopen, radial, zoomin, hblur, pixelize, dissolve… Chain offsets cumulatively for many clips (each xfade shortens the total by its duration).

### Overlays

```bash
# static PNG (full-frame, transparent) for the whole video — no -loop needed
[0:v][1:v]overlay=0:0:format=auto
# time-limited
overlay=0:0:enable='between(t,2.0,5.5)'
# animated overlay clip starting at T in the output
[1:v]setpts=PTS-STARTPTS+T/TB[ov];[0:v][ov]overlay=0:0:eof_action=pass
```
Alpha overlays: PNG sequence (`-framerate 30 -i ov/%04d.png`), ProRes 4444 (`-c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le`), or VP9 WebM (`-c:v libvpx-vp9 -pix_fmt yuva420p`).
Don't `-loop 1` a 4K RGBA PNG for long videos; it eats RAM. A single-image input is repeated by overlay automatically.

Piping raw frames from Python (PIL/OpenCV compositing) into ffmpeg:
```python
p = subprocess.Popen(["ffmpeg","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r","30","-i","-",
                      "-c:v","libx264","-crf","12","-pix_fmt","yuv420p","out.mp4"], stdin=subprocess.PIPE)
p.stdin.write(frame.tobytes())   # numpy uint8 HxWx3, per frame
```
Read source frames the same way (`-f rawvideo -pix_fmt rgb24 -`), which avoids OpenCV rotation and codec issues.

### Speed

- Constant: `setpts=PTS/2` (2x) + `atempo=2.0` (atempo range 0.5-100; chain for more).
- Smooth slow-mo from 30 fps: `minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:vsbmc=1`, then `setpts=2*PTS`. Check for warping on edges/hands.
- Variable speed ramps: render frame-by-frame from a time-map (see `beat-sync`), never stack many `setpts` expressions.

### Subtitles (last)

```bash
-vf "subtitles=captions.ass:fontsdir=fonts"     # ASS gives full styling control
```

## 3. Export presets

| Target | Video | Audio | Notes |
|---|---|---|---|
| Instagram Reels / TikTok / Shorts | 1080x1920 (or 2160x3840) H.264 High, 30 fps, CRF 16-18, `-maxrate 25M -bufsize 50M`, yuv420p | AAC 48 kHz 256-320k | `-movflags +faststart`; platforms re-encode, so feed a high-quality file |
| YouTube 16:9 | 3840x2160 or 1920x1080, H.264 CRF 16 or HEVC CRF 18, source fps | AAC 48 kHz 320k | upload 4K even for 1080p content to get the better VP9/AV1 encode |
| Master | ProRes 422 HQ or x264 CRF 10 / x265 CRF 14 `-tag:v hvc1` | PCM 24-bit 48 kHz | archive |
| Preview | 720p, CRF 28, `-preset veryfast` | AAC 128k | fast iteration |

Always add `-pix_fmt yuv420p` for social (10-bit or 4:2:2 can fail or look wrong after upload) and `-color_primaries bt709 -color_trc bt709 -colorspace bt709` to tag SDR correctly.

## 4. Verify

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt -show_entries format=duration -of compact out.mp4
ffmpeg -i out.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -12
ffmpeg -i out.mp4 -vf "select='gt(scene,0.3)',showinfo" -f null - 2>&1 | grep pts_time   # where cuts actually are
```
