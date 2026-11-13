"""
Tiberian Fallout – Tiberium tree ("blossom tree", TIBTRE01–03 of Tiberian Sun) on one cell.

After the in-game look of TIBTRE01 (the sprite in the unit palette UNITTEM.PAL and
screenshots of a temperate map): a thin organic stalk, about 0.75 cells tall (one and a
half infantrymen) and half a cell wide with its arms, twisted from three rust-orange
strands with dark brown crevices between them, orange-tan ridges and red-brown patches;
the upper end swells into a tan head that carries a dark brown, lobed knob. Through the
slits of the knob and its open crown a faint green glow shows (the rules give the tree a
green light). One arm curls out to the side and up and ends in a pale grey-pinkish bulb,
a shorter one on the other side carries a second bulb; small curled twigs without bulbs
on some variants. Dark roots grip the ground, with small Tiberium crystals between them
(the look of TIB.py). Every so often the bulbs swell, the knob pops and puffs a short
column of tiny whitish, light-blue and green specks, which spreads out over the eight
cells round the tree and fades – Tiberium sprouts there (SpawnsTiberium=yes).

Three variants as top-level nodes, all at the origin (the game shows one and removes
the others), like TIBTRE01–03:

    Tree1   0.76 cells tall, the bulb arm curls to the left (as the sprite)
    Tree2   0.69 cells, stouter and more twisted, mirrored: the bulb arm to the right
    Tree3   0.80 cells, slender, an extra twig

Inside each TreeN:

    TrunkN          the stalk with its head, knots and roots
    BranchN1 …      the arms and twigs (pivot where they leave the stalk)
      BulbN1, BulbN2  the pale bulbs at the ends of the two bulb arms (pivot at their stem)
    PodN            the dark knob on the head (pivot at its base)
      GlowN         the faintly glowing core inside the knob (pivot at its centre)
    CrystalsN       the Tiberium crystals at the roots
    SporesN         on top of the knob
      SporeN01 …    36 specks; at rest shrunk to 5 % inside the knob

Clips (every channel in one clip only):

    Idle     4 s loop: the core glows a little wider and back (subtle), the arms sway a hair
    Spread   1.6 s, once: the bulbs swell (0.13 … 0.4 s) and pop back, the knob swells and
             pops at 0.5 s; a short column of specks shoots 0.4 … 0.6 above the top
             (0.47 … 0.93 s), then spreads sideways and drifts down: it is over the
             neighbouring cells from about 1.0 s (median 0.93 cells from the centre,
             1.15 at 1.1 s, 1.23 at 1.2 s; 0.9 … 1.4 cells, farther towards the diagonal
             neighbours) and fades from 1.2 s (all gone by 1.47 s). cloud_reach() prints
             the spread per frame. The clips are sampled every second frame, so every key
             lies on an even frame.

Run headless:

    blender -b --factory-startup --python blender/TIBTRE.py
    blender -b --factory-startup --python blender/TIBTRE.py -- --preview <out dir>

Units: 1 = one map cell. Blender Z is up, front = -Y; origin on the ground in the
middle of the cell.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Quaternion, Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

kit.COLLECTION = 'TiberiumTree'
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'TIBTRE.glb')
BLEND = os.path.join(HERE, 'TIBTRE.blend')

FPS = 30
IDLE_END = 120          # frames of the Idle loop (4 s)
SPREAD_END = 48         # frames of the Spread clip (1.6 s)
BURST = 15              # frame the knob pops in Spread
HIDDEN = 0.05           # rest scale of the specks (inside the knob; 0 would make singular matrices)
SPORES = 36             # specks per tree
Z = Vector((0, 0, 1))

srgb, material = kit.srgb, kit.material
BARK = ('bark', 'shade', 'crevice', 'brown')   # slots of the stalk: orange ridge, tan, dark crevice, red-brown
KNOB = ('knob', 'crevice', 'brown')            # slots of the knob
BULB = ('bulb', 'bulb_shade')                  # slots of the bulbs
CRYSTAL = ('crystal', 'deep', 'tip')           # slots of the crystals (as in TIB.py)
SPECKS = ('speck_white', 'speck_blue', 'speck_green')

# The three variants. Azimuths in degrees (0 = +X, 90 = +Y = back); from the game camera
# 225 points left on the screen, 45 right, 315 to the front.
VARIANTS = (
    dict(name='1', seed=11, height=0.72, pod=(0.038, 0.042), girth=0.032, lean=(-0.03, 0.02),
         wobble=0.02, turns=1.2, roots=5, sprigs=3,
         # height share on the stalk, azimuth, length, curl, start elevation (deg), base radius,
         # sideways drift, bulb radius (0: a bare twig)
         branches=((0.66, 215, 0.30, 140, -25, 0.022, 0.10, 0.044),   # the bulb arm curling up on the left
                   (0.60, 40, 0.11, 45, 15, 0.018, -0.10, 0.045),     # the stub with the right bulb
                   (0.32, 320, 0.12, 170, 0, 0.011, 0.20, 0))),
    dict(name='2', seed=23, height=0.66, pod=(0.04, 0.04), girth=0.036, lean=(0.03, -0.015),
         wobble=0.028, turns=1.6, roots=6, sprigs=3,
         branches=((0.64, 50, 0.28, 145, -25, 0.024, -0.10, 0.044),
                   (0.58, 232, 0.11, 40, 15, 0.019, 0.10, 0.045),
                   (0.36, 140, 0.12, 170, 5, 0.011, 0.10, 0))),
    dict(name='3', seed=37, height=0.76, pod=(0.036, 0.044), girth=0.029, lean=(0.015, 0.035),
         wobble=0.02, turns=1.0, roots=5, sprigs=2,
         branches=((0.70, 222, 0.32, 135, -20, 0.021, 0.10, 0.042),
                   (0.64, 32, 0.12, 50, 15, 0.017, -0.10, 0.043),
                   (0.42, 300, 0.14, 175, 0, 0.011, 0.20, 0),
                   (0.26, 115, 0.11, 155, 10, 0.010, -0.20, 0))),
)


def materials():
    m = {
        'bark': material('TreeOrange', srgb('#c9741f'), 0.65),
        'shade': material('TreeTan', srgb('#b08f5a'), 0.7),
        'crevice': material('TreeCrevice', srgb('#2a1409'), 0.9),
        'brown': material('TreeRust', srgb('#7c3415'), 0.8),
        'knob': material('TreeKnob', srgb('#45261a'), 0.6),
        'bulb': material('TreeBulb', srgb('#ceb0aa'), 0.45),
        'bulb_shade': material('TreeBulbShade', srgb('#93605a'), 0.6),
        'glow': material('TreeGlow', srgb('#24661f'), 0.4, emission=srgb('#34a82c'), strength=0.45),
        'speck_white': material('TreeSpeckWhite', srgb('#eef4f2'), 0.5, emission=srgb('#dfe9e6'), strength=0.9),
        'speck_blue': material('TreeSpeckBlue', srgb('#a6ccf2'), 0.5, emission=srgb('#8fbcf0'), strength=1.0),
        'speck_green': material('TreeSpeckGreen', srgb('#7ad65e'), 0.5, emission=srgb('#62d248'), strength=1.2),
        # the crystals of TIB.py
        'crystal': material('TiberiumCrystal', srgb('#2ee63a'), 0.15, 0.05, emission=srgb('#22e030'), strength=1.6),
        'deep': material('TiberiumDeep', srgb('#14a028'), 0.2, 0.05, emission=srgb('#10b024'), strength=1.0),
        'tip': material('TiberiumTip', srgb('#78ff64'), 0.1, 0.0, emission=srgb('#6cff58'), strength=2.4),
    }
    for key in ('bulb', 'bulb_shade', 'glow') + SPECKS:
        m[key].use_backface_culling = True   # closed shapes: single-sided in glTF
    return m


def assign(obj, m, slots, smooth_shading=True):
    for key in slots:
        obj.data.materials.append(m[key])
    for poly in obj.data.polygons:
        poly.use_smooth = smooth_shading
    return obj


# --------------------------------------------------------------------------- geometry

def smooth(edge0, edge1, x):
    t = min(1.0, max(0.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3 - 2 * t)


def angle_between(a, b):
    """The smallest difference of two angles (radians)."""
    return abs((a - b + math.pi) % (2 * math.pi) - math.pi)


def transport_frames(points):
    """(tangent, normal, binormal) along a polyline; the normal is carried along without
    spinning (parallel transport), so the rings of a tube do not twist."""
    n = len(points)
    tangents = [(points[min(i + 1, n - 1)] - points[max(i - 1, 0)]).normalized() for i in range(n)]
    normal = tangents[0].cross(Z)
    if normal.length < 1e-3:
        normal = tangents[0].cross(Vector((1, 0, 0)))
    frames = []
    for t in tangents:
        normal = (normal - t * normal.dot(t)).normalized()
        frames.append((t, normal, t.cross(normal)))
    return frames


def tube(bm, points, sides, radius, paint, cap_end=True, tip=0.0, turn=lambda i: 0.0):
    """Sweeps a ring of `sides` vertices along `points`; ring i is turned by turn(i) round
    the curve (so twisted strands stay on the vertex columns). radius(i, a): the radius of
    ring i at the angle a round it; paint(i, k, centre): the material slot of the face
    between ring i and i + 1 (i + 0.5 is passed) in column k. The end is closed by a
    cone `tip` long. Returns the rings and the frames."""
    frames = transport_frames(points)
    rings = []
    for i, (p, (_, n, b)) in enumerate(zip(points, frames)):
        rings.append([bm.verts.new(p + (n * math.cos(a) + b * math.sin(a)) * radius(i, a))
                      for a in (2 * math.pi * k / sides + turn(i) for k in range(sides))])
    for i in range(len(rings) - 1):
        for k in range(sides):
            j = (k + 1) % sides
            face = bm.faces.new((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]))
            face.material_index = paint(i + 0.5, k, face.calc_center_median())
    if cap_end:
        last = len(points) - 1
        end = bm.verts.new(points[-1] + frames[-1][0] * tip)
        for k in range(sides):
            face = bm.faces.new((rings[-1][k], rings[-1][(k + 1) % sides], end))
            face.material_index = paint(last, k, face.calc_center_median())
    return rings, frames


def mottle(centre, seed, brown=0.35, shade=-0.35):
    """Stalk colour from smooth noise: red-brown patches, tan patches, mostly orange."""
    n = noise.noise(centre * 8 + Vector((seed * 3.1, seed * 1.7, seed * 0.9)))
    if n > brown:
        return BARK.index('brown')
    if n < shade:
        return BARK.index('shade')
    return BARK.index('bark')


def add_shard(bm, base, direction, length, radius, twist, body, sides=5):
    """A thin crystal shard from `base` along `direction` (as in TIB.py): the shaft in
    material slot `body`, the pointed tip glowing. It starts a little under the ground."""
    d = direction.normalized()
    side = d.cross(Z)
    if side.length < 1e-4:
        side = Vector((1, 0, 0))
    side.normalize()
    up = side.cross(d)
    start = base - d * 0.015
    shaft = length * 0.8

    def ring(centre, r):
        return [bm.verts.new(centre + (side * math.cos(a) + up * math.sin(a)) * r)
                for a in (twist + 2 * math.pi * k / sides for k in range(sides))]

    bottom = ring(start, radius * 0.6)
    top = ring(start + d * shaft, radius)
    tip = bm.verts.new(start + d * (length + 0.015))
    for k in range(sides):
        j = (k + 1) % sides
        bm.faces.new((bottom[k], bottom[j], top[j], top[k])).material_index = body
        bm.faces.new((top[k], top[j], tip)).material_index = CRYSTAL.index('tip')
    bm.faces.new(list(reversed(bottom))).material_index = body


# --------------------------------------------------------------------------- the tree's parts

STALK_RINGS = 22
STRANDS = 3
PER_STRAND = 5                       # columns per strand: two ridge, two flank, one crevice
STALK_SIDES = STRANDS * PER_STRAND


def stalk_points(spec, rng):
    """The centreline of the stalk from under the ground into the knob."""
    top = spec['height'] - spec['pod'][1] * 0.6
    lx, ly = spec['lean']
    w = spec['wobble']
    p1, p2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
    points = []
    for i in range(STALK_RINGS + 1):
        t = i / STALK_RINGS
        x = lx * t ** 1.5 + w * math.sin(math.pi * 1.7 * t + p1) * math.sin(math.pi * t)
        y = ly * t ** 1.5 + w * math.sin(math.pi * 1.3 * t + p2) * math.sin(math.pi * t)
        points.append(Vector((x, y, -0.03 + (top + 0.03) * t)))
    return points


def at(points, t):
    """The point at share t along a polyline of evenly spaced samples."""
    f = t * (len(points) - 1)
    i = min(int(f), len(points) - 2)
    return points[i].lerp(points[i + 1], f - i)


def stalk(bm, spec, rng, points):
    """The stalk twisted from three strands, swelling into the head under the knob."""
    girth, turns = spec['girth'], spec['turns']
    phase = rng.uniform(0, 6.3)
    knots = [(rng.uniform(0.15, 0.7), rng.uniform(0, 2 * math.pi), rng.uniform(0.008, 0.013)) for _ in range(3)]

    def turn(i):
        return 2 * math.pi * turns * (i / STALK_RINGS) ** 1.1

    def knot(i, a):
        return max(math.exp(-(((i / STALK_RINGS - tk) * STALK_RINGS / 1.3) ** 2) - (angle_between(a, ak) / 0.6) ** 2)
                   for tk, ak, _ in knots)

    def radius(i, a):
        t = i / STALK_RINGS
        r = girth * (1 + 0.1 * math.sin(t * 13 + phase)) + 0.035 * math.exp(-t / 0.05)   # flared foot
        r *= 1 + 0.5 * math.exp(-((t - 0.84) / 0.08) ** 2)                               # the head
        r *= 1 - 0.25 * smooth(0.94, 1.0, t)                                             # into the knob
        r *= 1 + 0.24 * math.cos(STRANDS * (a - turn(i)))                                # the strands
        return r + sum(amp * math.exp(-(((t - tk) * STALK_RINGS / 1.3) ** 2) - (angle_between(a, ak) / 0.6) ** 2)
                       for tk, ak, amp in knots)

    def paint(i, k, centre):
        t = i / STALK_RINGS
        a = 2 * math.pi * (k + 0.5) / STALK_SIDES + turn(i)
        column = k % PER_STRAND
        n = noise.noise(centre * 9 + Vector((0, 0, spec['seed'])))
        if knot(i, a) > 0.5:
            return BARK.index('shade')                   # a knot catches the light
        if column == 2:                                  # between two strands
            return BARK.index('crevice') if n > -0.4 else BARK.index('brown')
        if column in (1, 3):                             # the flanks of a strand
            return BARK.index('brown') if n > -0.1 else BARK.index('crevice')
        if centre.z < 0.035:
            return BARK.index('brown')                   # earthy foot
        if t > 0.74:
            return BARK.index('shade') if n > -0.3 else BARK.index('bark')   # the tan head
        return mottle(centre, spec['seed'])

    tube(bm, points, STALK_SIDES, radius, paint, cap_end=False, turn=turn)


def roots(bm, spec, rng, points):
    """Dark roots gripping the ground; returns their azimuths."""
    count = spec['roots']
    azimuths = []
    base = points[0] + Vector((0, 0, 0.08))
    for r in range(count):
        a = 2 * math.pi * (r + rng.uniform(-0.25, 0.25)) / count + spec['seed']
        azimuths.append(a)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Z.cross(d)
        reach = rng.uniform(0.11, 0.18)
        wiggle = rng.uniform(-0.025, 0.025)
        pts = []
        for i in range(6):
            s = i / 5
            # out of the foot, over the ground in a low hump, then down into it
            pts.append(base + d * (0.012 + reach * s ** 0.8) + side * wiggle * math.sin(math.pi * s * 1.5)
                       + Vector((0, 0, -0.06 * s ** 0.7 + 0.012 * math.sin(math.pi * s) - 0.05 * s ** 2)))
        thick = rng.uniform(0.016, 0.022)

        def radius(i, a, thick=thick):
            return thick * (1 - i / 5) ** 0.8 + 0.004

        def paint(i, k, centre, seed=spec['seed'] + r):
            n = noise.noise(centre * 12 + Vector((seed, 0, 0)))
            if centre.z < 0.01 or n < -0.2:
                return BARK.index('crevice')
            return BARK.index('bark') if n > 0.45 else BARK.index('brown')

        tube(bm, pts, 6, radius, paint, tip=0.006)
    return azimuths


def branch(name, m, spec, rng, points, h, azimuth, length, curl, elevation, thick, drift, bulb):
    """An arm leaving the stalk at share h of its height and curling up; its pivot is
    where it leaves the stalk. Returns the arm and, if it carries one, its bulb."""
    az, curl, elevation = math.radians(azimuth), math.radians(curl), math.radians(elevation)
    d = Vector((math.cos(az), math.sin(az), 0))
    side = Z.cross(d)
    start = at(points, h) + d * spec['girth'] * 0.5
    steps = 10
    pts, heads = [Vector()], [elevation]
    p = Vector()
    for k in range(steps):
        s = (k + 0.5) / steps
        e = elevation + curl * s ** 1.7       # the curl tightens towards the tip
        heads.append(e)
        p = p + (d * math.cos(e) + Z * math.sin(e) + side * drift * s).normalized() * length / steps
        pts.append(p.copy())

    def radius(i, a):
        s = i / steps
        return thick * (1 - (0.45 if bulb else 0.7) * s)

    def paint(i, _column, centre):
        k = min(int(i), steps)
        e = heads[k]
        inner = -d * math.sin(e) + Z * math.cos(e)          # towards the centre of the curl
        out = centre - pts[k].lerp(pts[min(k + 1, steps)], 0.5)
        if out.length > 1e-6 and out.normalized().dot(inner) > 0.7:
            return BARK.index('crevice')                     # dark on the inside of the curl
        if out.length > 1e-6 and out.normalized().dot(inner) > 0.2:
            return BARK.index('brown')
        return mottle(centre + start, spec['seed'] + azimuth, brown=0.5, shade=-0.2)

    frames = []

    def build(bm):
        frames.extend(tube(bm, pts, 6, radius, paint, tip=thick * (0.2 if bulb else 0.45))[1])

    obj = assign(kit.mesh_object(name, build), m, BARK)
    obj.location = start
    obj.rotation_mode = 'QUATERNION'
    obj['swayAxis'] = tuple(side)  # read back by idle_keys
    if not bulb:
        return obj, None
    tip_dir = frames[-1][0]
    return obj, (start + pts[-1] - tip_dir * thick * 0.3, tip_dir, bulb)


def bulb_object(name, m, base, direction, radius, seed):
    """A pale grey-pinkish bulb on the end of an arm, a little lumpy, darker at its stem;
    its pivot is the stem, so it swells away from the arm."""
    q = direction.to_track_quat('Z', 'Y')
    length = radius * 1.3

    def build(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=7, radius=1.0)
        for v in bm.verts:
            c = v.co.copy()
            lump = 1 + 0.08 * noise.noise(c * 2.2 + Vector((seed, 0, 0)))
            v.co = q @ Vector((c.x * radius * lump, c.y * radius * lump, (c.z + 1) * length * lump))
        for face in bm.faces:
            local = q.inverted() @ face.calc_center_median()
            face.material_index = BULB.index('bulb_shade') if local.z < length * 0.45 else BULB.index('bulb')

    obj = assign(kit.mesh_object(name, build), m, BULB)
    obj.location = base
    return obj


POD_LOBES = 4
POD_PER_LOBE = 5
POD_ROWS = 6


def pod(name, m, spec, rng, centre):
    """The dark knob on the head: lobes split by slits, open at the crown; pivot at its base."""
    rx, rz = spec['pod']
    pivot = centre - Vector((0, 0, rz * 0.8))
    segs = POD_LOBES * POD_PER_LOBE
    top, bottom = 0.55, math.pi - 0.35
    spiral = rng.uniform(0.3, 0.6)
    seed = spec['seed']

    def lobe(k):
        u = (k % POD_PER_LOBE) / POD_PER_LOBE
        return math.sin(math.pi * u) ** 0.6

    def point(phi, k, shrink=1.0, drop=0.0):
        theta = 2 * math.pi * k / segs + spiral * (phi - top)
        depth = 0.28 * min(1.0, 1.5 * math.sin(phi))
        r = 1 - depth * (1 - lobe(k))
        bump = Vector((math.cos(theta), math.sin(theta), math.cos(phi)))
        r *= 1 + 0.12 * max(0.0, noise.noise(bump * 3.0 + Vector((seed, 0, 0))))   # knobbly lobes
        return Vector((math.cos(theta) * rx * math.sin(phi) * r * shrink,
                       math.sin(theta) * rx * math.sin(phi) * r * shrink,
                       rz * math.cos(phi) - drop)) + centre - pivot

    def build(bm):
        rows = []
        # the crown: a lip curling into the opening
        rows.append([bm.verts.new(point(top, k, 0.6, rz * 0.3)) for k in range(segs)])
        rows.append([bm.verts.new(point(top, k, 0.8, rz * 0.05)) for k in range(segs)])
        for i in range(POD_ROWS + 1):
            phi = top + (bottom - top) * i / POD_ROWS
            rows.append([bm.verts.new(point(phi, k)) for k in range(segs)])
        for i in range(len(rows) - 1):
            for k in range(segs):
                j = (k + 1) % segs
                face = bm.faces.new((rows[i][k], rows[i][j], rows[i + 1][j], rows[i + 1][k]))
                u = (k % POD_PER_LOBE + 0.5) / POD_PER_LOBE
                if i < 2:
                    face.material_index = KNOB.index('brown')      # the rim of the crown
                elif min(u, 1 - u) < 0.5 / POD_PER_LOBE + 0.01 and i < POD_ROWS:
                    face.material_index = KNOB.index('crevice')    # the edges of the slits
                else:
                    face.material_index = KNOB.index('knob')
        end = bm.verts.new(Vector((0, 0, -0.2 * rz)))   # the bottom pole, inside the head
        for k in range(segs):
            face = bm.faces.new((rows[-1][(k + 1) % segs], rows[-1][k], end))
            face.material_index = KNOB.index('knob')

    obj = assign(kit.mesh_object(name, build), m, KNOB)
    obj.location = pivot
    return obj


def glow(name, m, spec, centre):
    """The faintly glowing core inside the knob (just inside the lobes, out in the slits)."""
    rx, rz = spec['pod']

    def build(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0)
        for v in bm.verts:
            v.co = Vector((v.co.x * rx * 0.84, v.co.y * rx * 0.84, v.co.z * rz * 0.85))

    obj = assign(kit.mesh_object(name, build), m, ('glow',))
    obj.location = centre
    return obj


def crystals(name, m, spec, rng, root_azimuths):
    """Small sprigs of Tiberium crystal between the roots."""
    sprigs = []
    for c in range(spec['sprigs']):
        a = root_azimuths[c % len(root_azimuths)] + math.pi / len(root_azimuths) + rng.uniform(-0.3, 0.3)
        dist = rng.uniform(0.09, 0.2)
        centre = Vector((math.cos(a) * dist, math.sin(a) * dist, 0))
        size = rng.uniform(0.045, 0.08)
        shards = []
        count = rng.randint(4, 6)
        for k in range(count):
            b = 2 * math.pi * k / count + rng.uniform(-0.35, 0.35)
            spread = 0.2 if k == 0 else rng.uniform(0.9, 1.7)
            shards.append((Vector((math.cos(b) * spread, math.sin(b) * spread, 1)).normalized(),
                           0.6 if k == 0 else rng.uniform(0.65, 1.0), rng.uniform(0.16, 0.22),
                           rng.uniform(0, 1), rng.choice((0, 0, 1))))
        sprigs.append((centre, size, shards))

    def build(bm):
        for centre, size, shards in sprigs:
            for direction, share, thickness, twist, body in shards:
                base = centre + Vector((direction.x, direction.y, 0)) * 0.01
                add_shard(bm, base, direction, size * share, size * share * thickness, twist, body)

    return assign(kit.mesh_object(name, build), m, CRYSTAL, smooth_shading=False)   # cut facets


def speck_meshes(m):
    """Three shared speck meshes: whitish, light blue, green."""
    meshes = []
    for key, radius in zip(SPECKS, (0.013, 0.012, 0.011)):
        mesh = bpy.data.meshes.new(key.replace('_', ' ').title().replace(' ', ''))
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=radius)
        bm.to_mesh(mesh)
        bm.free()
        mesh.materials.append(m[key])
        for poly in mesh.polygons:
            poly.use_smooth = True
        meshes.append(mesh)
    return meshes


# --------------------------------------------------------------------------- animation

def idle_keys(glow_obj, branches, rng):
    """Idle: the core glows a little wider, the arms sway a hair (a seamless 4 s loop)."""
    kit.keys(glow_obj, 'scale', {0: Vector((1, 1, 1)), 60: Vector((1.07, 1.07, 1.05)), IDLE_END: Vector((1, 1, 1))})
    kit.to_track(glow_obj, 'Idle')
    for obj in branches:
        axis = Vector(obj['swayAxis'])
        del obj['swayAxis']
        amplitude = math.radians(rng.uniform(1.2, 2.0))
        cycles = rng.choice((1, 2))
        phase = rng.uniform(0, 2 * math.pi)
        frames = {f: Quaternion(axis, amplitude * math.sin(2 * math.pi * cycles * f / IDLE_END + phase))
                  for f in range(0, IDLE_END + 1, 10)}
        kit.keys(obj, 'rotation_quaternion', frames)
        kit.to_track(obj, 'Idle')


def spread_pod(pod_obj):
    """Spread: the knob swells, pops and settles back."""
    def s(x, z):
        return Vector((x, x, z))
    kit.keys(pod_obj, 'scale', {0: s(1, 1), 6: s(1.04, 1.06), 12: s(1.2, 1.3), BURST - 1: s(1.26, 1.38),
                                BURST + 1: s(0.84, 0.8), BURST + 7: s(1.06, 1.08), BURST + 13: s(0.97, 0.97),
                                BURST + 19: s(1, 1), SPREAD_END: s(1, 1)})
    kit.to_track(pod_obj, 'Spread')


def spread_bulb(bulb_obj, delay):
    """Spread: a bulb swells and pops back just before the knob."""
    def s(x):
        return Vector((x, x, x * 1.08))
    kit.keys(bulb_obj, 'scale', {0: s(1), 4 + delay: s(1), 10 + delay: s(1.22), 12 + delay: s(0.88),
                                 18 + delay: s(1.05), 24 + delay: s(1), SPREAD_END: s(1)})
    kit.to_track(bulb_obj, 'Spread')


def spread_speck(obj, rng, j, centre, rz):
    """Spread: one speck shoots up in a short column from the knob, spreads sideways over
    the neighbouring cells, drifts down and fades; then it is back inside the knob.
    Returns (start, end, reach) for the report."""
    a = 2 * math.pi * (j + rng.uniform(-0.4, 0.4)) / SPORES
    reach = rng.uniform(0.85, 1.12) * (1 + 0.2 * abs(math.sin(2 * a)))   # farther towards the diagonal cells
    d = Vector((math.cos(a), math.sin(a), 0))
    target = d * reach - Vector((centre.x, centre.y, 0))                 # over the ground, relative to the knob
    start = BURST - 1 + 2 * int(j * 4 / SPORES)                         # a stream over 0.2 s: the column
    apex = start + rng.choice((6, 8))
    arrive = rng.choice((30, 32, 34))
    end = rng.choice((40, 42, 44))
    up = rng.uniform(0.4, 0.6)
    size = rng.uniform(0.8, 1.25)
    zero = Vector()
    keys = {
        0: (zero, HIDDEN),
        start - 2: (zero, HIDDEN),
        start: (Vector((0, 0, rz * 1.1)), size * 0.6),
        apex: (d * rng.uniform(0.02, 0.07) + Vector((0, 0, up)), size),                    # the column
        arrive: (target + Vector((0, 0, up * rng.uniform(0.35, 0.7))), size * 0.9),       # over the neighbours
        end: (target * 1.08 + Vector((0, 0, -centre.z * rng.uniform(0.15, 0.5))), HIDDEN),  # sunk and faded
        end + 2: (zero, HIDDEN),
        SPREAD_END: (zero, HIDDEN),
    }
    kit.keys(obj, 'location', {f: v for f, (v, _) in keys.items()})
    kit.keys(obj, 'scale', {f: Vector((s, s, s)) for f, (_, s) in keys.items()})
    kit.to_track(obj, 'Spread')
    return start, end, reach


# --------------------------------------------------------------------------- build

def tree(m, spec, meshes, report):
    n = spec['name']
    rng = random.Random(spec['seed'])
    root = kit.empty(f'Tree{n}')
    points = stalk_points(spec, rng)
    centre = points[-1] + Vector((0, 0, spec['pod'][1] * 0.6))
    azimuths = []

    def wood(bm):
        stalk(bm, spec, rng, points)
        azimuths.extend(roots(bm, spec, rng, points))

    kit.parent(assign(kit.mesh_object(f'Trunk{n}', wood), m, BARK), root)

    branches, bulbs = [], []
    for b, args in enumerate(spec['branches']):
        obj, bulb = branch(f'Branch{n}{b + 1}', m, spec, rng, points, *args)
        kit.parent(obj, root)
        branches.append(obj)
        if bulb:
            base, direction, radius = bulb
            bulbs.append(kit.parent(bulb_object(f'Bulb{n}{len(bulbs) + 1}', m, base, direction, radius,
                                                spec['seed'] + b), obj))

    pod_obj = kit.parent(pod(f'Pod{n}', m, spec, rng, centre), root)
    glow_obj = kit.parent(glow(f'Glow{n}', m, spec, centre), pod_obj)
    kit.parent(crystals(f'Crystals{n}', m, spec, rng, azimuths), root)

    group = kit.parent(kit.empty(f'Spores{n}', centre), root)
    timing = []
    for j in range(SPORES):
        obj = bpy.data.objects.new(f'Spore{n}{j + 1:02d}', meshes[j % 3])
        kit.collection().objects.link(obj)
        obj.parent = group
        timing.append(spread_speck(obj, rng, j, centre, spec['pod'][1]))

    idle_keys(glow_obj, branches, rng)
    spread_pod(pod_obj)
    for k, obj in enumerate(bulbs):
        spread_bulb(obj, 2 * k)
    report[f'Tree{n}'] = {'top': round(centre.z + spec['pod'][1], 3), 'timing': timing}


def build():
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 0
    scene.frame_end = IDLE_END
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    m = materials()
    meshes = speck_meshes(m)
    report = {}
    for spec in VARIANTS:
        tree(m, spec, meshes, report)
    return report


def triangles():
    """Triangles per tree, the specks apart."""
    counts = {}
    for obj in kit.collection().objects:
        if obj.type != 'MESH':
            continue
        top = obj
        while top.parent:
            top = top.parent
        key = top.name + (' specks' if obj.name.startswith('Spore') else '')
        counts[key] = counts.get(key, 0) + sum(len(p.vertices) - 2 for p in obj.data.polygons)
    return counts


def extent(tree_name):
    """Width (largest horizontal extent) and height of a tree at rest, specks apart."""
    bpy.context.scene.frame_set(0)
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for obj in bpy.data.objects[tree_name].children_recursive:
        if obj.type != 'MESH' or obj.name.startswith('Spore'):
            continue
        for v in obj.data.vertices:
            w = obj.matrix_world @ v.co
            if w.z < 0:
                continue   # roots under the ground
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return round(max(hi.x - lo.x, hi.y - lo.y), 2), round(hi.z, 2)


def cloud_reach():
    """Per frame of Spread: how far the visible specks of Tree1 are from the cell's centre
    (median and maximum, in cells)."""
    scene = bpy.context.scene
    specks = [o for o in kit.collection().objects if o.name.startswith('Spore1') and o.type == 'MESH']
    rows = []
    for frame in range(0, SPREAD_END + 1, 3):
        scene.frame_set(frame)
        seen = sorted(Vector((o.matrix_world.translation.x, o.matrix_world.translation.y)).length
                      for o in specks if o.matrix_world.to_scale().x > 0.3)
        if seen:
            rows.append((frame, round(frame / FPS, 2), len(seen), round(seen[len(seen) // 2], 2), round(seen[-1], 2)))
        else:
            rows.append((frame, round(frame / FPS, 2), 0, None, None))
    scene.frame_set(0)
    return rows


def export_glb(path=OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in kit.collection().objects:
        obj.select_set(True)
    bpy.context.scene.frame_set(0)   # the rest pose: specks hidden, knob and bulbs at their size
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_lights=False,
        export_cameras=False,
        export_animations=True,
        export_animation_mode='ACTIONS',
        export_merge_animation='NLA_TRACK',   # one clip per NLA track name
        export_force_sampling=True,
        # sampled every second frame (half the size); all keys of the clips lie on even
        # frames, so a speck's jump back into the knob happens while it is hidden
        export_frame_step=2,
    )
    return {'path': path, 'bytes': os.path.getsize(path)}


# --------------------------------------------------------------------------- preview

def preview_scene(size):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = size
    scene.render.resolution_y = int(size * 0.75)
    world = scene.world or bpy.data.worlds.new('World')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.35, 0.37, 0.42, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8
    try:
        scene.view_settings.view_transform = 'Standard'
    except TypeError:
        pass
    light = material('PreviewCellLight', srgb('#5f6a34'), 1.0)
    dark = material('PreviewCellDark', srgb('#525c2c'), 1.0)
    for i in range(-2, 3):
        for j in range(-2, 3):
            bpy.ops.mesh.primitive_plane_add(size=0.98, location=(i, j, -0.002))
            cell = bpy.context.active_object
            cell.name = f'PreviewCell{i}{j}'
            cell.data.materials.append(light if (i + j) % 2 == 0 else dark)
    sun = bpy.data.objects.new('PreviewSun', bpy.data.lights.new('PreviewSun', 'SUN'))
    sun.data.energy = 4.0
    sun.data.angle = math.radians(3)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((-6, 2, 9)).to_track_quat('Z', 'Y').to_euler()
    cam = bpy.data.objects.new('PreviewCamera', bpy.data.cameras.new('PreviewCamera'))
    cam.data.type = 'ORTHO'
    scene.collection.objects.link(cam)
    scene.camera = cam
    return cam


def aim(cam, target, scale, azimuth=45, elevation=30):
    direction = Vector((math.sin(math.radians(azimuth)) * math.cos(math.radians(elevation)),
                        -math.cos(math.radians(azimuth)) * math.cos(math.radians(elevation)),
                        math.sin(math.radians(elevation))))
    cam.location = Vector(target) + direction * 10
    cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
    cam.data.ortho_scale = scale


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def preview(out_dir, size=640):
    """Renders through the game's camera: the three variants side by side, a close-up of
    Tree1 (rest, Idle half way, the pop), and frames of Tree1's Spread over the 5 × 5
    cells round it."""
    os.makedirs(out_dir, exist_ok=True)
    scene = bpy.context.scene
    cam = preview_scene(size)
    trees = [bpy.data.objects[f'Tree{v["name"]}'] for v in VARIANTS]
    right = Vector((1, 1, 0)).normalized()
    for k, obj in enumerate(trees):
        obj.location = right * (k - 1) * 0.6
    scene.frame_set(0)
    aim(cam, (0, 0, 0.4), 2.0)
    render(os.path.join(out_dir, 'variants.png'))
    aim(cam, (0, 0, 0.4), 2.0, azimuth=-35, elevation=12)
    render(os.path.join(out_dir, 'variants_low.png'))
    for obj in trees:
        obj.location = (0, 0, 0)
    for obj in trees[1:]:
        for child in [obj] + list(obj.children_recursive):
            child.hide_render = True
    aim(cam, (0, 0, 0.42), 1.0)
    render(os.path.join(out_dir, 'closeup.png'))
    scene.frame_set(60)
    render(os.path.join(out_dir, 'closeup_idle60.png'))
    aim(cam, (0, 0, 0.75), 1.0)
    for frame in (0, BURST - 3, BURST - 1, BURST + 3, BURST + 7):
        scene.frame_set(frame)
        render(os.path.join(out_dir, f'burst_{frame:03d}.png'))
    aim(cam, (0, 0, 0.35), 3.8)
    for frame in (0, 14, 17, 20, 24, 28, 32, 36, 41, 46):
        scene.frame_set(frame)
        render(os.path.join(out_dir, f'spread_{frame:03d}.png'))
    scene.frame_set(0)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    report = build()
    print('triangles', triangles(), flush=True)
    for name, info in report.items():
        starts = [s for s, _, _ in info['timing']]
        ends = [e for _, e, _ in info['timing']]
        reach = [r for _, _, r in info['timing']]
        print(name, 'width, height', extent(name), 'specks from', min(starts), 'gone by', max(ends),
              'reach', round(min(reach), 2), '…', round(max(reach), 2), flush=True)
    print('cloud (frame, s, visible, median, max)', cloud_reach(), flush=True)
    print('export', export_glb(), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        preview(args[args.index('--preview') + 1])


if __name__ == '__main__' and bpy.app.background:
    main()
