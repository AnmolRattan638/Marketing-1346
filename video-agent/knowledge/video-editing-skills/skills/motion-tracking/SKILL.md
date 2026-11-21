---
name: motion-tracking
description: Computer-vision helpers for editing with OpenCV - global camera-motion analysis (find pans/rotations vs static parts), stabilization with smoothed camera paths and masked foregrounds, point and template tracking, planar/affine text attachment to objects, ellipse/edge fitting for rims and screens, optical flow speed for motion-driven SFX, chroma keying green screen, and attaching graphics, glows or 3D overlays that stick to footage. Use when text or graphics must follow something in the shot, footage needs stabilizing, or an edit decision depends on motion.
---

# Motion tracking and analysis

Scripts in `scripts/` (need `opencv-python numpy scipy`):
- `camera_motion.py IN out.json` — per-frame rotation and translation of the camera (LK flow + RANSAC similarity), with a 0.5 s summary to find moves vs static parts.
- `stabilize.py IN OUT [--sigma 14] [--mask-hsv h0,h1,s0,v0]` — smooth-path stabilization; optional colour mask keeps a moving subject from biasing the estimate.
- `track_point.py IN out.json --x X --y Y --t T [--size 120]` — template-match a patch through the clip (forward from time T) → per-frame centre + confidence.

## 1. Read the camera motion before cutting

Optical flow on corners (`goodFeaturesToTrack` + `calcOpticalFlowPyrLK`) and `estimateAffinePartial2D(..., RANSAC)` gives one similarity transform per frame. Majority background drives the fit; screens with scrolling content and moving people become outliers.

Uses:
- Find where the camera is moving (keep those parts at 1x) vs static (speed up / cut) — real use: auto-planning a speed-ramp reel.
- Detect shake to decide if stabilization is needed (frame-to-frame std of translation > ~1.5 px at 480p).
- Find natural cut points (end of a pan).

Work at low resolution (270x480 or 540x960) for speed; scale results back.

## 2. Stabilization

1. Accumulate per-frame (dx, dy, da) into a trajectory.
2. Smooth with a Gaussian (sigma 10-30 frames; larger = steadier, more crop).
3. Correction = smooth − raw; warp each frame by the correction; crop/zoom 5-10% to hide borders.
4. Mask the subject (HSV range, or a person mask) out of feature detection, or the subject's motion is "stabilized" away.

ffmpeg alternative: `vidstabdetect=shakiness=5:accuracy=15` → `vidstabtransform=smoothing=30:zoom=5,unsharp=5:5:0.8`. Resolve: Stabilizer in the Tracker palette.

## 3. Sticking things to footage

| Need | Method |
|---|---|
| Text near an object that moves slowly | point/template track the object, smooth, offset the text |
| Text "printed" on a surface (can, laptop lid, wall, sign) | track 4 corners (or fit the surface), `getPerspectiveTransform`, warp the text layer with `warpPerspective` |
| Text aligned to a logo/glyph in the shot | measure the glyph's centre, angle and height on one frame; lay out text in that local coordinate system; map to frame with an affine; track the centre per frame |
| Glow around a round object (mirror, plate, wheel) | seed an ellipse by hand, refine per frame by snapping to the strongest gradient along normals, fit `fitEllipse`, smooth over 5 frames |
| Graphic on a screen | track the screen's 4 corners; screen-blend for a backlit look |
| 3D object matched to a real object | fit a camera pose from known 2D-3D points (`solvePnP`), render 3D with the same pose (see `style-vfx-compositing`) |

Always smooth tracks (moving average / Savitzky-Golay) and inspect a debug render with the track drawn on.

## 4. Motion-driven sound

Farneback dense flow on the subject minus the median background flow = subject speed (px/s). Drive a rolling/whoosh SFX gain from it so sound follows the motion. Smooth over ~3 frames.

## 5. Chroma key (green screen)

- ffmpeg: `chromakey=0x00FF00:0.12:0.08` (YUV distance) or `colorkey` (RGB), then `despill=type=green`. Tune similarity on a frame with hair/edges.
- Python: HSV mask on green hue (≈ 35-85 in OpenCV's 0-180 scale), erode 1 px, feather (Gaussian 2-3 px), suppress spill by clamping G to max(R, B) at edges.
- Match the key to the plate: grade the foreground to the background's black level, WB and saturation; add matching grain and light wrap (blur the background, screen 10-20% onto the foreground edge).
- Ground it: contact shadow, matching motion blur, track the attachment point so it moves with the handheld camera.

## 6. Verify

Render a debug video with tracks/ellipses/corners drawn; scrub the frames where the object is fastest, occluded or blurred. Fix drift with keyframed manual corrections instead of fighting the tracker.
