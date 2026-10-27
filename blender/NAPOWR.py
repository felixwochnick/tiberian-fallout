"""
Tiberian Fallout – Nod power plant (NAPOWR), after Tiberian Sun.

A tall, barely tapering reactor cone (top ~0.75 × the foot) of mid grey concrete with
dark ribs, standing on a wide oval platform (foundation 2 × 2 cells) that reaches out
furthest towards the front (-Y, lower left on screen). The cone is open on top: a
dark shaft inside a light lip, two thick red bands right under the rim, glowing from
within. The platform is light beige-grey stained concrete on a dark drum; six long red
blades jut out from its edge, slanting down to the ground, four small red fins stand
on its deck round the cone's foot. On the right (+X/+Y, screen right) a thick pipe
arcs from the cone's flank down to a generator on the deck's edge.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Nodes: NodPowerPlant (root) – PlatformGroup (Deck, blades, fins, generator, pipe) and
ConeGroup (Cone with ribs, bands, ShaftGlow, BandGlow, lamps).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the platform rises out of the ground, the blades shoot
             out, the cone rises out of the deck, the generator comes up, the pipe
             grows down to it, the lamps come on
    Idle     loop, 2 s: the reactor glows up and fades in the open top and round the
             red bands (the original's NAPOWR_A overlay), the white lamps on the cone
             and the generator's lamp blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NAPOWR.py [-- --preview <dir>]

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

DECK = 0.16             # top of the platform
DECK_RX = 0.8           # the oval platform's half widths …
DECK_RY = 0.86
DECK_SHIFT = -0.08      # … shifted to the front (-Y)
CONE_FOOT = 0.39
CONE_TOP = 0.29
CONE_HEIGHT = 1.2       # above the deck
PIPE_ANGLE = math.radians(30)   # the pipe and the generator: screen right
CONE_CONCRETE = '#9a9b9c'
DECK_CONCRETE = '#b2ad9f'

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def cone_radius(z):
    """Radius of the cone at a height z above the deck (straight flank)."""
    t = max(0.0, min(1.0, z / CONE_HEIGHT))
    return CONE_FOOT + (CONE_TOP - CONE_FOOT) * t


def deck_edge(a):
    """Point on the deck's oval edge in direction `a` (radians), on the ground plane."""
    d = Vector((math.cos(a), math.sin(a), 0))
    # ray from the cone's axis (0, 0) to the shifted ellipse
    ay, by = d.y, -DECK_SHIFT
    qa = (d.x / DECK_RX) ** 2 + (ay / DECK_RY) ** 2
    qb = 2 * ay * by / DECK_RY ** 2
    qc = (by / DECK_RY) ** 2 - 1
    t = (-qb + math.sqrt(qb * qb - 4 * qa * qc)) / (2 * qa)
    return d * t


def oval(obj):
    """Stretches a round lathe (radius 1 = DECK_RX) to the deck's oval and shifts it."""
    obj.data.transform(Matrix.Translation((0, DECK_SHIFT, 0)) @ Matrix.Diagonal((1, DECK_RY / DECK_RX, 1, 1)))
    return obj


def platform(m, root):
    """The stained concrete deck and its dark drum and rim (returned apart: the
    concrete is baked); origin on the ground."""
    deck = nod.concrete('Deck', [
        oval(nod.lathe('DeckTop', m['steel'], ((DECK_RX - 0.01, DECK - 0.045), (DECK_RX + 0.015, DECK - 0.02), (DECK_RX - 0.02, DECK),
                                               (0.3, DECK + 0.004)), (0, 0, 0), 56)),
    ], root, DECK_CONCRETE)
    parts = [
        oval(cylinder('Drum', m['nplate_dark'], DECK_RX * 0.8, 0.12, (0, 0, 0.06), segments=48, bevel=0.006)),
        oval(nod.lathe('DeckUnder', m['nplate'], ((DECK_RX * 0.8, 0.115), (DECK_RX - 0.01, DECK - 0.045)), (0, 0, 0), 56)),
        oval(cylinder('DeckRim', m['nsteel'], DECK_RX + 0.02, 0.018, (0, 0, DECK - 0.032), segments=56, bevel=0)),
        oval(cylinder('Dirt', m['dirt'], DECK_RX + 0.08, 0.012, (0, 0, 0.006), segments=48, bevel=0)),
    ]
    for i in range(10):  # radial seams on the deck
        a = 2 * math.pi * (i + 0.5) / 10
        edge = deck_edge(a)
        d = edge.normalized()
        parts.append(beam(f'Seam{i}', m['nplate'], d * (CONE_FOOT + 0.06) + Vector((0, 0, DECK + 0.004)),
                          edge - d * 0.05 + Vector((0, 0, DECK + 0.002)), 0.016, 0.008))
    # stains: flat dirty patches on the deck
    for i, (x, y, r) in enumerate(((-0.55, -0.42, 0.11), (0.1, -0.78, 0.09), (-0.6, 0.25, 0.08), (0.52, -0.38, 0.07))):
        parts.append(cylinder(f'Stain{i}', m['dirt'], r, 0.004, (x, y, DECK + 0.002), segments=12, bevel=0))
    return deck, kit.merge('DeckDetails', parts)


def blade(m, i, a):
    """A long red blade jutting out of the deck's edge in direction `a`, slanting down
    to the ground, with its clamp; origin at its root."""
    edge = deck_edge(a)
    d = edge.normalized()
    root = edge - d * 0.1 + Vector((0, 0, DECK - 0.04))
    parts = [nod.spike(f'Blade{i}', m['remap'], root, d, 0.7, 0.17, 0.05, droop=0.19),
             box(f'BladeClamp{i}', m['nplate_dark'], (0.11, 0.16, 0.07), root + Vector((0, 0, 0.012)), bevel=0.006, rotation=(0, 0, a))]
    return kit.merge(f'Blade{i}', parts, root)


def fin(m, i, a):
    """A small red fin standing on the deck, leaning out; origin at its foot."""
    d = Vector((math.cos(a), math.sin(a), 0))
    s = Vector((-d.y, d.x, 0))
    root = d * (CONE_FOOT + 0.12) + Vector((0, 0, DECK))
    up = Vector((0, 0, 1))
    shape = kit.hexahedron(f'Fin{i}', m['remap'], (
        root - d * 0.04 + s * 0.016, root + d * 0.12 + s * 0.012, root + d * 0.12 - s * 0.012, root - d * 0.04 - s * 0.016,
        root + d * 0.05 + s * 0.008 + up * 0.22, root + d * 0.08 + s * 0.006 + up * 0.05,
        root + d * 0.08 - s * 0.006 + up * 0.05, root + d * 0.05 - s * 0.008 + up * 0.22,
    ), bevel=0.003)
    return kit.merge(f'Fin{i}', [shape], root)


def band(name, mat, base, profile, segments=32):
    """A ring round the cone (no caps over the open top): `profile` (radius, height)
    is a closed outline, swept round the vertical through `base`."""
    loop = list(profile) + [profile[0]]
    sections = [[base + Vector((math.cos(a) * r, math.sin(a) * r, z)) for r, z in loop]
                for a in (2 * math.pi * k / segments for k in range(segments + 1))]
    obj = nod.loft(name, sections, lambda i, k: mat)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def cone(m, root):
    """The reactor cone (concrete, returned first) and its ribs, bands and open top;
    origin on the deck."""
    base = Vector((0, 0, DECK))
    lip = CONE_HEIGHT
    profile = [(cone_radius(z), z) for z in (0, 0.3, 0.6, 0.9, lip)] + [(CONE_TOP - 0.05, lip), (CONE_TOP - 0.06, lip - 0.12)]
    shell = nod.concrete('Cone', [nod.lathe('ConeShell', m['steel'], profile, base, 32)], root, CONE_CONCRETE, base)
    parts = [
        # the dark shaft inside the open top
        cylinder('Shaft', m['dark'], CONE_TOP - 0.055, 0.01, base + Vector((0, 0, lip - 0.115)), segments=32, bevel=0),
        cylinder('ConeFoot', m['nplate_dark'], CONE_FOOT + 0.03, 0.06, base + Vector((0, 0, 0.03)), segments=32, bevel=0.006),
    ]
    for k in range(10):  # dark ribs from the foot up to the bands
        a = 2 * math.pi * (k + 0.5) / 10
        d = Vector((math.cos(a), math.sin(a), 0))
        lo, hi = 0.06, lip - 0.2
        parts.append(beam(f'Rib{k}', m['nplate'], base + d * (cone_radius(lo) + 0.006) + Vector((0, 0, lo)),
                          base + d * (cone_radius(hi) + 0.006) + Vector((0, 0, hi)), 0.024, 0.016))
    for i, z in enumerate((lip - 0.17, lip - 0.075)):  # the two thick red bands right under the rim
        lo, hi = z - 0.035, z + 0.035
        parts.append(band(f'Band{i}', m['remap'], base, ((cone_radius(lo) - 0.01, lo), (cone_radius(lo) + 0.022, lo), (cone_radius(lo) + 0.032, lo + 0.01),
                                                        (cone_radius(hi) + 0.032, hi - 0.01), (cone_radius(hi) + 0.022, hi), (cone_radius(hi) - 0.01, hi))))
    z = lip - 0.122
    parts.append(band('BandGap', m['nplate_dark'], base, ((cone_radius(z) - 0.01, z - 0.013), (cone_radius(z) + 0.018, z - 0.013),
                                                         (cone_radius(z) + 0.018, z + 0.013), (cone_radius(z) - 0.01, z + 0.013))))
    return shell, kit.merge('ConeDetails', parts, base)


def pipe_points():
    """The pipe from the cone's flank down to the generator (a quadratic curve)."""
    d = Vector((math.cos(PIPE_ANGLE), math.sin(PIPE_ANGLE), 0))
    start = d * (cone_radius(0.85) + 0.02) + Vector((0, 0, DECK + 0.85))
    foot = deck_edge(PIPE_ANGLE) - d * 0.12 + Vector((0, 0, DECK + 0.13))
    control = d * (CONE_FOOT + 0.3) + Vector((0, 0, DECK + 0.75))
    return start, control, foot


def bezier(a, c, b, t):
    return (1 - t) ** 2 * a + 2 * (1 - t) * t * c + t * t * b


def tube(name, mat, points, radius, segments=10):
    """A tube along a polyline (one cylinder per segment, overlapping a little)."""
    parts = []
    for k, (a, b) in enumerate(zip(points, points[1:])):
        part = cylinder(f'{name}_{k}', mat, radius, (b - a).length + radius * 0.6, (a + b) / 2, segments=segments, bevel=0)
        part.rotation_mode = 'QUATERNION'
        part.rotation_quaternion = (b - a).to_track_quat('Z', 'Y')
        parts.append(part)
    return parts


def pipe(m):
    """The thick pipe and a thin cable beside it, with clamps; origin at the cone."""
    start, control, foot = pipe_points()
    n = 14
    points = [bezier(start, control, foot, k / n) for k in range(n + 1)]
    side = Vector((-math.sin(PIPE_ANGLE), math.cos(PIPE_ANGLE), 0)) * 0.07
    thin = [p + side + Vector((0, 0, 0.01)) for p in points]
    parts = tube('Pipe', m['nsteel'], points, 0.042) + tube('Cable', m['nplate_dark'], thin, 0.016, 8)
    for t in (0.0, 0.3, 0.62):
        p, q = bezier(start, control, foot, t), bezier(start, control, foot, t + 0.03)
        ring = cylinder(f'Clamp{t}', m['nplate_dark'], 0.056, 0.04, p, segments=10, bevel=0)
        ring.rotation_mode = 'QUATERNION'
        ring.rotation_quaternion = (q - p).to_track_quat('Z', 'Y')
        parts.append(ring)
    return kit.merge('Pipe', parts, start)


def generator(m):
    """The generator on the deck's edge at the pipe's foot; origin at its foot."""
    d = Vector((math.cos(PIPE_ANGLE), math.sin(PIPE_ANGLE), 0))
    at = deck_edge(PIPE_ANGLE) - d * 0.12 + Vector((0, 0, DECK))
    rot = (0, 0, PIPE_ANGLE + math.pi / 2)
    parts = [
        box('GenBase', m['nplate_dark'], (0.3, 0.2, 0.05), at + Vector((0, 0, 0.025)), bevel=0.008, rotation=rot),
        cylinder('GenDrum', m['nplate'], 0.07, 0.24, at + Vector((0, 0, 0.11)), rotation=(math.pi / 2, 0, PIPE_ANGLE + math.pi / 2),
                 segments=16, bevel=0.006),
        box('GenStripe', m['remap'], (0.03, 0.16, 0.16), at + Vector((0, 0, 0.11)), bevel=0.004, rotation=rot),
        cylinder('GenCap', m['nsteel'], 0.05, 0.06, at + Vector((0, 0, 0.17)), segments=12, bevel=0.006),
    ]
    for s in (-1, 1):
        parts.append(cylinder(f'GenRib{s}', m['nplate_dark'], 0.076, 0.02, at + Vector((0, 0, 0.11)) + d.cross(Vector((0, 0, 1))) * 0.08 * s,
                              rotation=(math.pi / 2, 0, PIPE_ANGLE + math.pi / 2), segments=16, bevel=0))
    return kit.merge('Generator', parts, at)


def ring_glow(m, centre, radius, height, segments=32):
    """An open glowing band (a tube without caps) round `centre`; origin there."""
    ring = [Vector((math.cos(a) * radius, math.sin(a) * radius, 0)) for a in (2 * math.pi * k / segments for k in range(segments + 1))]
    sections = [[centre + p + Vector((0, 0, dz)) for p in ring] for dz in (-height / 2, height / 2)]
    obj = nod.loft('BandGlow', sections, lambda i, k: m['glow_red'])
    obj.data.transform(Matrix.Translation(-centre))
    obj.location = centre
    return obj


def build():
    root = nod.start('NodPowerPlant', 'NodPowerPlant', BUILD_END)
    m = nod.materials()
    m['glow_white'] = kit.material('GlowWhite', (0, 0, 0), 1.0, emission=kit.srgb('#fff2c8'), strength=3, alpha=0.25)
    keys = kit.keys

    # ---- the platform rises out of the ground
    group = kit.parent(kit.empty('PlatformGroup'), root)
    deck, details = platform(m, root)
    kit.parent(deck, group)
    kit.parent(details, deck)
    nod.rise(group, 0, 16, 0.24)
    # ---- the blades shoot out, the fins pop up
    for i, a in enumerate((200, 245, 285, 330, 40, 130)):
        obj = kit.parent(blade(m, i, math.radians(a)), group)
        kit.pop(obj, 14 + 2 * i, 7)
    for i, a in enumerate((215, 250, 290, 325)):
        obj = kit.parent(fin(m, i, math.radians(a)), group)
        kit.pop(obj, 44 + 2 * i, 6)

    # ---- the cone rises out of the deck (translation only: its lamps blink in Idle)
    cone_group = kit.parent(kit.empty('ConeGroup'), root)
    shell, cone_details = cone(m, root)
    kit.parent(shell, cone_group)
    kit.parent(cone_details, shell)
    low = Vector((0, 0, -(DECK + CONE_HEIGHT + 0.25)))
    keys(cone_group, 'location', {0: low, 12: low, 42: Vector((0, 0, 0.012)), 46: Vector((0, 0, 0))})

    # ---- the generator comes up out of the deck, the pipe grows down to it
    gen = kit.parent(generator(m), group)
    nod.rise(gen, 30, 10, 0.22)
    pipe_obj = kit.parent(pipe(m), shell)
    kit.pop(pipe_obj, 46, 10)

    # ---- the reactor's glow round the red bands (the original's NAPOWR_A)
    top = Vector((0, 0, DECK + CONE_HEIGHT))
    band_glow = kit.parent(ring_glow(m, top - Vector((0, 0, 0.12)), cone_radius(CONE_HEIGHT - 0.12) + 0.055, 0.2), shell)

    def throb(obj, lo, hi, axes, phase=0.0):
        base = Vector(obj.scale)
        frames = {}
        for f in range(0, kit.IDLE_END + 1, 3):
            t = (math.sin(2 * math.pi * (2 * f / kit.IDLE_END + phase)) + 1) / 2
            v = base.copy()
            for ax in axes:
                v[ax] = base[ax] * (lo + (hi - lo) * t)
            frames[f] = v
        frames[kit.IDLE_END] = frames[0]
        kit.keys(obj, 'scale', frames, 'LINEAR')

    idle = [(band_glow, lambda o: throb(o, 0.4, 1.0, (2,), 0.15))]

    # ---- lamps: white ones on the cone (as in the original), amber on the generator
    lights = []
    for k, (a, z) in enumerate(((250, 0.32), (300, 0.62), (20, 0.4), (330, 0.95))):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        at = d * (cone_radius(z) + 0.012) + Vector((0, 0, DECK + z - 0.03))
        housing, light = kit.beacon(f'ConeLamp{k}', m, at, 'white', m['lamp_white'])
        housing = kit.parent(kit.merge(f'ConeLamp{k}', [housing], at), shell)
        kit.parent(light, shell)
        kit.pop(housing, 54 + 2 * k, 5)
        lights.append((light, kit.flashes((k * 15, 6), (k * 15 + 30, 3))))
    d = Vector((math.cos(PIPE_ANGLE), math.sin(PIPE_ANGLE), 0))
    at = deck_edge(PIPE_ANGLE) - d * 0.12 + Vector((0, 0, DECK + 0.2))
    lights.append((nod.lamp(m, gen, 'GenLamp', at, 'amber', 52), kit.flashes((5, 4), (14, 4), (40, 6))))

    nod.clips(lights, idle)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, 'NAPOWR', {'Build': [BUILD_END // 3, 2 * BUILD_END // 3, BUILD_END], 'Idle': [0, 8, 15]},
             ortho=2.9, target=(0.0, -0.05, 0.55))
