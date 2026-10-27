"""
Tiberian Fallout – GDI radar (GARADR), after Tiberian Sun.

A square, stepped camouflaged base (foundation 2 × 2 cells) with the radar tower in
its middle: a camouflaged block between dark steel pillars, a narrower top storey with
a band in the house colour, and on it the turntable with the antenna – a wide, curved
plate with rolled ends, braced from behind, the feed horn in front of it. Around the
tower: a generator block with a house-colour housing at the front left, a low house-colour
cabinet in front, a small sensor dome on legs at the front right and a house-colour
vaulted shed with a grey pipe arch on the right.

Materials as for the barracks (see GAPILE.py): Camo_* is the baked camouflage in a
pale shade of the house colour, Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.6 s: the base spreads, the tower rises out of it, the
             outbuildings pop up, the mast telescopes up, the antenna unfolds
    Idle     loop, 6 s: the antenna turns once round, the beacons blink, the dome's
             lights run round

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GARADR.py [-- --preview 0,40,78 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -1 … 1 and y -1 … 1.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import gdibuilding as gb  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GARADR.glb')
BLEND = os.path.join(HERE, 'GARADR.blend')

BUILD_END = 78
kit.IDLE_END = 180      # one turn of the antenna

BASE = 0.1              # top of the stepped base
TOWER = (-0.36, -0.12, 0.38, 0.62)    # x0, y0, x1, y1 of the tower block
TOWER_TOP = 0.56
UPPER_TOP = 0.74
AXIS = Vector((0.01, 0.25, UPPER_TOP))   # the turntable's axis, on the top storey
DOME = Vector((0.5, -0.5, BASE))

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m['hazard'] = material('Hazard', srgb('#e2a21c'), 0.6)
    return m


# --------------------------------------------------------------------------- parts

def base(m, root):
    """The stepped base: a dark footing and the camouflaged step with sloped edges."""
    footing = gb.slab('Footing', m['concrete_dark'], gb.chamfered(-0.98, -0.98, 0.98, 0.98, 0.12), 0.04, inset=0.01, bevel=0.004)
    step = gb.camo(gb.slab('Step', m['sand'], gb.chamfered(-0.92, -0.92, 0.92, 0.92, 0.1), BASE - 0.04, inset=0.05, z0=0.04, bevel=0.006), root)
    parts = [footing]
    for k in range(4):  # dark joints over the step
        a = -0.6 + k * 0.4
        parts.append(box(f'JointX{k}', m['concrete_dark'], (0.008, 1.7, 0.003), (a, 0, BASE + 0.0015), bevel=0))
    parts.append(box('Path', m['grating'], (0.3, 0.6, 0.008), (0.0, -0.62, BASE + 0.004), bevel=0))
    return kit.merge('Base', parts), step


def tower(m, root):
    """The tower block and the top storey (camouflage) and their steel and house-colour details."""
    x0, y0, x1, y1 = TOWER
    body = gb.slab('TowerBody', m['sand'], gb.chamfered(x0, y0, x1, y1, 0.06), TOWER_TOP - BASE, inset=0.04, z0=BASE, bevel=0.01)
    upper = gb.slab('TowerUpper', m['sand'], gb.chamfered(x0 + 0.08, y0 + 0.1, x1 - 0.06, y1 - 0.04, 0.05), UPPER_TOP - TOWER_TOP, inset=0.03,
                    z0=TOWER_TOP, bevel=0.008)
    shell = gb.camo(kit.merge('TowerShell', [body, upper]), root)
    parts = [box('Ledge', m['steel'], (x1 - x0 - 0.04, y1 - y0 - 0.04, 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, TOWER_TOP + 0.015), bevel=0.006)]
    # dark steel pillars at the corners and in the front, a door between them
    for k, (x, y) in enumerate(((x0 + 0.02, y0 + 0.02), (x1 - 0.02, y0 + 0.02), (x1 - 0.02, y1 - 0.02), (-0.1, y0 + 0.02), (0.12, y0 + 0.02))):
        parts.append(box(f'Pillar{k}', m['steel'], (0.07, 0.07, TOWER_TOP - BASE + 0.02), (x, y, (TOWER_TOP + BASE) / 2), bevel=0.006))
        parts.append(box(f'PillarCap{k}', m['steel_light'], (0.08, 0.08, 0.02), (x, y, TOWER_TOP + 0.03), bevel=0.004))
    parts.append(box('Door', m['dark'], (0.15, 0.012, 0.2), (0.01, y0 + 0.01, BASE + 0.1), bevel=0.003))
    parts.append(box('DoorHood', m['steel_light'], (0.2, 0.05, 0.015), (0.01, y0 - 0.005, BASE + 0.215), bevel=0.003))
    for k, x in enumerate((-0.26, 0.25)):
        parts.append(box(f'Window{k}', m['window'], (0.08, 0.012, 0.05), (x, y0 + 0.02, 0.4), bevel=0.002))
    # the band round the top storey, vents on its right side
    parts.append(box('BandFront', m['remap'], (x1 - x0 - 0.17, 0.012, 0.05), ((x0 + x1) / 2 + 0.01, y0 + 0.11, UPPER_TOP - 0.07), bevel=0.003))
    parts.append(box('BandSide', m['remap'], (0.012, y1 - y0 - 0.17, 0.05), (x1 - 0.075, (y0 + y1) / 2 + 0.03, UPPER_TOP - 0.07), bevel=0.003))
    for k in range(4):
        parts.append(box(f'SideRib{k}', m['steel'], (0.02, 0.025, TOWER_TOP - BASE - 0.06), (x1 - 0.02, y0 + 0.15 + k * 0.13, (TOWER_TOP + BASE) / 2), bevel=0))
    return shell, kit.merge('TowerDetails', parts)


def generator(m, root):
    """The generator block at the front left with its house-colour housing; origin at the foot."""
    c = Vector((-0.56, -0.5, BASE))
    body = gb.camo(gb.slab('GenBody', m['sand'], gb.chamfered(c.x - 0.3, c.y - 0.3, c.x + 0.3, c.y + 0.3, 0.04), 0.14, inset=0.03, z0=BASE, bevel=0.006), root)
    parts = [
        box('GenHousing', m['remap'], (0.4, 0.36, 0.13), c + Vector((0.0, 0.02, 0.14 + 0.065)), bevel=0.03),
        box('GenGrille', m['dark'], (0.28, 0.012, 0.06), c + Vector((0.0, -0.165, 0.2)), bevel=0),
    ]
    for k in range(3):
        parts.append(box(f'GenSlat{k}', m['steel'], (0.26, 0.012, 0.006), c + Vector((0, -0.17, 0.18 + k * 0.02)), bevel=0))
    parts.append(cylinder('GenExhaust', m['steel'], 0.02, 0.12, c + Vector((0.15, 0.14, 0.33)), segments=10))
    details = kit.merge('GenDetails', parts, c)
    group = kit.empty('Generator', c)
    for obj in (body, details):
        kit.parent(obj, group)
    return group


def cabinet(m):
    """A low house-colour cabinet in front of the tower; origin at its foot."""
    c = Vector((-0.08, -0.48, BASE))
    parts = [
        box('CabFoot', m['steel'], (0.34, 0.24, 0.03), c + Vector((0, 0, 0.015)), bevel=0.004),
        box('CabBody', m['remap'], (0.3, 0.2, 0.12), c + Vector((0, 0, 0.09)), bevel=0.025),
        box('CabPanel', m['steel_light'], (0.12, 0.012, 0.06), c + Vector((0.05, -0.1, 0.09)), bevel=0.002),
        beam('CabCable', m['dark'], c + Vector((0.0, 0.1, 0.1)), Vector((-0.05, TOWER[1] + 0.02, 0.25)), 0.02),
    ]
    return kit.merge('Cabinet', parts, c)


def dome(m):
    """The small sensor dome on six legs over a square plinth; returns (group, light ring)."""
    c = DOME
    parts = [
        box('DomePlinth', m['concrete'], (0.42, 0.42, 0.06), c + Vector((0, 0, 0.03)), bevel=0.01),
        box('DomePlinthTop', m['steel'], (0.36, 0.36, 0.012), c + Vector((0, 0, 0.066)), bevel=0.003),
        cylinder('DomeRing', m['steel'], 0.16, 0.03, c + Vector((0, 0, 0.25)), segments=24),
    ]
    for k in range(6):
        a = 2 * math.pi * k / 6
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'DomeLeg{k}', m['steel'], c + d * 0.14 + Vector((0, 0, 0.07)), c + d * 0.15 + Vector((0, 0, 0.24)), 0.022))
    parts.append(cylinder('DomeCore', m['dark'], 0.08, 0.17, c + Vector((0, 0, 0.155)), segments=16))
    hemi = gb.lathe('DomeShell', m['sand_light'], [(0.155 * math.cos(t), 0.155 * math.sin(t)) for t in
                                                    (math.radians(a) for a in range(0, 91, 10))][:-1] + [(0.001, 0.155)],
                    c + Vector((0, 0, 0.265)), segments=24)
    parts.append(hemi)
    parts.append(cylinder('DomeTip', m['steel'], 0.012, 0.06, c + Vector((0, 0, 0.45)), segments=8))
    group = kit.merge('Dome', parts, c)
    lights = [sphere(f'DomeLamp{k}', m['lamp_green'], 0.014, c + Vector((math.cos(a) * 0.165, math.sin(a) * 0.165, 0.25)), 8)
              for k, a in enumerate(2 * math.pi * k / 8 for k in range(8))]
    return group, lights


def shed(m):
    """The house-colour vaulted shed on the right with a grey pipe arch; origin at its foot."""
    c = Vector((0.66, 0.24, BASE))
    r = 0.17
    parts = [
        box('ShedFoot', m['concrete_dark'], (0.42, 0.66, 0.04), c + Vector((0, 0, 0.02)), bevel=0.006),
        box('ShedWall', m['steel'], (0.36, 0.6, 0.06), c + Vector((0, 0, 0.07)), bevel=0.004),
        gb.prism('ShedVault', m['remap'], gb.arc((c.x, c.z + 0.1), r, 0, math.pi, 16), c.y - 0.3, c.y + 0.3, 'Y', bevel=0.004),
    ]
    for k in range(4):  # ribs over the vault
        y = c.y - 0.24 + k * 0.16
        rib = gb.arc((c.x, c.z + 0.1), r + 0.01, 0, math.pi, 16) + gb.arc((c.x, c.z + 0.1), r - 0.01, math.pi, 0, 16)
        parts.append(gb.prism(f'ShedRib{k}', m['steel'], rib, y - 0.01, y + 0.01, 'Y'))
    # the pipe arch in front of the shed, grey, from the base up and back down
    pts = [Vector((c.x + 0.05 + 0.18 * math.cos(t), c.y - 0.42, BASE + 0.22 * math.sin(t))) for t in (math.pi * k / 8 for k in range(9))]
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        parts.append(beam(f'Arch{k}', m['steel_light'], a, b, 0.04))
    parts.append(beam('ArchFeed', m['steel_light'], pts[-1], Vector((pts[-1].x, c.y - 0.28, BASE + 0.02)), 0.04))
    return kit.merge('Shed', parts, c)


def antenna(m):
    """The turntable, the mast and the antenna; returns (turntable, mast, head): the head
    turns about z (Idle), its origin on the mast's top."""
    table = kit.merge('Turntable', [
        cylinder('TableBase', m['steel'], 0.15, 0.05, AXIS + Vector((0, 0, 0.025)), segments=24),
        cylinder('TableRing', m['remap'], 0.155, 0.015, AXIS + Vector((0, 0, 0.045)), segments=24, bevel=0),
    ], AXIS)
    top = AXIS + Vector((0, 0, 0.2))
    mast = kit.merge('Mast', [
        cylinder('MastPole', m['steel_light'], 0.04, 0.2, AXIS + Vector((0, 0, 0.1)), segments=12),
        cylinder('MastCollar', m['steel'], 0.06, 0.04, top - Vector((0, 0, 0.02)), segments=12),
    ], AXIS + Vector((0, 0, 0.04)))

    # the plate: curved in plan (concave to the front), tilted back, rolled ends
    half, height, bend = 0.52, 0.36, 1.3
    tilt = math.radians(40)
    centre = top + Vector((0, -0.02, 0.14))
    plan = []
    steps = 12
    for k in range(steps + 1):
        a = -math.asin(half / bend) + 2 * math.asin(half / bend) * k / steps
        plan.append((bend * math.sin(a), bend * (1 - math.cos(a))))
    outline = plan + [(x, y + 0.04) for x, y in reversed(plan)]
    plate = gb.prism('Plate', m['sand_light'], outline, -height / 2, height / 2, 'Z', bevel=0.003)
    parts = [plate]
    for k in range(5):  # panel lines on the face
        z = -height / 2 + (k + 1) * height / 6
        line = gb.prism(f'PlateLine{k}', m['steel'], [(x, y - 0.004) for x, y in plan] + [(x, y + 0.002) for x, y in reversed(plan)], z - 0.004, z + 0.004, 'Z')
        parts.append(line)
    for s in (-1, 1):  # rolled ends
        x, y = plan[0 if s < 0 else -1]
        parts.append(cylinder(f'Roll{s}', m['steel'], 0.045, height + 0.04, (x + s * 0.02, y + 0.02, 0), segments=14))
    # the bracing behind it and the feed horn in front
    for s in (-1, 1):
        parts.append(beam(f'Brace{s}', m['steel'], (s * 0.4, 0.12, 0.1), (0, 0.22, -0.06), 0.025))
        parts.append(beam(f'BraceLow{s}', m['steel'], (s * 0.4, 0.12, -0.1), (0, 0.22, -0.06), 0.025))
    parts.append(box('Spine', m['steel'], (0.06, 0.12, 0.26), (0, 0.18, -0.02), bevel=0.006))
    parts.append(beam('FeedArm', m['steel'], (0, -0.005, -0.15), (0, -0.14, -0.04), 0.016))
    parts.append(box('FeedHorn', m['steel_light'], (0.05, 0.05, 0.04), (0, -0.15, -0.035), bevel=0.006))
    dish = kit.merge('AntennaDish', parts)
    dish.rotation_euler = (-tilt, 0, 0)
    dish.location = centre
    kit.bake_modifiers(dish)
    dish = kit.merge('AntennaDish', [dish], top)
    head = kit.merge('AntennaHead', [
        box('HeadYoke', m['steel'], (0.14, 0.14, 0.08), top + Vector((0, 0.02, 0.04)), bevel=0.008),
        beam('HeadArm', m['steel'], top + Vector((0, 0.02, 0.06)), centre + Vector((0, 0.12, 0.0)), 0.05),
    ], top)
    kit.parent(dish, head)
    return table, mast, head, dish


# --------------------------------------------------------------------------- model

def build():
    gb.start('GDIRadar', BUILD_END)
    m = materials()
    root = kit.empty('GDIRadar')
    keys = kit.keys
    H = kit.HIDDEN

    # ---- the base spreads
    ground, step = base(m, root)
    ground = kit.parent(ground, root)
    kit.parent(step, ground)
    keys(ground, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 14: Vector((1.03, 1.03, 1)), 17: Vector((1, 1, 1))})

    # ---- the tower rises
    group = kit.parent(kit.empty('TowerGroup'), root)
    for obj in tower(m, root):
        kit.parent(obj, group)
    keys(group, 'location', {0: Vector((0, 0, -0.75)), 8: Vector((0, 0, -0.75)), 32: Vector((0, 0, 0.012)), 36: Vector((0, 0, 0))})

    # ---- the outbuildings
    gen = kit.parent(generator(m, root), root)
    kit.pop(gen, 24, 8)
    kit.pop(kit.parent(cabinet(m), root), 30, 7)
    dome_obj, dome_lamps = dome(m)
    kit.parent(dome_obj, root)
    kit.pop(dome_obj, 34, 8)
    kit.pop(kit.parent(shed(m), root), 28, 8)

    # ---- the mast telescopes up, the antenna unfolds
    table, mast, head, dish = antenna(m)
    kit.parent(table, group)
    kit.pop(table, 38, 6)
    kit.parent(mast, table)
    kit.grow(mast, 42, 10, 2)
    kit.parent(head, mast)
    keys(head, 'scale', {0: Vector((H, H, H)), 50: Vector((H, H, H)), 51: Vector((0.3, 0.3, 0.3)), 56: Vector((1, 1, 1))})
    keys(dish, 'scale', {0: Vector((H, 1, 1)), 52: Vector((H, 1, 1)), 64: Vector((1.06, 1, 1)), 68: Vector((1, 1, 1))})

    # ---- lights
    lights = []
    x0, y0, x1, y1 = TOWER
    for k, (x, y) in enumerate(((x0 + 0.02, y0 + 0.02), (x1 - 0.02, y0 + 0.02), (x1 - 0.02, y1 - 0.02))):
        gb.beacon(f'Corner{k}', m, (x, y, TOWER_TOP + 0.04), 'red', group, 60 + 2 * k, kit.flashes(*((s + 20 * k, 8) for s in range(0, 180, 60))), lights)
    gb.beacon('GenLamp', m, (-0.56 - 0.17, -0.5 + 0.17, BASE + 0.27), 'amber', gen, 66, kit.flashes(*((s, 10) for s in range(0, 180, 30))), lights)
    gb.beacon('ShedLamp', m, (0.66, 0.24 + 0.32, BASE + 0.3), 'green', root, 68, kit.flashes((0, 150)), lights)
    for k, lamp in enumerate(dome_lamps):
        kit.parent(lamp, dome_obj)
        lights.append((lamp, kit.flashes(*((s + 4 * k, 6) for s in range(0, 180, 32)))))

    gb.clips([(head, lambda o: gb.spin(o, 1))], lights)
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=3.0, target=(0, 0, 0.45))
