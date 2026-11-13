"""
Tiberian Fallout – Nod Obelisk of Light (NAOBEL), after Tiberian Sun.

On two cells by two, like the original's (and Tiberian Sun Rising's remake of it): a
low, faceted dome of dark concrete panels on a flat footing, to the front left – dark
seams between the panels, a band of rivets round its skirt, two slatted vents and a
red (house colour) hexagonal plate with the Nod delta on its front. Round the dome's
back lies a great dark crescent blade with a red inner edge, like a sickle: its short
horn rises at the left, it curls round behind the obelisk, leaves the dome at the back
and sweeps out to the right, deep at its root and held by a sprung strut, and ends in
a point low over the ground. From a dark socket with a red band on the dome rises the
obelisk, leaning far to the back right over the blade: a segmented, squarish shaft of
grey concrete with dark collars, a slatted vent strip up its upper face and a dark head
whose prongs hold the red crystal, from whose tip the beam leaves.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel/NodArmour
dark plate (extra nodColour), Remap the house colour (the crystal too), Lamp*
emissive, Glow* additive.

Nodes:
    Flash        the glow at the crystal's tip, where the beam starts (shown in Fire;
                 the beam itself is drawn by the game)
    Tower        the leaning obelisk (static); in it TowerLift, which slides the shaft
                 up along its axis in Build
    CrystalGlow  the halo round the crystal (charges up in Fire)
    ChargeGlow   the glow over the vent strip (runs up the shaft in Fire)
    BandGlow     the glow round the red band at the foot (Idle, the original's NAOBEL_A)
    Blade        the crescent with its strut (rises and swings out in Build)
    DomeLamp…    red lamps on the dome
Animations (glTF clips)
    Build    one-shot, 2.4 s: the footing and the dome rise out of the ground, the
             blade comes up and swings out round the dome, the obelisk slides up out
             of its socket, the crystal out of its head
    Idle     loop, 2 s: the band at the foot glows up and fades, lamps blink
    Fire     one-shot, 1.2 s: a glow runs up the vent strip and the crystal charges
             (its halo swells and brightens), then discharges in a flash at the tip and
             falls back to rest

Run headless:

    blender -b --factory-startup --python blender/NAOBEL.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); origin in the middle on the ground.
"""
import math
import os
import sys

import bmesh
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
HIDDEN = kit.HIDDEN
UP = Vector((0, 0, 1))

BUILD_END = 72
FIRE_FRAMES = 36
FOOTING = 0.04                 # top of the footing
C = Vector((-0.18, -0.18, 0))  # the dome's middle (to the front left: the blade sweeps out round its back to the right)
FACETS = 10                    # the dome's sides; side k faces FRONT + k·36°
FRONT = 270.0                  # the first side faces the front (-y)
# the dome's tiers: from z0 to z1 the facets lean in from r0 to r1 (their distance from the middle)
TIERS = ((FOOTING, 0.3, 0.72, 0.62), (0.3, 0.43, 0.62, 0.44), (0.43, 0.48, 0.44, 0.38))
DOME_TOP = TIERS[-1][1]
# the crescent: from its short horn (degrees round the dome's middle, from +x) clockwise
# round the back to its point, BLADE_R from the dome's middle at both
BLADE_FROM, BLADE_TO = 215.0, 30.0
BLADE_R = (0.47, 1.25)
BLADE_W = 0.23                 # its thickness
BLADE_TOP, BLADE_TIP = 0.65, 0.15   # the height of its crest round the back and at the point
HORN = 0.16                    # the short horn, rising off the dome
TOP_FROM = 0.6                 # from here on the crest sinks to the point
LIFT_OFF = 0.55                # from here on the blade leaves the dome
STRUT_AT = 0.84                # where the strut holds it
# the obelisk leans that way (degrees from +x: to the back right, over the blade) by LEAN
LEAN_TO, LEAN = math.radians(64), math.radians(27)
D = Vector((math.cos(LEAN_TO), math.sin(LEAN_TO), 0))
SOCKET_TOP = DOME_TOP + 0.05
FOOT = C - D * 0.08 + Vector((0, 0, SOCKET_TOP - 0.02))   # the shaft's foot (in the socket)
LOW = (-0.3, 0.36, 0.38, 0.34)     # the shaft's lower segment: z0, z1 and its width at both (in its own frame)
HIGH = (0.44, 0.95, 0.33, 0.26)    # the upper one
SHAFT = 1.13                   # the top of its head
CRYSTAL = (SHAFT - 0.08, SHAFT + 0.44)   # the crystal's foot and tip
FOOT_CONCRETE = '#55565a'
DOME_CONCRETE = '#4a4b4f'
SHAFT_CONCRETE = '#7a7b7f'


# --------------------------------------------------------------------------- helpers

def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def ngon(r, c=C, n=FACETS):
    """A regular n-gon round c whose sides lie at distance r; side k faces FRONT + k·360/n°."""
    big = r / math.cos(math.pi / n)
    first = math.radians(FRONT)
    return [(c.x + big * math.cos(first + math.pi / n * (2 * k + 1)), c.y + big * math.sin(first + math.pi / n * (2 * k + 1))) for k in range(n)]


def facet(angle, z, lift=0.0):
    """The point of the dome at height z towards `angle` (degrees), lifted off its
    surface by `lift`, and the normal of the facet there."""
    z0, z1, r0, r1 = next((t for t in TIERS if z <= t[1] + 1e-6), TIERS[-1])
    step = 360 / FACETS
    side = FRONT + round((angle - FRONT) / step) * step   # the facet's own direction
    a, s = math.radians(angle), math.radians(side)
    out = Vector((math.cos(s), math.sin(s), 0))
    normal = (out + UP * (r0 - r1) / (z1 - z0)).normalized()
    r = (r0 + (r1 - r0) * (z - z0) / (z1 - z0)) / math.cos(a - s)
    return C + Vector((math.cos(a), math.sin(a), 0)) * r + UP * z + normal * lift, normal


def dome_height(r):
    """The dome's height at distance r from its middle (on a facet's middle line)."""
    if r <= TIERS[-1][3]:
        return DOME_TOP
    for z0, z1, r0, r1 in reversed(TIERS):
        if r <= r0:
            return z1 + (z0 - z1) * (r - r1) / (r0 - r1)
    return FOOTING


def place(obj, at, normal):
    """Puts a part built round the origin (its face looking up +z, its top towards +y)
    onto a surface at `at` looking along `normal` (its top up the slope)."""
    n = Vector(normal).normalized()
    x = UP.cross(n)
    x = x.normalized() if x.length > 1e-6 else Vector((1, 0, 0))
    y = n.cross(x)
    m = Matrix((x, y, n)).transposed().to_4x4()
    m.translation = at
    obj.matrix_world = m @ obj.matrix_world
    return obj


def along(obj, a, b):
    """Turns a cylinder (built along z) to lie from a to b."""
    a, b = Vector(a), Vector(b)
    obj.location = (a + b) / 2
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = (b - a).to_track_quat('Z', 'Y')
    return obj


def hexagon(r):
    """A hexagon with its points left and right, flat at top and bottom."""
    return [(r * math.cos(math.pi / 3 * k), r * math.sin(math.pi / 3 * k)) for k in range(6)]


def delta(s):
    """A triangle pointing up (the Nod delta), its corners s from the middle."""
    return [(0, s), (-s * 0.866, -s / 2), (s * 0.866, -s / 2)]


def square(w, c=0.28):
    """The shaft's section: a square of side w with chamfered corners."""
    return nb.chamfered(0, 0, w, w, w * c)


def rotated(points, angle, centre):
    ca, sa = math.cos(angle), math.sin(angle)
    return [(centre.x + (x - centre.x) * ca - (y - centre.y) * sa, centre.y + (x - centre.x) * sa + (y - centre.y) * ca) for x, y in points]


# --------------------------------------------------------------------------- footing and dome

def footing(m, root):
    """The flat footing (concrete, returned first) and the dirt round it."""
    body = nb.concrete('Footing', [nb.prism('FootingSlab', m['steel'], nb.chamfered(0, 0, 1.9, 1.9, 0.46),
                                            nb.chamfered(0, 0, 1.84, 1.84, 0.44), 0, FOOTING, bevel=0.006)], root, FOOT_CONCRETE)
    parts = [nb.prism('FootingDirt', m['dirt'], nb.chamfered(0, 0, 2.02, 2.02, 0.5), nb.chamfered(0, 0, 2.02, 2.02, 0.5), 0, 0.008, bevel=0)]
    # joints between the slabs (under the dome they go unseen)
    for k, (a, b) in enumerate((((0.42, -0.9), (0.42, 0.9)), ((-0.9, 0.42), (0.9, 0.42)), ((0.42, -0.42), (0.9, -0.42)), ((-0.42, 0.42), (-0.42, 0.9)))):
        a, b = Vector((*a, FOOTING)), Vector((*b, FOOTING))
        parts.append(beam(f'Joint{k}', m['nplate_dark'], a, b, 0.014, 0.006))
    return body, kit.merge('FootingDetails', parts)


def dome(m, root):
    """The faceted dome (concrete, returned first) and its details: seams, rivets,
    vents, the socket with its red band and the red plate on the front."""
    tiers = [nb.prism(f'DomeTier{i}', m['steel'], ngon(r0), ngon(r1), z0, z1, bevel=0.012) for i, (z0, z1, r0, r1) in enumerate(TIERS)]
    body = nb.concrete('Dome', tiers, root, DOME_CONCRETE)
    parts = []
    corner = 1 / math.cos(math.pi / FACETS)
    # seams up the corners of the two big tiers and round the tiers' edges
    for i, (z0, z1, r0, r1) in enumerate(TIERS[:2]):
        for k, (x, y) in enumerate(ngon(1.0, Vector((0, 0, 0)))):
            out = Vector((x, y, 0)).normalized()
            p0 = C + out * (r0 * corner + 0.002) + UP * (z0 + 0.012)
            p1 = C + out * (r1 * corner + 0.002) + UP * (z1 - 0.008)
            parts.append(beam(f'Seam{i}_{k}', m['nplate_dark'], p0, p1, 0.02, 0.014))
    for i, (z, r) in enumerate(((TIERS[0][1], TIERS[0][3]), (TIERS[1][1], TIERS[1][3]))):
        parts.append(nb.prism(f'SeamRing{i}', m['nplate_dark'], ngon(r + 0.012), ngon(r + 0.004), z - 0.012, z + 0.012, bevel=0))
    # the skirt's foot: a dark plate band all round
    parts.append(nb.prism('SkirtBand', m['nplate_dark'], ngon(TIERS[0][2] + 0.016), ngon(TIERS[0][2] - 0.008), FOOTING, FOOTING + 0.04, bevel=0.003))
    # rivets along the skirt's panels (not round the plate)
    for k in range(1, FACETS):
        angle = FRONT + k * 360 / FACETS
        for z, offsets in ((0.255, (-0.15, 0.0, 0.15)), (0.11, (-0.17, 0.17))):
            p, n = facet(angle, z)
            x = UP.cross(n).normalized()
            for j, off in enumerate(offsets):
                rivet = cylinder(f'Rivet{k}_{j}_{z}', m['nsteel'], 0.011, 0.012, (0, 0, 0), segments=6, bevel=0)
                parts.append(place(rivet, p + x * off, n))
    # slatted vents either side of the plate
    for angle in (FRONT - 36, FRONT + 36):
        p, n = facet(angle, 0.16, 0.004)
        parts.append(place(box(f'Vent{angle}', m['nplate_dark'], (0.22, 0.1, 0.014), (0, 0, 0), bevel=0.002), p, n))
        parts.append(place(box(f'Vent{angle}Hole', m['dark'], (0.19, 0.072, 0.016), (0, 0, 0.002), bevel=0), p, n))
        for j in range(3):
            parts.append(place(box(f'Vent{angle}Slat{j}', m['nsteel'], (0.19, 0.012, 0.02), (0, -0.024 + 0.024 * j, 0.004), bevel=0), p, n))
    # the red plate on the front with the Nod delta
    p, n = facet(FRONT, 0.17, 0.002)
    emblem = [nb.prism('PlateFrame', m['nplate_dark'], hexagon(0.16), hexagon(0.15), 0, 0.016, bevel=0.003),
              nb.prism('Plate', m['remap'], hexagon(0.14), hexagon(0.132), 0.008, 0.024, bevel=0.002),
              nb.prism('Delta', m['nplate_dark'], delta(0.085), delta(0.08), 0.02, 0.03, bevel=0),
              nb.prism('DeltaInner', m['remap'], delta(0.038), delta(0.035), 0.022, 0.034, bevel=0)]
    for k, (x, y) in enumerate(hexagon(0.152)):   # bolts in its corners
        emblem.append(cylinder(f'PlateBolt{k}', m['nsteel'], 0.01, 0.012, (x, y, 0.014), segments=6, bevel=0))
    parts += [place(obj, p, n) for obj in emblem]
    # the socket the obelisk stands in, turned with it, with its red band
    turn = LEAN_TO - math.pi / 2
    parts.append(nb.prism('Socket', m['nplate_dark'], rotated(nb.chamfered(FOOT.x, FOOT.y, 0.52, 0.52, 0.15), turn, FOOT),
                          rotated(nb.chamfered(FOOT.x, FOOT.y, 0.45, 0.45, 0.13), turn, FOOT), DOME_TOP - 0.03, SOCKET_TOP, bevel=0.006))
    parts.append(nb.prism('SocketBand', m['remap'], rotated(nb.chamfered(FOOT.x, FOOT.y, 0.55, 0.55, 0.16), turn, FOOT),
                          rotated(nb.chamfered(FOOT.x, FOOT.y, 0.54, 0.54, 0.16), turn, FOOT), DOME_TOP - 0.02, DOME_TOP + 0.025, bevel=0.002))
    return body, kit.merge('DomeDetails', parts)


# --------------------------------------------------------------------------- the crescent blade

def blade_radius(t):
    """The crescent's distance from the dome's middle at t (0 its short horn, 1 its point)."""
    return BLADE_R[0] + (BLADE_R[1] - BLADE_R[0]) * t ** 3


def blade_top(t):
    """The height of its crest: level round the back (the short horn a little higher), sinking to the point."""
    z = BLADE_TOP + 0.16 * (1 - smooth(t / HORN)) ** 1.5
    if t > TOP_FROM:
        z -= (BLADE_TOP - BLADE_TIP) * ((t - TOP_FROM) / (1 - TOP_FROM)) ** 1.5
    return z


def blade_bottom(t):
    """The height of its keel: in the dome up to LIFT_OFF (the horn's rising off it),
    then rising towards the point – a sickle, deep at its root."""
    seated = dome_height(blade_radius(min(t, LIFT_OFF))) - 0.03
    if t < HORN:
        return seated + (blade_top(t) - 0.02 - seated) * (1 - smooth(t / HORN)) ** 0.7
    if t <= LIFT_OFF:
        return seated
    deep = blade_top(LIFT_OFF) - seated
    return blade_top(t) - deep * (1 - ((t - LIFT_OFF) / (1 - LIFT_OFF)) ** 1.2)


def blade_width(t):
    w = BLADE_W * (0.08 + 0.92 * smooth(t / HORN) ** 0.6)
    if t > LIFT_OFF:
        w *= 1 - ((t - LIFT_OFF) / (1 - LIFT_OFF)) ** 2.6
    return w + 0.004


def blade_ring(t):
    """The crescent's section at t: a crested top over a keel, as points round it."""
    theta = math.radians(BLADE_FROM + (BLADE_TO - BLADE_FROM) * t)
    r = blade_radius(t)
    p = C + Vector((r * math.cos(theta), r * math.sin(theta), 0))
    # across the way: perpendicular to the spiral in plan, pointing away from the dome
    dr = 3 * (BLADE_R[1] - BLADE_R[0]) * t ** 2
    dtheta = math.radians(BLADE_TO - BLADE_FROM)
    tangent = Vector((dr * math.cos(theta) - r * dtheta * math.sin(theta), dr * math.sin(theta) + r * dtheta * math.cos(theta), 0)).normalized()
    out = tangent.cross(UP)
    if out.dot(p - C) < 0:
        out = -out
    top, bottom, w = blade_top(t), blade_bottom(t), blade_width(t)
    h = max(top - bottom, 0.006) / (SECTION[2][1] - SECTION[5][1])
    mid = top - SECTION[2][1] * h
    return [p + out * (u * w) + UP * (mid + v * h) for u, v in SECTION]


# the section (across, up) in units of width and depth; a crested top over a keel
SECTION = ((0.5, 0.0), (0.4, 0.28), (0.0, 0.36), (-0.4, 0.28), (-0.5, 0.0), (-0.14, -0.7), (0.14, -0.7))
TOP_FACES = (0, 1, 2, 3)       # the faces from the outer edge over the crest to the inner edge
RED_FACE = 3                   # the inner top edge (towards the obelisk): red
SEAMS = (0.22, 0.34, 0.46, 0.58, 0.7, 0.82)


def blade(m):
    """The crescent with its strut (origin at the dome's middle on the ground)."""
    ts = [i / 56 for i in range(57)]
    ts = [t for t in ts if all(abs(t - s) > 0.008 for s in SEAMS)]
    for s in SEAMS:
        ts += [s - 0.005, s + 0.005]
    ts.sort()
    seam_starts = {i for i, t in enumerate(ts) if any(abs(t - (s - 0.005)) < 1e-9 for s in SEAMS)}
    sections = []
    for t in ts:
        ring = blade_ring(t)
        sections.append(ring + [ring[0]])

    def material_of(i, k):
        if i in seam_starts or k == 5:
            return m['nplate_dark']
        if k == RED_FACE and 0.06 < ts[i] < 0.95:
            return m['remap']
        return m['armour'] if k in TOP_FACES else m['nplate']

    shell = nb.loft('BladeShell', sections, material_of, cap=m['nplate_dark'])
    # sharp along the blade (its section's corners), smooth round its curve
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    ring = len(SECTION) + 1
    for e in bm.edges:
        a, b = e.verts
        if a.index // ring != b.index // ring:
            e.smooth = False
    bm.to_mesh(shell.data)
    bm.free()
    parts = [shell]
    # the sprung strut between the dome's flank and the blade's underside
    ring = blade_ring(STRUT_AT)
    top = (ring[5] + ring[6]) / 2 + UP * 0.01
    angle = math.degrees(math.atan2((top - C).y, (top - C).x)) - 10
    foot, n = facet(angle, 0.14)
    axis = (top - foot).normalized()
    parts.append(along(cylinder('StrutHousing', m['nplate_dark'], 0.045, 1.0, (0, 0, 0), segments=10, bevel=0.003), foot - axis * 0.02, foot + axis * 0.1))
    parts[-1].scale = (1, 1, 0.12)
    parts.append(along(cylinder('StrutRod', m['nsteel_light'], 0.016, 1.0, (0, 0, 0), segments=8, bevel=0), foot, top))
    parts[-1].scale = (1, 1, (top - foot).length)
    for j in range(7):
        q = foot.lerp(top, 0.3 + 0.075 * j)
        parts.append(along(cylinder(f'StrutCoil{j}', m['nsteel'], 0.034, 1.0, (0, 0, 0), segments=10, bevel=0), q, q + axis * 0.014))
        parts[-1].scale = (1, 1, 0.014)
    parts.append(along(cylinder('StrutClevis', m['nplate_dark'], 0.032, 1.0, (0, 0, 0), segments=8, bevel=0.003), top - axis * 0.06, top))
    parts[-1].scale = (1, 1, 0.06)
    return kit.merge('Blade', parts, C)


# --------------------------------------------------------------------------- the obelisk

def width(z):
    """The upper segment's width at height z (in the shaft's frame)."""
    z0, z1, w0, w1 = HIGH
    return w0 + (w1 - w0) * (z - z0) / (z1 - z0)


def shaft(m, root):
    """The obelisk, built upright with its foot at the origin and its upper face
    (the one the lean turns to the sky) towards -y: concrete returned first, then the
    details and the crystal."""
    low = nb.prism('ShaftLow', m['steel'], square(LOW[2]), square(LOW[3]), LOW[0], LOW[1])
    high = nb.prism('ShaftHigh', m['steel'], square(HIGH[2]), square(HIGH[3]), HIGH[0], HIGH[1])
    body = nb.concrete('Shaft', [low, high], root, SHAFT_CONCRETE)
    parts = [
        # the collars between the segments and the red band round the lower one
        nb.prism('Collar', m['nplate_dark'], square(0.43), square(0.4), LOW[1] - 0.03, HIGH[0] + 0.03, bevel=0.005),
        nb.prism('CollarBand', m['remap'], square(0.44), square(0.435), LOW[1] + 0.005, LOW[1] + 0.04, bevel=0.002),
        nb.prism('CollarHigh', m['nplate_dark'], square(0.31), square(0.29), HIGH[1] - 0.04, HIGH[1] + 0.04, bevel=0.004),
        # the head holding the crystal, with a red trim
        nb.prism('Head', m['nplate'], square(0.27, 0.34), square(0.19, 0.34), HIGH[1] + 0.02, SHAFT, bevel=0.005),
        nb.prism('HeadTrim', m['remap'], square(0.275, 0.34), square(0.262, 0.34), HIGH[1] + 0.045, HIGH[1] + 0.07, bevel=0.002),
    ]
    # the joints of the upper segment's panels
    for j, z in enumerate((0.61, 0.78)):
        w = width(z)
        parts.append(nb.prism(f'Joint{j}', m['nplate_dark'], square(w + 0.014), square(w + 0.012), z - 0.011, z + 0.011, bevel=0))
    # the vent strip up the upper face: a dark frame, the slot, steel slats
    z0, z1 = HIGH[0] + 0.06, HIGH[1] - 0.07
    y0, y1 = -width(z0) / 2, -width(z1) / 2
    parts.append(kit.hexahedron('VentFrame', m['nplate_dark'], (
        (-0.07, y0 - 0.012, z0), (0.07, y0 - 0.012, z0), (0.07, y0 + 0.02, z0), (-0.07, y0 + 0.02, z0),
        (-0.07, y1 - 0.012, z1), (0.07, y1 - 0.012, z1), (0.07, y1 + 0.02, z1), (-0.07, y1 + 0.02, z1)), bevel=0.003))
    parts.append(kit.hexahedron('VentSlot', m['dark'], (
        (-0.052, y0 - 0.016, z0 + 0.02), (0.052, y0 - 0.016, z0 + 0.02), (0.052, y0, z0 + 0.02), (-0.052, y0, z0 + 0.02),
        (-0.052, y1 - 0.016, z1 - 0.02), (0.052, y1 - 0.016, z1 - 0.02), (0.052, y1, z1 - 0.02), (-0.052, y1, z1 - 0.02)), bevel=0))
    for j in range(10):
        z = z0 + 0.04 + (z1 - z0 - 0.08) * j / 9
        parts.append(box(f'VentSlat{j}', m['nsteel'], (0.104, 0.012, 0.013), (0, -width(z) / 2 - 0.016, z), bevel=0))
    # dark spines up the other faces
    for name, (sx, sy) in (('SpineX', (1, 0)), ('SpineXn', (-1, 0)), ('SpineY', (0, 1))):
        a, b = HIGH[0] + 0.05, HIGH[1] - 0.05
        pa = Vector((sx * (width(a) / 2 + 0.006), sy * (width(a) / 2 + 0.006), a))
        pb = Vector((sx * (width(b) / 2 + 0.006), sy * (width(b) / 2 + 0.006), b))
        parts.append(beam(name, m['nplate_dark'], pa, pb, 0.045, 0.018))
    # ports on the lower segment's side towards the camera
    for j, z in enumerate((0.08, 0.23)):
        half = (LOW[2] + (LOW[3] - LOW[2]) * (z - LOW[0]) / (LOW[1] - LOW[0])) / 2
        parts.append(box(f'Port{j}', m['dark'], (0.016, 0.11, 0.055), (half, 0, z), bevel=0.002))
        parts.append(box(f'PortLid{j}', m['nplate_dark'], (0.014, 0.13, 0.014), (half + 0.004, 0, z + 0.036), bevel=0))
    # rivets round the lower collar
    for s in (-1, 1):
        for j, off in enumerate((-0.11, 0.0, 0.11)):
            z = HIGH[0] + 0.005
            parts.append(cylinder(f'CollarRivetX{s}{j}', m['nsteel'], 0.01, 0.012, (s * 0.212, off, z), rotation=(0, math.pi / 2, 0), segments=6, bevel=0))
            parts.append(cylinder(f'CollarRivetY{s}{j}', m['nsteel'], 0.01, 0.012, (off, s * 0.212, z), rotation=(math.pi / 2, 0, 0), segments=6, bevel=0))
    # the prongs of the head, rising either side of the crystal
    for s in (-1, 1):
        b, t = SHAFT - 0.1, SHAFT + 0.18
        parts.append(kit.hexahedron(f'Prong{s}', m['nplate_dark'], (
            (s * 0.055, -0.04, b), (s * 0.125, -0.04, b), (s * 0.125, 0.04, b), (s * 0.055, 0.04, b),
            (s * 0.047, -0.018, t), (s * 0.07, -0.018, t), (s * 0.07, 0.018, t), (s * 0.047, 0.018, t)), bevel=0.004))
    details = kit.merge('ShaftDetails', parts)
    # the crystal: a long six-sided red point on a short one, a small shard at its side
    lo, tip = CRYSTAL
    mid = lo + 0.1

    def section(rx, ry):
        return [(rx * math.cos(math.pi / 3 * k), ry * math.sin(math.pi / 3 * k)) for k in range(6)]

    shard = nb.prism('CrystalShard', m['remap'], section(0.034, 0.03), section(0.003, 0.003), 0, 0.2, bevel=0.002)
    shard.rotation_euler = (0, math.radians(-16), 0)
    shard.location = (-0.028, 0.03, mid - 0.04)
    crystal = kit.merge('Crystal', [nb.prism('CrystalLow', m['remap'], section(0.03, 0.025), section(0.082, 0.068), lo, mid, bevel=0.002),
                                    nb.prism('CrystalHigh', m['remap'], section(0.082, 0.068), section(0.004, 0.003), mid, tip, bevel=0.002),
                                    shard], Vector((0, 0, lo)))
    return body, details, crystal


# --------------------------------------------------------------------------- build

def build():
    root = nb.start('NodObelisk', 'NodObelisk', BUILD_END)
    m = nb.materials()
    keys = kit.keys

    # ---- the footing and the dome rise out of the ground
    base, dirt = footing(m, root)
    kit.parent(base, root)
    kit.parent(dirt, base)
    nb.rise(base, 0, 8, FOOTING + 0.02)
    dome_group = kit.parent(kit.empty('DomeGroup'), root)
    body, details = dome(m, root)
    kit.parent(body, dome_group)
    kit.parent(details, body)
    nb.rise(dome_group, 4, 18, DOME_TOP + 0.08)

    # ---- the blade comes up out of the dome and swings out round it
    crescent = kit.parent(blade(m), dome_group)
    rest = Vector(crescent.location)
    keys(crescent, 'location', {0: rest - UP * 0.8, 18: rest - UP * 0.8, 34: rest + UP * 0.01, 38: rest})
    turned = Euler((0, 0, math.radians(80)))
    keys(crescent, 'rotation_euler', {0: turned, 18: turned, 37: Euler((0, 0, math.radians(-3))), 41: Euler((0, 0, 0))})

    # ---- the obelisk, built upright at the origin, then stood in its socket and leant over
    tower = kit.parent(kit.empty('Tower'), root)
    lift = kit.parent(kit.empty('TowerLift'), tower)
    sbody, sdetails, crystal = shaft(m, root)
    kit.parent(sbody, lift)
    kit.parent(sdetails, sbody)
    holder = kit.parent(kit.empty('CrystalHolder', (0, 0, CRYSTAL[0])), lift)
    kit.parent(crystal, holder)
    tip = Vector((0, 0, CRYSTAL[1]))
    halo = kit.parent(kit.merge('CrystalGlow', [sphere('CrystalHalo', m['glow_red'], 0.06, tip - Vector((0, 0, 0.17)), 14)], tip - Vector((0, 0, 0.17))), holder)
    halo.scale = (0.75, 0.75, 1.8)
    flash = kit.parent(nb.glow(m, 'Flash', tip, 0.07, 'glow_laser', balls=1), holder)
    # the glow over the vent strip, grows from its foot in Fire
    z0, z1 = HIGH[0] + 0.07, HIGH[1] - 0.08
    y0, y1 = -width(z0) / 2, -width(z1) / 2
    charge = kit.parent(kit.merge('ChargeGlow', [kit.hexahedron('ChargeStrip', m['glow_red'], (
        (-0.065, y0 - 0.03, z0), (0.065, y0 - 0.03, z0), (0.065, y0 - 0.005, z0), (-0.065, y0 - 0.005, z0),
        (-0.065, y1 - 0.03, z1), (0.065, y1 - 0.03, z1), (0.065, y1 - 0.005, z1), (-0.065, y1 - 0.005, z1)), bevel=0)], Vector((0, y0, z0))), lift)
    tower.location = FOOT
    tower.rotation_euler = Euler((-LEAN, 0, LEAN_TO - math.pi / 2))

    # Build: the obelisk slides up out of its socket along its axis, the crystal out of its head
    low = Vector((0, 0, -(SHAFT + 0.5)))
    keys(lift, 'location', {0: low, 24: low, 52: Vector((0, 0, 0.01)), 56: Vector((0, 0, 0))})
    sunk = Vector((0, 0, -(CRYSTAL[1] - CRYSTAL[0])))
    rest = Vector(holder.location)
    keys(holder, 'location', {0: rest + sunk, 54: rest + sunk, 66: rest + Vector((0, 0, 0.01)), 69: rest})
    flash.scale = Vector((HIDDEN,) * 3)
    charge.scale = Vector((HIDDEN,) * 3)

    # lamps on the dome's upper tier
    lights = []
    for k, angle in enumerate((FRONT + 72, FRONT - 72)):
        p, _ = facet(angle, 0.35)
        lights.append((nb.lamp(m, body, f'DomeLamp{k}', tuple(p), 'red', 44 + 4 * k), kit.flashes((k * 30, 8))))

    # Idle: the band at the foot glows up and fades
    turn = LEAN_TO - math.pi / 2
    band = kit.parent(kit.merge('BandGlow', [nb.prism('BandHalo', m['glow_red'], rotated(nb.chamfered(FOOT.x, FOOT.y, 0.62, 0.62, 0.19), turn, FOOT),
                                                      rotated(nb.chamfered(FOOT.x, FOOT.y, 0.56, 0.56, 0.17), turn, FOOT),
                                                      DOME_TOP - 0.03, DOME_TOP + 0.05, bevel=0)],
                                Vector((FOOT.x, FOOT.y, DOME_TOP - 0.03))), body)

    def throb(obj):
        frames = {}
        for f in range(0, kit.IDLE_END + 1, 3):
            t = (math.sin(2 * math.pi * f / kit.IDLE_END) + 1) / 2
            frames[f] = Vector((1, 1, 0.35 + 0.65 * t))
        frames[kit.IDLE_END] = frames[0]
        kit.keys(obj, 'scale', frames, 'LINEAR')

    nb.clips(lights, [(band, throb)])

    # Fire: a glow runs up the vent strip, the crystal charges, then discharges at the tip
    hidden = Vector((HIDDEN,) * 3)
    keys(charge, 'scale', {0: hidden, 1: Vector((1, 1, 0.05)), 20: Vector((1, 1, 1)), 24: Vector((1.15, 1.3, 1)), 26: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
    kit.to_track(charge, 'Fire')
    s = Vector(halo.scale)
    keys(halo, 'scale', {0: s, 22: s * 2.1, 26: s * 2.4, 30: s * 0.7, FIRE_FRAMES: s}, 'LINEAR')
    kit.to_track(halo, 'Fire')
    keys(flash, 'scale', {0: hidden, 25: hidden, 26: Vector((1, 1, 1)), 28: Vector((1.6, 1.6, 1.6)), 32: Vector((0.8, 0.8, 0.8)), 33: hidden,
                          FIRE_FRAMES: hidden}, 'CONSTANT')
    kit.to_track(flash, 'Fire')
    charge.scale = hidden
    halo.scale = s
    flash.scale = hidden
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAOBEL', {'Build': [20, 30, 44, 60, BUILD_END], 'Idle': [0, 15], 'Fire': [12, 24, 28]}, ortho=3.2, target=(0, 0.1, 0.75))
