"""
Tiberian Fallout – Nod tech center (NATECH), after Tiberian Sun.

A wide, low, uneven mound of light concrete (foundation 2 × 2 cells) running out into
the corners of the foundation. On its left a low grooved dome, at the back a dark
craggy tower of stacked, rough blocks, from which a dark rocky ridge falls away to the
right. Three thick red conduits arch from the mound's left edge over the dome into the
tower's flank; two red claws stand at the mound's front foot.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Nodes: NodTechCenter (root) – PlatformGroup (Platform, PlatformTrim, Dome, Ridge,
Tier0 – Tier1 – Tier2 – Spire, Conduit0–2, Claw0/1, lamps).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the mound rises out of the ground, the dome, the ridge and
             the tower's blocks come up, the conduits arch over, the claws come up, the
             lights come on
    Idle     loop, 2 s: the beacons on the tower's top blink red and amber in turn, the
             small lamps on the mound flicker (the original's NATECH_A)

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NATECH.py [-- --preview <dir>]

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

BUILD_END = 72

SEGMENTS = 48
# the mound: (radius, height) from its foot up
MOUND = ((0.98, 0.0), (0.88, 0.05), (0.74, 0.12), (0.56, 0.18), (0.3, 0.21), (0.0, 0.22))
DOME = Vector((-0.3, -0.12, 0.0))
DOME_RADIUS = 0.5
TOWER = Vector((0.12, 0.42, 0.0))
# the tower's rough blocks: centre offset, bottom size, top size, height (stacked)
TIERS = (((0.0, 0.0), (0.62, 0.56), (0.5, 0.44), 0.26),
         ((0.02, 0.03), (0.44, 0.38), (0.34, 0.3), 0.22),
         ((0.04, 0.05), (0.3, 0.26), (0.2, 0.17), 0.2))
CLAWS = (Vector((0.24, -0.8, 0)), Vector((0.64, -0.5, 0)))
LIGHT_CONCRETE = '#aeaaa1'
ROCK = '#5c5d61'

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def jitter(x, y, z, amount):
    """A small deterministic wobble (the original's mound is rough, no lathe)."""
    return amount * (math.sin(12.9 * x + 7.3 * y + 3.1 * z) * 0.6 + math.sin(31.7 * y - 17.1 * x + 1.3) * 0.4)


def spread(a, r):
    """How far the mound reaches in direction `a` at the nominal radius `r`: out into
    the foundation's corners at its foot, a little uneven."""
    n = 3.0
    square = 1 / (abs(math.cos(a)) ** n + abs(math.sin(a)) ** n) ** (1 / n)
    t = max(0.0, min(1.0, (r - 0.4) / 0.58))
    return 1 + (square * 0.93 * (1 + 0.04 * math.sin(3 * a + 0.4) + 0.03 * math.sin(7 * a)) - 1) * t


def mound_height(x, y):
    a, d = math.atan2(y, x), math.hypot(x, y)
    for (r0, z0), (r1, z1) in zip(MOUND, MOUND[1:]):
        R0, R1 = r0 * spread(a, r0), r1 * spread(a, r1)
        if R1 <= d <= R0 and R0 != R1:
            return z0 + (z1 - z0) * (R0 - d) / (R0 - R1)
    return MOUND[-1][1] if d < 0.4 else 0.0


def mound_mesh(name, mat):
    def build(bm):
        rings = []
        for i, (r, z) in enumerate(MOUND[:-1]):
            ring = []
            for k in range(SEGMENTS):
                a = 2 * math.pi * k / SEGMENTS
                R = r * spread(a, r)
                x, y = R * math.cos(a), R * math.sin(a)
                dz = 0 if i == 0 else jitter(x, y, z, 0.018)
                ring.append(bm.verts.new((x, y, z + dz)))
            rings.append(ring)
        for lower, upper in zip(rings, rings[1:]):
            for k in range(SEGMENTS):
                j = (k + 1) % SEGMENTS
                bm.faces.new((lower[k], lower[j], upper[j], upper[k]))
        centre = bm.verts.new((0, 0, MOUND[-1][1]))
        for k in range(SEGMENTS):
            bm.faces.new((rings[-1][k], rings[-1][(k + 1) % SEGMENTS], centre))
        bm.faces.new(rings[0][::-1])

    return kit.finish(kit.mesh_object(name, build), mat, 0.0)


def platform(m, root):
    """The light concrete mound and its trims: dirt at the foot, dark cracks."""
    shell = nod.concrete('Platform', [mound_mesh('PlatformBody', m['steel'])], root, LIGHT_CONCRETE)
    parts = []
    for i in range(SEGMENTS):   # dirt round the foot, following the outline
        a0, a1 = 2 * math.pi * i / SEGMENTS, 2 * math.pi * (i + 1) / SEGMENTS
        p0 = Vector((math.cos(a0), math.sin(a0), 0)) * 0.98 * spread(a0, 0.98)
        p1 = Vector((math.cos(a1), math.sin(a1), 0)) * 0.98 * spread(a1, 0.98)
        parts.append(kit.hexahedron(f'Dirt{i}', m['dirt'], (
            p0 * 0.95, p0 * 1.05, p1 * 1.05, p1 * 0.95,
            p0 * 0.95 + Vector((0, 0, 0.01)), p0 * 1.05 + Vector((0, 0, 0.003)), p1 * 1.05 + Vector((0, 0, 0.003)),
            p1 * 0.95 + Vector((0, 0, 0.01))), bevel=0))
    return shell, kit.merge('PlatformTrim', parts)


def dome(m, root):
    """The low grooved dome on the left (concrete) and its dark grooves; origin at its foot."""
    r = DOME_RADIUS
    profile = ((r, 0.0), (r * 0.97, 0.12), (r * 0.86, 0.23), (r * 0.68, 0.32), (r * 0.42, 0.39), (r * 0.18, 0.415), (0.0, 0.42))
    body = nod.lathe('DomeBody', m['steel'], profile, DOME, 28)
    shell = nod.concrete('Dome', [body], root, LIGHT_CONCRETE, DOME)
    parts = []
    for i, (lo, hi) in enumerate(((1, 2), (2, 3), (3, 4))):   # grooves: thin dark bands following the dome's shape
        (r0, z0), (r1, z1) = profile[lo], profile[hi]
        z = (z0 + z1) / 2
        rr = (r0 + r1) / 2
        parts.append(cylinder(f'Groove{i}', m['nplate'], rr + 0.008 + (r0 - r1) * 0.011 / (z1 - z0), 0.022, DOME + Vector((0, 0, z)),
                              segments=28, bevel=0, radius2=rr + 0.008 - (r0 - r1) * 0.011 / (z1 - z0)))
    parts.append(cylinder('DomeHatch', m['nplate'], 0.09, 0.03, DOME + Vector((0, 0, 0.425)), segments=12))
    return shell, kit.merge('DomeTrim', parts, DOME)


def rough_prism(name, mat, centre, bottom, top, z0, z1, seed):
    """A block with cut corners whose corners are pushed about (craggy)."""
    cx, cy = centre
    lo = nod.chamfered(cx, cy, bottom[0], bottom[1], bottom[0] * 0.25)
    hi = nod.chamfered(cx + 0.01, cy + 0.01, top[0], top[1], top[0] * 0.3)
    lo = [(x + jitter(x, y, seed, 0.04), y + jitter(y, x, seed + 1, 0.04)) for x, y in lo]
    hi = [(x + jitter(x, y, seed + 2, 0.05), y + jitter(y, x, seed + 3, 0.05)) for x, y in hi]
    return nod.prism(name, mat, lo, hi, z0, z1, 0.006)


def tiers(m, root):
    """The tower's rough blocks (dark concrete, each its own object, origin at its foot)
    and a spire; returns [(tier, trims)], the top."""
    out = []
    z = mound_height(TOWER.x, TOWER.y) - 0.04
    for i, ((ox, oy), bottom, top, h) in enumerate(TIERS):
        cx, cy = TOWER.x + ox, TOWER.y + oy
        body = rough_prism(f'Tier{i}Body', m['steel'], (cx, cy), bottom, top, z, z + h, i * 1.7)
        foot = Vector((cx, cy, z))
        tier = nod.concrete(f'Tier{i}', [body], root, ROCK, foot)
        parts = [box(f'Tier{i}Slit{k}', m['dark'], (0.07, 0.02, 0.03),
                     Vector((cx - 0.07 + k * 0.1, cy - (bottom[1] + top[1]) / 4 - 0.006, z + h * 0.45)),
                     bevel=0.003, rotation=(math.radians(-22), 0, 0)) for k in range(2)]
        parts.append(box(f'Tier{i}Ledge', m['nplate_dark'], (top[0] * 0.8, top[1] * 0.8, 0.014), Vector((cx + 0.01, cy + 0.01, z + h + 0.007)),
                         bevel=0.003))
        out.append((tier, kit.merge(f'Tier{i}Trim', parts, foot)))
        z += h
    return out, Vector((TOWER.x + TIERS[2][0][0] + 0.01, TOWER.y + TIERS[2][0][1] + 0.01, z + 0.014))


def ridge(m, root):
    """The dark rocky ridge falling from the tower to the right (+X), as a few rough
    blocks; origin at its foot."""
    blocks = []
    for i, (x, y, sx, sy, h) in enumerate(((0.4, 0.26, 0.42, 0.4, 0.3), (0.56, 0.08, 0.4, 0.38, 0.2), (0.7, -0.1, 0.36, 0.34, 0.12),
                                           (0.82, -0.26, 0.24, 0.24, 0.06))):
        z = mound_height(x, y) - 0.04
        blocks.append(rough_prism(f'RidgeBlock{i}', m['steel'], (x, y), (sx, sy), (sx * 0.6, sy * 0.55), z, z + h, 5 + i))
    foot = Vector((0.6, 0.06, 0))
    return nod.concrete('Ridge', blocks, root, ROCK, foot)


def bezier(a, c, b, t):
    return (1 - t) ** 2 * a + 2 * (1 - t) * t * c + t * t * b


# the conduits: from the mound's left edge over the dome into the tower's left flank
CONDUITS = []
for k in range(3):
    start = Vector((-0.86 + 0.08 * k, -0.42 + 0.2 * k, 0.0))
    start.z = mound_height(start.x, start.y) - 0.01
    end = TOWER + Vector((-0.2, -0.16 + 0.1 * k, 0.5 - 0.03 * k))
    control = (start + end) / 2 + Vector((0.02, -0.1, 0.62 - 0.05 * k))
    CONDUITS.append((start, control, end))


def conduit(m, i, start, control, end):
    """A thick red conduit along a curve, with dark collars at both ends; origin at its start."""
    parts = []
    n = 14
    points = [bezier(start, control, end, k / n) for k in range(n + 1)]
    for k, (a, b) in enumerate(zip(points, points[1:])):
        part = cylinder(f'Conduit{i}_{k}', m['remap'], 0.038, (b - a).length + 0.02, (a + b) / 2, segments=10, bevel=0)
        part.rotation_mode = 'QUATERNION'
        part.rotation_quaternion = (b - a).to_track_quat('Z', 'Y')
        parts.append(part)
    for p, q in ((points[0], points[1]), (points[-1], points[-2])):
        collar = cylinder(f'Collar{i}{p.x:.2f}', m['nplate_dark'], 0.054, 0.08, p, segments=10, bevel=0.006)
        collar.rotation_mode = 'QUATERNION'
        collar.rotation_quaternion = (q - p).to_track_quat('Z', 'Y')
        parts.append(collar)
    return kit.merge(f'Conduit{i}', parts, start)


def claw(m, i, at):
    """A red claw at the mound's front foot: a dark socket, a red block, two red prongs
    bent outwards; origin on the ground."""
    at = at + Vector((0, 0, mound_height(at.x, at.y)))
    face = Vector((at.x, at.y, 0)).normalized()
    side = Vector((-face.y, face.x, 0))
    rot = (0, 0, math.atan2(face.y, face.x) + math.pi / 2)
    parts = [
        box(f'Claw{i}Socket', m['nplate_dark'], (0.2, 0.14, 0.06), at + Vector((0, 0, 0.0)), bevel=0.01, rotation=rot),
        box(f'Claw{i}Block', m['remap'], (0.16, 0.11, 0.08), at + Vector((0, 0, 0.06)), bevel=0.015, rotation=rot),
    ]
    up = Vector((0, 0, 1))
    for s in (-1, 1):
        root = at + side * 0.06 * s + up * 0.07
        tip = root + side * 0.07 * s + face * 0.1 + up * 0.08
        parts.append(beam(f'Claw{i}Prong{s}', m['remap'], root, tip, 0.04, 0.04))
        parts.append(beam(f'Claw{i}Tip{s}', m['remap'], tip, tip + face * 0.06 - up * 0.03, 0.03, 0.03))
    return kit.merge(f'Claw{i}', parts, at)


def build():
    root = nod.start('NodTechCenter', 'NodTechCenter', BUILD_END)
    m = nod.materials()
    m['glow_white'] = kit.material('GlowWhite', (0, 0, 0), 1.0, emission=kit.srgb('#fff2c8'), strength=3, alpha=0.25)
    keys = kit.keys

    # ---- the mound rises out of the ground (translation only: lamps hang on it)
    base = kit.parent(kit.empty('PlatformGroup'), root)
    shell, trim = platform(m, root)
    kit.parent(shell, base)
    kit.parent(trim, base)
    nod.rise(base, 0, 14, 0.2)

    # ---- the dome, the ridge and the tower's blocks come up
    dome_obj, dome_trim = dome(m, root)
    kit.parent(dome_obj, base)
    kit.parent(dome_trim, dome_obj)
    keys(dome_obj, 'location', {0: DOME - Vector((0, 0, 0.38)), 10: DOME - Vector((0, 0, 0.38)), 28: DOME + Vector((0, 0, 0.006)), 31: DOME.copy()})
    ridge_obj = kit.parent(ridge(m, root), base)
    nod.rise(ridge_obj, 16, 14, 0.36)
    stack, top = tiers(m, root)
    holder = base
    for i, (tier, tier_trim) in enumerate(stack):
        kit.parent(tier, holder)
        kit.parent(tier_trim, tier)
        rest = tier.location.copy()
        h = TIERS[i][3]
        keys(tier, 'location', {0: rest - Vector((0, 0, h + 0.06)), 14 + 8 * i: rest - Vector((0, 0, h + 0.06)),
                                26 + 8 * i: rest + Vector((0, 0, 0.006)), 29 + 8 * i: rest})
        holder = tier
    spire = kit.merge('Spire', [
        nod.prism('SpireBody', m['nplate_dark'], nod.chamfered(top.x, top.y, 0.12, 0.1, 0.03), nod.chamfered(top.x, top.y, 0.06, 0.05, 0.012),
                  top.z, top.z + 0.08, 0.004),
        box('SpireCap', m['remap'], (0.08, 0.07, 0.025), top + Vector((0, 0, 0.08)), bevel=0.006),
    ], top)
    kit.parent(spire, holder)
    keys(spire, 'location', {0: spire.location - Vector((0, 0, 0.18)), 50: spire.location - Vector((0, 0, 0.18)), 58: spire.location.copy()})

    # ---- the conduits arch over, the claws come up
    for i, (start, control, end) in enumerate(CONDUITS):
        obj = kit.parent(conduit(m, i, start, control, end), base)
        kit.pop(obj, 40 + 4 * i, 10)
    lights = []
    for i, at in enumerate(CLAWS):
        obj = kit.parent(claw(m, i, at), base)
        kit.pop(obj, 46 + 4 * i, 8)

    # ---- the beacons on the tower's top and small lamps on the mound (NATECH_A)
    tip = top + Vector((0, 0, 0.0925))
    lights.append((nod.lamp(m, spire, 'TopLamp', tip + Vector((-0.02, 0, 0)), 'red', 60),
                   kit.flashes((0, 8), (20, 8), (40, 8))))
    lights.append((nod.lamp(m, spire, 'TopLampAmber', tip + Vector((0.025, 0.0, 0)), 'amber', 61),
                   kit.flashes((10, 8), (30, 8), (50, 8))))
    for i, (x, y) in enumerate(((-0.78, 0.2), (-0.62, 0.36), (-0.5, -0.66))):
        at = Vector((x, y, mound_height(x, y)))
        lights.append((nod.lamp(m, base, f'MoundLamp{i}', at, 'white' if i != 1 else 'red', 62 + i),
                       kit.flashes((7 + 17 * i, 3), (33 + 11 * i, 4))))

    nod.clips(lights)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, 'NATECH', {'Build': [BUILD_END // 3, 2 * BUILD_END // 3, BUILD_END], 'Idle': [0, 10]},
             ortho=2.9, target=(0.05, 0, 0.3))
