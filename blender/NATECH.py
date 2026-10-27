"""
Tiberian Fallout – Nod tech center (NATECH), after Tiberian Sun.

A low, wide concrete platform with a dirty rim (foundation 2 × 2 cells). On it a
stepped round dome on the left and a stepped, angular tower at the back right; three
thick red conduits arch from the platform's left edge over the dome into the tower's
flank. Two red pods sit half sunk into the platform's front edge, a small sensor turns
on the tower's top.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the platform rises out of the ground, the dome and the
             tower's tiers come up, the conduits grow from the platform to the tower,
             the pods and the sensor appear, the lights come on
    Idle     loop, 2 s: glowing charges run up the conduits into the tower, the
             sensor turns, the pods' lamps blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NATECH.py [-- --preview 0,30,72 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); seen in the game, (-0.5, 0.5) is the top one.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nod  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'NATECH.glb')
BLEND = os.path.join(HERE, 'NATECH.blend')
BUILD_END = 72

DECK = 0.13
DOME = Vector((-0.28, 0.0, DECK))
TOWER = Vector((0.38, 0.36, DECK))
# the tower's tiers: centre offset, bottom size, top size, height (stacked)
TIERS = (((0, 0), (0.78, 0.74), (0.66, 0.62), 0.2),
         ((0.04, 0.05), (0.56, 0.52), (0.46, 0.42), 0.18),
         ((0.07, 0.09), (0.36, 0.32), (0.26, 0.22), 0.2))
PODS = (Vector((-0.46, -0.78, 0)), Vector((0.2, -0.86, 0)))

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def bezier(a, c, b, t):
    return (1 - t) ** 2 * a + 2 * (1 - t) * t * c + t * t * b


# the conduits: start on the platform's left edge, control point, end in the tower's flank
CONDUITS = []
for k in range(3):
    start = Vector((-0.86 + 0.06 * k, -0.28 + 0.24 * k, DECK - 0.02))
    end = TOWER + Vector((-0.3, -0.12 + 0.12 * k, 0.3 + 0.05 * k))
    control = (start + end) / 2 + Vector((0.05, -0.12, 0.72 - 0.06 * k))
    CONDUITS.append((start, control, end))


def platform(m, root):
    """The low concrete platform (faceted), its dirty rim and seams."""
    body = nod.lathe('PlatformBody', m['steel'], ((0.98, 0.0), (0.96, 0.04), (0.88, 0.09), (0.8, DECK), (0.0, DECK)), (0, 0, 0), 16)
    body.rotation_euler = (0, 0, math.pi / 16)
    shell = nod.concrete('Platform', [body], root, nod.LIGHT)
    parts = [nod.lathe('Dirt', m['dirt'], ((1.06, 0.0), (1.0, 0.035), (0.6, 0.035)), (0, 0, 0), 16)]
    parts[0].rotation_euler = (0, 0, math.pi / 16)
    for k in range(16):
        a = 2 * math.pi * k / 16
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'Seam{k}', m['nplate'], d * 0.95 + Vector((0, 0, 0.045)), d * 0.8 + Vector((0, 0, DECK + 0.002)), 0.02, 0.012))
    return shell, kit.merge('PlatformTrim', parts)


def dome(m, root):
    """The stepped round dome on the left (concrete) with its trims; origin at its foot."""
    profile = ((0.5, 0.0), (0.48, 0.1), (0.4, 0.13), (0.39, 0.2), (0.3, 0.23), (0.29, 0.29), (0.17, 0.31), (0.0, 0.32))
    body = nod.lathe('DomeBody', m['steel'], profile, DOME, 14)
    shell = nod.concrete('Dome', [body], root, nod.GREY, DOME)
    parts = [cylinder('DomeBand', m['nplate_dark'], 0.405, 0.03, DOME + Vector((0, 0, 0.12)), segments=14, bevel=0),
             cylinder('DomeHatch', m['nplate'], 0.1, 0.03, DOME + Vector((0, 0, 0.325)), segments=12)]
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(box(f'DomeVent{k}', m['dark'], (0.03, 0.12, 0.04), DOME + d * 0.44 + Vector((0, 0, 0.06)), bevel=0.004,
                         rotation=(0, math.radians(-12), a)))
    return shell, kit.merge('DomeTrim', parts, DOME)


def tiers(m, root):
    """The tower's three stepped tiers (concrete, each its own object, origin at its
    foot) and their trims; returns [(tier, trims)]."""
    out = []
    z = DECK
    for i, ((ox, oy), (bx, by), (tx, ty), h) in enumerate(TIERS):
        cx, cy = TOWER.x + ox, TOWER.y + oy
        # sharp: the front corner cut deep, sloped walls
        body = nod.prism(f'Tier{i}Body', m['steel'], nod.chamfered(cx, cy, bx, by, bx * 0.22), nod.chamfered(cx, cy, tx, ty, tx * 0.22), z, z + h, 0.008)
        foot = Vector((cx, cy, z))
        tier = nod.concrete(f'Tier{i}', [body], root, nod.GREY if i != 1 else nod.DARK_GREY, foot)
        parts = [box(f'Tier{i}Slit{k}', m['dark'], (0.1, 0.02, 0.035), Vector((cx - bx * 0.25 + k * 0.14, cy - (by + ty) / 4 - 0.005, z + h * 0.5)),
                     bevel=0.003, rotation=(math.radians(-25), 0, 0)) for k in range(3)]
        parts.append(box(f'Tier{i}Trim', m['remap'] if i == 2 else m['nplate_dark'], (tx * 0.7, ty * 0.7, 0.02), Vector((cx, cy, z + h + 0.01)),
                         bevel=0.004))
        out.append((tier, kit.merge(f'Tier{i}Trim', parts, foot)))
        z += h
    return out, Vector((TOWER.x + TIERS[2][0][0], TOWER.y + TIERS[2][0][1], z + 0.02))


def conduit(m, i, start, control, end):
    """A thick red conduit along a curve, with dark collars at both ends; origin at its start."""
    parts = []
    n = 12
    points = [bezier(start, control, end, k / n) for k in range(n + 1)]
    for k, (a, b) in enumerate(zip(points, points[1:])):
        part = cylinder(f'Conduit{i}_{k}', m['remap'], 0.035, (b - a).length + 0.02, (a + b) / 2, segments=10, bevel=0)
        part.rotation_mode = 'QUATERNION'
        part.rotation_quaternion = (b - a).to_track_quat('Z', 'Y')
        parts.append(part)
    for p, q in ((points[0], points[1]), (points[-1], points[-2])):
        collar = cylinder(f'Collar{i}{p.x:.2f}', m['nplate_dark'], 0.05, 0.08, p, segments=10, bevel=0.006)
        collar.rotation_mode = 'QUATERNION'
        collar.rotation_quaternion = (q - p).to_track_quat('Z', 'Y')
        parts.append(collar)
    for t in (0.33, 0.66):  # clamp rings
        p = bezier(start, control, end, t)
        q = bezier(start, control, end, t + 0.02)
        ring = cylinder(f'Ring{i}{t}', m['nplate'], 0.045, 0.03, p, segments=10, bevel=0)
        ring.rotation_mode = 'QUATERNION'
        ring.rotation_quaternion = (q - p).to_track_quat('Z', 'Y')
        parts.append(ring)
    return kit.merge(f'Conduit{i}', parts, start)


def pod(m, i, at):
    """A red pod sunk into the platform's front edge; origin on the ground."""
    parts = [
        cylinder(f'Pod{i}Ring', m['nplate_dark'], 0.11, 0.06, at + Vector((0, 0, 0.03)), segments=16, bevel=0.008),
        sphere(f'Pod{i}', m['remap'], 0.09, at + Vector((0, 0, 0.05)), 16),
        box(f'Pod{i}Grille', m['dark'], (0.1, 0.02, 0.03), at + Vector((0, -0.085, 0.07)), bevel=0.004),
    ]
    return kit.merge(f'Pod{i}', parts, at)


def sensor(m, top):
    """A small turning sensor on the tower's top; returns (mount, rotor)."""
    mount = kit.merge('SensorMount', [cylinder('SensorFoot', m['nplate_dark'], 0.05, 0.06, top + Vector((0, 0, 0.03)), segments=12)], top)
    head = top + Vector((0, 0, 0.06))
    rotor = kit.merge('Sensor', [
        cylinder('SensorPost', m['nsteel'], 0.015, 0.1, head + Vector((0, 0, 0.05)), segments=8, bevel=0),
        box('SensorBar', m['nsteel_light'], (0.2, 0.03, 0.03), head + Vector((0, 0, 0.1)), bevel=0.006),
        box('SensorTipA', m['remap'], (0.03, 0.04, 0.04), head + Vector((0.1, 0, 0.1)), bevel=0.006),
        box('SensorTipB', m['nplate_dark'], (0.03, 0.04, 0.04), head + Vector((-0.1, 0, 0.1)), bevel=0.006),
    ], head)
    return mount, rotor


def charge(obj, start, control, end, phase):
    """The Idle loop: a glow runs along the conduit from the platform into the tower."""
    frames = {}
    for f in range(0, kit.IDLE_END + 1, 2):
        t = (f / kit.IDLE_END + phase) % 1.0
        frames[f] = bezier(start, control, end, t)
    kit.keys(obj, 'location', frames, 'LINEAR')
    sizes = {}
    for f in range(0, kit.IDLE_END + 1, 2):
        t = (f / kit.IDLE_END + phase) % 1.0
        s = min(1.0, t / 0.08, (1 - t) / 0.08)
        sizes[f] = Vector((max(s, kit.HIDDEN),) * 3)
    kit.keys(obj, 'scale', sizes, 'LINEAR')


def build():
    root = nod.start('NodTechCenter', 'NodTechCenter', BUILD_END)
    m = nod.materials()
    keys = kit.keys

    # ---- the platform rises out of the ground
    base = kit.parent(kit.empty('PlatformGroup'), root)
    shell, trim = platform(m, root)
    kit.parent(shell, base)
    kit.parent(trim, base)
    nod.rise(base, 0, 14, 0.2)

    # ---- the dome and the tower's tiers come up
    dome_obj, dome_trim = dome(m, root)
    kit.parent(dome_obj, base)
    kit.parent(dome_trim, dome_obj)
    keys(dome_obj, 'location', {0: DOME - Vector((0, 0, 0.36)), 10: DOME - Vector((0, 0, 0.36)), 28: DOME + Vector((0, 0, 0.006)), 31: DOME.copy()})
    stack, top = tiers(m, root)
    holder = base
    for i, (tier, tier_trim) in enumerate(stack):
        kit.parent(tier, holder)
        kit.parent(tier_trim, tier)
        rest = tier.location.copy()
        h = TIERS[i][3]
        keys(tier, 'location', {0: rest - Vector((0, 0, h + 0.02)), 14 + 8 * i: rest - Vector((0, 0, h + 0.02)),
                                26 + 8 * i: rest + Vector((0, 0, 0.006)), 29 + 8 * i: rest})
        holder = tier
    mount, rotor = sensor(m, top)
    kit.parent(mount, holder)
    kit.pop(mount, 52, 6)
    kit.parent(rotor, mount)

    # ---- the conduits grow from the platform to the tower
    pipes = []
    for i, (start, control, end) in enumerate(CONDUITS):
        obj = kit.parent(conduit(m, i, start, control, end), base)
        kit.pop(obj, 40 + 4 * i, 10)
        pipes.append(obj)

    # ---- the pods, lights
    lights = []
    for i, at in enumerate(PODS):
        obj = kit.parent(pod(m, i, at), base)
        kit.pop(obj, 48 + 4 * i, 8)
        lights.append((nod.lamp(m, obj, f'PodLamp{i}', at + Vector((0, 0, 0.14)), 'red', 60 + 3 * i), kit.flashes((i * 30, 12))))
    lights.append((nod.lamp(m, holder, 'TowerLamp', top + Vector((-0.1, -0.08, -0.02)), 'amber', 64), kit.flashes((5, 4), (15, 4), (45, 4))))

    idle = [(rotor, lambda o: nod.spin(o, kit.IDLE_END, 2, 1))]
    for i, (start, control, end) in enumerate(CONDUITS):
        glow = kit.merge(f'Charge{i}', [sphere(f'ChargeCore{i}', m['ember'], 0.04, start, 10),
                                        sphere(f'ChargeHalo{i}', m['glow_red'], 0.075, start, 10)], start)
        kit.parent(glow, pipes[i])  # keyed in the conduit's space: its origin is the start
        idle.append((glow, lambda o, c=control - start, e=end - start, p=i / 3: charge(o, Vector((0, 0, 0)), c, e, p)))
    nod.clips(lights, idle)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, ortho=2.9, target=(0.05, 0, 0.35))
