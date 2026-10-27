"""
Tiberian Fallout – Nod laser fence post (NAPOST), after Tiberian Sun / Firestorm.

A post on one cell, like the original's: a low octagonal footing of dark concrete with
a red (house colour) rim on a sandy ground plate, on it a dark ribbed dome and from its
middle a steel column. Low on the column sits the emitter: a ring of blue lenses
between a cup and a collar, from where the laser fence is spanned to the next post.
Above it the column carries a big grey head with a dark slot and two thin prongs;
four thin rods with short crossbars stand round it on the footing's corners.

Nodes:
    Post       the column, head and emitter housing (rises in Build)
    Emitter    the blue lens ring at the height of the fence (its glow pulses in Idle);
               the game spans the fence between the Emitters of two posts
    Rod0…3     the four rods round the column (grow in Build)
    Lamp…      a small red lamp on a prong (housing pops in Build, the light blinks
               in Idle)
Animations (glTF clips)
    Build    one-shot, 1.6 s: the footing spreads, the dome rises, the column comes up
             out of it, the rods grow, the emitter lights up
    Idle     loop, 2 s: the emitter's glow pulses (the original's NAPOST_A), the lamp
             on the prong blinks

Run headless:

    blender -b --factory-startup --python blender/NAPOST.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). Origin in the
middle of the cell on the ground.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
BUILD_END = 48

FOOT = 0.06           # top of the footing
HUMP = 0.2            # top of the dome
EMITTER = 0.27        # the height of the fence
COLUMN = 0.05         # the column's radius
HEAD = (0.34, 0.47)   # the head's bottom and top
MAST_TOP = 0.66
RODS = [(x, y) for x, y in ((-0.25, -0.25), (0.25, -0.25), (0.25, 0.25), (-0.25, 0.25))]
ROD_TOP = (0.56, 0.6, 0.64, 0.68)


def footing(m, root):
    """The octagonal footing (concrete), its red rim and the sandy plate; origin on the ground."""
    outline = nb.chamfered(0, 0, 0.84, 0.84, 0.22)
    top = nb.chamfered(0, 0, 0.74, 0.74, 0.2)
    body = nb.concrete('Footing', [nb.prism('FootingBody', m['steel'], outline, top, 0, FOOT)], root, nb.DARK_GREY)
    plate = [(x * 1.1, y * 1.1) for x, y in nb.chamfered(0, 0, 0.88, 0.88, 0.3)]
    parts = [nb.prism('Plate', m['dirt'], plate, plate, 0, 0.008, bevel=0)]
    # the red rim: a band round the footing's sloped side
    rim_lo = nb.chamfered(0, 0, 0.82, 0.82, 0.215)
    rim_hi = nb.chamfered(0, 0, 0.8, 0.8, 0.21)
    parts.append(nb.prism('Rim', m['remap'], rim_lo, rim_hi, 0.012, 0.034, bevel=0.002))
    # dark spikes jutting from the footing's corners
    for k in range(4):
        a = math.radians(45 + 90 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(nb.spike(f'Spike{k}', m['nplate_dark'], d * 0.32 + Vector((0, 0, 0.03)), d, 0.16, 0.08, 0.03, droop=0.03))
    return body, kit.merge('FootingDetails', parts)


def hump(m):
    """The armoured dome on the footing; origin on the footing."""
    base = Vector((0, 0, FOOT))
    profile = [(0.33, 0.0), (0.33, 0.02), (0.3, 0.07), (0.24, 0.115), (0.16, 0.135), (0.08, HUMP - FOOT)]
    parts = [nb.lathe('HumpBody', m['nplate'], profile, base, 24, bevel=0)]
    parts.append(cylinder('HumpRing', m['remap'], 0.335, 0.022, base + Vector((0, 0, 0.012)), segments=24, bevel=0.002))
    for k in range(8):   # dark ribs over the dome
        a = 2 * math.pi * (k + 0.5) / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'HumpRib{k}', m['nplate_dark'], base + d * 0.315 + Vector((0, 0, 0.03)), base + d * 0.17 + Vector((0, 0, 0.13)), 0.02, 0.016))
    for x, y in RODS:   # the rods' sockets
        parts.append(cylinder(f'Socket{x}{y}', m['nplate_dark'], 0.03, 0.05, (x, y, FOOT + 0.025), segments=10, bevel=0.004))
    return kit.merge('Hump', parts, base)


def post(m):
    """The column, the emitter housing and the mast; origin on the hump."""
    base = Vector((0, 0, HUMP - 0.01))
    lo, hi = HEAD
    parts = [
        cylinder('ColumnFoot', m['nplate_dark'], 0.09, 0.05, base + Vector((0, 0, 0.025)), segments=16, bevel=0.006),
        cylinder('Column', m['nsteel'], COLUMN, lo - HUMP + 0.02, (0, 0, (HUMP + lo) / 2), segments=16, bevel=0.003),
        # the emitter's housing: a cup below, a collar above the lenses
        cylinder('Cup', m['nplate'], 0.07, 0.03, (0, 0, EMITTER - 0.035), segments=20, bevel=0.005, radius2=0.08),
        cylinder('Collar', m['nplate'], 0.08, 0.03, (0, 0, EMITTER + 0.035), segments=20, bevel=0.005, radius2=0.068),
        cylinder('LensCore', m['dark'], 0.058, 0.045, (0, 0, EMITTER), segments=20, bevel=0),
        # the big head: a grey drum with a dark slot to the front and a red band
        cylinder('Head', m['nsteel_light'], 0.085, hi - lo, (0, 0, (lo + hi) / 2), segments=20, bevel=0.008),
        cylinder('HeadBase', m['nplate_dark'], 0.07, 0.03, (0, 0, lo + 0.005), segments=20, bevel=0.004),
        cylinder('HeadBand', m['remap'], 0.088, 0.018, (0, 0, lo + 0.03), segments=20, bevel=0.002),
        box('HeadSlot', m['dark'], (0.06, 0.02, 0.07), (0, -0.078, hi - 0.05), bevel=0.004),
        cylinder('HeadCap', m['nplate_dark'], 0.07, 0.016, (0, 0, hi + 0.008), segments=20, bevel=0.003),
    ]
    for k, z in enumerate((HUMP + 0.03, HUMP + 0.07, lo - 0.02)):     # ribs round the column
        if abs(z - EMITTER) > 0.06:
            parts.append(cylinder(f'ColRib{k}', m['nplate_dark'], COLUMN + 0.01, 0.014, (0, 0, z), segments=16, bevel=0.002))
    for k, x in enumerate((-0.035, 0.035)):                          # the two prongs on the head
        parts.append(cylinder(f'Prong{k}', m['nsteel'], 0.011, MAST_TOP - hi, (x, 0, (MAST_TOP + hi) / 2), segments=8, bevel=0))
        for j, z in enumerate((hi + 0.05, hi + 0.1)):
            parts.append(cylinder(f'Insulator{k}{j}', m['nsteel_light'], 0.02, 0.008, (x, 0, z), segments=10, bevel=0))
    return kit.merge('Post', parts, base)


def lenses(m):
    """The ring of blue lenses (lit); origin at the emitter's centre."""
    centre = Vector((0, 0, EMITTER))
    parts = []
    for k in range(8):
        a = 2 * math.pi * k / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(box(f'Lens{k}', m['lamp_pulse'], (0.012, 0.03, 0.03), centre + d * 0.064, bevel=0.003, rotation=(0, 0, a)))
    return kit.merge('Lenses', parts, centre)


def rod(m, k, x, y, top):
    """A thin ribbed rod with a pointed tip; origin at its foot."""
    foot = Vector((x, y, FOOT + 0.04))
    parts = [cylinder(f'Rod{k}Shaft', m['nsteel'], 0.015, top - foot.z, (x, y, (top + foot.z) / 2), segments=8, bevel=0),
             cylinder(f'Rod{k}Tip', m['nsteel_light'], 0.012, 0.05, (x, y, top + 0.025), segments=8, bevel=0, radius2=0.0)]
    d = Vector((x, y, 0)).normalized()
    side = Vector((-d.y, d.x, 0))
    for j in range(int((top - foot.z - 0.04) / 0.07)):   # short crossbars (the original's fishbone rods)
        z = foot.z + 0.07 + 0.07 * j
        w = 0.05 if j % 2 else 0.038
        across = side if j % 2 else d   # crossing each other, seen from every side
        parts.append(beam(f'Rod{k}Bar{j}', m['nplate_dark'], Vector((x, y, z)) - across * w, Vector((x, y, z)) + across * w, 0.016, 0.016))
    return kit.merge(f'Rod{k}', parts, foot)


def build():
    root = nb.start('NodLaserPost', 'NodLaserPost', BUILD_END)
    m = nb.materials()
    keys = kit.keys

    body, details = footing(m, root)
    base = kit.parent(kit.empty('Base'), root)
    kit.parent(body, base)
    kit.parent(details, body)
    kit.keys(base, 'scale', {0: Vector((0.05, 0.05, 1)), 10: Vector((1.04, 1.04, 1)), 13: Vector((1, 1, 1))})
    hump_obj = kit.parent(hump(m), root)
    nb.rise(hump_obj, 6, 10, HUMP)

    # the column rises out of the hump (translation only: the emitter and the lamp ride on it)
    column = kit.parent(post(m), root)
    nb.rise(column, 14, 16, MAST_TOP)
    emitter = kit.parent(kit.empty('Emitter', (0, 0, EMITTER)), column)
    lens = kit.parent(lenses(m), emitter)
    glow = kit.parent(kit.merge('EmitterGlow', [cylinder('EmitterHalo', m['glow_pulse'], 0.09, 0.035, (0, 0, EMITTER), segments=24, bevel=0)], (0, 0, EMITTER)), column)
    kit.pop(lens, 34, 6)
    for k, ((x, y), top) in enumerate(zip(RODS, ROD_TOP)):
        r = kit.parent(rod(m, k, x, y, top), root)
        kit.grow(r, 26 + 3 * k, 10, 2)
    light = nb.lamp(m, column, 'MastLamp', (0.035, 0, MAST_TOP), 'red', 40)

    def throb(obj):
        frames = {}
        for f in range(0, kit.IDLE_END + 1, 3):
            t = (math.sin(2 * math.pi * 3 * f / kit.IDLE_END) + 1) / 2
            frames[f] = Vector((0.85 + 0.35 * t, 0.85 + 0.35 * t, 0.6 + 0.6 * t))
        frames[kit.IDLE_END] = frames[0]
        kit.keys(obj, 'scale', frames, 'LINEAR')

    nb.clips([(light, kit.flashes((0, 8), (30, 8)))], [(glow, throb)])
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAPOST', {'Build': [12, 26, 40], 'Idle': [0, 10]}, ortho=1.3, target=(0, 0, 0.32))
