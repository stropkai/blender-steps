---
name: blender-steps
description: Build 3D scenes in a local, headless Blender (5.x) from small Python steps. Each step that succeeds becomes a numbered revision you can revert to; a failed step changes nothing. Renders are PNGs that Claude opens and checks before reporting. Covers stills, product turntables, camera orbits, short animations, and GLB or .blend exports. Use when the user says "build it in blender", "make a 3d scene", "blender scene of <x>", "render a still in blender", "product turntable", "3d mockup", "spin it in 3d", "export a glb", or asks to change, relight, reframe or roll back a scene this skill made.
---

# Blender Steps

You build the scene by writing short Python files and handing them to `bsteps`, which runs them inside headless Blender. You never open the Blender GUI.

`SK` is this skill's directory, and `BS="$SK/scripts/bsteps"`. `"$BS" --help` prints every command and flag.

## Setup

- **Blender 5.x.** `bsteps` uses `$BLENDER` if set, then `blender` on `PATH`, then `/Applications/Blender.app/Contents/MacOS/Blender`.
- **ffmpeg** is needed only for `bsteps video`.
- **Python 3** runs the CLI. Blender brings its own Python for the steps.
- **Projects live in `~/blender-steps/<slug>/`** (override with `$BSTEPS_HOME`):

```text
<slug>/
  scene.blend          the current scene
  brief.md             what the scene must deliver (bsteps new writes the template)
  drafts/              where you write step files
  steps/rNNN-*.py      a copy of each step that committed
  revisions/rNNN.blend every revision; revisions.tsv is the log
  renders/  exports/
```

## Workflow

1. `bsteps new <slug>`: revision 0 is an empty metric scene with no default cube, camera or light.
2. **Fill in `brief.md`.** Without it you have nothing to judge a render against except "the code ran".
3. **Step 1:** rough shapes for the main subject plus `working_rig(...)`, so the scene has a camera and light from the start.
4. `bsteps render <slug>`, then **open the PNG with the Read tool** and compare it to the brief.
5. Write the next step for the biggest problem you saw. One purpose per step: "fix proportions", "add wheels", "materials", "relight".
6. Repeat 4–5 until every "Done when" line in the brief is visibly true.
7. `bsteps export <slug> glb` or `blend` if the user wants the file.

| Command | What it does |
|---|---|
| `bsteps run <slug> drafts/step.py --note "..."` | Runs the step on the saved scene and commits a new revision only if it succeeds |
| `bsteps query <slug> -e "print(dims(obj('HERO_x')))"` | Read-only Python; prints, never saves |
| `bsteps audit <slug>` | Object list with sizes and floor contact, camera, lights, frame range, warnings |
| `bsteps render <slug> [--view right --engine workbench]` | Stills into `renders/` |
| `bsteps video <slug>` | Renders the frame range and joins it into an mp4 |
| `bsteps log <slug>` / `bsteps revert <slug> <rev>` | History; a revert is itself a new revision |

## Writing a step

A step is plain Python run inside Blender against the saved scene. It gets `bpy`, `Vector`, `math`, `PROJECT` (the project path), `K` (the helper module) and every helper below as globals:

- **Objects:** `box`, `cylinder` (`axis="X"` or `"Y"` lays it on its side, e.g. a wheel), `torus`, `plane`, `sphere`, `obj(name)`, `coll`, `link`.
- **Camera and light:** `working_rig`, `camera`, `light`, `look_at`, `sky`, `world_color`.
- **Materials:** `mat(name, color, roughness, metallic, coat=, transmission=, ior=, emission=, strength=)` only changes what you pass, so `mat("M_tyre")` just fetches it. `assign(ob, m0, m1, ...)` fills slots in place.
- **Placement and shading:** `drop_to_floor`, `seat_on` / `surface_hit` (ray-cast onto one named host, for parts on a curved body), `bevel`, `smooth`, `dims`, `lowest_z`.
- **Animation:** `key`, `turntable`, `orbit_camera`.

Rules that keep steps safe to re-run:
- **Names are identity.** A helper called with an existing name updates that object instead of creating `Name.001`. Always fetch objects with `obj("...")`, never from the selection or active object.
- **Name everything by role:** `ENV_` (floor, walls), `HERO_` (subject), `PRP_` (props), `CAM_`, `LGT_`, `RIG_`. The audit flags default names like `Cube.001`.
- **Model in metres, front facing -Y.** A vehicle's length runs along Y. Ortho views use Blender's names: `front` looks from -Y, `right` from +X, so `--view right` shows a car's side.
- **Indoors, build `ENV_ceiling` before `working_rig`**, which keeps the key light below it.
- **Don't use AREA lights.** glTF drops them, so a GLB would come out darker than the render. Use SPOT or POINT with a large `size` for soft light.
- **Timeouts:** each Blender call gets 300 s; `bsteps --timeout 900 render ...` raises it. A failed or timed-out step commits nothing and prints the traceback.
- Don't pipe `bsteps` output through `head` or `tail`. It's already short, and a pipe hides the exit code.

## Checking your work

A step that runs without errors proves only that the code ran. Floating parts, bad crops, magenta textures and dark scenes show up only in the image, so:

- **Read every render you're going to describe.** Never describe one you didn't open.
- Before reporting, list every flaw you can see. A flaw on the subject (a missing part, a part floating or clipping through, something in the wrong place, blown highlights on it) means the scene isn't done: fix it and render again. Small background flaws can ship if you name them.
- For animation, check at least the first, middle and last frames as stills (`--frames 1,60,120`), plus last-next-to-first for a loop.
- If a render fails or times out, say the check is blocked. Don't call it passed.

| Purpose | Command |
|---|---|
| Shape check, no lighting | `bsteps render <slug> --engine workbench --view right` (or `front`, `back`, `left`, `top`) |
| Working preview | `bsteps render <slug>` (EEVEE, 960x540, 16 samples) |
| Final still | `bsteps render <slug> --res 1920x1080 --samples 64 --name final`, or `--engine cycles --samples 128` for glass, chrome and glossy paint |
| Motion check | `bsteps render <slug> --frames 1,30,60,90,120 --name motion` |
| Video | `bsteps video <slug>` (EEVEE, 640x360, 8 samples). Only after the stills pass |

Cycles uses Metal on Apple GPUs when it can and otherwise falls back to the CPU (bsteps prints a note).

## Reference notes

Open the one you need when the work gets there:
- `references/modeling.md`: sizes, construction patterns, hard-surface tips, GLB prep.
- `references/materials-and-light.md`: material values, light setups and energies, product and night shots.
- `references/animation.md`: the motion helpers, sensible default motions, Blender 5 keyframes, video timing.

## Reporting

Show the final render (attach or display the PNG if your client can; otherwise give its path), then say briefly what the scene shows, its revision number, what you checked in the image, anything still weak or blocked, and where the `.blend` and GLB are.
