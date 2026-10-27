"""
Tiberian Fallout – Nod helipad (NAHPAD), after Tiberian Sun.

On 2 × 2 cells: a raised, round landing pad of dark concrete – a thick red (house
colour) rim, a dark cross dividing it into four fields and four white landing lights –
standing on a mound of light, rough concrete that spills out towards the front. At the
back right a light grey control tower: a concrete footing, a cabin with dark windows, a
pale radar ring on a turntable and an antenna mast with a beacon. At the left three red
fuel tanks on a footing, and from them a dark lattice gantry runs along the back left
edge to the back corner and over to the tower.

Nodes the game uses:
    Pad      the landing point on the middle of the pad; its -Y is the way an aircraft
             faces when it has landed
Animations (glTF clips)
    Build    one-shot, 2 s: the mound comes up out of the ground, the pad rises onto it,
             the tower's footing and cabin rise, the tanks and the gantry grow
    Idle     loop, 2 s: the landing lights flash round the pad, all four together at
             the end; the radar ring turns, the mast's beacon blinks

Run headless:

    blender -b --factory-startup --python blender/NAHPAD.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); origin in the middle on the ground.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodstructure as nb  # noqa: E402

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
HIDDEN = kit.HIDDEN

PAD = Vector((-0.12, -0.2, 0))      # the pad's middle (on the ground)
RADIUS = 0.66                       # the pad's concrete
RIM = 0.055                         # the red rim's width (it overhangs a little)
PAD_LOW, PAD_TOP = 0.22, 0.3        # the pad's underside and top
TOWER = Vector((0.2, 0.78, 0))
TANKS = Vector((-0.8, -0.76, 0))
GANTRY_Z = 0.36                     # the gantry's lower chord
LIGHTS = 4


def coloured(name, hex_colour, roughness=0.6, metallic=0.2):
    mat = material(name, srgb(hex_colour), roughness, metallic)
    mat['nodColour'] = hex_colour
    return mat


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
    return obj


def mound(m, root):
    """The rough light concrete under the pad: an irregular lump, wider towards the
    front, low at the back right where the tower stands; a few boulders at its foot."""
    count = 16
    bottom, top = [], []
    for k in range(count):
        a = 2 * math.pi * k / count
        d = Vector((math.cos(a), math.sin(a), 0))
        front = max(0.0, -(d.x * -0.3 + d.y))           # towards -y, a little -x
        back_right = max(0.0, d.x * 0.7 + d.y * 0.7)
        jag = 0.05 * math.sin(5 * a + 1.3) + 0.03 * math.sin(11 * a)
        towards_tanks = max(0.0, -(d.x + d.y) / math.sqrt(2)) ** 6
        rb = 0.8 + 0.12 * front - 0.2 * back_right - 0.14 * towards_tanks + jag
        rt = 0.58 + 0.03 * math.sin(7 * a)
        bottom.append((PAD.x + d.x * rb, PAD.y + d.y * rb))
        top.append((PAD.x + d.x * rt, PAD.y + d.y * rt))
    parts = [nb.prism('MoundBody', m['steel'], bottom, top, 0, PAD_LOW + 0.005, 0.02)]
    for k, (a, size, h) in enumerate(((-100, 0.16, 0.08), (-70, 0.12, 0.06), (-115, 0.12, 0.07), (-40, 0.1, 0.05), (-165, 0.1, 0.06))):
        r = math.radians(a)
        at = PAD + Vector((math.cos(r), math.sin(r), 0)) * 0.84
        parts.append(kit.frustum(f'Boulder{k}', m['steel'], (size, size * 0.8), (size * 0.55, size * 0.4), h, at, bevel=0.02))
        parts[-1].rotation_euler.z = r + 0.4
    return nb.concrete('Mound', parts, root, '#b1aea4', pivot=PAD)


def pad(m, root):
    """The landing pad (concrete), its markings with the light housings, and the lights."""
    disc = nb.concrete('PadSlab', [
        cylinder('Slab', m['steel'], RADIUS, PAD_TOP - PAD_LOW, PAD + Vector((0, 0, (PAD_LOW + PAD_TOP) / 2)), segments=48, bevel=0.01),
    ], root, '#3e3f43', pivot=PAD + Vector((0, 0, PAD_LOW)))
    z = PAD_TOP
    rim = nb.lathe('Rim', m['remap'], [(RADIUS - RIM, z - 0.012), (RADIUS - RIM, z + 0.012), (RADIUS + 0.02, z + 0.012), (RADIUS + 0.02, z - 0.05)],
                   PAD, segments=48, bevel=0.004)
    field = coloured('PadField', '#4d4e53', 0.85, 0.1)
    parts = [rim]
    # the four fields between the dark cross (slightly lighter plates)
    inner = RADIUS - RIM - 0.005
    for q in range(4):
        a0 = q * math.pi / 2 + 0.06
        a1 = (q + 1) * math.pi / 2 - 0.06

        def build(bm, a0=a0, a1=a1):
            steps = 10
            centre_off = Vector((math.cos((a0 + a1) / 2), math.sin((a0 + a1) / 2), 0)) * 0.045
            c = bm.verts.new(PAD + centre_off + Vector((0, 0, z + 0.003)))
            arc = [bm.verts.new(PAD + Vector((inner * math.cos(a0 + (a1 - a0) * i / steps), inner * math.sin(a0 + (a1 - a0) * i / steps), z + 0.003)))
                   for i in range(steps + 1)]
            for i in range(steps):
                bm.faces.new((c, arc[i], arc[i + 1]))

        obj = kit.mesh_object(f'Field{q}', build)
        kit.finish(obj, field, 0)
        parts.append(obj)
    parts.append(ring('Target', coloured('PadTarget', '#77787c', 0.8, 0.1), PAD, 0.2, 0.02, z + 0.005))
    lights, light_at = [], []
    for k in range(LIGHTS):
        a = k * math.pi / 2       # on the cross's arms: the corners of the pad on screen
        at = PAD + Vector((math.cos(a) * 0.46, math.sin(a) * 0.46, z))
        housing, light = kit.beacon(f'PadLight{k}', m, at, 'white')
        parts.append(housing)
        parts.append(cylinder(f'PadLightBase{k}', m['armour_dark'], 0.032, 0.008, at + Vector((0, 0, 0.004)), segments=12, bevel=0))
        lights.append(light)
        light_at.append(at)
    marks = kit.merge('PadMarks', parts, PAD + Vector((0, 0, z)))
    return disc, marks, lights


def tower(m, root):
    """The control tower at the back right: footing (concrete), cabin, ring, mast."""
    footing = nb.concrete('TowerFooting', [
        kit.frustum('Footing', m['steel'], (0.36, 0.36), (0.32, 0.32), 0.26, TOWER, bevel=0.015),
        kit.frustum('FootingStep', m['steel'], (0.2, 0.12), (0.18, 0.1), 0.1, TOWER + Vector((-0.27, -0.06, 0)), bevel=0.01),
    ], root, '#a9a8a2', pivot=TOWER)
    panel = coloured('TowerPanel', '#d4d4d2', 0.6, 0.1)
    c = TOWER + Vector((0, 0, 0.26))
    parts = [
        kit.frustum('Cabin', panel, (0.3, 0.3), (0.26, 0.26), 0.2, c, bevel=0.012),
        box('CabinRoof', m['steel_light'], (0.29, 0.29, 0.025), c + Vector((0, 0, 0.212)), bevel=0.006),
        box('CabinBand', m['remap'], (0.296, 0.296, 0.022), c + Vector((0, 0, 0.03)), bevel=0.003),
        cylinder('Turntable', m['steel'], 0.06, 0.04, c + Vector((0.02, 0.02, 0.245)), segments=16, bevel=0.004),
    ]
    # dark windows on the two sides the camera sees (-y and +x), slanted with the walls
    for k, (normal, side) in enumerate(((Vector((0, -1, 0)), Vector((1, 0, 0))), (Vector((1, 0, 0)), Vector((0, 1, 0))))):
        lo, hi = c + normal * 0.1495 + Vector((0, 0, 0.08)), c + normal * 0.1355 + Vector((0, 0, 0.17))
        out = normal * 0.004
        parts.append(kit.hexahedron(f'Window{k}', m['window'], (
            lo - side * 0.1, lo + side * 0.1, lo + side * 0.1 + out, lo - side * 0.1 + out,
            hi - side * 0.09, hi + side * 0.09, hi + side * 0.09 + out, hi - side * 0.09 + out), bevel=0))
    parts.append(box('Door', m['armour_dark'], (0.012, 0.08, 0.13), c + Vector((-0.149, -0.05, 0.065)), bevel=0.003))
    parts += detail.rail('TowerRail', m['steel'], [c + Vector((-0.13, -0.13, 0.225)), c + Vector((0.13, -0.13, 0.225)), c + Vector((0.13, 0.13, 0.225))], 0.04)
    mast_at = c + Vector((-0.08, 0.08, 0.225))
    parts += [
        cylinder('MastPole', m['steel_light'], 0.01, 0.36, mast_at + Vector((0, 0, 0.18)), segments=8, bevel=0),
        beam('MastBar', m['steel'], mast_at + Vector((-0.05, 0.05, 0.27)), mast_at + Vector((0.05, -0.05, 0.27)), 0.007),
        beam('MastBar2', m['steel'], mast_at + Vector((-0.035, -0.035, 0.31)), mast_at + Vector((0.035, 0.035, 0.31)), 0.006),
    ]
    cabin = kit.merge('TowerCabin', parts, TOWER)
    housing, beacon = kit.beacon('MastTop', m, mast_at + Vector((0, 0, 0.36)))
    housing = kit.merge('MastTopHousing', [housing], mast_at)
    ring_at = c + Vector((0.02, 0.02, 0.265))
    pale = coloured('RadarRing', '#b9b6d6', 0.4, 0.4)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.125, minor_radius=0.009, major_segments=28, minor_segments=6)
    hoop = bpy.context.active_object
    hoop.name = 'RingHoop'
    kit.finish(hoop, pale, 0)
    hoop.rotation_euler = (math.radians(70), 0, 0)
    hoop.location = ring_at + Vector((0, 0, 0.14))
    dish = kit.merge('RadarDish', [
        cylinder('RingPost', m['steel'], 0.012, 0.012, ring_at + Vector((0, 0, 0.006)), segments=8, bevel=0),
        beam('RingFork0', m['steel'], ring_at + Vector((-0.02, 0, 0.004)), ring_at + Vector((-0.125, 0, 0.14)), 0.012),
        beam('RingFork1', m['steel'], ring_at + Vector((0.02, 0, 0.004)), ring_at + Vector((0.125, 0, 0.14)), 0.012),
        hoop,
        sphere('RingHub', m['steel_light'], 0.022, ring_at + Vector((0, 0, 0.14)), 12),
    ], ring_at)
    return footing, cabin, housing, beacon, dish


def tanks(m):
    parts = [box('TankFooting', m['armour_dark'], (0.24, 0.42, 0.03), TANKS + Vector((0, 0, 0.015)), bevel=0.008)]
    parts[-1].rotation_euler.z = math.pi / 4
    for k, off in enumerate(((-0.11, 0.11), (0.0, 0.0), (0.11, -0.11))):
        at = TANKS + Vector((off[0], off[1], 0.03))
        h, r = (0.2, 0.09) if k == 1 else (0.16, 0.085)
        parts += [
            cylinder(f'Tank{k}', m['remap'], r, h, at + Vector((0, 0, h / 2)), segments=20, bevel=0.006),
            sphere(f'TankDome{k}', m['remap'], r, at + Vector((0, 0, h)), 16),
            cylinder(f'TankBand{k}', m['dark'], r + 0.003, 0.016, at + Vector((0, 0, h * 0.35)), segments=20, bevel=0),
            cylinder(f'TankValve{k}', m['steel'], 0.014, 0.03, at + Vector((0, 0, h + r + 0.005)), segments=8, bevel=0),
        ]
    parts += detail.hose('TankHose', m['dark'], TANKS + Vector((0.1, -0.1, 0.1)), TANKS + Vector((0.22, -0.02, 0.05)), TANKS + Vector((0.2, 0.12, 0.03)), 0.01)
    return kit.merge('FuelTanks', parts, TANKS)


def gantry(m):
    """A dark box truss on legs from the tanks along the back left edge (-x) to the back
    corner, then along the back edge (+y) to the tower."""
    steel = m['nplate_dark']
    x, y = -0.9, 0.88
    path = [Vector((x, TANKS.y + 0.24, 0)), Vector((x, y, 0)), Vector((TOWER.x - 0.152, y, 0))]
    parts = []
    h, w = 0.08, 0.035
    for i, (a, b) in enumerate(zip(path, path[1:])):
        d = (b - a).normalized()
        side = Vector((-d.y, d.x, 0)) * w
        n = max(2, round((b - a).length / 0.1))
        for s in (-1, 1):
            for zz in (GANTRY_Z, GANTRY_Z + h):
                parts.append(beam(f'Chord{i}{s}{zz:.2f}', steel, a + side * s + Vector((0, 0, zz)), b + side * s + Vector((0, 0, zz)), 0.012))
            for k in range(n):   # zigzag diagonals in both side faces
                p0 = a + (b - a) * (k / n) + side * s
                p1 = a + (b - a) * ((k + 1) / n) + side * s
                lo, hi = Vector((0, 0, GANTRY_Z)), Vector((0, 0, GANTRY_Z + h))
                parts.append(beam(f'Diag{i}{s}{k}', steel, p0 + (lo if k % 2 else hi), p1 + (hi if k % 2 else lo), 0.007))
        for k in range(n + 1):   # rungs across the top
            p = a + (b - a) * (k / n) + Vector((0, 0, GANTRY_Z + h))
            parts.append(beam(f'Rung{i}{k}', steel, p - side, p + side, 0.008))
    for k, p in enumerate((path[0], path[1], path[0] + (path[1] - path[0]) * 0.5)):
        parts.append(box(f'Leg{k}', steel, (0.03, 0.03, GANTRY_Z), p + Vector((0, 0, GANTRY_Z / 2)), bevel=0.003))
        parts.append(box(f'LegFoot{k}', m['armour_dark'], (0.06, 0.06, 0.02), p + Vector((0, 0, 0.01)), bevel=0.003))
    return kit.merge('Gantry', parts, path[1])


def build():
    root = nb.start('NodHelipad', 'NodHelipad', 60)
    m = nb.materials()
    m['glow_white'] = material('GlowWhite', (0, 0, 0), 1.0, emission=srgb('#fff4d8'), strength=3, alpha=0.3)
    hill = kit.parent(mound(m, root), root)
    disc, marks, lights = pad(m, root)
    kit.parent(disc, root)
    kit.parent(marks, disc)
    for light in lights:
        kit.parent(light, disc)
    footing, cabin, housing, beacon, dish = tower(m, root)
    kit.parent(footing, root)
    kit.parent(cabin, root)
    for obj in (housing, beacon, dish):
        kit.parent(obj, cabin)
    fuel = kit.parent(tanks(m), root)
    truss = kit.parent(gantry(m), root)
    kit.parent(kit.empty('Pad', PAD + Vector((0, 0, PAD_TOP))), root)

    # Build (only translations above the lights, the beacon and the ring, which Idle drives)
    nb.rise(hill, 0, 16, PAD_LOW + 0.03)
    nb.rise(disc, 10, 16, PAD_TOP + 0.06)
    nb.rise(footing, 18, 14, 0.3)
    nb.rise(cabin, 26, 16, 0.75)
    kit.grow(fuel, 34, 10, 2)
    kit.grow(truss, 42, 14, 2)
    nb.all_to_build()

    # Idle: the lights flash round the pad, then all four together; the ring turns, the
    # beacon blinks
    end = kit.IDLE_END
    nb.blinking([(light, kit.flashes((k * 9, 6), (40, 6), (50, 6))) for k, light in enumerate(lights)] +
                [(beacon, kit.flashes((0, 6), (30, 6)))])
    kit.keys(dish, 'rotation_euler', {0: Vector((0, 0, 0)), end: Vector((0, 0, 2 * math.pi))}, 'LINEAR')
    kit.to_track(dish, 'Idle')

    hill.location = PAD
    disc.location = PAD + Vector((0, 0, PAD_LOW))
    footing.location = cabin.location = TOWER
    fuel.scale = truss.scale = (1, 1, 1)
    dish.rotation_euler = (0, 0, 0)
    for light in (*lights, beacon):
        light.scale = (1, 1, 1)
    return len(kit.collection().objects)


def _rest():
    """Puts back what evaluating Idle leaves behind (lights off, the ring turned) – only
    for the previews; the glTF is not affected."""
    for obj in bpy.data.objects:
        if obj.name.endswith('Light'):
            obj.scale = (1, 1, 1)
    if 'RadarDish' in bpy.data.objects:
        bpy.data.objects['RadarDish'].rotation_euler = (0, 0, 0)


def _render_and_rest(frames, out_dir, _render=kit.render_preview):
    result = _render(frames, out_dir)
    _rest()
    return result


if __name__ == '__main__':
    kit.render_preview = _render_and_rest
    nb.main(build, 'NAHPAD', {'Build': [12, 24, 36, 60], 'Idle': [0, 12, 42]}, ortho=2.7, target=(0, 0, 0.25), texture=1024)
