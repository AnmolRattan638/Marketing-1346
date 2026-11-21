---
name: style-vfx-compositing
description: VFX and compositing editing style - adding things that were not in the shot - tracked text and graphics on surfaces, green-screen keying, CG/3D objects matched to camera, holograms and wireframe twins, neon glows on real objects, screen replacements, sky replacement, day-for-night, particles and light effects - with matching grade, grain, lighting and motion. Use when the user wants objects, effects, 3D, holograms, glows, or composited elements integrated into real footage.
---

# Style: VFX compositing

Load with: `motion-tracking` (essential), `color-grading`, `ffmpeg-pipeline` (+ Three.js / Blender skills for 3D, HyperFrames for HTML layers).

## Integration checklist (what makes a composite believable)

1. **Track**: the element moves with the camera (point, planar or full camera solve).
2. **Perspective**: matches the surface/camera (corner pin, `solvePnP` pose for 3D).
3. **Light**: direction and colour of light on the element match the plate; add light wrap at edges.
4. **Colour**: black level, white level, saturation and WB match the plate.
5. **Focus and motion blur**: blur the element to the plate's depth of field and motion blur.
6. **Grain/noise**: add matching grain over the element (or over everything after compositing).
7. **Contact**: shadows/occlusion/reflections where the element meets the scene.
8. **Interaction**: the element affects the scene (glow lights nearby surfaces, objects cast light, sound reacts).

## Recipes

| Effect | How |
|---|---|
| **Text on a moving object** | planar track 4 corners → warp text layer → multiply/overlay blend for printed look, or normal + shadow for floating |
| **Hologram / wireframe twin of a real object** | fit camera pose from 2D-3D correspondences (lid edges, key centres; ~6 px reprojection error is fine), render a wireframe model with the same pose; states: build (scan line prints it on), live (pulses on beat), explode (layers lift off on a drop); screen-blend cyan glow |
| **Neon glow around a round object** | per-frame ellipse fit (seed by hand, snap to gradients along normals, smooth 5 frames) → draw core line + bloom (Gaussian 15-40 px) + comet highlight running around + sparks; screen blend; pulse on beats |
| **Green screen object** | key (chromakey/despill or HSV), grade to plate, track attachment point (e.g. a spider dropping from a fan hub on a thread: track the hub, simulate swing with eased bounce, draw the thread) |
| **Screen replacement** | track screen corners, warp new content, add screen glare from the plate (screen-blend the plate's highlights back on top) |
| **Sky replacement** | luma/colour key the sky + refine edge, new sky moves with camera track, re-grade foreground toward sky colour |
| **Day for night** | -1.5 to -2 stops, blue, low saturation, darken sky most, keep practical lights warm and bright (see `color-grading`) |
| **Particles / bokeh / light leaks** | rendered or procedural layers, screen/add blend, drift slowly, keep away from faces and text |
| **Glitch / RGB split** | channel offsets + block displacement on hits |

## 3D in a video

- Pick engine: Three.js (render frames headless via HyperFrames/Puppeteer), Blender (Python bpy, Cycles/Eevee), or pre-rendered assets.
- Match camera: focal length (phone main ≈ 24-26 mm equivalent), sensor/FOV, and pose; render with alpha.
- Render at plate resolution and fps; export PNG/EXR sequence.

## Quality bar

Scrub the hardest frames (fast motion, occlusion, edges of frame). If the element slides even 2-3 px against the plate, fix the track before anything else. Show the user a still and a 2-3 s preview before rendering everything.
