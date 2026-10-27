"""
Tiberian Fallout – Nod radar (NARADR), after Tiberian Sun.

A stepped grey concrete hill (foundation 2 × 2 cells): a concave skirt that runs out
into the corners of the foundation, three terraces above it, the flat top ringed by a
thick red collar. Out of the collar rises a dark pedestal carrying the big, pale,
nearly white radar dish, standing steep (20° up), which turns all the time. A red
signal block with a dark doorway sits on the slope at the front left, two thin masts
with cross spars stand on the terraces at the left and the right.

Materials (see nodstructure.py): Nod_* baked concrete (also the dish's pale, stained
face), NodPlate*/NodSteel dark plate and steel (extra nodColour), Remap the house
colour, Lamp* emissive, Glow* additive.

Nodes: NodRadar (root) – MoundGroup (Mound, MoundTrim, Collar, Entrance, Mast0/1,
Pedestal – Head – Dish).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the hill rises out of the ground, the red block and the
             masts come up out of it, the pedestal rises out of the collar, the dish
             unfolds, the lights come on
    Idle     loop, 4 s: the dish turns once round, nodding a little (the original's
             NARADR_A); the mast lamps and the signal lamp blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NARADR.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); seen in the game, (-0.5, 0.5) is the top one.
"""
import math
import os
import sys

from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nod  # noqa: E402

BUILD_END = 72
IDLE_END = 120

SEGMENTS = 48
TOP = 0.51
# the hill: (radius, height) from its foot up – a concave skirt, three terraces
HILL = ((0.98, 0.0), (0.88, 0.04), (0.78, 0.1), (0.71, 0.17), (0.67, 0.23), (0.585, 0.245), (0.565, 0.32), (0.49, 0.335),
        (0.47, 0.41), (0.41, 0.42), (0.395, TOP), (0.0, TOP))
COLLAR = 0.33                     # outer radius of the red collar
HEAD = Vector((0, 0, 0.78))       # the dish's turning head (on the pedestal)
PIVOT = HEAD + Vector((0, 0, 0.32))
DISH = 0.47                       # the dish's radius
TILT = math.radians(70)           # the dish's face 20° above the horizon
ENTRANCE = Vector((-0.42, -0.5, 0))
MASTS = (Vector((-0.6, 0.12, 0)), Vector((0.16, 0.6, 0)))
HILL_CONCRETE = '#7c7d80'
DISH_FACE = '#f2ede2'

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def spread(a, r):
    """How far the hill's outline reaches in direction `a` at the nominal radius `r`:
    round at the top, running out into the foundation's corners at the foot, a little
    uneven (the original's hill is no lathe)."""
    n = 3.2
    square = 1 / (abs(math.cos(a)) ** n + abs(math.sin(a)) ** n) ** (1 / n)
    t = max(0.0, min(1.0, (r - 0.55) / 0.43))
    bumps = 1 + 0.035 * math.sin(3 * a + 0.7) + 0.025 * math.sin(5 * a + 2.1)
    return 1 + (square * 0.94 * bumps - 1) * t


def hill_height(x, y):
    """Height of the hill's surface at (x, y)."""
    a = math.atan2(y, x)
    d = math.hypot(x, y)
    for (r0, z0), (r1, z1) in zip(HILL, HILL[1:]):
        R0, R1 = r0 * spread(a, r0), r1 * spread(a, r1)
        if R1 <= d <= R0 and R0 != R1:
            return z0 + (z1 - z0) * (R0 - d) / (R0 - R1)
    return TOP if d < 0.4 else 0.0


def hill_mesh(name, mat):
    """The hill: the profile swept round, each ring pushed out by spread()."""
    def build(bm):
        rings = []
        for r, z in HILL[:-1]:
            rings.append([bm.verts.new((r * spread(a, r) * math.cos(a), r * spread(a, r) * math.sin(a), z))
                          for a in (2 * math.pi * i / SEGMENTS for i in range(SEGMENTS))])
        for lower, upper in zip(rings, rings[1:]):
            for i in range(SEGMENTS):
                j = (i + 1) % SEGMENTS
                bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
        centre = bm.verts.new((0, 0, TOP))
        last = rings[-1]
        for i in range(SEGMENTS):
            bm.faces.new((last[i], last[(i + 1) % SEGMENTS], centre))
        bm.faces.new(rings[0][::-1])

    obj = kit.finish(kit.mesh_object(name, build), mat, 0.0)
    obj.data.set_sharp_from_angle(angle=math.radians(25))   # smooth round, sharp terrace edges
    return obj


def mound(m, root):
    """The concrete hill (baked) and its trims: dirt at the foot, the dark well under
    the collar, stains on the terraces."""
    shell = nod.concrete('Mound', [hill_mesh('MoundBody', m['steel'])], root, HILL_CONCRETE)
    parts = [
        cylinder('Well', m['dark'], COLLAR - 0.08, 0.008, (0, 0, TOP + 0.003), segments=32, bevel=0),
    ]
    # dirt round the foot (a flat band following the outline)
    for i in range(SEGMENTS):
        a0, a1 = 2 * math.pi * i / SEGMENTS, 2 * math.pi * (i + 1) / SEGMENTS
        p0 = Vector((math.cos(a0), math.sin(a0), 0)) * 0.98 * spread(a0, 0.98)
        p1 = Vector((math.cos(a1), math.sin(a1), 0)) * 0.98 * spread(a1, 0.98)
        parts.append(kit.hexahedron(f'Dirt{i}', m['dirt'], (
            p0 * 0.95, p0 * 1.05, p1 * 1.05, p1 * 0.95,
            p0 * 0.95 + Vector((0, 0, 0.01)), p0 * 1.05 + Vector((0, 0, 0.003)), p1 * 1.05 + Vector((0, 0, 0.003)),
            p1 * 0.95 + Vector((0, 0, 0.01))), bevel=0))
    return shell, kit.merge('MoundTrim', parts)


def collar(m):
    """The thick red collar round the top, on a dark ring; origin on the top."""
    base = Vector((0, 0, TOP))
    parts = [
        cylinder('CollarRing', m['nplate_dark'], COLLAR + 0.03, 0.03, base + Vector((0, 0, 0.015)), segments=32, bevel=0.006),
        band('CollarRed', m['remap'], base, ((COLLAR - 0.1, 0.03), (COLLAR, 0.03), (COLLAR + 0.01, 0.06), (COLLAR - 0.01, 0.1),
                                             (COLLAR - 0.1, 0.1), (COLLAR - 0.11, 0.065))),
        band('CollarInner', m['nplate_dark'], base, ((COLLAR - 0.16, 0.0), (COLLAR - 0.1, 0.0), (COLLAR - 0.1, 0.095), (COLLAR - 0.16, 0.08))),
    ]
    return kit.merge('Collar', parts, base)


def band(name, mat, base, profile, segments=32):
    """A ring: the closed outline `profile` (radius, height) swept round `base`."""
    loop = list(profile) + [profile[0]]
    sections = [[base + Vector((math.cos(a) * r, math.sin(a) * r, z)) for r, z in loop]
                for a in (2 * math.pi * k / segments for k in range(segments + 1))]
    obj = nod.loft(name, sections, lambda i, k: mat)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def entrance(m):
    """The red signal block on the slope at the front left, its dark doorway under it;
    origin on the ground."""
    p = ENTRANCE
    z = hill_height(p.x, p.y)
    rot = (0, 0, math.radians(-20))
    parts = [
        nod.prism('EntranceBody', m['nplate'], nod.chamfered(0, 0, 0.26, 0.24, 0.04), nod.chamfered(0, 0.02, 0.22, 0.18, 0.03),
                  -0.15, z + 0.05, 0.008),
        box('EntranceDoor', m['dark'], (0.13, 0.02, 0.1), Vector((0, -0.12, z - 0.0)), bevel=0),
        box('EntranceLintel', m['nplate_dark'], (0.18, 0.04, 0.025), Vector((0, -0.115, z + 0.06)), bevel=0.004),
        box('SignalBlock', m['remap'], (0.2, 0.17, 0.12), Vector((0, 0.02, z + 0.11)), bevel=0.025),
        box('SignalTop', m['nplate_dark'], (0.12, 0.1, 0.03), Vector((0, 0.02, z + 0.18)), bevel=0.008),
    ]
    for part in parts:
        part.location = p + Matrix.Rotation(rot[2], 3, 'Z') @ Vector(part.location)
        part.rotation_euler.z += rot[2]
    return kit.merge('Entrance', parts, p)


def mast(m, i, foot):
    """A thin mast with cross spars; origin at its foot. Returns (mast, its top)."""
    foot = foot + Vector((0, 0, hill_height(foot.x, foot.y)))
    h = 0.6
    parts = [
        box(f'Mast{i}Foot', m['nplate_dark'], (0.07, 0.07, 0.08), foot + Vector((0, 0, 0.0)), bevel=0.006),
        cylinder(f'Mast{i}', m['nsteel'], 0.012, h, foot + Vector((0, 0, h / 2)), segments=8, bevel=0),
        beam(f'Mast{i}Spar0', m['nsteel'], foot + Vector((-0.06, 0, h * 0.75)), foot + Vector((0.06, 0, h * 0.75)), 0.01),
        beam(f'Mast{i}Spar1', m['nsteel'], foot + Vector((0, -0.045, h * 0.88)), foot + Vector((0, 0.045, h * 0.88)), 0.01),
    ]
    return kit.merge(f'Mast{i}', parts, foot), foot + Vector((0, 0, h))


def pedestal(m):
    """The dark pedestal out of the collar; origin deep in the hill."""
    base = Vector((0, 0, TOP - 0.36))
    parts = [
        cylinder('Column', m['nplate_dark'], 0.11, HEAD.z - base.z, base + Vector((0, 0, (HEAD.z - base.z) / 2)), segments=20),
        cylinder('ColumnBand', m['nplate'], 0.125, 0.05, Vector((0, 0, TOP + 0.16)), segments=20, bevel=0.006),
        cylinder('Bearing', m['nsteel'], 0.13, 0.05, HEAD - Vector((0, 0, 0.025)), segments=20),
    ]
    return kit.merge('Pedestal', parts, base)


def dish(m, root):
    """The turning head and the dish on it, facing -Y at rest; returns (head, dish)."""
    head = kit.merge('Head', [
        box('HeadBlock', m['nplate'], (0.2, 0.18, 0.12), HEAD + Vector((0, 0.03, 0.06)), bevel=0.02),
        box('HeadStripe', m['remap'], (0.205, 0.185, 0.025), HEAD + Vector((0, 0.03, 0.08)), bevel=0),
        *[box(f'Yoke{s}', m['nplate_dark'], (0.035, 0.08, 0.24), HEAD + Vector((s * 0.11, 0.035, 0.22)), bevel=0.008) for s in (-1, 1)],
        cylinder('Axle', m['nsteel'], 0.025, 0.26, PIVOT + Vector((0, 0.03, 0)), rotation=(0, math.pi / 2, 0), segments=10, bevel=0),
        box('Counterweight', m['nplate_dark'], (0.14, 0.1, 0.1), HEAD + Vector((0, 0.16, 0.08)), bevel=0.015),
    ], HEAD)
    # the bowl, opening up +Z before it is tipped to face -Y
    face = nod.lathe('BowlFace', m['steel'], ((0.0, 0.05), (0.14, 0.062), (0.28, 0.1), (0.4, 0.16), (DISH, 0.19), (DISH - 0.012, 0.19),
                                              (0.0, 0.065)), (0, 0, 0), 40)
    face = nod.concrete('DishFace', [face], root, DISH_FACE)
    parts = [
        nod.lathe('BowlBack', m['nsteel'], ((0.0, 0.035), (0.16, 0.045), (0.3, 0.085), (DISH - 0.02, 0.15), (DISH - 0.03, 0.155),
                                            (0.0, 0.05)), (0, 0, 0), 40),
        cylinder('BowlHub', m['nplate_dark'], 0.09, 0.08, (0, 0, 0.02), segments=16, bevel=0.008),
        cylinder('BowlStrut', m['nplate_dark'], 0.025, 0.36, (0, 0, 0.24), segments=10, bevel=0),
        cylinder('FeedHorn', m['nplate_dark'], 0.05, 0.1, (0, 0, 0.44), segments=12, bevel=0.006, radius2=0.03),
        cylinder('FeedTip', m['remap'], 0.022, 0.03, (0, 0, 0.5), segments=10, bevel=0),
    ]
    for k in range(3):
        a = 0.4 + 2 * math.pi * k / 3
        parts.append(beam(f'FeedArm{k}', m['nsteel'], Vector((math.cos(a) * (DISH - 0.05), math.sin(a) * (DISH - 0.05), 0.18)),
                          Vector((0, 0, 0.42)), 0.012))
    back = kit.merge('DishParts', parts)
    turn = Matrix.Rotation(TILT, 4, 'X')
    for obj in (face, back):
        obj.data.transform(Matrix.Translation(-obj.location))
        obj.data.transform(turn @ Matrix.Translation(obj.location))
        obj.location = PIVOT
    kit.parent(back, face)
    face.name = 'Dish'
    return head, face


def build():
    root = nod.start('NodRadar', 'NodRadar', BUILD_END, IDLE_END)
    m = nod.materials()
    keys = kit.keys

    # ---- the hill rises out of the ground
    group = kit.parent(kit.empty('MoundGroup'), root)
    shell, trim = mound(m, root)
    kit.parent(shell, group)
    kit.parent(trim, group)
    nod.rise(group, 0, 22, 0.6)
    ring = kit.parent(collar(m), group)
    nod.rise(ring, 16, 10, 0.14)
    door = kit.parent(entrance(m), group)
    nod.rise(door, 20, 10, 0.3)

    # ---- the pedestal rises out of the collar, the dish unfolds on it
    column = kit.parent(pedestal(m), group)
    keys(column, 'location', {0: column.location - Vector((0, 0, 0.62)), 24: column.location - Vector((0, 0, 0.62)),
                              42: column.location + Vector((0, 0, 0.01)), 46: column.location.copy()})
    head, bowl = dish(m, root)
    kit.parent(head, column)
    kit.parent(bowl, head)
    kit.pop(bowl, 44, 12)
    head.rotation_euler.z = math.radians(45)   # at rest it faces the viewer (lower right of the screen)

    # ---- masts come up out of the hill
    lights = []
    for i, foot in enumerate(MASTS):
        pole, top = mast(m, i, foot)
        kit.parent(pole, group)
        nod.rise(pole, 36 + 6 * i, 14, 0.72)
        lights.append((nod.lamp(m, pole, f'MastLamp{i}', top, 'red', 58 + 3 * i), kit.flashes((i * 60, 12), (30 + i * 60, 6))))
    z = hill_height(ENTRANCE.x, ENTRANCE.y)
    at = ENTRANCE + Vector((0, 0, z + 0.195))
    lights.append((nod.lamp(m, door, 'SignalLamp', at, 'red', 64), kit.flashes((10, 20), (70, 20))))

    def turn(obj):
        rest = obj.rotation_euler.copy()
        frames = {}
        for f in range(0, IDLE_END + 1, 5):
            frames[f] = Vector((0.05 * math.sin(4 * math.pi * f / IDLE_END), 0, rest.z + 2 * math.pi * f / IDLE_END))
        kit.keys(obj, 'rotation_euler', frames, 'LINEAR')
        obj.rotation_euler = rest

    nod.clips(lights, [(head, turn)])
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, 'NARADR', {'Build': [BUILD_END // 3, 2 * BUILD_END // 3, BUILD_END], 'Idle': [0, 30, 60, 90]},
             ortho=3.0, target=(0.0, 0, 0.55))
