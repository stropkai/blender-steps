# blender-steps

A [Claude Code](https://claude.com/claude-code) skill for building 3D scenes in your own Blender, headless and free.

Claude writes the scene as a series of small Python steps. Each step that succeeds becomes a numbered revision you can roll back to; a step that fails changes nothing. After each step Claude renders a PNG and looks at it before deciding what to fix next, so "the script ran" never counts as "the scene is done".

It handles stills, product turntables, camera orbits, short animations, and GLB or `.blend` exports.

## Requirements

- Blender 5.x (tested on 5.2.1, macOS)
- Python 3
- ffmpeg, for video only

`bsteps` finds Blender through `$BLENDER`, then `blender` on your `PATH`, then `/Applications/Blender.app/Contents/MacOS/Blender`.

## Install

As a Claude Code plugin:

```bash
claude plugin marketplace add stropkai/blender-steps
```

```bash
claude plugin install blender-steps@blender-steps
```

Or copy `skills/blender-steps/` into `~/.claude/skills/`.

Then ask Claude for something like "make a 3d scene of a red sports car in a garage" or "product turntable of a glass bottle".

## The CLI

The skill drives `skills/blender-steps/scripts/bsteps`, which you can also run yourself:

```text
bsteps new <slug>                      empty metric scene, revision 0, brief.md template
bsteps run <slug> step.py --note "..." run a step; commit a revision only if it succeeds
bsteps query <slug> -e "code"          read-only Python against the scene
bsteps audit <slug>                    objects, sizes, floor contact, camera, lights, warnings
bsteps render <slug> [--view right --engine workbench|eevee|cycles --frames 1,60,120]
bsteps video <slug>                    frame range -> mp4
bsteps export <slug> glb|blend
bsteps log <slug> / bsteps revert <slug> <rev>
```

Projects go to `~/blender-steps/<slug>/` (set `$BSTEPS_HOME` to change it). Steps get a small helper library (`scripts/kit.py`) as globals: `box`, `cylinder`, `mat`, `working_rig`, `light`, `seat_on`, `turntable`, `orbit_camera` and more.

A first step looks like this:

```python
working_rig(subject=(0, 0, 0.15), cam_location=(1.4, -1.4, 0.35), lens=85)
plane("ENV_floor", size=6)
assign(obj("ENV_floor"), mat("M_floor", (0.1, 0.1, 0.11), roughness=0.4))
cylinder("HERO_bottle", radius=0.035, depth=0.28)
assign(obj("HERO_bottle"), mat("M_glass", (0.6, 0.8, 0.7), roughness=0.0, transmission=1.0, ior=1.5))
```

## License

MIT
