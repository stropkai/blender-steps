# Materials and light

## What `working_rig()` gives you

`working_rig(subject, cam_location, lens, key_energy, fill_energy)` creates:
- `CAM_main`, aimed at `subject`;
- `LGT_key`, a spot above and to one side;
- `LGT_fill`, a large soft point on the other side;
- a dim world colour, if the scene has no world yet (`bsteps new` already sets one).

It's meant to make the scene readable from step 1, not to be the final lighting. Re-aim lights with `light("LGT_key", "SPOT", location, target, energy, size=...)` whenever the geometry moves.

## Material values

`mat(name, color, roughness, metallic, coat=, transmission=, ior=, emission=, strength=)`. Name materials by what they are (`M_paint`, `M_chrome`, `M_floor`) and reuse them instead of making near-copies.

| Surface | Settings |
|---|---|
| Glossy car paint | your colour, roughness 0.35, metallic 0.6, coat 1.0 |
| Chrome | (0.9, 0.9, 0.9), roughness 0.05, metallic 1.0 |
| Brushed aluminium | (0.8, 0.8, 0.82), roughness 0.3, metallic 1.0 |
| Matte plastic | your colour, roughness 0.6 |
| Rubber / tyre | (0.02, 0.02, 0.02), roughness 0.8 |
| Clear glass | roughness 0.0, transmission 1.0, ior 1.5 (darken the colour for tinted car glass) |
| Polished concrete / epoxy floor | grey, roughness 0.25 |
| Wood (flat) | (0.35, 0.2, 0.1), roughness 0.55 |
| Light panel / LED strip | emission (1, 1, 1), strength 5–30 |

Notes:
- **No downloaded textures.** Build patterns with procedural nodes (noise, voronoi, wave, colour ramp) or bake them. An image node whose file is missing renders magenta, and the audit flags it.
- Colour inputs use colour data; roughness, metallic, normal and mask maps use non-colour data.
- Wear and dirt look believable when they follow a cause: worn paint on edges people touch, grime that runs down from seams, fading on the side that faces the sun.

## Setting up the light

Lock the camera first; balancing light while the camera keeps moving wastes renders. Then change one light per step and compare renders at the same size, samples and exposure.

**Product or studio:** a dark `world_color`, the key from 45° to the side and above, a large soft fill on the opposite side at roughly a quarter of the key's energy, and optionally a rim light behind if the subject merges with the background.

**Daylight exterior:** `sky(sun_elevation_deg, sun_rotation_deg, strength)` plus a SUN light pointing the same way as the sky's sun. The sky alone is soft ambient light; the sun light gives the shadows.

**Interior:** build the room (including `ENV_ceiling`) before `working_rig`. Visible fixtures (ceiling panels, lamps) get an emissive material plus a hidden spot or point light near them, pointing the same way, so the light has a believable source.

**Night:** a very dim world, one strong motivated source (street lamp, window, headlights) with its pool of light in frame. Keep fog light; it greys out everything quickly.

Starting energies for EEVEE, for a subject about 1 m tall with lights 4–6 m away:

| Light | Energy |
|---|---|
| Spot key | 800–2000 W |
| Point fill | 150–500 W |
| Sun | 2–5 |

Spot and point light fade with the square of distance, so moving a light closer brightens it fast; sun strength doesn't depend on position. A bigger `size` gives softer shadows. Judge brightness from the render, not the numbers.

**Colour management:** the view transform is AgX. For more contrast, set `bpy.context.scene.view_settings.look = 'AgX - High Contrast'` (also `'AgX - Medium High Contrast'`, `'AgX - Punchy'`).

## Glossy products, glass and metal

Shiny surfaces show what they reflect, so give them something to reflect:
- Add large planes with an emission material near the product. Set `ob.visible_camera = False` so they show only in reflections.
- A tall, thin card gives the long vertical highlight that makes a bottle or can look round.
- A dark card on the other side keeps glass edges defined.
- Check each camera angle for cards showing in frame.

Cycles handles glass and chrome much better than EEVEE; use it for the final still. If a Cycles render runs out of time, drop samples or resolution first.

## Troubleshooting a render

| You see | Try |
|---|---|
| Everything flat and grey | The world is too bright compared with the key. Lower the world strength or raise the key |
| Subject disappears into the background | A rim light behind it, or a lighter or darker background |
| Two shadows going different ways | The fill is too strong or too directional. Make it bigger and dimmer |
| Highlights burned out on the subject | Lower that light, enlarge it, or move it farther away |
| Black, empty render | No camera, lights pointing away, or the camera is inside an object. Run `bsteps audit` |
| Magenta surfaces | An image texture with a missing file |
