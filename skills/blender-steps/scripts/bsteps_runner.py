"""Runs inside Blender (bsteps passes everything after `--`). Not meant to be called directly."""
import json
import math
import os
import runpy
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit  # noqa: E402  (helpers for steps)

ENGINES = {"eevee": "BLENDER_EEVEE", "workbench": "BLENDER_WORKBENCH", "cycles": "CYCLES"}


def argv():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    mode, rest, opts = a[0], a[1:], {}
    i = 0
    while i < len(rest):
        k = rest[i].lstrip("-")
        if k == "res":
            opts[k] = (int(rest[i + 1]), int(rest[i + 2])); i += 3
        else:
            opts[k] = rest[i + 1] if i + 1 < len(rest) else ""; i += 2
    return mode, opts


def say(msg):
    print(f"BS {msg}", flush=True)


def new_scene(o):
    # Start from nothing: no default cube, light or camera. Metric, AgX, EEVEE.
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for pool in (bpy.data.meshes, bpy.data.lights, bpy.data.cameras, bpy.data.materials, bpy.data.collections):
        for d in list(pool):
            pool.remove(d)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 1.0
    s.render.fps = int(o.get("fps", 24))
    s.render.resolution_x, s.render.resolution_y = o.get("res", (1920, 1080))
    s.render.resolution_percentage = 100
    s.render.engine = "BLENDER_EEVEE"
    s.view_settings.view_transform = "AgX"
    s.frame_start, s.frame_end = 1, 120
    if s.world is None:
        s.world = bpy.data.worlds.new("World")
    kit.world_color((0.05, 0.05, 0.055), 0.6)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(o["project"]) / "scene.blend"))
    say("new scene saved")


def run_step(o, save):
    path = o["step"]
    g = {"bpy": bpy, "Vector": Vector, "math": math, "K": kit, "PROJECT": Path(o["project"])}
    g.update({k: getattr(kit, k) for k in kit.__all__})
    print("BS-OUT-BEGIN", flush=True)
    try:
        runpy.run_path(path, init_globals=g, run_name="__bsteps_step__")
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc(file=sys.stdout)
        print("BS-OUT-END", flush=True)
        say("STEP FAILED (nothing committed)")
        sys.exit(3)
    print("BS-OUT-END", flush=True)
    if save:
        bpy.context.view_layer.update()
        bpy.ops.wm.save_as_mainfile(filepath=o["save"], copy=True)
        say("step ok")


def audit(o):
    for line in kit.audit_lines():
        print("BS|" + line)


def _ortho_camera(view):
    # Frame everything except the environment (a 20 m floor would shrink the subject to a speck).
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and not o.hide_render]
    subjects = [o for o in meshes if not o.name.startswith("ENV_")] or meshes
    pts = []
    for ob in subjects:
        pts += [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    if not pts:
        raise RuntimeError("no visible meshes to frame")
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c, size = (lo + hi) / 2, hi - lo
    cam = bpy.data.objects.new("BS_ortho", bpy.data.cameras.new("BS_ortho"))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    d = max(size) * 3 + 1
    # Blender's own view names: front looks from -Y toward +Y, right from +X, back from +Y, left from -X.
    if view == "front":
        cam.location, cam.rotation_euler, span = c + Vector((0, -d, 0)), (math.radians(90), 0, 0), (size.x, size.z)
    elif view == "back":
        cam.location, cam.rotation_euler, span = c + Vector((0, d, 0)), (math.radians(90), 0, math.radians(180)), (size.x, size.z)
    elif view == "right":
        cam.location, cam.rotation_euler, span = c + Vector((d, 0, 0)), (math.radians(90), 0, math.radians(90)), (size.y, size.z)
    elif view == "left":
        cam.location, cam.rotation_euler, span = c + Vector((-d, 0, 0)), (math.radians(90), 0, math.radians(-90)), (size.y, size.z)
    else:
        cam.location, cam.rotation_euler, span = c + Vector((0, 0, d)), (0, 0, 0), (size.x, size.y)
    r = bpy.context.scene.render
    aspect = r.resolution_x / r.resolution_y
    cam.data.ortho_scale = max(span[0], span[1] * aspect) * 1.15
    cam.data.clip_end = d * 4
    return cam


def _setup_render(o):
    s = bpy.context.scene
    s.render.engine = ENGINES[o["engine"]]
    s.render.resolution_x, s.render.resolution_y = o["res"]
    s.render.resolution_percentage = 100
    n = int(o.get("samples", 16))
    if s.render.engine == "BLENDER_EEVEE":
        s.eevee.taa_render_samples = n
    elif s.render.engine == "CYCLES":
        s.cycles.samples = n
        s.cycles.use_denoising = True
        # Headless Blender defaults to CPU; use the Mac's GPU through Metal when it is there.
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "METAL"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            s.cycles.device = "GPU"
        except Exception as e:
            say(f"note: Cycles on CPU ({e})")
    s.render.image_settings.file_format = "PNG"


def render(o):
    s = bpy.context.scene
    _setup_render(o)
    view = o.get("view", "camera")
    if view != "camera":
        s.camera = _ortho_camera(view)
        if o["engine"] != "workbench":
            say("note: ortho views are form checks; workbench is the usual engine for them")
    elif s.camera is None:
        say("ERROR no active camera (add CAM_main in a step, or use --view front|side|top)")
        sys.exit(3)
    frames = [int(f) for f in o.get("frames", "").split(",") if f.strip()] or [s.frame_current]
    rev = int(o["rev"])
    tag = o.get("name") or view
    for f in frames:
        s.frame_set(f)
        out = Path(o["project"]) / "renders" / f"r{rev:03d}-{tag}-{o['engine']}-f{f:04d}.png"
        s.render.filepath = str(out)
        bpy.ops.render.render(write_still=True)
        say(f"render {out}")


def video(o):
    s = bpy.context.scene
    _setup_render(o)
    if s.camera is None:
        say("ERROR no active camera")
        sys.exit(3)
    start = int(o.get("start", s.frame_start))
    end = int(o.get("end", s.frame_end))
    outdir = Path(o["outdir"])
    s.frame_start, s.frame_end = start, end
    s.render.filepath = str(outdir / "f")
    s.render.use_file_extension = True
    bpy.ops.render.render(animation=True)
    (outdir / "meta.json").write_text(json.dumps({"fps": s.render.fps / s.render.fps_base, "start": start, "end": end}))
    say(f"frames {start}-{end} rendered")


def export(o):
    bpy.ops.export_scene.gltf(filepath=o["out"], export_format="GLB", export_apply=True,
                              export_cameras=True, export_lights=True, export_animations=True)
    if any(ob.type == "LIGHT" and ob.data.type == "AREA" for ob in bpy.context.scene.objects):
        say("warning: Area lights are dropped by glTF; the GLB will be darker than the render")


def main():
    mode, o = argv()
    if mode == "new":
        new_scene(o)
    elif mode == "run":
        run_step(o, save=True)
    elif mode == "query":
        run_step(o, save=False)
    elif mode == "audit":
        audit(o)
    elif mode == "render":
        render(o)
    elif mode == "video":
        video(o)
    elif mode == "export":
        export(o)
    else:
        say(f"ERROR unknown mode {mode}")
        sys.exit(3)


try:
    main()
except SystemExit:
    raise
except Exception:
    traceback.print_exc()
    sys.exit(3)
