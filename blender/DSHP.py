"""
Tiberian Fallout – GDI dropship (DSHP), after Tiberian Sun.

Two parts, after help/buildings/GDI/DSHP/img_1-3.png: the aircraft and the cargo
container clamped under it.

The aircraft: a slim fuselage with a deep rounded nose (canopy slits, headlight, the
GDI emblem on the cheeks), a ridge along the top and a tail boom; four engine pods
hang at the ends of long thin pylon arms, far out from the fuselage, a front and a
back pair with a wide gap between them. The pods are rounded boxes with dark intakes
at the front, nozzles at the back, lift vents below and red chevrons.

The container (img_3): a long box whose lower side panels slope inwards, a recessed
slatted section in the middle of each side, the GDI emblem and "CP 034" on the
panels, the door with the ramp at the back. Landed it stands on the ground and the
cargo (up to an MCV) drives out over the ramp.

Desert camouflage (baked), navigation lights on the pods (red left, green right), a
white strobe on the tail and a red beacon under the nose.

The origin is on the ground under the middle of the ship. The clips carry the height:
flying at FLY_HEIGHT, landed on the ground. The game moves the ship over the map.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Fly      loop, 1 s: cruising steadily, engines forward
    Land     once, 3 s: from Fly: flares, tilts the engines down, sinks onto its
             legs and opens the ramp
    Landed   loop, 2 s: on the ground, engines idling, ramp open
    TakeOff  once, 3 s: from Landed: closes the ramp, lifts off, pulls the legs in,
             tilts the engines forward and climbs to Fly
    Crash    once, 3.5 s: from Fly: hit, an engine catches fire, it spirals down,
             explodes on impact, the tail breaks and an engine tears off; it ends as a
             burning wreck
    Lights   loop, 2 s: strobe and beacon blink (plays all the time)

Nodes for the game: CargoExit (where unloaded units come out, past the ramp's end).

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
GEAR_TOP = 0.06         # underside of the container (its floor); the feet reach from there to the ground
BOX = (0.72, 1.35, 0.85)  # container: half width at the belt, half length, height (the top, where the aircraft sits)
BOX_BOTTOM = (0.6, 1.15)  # half width and front of the bottom (the panels slope in below the belt)
BOX_TOP = 0.6          # half width of the top (the panels slope in above the belt)
BOX_BELT = 0.4          # the widest line of the flat hexagonal cross-section
ENGINES = (             # pivot (middle) of each pod: front/back, left/right
    Vector((-1.05, -1.0, 1.22)), Vector((1.05, -1.0, 1.22)),
    Vector((-1.05, 1.1, 1.22)), Vector((1.05, 1.1, 1.22)),
)
POD = (0.42, 0.9, 0.55)  # width, length, height of a pod
ARM_Z = 1.32            # height of the pylon arms
TILT_FLY = -2           # pod tilt in degrees (negative: the nozzle swings down)
TILT_HOVER = -12        # hovering, the thrust goes out of the lift vents below
TAIL_JOINT = Vector((0, 1.25, 1.15))

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


def on_side(obj, side, centre, lean=0.0):
    """Lays a flat object (made in the XY plane, facing +Z) onto a side of the hull:
    its x along the ship (reading towards the tail on the right side), its y up, its
    z out of the side; `lean` (radians) tilts it back for a side sloping inwards."""
    along = Vector((0, side, 0))
    out = along.cross(Vector((0, 0, 1)))
    up = Vector((0, 0, 1)) * math.cos(lean) - out * math.sin(lean)
    out = out * math.cos(lean) + Vector((0, 0, 1)) * math.sin(lean)
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

HULL = (  # y, half width, bottom, top: the deep rounded nose, then the slim fuselage on the container
    (-2.3, 0.1, 0.9, 1.08), (-2.22, 0.3, 0.7, 1.25), (-2.05, 0.43, 0.56, 1.37), (-1.8, 0.48, 0.52, 1.43),
    (-1.55, 0.46, 0.6, 1.45), (-1.38, 0.36, BOX[2] - 0.02, 1.43), (-1.15, 0.31, BOX[2] - 0.02, 1.42), (1.25, 0.3, BOX[2] - 0.02, 1.38),
)
TAIL = ((1.25, 0.3, BOX[2] - 0.02, 1.38), (1.9, 0.18, 1.05, 1.34), (2.45, 0.09, 1.13, 1.3))  # the tail boom


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
    """The aircraft's fuselage with its details and the pylon arms (on the ship), and
    the tail boom (on the tail joint, it breaks off in Crash)."""
    body = camo(loft('Hull', m['sand'], HULL, chamfer=0.45), root)
    tail = camo(loft('Tail', m['sand'], TAIL, chamfer=0.4), root)

    parts = [
        loft('Canopy', m['glass'], ((-2.17, 0.1, 1.17, 1.22), (-2.03, 0.22, 1.29, 1.37), (-1.86, 0.26, 1.37, 1.44), (-1.74, 0.2, 1.41, 1.455))),
        sphere('Headlight', m['lamp_white'], 0.035, (0, -2.3, 1.0), 10),
        sphere('HeadlightHalo', m['glow_white'], 0.09, (0, -2.3, 1.0), 10),
        box('Ridge', m['sand_light'], (0.14, 2.6, 0.06), (0, -0.1, 1.43), bevel=0.02),
        box('Clamp', m['concrete_dark'], (0.66, 2.5, 0.05), (0, 0, BOX[2] + 0.005), bevel=0.01),
        box('Stabiliser', m['sand_light'], (0.8, 0.22, 0.03), (0, 2.3, 1.25), bevel=0.01),
    ]
    for k in range(4):  # vents along the ridge
        parts.append(box(f'Vent{k}', m['dark'], (0.08, 0.05, 0.012), (0, -1.2 + 0.25 * k, 1.462), bevel=0.003))
    for s in (-1, 1):
        parts.append(beam(f'Antenna{s}', m['steel'], (s * 0.06, -1.55, 1.42), (s * 0.07, -1.5, 1.62), 0.012))
        parts.append(box(f'NoseStripe{s}', m['red'], (0.012, 0.14, 0.035), (s * 0.39, -2.15, 0.78), bevel=0.003))
        for k in range(3):  # slits along the sides of the fuselage
            parts.append(box(f'SideSlit{s}{k}', m['dark'], (0.012, 0.18, 0.025), (s * 0.31, -0.9 + 0.5 * k, 1.27), bevel=0.003))
        # the pylon arms out to the pods, with a fairing at the root
        for pivot in (e for e in ENGINES if (e.x > 0) == (s > 0)):
            inner = abs(pivot.x) - POD[0] / 2 + 0.02
            parts.append(cylinder(f'Arm{s}{pivot.y}', m['sand_light'], 0.05, inner - 0.25, (s * (inner + 0.25) / 2, pivot.y, ARM_Z),
                                  rotation=(0, math.pi / 2, 0), segments=12, bevel=0))
            parts.append(box(f'ArmRoot{s}{pivot.y}', m['sand_light'], (0.16, 0.3, 0.14), (s * 0.34, pivot.y, ARM_Z - 0.01), bevel=0.03))
    details = kit.merge('HullDetails', parts)

    decals = []
    emblem = decal_material()
    for s in (-1, 1):  # the emblem on the nose's cheeks
        decals.append(on_side(quad(f'NoseEmblem{s}', emblem, 0.28, 0.28), s, Vector((s * 0.48, -1.8, 0.98))))
    return body, details, decals, tail


def container(m, root):
    """The cargo container under the aircraft, after img_2/img_3: a flat hexagonal
    cross-section (its panels slope in above and below the belt, the lower ones also at
    the front), a slatted recess in the middle of each side, the emblem and "CP 034",
    the door at the back (the ramp closes it)."""
    hw, hl, top = BOX
    bw, bf = BOX_BOTTOM
    tw = BOX_TOP
    lower = kit.hexahedron('BoxLower', m['sand'], (
        (-bw, -bf, GEAR_TOP), (bw, -bf, GEAR_TOP), (bw, hl, GEAR_TOP), (-bw, hl, GEAR_TOP),
        (-hw, -hl, BOX_BELT), (hw, -hl, BOX_BELT), (hw, hl, BOX_BELT), (-hw, hl, BOX_BELT)), bevel=0.02)
    upper = kit.hexahedron('BoxUpper', m['sand'], (
        (-hw, -hl, BOX_BELT), (hw, -hl, BOX_BELT), (hw, hl, BOX_BELT), (-hw, hl, BOX_BELT),
        (-tw, -hl, top), (tw, -hl, top), (tw, hl, top), (-tw, hl, top)), bevel=0.02)
    shell = camo(kit.merge('Container', [lower, upper]), root)

    lean = math.atan2(hw - tw, top - BOX_BELT)  # of the upper panels

    def upper_x(z):  # the upper panel's distance from the middle at height z
        return hw - (z - BOX_BELT) * math.tan(lean)

    parts = [
        box('BoxBelt', m['concrete_dark'], (2 * hw + 0.01, 2 * hl + 0.01, 0.03), (0, 0, BOX_BELT), bevel=0.006),
        box('BoxTopRim', m['sand_light'], (2 * tw - 0.1, 2 * hl - 0.1, 0.025), (0, 0, top), bevel=0.008),
        box('BayDoor', m['dark'], (1.12, 0.012, 0.7), (0, hl + 0.002, GEAR_TOP + 0.35), bevel=0),
    ]
    mid = (top + BOX_BELT) / 2
    for s in (-1, 1):
        tilt = (0, -s * lean, 0)
        parts.append(box(f'Recess{s}', m['dark'], (0.02, 0.7, 0.36), (s * upper_x(mid), 0, mid), bevel=0.004, rotation=tilt))
        for k in range(3):
            z = BOX_BELT + 0.1 + k * 0.12
            parts.append(box(f'Slat{s}{k}', m['steel'], (0.05, 0.72, 0.03), (s * (upper_x(z) + 0.005), 0, z), bevel=0.004, rotation=tilt))
        for y in (-0.36, 0.36):  # frames left and right of the recess
            parts.append(box(f'RecessFrame{s}{y}', m['sand_light'], (0.04, 0.05, 0.42), (s * (upper_x(mid) + 0.01), y, mid), bevel=0.006, rotation=tilt))
        parts.append(box(f'BeltStripe{s}', m['remap'], (0.02, 0.5, 0.032), (s * (hw + 0.004), 0.85, BOX_BELT), bevel=0.003))
    details = kit.merge('ContainerDetails', parts)

    decals = []
    emblem = decal_material()
    for s in (-1, 1):
        decals.append(on_side(quad(f'Emblem{s}', emblem, 0.28, 0.28), s, Vector((s * upper_x(0.62), -0.85, 0.62)), lean))
        decals.append(on_side(text_mesh(f'Serial{s}', 'CP 034', m['stencil'], 0.15), s, Vector((s * upper_x(0.6), 0.85, 0.6)), lean))
    return shell, details, decals


def nacelle(m, root, i, pivot):
    """Engine pod around its pivot: a big rounded box in camouflage, the front leaning
    back towards the bottom with a dark intake, the nozzle at the back, a lift vent
    below, a red chevron and a navigation light outside, panels and an antenna on top,
    and the two exhaust plumes (back and down)."""
    side = 1 if pivot.x > 0 else -1
    w, l, h = POD[0] / 2, POD[1] / 2, POD[2] / 2
    shell = kit.hexahedron(f'Pod{i}', m['sand'], [pivot + Vector(v) for v in (
        (-w, -l + 0.1, -h), (w, -l + 0.1, -h), (w, l - 0.04, -h), (-w, l - 0.04, -h),
        (-w, -l, h), (w, -l, h), (w, l, h), (-w, l, h))], bevel=0.12)
    pod = camo(kit.merge(f'Pod{i}', [shell], pivot), root)
    lean = math.atan2(0.1, POD[2])
    parts = [
        box(f'Intake{i}', m['dark'], (2 * w - 0.16, 0.04, 2 * h - 0.2), pivot + Vector((0, -l + 0.06, 0)), bevel=0.015, rotation=(lean, 0, 0)),
        box(f'IntakeRim{i}', m['steel'], (2 * w - 0.12, 0.03, 2 * h - 0.16), pivot + Vector((0, -l + 0.075, 0)), bevel=0.015, rotation=(lean, 0, 0)),
        box(f'Nozzle{i}', m['dark'], (2 * w - 0.16, 0.04, 2 * h - 0.2), pivot + Vector((0, l - 0.015, 0)), bevel=0.015),
        box(f'NozzleRim{i}', m['steel'], (2 * w - 0.12, 0.03, 2 * h - 0.16), pivot + Vector((0, l - 0.03, 0)), bevel=0.015),
        box(f'LiftVent{i}', m['dark'], (2 * w - 0.12, 0.34, 0.025), pivot + Vector((0, 0.07, -h)), bevel=0.005),
        box(f'Band{i}', m['remap'], (2 * w + 0.008, 0.05, 2 * h - 0.1), pivot + Vector((0, 0.18, 0)), bevel=0.012),
        box(f'ArmMount{i}', m['steel'], (0.04, 0.2, 0.14), pivot + Vector((-side * (w + 0.01), 0, ARM_Z - pivot.z)), bevel=0.01),
        beam(f'Antenna{i}', m['steel'], pivot + Vector((side * 0.1, 0.26, h)), pivot + Vector((side * 0.11, 0.31, h + 0.13)), 0.012),
    ]
    for k in range(2):  # panels on top
        parts.append(box(f'Panel{i}{k}', m['dark'], (0.08, 0.05, 0.015), pivot + Vector((0.11 * (k - 0.5), -l + 0.2, h)), bevel=0.004))
    for k, angle in enumerate((35, -35)):  # red chevron at the front, outside
        parts.append(box(f'Chevron{i}{k}', m['red'], (0.015, 0.15, 0.032), pivot + Vector((side * (w + 0.002), -l + 0.18, 0.07 - 0.12 * k)),
                         bevel=0, rotation=(math.radians(angle), 0, 0)))
    details = kit.merge(f'PodDetails{i}', parts, pivot)
    nav = 'green' if side > 0 else 'red'
    light = pivot + Vector((side * (w + 0.015), -l + 0.3, h - 0.06))
    bulb = kit.merge(f'NavLight{i}', [
        sphere(f'NavBulb{i}', m[f'lamp_{nav}'], 0.022, light, 10),
        sphere(f'NavHalo{i}', m[f'glow_{nav}'], 0.05, light, 10),
    ], pivot)
    plume = cylinder(f'Plume{i}', m['plume'], 0.03, 0.45, pivot + Vector((0, l + 0.24, 0)), rotation=(math.pi / 2, 0, 0),
                     segments=16, bevel=0, radius2=0.14)
    plume = kit.merge(f'Plume{i}', [plume], pivot + Vector((0, l + 0.01, 0)))
    lift = cylinder(f'Lift{i}', m['plume'], 0.04, 0.4, pivot + Vector((0, 0.07, -h - 0.21)), segments=16, bevel=0, radius2=0.13)
    lift = kit.merge(f'Lift{i}', [lift], pivot + Vector((0, 0.07, -h - 0.01)))
    return pod, details, bulb, plume, lift


def gear(m):
    """Four feet under the container; their object's origin is at its underside, so
    scaling it in z pulls them in."""
    parts = []
    for x in (-0.45, 0.45):
        for y in (-0.85, 1.0):
            parts.append(cylinder(f'Foot{x}{y}', m['steel_light'], 0.035, GEAR_TOP, (x, y, GEAR_TOP / 2), segments=8, bevel=0))
            parts.append(cylinder(f'Pad{x}{y}', m['pod_dark'], 0.08, 0.02, (x, y, 0.01), segments=12, bevel=0.003))
    return kit.merge('Gear', parts, (0, 0, GEAR_TOP))


RAMP_HINGE = Vector((0, BOX[1] + 0.03, GEAR_TOP))  # just behind the door, so the closed ramp covers it
RAMP_LENGTH = 0.78
RAMP_CLOSED = 90                                   # up against the door
RAMP_OPEN = -math.degrees(math.asin(GEAR_TOP / RAMP_LENGTH))


def ramp(m):
    """Ramp at the back of the container, made lying flat behind its hinge; rotated about
    x it closes the door (RAMP_CLOSED) or reaches the ground (RAMP_OPEN)."""
    parts = [
        box('RampPlate', m['steel'], (1.16, RAMP_LENGTH, 0.03), RAMP_HINGE + Vector((0, RAMP_LENGTH / 2, 0.015)), bevel=0.005),
        # armour outside: the back of the container while the ramp is closed
        box('RampArmour', m['sand_light'], (1.12, RAMP_LENGTH - 0.03, 0.008), RAMP_HINGE + Vector((0, RAMP_LENGTH / 2, -0.003)), bevel=0.002),
    ]
    for i in range(8):
        parts.append(box(f'RampGrip{i}', m['steel_light'], (1.08, 0.012, 0.008), RAMP_HINGE + Vector((0, 0.06 + i * 0.09, 0.033)), bevel=0))
    for s in (-1, 1):
        parts.append(box(f'RampEdge{s}', m['remap'], (0.03, RAMP_LENGTH, 0.035), RAMP_HINGE + Vector((s * 0.56, RAMP_LENGTH / 2, 0.017)), bevel=0))
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
    body, details, decals, tail_part = hull(m, root)
    box_parts = container(m, root)
    for obj in (body, details, *decals, box_parts[0], box_parts[1], *box_parts[2]):
        kit.parent(obj, ship)
    tail = kit.parent(kit.empty('TailJoint', TAIL_JOINT), ship)   # breaks off in Crash
    kit.parent(tail_part, tail)

    engines, plumes, lifts = [], [], []
    for i, pivot in enumerate(ENGINES):
        joint = kit.parent(kit.empty(f'Engine{i}', pivot), ship)
        *parts, plume, lift = nacelle(m, root, i, pivot)
        for obj in (*parts, plume, lift):
            kit.parent(obj, joint)
        engines.append(joint)
        plumes.append(plume)
        lifts.append(lift)

    legs = kit.parent(gear(m), ship)
    hatch = kit.parent(ramp(m), ship)
    exit_node = kit.parent(kit.empty('CargoExit', (0, RAMP_HINGE.y + RAMP_LENGTH + 0.4, 0)), root)
    exit_node.empty_display_size = 0.1

    # lights: strobe at the end of the tail boom, beacon under the nose
    strobe = kit.merge('Strobe', [sphere('StrobeBulb', m['lamp_white'], 0.025, (0, 2.42, 1.33), 10),
                                  sphere('StrobeHalo', m['glow_white'], 0.07, (0, 2.42, 1.33), 10)], (0, 2.42, 1.33))
    kit.parent(strobe, tail)
    beacon = kit.merge('Beacon', [sphere('BeaconBulb', m['lamp_red'], 0.03, (0, -1.8, 0.51), 10),
                                  sphere('BeaconHalo', m['glow_red'], 0.07, (0, -1.8, 0.51), 10)], (0, -1.8, 0.51))
    kit.parent(beacon, ship)

    burning = kit.parent(fire(m, 'EngineFire', ENGINES[1] + Vector((0, 0.05, 0.3)), 0.13), ship)
    wreck_fire = kit.parent(fire(m, 'WreckFire', Vector((0.05, 0, 1.0)), 0.22), ship)
    blast = kit.parent(kit.merge('Blast', [sphere('BlastBall', m['blast'], 1.3, (0, 0, 0.7), 20)], (0, 0, 0.7)), ship)

    CHANNELS[:] = [(ship, 'location'), (ship, 'rotation_euler'), (legs, 'scale'), (hatch, 'rotation_euler'),
                   (tail, 'location'), (tail, 'rotation_euler'), (burning, 'scale'), (wreck_fire, 'scale'), (blast, 'scale')]
    for joint, plume, lift in zip(engines, plumes, lifts):
        CHANNELS.extend([(joint, 'location'), (joint, 'rotation_euler'), (plume, 'scale'), (lift, 'scale')])

    rad = math.radians
    hidden = Vector((HIDDEN,) * 3)

    def base(height, tilt, thrust, gear_out, ramp_angle, pitch=0.0, roll=0.0, yaw=0.0, y=0.0):
        # the thrust goes out of the nozzles in flight and out of the lift vents hovering
        hover = min(1.0, max(0.0, (tilt - TILT_FLY) / (TILT_HOVER - TILT_FLY)))
        back, down = thrust * (1 - hover), thrust * hover
        values = {
            ('Ship', 'location'): Vector((0, y, height)),
            ('Ship', 'rotation_euler'): Vector((rad(pitch), rad(roll), rad(yaw))),
            ('Gear', 'scale'): Vector((1, 1, mix(0.05, 1, gear_out))),
            ('Ramp', 'rotation_euler'): Vector((rad(ramp_angle), 0, 0)),
            ('TailJoint', 'location'): TAIL_JOINT.copy(),
            ('TailJoint', 'rotation_euler'): Vector((0, 0, 0)),
            ('EngineFire', 'scale'): hidden,
            ('WreckFire', 'scale'): hidden,
            ('Blast', 'scale'): hidden,
        }
        for i, (joint, plume, lift) in enumerate(zip(engines, plumes, lifts)):
            values[(joint.name, 'location')] = ENGINES[i].copy()
            values[(joint.name, 'rotation_euler')] = Vector((rad(tilt), 0, 0))
            values[(plume.name, 'scale')] = Vector((1, back, 1)) if back > 0.02 else hidden
            values[(lift.name, 'scale')] = Vector((1, 1, down)) if down > 0.02 else hidden
        return values

    def flicker(f, amount=0.12):
        return 1 + amount * math.sin(f * 2.3) * math.sin(f * 0.7 + 1)

    # ---- Fly (1 s loop)
    def fly(f):
        return base(FLY_HEIGHT, TILT_FLY, flicker(f), 0, RAMP_CLOSED, pitch=3)

    flight_clip('Fly', 30, fly)

    # ---- Land (3 s)
    def land(f):
        descent = span(f, 18, 80)
        height = FLY_HEIGHT * (1 - descent) ** 1.6 if f < 80 else 0.0
        if 80 <= f < 88:  # settles onto its legs
            height = -0.018 * math.sin(math.pi * (f - 80) / 8)
        pitch = mix(3, -2, span(f, 0, 18)) if f < 18 else mix(-2, 0, span(f, 18, 55))
        thrust = mix(1.0, 1.35, span(f, 10, 35)) if f < 70 else mix(1.35, 0.35, span(f, 70, 86))
        return base(height, mix(TILT_FLY, TILT_HOVER, span(f, 5, 38)), thrust * flicker(f), span(f, 48, 62),
                    mix(RAMP_CLOSED, RAMP_OPEN, span(f, 82, 90)), pitch=pitch)

    flight_clip('Land', 90, land)

    # ---- Landed (2 s loop)
    flight_clip('Landed', 60, lambda f: base(0, TILT_HOVER, 0.35 * flicker(f, 0.25), 1, RAMP_OPEN))

    # ---- TakeOff (3 s)
    def take_off(f):
        climb = span(f, 20, 78)
        height = FLY_HEIGHT * climb ** 1.3
        pitch = mix(0, 3, span(f, 50, 90))
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
        v[('Ship', 'location')].z -= GEAR_TOP - 0.01  # on the container's belly, feet up
        v[('Blast', 'scale')] = Vector((1, 1, 1)) * (math.sin(math.pi * span(f, 62, 78)) if f < 78 else HIDDEN) + Vector((HIDDEN,) * 3)
        v[('EngineFire', 'scale')] = Vector((1, 1, 1)) * 1.4 * flicker(f, 0.3)
        v[('WreckFire', 'scale')] = Vector((1, 1, 1)) * span(f, 64, 74) * flicker(f + 7, 0.3)
        # the tail breaks and droops, the front right engine tears off and lies askew
        v[('TailJoint', 'rotation_euler')] = Vector((rad(18 * t), rad(-8 * t), rad(16 * t)))
        v[('TailJoint', 'location')] = TAIL_JOINT + Vector((0.03, 0.08, -0.06)) * t
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
    kit.bake_camo(1024)
    bpy.context.scene.frame_set(0)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)


if __name__ == '__main__' and bpy.app.background:
    main()
