# Modeling

## Get the size right first

Wrong scale can't be fixed with lighting or materials. Write each object's real size in `brief.md`, then check it with `bsteps audit` or `dims(obj("..."))` before adding detail.

| Object | Rough size (m) |
|---|---|
| Car | 4.5 L × 1.9 W × 1.4 H |
| Wheel (car) | 0.65–0.75 diameter |
| Door | 2.0 H × 0.9 W |
| Desk / table height | 0.75 |
| Chair seat height | 0.45 |
| Wine or soda bottle | 0.25–0.33 H |
| Phone | 0.15 × 0.07 × 0.008 |
| Room ceiling | 2.4–3.0 |

Lens choice changes how big things feel: 24–35 mm for rooms and environments, about 50 mm for a natural look, 85–135 mm for products. Pick the lens for the shot, not to hide a proportion problem.

## Structure

- **Separate parts that differ.** A car's body, glass and wheels are separate objects, because they get different materials and the wheels may turn.
- **Put the origin at the pivot.** A wheel's origin at its hub, a bottle's at the centre of its base, a door's on its hinge line.
- **Collections by role:** `ENV`, `HERO`, `PRP`, `CAM`, `LGT`, `RIG`. The helpers take `collection=`.
- **Contact:** anything resting on the floor has its lowest point at z = 0. `drop_to_floor(ob)` does it; the audit shows each object's lowest z.

## Patterns that save time

- **Many copies of one thing** (bolts, tiles, shelves): build one mesh and create the other objects with the same mesh data (`bpy.data.objects.new(name, mesh)`). It's faster than calling a primitive operator in a loop, and editing the shared mesh updates every copy. Check `mesh.users` before editing so you don't change copies by accident.
- **Keep modifiers live** (bevel, mirror, array, subdivision). GLB export applies them for you.
- **Bevels need applied scale.** `box()` applies scale already. If you scale an object unevenly after adding a bevel, the bevel stretches, and the audit warns about it.
- **Which way is it facing?** Compute the world-space normal and compare it with the camera direction instead of reasoning about Euler angles.
- **Parenting into a rig:** set `child.matrix_parent_inverse.identity()` when the child should take on the parent's space, as with orbit and turntable rigs.
- **Editing part of a mesh:** select by material, island or normal and print the counts before and after, so you know exactly what changed.

## Hard-surface subjects (vehicles, devices, machines, buildings)

What makes them read as real rather than a placeholder:
- **A profile with character.** Build the main body from cross-sections (bmesh, or a curve with bevel) rather than one stretched box. Real products have shoulders, tapers and breaks in the line.
- **Recessed details.** Grilles, vents, screens and panel lines go into the surface. Small boxes stuck on top look glued on.
- **Parts that follow the surface.** For mirrors, lights, badges and handles on a curved body, use `seat_on(ob, host, origin, direction, offset)`. It ray-casts against the host object only, so it never lands on another part.
- **Detail where the camera looks.** Put fine detail on the side the camera sees and leave some plain areas, so the detail stands out.
- **Shading:** `smooth(ob)` for organic shapes, `smooth(ob, 30)` for smooth surfaces with crisp edges (Blender 5 has no auto-smooth toggle), flat shading where facets are the look.

## Background objects

Props in the middle distance should still be recognisable: a tool cart needs drawers and handles, not just a box. Objects far in the background only need the right silhouette and size.

## GLB export

- Model in metres. If another unit is needed, scale one root object once.
- Use plain Principled BSDF values (what `mat()` makes). Procedural node setups mostly don't survive glTF.
- glTF makes one primitive per material per mesh, so merge objects that share a material when you don't need them separate.
- Only SUN, SPOT and POINT lights export. AREA lights are dropped.
- Keep polygon counts in line with how close the object will be seen.
- Before you hand the file over, check normals, applied transforms, material slots and the animation range, and say what you couldn't check.
