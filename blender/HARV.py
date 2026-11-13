"""
Tiberian Fallout – GDI harvester (HARV), after Tiberian Sun.

A heavy tracked harvester, like the original: a long hull on two broad tracks under
armoured side skirts, in two parts:
  * the cab in front: an armoured block with a sloped upper front carrying two
    louvred grilles and vision slits, lamps at its corners, door seams, a vent and a
    side window on its flanks; on the roof a small cupola with a searchlight, the
    amber beacon, an antenna and two exhaust stacks at the back corners. Low in front
    of it, on two arms, the collector: a wide scoop hood in the house colour between
    two round drum housings, the toothed drum turning in its mouth, a rake of tines
    over the ground;
  * the Tiberium bin behind it: a big box with ribbed flanks and chamfered top edges,
    bands in the house colour round its front and back, on top two rows of grated
    slots through which the green load glows, double doors with locking bars and a
    ladder at the back. At the refinery it is swapped: the full bin rolls off
    backwards into the refinery's gate, an empty one rolls forward onto the deck
    (its rollers, rails and locks show while it is away).
The hull, the cab and the bin are in the light camouflage of the buildings, tinted with
the house colour in the game (GAPILE.camo_material).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle     loop, 2 s: the beacon blinks
    Walk     loop: driving, the road wheels and sprockets turn (one turn of the wheels
             per loop), the body rocks a little; the root's walkSpeed (glTF extras) is
             the ground speed in cells per second at which the tracks do not slip
    Harvest  loop, 1 s: the drum turns, the body shakes
    Unload   once, 4.5 s: docked with its back in the refinery's gate, the bin lifts
             off its locks, rolls back into the refinery (there from 1.7 to 2.3 s), and
             a new one rolls forward onto the deck

Places the game relies on (app/lib/game/harvesting.ts): the two exhaust stacks' tips
(EXHAUSTS) and the collector's drum (COLLECTOR, about 0.58 cells in front of the
origin) are where they were on the wheeled harvester.

Run headless:

    blender -b --factory-startup --python blender/HARV.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402 – materials, tracks, road wheels, start/main

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'HARV.glb')
BLEND = os.path.join(HERE, 'HARV.blend')

TRACK_X = 0.27                          # the tracks' middle (x)
TRACK_WIDTH = 0.14
TRACK = (-0.56, 0.6)
TRACK_HEIGHT = 0.15
WHEEL_RADIUS = 0.05
WHEELS_Y = (-0.36, -0.2, -0.04, 0.12, 0.28, 0.42)
SPROCKET = 0.075                        # 1.5 × the wheels: 2/3 of a turn per loop (3 bolts: seamless)
WALK_FRAMES = 30        # one turn of the road wheels
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
HARVEST_FRAMES = 30
UNLOAD_FRAMES = 135
SKIRT = (0.29, 0.37, 0.155, 0.235)      # the side skirts over the tracks: inner and outer x, bottom, top
APRON = (-0.4, 0.46, 0.105)             # the apron down their flanks: from y to y, its bottom
DECK = 0.175                            # the deck the bin sits on
CAB = (-0.58, -0.18, 0.44)              # the cab: front, back, roof
HALF = 0.31                             # the cab's half width
BIN = (-0.16, 0.62, 0.46)               # the bin: front, back, top
BIN_HALF = 0.29
DRUM = Vector((0, -0.68, 0.075))        # in the collector's mouth (harvesting.ts COLLECTOR: its middle, scaled)
STACKS = (0.212, -0.224, 0.635)         # the exhaust stacks' tips (x, y, z; harvesting.ts EXHAUSTS)
SWAP = 1.35             # how far the bin rolls back: all of it into the refinery
SCALE = 0.85            # the whole harvester, against the walkers and Nod's vehicles

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = nod.materials()
    m.update({
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'load': material('LoadCrystal', srgb('#3fdc5c'), 0.3, emission=srgb('#2fd04a'), strength=2.5),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def loft(name, mat, sections, bevel=0.008, axis='Y'):
    """A solid through cross-sections: `sections` = [(t, [(a, b), …]), …], each a
    convex polygon with the same number of corners at t along `axis` ('Y': the
    polygons in (x, z); 'X': in (y, z)); capped at both ends."""
    def point(t, a, b):
        return (a, t, b) if axis == 'Y' else (t, a, b)

    def build(bm):
        rings = [[bm.verts.new(point(t, a, b)) for a, b in points] for t, points in sections]
        n = len(rings[0])
        for p, q in zip(rings, rings[1:]):
            for i in range(n):
                bm.faces.new((p[i], p[(i + 1) % n], q[(i + 1) % n], q[i]))
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def tilted(name, mat, size, centre, tilt, bevel=0.002):
    """A box lying on a plate tipped back by `tilt` (its y along the slope)."""
    return box(name, mat, size, centre, bevel=bevel, rotation=(tilt, 0, 0))


def crystal(name, mat, base, height, radius):
    """A small Tiberium crystal: a four-sided spike standing on `base`."""
    spike = cylinder(name, mat, radius, height, Vector(base) + Vector((0, 0, height / 2)), segments=4, bevel=0, radius2=0.002)
    for poly in spike.data.polygons:
        poly.use_smooth = False
    return spike


# --------------------------------------------------------------------------- hull and cab

def cab_profile(inset=0.0):
    """The cab's side profile (y, z): a near-vertical lower front, the sloped upper
    front plate, the roof; `inset` shrinks it (the chamfered side edges)."""
    front, back, roof = CAB
    return [(front + inset * 0.6, SKIRT[2]), (front + inset * 0.6, 0.3 - inset * 0.3), (front + 0.03 + inset, 0.335 - inset * 0.3),
            (front + 0.11 + inset, roof - inset), (back, roof - inset), (back, SKIRT[2])]


UPPER = (Vector((0, CAB[0] + 0.03, 0.335)), Vector((0, CAB[0] + 0.11, CAB[2])))  # the upper front plate: bottom and top edge
UPPER_TILT = math.atan2(UPPER[1].z - UPPER[0].z, UPPER[1].y - UPPER[0].y)


def upper(t, x, out=0.0):
    """A point on the cab's upper front plate (t = 0 at its bottom edge, 1 at the top)."""
    normal = Vector((0, -math.sin(UPPER_TILT), math.cos(UPPER_TILT)))
    return UPPER[0].lerp(UPPER[1], t) + Vector((x, 0, 0)) + normal * out


def hull(m, root):
    """The lower hull between the tracks, the floor over them, the side skirts and
    the cab (one camouflaged mesh)."""
    xi, xo, bottom, top = SKIRT
    parts = [
        kit.hexahedron('Lower', m['sand'], (
            (-0.19, CAB[0] + 0.03, 0.06), (0.19, CAB[0] + 0.03, 0.06), (0.19, BIN[1] - 0.01, 0.06), (-0.19, BIN[1] - 0.01, 0.06),
            (-0.19, CAB[0], bottom), (0.19, CAB[0], bottom), (0.19, BIN[1] + 0.01, bottom), (-0.19, BIN[1] + 0.01, bottom)), bevel=0.008),
        box('Floor', m['sand'], (2 * xi, BIN[1] - CAB[0] + 0.01, DECK - bottom + 0.004), (0, (CAB[0] + BIN[1]) / 2, (DECK + bottom) / 2),
            bevel=0.004),
        loft('Cab', m['sand'], [(x, cab_profile(inset)) for x, inset in (
            (-HALF, 0.022), (-HALF + 0.02, 0.0), (HALF - 0.02, 0.0), (HALF, 0.022))], bevel=0.008, axis='X'),
    ]
    for s in (-1, 1):
        # the skirt over the track, its ends sloping down
        parts.append(loft(f'Skirt{s}', m['sand'], [(y, [(s * xi, b), (s * xo, b), (s * xo, t), (s * xi, t)]) for y, b, t in (
            (CAB[0] - 0.02, bottom + 0.02, top - 0.04), (CAB[0] + 0.06, bottom, top), (BIN[1] - 0.06, bottom, top),
            (BIN[1] + 0.02, bottom + 0.02, top - 0.04))], bevel=0.008))
        # the apron down its flank over the upper run of the track
        parts.append(kit.hexahedron(f'Apron{s}', m['sand'], (
            (s * (xo - 0.012), APRON[0] + 0.05, APRON[2]), (s * xo, APRON[0] + 0.05, APRON[2]), (s * xo, APRON[1] - 0.05, APRON[2]),
            (s * (xo - 0.012), APRON[1] - 0.05, APRON[2]),
            (s * (xo - 0.012), APRON[0], bottom + 0.01), (s * xo, APRON[0], bottom + 0.01), (s * xo, APRON[1], bottom + 0.01),
            (s * (xo - 0.012), APRON[1], bottom + 0.01)), bevel=0.004))
    return camo(kit.merge('HullShell', parts), root)


def louvres(name, m, x, t0, t1, width, slats=5):
    """A louvred grille on the cab's upper front plate."""
    mid = (t0 + t1) / 2
    length = (UPPER[1] - UPPER[0]).length * (t1 - t0)
    parts = [tilted(f'{name}Frame', m['steel'], (width + 0.016, length + 0.016, 0.008), upper(mid, x, 0.002), UPPER_TILT),
             tilted(f'{name}Well', m['dark'], (width, length, 0.008), upper(mid, x, 0.004), UPPER_TILT, 0)]
    for k in range(slats):
        t = t0 + (t1 - t0) * (k + 0.5) / slats
        parts.append(box(f'{name}Slat{k}', m['steel_light'], (width - 0.004, 0.006, length / slats * 0.9), upper(t, x, 0.008), bevel=0,
                         rotation=(UPPER_TILT - math.radians(40), 0, 0)))
    return parts


def cab_details(m):
    front, back, roof = CAB
    parts = [
        # the upper front: two louvred grilles, vision slits over them
        *louvres('GrilleL', m, -0.13, 0.12, 0.62, 0.18),
        *louvres('GrilleR', m, 0.13, 0.12, 0.62, 0.18),
        *[tilted(f'Slit{s}', m['glass'], (0.14, 0.018, 0.01), upper(0.82, s * 0.12, 0.003), UPPER_TILT) for s in (-1, 1)],
        tilted('SlitHood', m['steel'], (0.5, 0.012, 0.012), upper(0.94, 0, 0.006), UPPER_TILT),
        # the lower front: an armour plate with seams, tow hooks
        box('FrontPlate', m['sand_light'], (0.34, 0.008, 0.11), (0, front - 0.004, 0.225), bevel=0.003),
        *detail.seam('FrontSeam', m['seam'], (0, front - 0.009, 0.175), (0, front - 0.009, 0.275)),
        *detail.rivets('FrontRivets', m['steel_light'], (-0.15, front - 0.009, 0.272), (0.15, front - 0.009, 0.272), 7, axis='Y'),
        # on the roof: a hatch, seams, an antenna
        box('RoofHatch', m['sand_light'], (0.12, 0.1, 0.01), (-0.12, -0.28, roof + 0.003), bevel=0.003),
        *detail.seam('RoofSeam', m['seam'], (-0.29, -0.37, roof + 0.001), (0.29, -0.37, roof + 0.001)),
        beam('Antenna', m['steel'], (-0.25, -0.21, roof), (-0.26, -0.18, roof + 0.33), 0.005),
        cylinder('AntennaBase', m['dark'], 0.012, 0.02, (-0.25, -0.21, roof + 0.01), segments=8, bevel=0),
        # the cupola: a short octagonal turret, its hatch, a searchlight
        cylinder('Cupola', m['steel'], 0.065, 0.05, (0.08, -0.33, roof + 0.025), segments=8, bevel=0.005, rotation=(0, 0, math.pi / 8)),
        cylinder('CupolaHatch', m['sand_light'], 0.05, 0.012, (0.08, -0.325, roof + 0.056), segments=16),
        *[box(f'CupolaSlit{k}', m['glass'], (0.03, 0.006, 0.01), (0.08 + 0.064 * math.cos(a), -0.33 + 0.064 * math.sin(a), roof + 0.035),
              bevel=0, rotation=(0, 0, a + math.pi / 2)) for k, a in enumerate((-math.pi / 2, -math.pi / 4 - math.pi / 2, -math.pi / 4))],
        box('SearchlightArm', m['steel'], (0.012, 0.02, 0.03), (0.145, -0.34, roof + 0.045), bevel=0.002),
        *detail.lamp('Searchlight', m['steel'], m['lamp_white'], (0.155, -0.36, roof + 0.065), (0, -1, 0.15), 0.016),
        cylinder('BeaconBase', m['steel'], 0.018, 0.03, (-0.08, -0.4, roof + 0.015), segments=10, bevel=0),
    ]
    for s in (-1, 1):
        x = s * HALF
        parts += [
            # lamps at the lower front corners and on the roof edge
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.235, front - 0.004, 0.275), (0, -1, 0), 0.018),
            *detail.lamp(f'Marker{s}', m['dark'], m['lamp_amber'], (s * 0.235, front - 0.004, 0.235), (0, -1, 0), 0.01),
            *detail.lamp(f'RoofLight{s}', m['steel'], m['lamp_white'], (s * 0.22, front + 0.115, roof + 0.008), (0, -1, 0.3), 0.012),
            box(f'TowHook{s}', m['steel'], (0.03, 0.04, 0.03), (s * 0.24, front - 0.012, 0.18), bevel=0.005),
            # the flank: a door in seams, its window and handle, a vent, a house-colour panel
            *detail.seam(f'DoorFront{s}', m['seam'], (x + s * 0.001, -0.5, SKIRT[3]), (x + s * 0.001, -0.5, 0.41)),
            *detail.seam(f'DoorBack{s}', m['seam'], (x + s * 0.001, -0.34, SKIRT[3]), (x + s * 0.001, -0.34, 0.41)),
            *detail.seam(f'DoorTop{s}', m['seam'], (x + s * 0.001, -0.5, 0.41), (x + s * 0.001, -0.34, 0.41)),
            box(f'SideWindow{s}', m['glass'], (0.008, 0.1, 0.05), (x + s * 0.002, -0.42, 0.36), bevel=0.002),
            box(f'DoorHandle{s}', m['steel_light'], (0.012, 0.035, 0.01), (x + s * 0.005, -0.37, 0.29), bevel=0.002),
            *detail.grille(f'SideVent{s}', m['steel'], m['dark'], (x + s * 0.004, -0.25, 0.33), 0.1, 0.07, 'X', 5, 0.008),
            box(f'CabStripe{s}', m['remap'], (0.006, 0.36, 0.025), (x + s * 0.002, -0.38, SKIRT[3] + 0.022), bevel=0.002),
            beam(f'Handrail{s}', m['steel_light'], (x + s * 0.012, -0.31, SKIRT[3] + 0.04), (x + s * 0.012, -0.31, 0.4), 0.008),
            # the exhaust stacks at the back corners of the roof, up past it
            cylinder(f'Exhaust{s}', m['steel'], 0.022, STACKS[2] - roof - 0.01, (s * STACKS[0], STACKS[1], (STACKS[2] + roof - 0.01) / 2),
                     segments=10),
            cylinder(f'ExhaustTip{s}', m['dark'], 0.026, 0.02, (s * STACKS[0], STACKS[1], STACKS[2]), segments=10, bevel=0),
            *[cylinder(f'HeatShield{s}{k}', m['steel_light'], 0.027, 0.03, (s * STACKS[0], STACKS[1], z), segments=10, bevel=0)
              for k, z in enumerate((roof + 0.05, roof + 0.12))],
            box(f'StackClamp{s}', m['steel'], (0.06, 0.03, 0.03), (s * STACKS[0], STACKS[1], roof + 0.015), bevel=0.004),
        ]
    return parts


def chassis(m):
    """The deck under the bin (rollers, guide rails, locks), the skirts' fittings, the
    rear bumper; and the cab's fittings."""
    xi, xo, bottom, top = SKIRT
    front, back = BIN[0], BIN[1]
    parts = [box('DeckPlate', m['steel'], (2 * xi - 0.02, back - front, 0.01), (0, (front + back) / 2, DECK - 0.002), bevel=0.003)]
    for k in range(7):  # rollers in the deck, guide rails along its edges, twist locks at the corners
        y = front + 0.06 + k * (back - front - 0.12) / 6
        parts.append(cylinder(f'Roller{k}', m['steel_light'], 0.01, 2 * xi - 0.08, (0, y, DECK + 0.004), rotation=(0, math.pi / 2, 0),
                              segments=8, bevel=0))
    for s in (-1, 1):
        parts.append(box(f'GuideRail{s}', m['steel_light'], (0.012, back - front - 0.04, 0.02), (s * (xi + 0.01), (front + back) / 2, top + 0.008),
                         bevel=0.002))
        for y in (front + 0.04, back - 0.04):
            parts.append(box(f'Lock{s}{y:.2f}', m['hazard'], (0.03, 0.03, 0.02), (s * (BIN_HALF - 0.035), y, DECK + 0.006), bevel=0.003))
        # the skirt: armour plates in seams, rivets, a house-colour band, a vent at the back
        parts += [
            *[p for k, y in enumerate((-0.2, 0.04, 0.28)) for p in detail.seam(
                f'SkirtSeam{s}{k}', m['seam'], (s * (xo + 0.001), y, APRON[2] + 0.004), (s * (xo + 0.001), y, top - 0.005))],
            *detail.rivets(f'SkirtRivets{s}', m['steel_light'], (s * (xo + 0.003), -0.5, top - 0.018), (s * (xo + 0.003), 0.56, top - 0.018), 10,
                           axis='X'),
            *detail.rivets(f'ApronRivets{s}', m['steel_light'], (s * (xo + 0.003), APRON[0] + 0.03, APRON[2] + 0.012),
                           (s * (xo + 0.003), APRON[1] - 0.03, APRON[2] + 0.012), 8, axis='X'),
            box(f'SkirtBand{s}', m['remap'], (0.006, 0.16, 0.03), (s * (xo + 0.002), 0.47, bottom + 0.035), bevel=0.002),
            box(f'SkirtLip{s}', m['steel'], (0.016, BIN[1] - CAB[0] - 0.06, 0.012), (s * (xo - 0.002), (CAB[0] + BIN[1]) / 2, bottom + 0.006),
                bevel=0.003),
            *detail.grille(f'SkirtVent{s}', m['steel'], m['dark'], (s * (xo + 0.003), 0.16, bottom + 0.042), 0.12, 0.045, 'X', 4, 0.008),
        ]
    # the rear bumper in warning stripes, tail lights at its ends, a tow hook
    parts.append(box('Bumper', m['dark'], (2 * xi, 0.04, 0.05), (0, back + 0.02, 0.11), bevel=0.006))
    for k in range(5):
        parts.append(box(f'BumperStripe{k}', m['hazard'] if k % 2 == 0 else m['dark'], (0.08, 0.006, 0.04), (-0.16 + k * 0.08, back + 0.042, 0.11),
                         bevel=0))
    for s in (-1, 1):
        parts += detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.245, back + 0.042, 0.11), (0, 1, 0), 0.014)
    parts.append(cylinder('TowHitch', m['steel'], 0.018, 0.04, (0, back + 0.05, 0.075), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0))
    return kit.merge('Chassis', parts + cab_details(m))


# --------------------------------------------------------------------------- collector

def collector(m):
    """The scoop on its arms: the hood in the house colour, the drum housings, the
    dark mouth and the rake (fixed parts; the drum turns on its own)."""
    y0 = CAB[0] - 0.01
    parts = [
        # the hood over the drum, its back closed by a dark wall
        kit.hexahedron('Hood', m['remap'], (
            (-0.25, y0, 0.06), (0.25, y0, 0.06), (0.25, -0.735, 0.125), (-0.25, -0.735, 0.125),
            (-0.25, y0, 0.2), (0.25, y0, 0.2), (0.25, -0.755, 0.15), (-0.25, -0.755, 0.15)), bevel=0.008),
        box('MouthWall', m['dark'], (0.46, 0.03, 0.1), (0, -0.63, 0.06), bevel=0.003),
        box('HoodRib', m['steel'], (0.5, 0.02, 0.012), (0, -0.69, 0.17), bevel=0.003, rotation=(math.radians(-15), 0, 0)),
        *[box(f'HoodStrut{k}', m['steel'], (0.014, 0.17, 0.008), (x, -0.65, 0.18), bevel=0.002, rotation=(math.radians(-15), 0, 0))
          for k, x in enumerate((-0.15, 0.0, 0.15))],
        # the rake: a bar along the front bottom with tines turned up at their tips
        box('RakeBar', m['steel'], (0.58, 0.03, 0.025), (0, -0.77, 0.022), bevel=0.005),
    ]
    for k in range(9):
        x = -0.24 + k * 0.06
        parts += [box(f'Tine{k}', m['steel_light'], (0.02, 0.07, 0.014), (x, -0.8, 0.016), bevel=0.003),
                  box(f'TineTip{k}', m['steel_light'], (0.018, 0.03, 0.014), (x, -0.835, 0.026), bevel=0.003, rotation=(math.radians(-30), 0, 0))]
    for s in (-1, 1):
        parts += [
            # a round housing at each end of the drum, capped in the house colour
            cylinder(f'DrumHousing{s}', m['steel'], 0.075, 0.15, (s * 0.27, -0.68, 0.095), segments=20),
            cylinder(f'HousingCap{s}', m['remap'], 0.068, 0.014, (s * 0.27, -0.68, 0.172), segments=20),
            cylinder(f'HousingHub{s}', m['steel_light'], 0.028, 0.03, (s * 0.27, -0.68, 0.18), segments=12),
            # the arms onto the cab's front, with their rams
            box(f'Arm{s}', m['steel'], (0.04, 0.1, 0.04), (s * 0.16, CAB[0] - 0.02, 0.17), bevel=0.005),
            beam(f'Ram{s}', m['steel_light'], (s * 0.08, CAB[0] - 0.005, 0.28), (s * 0.08, -0.63, 0.19), 0.012),
            beam(f'RamBody{s}', m['dark'], (s * 0.08, CAB[0] - 0.006, 0.282), (s * 0.08, -0.607, 0.235), 0.026),
        ]
    return kit.merge('Collector', parts)


def drum(m):
    """The collector drum with its rows of teeth; origin on its axle (it turns about x)."""
    parts = [cylinder('Drum', m['steel'], 0.04, 0.4, DRUM, rotation=(0, math.pi / 2, 0), segments=16),
             cylinder('DrumAxle', m['dark'], 0.018, 0.44, DRUM, rotation=(0, math.pi / 2, 0), segments=10, bevel=0)]
    for k in range(8):
        a = 2 * math.pi * k / 8
        d = Vector((0, math.cos(a), math.sin(a)))
        for i in range(4):
            x = -0.15 + i * 0.1 + (0.05 if k % 2 else 0)
            parts.append(beam(f'Tooth{k}_{i}', m['steel_light'], DRUM + Vector((x, 0, 0)) + d * 0.036, DRUM + Vector((x, 0, 0)) + d * 0.066, 0.018,
                              0.012))
    return kit.merge('Drum', parts, DRUM)


# --------------------------------------------------------------------------- the bin

def bin_section(y, inset=0.0):
    w, top, chamfer = BIN_HALF - inset, BIN[2] - inset, 0.045
    return y, [(-w, DECK), (w, DECK), (w, top - chamfer), (w - chamfer, top), (-w + chamfer, top), (-w, top - chamfer)]


def tiberium_bin(m, root):
    """The swappable bin (node Container, with its camouflaged shell as a child);
    origin in the middle of its floor (it rolls along y)."""
    front, back, top = BIN
    floor = Vector((0, (front + back) / 2, DECK))
    shell = camo(kit.merge('ContainerShell', [loft('ContainerShell', m['sand'], [
        bin_section(front, 0.012), bin_section(front + 0.012), bin_section(back - 0.012), bin_section(back, 0.012)], bevel=0.008)], floor), root)
    parts = []
    for s in (-1, 1):
        x = s * (BIN_HALF + 0.004)
        # ribs down the flanks, a rail along the bottom
        for k in range(12):
            y = front + 0.07 + k * (back - front - 0.14) / 11
            parts.append(box(f'Rib{s}{k}', m['sand_light'], (0.012, 0.022, top - DECK - 0.09), (x, y, (top + DECK - 0.07) / 2), bevel=0))
        parts += [
            box(f'FootRail{s}', m['steel'], (0.014, back - front - 0.02, 0.022), (x, (front + back) / 2, DECK + 0.016), bevel=0.003),
            box(f'TopRail{s}', m['steel'], (0.014, back - front - 0.02, 0.014), (x, (front + back) / 2, top - 0.05), bevel=0.003),
        ]
    # house-colour bands round the front and the back
    for name, y in (('Front', front + 0.035), ('Back', back - 0.035)):
        parts += [
            box(f'Band{name}Top', m['remap'], (2 * BIN_HALF - 0.09, 0.05, 0.006), (0, y, top + 0.002), bevel=0.002),
            *[box(f'Band{name}{s}', m['remap'], (0.006, 0.05, top - DECK - 0.06), (s * (BIN_HALF + 0.002), y, (top + DECK - 0.04) / 2), bevel=0.002)
              for s in (-1, 1)],
            *[box(f'Band{name}Edge{s}', m['remap'], (0.066, 0.05, 0.006), (s * (BIN_HALF - 0.022), y, top - 0.022), bevel=0.002,
                  rotation=(0, -s * math.pi / 4, 0)) for s in (-1, 1)],
        ]
    # on top: two rows of grated slots, the green load glowing through them
    for i, x in enumerate((-0.11, 0.11)):
        for j in range(4):
            y = front + 0.17 + j * 0.155
            parts += [
                box(f'SlotFrame{i}{j}', m['steel'], (0.17, 0.11, 0.01), (x, y, top + 0.002), bevel=0.003),
                box(f'SlotLoad{i}{j}', m['load'], (0.15, 0.09, 0.006), (x, y, top + 0.005), bevel=0),
                *[box(f'SlotBar{i}{j}{k}', m['steel'], (0.008, 0.094, 0.008), (x - 0.05 + 0.05 * k, y, top + 0.009), bevel=0) for k in range(3)],
            ]
            for c, (dx, dy, h) in enumerate(((-0.025, -0.02, 0.03), (0.03, 0.018, 0.024), (0.005, 0.025, 0.018))[:2 + (i + j) % 2]):
                parts.append(crystal(f'Crystal{i}{j}{c}', m['load'], (x + dx, y + dy, top + 0.005), h, 0.012))
    # the back: double doors with locking bars, a warning stripe, a ladder
    parts += [
        box('DoorSeam', m['seam'], (0.006, 0.006, top - DECK - 0.07), (0, back + 0.002, (top + DECK - 0.04) / 2), bevel=0),
        box('DoorStripe', m['hazard'], (0.44, 0.006, 0.03), (0, back + 0.003, DECK + 0.05), bevel=0),
    ]
    for k, x in enumerate((-0.15, -0.05, 0.05, 0.15)):
        parts += [beam(f'LockBar{k}', m['steel_light'], (x, back + 0.01, DECK + 0.02), (x, back + 0.01, top - 0.05), 0.01),
                  box(f'LockHandle{k}', m['steel'], (0.012, 0.014, 0.04), (x + 0.012, back + 0.016, DECK + 0.13), bevel=0.002)]
    parts += detail.ladder('Ladder', m['steel_light'], (0.22, back + 0.02, DECK + 0.03), (0.22, back + 0.02, top - 0.01), 0.05, 6, out=(0, 0.012, 0))
    for x in (-BIN_HALF + 0.02, BIN_HALF - 0.02):  # corner castings at the bottom (where the locks take hold)
        for y in (front + 0.02, back - 0.02):
            parts.append(box(f'Corner{x:.2f}{y:.2f}', m['dark'], (0.042, 0.042, 0.03), (x, y, DECK + 0.015), bevel=0.004))
    load = kit.merge('Container', parts, floor)
    kit.parent(shell, load)
    return load


# --------------------------------------------------------------------------- model

def build():
    root, body = nod.start('GDIHarvester', 'Harvester', WALK_SPEED)
    m = materials()
    kit.parent(hull(m, root), body)
    kit.parent(chassis(m), body)
    kit.parent(collector(m), body)
    roller = kit.parent(drum(m), body)
    load = kit.parent(tiberium_bin(m, root), body)
    rest = load.location.copy()
    lamp = Vector((-0.08, -0.4, CAB[2] + 0.045))
    beacon = kit.parent(kit.merge('Beacon', [sphere('BeaconBulb', m['lamp_amber'], 0.02, lamp, 10),
                                             sphere('BeaconHalo', m['glow_amber'], 0.045, lamp, 10)], lamp), body)
    # the running gear stays on the ground (on the root) while the body rocks and shakes
    wheels, sprockets = [], []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], TRACK_HEIGHT, 18), root)
        x = s * (TRACK_X + TRACK_WIDTH / 2 + 0.004)
        wheels += [kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (x, y, WHEEL_RADIUS + 0.004), WHEEL_RADIUS, 0.022), root)
                   for k, y in enumerate(WHEELS_Y)]
        sprockets += [kit.parent(nod.road_wheel(m, f'Sprocket{s}{k}', (x, y, SPROCKET + 0.004), SPROCKET, 0.024), root)
                      for k, y in enumerate((TRACK[0] + 0.07, TRACK[1] - 0.07))]
    kit.bake_camo(512)

    keys = kit.keys
    still = Vector((0, 0, 0))
    # Idle: the beacon blinks
    kit.blink(beacon, kit.flashes((0, 10), (30, 10)))
    kit.to_track(beacon, 'Idle')
    # Walk: the wheels and sprockets turn, the body rocks
    nod.spin(wheels, WALK_FRAMES)
    nod.spin(sprockets, WALK_FRAMES, WHEEL_RADIUS / SPROCKET)
    keys(body, 'location', {f: Vector((0, 0, 0.005 * math.sin(4 * math.pi * f / WALK_FRAMES))) for f in range(WALK_FRAMES + 1)}, 'LINEAR')
    keys(body, 'rotation_euler', {f: Vector((0.004 * math.sin(2 * math.pi * f / WALK_FRAMES + 1), 0, 0)) for f in range(WALK_FRAMES + 1)},
         'LINEAR')
    kit.to_track(body, 'Walk')
    # Harvest: the drum turns against the driving direction, the body shakes
    keys(roller, 'rotation_euler', {0: still, HARVEST_FRAMES: Vector((-2 * math.pi, 0, 0))}, 'LINEAR')
    kit.to_track(roller, 'Harvest')
    keys(body, 'location', {f: Vector((0.002 * math.sin(f * 2.1), 0, 0.003 * math.sin(f * 3.3))) for f in range(HARVEST_FRAMES)} |
         {HARVEST_FRAMES: still}, 'LINEAR')
    kit.to_track(body, 'Harvest')
    # Unload: the bin lifts off its locks, rolls back into the refinery (out of sight
    # there), the next one rolls forward and settles on the locks
    lift, away = Vector((0, 0, 0.012)), Vector((0, SWAP, 0.012))
    keys(load, 'location', {0: rest, 6: rest + lift, 50: rest + away, 70: rest + away, 114: rest + lift, 120: rest, UNLOAD_FRAMES: rest})
    kit.to_track(load, 'Unload')
    load.location = rest
    roller.rotation_euler = still
    body.location, body.rotation_euler = still, still
    for w in wheels + sprockets:
        w.rotation_euler = still
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Unload': [30, 60]}, scale=1.9, target=(0, 0.2, 0.25))
