"""
Tiberian Fallout – GDI upgrade center (GAPLUG), after Tiberian Sun.

A long camouflaged hall on the back two thirds of the foundation (2 × 3 cells): a low
body under an overhanging roof slab with a blue-violet band under its edge, a row of
sloped plates in the house colour along its front, a cluster of vent pipes and a
gauge lamp on its right; on the roof a forest of thin antennas and a small turning
sensor. In front of it a grey steel platform on short legs with two round places in a
thick ring of the house colour, each with four holes the pegs of an upgrade lock into
(like the power plant's turbine places, see GAPOWR.py); a third place is let into the
roof at the back.

Nodes the game drives
    PlugSlot1 … PlugSlot3   empty nodes at the top of the places, in the order the game
                            mounts upgrades (front right, front left, roof); the
                            upgrades (GAPLUG2/3/4) stand there with the middle of their
                            foot

Materials as for the barracks (see GAPILE.py): Camo_* is the baked camouflage in a
pale shade of the house colour, Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the platform spreads, the hall rises out of the ground,
             the front plates fold down, the places come up, the antennas shoot up,
             the lights come on
    Idle     loop, 2 s: the sensor on the roof turns, the gauge flickers up and down,
             the antenna lamps blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAPLUG.py [-- --preview 0,30,72 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -1 … 1 and y -1.5 … 1.5. The helpers plug_materials() and plug_foot() are used
by the upgrades (GAPLUG2/3/4).
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import GAPOWR as plant  # noqa: E402 – HOLE_RADIUS (where the pegs go)
import gdibuilding as gb  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAPLUG.glb')
BLEND = os.path.join(HERE, 'GAPLUG.blend')

BUILD_END = 72
PAD_TOP = 0.1           # top of the steel platform
PLACE_TOP = PAD_TOP + 0.04
HALL = (-0.95, -0.38, 0.95, 1.44)   # x0, y0, x1, y1 of the hall's body
BODY_TOP = 0.32
ROOF = (0.35, 0.5)      # bottom and top of the roof slab
PLACES = (Vector((0.46, -0.94, PLACE_TOP)), Vector((-0.46, -0.94, PLACE_TOP)), Vector((0.42, 0.9, ROOF[1] + 0.03)))
PLACE_R = 0.3           # the grey plate; the ring round it is wider
RING_R = 0.42
HOLE_RADIUS = plant.HOLE_RADIUS
FOOT = 0.025            # height of an upgrade's foot ring

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def plug_materials():
    """The barracks' materials and the extras of the upgrade center and its upgrades."""
    m = kit.materials()
    m['plate'] = material('PlugPlate', srgb('#8e949c'), 0.5, 0.7)
    m['pod_dark'] = material('PodDark', srgb('#2b3036'), 0.6, 0.6)
    m['band'] = material('PlugBand', srgb('#7076ad'), 0.4, 0.6)
    m['remap_dark'] = kit.material('RemapDark', srgb('#9a7c22'), 0.6, 0.15)
    m['glow_white'] = material('GlowWhite', (0, 0, 0), 1.0, emission=srgb('#e8f0ff'), strength=4, alpha=0.3)
    m['glow_blue'] = material('GlowBlue', (0, 0, 0), 1.0, emission=srgb('#6f8cff'), strength=5, alpha=0.35)
    m['lamp_blue'] = material('LampBlue', srgb('#b8c8ff'), 0.2, emission=srgb('#8aa4ff'), strength=8)
    return m


def plug_foot(m, root):
    """An upgrade's foot: a dark ring with four pegs down into a place's holes; origin
    in its middle on the place's top."""
    parts = [cylinder('FootRing', m['pod_dark'], 0.25, FOOT, (0, 0, FOOT / 2), segments=32, bevel=0.004)]
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        p = Vector((math.cos(a), math.sin(a), 0)) * HOLE_RADIUS
        parts.append(cylinder(f'Peg{k}', m['steel_light'], 0.026, 0.04, p, segments=12, bevel=0.002))
        parts.append(cylinder(f'PegCap{k}', m['steel'], 0.04, 0.012, p + Vector((0, 0, FOOT + 0.004)), segments=12, bevel=0.002))
    return kit.parent(kit.merge('Foot', parts), root)


def ring(name, mat, profile, location, segments=40, bevel=0.0):
    """A closed ring (no caps, open in the middle) swept from a closed 2D profile of
    (radius, height) points, counter-clockwise."""
    def build(bm):
        rings = [[bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in (2 * math.pi * i / segments for i in range(segments))]
                 for r, z in profile]
        n = len(profile)
        for k in range(n):
            lower, upper = rings[k], rings[(k + 1) % n]
            for i in range(segments):
                j = (i + 1) % segments
                bm.faces.new((lower[i], lower[j], upper[j], upper[i]))

    obj = kit.mesh_object(name, build)
    obj.location = location
    return kit.finish(obj, mat, bevel)


# --------------------------------------------------------------------------- parts

def platform(m):
    """The grey steel platform in front of the hall, on short legs, with tread plates."""
    x0, y0, x1, y1 = -0.97, -1.47, 0.97, -0.3
    parts = [gb.slab('Platform', m['plate'], gb.chamfered(x0, y0, x1, y1, (0.06, 0.06, 0, 0)), PAD_TOP - 0.04, inset=0.02, z0=0.04, bevel=0.005)]
    for k, (x, y) in enumerate(((x0 + 0.1, y0 + 0.1), (x1 - 0.1, y0 + 0.1), (x0 + 0.1, y1 - 0.12), (x1 - 0.1, y1 - 0.12), (0, y0 + 0.1))):
        parts.append(box(f'Leg{k}', m['concrete_dark'], (0.14, 0.14, 0.05), (x, y, 0.025), bevel=0.006))
    parts.append(box('Underside', m['steel'], (x1 - x0 - 0.2, y1 - y0 - 0.2, 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, 0.035), bevel=0.004))
    for k in range(5):  # tread seams across the platform
        y = y0 + 0.12 + k * 0.24
        parts.append(box(f'Seam{k}', m['steel'], (x1 - x0 - 0.12, 0.012, 0.004), (0, y, PAD_TOP + 0.001), bevel=0))
    parts.append(box('Kerb', m['remap'], (x1 - x0 - 0.16, 0.025, 0.012), (0, y0 + 0.035, PAD_TOP - 0.01), bevel=0.002))
    return kit.merge('Platform', parts, (0, (y0 + y1) / 2, 0))


def place(m, i, centre, base_z):
    """A round place: a thick ring in the house colour round a grey plate with four
    holes; returns (place object, slot node). `centre` is the plate's top."""
    c = Vector(centre)
    z0 = base_z
    h = c.z - z0
    parts = [
        plant.lathe(f'Ring{i}', m['remap'], ((RING_R, 0), (RING_R + 0.01, 0.03), (RING_R - 0.02, h + 0.035), (PLACE_R + 0.03, h + 0.04),
                                            (PLACE_R + 0.005, h + 0.01), (PLACE_R, 0)), (c.x, c.y, z0), 40, 0.004),
        cylinder(f'Plate{i}', m['plate'], PLACE_R, h, (c.x, c.y, z0 + h / 2), segments=40, bevel=0.004),
        cylinder(f'PlateDeck{i}', m['pod_dark'], PLACE_R - 0.06, 0.004, (c.x, c.y, c.z + 0.001), segments=40, bevel=0),
    ]
    for k in range(4):
        a = math.pi / 4 + math.pi / 2 * k
        p = c + Vector((math.cos(a), math.sin(a), 0)) * HOLE_RADIUS
        parts += [
            cylinder(f'HoleRim{i}_{k}', m['steel_light'], 0.042, 0.01, p + Vector((0, 0, 0.003)), segments=16, bevel=0.002),
            cylinder(f'Hole{i}_{k}', m['dark'], 0.03, 0.004, p + Vector((0, 0, 0.0075)), segments=16, bevel=0),
        ]
    obj = kit.merge(f'Place{i}', parts, (c.x, c.y, z0))
    slot = kit.empty(f'PlugSlot{i + 1}', c)
    slot.empty_display_size = 0.15
    return obj, slot


def hall(m, root):
    """The body and roof (camouflage) with their trims; returns (shell, details)."""
    x0, y0, x1, y1 = HALL
    body = gb.slab('Body', m['sand'], gb.chamfered(x0, y0, x1, y1, (0, 0.08, 0, 0)), BODY_TOP, inset=0.03, bevel=0.006)
    rx0, ry0, rx1, ry1 = x0 - 0.03, y0 - 0.06, x1 - 0.04, y1 + 0.02
    roof = gb.slab('Roof', m['sand'], gb.chamfered(rx0, ry0, rx1, ry1, (0.03, 0.1, 0.03, 0.03)), ROOF[1] - ROOF[0], inset=0.025, z0=ROOF[0], bevel=0.008)
    shell = gb.camo(kit.merge('Hall', [body, roof]), root)

    parts = [
        # the blue-violet band under the roof's edge, the dark gap to the body
        gb.slab('Band', m['band'], gb.chamfered(rx0 + 0.02, ry0 + 0.02, rx1 - 0.02, ry1 - 0.02, (0.02, 0.09, 0.02, 0.02)), ROOF[0] - BODY_TOP + 0.002,
                z0=BODY_TOP - 0.001, bevel=0.003),
        gb.slab('Footing', m['concrete_dark'], gb.chamfered(x0 - 0.02, y0 - 0.02, x1 + 0.02, y1 + 0.02, (0, 0.1, 0, 0)), 0.03, inset=0.01, bevel=0.003),
        box('RoofTrim', m['steel'], (rx1 - rx0 - 0.08, 0.02, 0.014), ((rx0 + rx1) / 2, ry0 + 0.04, ROOF[1] + 0.004), bevel=0.003),
    ]
    # a door in the left end, windows down the right side
    parts.append(box('Door', m['dark'], (0.012, 0.18, 0.2), (x0 - 0.002, 0.4, 0.13), bevel=0.003))
    parts.append(box('DoorHood', m['steel_light'], (0.05, 0.24, 0.015), (x0 - 0.015, 0.4, 0.25), bevel=0.003))
    for k in range(3):
        parts.append(box(f'Window{k}', m['window'], (0.012, 0.16, 0.045), (x1 + 0.001, 0.4 + k * 0.32, 0.23), bevel=0.002))
    # vent pipes up the right end at the front, the gauge cabinet next to them
    for k in range(4):
        y = -0.24 + k * 0.075
        parts.append(cylinder(f'Pipe{k}', m['steel_light'], 0.026, 0.42, (x1 + 0.04, y, 0.21), segments=12, bevel=0.003))
        parts.append(cylinder(f'PipeCap{k}', m['steel'], 0.032, 0.02, (x1 + 0.04, y, 0.43), segments=12, bevel=0.003))
    parts.append(box('PipeClamp', m['steel'], (0.05, 0.32, 0.03), (x1 + 0.02, -0.13, 0.3), bevel=0.004))
    parts.append(box('GaugeBox', m['steel'], (0.1, 0.05, 0.2), (x1 - 0.12, y0 - 0.01, 0.17), bevel=0.006))
    parts.append(box('GaugeSlot', m['dark'], (0.035, 0.01, 0.15), (x1 - 0.12, y0 - 0.036, 0.17), bevel=0))
    # on the roof: panel seams, a hatch and a vent
    for k in range(3):
        parts.append(box(f'RoofSeam{k}', m['concrete_dark'], (rx1 - rx0 - 0.1, 0.008, 0.003), (-0.02, -0.05 + k * 0.48, ROOF[1] + 0.001), bevel=0))
    parts.append(box('RoofHatch', m['steel'], (0.16, 0.16, 0.02), (-0.6, 1.05, ROOF[1] + 0.01), bevel=0.004))
    vent = kit.vent_block('RoofVent', m, -0.62, 0.15)
    vent.location.z = ROOF[1]
    parts.append(vent)
    return shell, kit.merge('HallDetails', parts)


def front_plates(m):
    """The row of sloped plates in the house colour along the hall's front (each its own
    object: they fold down in turn); origin at their top edge."""
    x0, y0 = HALL[0], HALL[1]
    plates = []
    n = 6
    width = (HALL[2] - 0.22 - x0 - 0.06) / n
    for k in range(n):
        x = x0 + 0.06 + (k + 0.5) * width
        top = Vector((x, y0 + 0.01, BODY_TOP - 0.03))
        low = Vector((x, y0 - 0.17, PAD_TOP + 0.02))
        verts = [(x - width / 2 + 0.006, low.y, low.z), (x + width / 2 - 0.006, low.y, low.z), (x + width / 2 - 0.006, top.y, top.z),
                 (x - width / 2 + 0.006, top.y, top.z)]
        lift = Vector((0, 0.025, 0.02))
        verts += [tuple(Vector(v) + lift) for v in verts]
        plate = kit.hexahedron(f'FrontPlate{k}', m['remap'], verts, 0.006)
        rib = beam(f'FrontRib{k}', m['remap_dark'], low + Vector((-width / 2 + 0.01, 0.03, 0.03)), top + Vector((-width / 2 + 0.01, 0.03, 0.02)), 0.012, 0.012)
        plates.append(kit.merge(f'FrontPlate{k}', [plate, rib], top))
    return plates


def antenna(m, k, foot, height, bars):
    """A thin mast with cross bars near its top; origin at its foot (it grows up)."""
    foot = Vector(foot)
    parts = [box(f'AntFoot{k}', m['steel'], (0.05, 0.05, 0.02), foot + Vector((0, 0, 0.01)), bevel=0.003),
             cylinder(f'AntMast{k}', m['steel'], 0.009, height, foot + Vector((0, 0, height / 2)), segments=8, bevel=0),
             cylinder(f'AntTip{k}', m['steel_light'], 0.005, 0.06, foot + Vector((0, 0, height + 0.03)), segments=6, bevel=0)]
    for j in range(bars):
        z = height * (0.62 + 0.13 * j)
        w = 0.07 - 0.015 * j
        parts.append(beam(f'AntBar{k}_{j}', m['steel'], foot + Vector((-w, -w * 0.3, z)), foot + Vector((w, w * 0.3, z)), 0.007))
    return kit.merge(f'Antenna{k}', parts, foot)


def sensor(m):
    """The small sensor on the roof (the original's GAPLUG_A): a dark drum and a head
    with a slanted face that turns; returns (drum, head)."""
    at = Vector((-0.15, 0.55, ROOF[1]))
    drum = kit.merge('SensorBase', [
        cylinder('SensorDrum', m['pod_dark'], 0.08, 0.06, at + Vector((0, 0, 0.03)), segments=20, bevel=0.005),
        cylinder('SensorRing', m['remap'], 0.083, 0.012, at + Vector((0, 0, 0.05)), segments=20, bevel=0),
    ], at)
    hz = at + Vector((0, 0, 0.06))
    head = kit.merge('SensorHead', [
        box('SensorBody', m['steel'], (0.1, 0.08, 0.07), hz + Vector((0, 0.005, 0.04)), bevel=0.012),
        box('SensorFace', m['steel_light'], (0.09, 0.012, 0.06), hz + Vector((0, -0.042, 0.045)), bevel=0.003, rotation=(math.radians(-20), 0, 0)),
        box('SensorEye', m['signal'], (0.04, 0.006, 0.018), hz + Vector((0, -0.05, 0.05)), bevel=0, rotation=(math.radians(-20), 0, 0)),
    ], hz)
    return drum, head


# --------------------------------------------------------------------------- model

ANTENNAS = (  # x, y, height, bars
    (-0.78, -0.2, 0.62, 2), (-0.55, -0.22, 0.38, 1), (-0.35, 0.35, 0.5, 3), (0.2, -0.15, 0.55, 2),
    (0.3, 0.15, 0.38, 1), (0.82, 0.05, 0.42, 2), (-0.8, 1.3, 0.48, 2), (0.0, 1.3, 0.3, 1),
)


def build():
    gb.start('GDIUpgradeCenter', BUILD_END)
    m = plug_materials()
    root = kit.empty('GDIUpgradeCenter')
    keys = kit.keys
    H = kit.HIDDEN

    # ---- the platform spreads, the places come up through it
    pad = kit.parent(platform(m), root)
    keys(pad, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 12: Vector((1.02, 1.02, 1)), 15: Vector((1, 1, 1))})
    for i, c in enumerate(PLACES[:2]):
        obj, slot = place(m, i, c, PAD_TOP - 0.01)
        group = kit.parent(kit.empty(f'PlaceGroup{i}', (c.x, c.y, 0)), root)
        for o in (obj, slot):
            kit.parent(o, group)
        s = 40 + 6 * i
        keys(group, 'location', {0: Vector((c.x, c.y, -0.16)), s: Vector((c.x, c.y, -0.16)), s + 9: Vector((c.x, c.y, 0.008)), s + 12: Vector((c.x, c.y, 0))})

    # ---- the hall rises out of the ground (never scaled: its lamps and sensor animate)
    body = kit.parent(kit.empty('HallGroup'), root)
    for obj in hall(m, root):
        kit.parent(obj, body)
    keys(body, 'location', {0: Vector((0, 0, -0.5)), 6: Vector((0, 0, -0.5)), 28: Vector((0, 0, 0.012)), 32: Vector((0, 0, 0))})
    # the front plates fold down from the body
    for k, plate in enumerate(front_plates(m)):
        kit.parent(plate, body)
        keys(plate, 'rotation_euler', {0: Vector((math.radians(-75), 0, 0)), 30 + 2 * k: Vector((math.radians(-75), 0, 0)),
                                       38 + 2 * k: Vector((math.radians(4), 0, 0)), 41 + 2 * k: Vector((0, 0, 0))})
    # the place in the roof
    c = PLACES[2]
    obj, slot = place(m, 2, c, ROOF[1] - 0.005)
    for o in (obj, slot):
        kit.parent(o, body)
    kit.pop(obj, 34, 8)

    # ---- the antennas shoot up, the sensor pops up
    lights = []
    for k, (x, y, height, bars) in enumerate(ANTENNAS):
        mast = kit.parent(antenna(m, k, (x, y, ROOF[1]), height, bars), body)
        kit.grow(mast, 44 + 2 * k, 8, 2)
        if k in (0, 2, 3, 6):
            gb.beacon(f'AntLamp{k}', m, Vector((x, y, ROOF[1] + height + 0.055)), 'red', body, 56 + k,
                      kit.flashes((k * 7, 6), (30 + k * 7, 6)), lights)
    drum, head = sensor(m)
    kit.parent(drum, body)
    kit.pop(drum, 40, 6)
    turner = kit.parent(kit.empty('SensorTurn', head.location), body)
    kit.parent(head, turner)
    kit.pop(head, 44, 6)
    gb.beacon('DoorLamp', m, Vector((HALL[0] - 0.03, 0.4, 0.27)), 'amber', body, 50, kit.flashes((0, 15), (30, 15)), lights)
    gb.beacon('PadLamp', m, Vector((0.0, -1.38, PAD_TOP)), 'green', root, 54, kit.flashes((5, 40)), lights)

    # ---- the gauge (the original's GAPLUG_C): five segments, red at the top
    gauge = []
    for k in range(5):
        at = Vector((HALL[2] - 0.12, HALL[1] - 0.04, 0.115 + k * 0.028))
        colour = m['lamp_red'] if k >= 3 else m['lamp_amber']
        seg = box(f'Gauge{k}', colour, (0.026, 0.008, 0.02), at, bevel=0)
        gauge.append(kit.parent(kit.merge(f'Gauge{k}', [seg], at), body))

    idle = [(turner, lambda o: gb.spin(o, 1))]
    gb.clips(idle, lights)
    for k, seg in enumerate(gauge):  # the level climbs and falls twice a loop
        on = {f for f in range(kit.IDLE_END) if k <= 4 * (0.5 - 0.5 * math.cos(4 * math.pi * f / kit.IDLE_END)) + 0.3}
        kit.blink(seg, on)
        kit.to_track(seg, 'Idle')
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=4.0, target=(0, 0, 0.3))
