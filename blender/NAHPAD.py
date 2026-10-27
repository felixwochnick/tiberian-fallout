"""
Tiberian Fallout – Nod helipad (NAHPAD), after Tiberian Sun.

On 2 × 2 cells: a round landing pad of dark concrete with a red (house colour) ring,
a light cross and a target circle painted on it and green landing lights round its
edge; at the back right a small control post – a concrete block with a light grey
cabin, slanted windows, an antenna mast and a turning radar dish; at the back left two
red fuel tanks on their cradles with a pump.

Nodes the game uses:
    Pad      the landing point on the middle of the pad; its -Y is the way an aircraft
             faces when it has landed
Animations (glTF clips)
    Build    one-shot, 2.2 s: the pad spreads, its markings and lights appear, the
             control post rises, the tanks and the mast come up
    Idle     loop, 2 s: the landing lights run round the pad, the radar dish turns,
             the mast's beacon blinks

Run headless:

    blender -b --factory-startup --python blender/NAHPAD.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); origin in the middle on the ground.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodbuilding as nb  # noqa: E402

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
HIDDEN = kit.HIDDEN

PAD = Vector((-0.14, -0.12, 0))     # the pad's middle
RADIUS = 0.74
PAD_TOP = 0.06
POST = Vector((0.6, 0.6, 0))        # the control post
TANKS = Vector((-0.74, 0.62, 0))
LIGHTS = 10


def ring(name, mat, centre, radius, width, z, count=48):
    """A flat painted ring (top faces only), `width` wide round `radius`."""
    def build(bm):
        inner, outer = [], []
        for k in range(count):
            a = 2 * math.pi * k / count
            d = Vector((math.cos(a), math.sin(a), 0))
            inner.append(bm.verts.new(centre + d * (radius - width / 2) + Vector((0, 0, z))))
            outer.append(bm.verts.new(centre + d * (radius + width / 2) + Vector((0, 0, z))))
        for k in range(count):
            j = (k + 1) % count
            bm.faces.new((inner[k], outer[k], outer[j], inner[j]))

    obj = kit.mesh_object(name, build)
    kit.finish(obj, mat, 0)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return [obj]


def pad(m, root):
    slab = nb.concrete('PadSlab', [
        cylinder('Slab', m['steel'], RADIUS, PAD_TOP, PAD + Vector((0, 0, PAD_TOP / 2)), segments=40, bevel=0.012),
        cylinder('Skirt', m['steel'], RADIUS + 0.04, 0.025, PAD + Vector((0, 0, 0.0125)), segments=40, bevel=0.008),
    ], root, pivot=PAD)
    z = PAD_TOP + 0.002
    paint = material('PadPaint', srgb('#a9aaa6'), 0.85)
    paint['nodColour'] = '#a9aaa6'
    parts = [
        *ring('Ring', m['remap'], PAD, RADIUS - 0.07, 0.06, z),
        *ring('Target', paint, PAD, 0.24, 0.025, z),
        *[box(f'Cross{k}', paint, (0.035, 0.84, 0.004), PAD + Vector((0, 0, z)), bevel=0, rotation=(0, 0, math.pi / 4 + k * math.pi / 2))
          for k in range(2)],
        box('PadSeam0', m['dark'], (2 * RADIUS - 0.05, 0.008, 0.003), PAD + Vector((0, 0, z - 0.0005)), bevel=0),
        box('PadSeam1', m['dark'], (0.008, 2 * RADIUS - 0.05, 0.003), PAD + Vector((0, 0, z - 0.0005)), bevel=0),
        # the front mark: an arrow on the pad's front edge (-Y)
        kit.hexahedron('Arrow', paint, (
            PAD + Vector((-0.07, -0.5, z - 0.002)), PAD + Vector((0.07, -0.5, z - 0.002)), PAD + Vector((0.0, -0.6, z - 0.002)), PAD + Vector((0.0, -0.6, z - 0.002)),
            PAD + Vector((-0.07, -0.5, z + 0.002)), PAD + Vector((0.07, -0.5, z + 0.002)), PAD + Vector((0.0, -0.6, z + 0.002)), PAD + Vector((0.0, -0.6, z + 0.002))), bevel=0),
    ]
    lights = []
    housings = []
    for k in range(LIGHTS):
        a = -math.pi / 2 + 2 * math.pi * k / LIGHTS
        at = PAD + Vector(((RADIUS - 0.015) * math.cos(a), (RADIUS - 0.015) * math.sin(a), PAD_TOP - 0.01))
        housing, light = nb.lamp(f'PadLight{k}', m, at, 'green')
        housings.append(housing)
        lights.append(light)
    return slab, kit.merge('PadMarks', parts, PAD), housings, lights


def post(m, root):
    """The control post: block (baked), cabin and fittings, mast with beacon, dish."""
    block = nb.concrete('PostBlock', [
        kit.frustum('Block', m['steel'], (0.5, 0.46), (0.46, 0.42), 0.16, POST, bevel=0.012),
        box('Stair', m['steel'], (0.12, 0.16, 0.06), POST + Vector((-0.31, -0.08, 0.03)), bevel=0.008),
    ], root, pivot=POST)
    panel = material('NodPanel', srgb('#b4b6b9'), 0.55, 0.2)
    panel['nodColour'] = '#b4b6b9'
    c = POST + Vector((0.02, 0.04, 0.16))
    parts = [
        box('Cabin', panel, (0.36, 0.3, 0.16), c + Vector((0, 0, 0.08)), bevel=0.012),
        kit.hexahedron('Glazing', m['window'], (
            c + Vector((-0.16, -0.155, 0.07)), c + Vector((0.16, -0.155, 0.07)), c + Vector((0.16, -0.14, 0.07)), c + Vector((-0.16, -0.14, 0.07)),
            c + Vector((-0.16, -0.19, 0.15)), c + Vector((0.16, -0.19, 0.15)), c + Vector((0.16, -0.14, 0.15)), c + Vector((-0.16, -0.14, 0.15))), bevel=0.003),
        kit.hexahedron('GlazingSide', m['window'], (
            c + Vector((-0.195, -0.1, 0.07)), c + Vector((-0.18, -0.1, 0.07)), c + Vector((-0.18, 0.08, 0.07)), c + Vector((-0.195, 0.08, 0.07)),
            c + Vector((-0.215, -0.1, 0.15)), c + Vector((-0.18, -0.1, 0.15)), c + Vector((-0.18, 0.08, 0.15)), c + Vector((-0.215, 0.08, 0.15))), bevel=0.003),
        box('Roof', m['armour_dark'], (0.4, 0.34, 0.025), c + Vector((0, 0, 0.17)), bevel=0.008),
        box('Band', m['remap'], (0.364, 0.304, 0.025), c + Vector((0, 0, 0.035)), bevel=0.004),
        box('Door', m['armour_dark'], (0.012, 0.09, 0.12), c + Vector((-0.185, 0.0, -0.1)) + Vector((0, -0.12, 0.16)), bevel=0.003),
        *detail.grille('PostVent', m['steel'], m['dark'], c + Vector((0.08, 0.152, 0.08)), 0.12, 0.07, 'Y', 4),
        box('AcBox', m['steel'], (0.1, 0.08, 0.05), c + Vector((-0.08, 0.06, 0.207)), bevel=0.006),
        *detail.rail('Rail', m['steel'], [c + Vector((-0.19, -0.16, 0.183)), c + Vector((0.19, -0.16, 0.183)), c + Vector((0.19, 0.16, 0.183))], 0.04),
    ]
    body = kit.merge('PostCabin', parts, POST)
    mast_at = c + Vector((0.12, 0.08, 0.183))
    mast = kit.merge('Mast', [
        cylinder('MastPole', m['steel_light'], 0.01, 0.38, mast_at + Vector((0, 0, 0.19)), segments=8, bevel=0),
        beam('MastBar', m['steel'], mast_at + Vector((-0.05, 0, 0.28)), mast_at + Vector((0.05, 0, 0.28)), 0.006),
        beam('MastWhip', m['steel'], mast_at + Vector((0.05, 0, 0.28)), mast_at + Vector((0.05, 0, 0.36)), 0.004),
    ], mast_at)
    housing, beacon = kit.beacon('MastTop', m, mast_at + Vector((0, 0, 0.38)))
    kit.parent(housing, mast)
    dish_at = c + Vector((-0.08, 0.06, 0.232))
    dish = kit.merge('RadarDish', [
        cylinder('DishStand', m['steel'], 0.012, 0.06, dish_at + Vector((0, 0, 0.03)), segments=8, bevel=0),
        cylinder('DishBowl', m['steel_light'], 0.08, 0.03, dish_at + Vector((0, -0.01, 0.08)), rotation=(math.radians(-60), 0, 0), radius2=0.02, segments=20),
        beam('DishFeed', m['steel'], dish_at + Vector((0, -0.01, 0.08)), dish_at + Vector((0, -0.07, 0.11)), 0.006),
    ], dish_at)
    return block, body, mast, beacon, dish


def tanks(m):
    parts = []
    for k, dx in enumerate((-0.09, 0.09)):
        at = TANKS + Vector((dx, 0, 0.11))
        along = (math.pi / 2, 0, 0)
        parts += [
            cylinder(f'Tank{k}', m['remap'], 0.075, 0.4, at, rotation=along, segments=20, bevel=0.01),
            *[sphere(f'TankEnd{k}{s}', m['remap'], 0.075, at + Vector((0, s * 0.2, 0)), 16) for s in (-1, 1)],
            *[box(f'Cradle{k}{j}', m['armour_dark'], (0.17, 0.035, 0.07), at + Vector((0, y, -0.075)), bevel=0.006) for j, y in enumerate((-0.12, 0.12))],
            *[box(f'Strap{k}{j}', m['dark'], (0.155, 0.016, 0.155), at + Vector((0, y, 0)), bevel=0.004) for j, y in enumerate((-0.12, 0.12))],
            box(f'TankPlate{k}', m['hazard'], (0.04, 0.06, 0.005), at + Vector((dx * 0.75, -0.02, 0.06)), bevel=0, rotation=(0, math.copysign(0.6, dx), 0)),
        ]
    parts += [
        box('TankFooting', m['armour_dark'], (0.38, 0.52, 0.03), TANKS + Vector((0, 0, 0.015)), bevel=0.008),
        box('Pump', m['steel'], (0.1, 0.08, 0.1), TANKS + Vector((0.18, -0.3, 0.05)), bevel=0.008),
        *detail.hose('PumpHose', m['dark'], TANKS + Vector((0.18, -0.3, 0.1)), TANKS + Vector((0.3, -0.42, 0.14)), TANKS + Vector((0.42, -0.5, 0.06)), 0.01),
    ]
    return kit.merge('FuelTanks', parts, TANKS)


def build():
    root = nb.start('NodHelipad', 'NodHelipad')
    m = nb.materials()
    slab, marks, housings, lights = pad(m, root)
    for obj in (slab, marks, *housings):
        kit.parent(obj, root)
    for housing, light in zip(housings, lights):
        kit.parent(light, housing)
    block, cabin, mast, beacon, dish = post(m, root)
    for obj in (block, cabin, mast, dish):
        kit.parent(obj, root)
    kit.parent(beacon, mast)
    fuel = kit.parent(tanks(m), root)
    kit.parent(kit.empty('Pad', PAD + Vector((0, 0, PAD_TOP))), root)

    # Build
    kit.keys(slab, 'scale', {0: Vector((0.04, 0.04, 1)), 2: Vector((0.04, 0.04, 1)), 16: Vector((1.03, 1.03, 1)), 19: Vector((1, 1, 1))})
    nb.show_at(marks, 20)
    for k, housing in enumerate(housings):
        kit.pop(housing, 22 + k * 2, 6)
    nb.rise(block, 12, 16, 0.2)
    nb.rise(cabin, 22, 16, 0.4)
    kit.grow(fuel, 36, 12, 2)
    kit.grow(mast, 44, 14, 2)
    kit.pop(dish, 50, 10)
    nb.all_to_build()

    # Idle: the lights run round the pad (two laps), the dish turns, the beacon blinks
    lap = kit.IDLE_END // 2
    step = lap // LIGHTS
    nb.blinking([(light, kit.flashes((k * step, step + 1), (lap + k * step, step + 1))) for k, light in enumerate(lights)] +
                [(beacon, kit.flashes((0, 6), (30, 6)))])
    kit.keys(dish, 'rotation_euler', {0: Vector((0, 0, 0)), kit.IDLE_END: Vector((0, 0, 2 * math.pi))}, 'LINEAR')
    kit.to_track(dish, 'Idle')

    block.location = POST
    cabin.location = POST
    dish.rotation_euler = (0, 0, 0)
    for light in (*lights, beacon):
        light.scale = (1, 1, 1)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAHPAD', {'Build': [14, 30, 48, 66], 'Idle': [0, 10]}, scale=2.7, target=(0, 0, 0.2), texture=1024)
