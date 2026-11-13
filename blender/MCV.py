"""
Tiberian Fallout – GDI mobile construction vehicle (MCV), after Tiberian Sun.

A wide, long, low carrier in the light camouflage of the buildings (in the house
colour: GAPILE.camo_material): one flat hull between four big armoured track pods at
its corners, their ends sloped, their tops in panels, house-colour stripes on their
flanks, the tracks with their road wheels below them. On the left half of the deck
lies the folded crane: a long stepped box boom of four telescoping sections (light
bars over dark panels on top, collars at the joints, the pulley at its tip) on its
turntable at the back and two saddles. On the right half the cab sits in front, its
sloped glass canopy over the nose, a beacon and an antenna on its roof; behind it the
long glass roof of the crew compartment on its ribs, and the engine deck with grilles
and exhausts at the back. A bumper in warning stripes across the front, equipment
boxes on the flanks between the pods, lamps front and back.

The crane is raised over the construction yard when the vehicle deploys (see
GACNST.py, which builds the same vehicle with vehicle(): its front half stays as the
crane, the rear half sinks into the slab).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle     loop, 2 s: the beacon on the cab blinks
    Walk     loop: driving, the road wheels turn (one turn per loop), the hull rocks a
             little; the root's custom property walkSpeed (glTF extras) is the ground
             speed in cells per second at which the wheels do not slip

Run headless:

    Blender -b --factory-startup --python blender/MCV.py

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import detail  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'MCV.glb')
BLEND = os.path.join(HERE, 'MCV.blend')

WHEEL_RADIUS = 0.055
WALK_FRAMES = 26        # one turn of the wheels
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
BOOM_PIVOT = Vector((-0.19, 0.58, 0.4))
BOOM_LENGTH = 1.2
# the boom's sections from the pivot forward: length, width, height (their bottoms on
# one line, so the top steps down towards the tip)
BOOM_SECTIONS = ((0.42, 0.27, 0.13), (0.32, 0.235, 0.11), (0.3, 0.2, 0.092), (0.26, 0.165, 0.075))
POD_Y = (-0.52, 0.5)    # the track pods' centres (y)
POD_X = (0.335, 0.55)   # their inner and outer sides
DECK = 0.3              # the hull's deck (and the pods' tops)
HULL = (-0.74, 0.74)    # the hull's front and back
CAB = (0.02, 0.3)       # the cab's sides (x)
CANOPY_X = 0.165        # the crew compartment's glass roof: its middle (x)
SPLIT = 0.04            # where the front half (the crane in the yard) ends

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'track': material('Track', srgb('#25231f'), 0.85, 0.2),
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'crane': material('CraneGrey', srgb('#9c9e9a'), 0.6, 0.2),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
    })
    return m


def camo(obj, root):
    """The light camouflage (baked; tinted with the house colour in the game), laid out
    in the space of `root`."""
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def wheel(m, name, centre):
    """A road wheel turning about x, with spokes so the turning shows."""
    s = 1 if centre.x > 0 else -1
    parts = [cylinder(f'{name}Tyre', m['track'], WHEEL_RADIUS, 0.036, centre, rotation=(0, math.pi / 2, 0), segments=16, bevel=0.004),
             cylinder(f'{name}Hub', m['steel_light'], WHEEL_RADIUS * 0.6, 0.042, centre, rotation=(0, math.pi / 2, 0), segments=12, bevel=0.003),
             cylinder(f'{name}Cap', m['steel'], WHEEL_RADIUS * 0.22, 0.05, centre, rotation=(0, math.pi / 2, 0), segments=8, bevel=0)]
    for k in range(3):
        a = math.pi * k / 3
        d = Vector((0, math.cos(a), math.sin(a))) * WHEEL_RADIUS * 0.5
        out = Vector((0.022 * s, 0, 0))
        parts.append(beam(f'{name}Spoke{k}', m['steel'], centre - d + out, centre + d + out, 0.012, 0.012))
    return kit.merge(name, parts, centre)


def track(m, name, s, yc):
    """A track's belt under a pod, round at its ends, with tread bars round them (where
    the belt shows under the pod)."""
    x, length, height = s * 0.42, 0.54, 0.11
    parts = [box(f'{name}Belt', m['track'], (0.17, length, height), (x, yc, height / 2), bevel=height * 0.45)]
    for end in (-1, 1):
        for k, a in enumerate((0.6, 1.2, 1.8, 2.4)):     # round the end, from the ground up
            r = height / 2 + 0.002
            at = Vector((x, yc + end * (length / 2 - height / 2 + math.sin(a) * r), height / 2 - math.cos(a) * r))
            parts.append(box(f'{name}Link{end}{k}', m['steel'], (0.174, 0.014, 0.008), at, bevel=0, rotation=(end * a, 0, 0)))
    return parts


def pod(m, p, s, yc):
    """A track pod at a corner: the camouflaged fairing (sloped ends, its outer top edge
    chamfered) and its fittings; returns (fairing, details)."""
    x0, x1 = s * POD_X[0], s * POD_X[1]
    front = yc < 0
    shell = kit.hexahedron(f'{p}Pod{s}{yc}', m['sand'], (
        (x0, yc - 0.28, 0.1), (x1, yc - 0.28, 0.1), (x1, yc + 0.28, 0.1), (x0, yc + 0.28, 0.1),
        (x0, yc - 0.23, DECK + 0.01), (s * 0.53, yc - 0.23, DECK + 0.01), (s * 0.53, yc + 0.23, DECK + 0.01), (x0, yc + 0.23, DECK + 0.01)),
        bevel=0.016)
    xm = s * 0.435
    out = s * 0.545                                  # on the outer flank
    parts = [
        box(f'{p}PodPlate{s}{yc}', m['sand_light'], (0.13, 0.3, 0.01), (xm, yc, DECK + 0.012), bevel=0.003),
        *[r for dy in (-0.17, 0.17) for r in detail.seam(f'{p}PodSeam{s}{yc}{dy}', m['seam'], (x0 + s * 0.01, yc + dy, DECK + 0.012),
                                                         (s * 0.52, yc + dy, DECK + 0.012), 0.008)],
        *detail.rivets(f'{p}PodRivets{s}{yc}', m['steel_light'], (s * 0.512, yc - 0.2, DECK + 0.012), (s * 0.512, yc + 0.2, DECK + 0.012), 7, axis='Z'),
        box(f'{p}PodStripe{s}{yc}', m['remap'], (0.012, 0.42, 0.035), (out, yc, 0.2), bevel=0.003),
        *detail.seam(f'{p}PodFlankSeam{s}{yc}', m['seam'], (out - s * 0.004, yc, 0.11), (out - s * 0.008, yc, DECK - 0.01)),
        # the skirt's lower edge over the wheels
        box(f'{p}Skirt{s}{yc}', m['steel'], (0.016, 0.54, 0.022), (s * 0.552, yc, 0.11), bevel=0.003),
    ]
    end = yc - 0.254 if front else yc + 0.254      # the sloped end at the lamps' height, facing out and up
    facing = Vector((0, -1 if front else 1, 0.45)).normalized()
    if front:
        parts += [*detail.lamp(f'{p}PodLight{s}', m['dark'], m['lamp_white'], (s * 0.47, end - 0.006, 0.21), facing, 0.018),
                  *detail.lamp(f'{p}PodMarker{s}', m['dark'], m['lamp_amber'], (s * 0.39, end - 0.006, 0.21), facing, 0.011)]
    else:
        parts += [*detail.lamp(f'{p}PodTail{s}', m['dark'], m['lamp_red'], (s * 0.47, end + 0.006, 0.21), facing, 0.014),
                  box(f'{p}PodTow{s}', m['steel'], (0.05, 0.03, 0.03), (s * 0.4, yc + 0.285, 0.12), bevel=0.004)]
    return shell, parts


def boom(m, p):
    """The crane boom, folded forward from its pivot: four camouflaged telescoping
    sections stepping down towards the tip (one object, origin BOOM_PIVOT), and its
    fittings (bars over dark panels, collars, slots, the pulley at the tip)."""
    base = BOOM_PIVOT.z - 0.065
    shells, parts = [], []
    y = BOOM_PIVOT.y + 0.07
    for k, (length, width, height) in enumerate(BOOM_SECTIONS):
        y0, y1 = y - length, y            # front and back of the section
        w, top = width / 2, base + height
        shells.append(kit.hexahedron(f'{p}BoomSeg{k}', m['sand'], (
            (BOOM_PIVOT.x - w, y0, base), (BOOM_PIVOT.x + w, y0, base), (BOOM_PIVOT.x + w, y1, base), (BOOM_PIVOT.x - w, y1, base),
            (BOOM_PIVOT.x - w + 0.012, y0, top), (BOOM_PIVOT.x + w - 0.012, y0, top), (BOOM_PIVOT.x + w - 0.012, y1, top),
            (BOOM_PIVOT.x - w + 0.012, y1, top)), bevel=0.01))
        mid = (y0 + y1) / 2
        parts.append(box(f'{p}BoomPanel{k}', m['dark'], (width - 0.07, length - 0.06, 0.006), (BOOM_PIVOT.x, mid, top + 0.001), bevel=0))
        bars = max(2, round(length / 0.075))
        for j in range(bars):
            yy = y0 + 0.04 + (j + 0.5) * (length - 0.08) / bars
            parts.append(box(f'{p}BoomBar{k}_{j}', m['crane'], (width - 0.04, 0.018, 0.012), (BOOM_PIVOT.x, yy, top + 0.004), bevel=0))
        for s in (-1, 1):
            parts.append(box(f'{p}BoomSlot{k}{s}', m['dark'], (0.006, length - 0.08, height * 0.35),
                             (BOOM_PIVOT.x + s * (w + 0.001), mid, base + height * 0.5), bevel=0))
        # the collar round the front end, holding the next section
        parts.append(box(f'{p}BoomCollar{k}', m['crane'], (width + 0.012, 0.03, height + 0.012), (BOOM_PIVOT.x, y0 + 0.015, base + height / 2),
                         bevel=0.004))
        y = y0 + 0.02                     # the next section starts inside this one
    tip = BOOM_PIVOT + Vector((0, -BOOM_LENGTH, -0.025))
    parts += [
        cylinder(f'{p}BoomTip', m['steel'], 0.035, 0.12, tip, rotation=(0, math.pi / 2, 0), segments=14),
        *[box(f'{p}BoomCheek{s}', m['crane'], (0.012, 0.09, 0.07), tip + Vector((s * 0.066, 0.02, 0.0)), bevel=0.003) for s in (-1, 1)],
        box(f'{p}BoomBand', m['remap'], (BOOM_SECTIONS[0][1] + 0.006, 0.05, BOOM_SECTIONS[0][2] + 0.006), (BOOM_PIVOT.x, BOOM_PIVOT.y - 0.1, base + 0.065),
            bevel=0.003),
        box(f'{p}BoomHeel', m['steel'], (0.2, 0.06, 0.08), (BOOM_PIVOT.x, BOOM_PIVOT.y + 0.06, base + 0.04), bevel=0.008),
        cylinder(f'{p}BoomPin', m['steel_light'], 0.025, 0.29, BOOM_PIVOT + Vector((0, 0.0, -0.02)), rotation=(0, math.pi / 2, 0), segments=12),
    ]
    return shells, parts


def vehicle(m, root, prefix=''):
    """The vehicle; returns the parts by role (all unparented, in place):
    hull (camouflaged objects), details, wheels, rear (the rear half: hull, details and
    wheels), boom (origin at BOOM_PIVOT), boom_details, beacon.

    Like the original: a wide, low hull between four track pods, the folded crane boom
    along its left half, the cab with its glass canopy at the front right."""
    p = prefix
    f, b = HULL
    # the hull in two halves: the front one stays as the crane when the MCV deploys
    hull_front = [kit.hexahedron(f'{p}HullFront', m['sand'], (
        (-0.335, f, 0.08), (0.335, f, 0.08), (0.335, SPLIT, 0.08), (-0.335, SPLIT, 0.08),
        (-0.33, f + 0.08, DECK), (0.33, f + 0.08, DECK), (0.33, SPLIT, DECK), (-0.33, SPLIT, DECK)), bevel=0.014)]
    hull_rear = [kit.hexahedron(f'{p}HullRear', m['sand'], (
        (-0.335, SPLIT, 0.08), (0.335, SPLIT, 0.08), (0.335, b, 0.08), (-0.335, b, 0.08),
        (-0.33, SPLIT, DECK), (0.33, SPLIT, DECK), (0.33, b - 0.02, DECK), (-0.33, b - 0.02, DECK)), bevel=0.014)]
    # the cab at the front right, its front sloped
    c0, c1 = CAB
    cab_top, cab_front, cab_back = 0.47, -0.8, -0.4
    hull_front.append(kit.hexahedron(f'{p}Cab', m['sand'], (
        (c0, cab_front, DECK - 0.04), (c1, cab_front, DECK - 0.04), (c1, cab_back, DECK - 0.04), (c0, cab_back, DECK - 0.04),
        (c0 + 0.02, cab_front + 0.1, cab_top), (c1 - 0.02, cab_front + 0.1, cab_top), (c1 - 0.02, cab_back - 0.02, cab_top),
        (c0 + 0.02, cab_back - 0.02, cab_top)), bevel=0.014))
    # equipment boxes on the flanks between the pods (one on each half)
    for s in (-1, 1):
        hull_front.append(kit.hexahedron(f'{p}SideBox{s}', m['sand'], (
            (s * 0.33, -0.22, 0.1), (s * 0.45, -0.22, 0.1), (s * 0.45, -0.005, 0.1), (s * 0.33, -0.005, 0.1),
            (s * 0.33, -0.21, 0.27), (s * 0.44, -0.21, 0.27), (s * 0.44, -0.015, 0.27), (s * 0.33, -0.015, 0.27)), bevel=0.01))
        hull_rear.append(kit.hexahedron(f'{p}SideBoxRear{s}', m['sand'], (
            (s * 0.33, 0.06, 0.1), (s * 0.43, 0.06, 0.1), (s * 0.43, 0.2, 0.1), (s * 0.33, 0.2, 0.1),
            (s * 0.33, 0.07, 0.24), (s * 0.42, 0.07, 0.24), (s * 0.42, 0.19, 0.24), (s * 0.33, 0.19, 0.24)), bevel=0.01))
    # the engine deck at the back right
    hull_rear.append(kit.hexahedron(f'{p}EngineDeck', m['sand'], (
        (0.0, 0.5, DECK - 0.02), (0.33, 0.5, DECK - 0.02), (0.33, b - 0.02, DECK - 0.02), (0.0, b - 0.02, DECK - 0.02),
        (0.01, 0.52, DECK + 0.1), (0.32, 0.52, DECK + 0.1), (0.32, b - 0.04, DECK + 0.1), (0.01, b - 0.04, DECK + 0.1)), bevel=0.01))

    # four track pods at the corners
    details_front, details_rear = [], []
    for y in POD_Y:
        for s in (-1, 1):
            shell, fittings = pod(m, p, s, y)
            (hull_front if y < 0 else hull_rear).append(shell)
            (details_front if y < 0 else details_rear).extend(fittings)
            (details_front if y < 0 else details_rear).extend(track(m, f'{p}Track{s}{y}', s, y))
    hull = [camo(kit.merge(f'{p}HullFront', hull_front), root)]
    rear_shell = camo(kit.merge(f'{p}HullRear', hull_rear), root)

    cab_slope = math.atan2(0.1, cab_top - DECK + 0.04)
    rear_slope = math.atan2(0.02, DECK - 0.08)

    def rear_face(z):  # the hull's back (y) at height z, just behind it
        return b - (z - 0.08) / (DECK - 0.08) * 0.02 + 0.004

    def cab_face(z):  # the cab's sloped front (y) at height z, just before it
        return cab_front + (z - DECK + 0.04) / (cab_top - DECK + 0.04) * 0.1 - 0.006

    def canopy(name, y0, y1):
        """A stretch of the crew compartment's glass roof with its ribs."""
        glass = [cylinder(f'{name}Glass', m['glass'], 0.13, y1 - y0, (CANOPY_X, (y0 + y1) / 2, DECK), rotation=(math.pi / 2, 0, 0), segments=18, bevel=0)]
        ribs = [cylinder(f'{name}Rib{k}', m['steel'], 0.137, 0.022, (CANOPY_X, y, DECK), rotation=(math.pi / 2, 0, 0), segments=18, bevel=0)
                for k, y in enumerate(v for v in (-0.36, -0.22, -0.08, 0.1, 0.24, 0.38) if y0 < v < y1)]
        sills = [box(f'{name}Sill{s}', m['sand_light'], (0.02, y1 - y0, 0.03), (CANOPY_X + s * 0.135, (y0 + y1) / 2, DECK + 0.012), bevel=0.003)
                 for s in (-1, 1)]
        return glass + ribs + sills

    details_front += [
        box(f'{p}Chassis', m['steel'], (0.6, SPLIT - f - 0.06, 0.06), (0, (SPLIT + f + 0.06) / 2, 0.07), bevel=0.01),
        # the bumper in warning stripes across the front
        box(f'{p}Bumper', m['dark'], (0.64, 0.05, 0.08), (0, f - 0.02, 0.13), bevel=0.008),
        *[box(f'{p}Hazard{k}', m['hazard'] if k % 2 == 0 else m['dark'], (0.08, 0.012, 0.064), (-0.28 + k * 0.08, f - 0.047, 0.13), bevel=0)
          for k in range(8)],
        *[box(f'{p}BumperHorn{s}', m['steel'], (0.04, 0.06, 0.1), (s * 0.31, f - 0.02, 0.13), bevel=0.006) for s in (-1, 1)],
        # the cab: glass canopy over its nose, side windows, lights, roof fittings
        box(f'{p}Windscreen', m['glass'], (c1 - c0 - 0.06, 0.012, 0.15), (CANOPY_X, cab_face(0.39), 0.39), bevel=0.004, rotation=(-cab_slope, 0, 0)),
        box(f'{p}WindscreenBar', m['steel'], (0.012, 0.016, 0.15), (CANOPY_X, cab_face(0.39) - 0.002, 0.39), bevel=0.002, rotation=(-cab_slope, 0, 0)),
        box(f'{p}Visor', m['steel'], (c1 - c0 - 0.03, 0.04, 0.014), (CANOPY_X, cab_face(cab_top) + 0.01, cab_top - 0.004), bevel=0.003),
        *[box(f'{p}CabWindow{s}', m['glass'], (0.01, 0.13, 0.05), ((c0 + c1) / 2 + s * ((c1 - c0) / 2 - 0.012), -0.6, 0.41), bevel=0.003)
          for s in (-1, 1)],
        *detail.lamp(f'{p}CabLightL', m['dark'], m['lamp_white'], (c0 + 0.05, cab_face(0.3), 0.3), (0, -1, 0.5), 0.016),
        *detail.lamp(f'{p}CabLightR', m['dark'], m['lamp_white'], (c1 - 0.05, cab_face(0.3), 0.3), (0, -1, 0.5), 0.016),
        *detail.grille(f'{p}CabGrille', m['steel'], m['dark'], (CANOPY_X, cab_face(0.3) - 0.002, 0.3), 0.12, 0.035, 'Y', 3, 0.006),
        box(f'{p}CabHatch', m['steel'], (0.1, 0.1, 0.012), (0.08, -0.52, cab_top + 0.004), bevel=0.003),
        beam(f'{p}Antenna', m['steel'], (c1 - 0.04, -0.45, cab_top), (c1 - 0.035, -0.43, cab_top + 0.2), 0.007),
        box(f'{p}CabBand', m['remap'], (c1 - c0 + 0.006, 0.035, 0.03), (CANOPY_X, cab_back - 0.04, DECK + 0.06), bevel=0.003),
        # the crew compartment's glass roof, front part
        *canopy(f'{p}Canopy', cab_back - 0.02, SPLIT),
        # saddles the boom lies on, a vent and a hatch on the deck
        *[box(f'{p}Saddle{k}', m['steel'], (0.2, 0.06, 0.035), (BOOM_PIVOT.x, y, DECK + 0.0175), bevel=0.004) for k, y in enumerate((-0.53, -0.1))],
        *detail.rivets(f'{p}DeckRivets', m['steel_light'], (-0.035, f + 0.12, DECK + 0.002), (-0.035, SPLIT - 0.04, DECK + 0.002), 9, axis='Z'),
    ]
    details_rear += [
        box(f'{p}ChassisRear', m['steel'], (0.6, b - SPLIT - 0.06, 0.06), (0, (SPLIT + b - 0.06) / 2, 0.07), bevel=0.01),
        cylinder(f'{p}Turntable', m['steel'], 0.11, 0.05, BOOM_PIVOT + Vector((0, 0.02, -0.06)), segments=20),
        cylinder(f'{p}TurntableRing', m['dark'], 0.118, 0.012, BOOM_PIVOT + Vector((0, 0.02, -0.08)), segments=20, bevel=0),
        *canopy(f'{p}CanopyRear', SPLIT, 0.52),
        # the engine deck: grilles, exhausts; the back: a door, a vent
        *[box(f'{p}EngineGrille{k}', m['steel'], (0.11, 0.15, 0.008), (0.09 + k * 0.13, 0.6, DECK + 0.1), bevel=0.002) for k in range(2)],
        *[box(f'{p}EngineSlat{k}{j}', m['dark'], (0.09, 0.014, 0.006), (0.09 + k * 0.13, 0.54 + j * 0.03, DECK + 0.103), bevel=0) for k in range(2) for j in range(5)],
        *[cylinder(f'{p}Exhaust{k}', m['steel'], 0.018, 0.12, (0.29, 0.56 + k * 0.06, DECK + 0.14), segments=10) for k in range(2)],
        *[cylinder(f'{p}ExhaustCap{k}', m['dark'], 0.022, 0.012, (0.29, 0.56 + k * 0.06, DECK + 0.2), segments=10, bevel=0) for k in range(2)],
        box(f'{p}RearDoor', m['dark'], (0.2, 0.012, 0.13), (-0.12, rear_face(0.18), 0.18), bevel=0.003, rotation=(rear_slope, 0, 0)),
        *detail.grille(f'{p}RearVent', m['steel'], m['dark'], (0.16, rear_face(0.18) + 0.002, 0.18), 0.16, 0.07, 'Y', 4, 0.008),
        box(f'{p}RearBand', m['remap'], (0.6, 0.012, 0.03), (0, rear_face(DECK - 0.03), DECK - 0.03), bevel=0.002, rotation=(rear_slope, 0, 0)),
    ]
    for s in (-1, 1):
        details_front += [
            *detail.grille(f'{p}SideBoxVent{s}', m['steel'], m['dark'], (s * 0.448, -0.11, 0.19), 0.12, 0.07, 'X', 4, 0.006),
            box(f'{p}SideBoxLid{s}', m['sand_light'], (0.1, 0.17, 0.01), (s * 0.385, -0.112, 0.272), bevel=0.003),
        ]
        details_rear += [
            box(f'{p}SideBoxRearHandle{s}', m['steel'], (0.012, 0.06, 0.014), (s * 0.428, 0.13, 0.2), bevel=0.002),
            *detail.seam(f'{p}SideBoxRearSeam{s}', m['seam'], (s * 0.429, 0.13, 0.11), (s * 0.429, 0.13, 0.16)),
        ]
    details = kit.merge(f'{p}Details', details_front)
    details_rear = kit.merge(f'{p}DetailsRear', details_rear)

    # road wheels under the pods, on the outside of their tracks
    wheels, wheels_rear = [], []
    for s in (-1, 1):
        for y in POD_Y:
            for k in (-1, 0, 1):
                (wheels if y < 0 else wheels_rear).append(wheel(m, f'{p}Wheel{s}{y}{k}', Vector((s * 0.515, y + k * 0.16, WHEEL_RADIUS))))

    shells, fittings = boom(m, p)
    boom_shell = camo(kit.merge(f'{p}Boom', shells, BOOM_PIVOT), root)
    boom_details = kit.merge(f'{p}BoomDetails', fittings, BOOM_PIVOT)

    lamp = Vector((0.2, -0.56, cab_top))
    beacon = kit.merge(f'{p}Beacon', [sphere(f'{p}BeaconBulb', m['lamp_amber'], 0.02, lamp + Vector((0, 0, 0.03)), 10),
                                      sphere(f'{p}BeaconHalo', m['glow_amber'], 0.045, lamp + Vector((0, 0, 0.03)), 10)],
                       lamp + Vector((0, 0, 0.03)))
    beacon_base = cylinder(f'{p}BeaconBase', m['steel'], 0.018, 0.03, lamp + Vector((0, 0, 0.012)), segments=10, bevel=0)
    # the front half (hull, details, wheels) stays as the crane in the construction yard,
    # the rear half (rear: hull, details and wheels) goes into the hall
    return {'hull': hull, 'details': [details, beacon_base], 'wheels': wheels,
            'rear': [rear_shell, details_rear, *wheels_rear],
            'boom': boom_shell, 'boom_details': boom_details, 'beacon': beacon}


def build():
    kit.COLLECTION = 'GDIMCV'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = kit.IDLE_END

    m = materials()
    root = kit.empty('MCV')
    root['walkSpeed'] = round(WALK_SPEED, 4)
    body = kit.parent(kit.empty('Body'), root)   # rocks while driving
    parts = vehicle(m, root)
    for obj in (*parts['hull'], *parts['details'], *[o for o in parts['rear'] if 'Wheel' not in o.name], parts['boom'], parts['beacon']):
        kit.parent(obj, body)
    kit.parent(parts['boom_details'], parts['boom'])
    parts['wheels'] += [o for o in parts['rear'] if 'Wheel' in o.name]
    for w in parts['wheels']:
        kit.parent(w, root)

    keys = kit.keys
    kit.blink(parts['beacon'], kit.flashes((0, 10), (30, 10)))
    kit.to_track(parts['beacon'], 'Idle')
    for w in parts['wheels']:
        # positive about x: the top of the wheel moves forward (-y)
        keys(w, 'rotation_euler', {f: Vector((2 * math.pi * f / WALK_FRAMES, 0, 0)) for f in range(0, WALK_FRAMES + 1, 2)} |
             {WALK_FRAMES: Vector((2 * math.pi, 0, 0))}, 'LINEAR')
        kit.to_track(w, 'Walk')
    keys(body, 'location', {f: Vector((0, 0, 0.005 * math.sin(4 * math.pi * f / WALK_FRAMES))) for f in range(WALK_FRAMES + 1)}, 'LINEAR')
    kit.to_track(body, 'Walk')
    return len(kit.collection().objects)


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(512)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)


if __name__ == '__main__' and bpy.app.background:
    main()
