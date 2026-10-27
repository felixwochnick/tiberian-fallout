"""
Tiberian Fallout – Nod gate (NAGATE_A), after Tiberian Sun.

A gate in the Nod wall, three cells long along x: two grey concrete piers at the ends
whose tops slope down towards the gate, between them the gate leaf – a dark armoured
slab with vertical ribs, framed in red (house colour) with the Nod emblem on both
faces – on a concrete sill flanked by yellow and black hazard stripes. Opening, the
leaf sinks into the ground.

Nodes:
    Door     the gate leaf (sinks in Open)
Animations (glTF clips)
    Build    one-shot, 1.8 s: the sill and stripes spread, the piers rise, the leaf
             comes up between them, the lamps appear
    Idle     loop, 2 s: the red lamps on the piers glow, now and then they blink
    Open     one-shot, 1 s: the amber lamps flash, the leaf sinks into the ground
             (played backwards: it shuts)

Run headless:

    blender -b --factory-startup --python blender/NAGATE_A.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells are
centred at x = -1, 0, 1; origin in the middle on the ground.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodbuilding as nb  # noqa: E402

box, beam = kit.box, kit.beam
HIDDEN = kit.HIDDEN

INNER, OUTER = 1.1, 1.48         # the piers span |x| from INNER to OUTER
PIER_HIGH, PIER_LOW = 0.66, 0.5   # the piers' top outside and inside
DEPTH = 0.32                      # the piers' depth (y)
LEAF = 0.46                       # the leaf's height
LEAF_THICK = 0.12
OPEN_FRAMES = 30
SILL = 0.02


def piers(m, root):
    parts = []
    for s in (-1, 1):
        d = DEPTH / 2
        parts.append(kit.hexahedron(f'Pier{s}', m['steel'], (
            (s * INNER, -d, 0), (s * OUTER, -d, 0), (s * OUTER, d, 0), (s * INNER, d, 0),
            (s * INNER, -d * 0.8, PIER_LOW), (s * OUTER, -d * 0.8, PIER_HIGH), (s * OUTER, d * 0.8, PIER_HIGH), (s * INNER, d * 0.8, PIER_LOW)), bevel=0.01))
        # a sloped blade on the outer end, like the wall's piers
        parts.append(kit.hexahedron(f'PierBlade{s}', m['steel'], (
            (s * OUTER - s * 0.02, -0.03, 0), (s * 1.5, -0.03, 0), (s * 1.5, 0.03, 0), (s * OUTER - s * 0.02, 0.03, 0),
            (s * OUTER - s * 0.02, -0.02, PIER_HIGH + 0.06), (s * 1.5, -0.02, 0.2), (s * 1.5, 0.02, 0.2), (s * OUTER - s * 0.02, 0.02, PIER_HIGH + 0.06)), bevel=0.006))
    obj = nb.concrete('Piers', parts, root, 'grey')
    details = []
    for s in (-1, 1):
        for f in (-1, 1):
            y = f * (DEPTH / 2 + 0.004)
            # red stripe down the inner edge, dark joints across the faces
            details.append(beam(f'PierRed{s}{f}', m['remap'], (s * (INNER + 0.03), y, 0.02), (s * (INNER + 0.03), f * (DEPTH * 0.4 + 0.004), PIER_LOW - 0.02), 0.04, 0.008))
            for k, z in enumerate((0.16, 0.34)):
                details.append(box(f'PierJoint{s}{f}{k}', m['dark'], (OUTER - INNER - 0.08, 0.006, 0.01), (s * (INNER + OUTER) / 2 + s * 0.02, f * (DEPTH / 2 - z * 0.06 + 0.002), z), bevel=0))
        details.append(box(f'PierFoot{s}', m['armour_dark'], (OUTER - INNER + 0.04, DEPTH + 0.04, 0.03), (s * (INNER + OUTER) / 2, 0, 0.015), bevel=0.006))
    return obj, kit.merge('PierDetails', details)


def sill(m):
    parts = [box('Sill', m['armour_dark'], (2 * INNER + 0.02, 0.22, SILL), (0, 0, SILL / 2), bevel=0.004),
             box('Slot', m['dark'], (2 * INNER - 0.02, LEAF_THICK + 0.02, 0.004), (0, 0, SILL + 0.001), bevel=0)]
    for f in (-1, 1):
        parts.append(nb.stripes(f'Stripes{f}', m, (0, f * 0.2, 0.006), (2.9, 0.18, 0.012), 'X', 30))
    return kit.merge('Sill', parts)


def leaf(m):
    """The gate leaf: dark armour with ribs, a red frame and the emblem on both faces."""
    t = LEAF_THICK / 2
    w = INNER - 0.005
    parts = [
        box('Leaf', m['armour'], (2 * w, LEAF_THICK, LEAF - 0.03), (0, 0, (LEAF - 0.03) / 2 + SILL), bevel=0.006),
        kit.hexahedron('LeafTop', m['armour_dark'], (
            (-w, -t, LEAF - 0.03 + SILL), (w, -t, LEAF - 0.03 + SILL), (w, t, LEAF - 0.03 + SILL), (-w, t, LEAF - 0.03 + SILL),
            (-w, -0.02, LEAF + SILL), (w, -0.02, LEAF + SILL), (w, 0.02, LEAF + SILL), (-w, 0.02, LEAF + SILL)), bevel=0.004),
    ]
    for f in (-1, 1):
        y = f * (t + 0.003)
        lo, hi = SILL + 0.05, SILL + LEAF - 0.07
        for k in range(-7, 8):
            if abs(k) <= 1:
                continue       # the emblem's place
            x = k * 0.135
            parts.append(box(f'Rib{f}{k}', m['armour_dark'], (0.03, 0.01, hi - lo - 0.03), (x, y, (lo + hi) / 2), bevel=0.003))
        # the red frame
        for z in (lo - 0.015, hi + 0.015):
            parts.append(box(f'FrameH{f}{z:.2f}', m['remap'], (2 * w - 0.08, 0.008, 0.025), (0, y, z), bevel=0.002))
        for x in (-w + 0.04, w - 0.04):
            parts.append(box(f'FrameV{f}{x:.2f}', m['remap'], (0.025, 0.008, hi - lo + 0.055), (x, y, (lo + hi) / 2), bevel=0.002))
        # the emblem: a red triangle with a dark one inside (Nod's scorpion-tail delta)
        zc = (lo + hi) / 2
        for name, size, mat, dy in (('Emblem', 0.2, m['remap'], 0.0), ('EmblemInner', 0.11, m['armour_dark'], 0.004)):
            h = size * math.sqrt(3) / 2
            yy = y + f * dy
            parts.append(kit.hexahedron(f'{name}{f}', mat, (
                (-size / 2, yy - 0.004, zc - h / 3), (size / 2, yy - 0.004, zc - h / 3), (0.001, yy - 0.004, zc + 2 * h / 3), (-0.001, yy - 0.004, zc + 2 * h / 3),
                (-size / 2, yy + 0.004, zc - h / 3), (size / 2, yy + 0.004, zc - h / 3), (0.001, yy + 0.004, zc + 2 * h / 3), (-0.001, yy + 0.004, zc + 2 * h / 3)), bevel=0))
    return kit.merge('Door', parts)


def build():
    root = nb.start('NodGate', 'NodGate', 60)
    m = nb.materials()
    pier, pier_details = piers(m, root)
    base = sill(m)
    door = leaf(m)
    for obj in (pier, pier_details, base, door):
        kit.parent(obj, root)
    lamps = []
    for s in (-1, 1):
        for k, (colour, y) in enumerate((('red', -0.06), ('amber', 0.06))):
            housing, light = nb.lamp(f'Lamp{s}{k}', m, (s * (INNER + 0.08), y, PIER_LOW + 0.03), colour)
            kit.parent(housing, root)
            kit.parent(light, housing)
            lamps.append((housing, light, colour))

    # Build
    kit.keys(base, 'scale', {0: Vector((0.03, 1, 1)), 2: Vector((0.03, 1, 1)), 14: Vector((1.02, 1, 1)), 17: Vector((1, 1, 1))})
    nb.rise(pier, 8, 18, PIER_HIGH + 0.08)
    nb.rise(pier_details, 8, 18, PIER_HIGH + 0.08)
    nb.rise(door, 24, 20, LEAF + 0.05)
    for k, (housing, _, _) in enumerate(lamps):
        kit.pop(housing, 44 + k, 6)
    nb.all_to_build()

    # Idle: red lamps on, blinking twice; the amber ones off
    nb.blinking([(light, kit.flashes((0, 24), (30, 24)) if colour == 'red' else set()) for _, light, colour in lamps])
    # Open: amber lamps flash, the leaf sinks
    for _, light, colour in lamps:
        frames = {}
        for f in range(OPEN_FRAMES + 1):
            on = colour == 'red' or (f // 4) % 2 == 0
            frames[f] = Vector((1, 1, 1)) if on else Vector((HIDDEN,) * 3)
        kit.keys(light, 'scale', frames, 'CONSTANT')
        kit.to_track(light, 'Open')
    kit.keys(door, 'location', {0: Vector((0, 0, 0)), 4: Vector((0, 0, 0.01)), OPEN_FRAMES: Vector((0, 0, -LEAF - 0.01))})
    kit.to_track(door, 'Open')

    pier.location = pier_details.location = door.location = (0, 0, 0)
    base.scale = (1, 1, 1)
    for _, light, colour in lamps:
        light.scale = (1, 1, 1) if colour == 'red' else (HIDDEN,) * 3
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAGATE_A', {'Build': [12, 30, 50], 'Idle': [0], 'Open': [15, 30]}, scale=3.4, target=(0, 0, 0.25), texture=1024)
