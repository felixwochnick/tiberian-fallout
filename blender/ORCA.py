"""
Tiberian Fallout – GDI Orca fighter (ORCA), after Tiberian Sun.

A VTOL fighter with a long, slim fuselage. In front an angular, faceted cockpit: a
wedge nose under a dark glass canopy (sloped side panes, a light frame along its
edges, two red lamps at the chin). Behind it a raised deck with an intake grille and
a hatch, the fuselage sides carry two boxy pods with a rocket launcher in their
fronts (four red-tipped rockets each, a vent above); behind the pods the two round
engines on short shafts (fan intakes, glowing nozzles, house-colour bands, navigation
lights, red left, green right): level when landed, they swing nose up into the hover
position in flight, their round openings facing down. A long tail boom ends in an H
tail: a swept stabiliser with a vertical fin at each tip (house-colour tips). A dark
keel under the belly, three gear legs with pads.

The fuselage, pods and engines wear the light camouflage of GDI (baked, tinted with
the house colour in the game: GAPILE.camo_material).

Nodes for the game: "Flash" (the rockets' muzzle flash at both launchers, its origin
between them); the engines turn on "Engine-1"/"Engine1".

Clips (see aircraft.py)
    Idle     loop, 2 s: landed, gear out, engines off and level
    TakeOff  once, 1 s: the engines light up and swing into the hover position, the
             gear comes in
    Fly      loop, 1 s: engines glowing in the hover position, a gentle sway
    Land     once, 1 s: the gear goes out, the engines swing back level and go out
    Fire     once, 0.4 s: two rocket salvoes flash at the launchers (Fly pose)

The faceted hull helpers (section_loft, outset, canopy, ring) and the engine
(nacelle) are shared with ORCAB.py and TRNSPORT.py.

Run headless:

    blender -b --factory-startup --python blender/ORCA.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle; landed, the gear's pads touch Z = 0.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import aircraft as air  # noqa: E402
import detail  # noqa: E402

OUT = os.path.join(air.PROJECT, 'public', 'models', 'ORCA.glb')
BLEND = os.path.join(HERE, 'ORCA.blend')

BELLY = 0.12                       # underside of the keel, landed (top of the gear)
ENGINE = Vector((0.245, 0.15, 0.215))  # pivot of the right engine (x mirrored for the left)
NACELLE = (0.072, 0.15)            # radius, length
TILT_HOVER = -75                   # degrees about x: the nozzles swing down
LAUNCHER = Vector((0.152, -0.165, 0.215))  # middle of the right rocket launcher's face
FLASH_AT = Vector((0, LAUNCHER.y - 0.02, LAUNCHER.z))
FIRE_FRAMES = 12

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
HIDDEN = kit.HIDDEN

# y, right half of the cross section (x, z) from the bottom up: the wedge nose, the
# cockpit, the middle and the start of the boom
HULL = (
    (-0.57, ((0.012, 0.172), (0.02, 0.18), (0.02, 0.19), (0.012, 0.196))),
    (-0.52, ((0.035, 0.155), (0.062, 0.165), (0.066, 0.2), (0.04, 0.226))),
    (-0.42, ((0.06, 0.14), (0.1, 0.15), (0.108, 0.235), (0.058, 0.298))),
    (-0.3, ((0.066, 0.14), (0.112, 0.15), (0.118, 0.255), (0.062, 0.336))),
    (-0.17, ((0.066, 0.14), (0.112, 0.15), (0.12, 0.265), (0.072, 0.346))),
    (0.1, ((0.066, 0.14), (0.11, 0.15), (0.118, 0.265), (0.075, 0.346))),
    (0.21, ((0.045, 0.17), (0.075, 0.18), (0.08, 0.27), (0.05, 0.34))),
)
CANOPY = range(1, 5)   # the hull sections the glass runs over (upper sides and top)
BOOM = (
    (0.17, ((0.03, 0.215), (0.052, 0.232), (0.058, 0.31), (0.036, 0.34))),
    (0.5, ((0.016, 0.283), (0.026, 0.291), (0.028, 0.33), (0.018, 0.345))),
    (0.6, ((0.012, 0.298), (0.02, 0.304), (0.02, 0.334), (0.012, 0.343))),
)
TAIL_SPAN = 0.25       # the fins stand at x = ±TAIL_SPAN
FIN = ((0.5, 0.615, 0.29), (0.592, 0.628, 0.49))  # leading and trailing edge y, z: at the root, at the top


def section_loft(name, mat, sections, skin=False):
    """A faceted hull through cross sections (y, half): `half` the right half of the
    outline, (x, z) points from the bottom up (x > 0), mirrored to the left; capped at
    both ends. skin: an open skin over the outline only (no strip along the bottom, no
    caps) – a canopy laid over a hull."""
    def build(bm):
        rings = []
        for y, half in sections:
            right = [(x, y, z) for x, z in half]
            left = [(-x, y, z) for x, z in reversed(half)]
            rings.append([bm.verts.new(p) for p in right + left])
        n = len(rings[0])
        for a, b in zip(rings, rings[1:]):
            for i in range(n - 1 if skin else n):
                j = (i + 1) % n
                bm.faces.new((a[i], a[j], b[j], b[i]))
        if not skin:
            bm.faces.new(rings[0])
            bm.faces.new(list(reversed(rings[-1])))

    obj = kit.mesh_object(name, build)
    kit.finish(obj, mat, 0)
    for poly in obj.data.polygons:
        poly.use_smooth = False  # faceted armour plates
    return obj


def ring(name, mat, centre, inner, outer, height, segments=24, rotation=(0, 0, 0)):
    """An open ring (a duct) round the vertical through `centre`, turned by `rotation`;
    flat shaded."""
    def build(bm):
        rings = []
        for r in (inner, outer):
            for z in (-height / 2, height / 2):
                rings.append([bm.verts.new((r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments), z))
                              for k in range(segments)])
        ib, it, ob, ot = rings
        for k in range(segments):
            j = (k + 1) % segments
            bm.faces.new((ib[k], ib[j], it[j], it[k]))
            bm.faces.new((ob[k], ot[k], ot[j], ob[j]))
            bm.faces.new((it[k], it[j], ot[j], ot[k]))
            bm.faces.new((ib[k], ob[k], ob[j], ib[j]))

    obj = kit.mesh_object(name, build)
    obj.location = centre
    obj.rotation_euler = rotation
    kit.finish(obj, mat, 0)
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def outset(half, d):
    """The half outline of a section pushed out by d (glass and frames over a hull)."""
    points = [Vector((-half[0][0], half[0][1]))] + [Vector(p) for p in half] + [Vector((-half[-1][0], half[-1][1]))]
    out = []
    for a, p, b in zip(points, points[1:], points[2:]):
        n = (Vector(((p - a).y, -(p - a).x)).normalized() + Vector(((b - p).y, -(b - p).x)).normalized()).normalized()
        out.append(tuple(p + n * d))
    return out


def canopy(name, m, sections, rows, d=0.004, frame=0.009):
    """The glass over the upper outline points `rows` (indices into the half outline)
    of the hull sections, and a light frame along its edges, ridges and section lines."""
    glass = [(y, outset(half, d)[rows[0]:rows[-1] + 1]) for y, half in sections]
    parts = [section_loft(f'{name}Glass', m['glass'], glass, skin=True)]
    framed = [(y, outset(half, d + 0.003)) for y, half in sections]
    for s in (-1, 1):
        for k in rows:  # along the edges and ridges
            for (y0, a), (y1, b) in zip(framed, framed[1:]):
                parts.append(beam(f'{name}Rail{s}{k}{y0}', m['frame'], (s * a[k][0], y0, a[k][1]), (s * b[k][0], y1, b[k][1]), frame, frame))
    for y, points in framed:  # across, at each section
        row = [Vector((x, y, z)) for x, z in points[rows[0]:rows[-1] + 1]]
        row = row + [Vector((-p.x, p.y, p.z)) for p in reversed(row)]
        for k, (a, b) in enumerate(zip(row, row[1:])):
            parts.append(beam(f'{name}Bow{y}{k}', m['frame'], a, b, frame, frame))
    return parts


def fin(name, mat, s, z0, z1, half, bevel=0.0):
    """The fin at the tip of the stabiliser on side s (or its part from z0 to z1), swept
    back to a pointed top; `half` its half thickness."""
    (a0, b0, r0), (a1, b1, r1) = FIN
    x0, x1 = s * (TAIL_SPAN - half), s * (TAIL_SPAN + half)
    corners = []
    for z in (z0, z1):
        t = (z - r0) / (r1 - r0)
        a, b = a0 + (a1 - a0) * t, b0 + (b1 - b0) * t
        corners += [(x0, a, z), (x1, a, z), (x1, b, z), (x0, b, z)]
    return kit.hexahedron(name, mat, corners, bevel)


def materials():
    m = kit.materials()
    m.update({
        'glass': material('Canopy', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'frame': material('CanopyFrame', srgb('#b8bcbf'), 0.35, 0.8),
        'red': material('WarningRed', srgb('#b3271c'), 0.6),
        'nozzle': material('GlowNozzle', srgb('#3a4048'), 0.5, emission=srgb('#8fd0ff'), strength=4),
        'plume': material('GlowPlume', (0, 0, 0), 1.0, emission=srgb('#9fd4ff'), strength=3, alpha=0.35),
        'flash': material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7),
    })
    return m


def camo(obj, root, name):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{name}', root))
    return obj


def hull(m, root):
    """Fuselage, boom, side pods and tail in camouflage (one object) and their details."""
    pods = []
    for s in (-1, 1):
        # a boxy pod on each side, its top sloping into the fuselage's flank
        pods.append(kit.hexahedron(f'Pod{s}', m['sand'], (
            (s * 0.1, -0.165, 0.155), (s * 0.205, -0.155, 0.165), (s * 0.205, 0.055, 0.175), (s * 0.1, 0.055, 0.165),
            (s * 0.1, -0.145, 0.292), (s * 0.198, -0.135, 0.272), (s * 0.198, 0.045, 0.272), (s * 0.1, 0.045, 0.292)), bevel=0))
        # the H tail: half the swept stabiliser and the fin at its tip
        pods.append(kit.hexahedron(f'Stabiliser{s}', m['sand'], (
            (0, 0.44, 0.326), (s * TAIL_SPAN, 0.52, 0.326), (s * TAIL_SPAN, 0.6, 0.326), (0, 0.6, 0.326),
            (0, 0.44, 0.342), (s * TAIL_SPAN, 0.52, 0.338), (s * TAIL_SPAN, 0.6, 0.338), (0, 0.6, 0.342)), bevel=0))
        pods.append(fin(f'Fin{s}', m['sand'], s, FIN[0][2], FIN[1][2], 0.007))
    shell = kit.merge('Hull', [
        section_loft('Fuselage', m['sand'], HULL),
        section_loft('Boom', m['sand'], BOOM),
        *pods,
    ])
    for poly in shell.data.polygons:
        poly.use_smooth = False
    camo(shell, root, 'Hull')

    deck = 0.346
    parts = [
        *canopy('Canopy', m, [HULL[k] for k in CANOPY], (2, 3)),
        # dark keel under the belly
        section_loft('Keel', m['steel'], (
            (-0.44, ((0.03, 0.148), (0.045, 0.156))), (-0.36, ((0.05, BELLY), (0.07, 0.145))),
            (0.1, ((0.05, BELLY), (0.07, 0.145))), (0.2, ((0.03, 0.165), (0.045, 0.178))))),
        # the raised deck behind the canopy: intake grille, hatch, seams
        kit.hexahedron('Deck', m['sand_light'], (
            (-0.07, -0.16, deck - 0.004), (0.07, -0.16, deck - 0.004), (0.07, 0.19, deck - 0.004), (-0.07, 0.19, deck - 0.004),
            (-0.06, -0.12, deck + 0.018), (0.06, -0.12, deck + 0.018), (0.06, 0.17, deck + 0.018), (-0.06, 0.17, deck + 0.018)), bevel=0.004),
        box('IntakeFrame', m['steel'], (0.08, 0.085, 0.01), (0, -0.065, deck + 0.02), bevel=0.002),
        *[box(f'IntakeSlat{k}', m['dark'], (0.068, 0.009, 0.012), (0, -0.098 + 0.016 * k, deck + 0.022), bevel=0) for k in range(5)],
        box('Hatch', m['sand'], (0.07, 0.07, 0.008), (0, 0.06, deck + 0.021), bevel=0.003),
        *detail.seam('HatchSeam', m['dark'], (-0.036, 0.024, deck + 0.026), (0.036, 0.024, deck + 0.026), 0.004, 0.003),
        *detail.seam('DeckSeam', m['dark'], (-0.058, 0.115, deck + 0.019), (0.058, 0.115, deck + 0.019), 0.004, 0.003),
        box('BoomStripe', m['remap'], (0.068, 0.045, 0.012), (0, 0.27, 0.335), bevel=0.003),
        box('StabiliserBand', m['remap'], (0.12, 0.03, 0.02), (0, 0.565, 0.334), bevel=0.003),
        # the little fan in the root of the stabiliser
        cylinder('TailFanRim', m['steel'], 0.032, 0.012, (0, 0.53, 0.346), segments=16, bevel=0.002),
        cylinder('TailFan', m['dark'], 0.024, 0.014, (0, 0.53, 0.346), segments=16, bevel=0),
        box('TailLight', m['lamp_white'], (0.016, 0.012, 0.012), (0, 0.602, 0.322), bevel=0),
        beam('Antenna', m['steel'], (0.025, 0.24, 0.338), (0.035, 0.31, 0.43), 0.006),
        *detail.lamp('Beacon', m['dark'], m['lamp_red'], (0, 0.15, deck + 0.025), (0, 0, 1), 0.011),
    ]
    for s in (-1, 1):
        x = s * LAUNCHER.x
        parts += [
            # red lamps at the chin, as on the icon
            *detail.lamp(f'ChinLamp{s}', m['dark'], m['lamp_red'], (s * 0.04, -0.5, 0.16), (0, -1, -0.4), 0.011),
            # a house-colour stripe under the canopy (along the flank narrowing to the nose), a step
            box(f'CheekStripe{s}', m['remap'], (0.008, 0.25, 0.016), (s * 0.1115, -0.295, 0.205), bevel=0.002,
                rotation=(0, 0, -s * math.atan2(0.011, 0.25))),
            box(f'Step{s}', m['steel'], (0.008, 0.03, 0.01), (s * 0.114, -0.22, 0.16), bevel=0),
            # vent slats on the pod's top
            *[box(f'PodSlat{s}{k}', m['dark'], (0.06, 0.008, 0.008), (s * 0.15, -0.09 + 0.018 * k, 0.284), bevel=0) for k in range(4)],
            # the rocket launcher in the pod's front: four tubes, red rocket tips; a vent above
            box(f'Launcher{s}', m['steel'], (0.088, 0.03, 0.086), (x, LAUNCHER.y + 0.01, LAUNCHER.z), bevel=0.006),
            *[cylinder(f'Tube{s}{k}', m['dark'], 0.016, 0.012, (x + (k % 2 - 0.5) * 0.04, LAUNCHER.y - 0.006, LAUNCHER.z + (k // 2 - 0.5) * 0.04),
                       rotation=(math.pi / 2, 0, 0), segments=10, bevel=0) for k in range(4)],
            *[cylinder(f'Rocket{s}{k}', m['red'], 0.011, 0.016, (x + (k % 2 - 0.5) * 0.04, LAUNCHER.y - 0.01, LAUNCHER.z + (k // 2 - 0.5) * 0.04),
                       rotation=(math.pi / 2, 0, 0), segments=8, bevel=0, radius2=0.004) for k in range(4)],
            *detail.grille(f'PodVent{s}', m['steel'], m['dark'], (x, -0.152, 0.272), 0.06, 0.022, 'Y', slats=3, depth=0.01),
            box(f'PodBand{s}', m['remap'], (0.008, 0.035, 0.1), (s * 0.206, -0.1, 0.22), bevel=0.002),
            *detail.rivets(f'PodRivets{s}', m['steel'], (s * 0.201, -0.06, 0.255), (s * 0.201, 0.035, 0.255), 5, 0.005, 'X'),
            *detail.rivets(f'PodRivetsLow{s}', m['steel'], (s * 0.205, -0.06, 0.185), (s * 0.205, 0.035, 0.185), 5, 0.005, 'X'),
            box(f'PodPanel{s}', m['sand_light'], (0.006, 0.08, 0.05), (s * 0.203, -0.01, 0.22), bevel=0.002),
            # the shaft the engine swings on
            cylinder(f'Shaft{s}', m['steel'], 0.022, 0.08, (s * 0.14, ENGINE.y, ENGINE.z), rotation=(0, math.pi / 2, 0), segments=12, bevel=0.003),
            box(f'ShaftFairing{s}', m['sand_light'], (0.05, 0.07, 0.05), (s * 0.115, ENGINE.y, ENGINE.z), bevel=0.012),
            # the fin's house-colour tip
            fin(f'FinTip{s}', m['remap'], s, FIN[1][2] - 0.045, FIN[1][2] + 0.003, 0.009, 0.002),
            *detail.lamp(f'FinLight{s}', m['dark'], m['lamp_green' if s > 0 else 'lamp_red'], (s * (TAIL_SPAN + 0.008), 0.55, 0.33), (s, 0, 0), 0.008),
        ]
    return shell, kit.merge('HullDetails', parts)


def nacelle(m, root, s, centre=ENGINE, size=NACELLE, plume_length=0.26):
    """An engine (round, a fan in its intake) around its pivot `centre` (mirrored to
    side s); returns the pivot, the joint's parts and the glow objects. Shared with
    ORCAB.py."""
    pivot = Vector((s * centre.x, centre.y, centre.z))
    r, length = size
    u = r / NACELLE[0]  # small parts grow with the engine
    along = (math.pi / 2, 0, 0)
    front, back = pivot.y - length / 2, pivot.y + length / 2
    shell = kit.merge(f'Nacelle{s}', [
        cylinder(f'NacelleBody{s}', m['sand'], r, length, pivot, rotation=along, segments=16, bevel=0.008 * u),
        cylinder(f'NacelleLip{s}', m['sand'], r * 0.9, 0.02 * u, Vector((pivot.x, front - 0.01 * u, pivot.z)), rotation=along, segments=16,
                 bevel=0.004, radius2=r),
    ], pivot)
    camo(shell, root, f'Nacelle{s}')
    fan_at = Vector((pivot.x, front - 0.016 * u, pivot.z))
    rays = [Vector((math.cos(a), 0, math.sin(a))) for a in (2 * math.pi * (k + 0.5) / 8 for k in range(8))]
    parts = [
        cylinder(f'Intake{s}', m['dark'], r * 0.78, 0.008 * u, fan_at, rotation=along, segments=16, bevel=0),
        cylinder(f'Spinner{s}', m['steel_light'], r * 0.22, 0.03 * u, fan_at - Vector((0, 0.008 * u, 0)), rotation=along, segments=10,
                 bevel=0.004, radius2=r * 0.08),
        *[beam(f'FanBlade{s}{k}', m['steel'], fan_at + d * r * 0.2 - Vector((0, 0.002, 0)), fan_at + d * r * 0.74 - Vector((0, 0.002, 0)),
               0.018 * u, 0.004) for k, d in enumerate(rays)],
        cylinder(f'NozzleRim{s}', m['steel'], r * 0.95, 0.03 * u, Vector((pivot.x, back + 0.01 * u, pivot.z)), rotation=along, segments=16,
                 bevel=0.003, radius2=r * 0.8),
        *[beam(f'NozzleVane{s}{k}', m['dark'], Vector((pivot.x - r * 0.62, back + 0.024 * u, pivot.z + dz * r)),
               Vector((pivot.x + r * 0.62, back + 0.024 * u, pivot.z + dz * r)), 0.008 * u, 0.012 * u) for k, dz in enumerate((-0.35, 0.0, 0.35))],
        cylinder(f'Band{s}', m['remap'], r + 0.003, 0.2 * length, Vector((pivot.x, pivot.y + 0.23 * length, pivot.z)), rotation=along, segments=16,
                 bevel=0.003),
        cylinder(f'Hub{s}', m['steel_light'], 0.03 * u, 0.012, pivot - Vector((s * (r + 0.002), 0, 0)), rotation=(0, math.pi / 2, 0), segments=12,
                 bevel=0.002),
        *detail.rivets(f'Rivets{s}', m['steel'], pivot + Vector((0, -0.37 * length, r + 0.002)), pivot + Vector((0, 0.07 * length, r + 0.002)), 4,
                       0.005, 'Z'),
        *detail.seam(f'NacelleSeam{s}', m['dark'], pivot + Vector((s * (r + 0.001), -0.4 * length, 0)),
                     pivot + Vector((s * (r + 0.001), 0.1 * length, 0)), 0.004, 0.004),
    ]
    details = kit.merge(f'NacelleDetails{s}', parts, pivot)
    nav = 'green' if s > 0 else 'red'
    light = pivot + Vector((s * (r + 0.006), -0.23 * length, 0.25 * r))
    navlight = kit.merge(f'NavLight{s}', [sphere(f'NavBulb{s}', m[f'lamp_{nav}'], 0.011 * u, light, 8),
                                         sphere(f'NavHalo{s}', m[f'glow_{nav}'], 0.024 * u, light, 8)], pivot)
    glow_at = Vector((pivot.x, back + 0.02 * u, pivot.z))
    nozzle = kit.merge(f'NozzleGlow{s}', [cylinder(f'Nozzle{s}', m['nozzle'], r * 0.72, 0.01, glow_at, rotation=along, segments=16, bevel=0)],
                       glow_at)
    plume = cylinder(f'PlumeCone{s}', m['plume'], r * 0.62, plume_length, glow_at + Vector((0, plume_length / 2 + 0.005, 0)),
                     rotation=(-math.pi / 2, 0, 0), segments=16, bevel=0, radius2=r * 0.15)
    plume = kit.merge(f'Plume{s}', [plume], glow_at + Vector((0, 0.005, 0)))
    return pivot, (shell, details, navlight), nozzle, plume


def gear(m):
    """Nose leg and two main legs with pads; origin at the belly, scaling it in z pulls
    them in."""
    parts = []
    for name, (x, y) in (('Nose', (0, -0.33)), ('Left', (-0.075, 0.05)), ('Right', (0.075, 0.05))):
        parts += [
            cylinder(f'Leg{name}', m['steel_light'], 0.011, BELLY, (x, y, BELLY / 2), segments=8, bevel=0),
            cylinder(f'Strut{name}', m['steel'], 0.017, 0.045, (x, y, BELLY - 0.03), segments=8, bevel=0.002),
            beam(f'Link{name}', m['steel'], (x, y + 0.02, BELLY - 0.01), (x, y + 0.005, 0.035), 0.008),
            cylinder(f'Pad{name}', m['dark'], 0.028, 0.012, (x, y, 0.006), segments=12, bevel=0.002),
        ]
    return kit.merge('Gear', parts, (0, 0, BELLY))


def flash(m):
    """The muzzle flash at both launchers in one node (scaled about the middle between them)."""
    parts = []
    for s in (-1, 1):
        muzzle = Vector((s * LAUNCHER.x, FLASH_AT.y, FLASH_AT.z))
        parts += [sphere(f'Flash{s}{k}', m['flash'], 0.04 * (1 - 0.25 * k), muzzle - Vector((0, 0.036 * k, 0)), 10) for k in range(3)]
    obj = kit.merge('Flash', parts, FLASH_AT)
    obj.scale = (HIDDEN,) * 3
    return obj


def build():
    root, body = air.start('GDIOrca', 'Orca')
    m = materials()
    for obj in hull(m, root):
        kit.parent(obj, body)
    legs = kit.parent(gear(m), body)
    engines, nozzles, plumes = [], [], []
    for s in (-1, 1):
        pivot, parts, nozzle, plume = nacelle(m, root, s)
        joint = kit.parent(kit.empty(f'Engine{s}', pivot), body)
        for obj in (*parts, nozzle, plume):
            kit.parent(obj, joint)
        engines.append(joint)
        nozzles.append(nozzle)
        plumes.append(plume)
    flash_node = kit.parent(flash(m), body)

    channels = [(body, 'location'), (body, 'rotation_euler'), (legs, 'scale'), (flash_node, 'scale')]
    for joint, nozzle, plume in zip(engines, nozzles, plumes):
        channels += [(joint, 'rotation_euler'), (nozzle, 'scale'), (plume, 'scale')]

    rad = math.radians
    hidden = Vector((HIDDEN,) * 3)

    def pose(tilt, thrust, gear_out, pitch=0.0, roll=0.0, lift=0.0, fire=None):
        v = {
            ('Body', 'location'): Vector((0, 0, lift)),
            ('Body', 'rotation_euler'): Vector((rad(pitch), rad(roll), 0)),
            ('Gear', 'scale'): Vector((1, 1, air.mix(0.02, 1, gear_out))),
            ('Flash', 'scale'): fire if fire is not None else hidden,
        }
        for joint, nozzle, plume in zip(engines, nozzles, plumes):
            v[(joint.name, 'rotation_euler')] = Vector((rad(tilt), 0, 0))
            v[(nozzle.name, 'scale')] = Vector((1, 1, 1)) if thrust > 0.05 else hidden
            v[(plume.name, 'scale')] = Vector((1, thrust, 1)) if thrust > 0.05 else hidden
        return v

    def flicker(f):
        return 1 + 0.12 * math.sin(f * 2.3) * math.sin(f * 0.7 + 1)

    def fly(f):
        t = 2 * math.pi * f / air.FLY_FRAMES
        return pose(TILT_HOVER, flicker(f), 0, pitch=-2 + 0.8 * math.sin(2 * t), roll=1.5 * math.sin(t), lift=0.008 * math.sin(t))

    def idle(f):
        return pose(0, 0, 1)

    def take_off(f):
        return pose(air.mix(0, TILT_HOVER, air.span(f, 4, 24)), air.span(f, 0, 10) * flicker(f), 1 - air.span(f, 12, 28),
                    pitch=air.mix(0, -2, air.span(f, 10, 30)))

    def land(f):
        return pose(air.mix(TILT_HOVER, 0, air.span(f, 8, 28)), (1 - air.span(f, 18, 30)) * flicker(f), air.span(f, 0, 16),
                    pitch=air.mix(-2, 0, air.span(f, 0, 20)))

    def fire(f):
        v = fly(f)
        if f in (0, 1, 5, 6):  # two salvoes
            v[('Flash', 'scale')] = Vector((1, 1, 1)) * (1.15 if f % 5 else 1.0)
        v[('Body', 'rotation_euler')].x += rad(1.5 * math.sin(math.pi * min(1, f / 8)))  # a small kick
        return v

    air.clip('Idle', air.IDLE_FRAMES, channels, idle)
    air.clip('TakeOff', air.TAKEOFF_FRAMES, channels, take_off)
    air.clip('Fly', air.FLY_FRAMES, channels, fly)
    air.clip('Land', air.LAND_FRAMES, channels, land)
    air.clip('Fire', FIRE_FRAMES, channels, fire)

    def rest():
        for (name, prop), value in idle(0).items():
            setattr(kit.collection().objects[name], prop, value)

    rest()
    return rest


if __name__ == '__main__':
    air.main(build, OUT, BLEND, {'Idle': [0], 'TakeOff': [15], 'Fly': [0], 'Fire': [1]}, bake=512, scale=1.5, target=(0, 0, 0.2))
