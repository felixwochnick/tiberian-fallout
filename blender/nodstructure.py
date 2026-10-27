"""
Tiberian Fallout – shared parts of the big Nod buildings (NAPOWR, NAHAND, NAWEAP,
NARADR, NATECH).

Nod builds in dark concrete and dark armour plate with sharp edges; the house colour
(red for Nod) only on accents: trims, spikes, frames, the hand's stripes.
    Nod_*        concrete: the procedural shader of the Nod defences
                 (nodbuilding.concrete_material: mottling, streaks, speckles, darker in
                 the corners) baked to a texture per object; extra nodColour white
    NodPlate*,   dark armour plate and steel, plain colours; extra nodColour = its own
    NodSteel     colour (applyHouseColour in app/lib/game/models.ts)
    Remap        the house colour
    Lamp*, Glow* emissive bulbs and additive halos as in the other models

Also here: polygon prisms with sloped walls, lofted shells, spikes, pulsing glows,
the preview camera and the build/bake/export main().

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is in
the middle of the foundation on the ground.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import nodbuilding  # noqa: E402 – the Nod concrete shader and its bake

PROJECT = os.path.dirname(HERE)
NOD_RED = '#c42a1c'   # the house colour of the previews (the game paints Remap itself)

# key: (material name, colour); every one gets the extra nodColour
DARK = {
    'nplate': ('NodPlate', '#3c3d42'),
    'nplate_dark': ('NodPlateDark', '#232428'),
    'nsteel': ('NodSteel', '#64676d'),
    'nsteel_light': ('NodSteelLight', '#a3a6aa'),
    'dirt': ('NodDirt', '#7a6744'),
}
# concrete tones
GREY = '#7b7c7e'
LIGHT = '#9a9893'
DARK_GREY = '#4b4c4f'


def dark_material(name, hex_colour, roughness=0.6, metallic=0.4):
    mat = kit.material(name, kit.srgb(hex_colour), roughness, metallic)
    mat['nodColour'] = hex_colour
    return mat


def materials():
    m = kit.materials()
    m['remap'] = kit.material('Remap', kit.srgb(NOD_RED), 0.5, 0.2)
    for key, (name, colour) in DARK.items():
        m[key] = dark_material(name, colour, 0.95 if key == 'dirt' else 0.6, 0.0 if key == 'dirt' else 0.45)
    m['dark']['nodColour'] = '#17181a'
    m['steel']['nodColour'] = '#4a4d50'   # the lamp housings
    m['glow_red'] = kit.material('GlowRed', (0, 0, 0), 1.0, emission=kit.srgb('#ff2a10'), strength=3, alpha=0.25)
    m['ember'] = kit.material('LampEmber', kit.srgb('#ff4a20'), 0.3, emission=kit.srgb('#ff3a10'), strength=6)
    m['hazard'] = kit.material('HazardYellow', kit.srgb('#d8a81c'), 0.6)
    return m


def concrete(name, parts, root, colour=GREY, pivot=(0, 0, 0)):
    """Merges `parts` into one object in baked Nod concrete of `colour`."""
    obj = kit.merge(name, parts, pivot)
    obj.data.materials.clear()
    obj.data.materials.append(nodbuilding.concrete_material(f'Nod_{name}', colour, root))
    return obj


# --------------------------------------------------------------------------- shapes

def prism(name, mat, bottom, top, z0, z1, bevel=0.01):
    """A solid between two outlines (lists of (x, y), same count, counter-clockwise):
    the bottom one at height z0, the top one at z1 – sloped walls, sharp Nod shapes."""
    def build(bm):
        low = [bm.verts.new((x, y, z0)) for x, y in bottom]
        high = [bm.verts.new((x, y, z1)) for x, y in top]
        bm.faces.new(low[::-1])
        bm.faces.new(high)
        n = len(bottom)
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((low[k], low[j], high[j], high[k]))

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def chamfered(cx, cy, sx, sy, c):
    """Outline of a rectangle (centre, size) with its corners cut by c, counter-clockwise."""
    x0, x1, y0, y1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def loft(name, sections, material_of, cap=None):
    """A shell through cross-sections (lists of points of equal count, in order);
    material_of(i, k) → material of the face between sections i, i+1 and points k,
    k+1. `cap`: material to close the first and the last section with (None: open)."""
    import bmesh
    mats = []

    def index(mat):
        if mat not in mats:
            mats.append(mat)
        return mats.index(mat)

    def build(bm):
        rings = [[bm.verts.new(p) for p in section] for section in sections]
        for i, (a, b) in enumerate(zip(rings, rings[1:])):
            for k in range(len(a) - 1):
                face = bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
                face.material_index = index(material_of(i, k))
        if cap is not None:
            for ring in (rings[0], rings[-1]):
                face = bm.faces.new(ring)
                face.material_index = index(cap)

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for mat in mats:
        mesh.materials.append(mat)
        mat.use_backface_culling = True
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    kit.collection().objects.link(obj)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj


def lathe(name, mat, profile, location, segments=32, bevel=0.0):
    """Surface of revolution from (radius, height) points, bottom to top, capped."""
    def build(bm):
        rings = []
        for r, z in profile:
            rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                          for a in (2 * math.pi * i / segments for i in range(segments))])
        for lower, upper in zip(rings, rings[1:]):
            for i in range(segments):
                j = (i + 1) % segments
                bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])

    obj = kit.mesh_object(name, build)
    obj.location = location
    return kit.finish(obj, mat, bevel)


def spike(name, mat, root, direction, length, width, thickness, droop=0.0):
    """A flat, sharp blade from `root` along `direction`, its tip lowered by `droop`."""
    d = Vector(direction).normalized()
    side = Vector((-d.y, d.x, 0)) * width / 2
    up = Vector((0, 0, thickness / 2))
    root = Vector(root)
    tip = root + d * length - Vector((0, 0, droop))
    return kit.hexahedron(name, mat, (
        root - side - up, root + side - up, tip + side * 0.08 - up * 0.3, tip - side * 0.08 - up * 0.3,
        root - side + up, root + side + up, tip + side * 0.08 + up * 0.3, tip - side * 0.08 + up * 0.3), bevel=0.003)


# --------------------------------------------------------------------------- animation

def pulse(obj, frames, low=0.6, high=1.15, phase=0.0, cycles=1):
    """Keys a glow swelling and fading (scale), `cycles` times a loop of `frames`."""
    base = Vector(obj.scale)
    keys = {}
    for f in range(0, frames + 1, 3):
        t = (math.sin(2 * math.pi * (cycles * f / frames + phase)) + 1) / 2
        keys[f] = base * (low + (high - low) * t)
    keys[frames] = keys[0]
    kit.keys(obj, 'scale', keys, 'LINEAR')


def spin(obj, frames, axis=2, turns=1):
    """Keys whole turns about one local axis over the loop."""
    rest = Vector(obj.rotation_euler)
    keys = {}
    for f in range(0, frames + 1, 5):
        r = rest.copy()
        r[axis] += 2 * math.pi * turns * f / frames
        keys[f] = r
    end = rest.copy()
    end[axis] += 2 * math.pi * turns
    keys[frames] = end
    kit.keys(obj, 'rotation_euler', keys, 'LINEAR')
    obj.rotation_euler = rest


def rise(obj, start, length, depth):
    """Keys the object rising out of the ground (from `depth` below) with a small overshoot."""
    p = Vector(obj.location)
    kit.keys(obj, 'location', {0: p - Vector((0, 0, depth)), start: p - Vector((0, 0, depth)),
                               start + length * 0.85: p + Vector((0, 0, 0.01)), start + length: p})


def clips(lights=(), idle=()):
    """Everything keyed so far goes on the track Build; then the lights blink
    ((object, frames on)) and the idle animations ((object, keyer)) go on Idle."""
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    for obj, pattern in lights:
        kit.blink(obj, pattern)
        kit.to_track(obj, 'Idle')
    for obj, animate in idle:
        animate(obj)
        kit.to_track(obj, 'Idle')


def lamp(m, holder, name, at, colour, start):
    """A beacon on `holder` that pops in at `start`; returns its light (blinks in Idle)."""
    housing, light = kit.beacon(name, m, at, colour)
    housing = kit.parent(kit.merge(name, [housing], at), holder)
    kit.parent(light, housing)
    kit.pop(housing, start, 5)
    return light


# --------------------------------------------------------------------------- run

def start(collection, root_name, build_end, idle_end=60):
    kit.COLLECTION = collection
    kit.BUILD_END = build_end
    kit.IDLE_END = idle_end
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = build_end + 12
    scene.frame_current = build_end  # parenting reads the evaluated pose: the finished building
    return kit.empty(root_name)


def preview(frames, out_dir, ortho, target):
    """kit.render_preview with a camera framing the foundation."""
    kit.render_preview([], out_dir)
    cam = bpy.data.objects['PreviewCamera']
    cam.data.ortho_scale = ortho
    direction = Vector((math.sin(math.radians(45)) * math.cos(math.radians(30)),
                        -math.cos(math.radians(45)) * math.cos(math.radians(30)),
                        math.sin(math.radians(30))))
    cam.location = Vector(target) + direction * 10
    kit.render_preview(frames, out_dir)


def main(build, out, blend, ortho=2.9, target=(0, 0, 0.35), texture=512):
    """Builds, bakes the concrete, saves the .blend, exports the GLB;
    -- --preview 0,40,72 <dir> renders frames through the game's camera."""
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    bpy.context.scene.frame_set(kit.BUILD_END)
    nodbuilding.bake(texture)
    bpy.context.scene.frame_set(kit.BUILD_END)
    print('export', kit.export_glb(out), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    if '--preview' in args:
        preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2], ortho, target)
