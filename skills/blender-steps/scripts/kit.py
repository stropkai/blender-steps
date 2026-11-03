"""Helpers every bsteps step gets as globals (also available as K). Blender 5.2 API.

All lookups are by name: each step starts from the saved scene, not from the last step's selection.
Re-running a helper with the same name updates that object instead of making `Name.001`.
"""
import math
import os
import re

import bpy
from mathutils import Vector

__all__ = ["obj", "coll", "link", "mat", "assign", "look_at", "camera", "light", "working_rig", "world_color",
           "sky", "box", "cylinder", "torus", "plane", "sphere", "surface_hit", "seat_on", "bevel", "smooth", "drop_to_floor", "key", "turntable",
           "orbit_camera", "dims", "lowest_z"]


def obj(name):
    """The object called `name`, or None."""
    return bpy.data.objects.get(name)


def coll(name, parent=None):
    """Get or create a collection (linked under the scene, or under `parent`)."""
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    host = parent if parent is not None else bpy.context.scene.collection
    if c.name not in [x.name for x in host.children]:
        host.children.link(c)
    return c


def link(ob, collection):
    """Move `ob` into exactly one collection (str or Collection)."""
    c = coll(collection) if isinstance(collection, str) else collection
    for old in list(ob.users_collection):
        old.objects.unlink(ob)
    c.objects.link(ob)
    return ob


def _replace(name, data, collection):
    ob = obj(name)
    if ob is not None:
        old = ob.data
        ob.data = data
        if old is not None and old is not data and old.users == 0:
            for pool in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras):
                if pool.get(old.name) == old:
                    pool.remove(old)
                    break
    else:
        ob = bpy.data.objects.new(name, data)
        (coll(collection) if collection else bpy.context.scene.collection).objects.link(ob)
    return ob


def mat(name, color=None, roughness=None, metallic=None, emission=None, strength=None,
        coat=None, transmission=None, ior=None, alpha=None):
    """Get or create a Principled BSDF material (glTF-safe: plain values only).

    Only the arguments you pass are changed, so `mat("M_tyre")` just fetches an existing material.
    A new material starts at grey 0.8, roughness 0.5, non-metal.
    """
    m = bpy.data.materials.get(name)
    fresh = m is None
    if fresh:
        m = bpy.data.materials.new(name)
        color = (0.8, 0.8, 0.8) if color is None else color
        roughness = 0.5 if roughness is None else roughness
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    if p is None:
        p = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = m.node_tree.nodes.get("Material Output") or m.node_tree.nodes.new("ShaderNodeOutputMaterial")
        m.node_tree.links.new(p.outputs["BSDF"], out.inputs["Surface"])

    def rgba(c):
        return tuple(c) + ((1.0,) if len(c) == 3 else ())

    if color is not None:
        p.inputs["Base Color"].default_value = rgba(color)
        m.diffuse_color = rgba(color)  # what Workbench shows
    for sock, v in (("Roughness", roughness), ("Metallic", metallic), ("Coat Weight", coat),
                    ("Transmission Weight", transmission), ("IOR", ior), ("Alpha", alpha)):
        if v is not None:
            p.inputs[sock].default_value = v
    if emission is not None:
        p.inputs["Emission Color"].default_value = rgba(emission)
        p.inputs["Emission Strength"].default_value = 1.0 if strength is None else strength
    elif strength is not None:
        p.inputs["Emission Strength"].default_value = strength
    elif fresh:
        p.inputs["Emission Strength"].default_value = 0.0
    return m


def assign(ob, *materials):
    """Set slot 0, 1, ... to `materials` in place. Per-face material indices are kept
    (slot 1 stays the windows), and slots past the ones given are left alone."""
    slots = ob.data.materials
    for i, m in enumerate(materials):
        if i < len(slots):
            slots[i] = m
        else:
            slots.append(m)
    return ob


def look_at(ob, target):
    """Point a camera/light's -Z at `target` (a Vector, tuple, or object name)."""
    if isinstance(target, str):
        target = obj(target).matrix_world.translation
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def camera(name="CAM_main", location=(6, -6, 1.6), target=(0, 0, 0.8), lens=50, active=True, collection="CAM"):
    data = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_end = 1000
    ob = _replace(name, data, collection)
    ob.location = location
    look_at(ob, target)
    if active:
        bpy.context.scene.camera = ob
    return ob


def light(name, kind="SPOT", location=(4, -4, 5), target=(0, 0, 0.5), energy=1000, size=0.5, color=(1, 1, 1),
          spot_deg=60, blend=0.4, collection="LGT"):
    """SUN / SPOT / POINT (glTF keeps these). AREA works in renders but glTF drops it."""
    data = bpy.data.lights.get(name)
    if data is None or data.type != kind:
        data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == "SUN":
        data.angle = math.radians(max(size, 0.1))  # size = sun disc in degrees
    elif kind in ("SPOT", "POINT"):
        data.shadow_soft_size = size  # radius in m: bigger = softer
    if kind == "SPOT":
        data.spot_size = math.radians(spot_deg)
        data.spot_blend = blend
    elif kind == "AREA":
        data.size = size
    ob = _replace(name, data, collection)
    ob.location = location
    if kind != "POINT":
        look_at(ob, target)
    return ob


def world_color(color=(0.05, 0.05, 0.055), strength=1.0):
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg.inputs["Color"].default_value = tuple(color) + (1.0,)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return w


def sky(sun_elevation_deg=35, sun_rotation_deg=0, strength=0.3):
    """Procedural daylight world (an ambient probe; still add a SUN key that matches it)."""
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    sk = nt.nodes.new("ShaderNodeTexSky")
    for t in ("NISHITA", "MULTIPLE_SCATTERING", "SINGLE_SCATTERING"):
        try:
            sk.sky_type = t
            break
        except TypeError:
            continue
    if hasattr(sk, "sun_elevation"):
        sk.sun_elevation = math.radians(sun_elevation_deg)
        sk.sun_rotation = math.radians(sun_rotation_deg)
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sk.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    return w


def working_rig(subject=(0, 0, 0.8), cam_location=(6, -6, 1.6), lens=50, key_energy=1500, fill_energy=300):
    """First-step scaffolding: CAM_main + LGT_key (spot, side/above) + LGT_fill (big soft point) + dim world.
    Build ENV_ceiling* before calling it in an interior: the key is kept 0.3 m under the lowest ceiling.
    Re-aim later with light("LGT_key", "SPOT", location, target, ...)."""
    s = Vector(subject)
    camera("CAM_main", cam_location, s, lens)
    k = s + Vector((-4, -3, 4.5))
    ceilings = [o for o in bpy.context.scene.objects if o.name.startswith("ENV_ceiling") and o.type == "MESH"]
    if ceilings:  # an interior: keep the key under the lowest ceiling
        k.z = min(k.z, min(lowest_z(c) for c in ceilings) - 0.3)
    light("LGT_key", "SPOT", k, s, key_energy, size=0.6, spot_deg=55)
    light("LGT_fill", "POINT", s + Vector((5, -2, 2)), s, fill_energy, size=2.0)
    if not bpy.context.scene.world:
        world_color((0.04, 0.04, 0.045), 0.5)


def _mesh_from_op(name, op, collection, **kw):
    """Run a primitive op, then rename/re-home its result (replacing any object of that name)."""
    old = obj(name)
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    op(**kw)
    ob = bpy.context.active_object
    ob.name = name
    ob.data.name = name
    if collection:
        link(ob, collection)
    return ob


def box(name, size=(1, 1, 1), location=(0, 0, 0), collection=None, on_floor=True):
    """Box with real dimensions in metres; on_floor puts its base at location.z."""
    ob = _mesh_from_op(name, bpy.ops.mesh.primitive_cube_add, collection, size=1)
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    ob.location = (location[0], location[1], location[2] + (size[2] / 2 if on_floor else 0))
    return ob


def cylinder(name, radius=0.5, depth=1, location=(0, 0, 0), vertices=48, collection=None, on_floor=True, axis="Z"):
    """axis="X"/"Y" lays it on its side (wheels, pipes); on_floor then rests the curved side on location.z."""
    rot = {"Z": (0, 0, 0), "X": (0, math.pi / 2, 0), "Y": (math.pi / 2, 0, 0)}[axis.upper()]
    ob = _mesh_from_op(name, bpy.ops.mesh.primitive_cylinder_add, collection,
                       radius=radius, depth=depth, vertices=vertices, rotation=rot)
    lift = (depth / 2 if axis.upper() == "Z" else radius) if on_floor else 0
    ob.location = (location[0], location[1], location[2] + lift)
    return ob


def torus(name, major=0.5, minor=0.1, location=(0, 0, 0), axis="Z", collection=None, segments=48, ring=16):
    """Ring/tyre. axis="X"/"Y" stands it up like a wheel."""
    rot = {"Z": (0, 0, 0), "X": (0, math.pi / 2, 0), "Y": (math.pi / 2, 0, 0)}[axis.upper()]
    ob = _mesh_from_op(name, bpy.ops.mesh.primitive_torus_add, collection, major_radius=major, minor_radius=minor,
                       major_segments=segments, minor_segments=ring, rotation=rot)
    ob.location = location
    smooth(ob)
    return ob


def surface_hit(host, origin, direction):
    """Ray-cast against ONE object (name or object) only; returns (world_point, world_normal) or None.
    Use it to seat details (mirrors, badges, lights) on a curved host without hitting earlier copies."""
    host = obj(host) if isinstance(host, str) else host
    dg = bpy.context.evaluated_depsgraph_get()
    ev = host.evaluated_get(dg)
    inv = ev.matrix_world.inverted()
    o = inv @ Vector(origin)
    d = (inv.to_3x3() @ Vector(direction)).normalized()
    ok, loc, nrm, _ = ev.ray_cast(o, d)
    if not ok:
        return None
    return ev.matrix_world @ loc, (ev.matrix_world.to_3x3().inverted().transposed() @ nrm).normalized()


def seat_on(ob, host, origin, direction, offset=0.0, align=True):
    """Place `ob` where a ray from `origin` along `direction` meets `host`; optionally turn its +Z to the normal."""
    hit = surface_hit(host, origin, direction)
    if hit is None:
        raise RuntimeError(f"seat_on: ray from {tuple(origin)} missed {host}")
    p, n = hit
    ob.location = p + n * offset
    if align:
        ob.rotation_euler = n.to_track_quat("Z", "Y").to_euler()
    return ob


def plane(name, size=10, location=(0, 0, 0), collection=None):
    ob = _mesh_from_op(name, bpy.ops.mesh.primitive_plane_add, collection, size=size)
    ob.location = location
    return ob


def sphere(name, radius=0.5, location=(0, 0, 0), segments=48, rings=24, collection=None):
    ob = _mesh_from_op(name, bpy.ops.mesh.primitive_uv_sphere_add, collection,
                       radius=radius, segments=segments, ring_count=rings)
    ob.location = location
    smooth(ob)
    return ob


def bevel(ob, width=0.01, segments=3):
    """Non-destructive bevel (apply scale first: bevel width is local-space)."""
    m = ob.modifiers.get("BS_bevel") or ob.modifiers.new("BS_bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    return m


def smooth(ob, angle_deg=None):
    """Smooth shading. With angle_deg, keep sharp edges above that angle (5.2 has no use_auto_smooth)."""
    for p in ob.data.polygons:
        p.use_smooth = True
    if angle_deg is not None:
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob],
                                       selected_editable_objects=[ob]):
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle_deg))
    return ob


def lowest_z(ob):
    bpy.context.view_layer.update()  # matrix_world is stale right after setting location
    return min((ob.matrix_world @ Vector(c)).z for c in ob.bound_box)


def drop_to_floor(ob, floor_z=0.0):
    """Move `ob` so its lowest point sits on floor_z (contact gate)."""
    bpy.context.view_layer.update()
    ob.location.z += floor_z - lowest_z(ob)
    return ob


def dims(ob):
    """World-space dimensions in metres (x, y, z), rounded."""
    return tuple(round(v, 3) for v in ob.dimensions)


def key(ob, path, frame, value=None, interp="BEZIER"):
    """Insert a keyframe on `path` (e.g. 'location', 'rotation_euler') at `frame`, optionally setting it first."""
    if value is not None:
        setattr(ob, path, value)
    ob.keyframe_insert(data_path=path, frame=frame)
    ad = ob.animation_data
    if ad and ad.action:
        for fc in _fcurves(ad):
            if fc.data_path == path:
                for kp in fc.keyframe_points:
                    if int(kp.co.x) == int(frame):
                        kp.interpolation = interp
    return ob


def _fcurves(ad):
    act = ad.action
    if hasattr(act, "fcurves"):
        return act.fcurves
    # Blender 5.x layered actions: curves live in the slot's channelbag.
    out = []
    for layer in getattr(act, "layers", []):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", []):
                out += list(bag.fcurves)
    return out


def turntable(ob, start=1, end=120, turns=1.0, axis=2):
    """Seamless linear spin: frame `end` lands one step before a full turn so the loop has no held frame."""
    s = bpy.context.scene
    s.frame_start, s.frame_end = start, end
    rot = list(ob.rotation_euler)
    base = rot[axis]
    key(ob, "rotation_euler", start, tuple(rot), "LINEAR")
    rot[axis] = base + 2 * math.pi * turns
    key(ob, "rotation_euler", end + 1, tuple(rot), "LINEAR")
    return ob


def orbit_camera(cam_name="CAM_main", target=(0, 0, 0.8), radius=6, height=1.6, start=1, end=120, degrees=360,
                 start_deg=-45):
    """Orbit rig: an empty at `target` that spins, with the camera parented and tracking the target."""
    s = bpy.context.scene
    rig = obj("RIG_orbit") or bpy.data.objects.new("RIG_orbit", None)
    if rig.name not in bpy.context.scene.collection.all_objects:
        coll("RIG").objects.link(rig)
    rig.location = target
    cam = obj(cam_name)
    cam.parent = rig
    cam.matrix_parent_inverse.identity()
    a = math.radians(start_deg)
    cam.location = (radius * math.cos(a), radius * math.sin(a), height - target[2])
    tr = cam.constraints.get("BS_track") or cam.constraints.new("TRACK_TO")
    tr.name = "BS_track"
    tr.target = rig
    tr.track_axis = "TRACK_NEGATIVE_Z"
    tr.up_axis = "UP_Y"
    s.frame_start, s.frame_end = start, end
    n = end - start + 1
    key(rig, "rotation_euler", start, (0, 0, 0), "LINEAR")
    key(rig, "rotation_euler", end + 1, (0, 0, math.radians(degrees)), "LINEAR")
    return rig


DEFAULT_NAME = re.compile(r"^(Cube|Sphere|Cylinder|Plane|Cone|Torus|Circle|Light|Camera|Empty|Suzanne|Icosphere)(\.\d+)?$")


def audit_lines():
    s = bpy.context.scene
    r = s.render
    L, W = [], []
    L.append(f"scene engine={r.engine} res={r.resolution_x}x{r.resolution_y}@{r.resolution_percentage}% "
             f"fps={r.fps} frames={s.frame_start}-{s.frame_end} view={s.view_settings.view_transform} "
             f"look={s.view_settings.look} camera={s.camera.name if s.camera else None}")
    if s.camera is None:
        W.append("no active camera")
    for c in bpy.data.collections:
        L.append(f"collection {c.name}: {len(c.objects)} objects")
    for ob in sorted(s.objects, key=lambda o: o.name):
        loc = tuple(round(v, 3) for v in ob.matrix_world.translation)
        line = f"{ob.type:<6} {ob.name:<22} loc={loc}"
        if ob.type == "MESH":
            mats = [m.name for m in ob.data.materials if m]
            line += f" dims={dims(ob)} lowz={round(lowest_z(ob), 3)} mats={mats} verts={len(ob.data.vertices)}"
            if not mats:
                W.append(f"{ob.name} has no material")
            if any(m.type == "BEVEL" for m in ob.modifiers) and len({round(v, 4) for v in ob.scale}) > 1:
                W.append(f"{ob.name} has a bevel on non-uniform scale {tuple(ob.scale)} (apply scale)")
        elif ob.type == "LIGHT":
            line += f" kind={ob.data.type} energy={ob.data.energy}"
            if ob.data.type == "AREA":
                W.append(f"{ob.name} is an AREA light (dropped by GLB export)")
        elif ob.type == "CAMERA":
            line += f" lens={ob.data.lens}mm type={ob.data.type}"
        if ob.parent:
            line += f" parent={ob.parent.name}"
        if ob.hide_render:
            line += " HIDDEN-IN-RENDER"
        if ob.animation_data and ob.animation_data.action:
            line += " animated"
        L.append(line)
        if DEFAULT_NAME.match(ob.name):
            W.append(f"{ob.name} still has a default name (use ENV_/HERO_/PRP_/CAM_/LGT_/RIG_)")
    for m in bpy.data.materials:
        if m.use_nodes and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE":
                    img = n.image
                    if img is None or (img.source == "FILE" and not os.path.exists(bpy.path.abspath(img.filepath))):
                        W.append(f"material {m.name}: image node with a missing file (renders magenta)")
    if not any(o.type == "LIGHT" for o in s.objects):
        W.append("no lights (only the world lights the scene)")
    L += [f"WARNING {w}" for w in W] or ["no warnings"]
    return L
