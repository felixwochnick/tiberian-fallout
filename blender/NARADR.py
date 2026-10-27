"""
Tiberian Fallout – Nod radar (NARADR), after Tiberian Sun.

A low faceted concrete mound (foundation 2 × 2 cells) flaring out to a wide, dirty
skirt, stepped twice towards its flat top. Out of the dark well in the top rises a
pedestal with a red collar carrying the big pale radar dish, which turns all the
time. In the front a small entrance block with a red signal light; two thin masts
with cross spars stand at the left and the right edge.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
and steel (extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the mound rises out of the ground, the steps come up,
             the pedestal rises out of the well, the dish unfolds, the masts grow,
             the lights come on
    Idle     loop, 4 s: the dish turns once round, nodding a little; the mast lamps
             and the signal light blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NARADR.py [-- --preview 0,30,72 <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'NARADR.glb')
BLEND = os.path.join(HERE, 'NARADR.blend')
BUILD_END = 72
IDLE_END = 120

FACETS = 12
TOP = 0.56
# the mound: (radius, height) from its foot up
MOUND = ((0.97, 0.0), (0.95, 0.05), (0.78, 0.17), (0.62, 0.3), (0.56, 0.38), (0.56, 0.42), (0.47, 0.44), (0.45, 0.5),
         (0.39, 0.5), (0.37, TOP), (0.3, TOP))
WELL = 0.24
HEAD = Vector((0, 0, 0.9))       # the dish's turning head
ENTRANCE = Vector((-0.28, -0.7, 0))
MASTS = (Vector((-0.66, -0.36, 0)), Vector((0.42, 0.62, 0)))

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def mound_height(r):
    for (r0, z0), (r1, z1) in zip(MOUND, MOUND[1:]):
        if min(r0, r1) <= r <= max(r0, r1) and r0 != r1:
            return z0 + (z1 - z0) * (r - r0) / (r1 - r0)
    return 0.0


def mound(m, root):
    """The faceted concrete mound (rotated so a facet faces the front) and its trims."""
    body = nod.lathe('MoundBody', m['steel'], MOUND, (0, 0, 0), FACETS)
    body.rotation_euler = (0, 0, math.pi / FACETS)
    shell = nod.concrete('Mound', [body], root, nod.GREY)
    parts = [
        nod.lathe('Dirt', m['dirt'], ((1.06, 0.0), (1.0, 0.03), (0.6, 0.03)), (0, 0, 0), FACETS),
        cylinder('Well', m['dark'], WELL, 0.01, (0, 0, TOP + 0.002), segments=24, bevel=0),
        cylinder('WellRim', m['nplate_dark'], WELL + 0.03, 0.02, (0, 0, TOP + 0.004), segments=24, bevel=0),
    ]
    parts[0].rotation_euler = (0, 0, math.pi / FACETS)
    # ribs down the facet edges of the skirt
    for k in range(FACETS):
        a = 2 * math.pi * k / FACETS
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'Rib{k}', m['nplate'], d * 0.94 + Vector((0, 0, 0.06)), d * 0.63 + Vector((0, 0, 0.3)), 0.03, 0.025))
    return shell, kit.merge('MoundTrim', parts)


def entrance(m):
    """The entrance block in front, with a red signal housing; origin on the ground."""
    p = ENTRANCE
    parts = [
        nod.prism('EntranceBody', m['nplate'], nod.chamfered(p.x, p.y + 0.06, 0.3, 0.34, 0.05), nod.chamfered(p.x, p.y + 0.1, 0.24, 0.24, 0.04),
                  0, 0.24, 0.01),
        box('EntranceDoor', m['dark'], (0.15, 0.02, 0.16), p + Vector((0, -0.105, 0.08)), bevel=0),
        box('EntranceLintel', m['nplate_dark'], (0.22, 0.05, 0.03), p + Vector((0, -0.1, 0.175)), bevel=0.005),
        box('SignalBox', m['remap'], (0.14, 0.12, 0.12), p + Vector((0.2, 0.04, 0.27)), bevel=0.02),
        box('SignalFoot', m['nplate_dark'], (0.1, 0.1, 0.14), p + Vector((0.2, 0.04, 0.14)), bevel=0.01),
    ]
    return kit.merge('Entrance', parts, p)


def mast(m, i, foot):
    """A thin mast with cross spars; origin at its foot. Returns (mast, its top)."""
    foot = foot + Vector((0, 0, mound_height(foot.length) - 0.02))
    h = 0.62
    parts = [
        box(f'Mast{i}Foot', m['nplate_dark'], (0.07, 0.07, 0.05), foot + Vector((0, 0, 0.025)), bevel=0.006),
        cylinder(f'Mast{i}', m['nsteel'], 0.012, h, foot + Vector((0, 0, h / 2)), segments=8, bevel=0),
        beam(f'Mast{i}Spar0', m['nsteel'], foot + Vector((-0.06, 0, h * 0.72)), foot + Vector((0.06, 0, h * 0.72)), 0.008),
        beam(f'Mast{i}Spar1', m['nsteel'], foot + Vector((0, -0.045, h * 0.85)), foot + Vector((0, 0.045, h * 0.85)), 0.008),
    ]
    return kit.merge(f'Mast{i}', parts, foot), foot + Vector((0, 0, h))


def pedestal(m):
    """The pedestal out of the well with its red collar; origin at the well's bottom."""
    base = Vector((0, 0, TOP - 0.3))
    parts = [
        cylinder('Column', m['nplate_dark'], 0.1, HEAD.z - base.z, base + Vector((0, 0, (HEAD.z - base.z) / 2)), segments=16),
        cylinder('Collar', m['remap'], 0.17, 0.08, Vector((0, 0, TOP + 0.08)), segments=16, bevel=0.01, radius2=0.13),
        cylinder('CollarRing', m['nplate'], 0.2, 0.03, Vector((0, 0, TOP + 0.03)), segments=16, bevel=0.006),
        cylinder('Bearing', m['nsteel'], 0.12, 0.05, HEAD - Vector((0, 0, 0.03)), segments=16),
    ]
    return kit.merge('Pedestal', parts, base)


def dish(m):
    """The turning head with the dish, tilted up, facing -Y; returns (head, dish)."""
    head = kit.merge('Head', [
        box('HeadBlock', m['nplate'], (0.16, 0.14, 0.1), HEAD + Vector((0, 0.02, 0.05)), bevel=0.015),
        box('HeadStripe', m['remap'], (0.165, 0.145, 0.02), HEAD + Vector((0, 0.02, 0.06)), bevel=0),
        *[box(f'Yoke{s}', m['nplate_dark'], (0.03, 0.06, 0.14), HEAD + Vector((s * 0.09, 0, 0.13)), bevel=0.006) for s in (-1, 1)],
        box('Counterweight', m['nplate_dark'], (0.12, 0.1, 0.08), HEAD + Vector((0, 0.12, 0.08)), bevel=0.012),
    ], HEAD)
    pivot = HEAD + Vector((0, 0, 0.17))
    # the bowl: a shallow lathe opening towards -Y
    bowl = nod.lathe('Bowl', m['nsteel_light'], ((0.0, 0.0), (0.12, 0.012), (0.24, 0.045), (0.33, 0.1), (0.32, 0.105), (0.0, 0.03)),
                     (0, 0, 0), 28)
    back = nod.lathe('BowlBack', m['nplate'], ((0.0, -0.012), (0.16, 0.0), (0.24, 0.03)), (0, 0, 0), 28)
    ring = [Vector((math.cos(a) * 0.328, math.sin(a) * 0.328, 0.104)) for a in (2 * math.pi * k / 28 for k in range(29))]
    rim = [beam(f'BowlRim{k}', m['remap'], a, b, 0.022, 0.018) for k, (a, b) in enumerate(zip(ring, ring[1:]))]
    feed = [beam(f'FeedArm{k}', m['nsteel'], Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 0.1)), Vector((0, 0, 0.26)), 0.01)
            for k, a in enumerate((0.3, 0.3 + 2 * math.pi / 3, 0.3 + 4 * math.pi / 3))]
    horn = cylinder('FeedHorn', m['nplate_dark'], 0.03, 0.06, (0, 0, 0.27), segments=10)
    bowl_obj = kit.merge('Dish', [bowl, back, *rim, *feed, horn])
    bowl_obj.data.transform(Matrix.Rotation(math.radians(62), 4, 'X'))  # face -Y, tilted up
    bowl_obj.location = pivot + Vector((0, -0.02, 0))
    return head, bowl_obj


def build():
    root = nod.start('NodRadar', 'NodRadar', BUILD_END, IDLE_END)
    m = nod.materials()
    keys = kit.keys

    # ---- the mound rises out of the ground
    group = kit.parent(kit.empty('MoundGroup'), root)
    shell, trim = mound(m, root)
    kit.parent(shell, group)
    kit.parent(trim, group)
    nod.rise(group, 0, 22, 0.6)
    door = kit.parent(entrance(m), group)
    kit.pop(door, 22, 8)

    # ---- the pedestal rises out of the well, the dish unfolds on it
    column = kit.parent(pedestal(m), group)
    keys(column, 'location', {0: column.location - Vector((0, 0, 0.62)), 24: column.location - Vector((0, 0, 0.62)),
                              44: column.location + Vector((0, 0, 0.01)), 48: column.location.copy()})
    head, bowl = dish(m)
    kit.parent(head, column)
    kit.parent(bowl, head)
    kit.pop(bowl, 46, 10)

    # ---- masts
    lights = []
    for i, foot in enumerate(MASTS):
        pole, top = mast(m, i, foot)
        kit.parent(pole, group)
        kit.grow(pole, 40 + 6 * i, 12, 2)
        lights.append((nod.lamp(m, pole, f'MastLamp{i}', top, 'red', 60 + 3 * i), kit.flashes((i * 60, 12), (30 + i * 60, 6))))
    at = ENTRANCE + Vector((0.2, -0.03, 0.335))
    lights.append((nod.lamp(m, door, 'SignalLamp', at, 'red', 66), kit.flashes((10, 20), (70, 20))))

    def turn(obj):
        rest = obj.rotation_euler.copy()
        frames = {}
        for f in range(0, IDLE_END + 1, 5):
            frames[f] = Vector((0.06 * math.sin(4 * math.pi * f / IDLE_END), 0, rest.z + 2 * math.pi * f / IDLE_END))
        kit.keys(obj, 'rotation_euler', frames, 'LINEAR')
        obj.rotation_euler = rest

    nod.clips(lights, [(head, turn)])
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, ortho=2.9, target=(0.05, 0, 0.45))
