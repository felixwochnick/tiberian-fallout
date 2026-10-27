"""
Tiberian Fallout – shared parts of the GDI building scripts (GAWEAP, GARADR, GASILO,
GATECH): the camouflage material, surfaces of revolution, slabs with sloped edges,
fans, beacons, the clip bookkeeping and the headless run with an optional preview.

All of it sits on top of the barracks' helpers (GAPILE.py, imported as `kit`).
Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z).
"""
import math
import sys

import bpy
from mathutils import Vector

import GAPILE as kit

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def camo(obj, root):
    """Gives an object the baked desert camouflage (in shades of the house colour),
    laid out in the space of `root` so the pattern runs on across the parts."""
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def lathe(name, mat, profile, location, segments=48, bevel=0.0, start=0.0):
    """Surface of revolution from (radius, height) points, bottom to top, capped."""
    def build(bm):
        rings = []
        for r, z in profile:
            rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                          for a in (start + 2 * math.pi * i / segments for i in range(segments))])
        for lower, upper in zip(rings, rings[1:]):
            for i in range(segments):
                j = (i + 1) % segments
                bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])

    obj = kit.mesh_object(name, build)
    obj.location = location
    return kit.finish(obj, mat, bevel)


def offset(outline, inset):
    """A convex outline (counter-clockwise) moved inwards by `inset` (mitred corners)."""
    if not inset:
        return list(outline)
    pts = [Vector(p) for p in outline]
    out = []
    for k, p in enumerate(pts):
        a, b = pts[k - 1], pts[(k + 1) % len(pts)]
        e1, e2 = (p - a).normalized(), (b - p).normalized()
        n1, n2 = Vector((-e1.y, e1.x)), Vector((-e2.y, e2.x))
        q = p + (n1 + n2) * (inset / (1 + n1.dot(n2)))
        out.append((q.x, q.y))
    return out


def slab(name, mat, outline, height, inset=0.0, z0=0.0, bevel=0.006):
    """A prism over a convex 2D outline (counter-clockwise), its top moved in by
    `inset`: a pad, plinth or hall body with sloped walls."""
    top_outline = offset(outline, inset)

    def build(bm):
        low = [bm.verts.new((x, y, z0)) for x, y in outline]
        top = [bm.verts.new((x, y, z0 + height)) for x, y in top_outline]
        bm.faces.new(low[::-1])
        bm.faces.new(top)
        for k in range(len(outline)):
            j = (k + 1) % len(outline)
            bm.faces.new((low[k], low[j], top[j], top[k]))

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def prism(name, mat, profile, a0, a1, axis='X', bevel=0.0):
    """Extrudes a 2D profile from a0 to a1 along `axis`: for 'X' the profile is
    (y, z), for 'Y' it is (x, z), for 'Z' it is (x, y)."""
    def point(a, u, v):
        return {'X': (a, u, v), 'Y': (u, a, v), 'Z': (u, v, a)}[axis]

    def build(bm):
        low = [bm.verts.new(point(a0, u, v)) for u, v in profile]
        top = [bm.verts.new(point(a1, u, v)) for u, v in profile]
        bm.faces.new(low)
        bm.faces.new(top[::-1])
        for k in range(len(profile)):
            j = (k + 1) % len(profile)
            bm.faces.new((low[k], low[j], top[j], top[k]))

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def arc(centre, r, a0, a1, steps):
    """Points (u, v) on a circle from angle a0 to a1 (radians)."""
    cu, cv = centre
    return [(cu + r * math.cos(a0 + (a1 - a0) * k / steps), cv + r * math.sin(a0 + (a1 - a0) * k / steps)) for k in range(steps + 1)]


def chamfered(x0, y0, x1, y1, cut):
    """Outline of a rectangle with its corners cut off (`cut` per corner, or a tuple
    for the corners from the front left counter-clockwise)."""
    c = cut if isinstance(cut, tuple) else (cut,) * 4
    corners = (((x0, y0 + c[0]), (x0 + c[0], y0)), ((x1 - c[1], y0), (x1, y0 + c[1])),
               ((x1, y1 - c[2]), (x1 - c[2], y1)), ((x0 + c[3], y1), (x0, y1 - c[3])))
    out = []
    for k, (a, b) in enumerate(corners):
        out += [a, b] if c[k] > 1e-6 else [a]
    return out


def fan(name, m, centre, radius, blades=6):
    """A round roof fan: dark ring, hole, blades as a separate child (they turn about z);
    returns (housing, blades)."""
    centre = Vector(centre)
    housing = kit.merge(name, [
        cylinder(f'{name}Ring', m['steel'], radius + 0.025, 0.04, centre + Vector((0, 0, 0.02)), segments=24, bevel=0.004),
        cylinder(f'{name}Hole', m['dark'], radius, 0.01, centre + Vector((0, 0, 0.041)), segments=24, bevel=0),
    ], centre)
    parts = [cylinder(f'{name}Hub', m['steel_light'], radius * 0.22, 0.02, centre + Vector((0, 0, 0.045)), segments=12, bevel=0)]
    for j in range(blades):
        a = 2 * math.pi * j / blades
        d = Vector((math.cos(a), math.sin(a), 0))
        blade = box(f'{name}Blade{j}', m['steel_light'], (radius * 0.8, radius * 0.28, 0.006), centre + d * radius * 0.55 + Vector((0, 0, 0.045)),
                    bevel=0, rotation=(math.radians(18), 0, a))
        parts.append(blade)
    spinner = kit.merge(f'{name}Blades', parts, centre + Vector((0, 0, 0.045)))
    kit.parent(spinner, housing)
    return housing, spinner


def spin(obj, turns=1, end=None, axis=2):
    """Idle: turns `obj` about a local axis, linear and seamless over the loop."""
    end = end or kit.IDLE_END
    start = obj.rotation_euler.copy()
    a, b = start.copy(), start.copy()
    b[axis] += 2 * math.pi * turns
    kit.keys(obj, 'rotation_euler', {0: a, end: b}, 'LINEAR')


def beacon(name, m, at, colour, holder, pop_at, pattern, lights):
    """A blinking lamp on `holder`: pops up in the Build clip at `pop_at`, blinks in
    the Idle clip after `pattern` (frames on)."""
    housing, light = kit.beacon(name, m, at, colour)
    housing = kit.parent(kit.merge(name, [housing], at), holder)
    kit.parent(light, housing)
    kit.pop(housing, pop_at, 5)
    lights.append((light, pattern))
    return housing


def pulse(obj, low=0.7, high=1.0, cycles=1, end=None):
    """Idle: a glow that swells and fades (scale), seamless over the loop."""
    end = end or kit.IDLE_END
    frames = {}
    for f in range(0, end + 1, 3):
        k = low + (high - low) * (0.5 - 0.5 * math.cos(2 * math.pi * cycles * f / end))
        frames[f] = Vector((k, k, k))
    frames[end] = Vector((low, low, low))
    kit.keys(obj, 'scale', frames)


def clips(idle, lights):
    """Everything keyed so far becomes the Build clip; then the Idle animations
    (callables) and the blinking lights go onto the Idle track."""
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    for obj, animate in idle:
        animate(obj)
        kit.to_track(obj, 'Idle')
    for light, pattern in lights:
        kit.blink(light, pattern)
        kit.to_track(light, 'Idle')


def start(collection, build_end):
    """Clears the collection and sets the scene up for building at the finished pose."""
    kit.COLLECTION = collection
    kit.BUILD_END = build_end
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = build_end + 12
    scene.frame_current = build_end  # parenting reads the evaluated pose


def preview(frames, out_dir, scale, target):
    """kit.render_preview with a camera framing the whole foundation."""
    kit.render_preview([], out_dir)
    for obj in kit.collection().objects:  # the preview shows Build and Idle only
        for track in (obj.animation_data.nla_tracks if obj.animation_data else ()):
            track.mute = track.name not in ('Build', 'Idle')
    cam = bpy.data.objects['PreviewCamera']
    cam.data.ortho_scale = scale
    direction = Vector((math.sin(math.radians(45)) * math.cos(math.radians(30)),
                        -math.cos(math.radians(45)) * math.cos(math.radians(30)),
                        math.sin(math.radians(30))))
    cam.location = Vector(target) + direction * 10
    kit.render_preview(frames, out_dir)


def run(build, out, blend, scale, target, bake=1024):
    """Builds, bakes, exports and saves; `-- --preview f0,f1,… <dir>` renders frames."""
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(bake)
    bpy.context.scene.frame_set(kit.BUILD_END)
    print('export', kit.export_glb(out), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    if '--preview' in args:
        preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2], scale, target)
