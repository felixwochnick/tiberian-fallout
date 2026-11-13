"""
Tiberian Fallout – GDI mobile EMP (MOBILEMP), after Tiberian Sun Firestorm.

A U-shaped tracked carrier, like the original: two long track hulls, joined at the
front by a low bridge and open at the back between them. Each hull runs on its own
track, its outer top edge sloped and set with a row of blue glowing panels, its ends
closed by sloped grated plates; hatches, vents, seams and exhausts on its back. On the
bridge stands the pulse emitter: an octagonal stepped base, a column with glowing slits
and on it a pale blue crystal dome in a cage of brackets; two ribbed power cables run
from the base across the open bay into the hulls. The hulls and the bridge are in the
light camouflage of the buildings, tinted with the house colour in the game
(GAPILE.camo_material); bands on the hulls, the bridge's hatch and the emitter's collar
are in the house colour.

Nodes the game uses: "Flash" (the discharge's glare at the emitter, the muzzle of
the pulse). Clips (see nodvehicle.py for Idle and Walk):
    Idle    loop, 2 s: the engine runs, the emitter's halo breathes
    Walk    loop: driving, the tracks' wheels turn, the body rocks; the root's
            walkSpeed (glTF extras) is the ground speed in cells per second
    Fire    once, 1.2 s: the discharge – the crystal charges up, flares and a bright
            blue ring of energy runs out over the ground and fades

Run headless:

    blender -b --factory-startup --python blender/MOBILEMP.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'MOBILEMP.glb')
BLEND = os.path.join(HERE, 'MOBILEMP.blend')

TRACK_X = 0.245
TRACK_WIDTH = 0.13
TRACK = (-0.42, 0.42)
TRACK_HEIGHT = 0.12
WHEEL_RADIUS = 0.045
WHEELS_Y = (-0.27, -0.13, 0.01, 0.15, 0.29)
SPROCKET = 0.0675                 # 1.5 × the wheels: 2/3 of a turn per loop (3 bolts: seamless)
WALK_FRAMES = 28
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 36
ARM = (0.13, 0.35)                # a track hull's inner and outer side (|x|)
ARM_BOTTOM = 0.11
ARM_TOP = 0.25
ARM_END = 0.47                    # its ends (|y|), the grated plates slope down to them
BRIDGE_TOP = 0.235
BRIDGE_BACK = 0.02                # the bridge's back face: behind it the bay is open
EMITTER = Vector((0, -0.17, 0.48))  # the crystal's middle
EMITTER_RADIUS = 0.085
BASE = Vector((0, EMITTER.y, BRIDGE_TOP))
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
OCTAGON = (0, 0, math.pi / 8)     # an 8-sided cylinder turned flat to the front


def materials():
    m = nod.materials()
    m.update({
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'emp': material('EmpCore', srgb('#c8f0ff'), 0.1, emission=srgb('#86d4ff'), strength=3.5),
        'emp_glow': material('EmpGlow', (0, 0, 0), 1.0, emission=srgb('#58b8ff'), strength=5, alpha=0.3),
        'emp_ring': material('EmpRing', (0, 0, 0), 1.0, emission=srgb('#7ccaff'), strength=8, alpha=0.6),
        'panel_blue': material('EmpPanel', srgb('#4ab6f2'), 0.25, emission=srgb('#3aa8ff'), strength=2.2),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def torus(name, mat, major, minor, location, segments=32, sides=8):
    """A flat ring lying in the ground plane."""
    def make(bm):
        rings = []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            ring = []
            for j in range(sides):
                b = 2 * math.pi * j / sides
                r = major + minor * math.cos(b)
                ring.append(bm.verts.new(Vector(location) + Vector((r * math.cos(a), r * math.sin(a), minor * math.sin(b)))))
            rings.append(ring)
        for i in range(segments):
            a, b = rings[i], rings[(i + 1) % segments]
            for j in range(sides):
                bm.faces.new((a[j], b[j], b[(j + 1) % sides], a[(j + 1) % sides]))
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    make(bm)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    kit.collection().objects.link(obj)
    mesh.materials.append(mat)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj


def loft(name, mat, sections, bevel=0.008):
    """A solid through cross-sections: `sections` = [(y, [(x, z), …]), …] from front
    to back, each a convex polygon with the same number of corners; capped at both
    ends."""
    def build(bm):
        rings = [[bm.verts.new((x, y, z)) for x, z in points] for y, points in sections]
        n = len(rings[0])
        for a, b in zip(rings, rings[1:]):
            for i in range(n):
                bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def crystal(name, mat, centre, radius, sides=8):
    """The faceted crystal dome: an octagonal gem, flat-shaded, standing on its rim."""
    centre = Vector(centre)
    profile = ((-0.55, 0.8), (-0.1, 1.0), (0.35, 0.92), (0.75, 0.62), (1.05, 0.25))  # (height, radius) × radius

    def build(bm):
        rings = []
        for k, (h, r) in enumerate(profile):
            turn = math.pi / sides * (k % 2)  # every other ring turned half a facet: crystal facets
            rings.append([bm.verts.new(centre + Vector((radius * r * math.cos(2 * math.pi * i / sides + turn),
                                                        radius * r * math.sin(2 * math.pi * i / sides + turn), radius * h)))
                          for i in range(sides)])
        for k, (a, b) in enumerate(zip(rings, rings[1:])):
            if k % 2:  # the lower ring is the turned one: the strip the other way round
                a, b = b, a
            for i in range(sides):
                bm.faces.new((a[i], a[(i + 1) % sides], b[i]))
                bm.faces.new((a[(i + 1) % sides], b[(i + 1) % sides], b[i]))
        apex = bm.verts.new(centre + Vector((0, 0, radius * 1.22)))
        for i in range(sides):
            bm.faces.new((rings[-1][i], rings[-1][(i + 1) % sides], apex))
        bm.faces.new(list(reversed(rings[0])))

    obj = kit.mesh_object(name, build)
    obj.data.materials.append(mat)
    return obj


def ribbed_hose(name, mat, rib_mat, start, control, end, radius=0.02, segments=10, ribs=9):
    """A thick cable along a quadratic curve, ringed with ribs."""
    start, control, end = Vector(start), Vector(control), Vector(end)

    def at(t):
        return (1 - t) ** 2 * start + 2 * (1 - t) * t * control + t * t * end

    def along(t):
        return (2 * (1 - t) * (control - start) + 2 * t * (end - control)).normalized()

    parts = detail.hose(name, mat, start, control, end, radius, segments)
    for k in range(ribs):
        t = (k + 0.5) / ribs
        rib = cylinder(f'{name}Rib{k}', rib_mat, radius + 0.004, 0.008, at(t), segments=10, bevel=0)
        rib.rotation_mode = 'QUATERNION'
        rib.rotation_quaternion = along(t).to_track_quat('Z', 'Y')
        parts.append(rib)
    return parts


# --------------------------------------------------------------------------- hull

def arm_section(s, y, top):
    """A track hull's cross-section at y: its outer top edge sloped (the blue panels'
    face), a small chamfer on the inner one."""
    xi, xo = s * ARM[0], s * ARM[1]
    slope = min(0.065, (top - ARM_BOTTOM) * 0.55)
    return y, [(xi, ARM_BOTTOM), (xo, ARM_BOTTOM), (xo, top - slope), (xo - s * 0.065, top), (xi + s * 0.015, top), (xi, top - 0.015)]


def slope_point(s, t, y, out=0.0):
    """A point on a hull's sloped outer edge: t = 0 at its foot, 1 at its top."""
    foot = Vector((s * ARM[1], y, ARM_TOP - 0.065))
    top = Vector((s * (ARM[1] - 0.065), y, ARM_TOP))
    normal = Vector((s * 0.065, 0, 0.065)).normalized()
    return foot.lerp(top, t) + normal * out


SLOPE_TILT = math.radians(45)


def hull(m, root):
    """The two track hulls and the bridge between them (one camouflaged mesh)."""
    low = ARM_BOTTOM + 0.04
    parts = [loft(f'Arm{s}', m['sand'], [
        arm_section(s, -ARM_END, low), arm_section(s, -ARM_END + 0.06, ARM_TOP),
        arm_section(s, ARM_END - 0.06, ARM_TOP), arm_section(s, ARM_END, low)], bevel=0.01) for s in (-1, 1)]
    w = ARM[0] + 0.012
    parts.append(loft('Bridge', m['sand'], [(y, [(-w, bottom), (w, bottom), (w, top), (-w, top)]) for y, bottom, top in (
        (-0.455, 0.1, 0.14), (-0.385, 0.08, BRIDGE_TOP), (BRIDGE_BACK - 0.012, 0.08, BRIDGE_TOP), (BRIDGE_BACK, 0.09, BRIDGE_TOP - 0.012))],
        bevel=0.008))
    return camo(kit.merge('Hull', parts), root)


def end_grate(name, m, s, end):
    """The grated plate on a hull's sloped end (`end`: -1 the front, +1 the back)."""
    p0 = Vector((s * (ARM[0] + ARM[1]) / 2, end * (ARM_END - 0.06), ARM_TOP))
    p1 = Vector((p0.x, end * ARM_END, ARM_BOTTOM + 0.04))
    centre = (p0 + p1) / 2 + Vector((0, end * 0.004, 0.004))
    length = (p1 - p0).length
    tilt = -end * math.atan2(p0.z - p1.z, abs(p1.y - p0.y))
    width = ARM[1] - ARM[0] - 0.09
    parts = [box(f'{name}Frame', m['steel'], (width + 0.016, length - 0.01, 0.008), centre, bevel=0.002, rotation=(tilt, 0, 0))]
    for k in range(6):
        p = p0.lerp(p1, (k + 0.6) / 6.4) + Vector((0, end * 0.008, 0.008))
        parts.append(box(f'{name}Bar{k}', m['dark'], (width, 0.008, 0.006), p, bevel=0, rotation=(tilt, 0, 0)))
    return parts


def blue_panel(name, m, s, y, length=0.07):
    """A glowing blue panel in a steel frame on a hull's sloped outer edge."""
    centre = slope_point(s, 0.5, y, 0.002)
    rotation = (0, s * SLOPE_TILT, 0)
    return [box(f'{name}Frame', m['steel'], (0.068, length + 0.014, 0.006), centre, bevel=0.002, rotation=rotation),
            box(f'{name}Glow', m['panel_blue'], (0.05, length, 0.006), slope_point(s, 0.5, y, 0.005), bevel=0.002, rotation=rotation)]


def details(m):
    parts = [
        # the bridge: a vision slit and a hatch on its front, a house-colour hatch on top
        box('Vision', m['glass'], (0.12, 0.01, 0.018), (0, -0.425, 0.185), bevel=0.002, rotation=(math.radians(-58), 0, 0)),
        box('VisionHood', m['steel'], (0.14, 0.03, 0.01), (0, -0.405, 0.212), bevel=0.003),
        box('BridgeHatch', m['remap'], (0.09, 0.07, 0.008), (0.06, -0.335, BRIDGE_TOP + 0.003), bevel=0.003),
        box('BridgeHatchHandle', m['steel_light'], (0.04, 0.008, 0.008), (0.06, -0.36, BRIDGE_TOP + 0.01), bevel=0),
        *[box(f'TowHook{s}', m['steel_light'], (0.03, 0.03, 0.03), (s * 0.07, -0.46, 0.105), bevel=0.004) for s in (-1, 1)],
        # its back face over the open bay: a ribbed plate, a lamp
        box('BackPlate', m['steel'], (0.22, 0.008, 0.1), (0, BRIDGE_BACK + 0.004, 0.16), bevel=0.003),
        *[box(f'BackRib{k}', m['dark'], (0.2, 0.01, 0.008), (0, BRIDGE_BACK + 0.006, 0.125 + 0.025 * k), bevel=0) for k in range(4)],
    ]
    for s in (-1, 1):
        xi, xo = s * ARM[0], s * ARM[1]
        mid = s * (ARM[0] + ARM[1] - 0.065) / 2   # the middle of the flat top
        parts += [
            *end_grate(f'GrateFront{s}', m, s, -1),
            *end_grate(f'GrateBack{s}', m, s, 1),
            # a row of blue panels on the sloped edge, a house-colour band
            *[p for k in range(5) for p in blue_panel(f'Panel{s}{k}', m, s, -0.3 + 0.15 * k)],
            box(f'Band{s}', m['remap'], (0.04, 0.6, 0.005), (mid + s * 0.035, 0.0, ARM_TOP + 0.002), bevel=0.002),
            # seams across the top, a skirt and rivets down the flank
            *[p for k, y in enumerate((-0.33, -0.12, 0.08, 0.3)) for p in detail.seam(
                f'TopSeam{s}{k}', m['seam'], (xi + s * 0.016, y, ARM_TOP + 0.001), (xo - s * 0.066, y, ARM_TOP + 0.001))],
            box(f'Skirt{s}', m['steel'], (0.012, 0.8, 0.03), (xo + s * 0.003, 0.0, ARM_BOTTOM + 0.008), bevel=0.003),
            *detail.rivets(f'Rivets{s}', m['steel_light'], (xo + s * 0.004, -0.36, ARM_BOTTOM + 0.04), (xo + s * 0.004, 0.36, ARM_BOTTOM + 0.04), 10,
                           axis='X'),
            # the inner wall over the bay: a plate down to the track, a hydraulic ram
            box(f'BayWall{s}', m['steel'], (0.01, 0.42, 0.07), (xi - s * 0.002, 0.24, ARM_BOTTOM - 0.02), bevel=0.003),
            beam(f'Ram{s}', m['steel_light'], (xi - s * 0.008, 0.08, 0.2), (xi - s * 0.008, 0.36, 0.14), 0.012),
            cylinder(f'RamBody{s}', m['dark'], 0.012, 0.12, (xi - s * 0.01, 0.13, 0.19), rotation=(math.pi / 2 - 0.2, 0, 0), segments=10),
            # headlights at the front ends, tail lights at the back ends
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.2, -ARM_END - 0.002, ARM_BOTTOM + 0.02), (0, -1, 0), 0.013),
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.3, ARM_END + 0.002, ARM_BOTTOM + 0.02), (0, 1, 0), 0.01),
            # on the back of the hull: an engine vent, an exhaust
            *[box(f'Vent{s}{k}', m['dark'], (0.08, 0.012, 0.006), (mid, 0.3 + 0.03 * k, ARM_TOP + 0.003), bevel=0) for k in range(4)],
            box(f'VentFrame{s}', m['steel'], (0.095, 0.11, 0.004), (mid, 0.345, ARM_TOP + 0.001), bevel=0.002),
            cylinder(f'Exhaust{s}', m['steel_light'], 0.015, 0.08, (xi + s * 0.03, 0.4, ARM_TOP + 0.03), segments=10),
            cylinder(f'ExhaustTip{s}', m['dark'], 0.013, 0.01, (xi + s * 0.03, 0.4, ARM_TOP + 0.07), segments=10, bevel=0),
        ]
    parts += [
        # a round hatch on the right hull, a box on the left one, an antenna
        cylinder('RoundHatch', m['steel'], 0.04, 0.014, (0.21, 0.17, ARM_TOP + 0.005), segments=16),
        box('RoundHatchHandle', m['steel_light'], (0.04, 0.008, 0.008), (0.21, 0.17, ARM_TOP + 0.014), bevel=0),
        box('Stowage', m['olive'], (0.08, 0.1, 0.035), (-0.21, 0.15, ARM_TOP + 0.018), bevel=0.008),
        beam('Antenna', m['steel'], (-0.2, 0.41, ARM_TOP), (-0.21, 0.44, ARM_TOP + 0.3), 0.005),
        cylinder('AntennaBase', m['dark'], 0.012, 0.02, (-0.2, 0.41, ARM_TOP + 0.01), segments=8, bevel=0),
    ]
    return kit.merge('HullDetails', parts)


def emitter(m):
    """The stepped octagonal base, the column with its glowing slits, the collar and
    the cage round the crystal, the power cables (fixed parts); the crystal and its
    halo are separate."""
    z = BASE.z
    parts = [
        cylinder('Step0', m['steel'], 0.17, 0.045, BASE + Vector((0, 0, 0.0225)), rotation=OCTAGON, segments=8, bevel=0.006, radius2=0.15),
        cylinder('Step1', m['sand_light'], 0.13, 0.04, BASE + Vector((0, 0, 0.065)), rotation=OCTAGON, segments=8, bevel=0.006, radius2=0.115),
        cylinder('Column', m['steel'], 0.075, 0.085, BASE + Vector((0, 0, 0.125)), rotation=OCTAGON, segments=8, bevel=0.004),
        cylinder('Collar', m['remap'], 0.09, 0.022, BASE + Vector((0, 0, 0.17)), rotation=OCTAGON, segments=8, bevel=0.004),
        cylinder('CrystalSeat', m['steel_light'], 0.075, 0.02, BASE + Vector((0, 0, 0.19)), rotation=OCTAGON, segments=8, bevel=0.003),
    ]
    for k in range(8):  # glowing slits on the column's faces, bolts round the lower step
        a = 2 * math.pi * k / 8 + math.pi / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(box(f'Slit{k}', m['panel_blue'], (0.012, 0.016, 0.06), BASE + d * 0.07 + Vector((0, 0, 0.125)), bevel=0,
                         rotation=(0, 0, a)))
        parts.append(sphere(f'Bolt{k}', m['steel_light'], 0.007, BASE + d * 0.14 + Vector((0, 0, 0.046)), 6))
    for k in range(4):  # the cage: four brackets from the step up past the crystal's waist
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        foot = BASE + d * 0.1 + Vector((0, 0, 0.085))
        knee = EMITTER + d * (EMITTER_RADIUS + 0.025) + Vector((0, 0, -0.03))
        tip = EMITTER + d * (EMITTER_RADIUS * 0.75) + Vector((0, 0, EMITTER_RADIUS * 0.75))
        parts += [beam(f'Cage{k}a', m['steel_light'], foot, knee, 0.012), beam(f'Cage{k}b', m['steel_light'], knee, tip, 0.01),
                  box(f'CageClamp{k}', m['steel'], (0.024, 0.024, 0.02), knee, bevel=0.003, rotation=(0, 0, a))]
    for s in (-1, 1):  # the power cables from the base across the bay into the hulls
        start = BASE + Vector((s * 0.08, 0.1, 0.03))
        parts += ribbed_hose(f'Cable{s}', m['dark'], m['steel'], start, start + Vector((s * 0.02, 0.2, 0.04)),
                             Vector((s * (ARM[0] + 0.005), 0.2, z - 0.035)), 0.018)
        parts.append(box(f'CableSocket{s}', m['steel'], (0.02, 0.05, 0.05), (s * (ARM[0] + 0.004), 0.2, z - 0.035), bevel=0.004))
    return kit.merge('Emitter', parts)


def build():
    root, body = nod.start('GDIMobileEMP', 'MobileEMP', WALK_SPEED)
    m = materials()
    kit.parent(hull(m, root), body)
    kit.parent(details(m), body)
    kit.parent(emitter(m), body)
    core = kit.parent(kit.merge('EmitterCore', [crystal('EmitterCore', m['emp'], EMITTER, EMITTER_RADIUS)], EMITTER), body)
    halo = kit.parent(kit.merge('Halo', [sphere('Halo', m['emp_glow'], EMITTER_RADIUS * 1.6, EMITTER + Vector((0, 0, 0.02)), 14)], EMITTER),
                      body)
    flash = kit.parent(kit.merge('Flash', [sphere('Flash', m['emp_glow'], EMITTER_RADIUS * 2.2, EMITTER, 14),
                                           sphere('FlashCore', m['emp'], EMITTER_RADIUS * 1.25, EMITTER, 12)], EMITTER), body)
    ground = Vector((0, EMITTER.y, 0.03))
    ring = kit.parent(kit.merge('Pulse', [torus('Pulse', m['emp_ring'], 0.25, 0.025, ground)], ground), root)
    wheels, sprockets = [], []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], TRACK_HEIGHT, 20), body)
        x = s * (TRACK_X + TRACK_WIDTH / 2 + 0.004)
        wheels += [kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (x, y, WHEEL_RADIUS + 0.004), WHEEL_RADIUS, 0.02), body)
                   for k, y in enumerate(WHEELS_Y)]
        sprockets += [kit.parent(nod.road_wheel(m, f'Sprocket{s}{k}', (x, y, SPROCKET + 0.004), SPROCKET, 0.02), body)
                      for k, y in enumerate((TRACK[0] + 0.06, TRACK[1] - 0.06))]
    kit.bake_camo(512)
    nod.drive(body, wheels, WALK_FRAMES, extra=[(sprockets, WHEEL_RADIUS / SPROCKET)], rock=0.003)

    one, hidden = Vector((1, 1, 1)), Vector((kit.HIDDEN,) * 3)
    # Idle: the halo breathes
    kit.keys(halo, 'scale', {f: one * (1 + 0.12 * math.sin(2 * math.pi * f / kit.IDLE_END)) for f in range(0, kit.IDLE_END + 1, 5)}, 'LINEAR')
    kit.to_track(halo, 'Idle')
    walker.hide([flash, ring], kit.IDLE_END, 'Idle')
    walker.hide([flash, ring], WALK_FRAMES, 'Walk')
    # Fire: charge up (the crystal and halo swell), the flash, the ring runs out and fades
    kit.keys(core, 'scale', {0: one, 8: one * 1.2, 10: one * 1.3, 14: one * 0.9, 24: one, FIRE_FRAMES: one})
    kit.to_track(core, 'Fire')
    kit.keys(halo, 'scale', {0: one, 8: one * 1.5, 10: one * 1.9, 14: one * 0.6, 26: one, FIRE_FRAMES: one})
    kit.to_track(halo, 'Fire')
    kit.keys(flash, 'scale', {0: hidden, 9: hidden, 10: one * 0.8, 12: one * 1.6, 16: one * 1.2, 20: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(flash, 'Fire')
    kit.keys(ring, 'scale', {0: hidden, 9: hidden, 10: Vector((0.6, 0.6, 1)), 22: Vector((4.2, 4.2, 0.8)), 30: Vector((6.0, 6.0, 0.4)),
                             31: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(ring, 'Fire')
    flash.scale = ring.scale = hidden
    core.scale = halo.scale = one
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels + sprockets:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Fire': [11, 22]}, scale=1.6, target=(0, 0, 0.25))
