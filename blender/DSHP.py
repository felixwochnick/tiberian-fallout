"""
Tiberian Fallout – GDI dropship (DSHP), after Tiberian Sun.

A long armoured fuselage with the cockpit at the nose, a cargo bay underneath with a
ramp at the back, and four tilting engine nacelles on stub wings. Desert camouflage
(baked), the GDI emblem and "CP 034" on the sides of the cargo bay, navigation
lights (red left, green right), a white strobe on the tail and a red beacon below.

The origin is on the ground under the middle of the ship. The clips carry the height:
flying at FLY_HEIGHT, landed on the ground. The game moves the ship over the map.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Fly      loop, 1 s: cruising, engines forward, a gentle sway
    Land     once, 3 s: from Fly: flares, tilts the engines down, sinks onto its
             legs and opens the ramp
    Landed   loop, 2 s: on the ground, engines idling, ramp open
    TakeOff  once, 3 s: from Landed: closes the ramp, lifts off, pulls the legs in,
             tilts the engines forward and climbs to Fly
    Crash    once, 3.5 s: from Fly: hit, an engine catches fire, it spirals down,
             explodes on impact, the tail breaks and an engine tears off; it ends as a
             burning wreck
    Lights   loop, 2 s: strobe and beacon blink (plays all the time)

Nodes for the game: CargoExit (where unloaded units come out, at the ramp's end).

Run headless:

    Blender -b --factory-startup --python blender/DSHP.py

Units: 1 = one map cell. Blender Z is up; -Y is the front (the nose; glTF +Z).
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

kit.COLLECTION = 'GDIDropship'
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'DSHP.glb')
BLEND = os.path.join(HERE, 'DSHP.blend')

FLY_HEIGHT = 1.6
HIDDEN = kit.HIDDEN
GEAR_TOP = 0.14         # underside of the cargo bay; the legs reach from there to the ground
ENGINES = (             # pivot of each nacelle: front/back, left/right
    Vector((-0.74, -0.32, 0.48)), Vector((0.74, -0.32, 0.48)),
    Vector((-0.72, 0.6, 0.46)), Vector((0.72, 0.6, 0.46)),
)
TILT_FLY = -5           # engine tilt in degrees (negative: the nozzle swings down)
TILT_HOVER = -90

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


# --------------------------------------------------------------------------- helpers

def loft(name, mat, sections, chamfer=0.3):
    """Hull through octagonal cross sections (y, half width, bottom, top), capped."""
    def ring(y, hw, zb, zt):
        c = min(hw, (zt - zb) / 2) * chamfer
        return [(hw, y, zb + c), (hw, y, zt - c), (hw - c, y, zt), (-hw + c, y, zt),
                (-hw, y, zt - c), (-hw, y, zb + c), (-hw + c, y, zb), (hw - c, y, zb)]

    def build(bm):
        rings = [[bm.verts.new(p) for p in ring(*s)] for s in sections]
        for a, b in zip(rings, rings[1:]):
            for i in range(8):
                j = (i + 1) % 8
                bm.faces.new((a[i], a[j], b[j], b[i]))
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])

    obj = kit.mesh_object(name, build)
    kit.finish(obj, mat, 0)
    for poly in obj.data.polygons:
        poly.use_smooth = False  # faceted armour plates
    return obj


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def emblem_image(size=256):
    """The GDI emblem, dark, on a transparent background (for decals)."""
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    ex = (xs + 0.5 - size / 2) / (size * 0.47)
    ey = -(ys + 0.5 - size / 2) / (size * 0.47)
    inside = np.zeros((size, size), bool)
    for poly in kit.logo_polygons():
        p = np.array(poly, np.float32)
        for (x0, y0), (x1, y1) in zip(p, np.roll(p, -1, axis=0)):
            if y0 == y1:
                continue
            crosses = (ey >= min(y0, y1)) & (ey < max(y0, y1))
            inside ^= crosses & (ex < x0 + (ey - y0) * (x1 - x0) / (y1 - y0))
    rgba = np.zeros((size, size, 4), np.float32)
    rgba[..., :3] = np.array((0x1c, 0x1b, 0x16), np.float32) / 255
    rgba[..., 3] = inside * 0.9
    image = bpy.data.images.get('EmblemGDI') or bpy.data.images.new('EmblemGDI', size, size, alpha=True)
    image.pixels.foreach_set(rgba.ravel())
    image.file_format = 'PNG'
    image.pack()
    return image


def decal_material():
    mat = bpy.data.materials.get('Emblem') or bpy.data.materials.new('Emblem')
    mat.use_nodes = True
    mat.surface_render_method = 'BLENDED'
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.8
    tex = nt.nodes.get('EmblemTexture') or nt.nodes.new('ShaderNodeTexImage')
    tex.name = 'EmblemTexture'
    tex.image = emblem_image()
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
    return mat


def on_side(obj, side, centre):
    """Lays a flat object (made in the XY plane, facing +Z) onto a side of the hull:
    its x along the ship (reading towards the tail on the right side), its y up, its
    z out of the side."""
    up = Vector((0, 0, 1))
    along = Vector((0, side, 0))
    out = along.cross(up)
    rot = Matrix((along, up, out)).transposed().to_4x4()
    obj.data.transform(rot)
    obj.location = centre + out * 0.004
    return obj


def text_mesh(name, text, mat, size):
    curve = bpy.data.curves.new(name, 'FONT')
    curve.body = text
    curve.size = size
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    holder = bpy.data.objects.new(name + 'Curve', curve)
    kit.collection().objects.link(holder)
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(holder.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(holder, do_unlink=True)
    bpy.data.curves.remove(curve)
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    kit.collection().objects.link(obj)
    return obj


def quad(name, mat, w, h):
    def build(bm):
        uv = bm.loops.layers.uv.new('UVMap')
        v = [bm.verts.new((x * w / 2, y * h / 2, 0)) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        face = bm.faces.new(v)
        for loop, coords in zip(face.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uv].uv = coords

    obj = kit.mesh_object(name, build)
    obj.data.materials.append(mat)
    return obj


# --------------------------------------------------------------------------- model parts

HULL = (  # y, half width, bottom, top
    (-1.08, 0.05, 0.36, 0.42), (-1.0, 0.14, 0.3, 0.48), (-0.85, 0.2, 0.26, 0.56), (-0.6, 0.25, 0.24, 0.6),
    (-0.3, 0.27, 0.24, 0.61), (0.2, 0.27, 0.26, 0.59), (0.6, 0.22, 0.3, 0.55),
)
TAIL = ((0.6, 0.22, 0.3, 0.55), (0.95, 0.14, 0.36, 0.5), (1.14, 0.08, 0.4, 0.47))


def materials():
    m = kit.materials()
    m.update({
        'pod_dark': material('PodDark', srgb('#2b3036'), 0.6, 0.6),
        'glass': material('Canopy', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'red': material('WarningRed', srgb('#b3271c'), 0.6),
        'stencil': material('Stencil', srgb('#e2dcc2'), 0.7),
        'plume': material('GlowPlume', (0, 0, 0), 1.0, emission=srgb('#9fd4ff'), strength=3, alpha=0.35),
        'fire': material('GlowFire', (0, 0, 0), 1.0, emission=srgb('#ff7a1a'), strength=4, alpha=0.6),
        'blast': material('GlowBlast', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=5, alpha=0.5),
        'glow_white': material('GlowWhite', (0, 0, 0), 1.0, emission=srgb('#fff2c8'), strength=3, alpha=0.25),
    })
    return m


def hull(m, root):
    body = camo(loft('Hull', m['sand'], HULL), root)
    tail = camo(loft('Tail', m['sand'], TAIL), root)
    bay = kit.hexahedron('CargoBay', m['sand'], (
        (0.24, -0.45, GEAR_TOP), (-0.24, -0.45, GEAR_TOP), (-0.24, 0.45, GEAR_TOP), (0.24, 0.45, GEAR_TOP),
        (0.3, -0.62, 0.27), (-0.3, -0.62, 0.27), (-0.3, 0.62, 0.27), (0.3, 0.62, 0.27)), bevel=0.01)
    bay = camo(kit.merge('CargoBay', [bay]), root)

    parts = [
        loft('Canopy', m['glass'], ((-0.95, 0.07, 0.47, 0.5), (-0.86, 0.12, 0.535, 0.572), (-0.74, 0.14, 0.582, 0.612), (-0.68, 0.12, 0.598, 0.616))),
        box('Spine', m['sand_light'], (0.16, 1.0, 0.05), (0, 0.15, 0.625), bevel=0.012),
        box('BayStrake', m['concrete_dark'], (0.62, 1.1, 0.025), (0, 0.0, 0.265), bevel=0.004),
        box('BayInside', m['dark'], (0.34, 0.02, 0.1), (0, 0.6, 0.2), bevel=0),
    ]
    for i in range(4):  # vents on the spine
        parts.append(box(f'Vent{i}', m['dark'], (0.1, 0.05, 0.012), (0, -0.2 + i * 0.16, 0.652), bevel=0.003))
    for s in (-1, 1):
        parts.append(beam(f'Antenna{s}', m['steel'], (s * 0.05, -0.55, 0.6), (s * 0.06, -0.52, 0.76), 0.008))
        parts.append(box(f'NoseStripe{s}', m['red'], (0.01, 0.12, 0.03), (s * 0.205, -0.86, 0.36), bevel=0.002))
        # stub wings to the nacelles
        for k, pivot in enumerate(e for e in ENGINES if (e.x > 0) == (s > 0)):
            parts.append(box(f'Wing{s}{k}', m['sand_light'], (abs(pivot.x) - 0.36, 0.12, 0.035),
                             (s * (abs(pivot.x) + 0.2) / 2, pivot.y, pivot.z), bevel=0.01))
        # twin tail fins
        parts.append(kit.hexahedron(f'Fin{s}', m['sand_light'], (
            (s * 0.06, 0.9, 0.48), (s * 0.1, 0.9, 0.48), (s * 0.1, 1.08, 0.46), (s * 0.06, 1.08, 0.46),
            (s * 0.08, 1.02, 0.64), (s * 0.11, 1.02, 0.64), (s * 0.11, 1.1, 0.63), (s * 0.08, 1.1, 0.63)), bevel=0.004))
    details = kit.merge('HullDetails', parts)

    # emblem and "CP 034" on both sides of the hull (seen from above, unlike the bay's)
    decals = []
    emblem = decal_material()
    for s in (-1, 1):
        decals.append(on_side(quad(f'Emblem{s}', emblem, 0.17, 0.17), s, Vector((s * 0.27, -0.38, 0.43))))
        decals.append(on_side(text_mesh(f'Serial{s}', 'CP 034', m['stencil'], 0.08), s, Vector((s * 0.27, 0.05, 0.43))))
    return body, tail, bay, details, decals


def nacelle(m, root, i, pivot):
    """Engine nacelle around its pivot: camouflaged pod, dark intake and nozzle, a red
    warning stripe on the inner side, a navigation light outside, the exhaust plume."""
    side = 1 if pivot.x > 0 else -1
    pod = camo(kit.merge(f'Nacelle{i}', [box(f'Nacelle{i}', m['sand'], (0.24, 0.46, 0.25), pivot, bevel=0.06)], pivot), root)
    parts = [
        box(f'Intake{i}', m['dark'], (0.17, 0.03, 0.17), pivot + Vector((0, -0.225, 0)), bevel=0.01),
        box(f'Nozzle{i}', m['dark'], (0.18, 0.03, 0.18), pivot + Vector((0, 0.225, 0)), bevel=0.01),
        box(f'NozzleRim{i}', m['steel'], (0.22, 0.02, 0.22), pivot + Vector((0, 0.215, 0)), bevel=0.01),
        box(f'Stripe{i}', m['red'], (0.01, 0.2, 0.03), pivot + Vector((-side * 0.121, -0.04, 0.06)), bevel=0.002),
        box(f'Band{i}', m['remap'], (0.245, 0.03, 0.255), pivot + Vector((0, -0.12, 0)), bevel=0.01),
    ]
    details = kit.merge(f'NacelleDetails{i}', parts, pivot)
    nav = 'green' if side > 0 else 'red'
    bulb = kit.merge(f'NavLight{i}', [
        sphere(f'NavBulb{i}', m[f'lamp_{nav}'], 0.016, pivot + Vector((side * 0.13, -0.15, 0.08)), 10),
        sphere(f'NavHalo{i}', m[f'glow_{nav}'], 0.035, pivot + Vector((side * 0.13, -0.15, 0.08)), 10),
    ], pivot)
    plume = cylinder(f'Plume{i}', m['plume'], 0.075, 0.3, pivot + Vector((0, 0.39, 0)), rotation=(math.pi / 2, 0, 0),
                     segments=16, bevel=0, radius2=0.02)
    plume = kit.merge(f'Plume{i}', [plume], pivot + Vector((0, 0.24, 0)))
    return pod, details, bulb, plume


def gear(m):
    """Four legs under the cargo bay; their object's origin is at the bay's underside,
    so scaling it in z pulls them in."""
    parts = []
    for x in (-0.18, 0.18):
        for y in (-0.36, 0.36):
            parts.append(cylinder(f'Leg{x}{y}', m['steel_light'], 0.018, GEAR_TOP, (x, y, GEAR_TOP / 2), segments=8, bevel=0))
            parts.append(beam(f'Strut{x}{y}', m['steel'], (x, y, 0.04), (x * 0.6, y * 0.8, GEAR_TOP), 0.012))
            parts.append(cylinder(f'Pad{x}{y}', m['pod_dark'], 0.045, 0.02, (x, y, 0.01), segments=12, bevel=0.003))
    return kit.merge('Gear', parts, (0, 0, GEAR_TOP))


RAMP_HINGE = Vector((0, 0.45, GEAR_TOP))
RAMP_CLOSED = math.degrees(math.atan2(0.27 - GEAR_TOP, 0.62 - 0.45))   # up along the bay's back
RAMP_OPEN = -math.degrees(math.asin(GEAR_TOP / math.hypot(0.17, 0.27 - GEAR_TOP)))


def ramp(m):
    """Ramp in the back of the cargo bay, made lying flat behind its hinge; rotated about
    x it closes the bay (RAMP_CLOSED) or reaches the ground (RAMP_OPEN)."""
    length = math.hypot(0.17, 0.27 - GEAR_TOP)
    parts = [box('RampPlate', m['steel'], (0.4, length, 0.02), RAMP_HINGE + Vector((0, length / 2, 0)), bevel=0.004)]
    for i in range(4):
        parts.append(box(f'RampGrip{i}', m['steel_light'], (0.36, 0.008, 0.006), RAMP_HINGE + Vector((0, 0.04 + i * 0.045, 0.012)), bevel=0))
    return kit.merge('Ramp', parts, RAMP_HINGE)


def fire(m, name, centre, size):
    """A cluster of flame blobs (additive); hidden unless burning."""
    blobs = [sphere(f'{name}{k}', m['fire'], size * (0.6 + 0.2 * (k % 3)), centre + Vector(((k % 3 - 1) * size * 0.6, (k // 3 - 0.5) * size * 0.8, (k % 2) * size * 0.5)), 10)
             for k in range(6)]
    return kit.merge(name, blobs, centre)


# --------------------------------------------------------------------------- animation

CHANNELS = []  # (object, property) keyed in every flight clip


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def span(f, start, end):
    return ease((f - start) / (end - start))


def mix(a, b, t):
    return a + (b - a) * t


def flight_clip(name, frames, pose):
    """Keys every flight channel at every frame from pose(f) → {(obj, prop): value} and
    makes it the clip `name` (an NLA track per object)."""
    objects = []
    for obj, _ in CHANNELS:
        if obj not in objects:
            objects.append(obj)
    for obj in objects:
        obj.animation_data_create().action = bpy.data.actions.new(f'{name}_{obj.name}')
    prefs = bpy.context.preferences.edit
    prefs.keyframe_new_interpolation_type = 'LINEAR'
    for f in range(frames + 1):
        values = pose(f)
        for obj, prop in CHANNELS:
            setattr(obj, prop, values[(obj.name, prop)])
            obj.keyframe_insert(prop, frame=f)
    for obj in objects:
        kit.to_track(obj, name)


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = 105

    m = materials()
    root = kit.empty('GDIDropship')
    ship = kit.parent(kit.empty('Ship'), root)          # all flight motion
    body, tail_part, bay, details, decals = hull(m, root)
    for obj in (body, bay, details, *decals):
        kit.parent(obj, ship)
    tail = kit.parent(kit.empty('TailJoint', (0, 0.6, 0.42)), ship)   # breaks off in Crash
    kit.parent(tail_part, tail)

    engines, plumes = [], []
    for i, pivot in enumerate(ENGINES):
        joint = kit.parent(kit.empty(f'Engine{i}', pivot), ship)
        *parts, plume = nacelle(m, root, i, pivot)
        for obj in (*parts, plume):
            kit.parent(obj, joint)
        engines.append(joint)
        plumes.append(plume)

    legs = kit.parent(gear(m), ship)
    hatch = kit.parent(ramp(m), ship)
    exit_node = kit.parent(kit.empty('CargoExit', (0, 0.85, 0)), root)
    exit_node.empty_display_size = 0.1

    # lights: strobe on the tail, beacon under the belly
    strobe = kit.merge('Strobe', [sphere('StrobeBulb', m['lamp_white'], 0.018, (0, 1.06, 0.66), 10),
                                  sphere('StrobeHalo', m['glow_white'], 0.05, (0, 1.06, 0.66), 10)], (0, 1.06, 0.66))
    kit.parent(strobe, tail)
    beacon = kit.merge('Beacon', [sphere('BeaconBulb', m['lamp_red'], 0.02, (0, -0.2, 0.235), 10),
                                  sphere('BeaconHalo', m['glow_red'], 0.05, (0, -0.2, 0.235), 10)], (0, -0.2, 0.235))
    kit.parent(beacon, ship)

    burning = kit.parent(fire(m, 'EngineFire', ENGINES[1] + Vector((0, 0.05, 0.12)), 0.08), ship)
    wreck_fire = kit.parent(fire(m, 'WreckFire', Vector((0.05, 0.1, 0.5)), 0.13), ship)
    blast = kit.parent(kit.merge('Blast', [sphere('BlastBall', m['blast'], 0.6, (0, 0, 0.3), 20)], (0, 0, 0.3)), ship)

    CHANNELS[:] = [(ship, 'location'), (ship, 'rotation_euler'), (legs, 'scale'), (hatch, 'rotation_euler'),
                   (tail, 'location'), (tail, 'rotation_euler'), (burning, 'scale'), (wreck_fire, 'scale'), (blast, 'scale')]
    for joint, plume in zip(engines, plumes):
        CHANNELS.extend([(joint, 'location'), (joint, 'rotation_euler'), (plume, 'scale')])

    rad = math.radians
    hidden = Vector((HIDDEN,) * 3)

    def base(height, tilt, thrust, gear_out, ramp_angle, pitch=0.0, roll=0.0, yaw=0.0, y=0.0):
        values = {
            ('Ship', 'location'): Vector((0, y, height)),
            ('Ship', 'rotation_euler'): Vector((rad(pitch), rad(roll), rad(yaw))),
            ('Gear', 'scale'): Vector((1, 1, mix(0.05, 1, gear_out))),
            ('Ramp', 'rotation_euler'): Vector((rad(ramp_angle), 0, 0)),
            ('TailJoint', 'location'): Vector((0, 0.6, 0.42)),
            ('TailJoint', 'rotation_euler'): Vector((0, 0, 0)),
            ('EngineFire', 'scale'): hidden,
            ('WreckFire', 'scale'): hidden,
            ('Blast', 'scale'): hidden,
        }
        for i, (joint, plume) in enumerate(zip(engines, plumes)):
            values[(joint.name, 'location')] = ENGINES[i].copy()
            values[(joint.name, 'rotation_euler')] = Vector((rad(tilt), 0, 0))
            values[(plume.name, 'scale')] = Vector((1, max(thrust, HIDDEN), 1)) if thrust > 0 else hidden
        return values

    def flicker(f, amount=0.12):
        return 1 + amount * math.sin(f * 2.3) * math.sin(f * 0.7 + 1)

    # ---- Fly (1 s loop)
    def fly(f):
        t = 2 * math.pi * f / 30
        return base(FLY_HEIGHT + 0.03 * math.sin(t), TILT_FLY, flicker(f), 0, RAMP_CLOSED, pitch=3, roll=2 * math.sin(t))

    flight_clip('Fly', 30, fly)

    # ---- Land (3 s)
    def land(f):
        descent = span(f, 18, 80)
        height = FLY_HEIGHT * (1 - descent) ** 1.6 if f < 80 else 0.0
        if 80 <= f < 88:  # settles onto its legs
            height = -0.018 * math.sin(math.pi * (f - 80) / 8)
        pitch = mix(3, -8, span(f, 0, 18)) if f < 18 else mix(-8, 0, span(f, 18, 55))
        thrust = mix(1.0, 1.35, span(f, 10, 35)) if f < 70 else mix(1.35, 0.35, span(f, 70, 86))
        return base(height, mix(TILT_FLY, TILT_HOVER, span(f, 5, 38)), thrust * flicker(f), span(f, 48, 62),
                    mix(RAMP_CLOSED, RAMP_OPEN, span(f, 82, 90)), pitch=pitch, roll=2 * math.sin(f * 0.21) * (1 - descent))

    flight_clip('Land', 90, land)

    # ---- Landed (2 s loop)
    flight_clip('Landed', 60, lambda f: base(0, TILT_HOVER, 0.35 * flicker(f, 0.25), 1, RAMP_OPEN))

    # ---- TakeOff (3 s)
    def take_off(f):
        climb = span(f, 20, 78)
        height = FLY_HEIGHT * climb ** 1.3
        pitch = mix(0, 6, span(f, 50, 70)) if f < 70 else mix(6, 3, span(f, 70, 90))
        thrust = mix(0.35, 1.35, span(f, 6, 24)) if f < 75 else mix(1.35, 1.0, span(f, 75, 90))
        return base(height, mix(TILT_HOVER, TILT_FLY, span(f, 46, 82)), thrust * flicker(f), 1 - span(f, 28, 42),
                    mix(RAMP_OPEN, RAMP_CLOSED, span(f, 0, 12)), pitch=pitch)

    flight_clip('TakeOff', 90, take_off)

    # ---- Crash (3.5 s)
    def crash(f):
        if f < 62:  # hit, burning engine, spiral dive
            t = f / 62
            height = FLY_HEIGHT * (1 - t ** 1.8) + 0.12 * t
            v = base(height, TILT_FLY, flicker(f, 0.4) * (1 - 0.5 * t), 0, RAMP_CLOSED,
                     pitch=mix(3, 22, t), roll=mix(0, 28, span(f, 0, 30)) + 6 * math.sin(f * 0.5) * (1 - t),
                     yaw=200 * t ** 1.4, y=-0.9 * t)
            v[('EngineFire', 'scale')] = Vector((1, 1, 1)) * span(f, 2, 10) * flicker(f, 0.3)
            v[('Engine1', 'rotation_euler')] = Vector((rad(TILT_FLY + 25 * math.sin(f * 0.6) * span(f, 0, 12)), 0, 0))
            return v
        # impact, slide, the wreck burns
        t = span(f, 62, 90)
        v = base(0.02 * math.sin(math.pi * span(f, 62, 72)), TILT_FLY, 0, 0, RAMP_CLOSED,
                 pitch=mix(22, -3, span(f, 62, 70)), roll=mix(28, 9, t), yaw=200 + 25 * t, y=-0.9 - 0.45 * t)
        v[('Ship', 'location')].z -= 0.13  # on its belly, legs up
        v[('Blast', 'scale')] = Vector((1, 1, 1)) * (math.sin(math.pi * span(f, 62, 78)) if f < 78 else HIDDEN) + Vector((HIDDEN,) * 3)
        v[('EngineFire', 'scale')] = Vector((1, 1, 1)) * 1.4 * flicker(f, 0.3)
        v[('WreckFire', 'scale')] = Vector((1, 1, 1)) * span(f, 64, 74) * flicker(f + 7, 0.3)
        # the tail breaks and droops, the front right engine tears off and lies askew
        v[('TailJoint', 'rotation_euler')] = Vector((rad(18 * t), rad(-8 * t), rad(16 * t)))
        v[('TailJoint', 'location')] = Vector((0.03 * t, 0.6 + 0.08 * t, 0.42 - 0.06 * t))
        v[('Engine1', 'location')] = ENGINES[1] + Vector((0.22, -0.12, -0.08)) * t
        v[('Engine1', 'rotation_euler')] = Vector((rad(TILT_FLY - 35 * t), rad(50 * t), rad(30 * t)))
        v[('Engine0', 'rotation_euler')] = Vector((rad(TILT_FLY + 20 * t), 0, 0))
        return v

    flight_clip('Crash', 105, crash)

    # ---- Lights (always): strobe double flash, beacon once a second
    kit.blink(strobe, kit.flashes((0, 2), (5, 2), (30, 2), (35, 2)))
    kit.to_track(strobe, 'Lights')
    kit.blink(beacon, kit.flashes((10, 8), (40, 8)))
    kit.to_track(beacon, 'Lights')
    return len(kit.collection().objects)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(512)
    bpy.context.scene.frame_set(0)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)


if __name__ == '__main__' and bpy.app.background:
    main()
