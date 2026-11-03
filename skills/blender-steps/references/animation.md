# Animation

## Decide the motion first

Fill in the Motion line of `brief.md` before keying anything: fps, frame range, what moves, and which frame holds still (useful as a thumbnail). Keep it to one clear main movement.

If the user doesn't say what should move, use a default:

| Subject | Default |
|---|---|
| Product | One slow turntable turn, or a partial camera orbit that ends on the best angle |
| Room or environment | A slow camera push or slide, perhaps with a light coming on |
| Vehicle | A slow orbit, or a push-in as the headlights switch on |

Don't add things nobody asked for: character acting, physics simulations, a camera that never stops.

## Helpers

- **`turntable(ob, start=1, end=120, turns=1.0)`** spins an object at constant speed. The last key sits one frame past `end`, so frame `end` and frame `start` don't duplicate and the loop is seamless.
- **`orbit_camera("CAM_main", target, radius, height, start, end, degrees=360, start_deg=-45)`** parents the camera to an empty, `RIG_orbit`, that spins about the target, and keeps the camera tracking the target. `degrees=40` gives a slow reveal instead of a full circle. For ease-in and ease-out, re-key `RIG_orbit` with Bezier interpolation.
- **`key(ob, "location", frame, value, interp="BEZIER")`** keys any property. Use `LINEAR` for constant speed and `CONSTANT` for switches (visibility, a light turning on).
  - Camera lens, focus distance and light energy live on the data block: `key(ob.data, "lens", ...)`, `key(ob.data, "energy", ...)`.
  - Blender 5 stores keyframes in layered actions; `key()` handles this. To read F-curves, use `K._fcurves(ob.animation_data)`.

## Getting physical motion right

- **Rolling wheels:** rotation in radians = distance travelled / wheel radius. Otherwise the wheels skid.
- **Spinning parts** need their origin on the spin axis, or they wobble.
- **Wagon-wheel effect:** a fast wheel or fan can seem to turn backwards when each frame's rotation is close to the angle between its spokes. Change the speed and look at the frames.
- **Uneven ground:** sample the ground height under several contact points. The average sets the height; the differences set the tilt.

## Checking motion

`bsteps audit` confirms the frame range, fps and active camera. The numbers can't tell you whether the motion looks right, so render stills at the key moments and Read each one:

```bash
"$BS" render <slug> --frames 1,30,60,90,120 --name motion
```

Look for: the subject leaving frame or getting cropped, objects passing through each other or the floor, sudden jumps or flips, motion too small to notice, and (for loops) a jump between the last and first frame.

## Video

`bsteps video <slug>` renders the frame range to PNGs (EEVEE, 640x360, 8 samples by default) and joins them into `renders/rNNN-anim.mp4`.
- **Estimate first:** render one still at video settings and time it. 120 frames at 2 s each is 4 minutes, beyond the default 300 s timeout once overhead is included, so use `bsteps --timeout 900 video <slug>`.
- **If it won't finish,** deliver the checked stills and the `.blend` (`bsteps export <slug> blend`) so the user can render it themselves.
