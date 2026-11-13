"""
Tiberian Fallout – mobile sensor array (LPST), after Tiberian Sun (GDI's, Nod builds it too).

A six-wheeled truck: a bulky armoured cab in front (two grilles with upright slats and
a round emblem in its nose, a narrow windscreen under a visor, three lamps on a bar on
its roof, a door with a window on each side), big boxy fairings over the front wheels
and over the two rear axles, house-colour stripes along them; between the rear
fairings the flat bed with a long equipment box on the left, two operator seats on the
right and at the back the tall sensor box with grilles, a ladder and a whip antenna.
On the sensor box sits the sensor head: a faceted dark dome with a ring round it, a
warning light and the folded radar panel on top. Four outriggers are stowed at the
corners, their jacks by the cab's nose and behind the rear fairings. The cab, the
fairings and the boxes are in the light camouflage of the buildings, tinted with the
house colour in the game (GAPILE.camo_material).

Deployed (like the original's, it reveals the map around it), the outriggers slide out
and their jacks press down and lift the truck a little, the telescopic mast in the
sensor box raises the head, its top section runs out, the radar panel unfolds, and
the head turns round and round, its light blinking.

Nodes: "Mast" (the lower section of the mast, rising out of the sensor box),
"MastTop" (the inner section), "Sensor" (the head, turning about the mast), "Dish"
(the radar panel), "Outrigger…" (the arms, sliding out) with "Jack…" (their rods,
running down).
Clips (see nodvehicle.py for Idle and Walk):
    Idle       loop, 2 s: the engine runs, the body shivers a little
    Walk       loop: driving, the wheels turn (one turn per loop), the body rocks; the
               root's walkSpeed (glTF extras) is the ground speed in cells per second
    Deploy     once, 2 s: outriggers down, mast up, top section out, panel open
    Deployed   loop, 2 s: the head turns once round, the light blinks
    Undeploy   once, 2 s: Deploy backwards

Run headless:

    blender -b --factory-startup --python blender/LPST.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'LPST.glb')
BLEND = os.path.join(HERE, 'LPST.blend')

WHEEL_RADIUS = 0.075
WHEEL_X = 0.245
WHEEL_WIDTH = 0.07
AXLES = (-0.3, 0.14, 0.31)
WALK_FRAMES = 28
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
CAB = (-0.53, -0.17, 0.13, 0.4)     # front, back, bottom, top
CAB_HALF = 0.215
FAIRINGS = ((-0.41, -0.19), (0.04, 0.42))   # front and rear fairing: front, back
FAIRING_X = (0.165, 0.315)          # their inner and outer side
FAIRING_Z = (0.11, 0.28)            # their bottom and top
BED = (-0.17, 0.47, 0.25)           # the flat bed: front, back, top
BOX = (0.22, 0.47, 0.36)            # the sensor box at the back: front, back, top
PIVOT = Vector((0.04, 0.34, 0.12))  # the foot of the mast (stowed) in the sensor box
MAST = (0.035, 0.25)                # lower section: half width, length
TOP = (0.025, 0.25, 0.19)           # inner section: half width, length, how far it runs out
TOP_BASE = 0.02                     # the inner section's foot above the lower one's
RISE = 0.22                         # how far the lower section rises out of the box
OUTRIGGERS = (-0.46, 0.46)          # the outriggers' y
OUTRIGGER_HINGE = (0.245, 0.15)     # the stowed jack's x (less its offset), the arm's z
OUTRIGGER_REACH = 0.12              # how far the arms slide out (x)
LIFT = 0.03                         # how much the outriggers lift the truck
JACK = 0.07                        # from the arm down to the bottom of the stowed jack's pad
DEPLOY_FRAMES = 60
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'tyre': material('Tyre', srgb('#25231f'), 0.9, 0.1),
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'dome': material('SensorDome', srgb('#3c4147'), 0.35, 0.5),
        'dish': material('DishWhite', srgb('#d9d6cc'), 0.5, 0.2),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
    })
    return m


def camo(obj, root):
    """The light camouflage (baked; tinted with the house colour in the game)."""
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def slatted(name, m, centre, width, height, slats):
    """A grille with upright slats in a face looking along -y."""
    centre = Vector(centre)
    parts = [box(f'{name}Frame', m['steel'], (width + 0.014, 0.012, height + 0.014), centre, bevel=0.002),
             box(f'{name}Back', m['dark'], (width, 0.014, height), centre - Vector((0, 0.001, 0)), bevel=0)]
    for k in range(slats):
        x = -width / 2 + (k + 0.5) * width / slats
        parts.append(box(f'{name}Slat{k}', m['steel_light'], (width / slats * 0.4, 0.018, height), centre + Vector((x, -0.002, 0)), bevel=0))
    return parts


def fairing(m, s, y0, y1):
    """A boxy wheel fairing (camouflaged): open below, its ends sloped back at the top,
    its outer top edge chamfered."""
    x0, x1 = s * FAIRING_X[0], s * FAIRING_X[1]
    z0, z1 = FAIRING_Z
    return kit.hexahedron(f'Fairing{s}{y0}', m['sand'], (
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0 + 0.035, z1), (x1 - s * 0.02, y0 + 0.035, z1), (x1 - s * 0.02, y1 - 0.035, z1), (x0, y1 - 0.035, z1)), bevel=0.014)


def truck(m, root):
    """Cab, fairings, bed and boxes (camouflaged) and their fittings."""
    f, b, z0, z1 = CAB
    bf, bb, bz = BED
    xf, xb, xz = BOX
    w = CAB_HALF
    shells = [
        kit.hexahedron('Cab', m['sand'], (
            (-w, f, z0), (w, f, z0), (w, b, z0), (-w, b, z0),
            (-w + 0.015, f + 0.04, z1), (w - 0.015, f + 0.04, z1), (w - 0.015, b - 0.01, z1), (-w + 0.015, b - 0.01, z1)), bevel=0.018),
        kit.hexahedron('Bed', m['sand'], (
            (-0.2, bf, 0.13), (0.2, bf, 0.13), (0.2, bb, 0.13), (-0.2, bb, 0.13),
            (-0.2, bf, bz), (0.2, bf, bz), (0.2, bb, bz), (-0.2, bb, bz)), bevel=0.01),
        kit.hexahedron('SensorBox', m['sand'], (
            (-0.17, xf, bz - 0.01), (0.17, xf, bz - 0.01), (0.17, xb, bz - 0.01), (-0.17, xb, bz - 0.01),
            (-0.16, xf + 0.01, xz), (0.16, xf + 0.01, xz), (0.16, xb - 0.01, xz), (-0.16, xb - 0.01, xz)), bevel=0.012),
        kit.hexahedron('LongBox', m['sand'], (
            (-0.195, -0.14, bz - 0.01), (-0.075, -0.14, bz - 0.01), (-0.075, 0.2, bz - 0.01), (-0.195, 0.2, bz - 0.01),
            (-0.19, -0.135, bz + 0.08), (-0.08, -0.135, bz + 0.08), (-0.08, 0.195, bz + 0.08), (-0.19, 0.195, bz + 0.08)), bevel=0.01),
    ]
    for s in (-1, 1):
        for y0, y1 in FAIRINGS:
            shells.append(fairing(m, s, y0, y1))
    shell = camo(kit.merge('Hull', shells), root)

    rake = math.atan2(0.04, z1 - z0)

    def nose(z):  # just before the cab's front at height z
        return f + (z - z0) / (z1 - z0) * 0.04 - 0.004

    parts = [
        box('Frame', m['dark'], (0.3, bb - f - 0.04, 0.05), (0, (f + bb) / 2, 0.11), bevel=0.006),
        *[cylinder(f'Axle{k}', m['dark'], 0.018, 2 * WHEEL_X - 0.05, (0, y, WHEEL_RADIUS), rotation=(0, math.pi / 2, 0), segments=8, bevel=0)
          for k, y in enumerate(AXLES)],
        # the cab's nose: two slatted grilles, the emblem between them, a bumper, lights
        *slatted('GrilleL', m, (-0.115, nose(0.26), 0.26), 0.13, 0.12, 6),
        *slatted('GrilleR', m, (0.115, nose(0.26), 0.26), 0.13, 0.12, 6),
        cylinder('Emblem', m['remap'], 0.03, 0.012, (0, nose(0.27), 0.27), rotation=(math.pi / 2 - rake, 0, 0), segments=16, bevel=0.002),
        cylinder('EmblemRim', m['steel'], 0.036, 0.008, (0, nose(0.27) + 0.003, 0.27), rotation=(math.pi / 2 - rake, 0, 0), segments=16, bevel=0),
        box('Bumper', m['dark'], (0.46, 0.05, 0.06), (0, f - 0.016, 0.14), bevel=0.008),
        *[box(f'BumperStripe{k}', m['hazard'] if k % 2 == 0 else m['dark'], (0.05, 0.006, 0.04), (-0.125 + k * 0.05, f - 0.043, 0.14), bevel=0)
          for k in range(6)],
        *[box(f'TowHook{s}', m['steel'], (0.03, 0.04, 0.03), (s * 0.19, f - 0.035, 0.14), bevel=0.004) for s in (-1, 1)],
        # windscreen under a visor, a pillar
        box('Windscreen', m['glass'], (0.36, 0.012, 0.05), (0, nose(0.35), 0.35), bevel=0.004, rotation=(-rake, 0, 0)),
        box('Pillar', m['steel'], (0.016, 0.014, 0.05), (0, nose(0.35) - 0.002, 0.35), bevel=0.002, rotation=(-rake, 0, 0)),
        box('Visor', m['steel'], (0.4, 0.045, 0.014), (0, nose(z1) + 0.012, z1 - 0.022), bevel=0.003),
        # the roof: three lamps on a bar, a hatch, a vent
        box('LampBar', m['steel'], (0.3, 0.03, 0.02), (0, f + 0.08, z1 + 0.01), bevel=0.004),
        *[box(f'LampPost{k}', m['steel'], (0.012, 0.012, 0.03), (x, f + 0.08, z1 + 0.03), bevel=0) for k, x in enumerate((-0.1, 0, 0.1))],
        *[box(f'Lamp{k}', m['steel'], (0.05, 0.04, 0.04), (x, f + 0.075, z1 + 0.058), bevel=0.006) for k, x in enumerate((-0.1, 0, 0.1))],
        *[box(f'LampGlass{k}', m['lamp_white'], (0.036, 0.006, 0.028), (x, f + 0.053, z1 + 0.058), bevel=0.002) for k, x in enumerate((-0.1, 0, 0.1))],
        box('RoofHatch', m['steel'], (0.11, 0.1, 0.012), (0.08, b - 0.1, z1 + 0.005), bevel=0.003),
        *detail.grille('RoofVent', m['steel'], m['dark'], (-0.09, b - 0.006, z1 - 0.05), 0.12, 0.05, 'Y', 3, 0.008),
        box('CabBand', m['remap'], (2 * w + 0.004, 0.02, 0.03), (0, b + 0.004, z1 - 0.12), bevel=0.003),
        # the bed: rails along its edges, two operator seats, a tool box
        *[box(f'BedRail{s}', m['steel'], (0.014, BOX[0] - bf - 0.02, 0.025), (s * 0.19, (bf + BOX[0]) / 2, bz + 0.0125), bevel=0.003) for s in (-1, 1)],
        *[part for k, y in enumerate((-0.08, 0.07)) for part in (
            box(f'Seat{k}', m['olive'], (0.08, 0.07, 0.03), (0.09, y, bz + 0.03), bevel=0.008),
            box(f'SeatBack{k}', m['olive'], (0.08, 0.02, 0.07), (0.09, y + 0.035, bz + 0.065), bevel=0.006),
            box(f'SeatPost{k}', m['steel'], (0.02, 0.02, 0.03), (0.09, y, bz + 0.008), bevel=0))],
        box('Console', m['steel'], (0.1, 0.05, 0.07), (0.09, -0.15, bz + 0.035), bevel=0.006),
        box('ConsoleScreen', m['signal'], (0.07, 0.006, 0.035), (0.09, -0.124, bz + 0.05), bevel=0, rotation=(math.radians(-20), 0, 0)),
        # the long box: its lid and latches
        box('LongBoxLid', m['sand_light'], (0.1, 0.31, 0.01), (-0.135, 0.03, bz + 0.082), bevel=0.003),
        *[box(f'Latch{k}', m['steel'], (0.006, 0.02, 0.025), (-0.074, -0.06 + k * 0.18, bz + 0.055), bevel=0) for k in range(2)],
        # the sensor box: the collar the mast comes out of, grilles, a ladder, the antenna, a stripe
        cylinder('MastCollar', m['steel'], 0.055, 0.025, (PIVOT.x, PIVOT.y, xz + 0.01), segments=16),
        cylinder('MastHole', m['dark'], 0.042, 0.006, (PIVOT.x, PIVOT.y, xz + 0.023), segments=16, bevel=0),
        *detail.grille('BoxGrille', m['steel'], m['dark'], (0, xf + 0.006, (bz + xz) / 2 + 0.005), 0.18, 0.06, 'Y', 4, 0.008),
        *detail.grille('BoxSideGrille', m['steel'], m['dark'], (0.168, (xf + xb) / 2, (bz + xz) / 2), 0.12, 0.06, 'X', 4, 0.008),
        *detail.ladder('Ladder', m['steel_light'], (-0.09, xb + 0.012, 0.12), (-0.09, xb + 0.012, xz), 0.05, 5, out=(0, 0.008, 0)),
        box('AntennaBase', m['steel'], (0.04, 0.04, 0.03), (-0.13, xb - 0.04, xz + 0.015), bevel=0.004),
        beam('Antenna', m['steel'], (-0.13, xb - 0.04, xz + 0.03), (-0.14, xb - 0.03, xz + 0.22), 0.007),
        box('BoxStripe', m['remap'], (0.33, 0.012, 0.03), (0, xb - 0.004, xz - 0.035), bevel=0.002),
        box('BackPlate', m['dark'], (0.42, 0.01, 0.06), (0, bb + 0.004, 0.17), bevel=0.002),
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.165, nose(0.18), 0.18), (0, -1, 0), 0.018),
            *detail.lamp(f'Indicator{s}', m['dark'], m['lamp_amber'], (s * 0.07, nose(0.18), 0.18), (0, -1, 0), 0.011),
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.19, bb + 0.008, 0.18), (0, 1, 0), 0.013),
            # the cab's sides: a door with its window and handle, a seam
            box(f'Door{s}', m['sand_light'], (0.01, 0.14, 0.17), (s * (w - 0.003), -0.3, 0.27), bevel=0.003),
            box(f'SideWindow{s}', m['glass'], (0.012, 0.1, 0.05), (s * (w - 0.004), -0.3, 0.33), bevel=0.003),
            box(f'DoorHandle{s}', m['steel'], (0.012, 0.035, 0.01), (s * (w + 0.003), -0.25, 0.26), bevel=0),
            *detail.seam(f'CabSeam{s}', m['seam'], (s * (w - 0.004), b + 0.03, 0.15), (s * (w - 0.012), b + 0.03, z1 - 0.02)),
            beam(f'MirrorArm{s}', m['steel'], (s * (w - 0.01), f + 0.08, z1 - 0.05), (s * (w + 0.06), f + 0.06, z1 - 0.04), 0.007),
            box(f'Mirror{s}', m['dark'], (0.014, 0.03, 0.05), (s * (w + 0.065), f + 0.06, z1 - 0.06), bevel=0.003),
            box(f'Step{s}', m['steel_light'], (0.05, 0.08, 0.01), (s * (w - 0.01), -0.17, 0.12), bevel=0.002),
        ]
        out = s * (FAIRING_X[1] + 0.001)
        for k, (y0, y1) in enumerate(FAIRINGS):
            mid = (y0 + y1) / 2
            parts += [
                # a house-colour stripe along each fairing, rivets along its top, a seam
                box(f'FairingStripe{s}{k}', m['remap'], (0.012, y1 - y0 - 0.06, 0.03), (out - s * 0.002, mid, FAIRING_Z[0] + 0.06), bevel=0.003),
                *detail.rivets(f'FairingRivets{s}{k}', m['steel_light'], (s * 0.275, y0 + 0.06, FAIRING_Z[1] + 0.002), (s * 0.275, y1 - 0.06, FAIRING_Z[1] + 0.002),
                               4 + k * 2, axis='Z'),
                *detail.seam(f'FairingSeam{s}{k}', m['seam'], (s * 0.17, mid, FAIRING_Z[1] + 0.002), (s * 0.29, mid, FAIRING_Z[1] + 0.002)),
                box(f'FairingLip{s}{k}', m['dark'], (FAIRING_X[1] - FAIRING_X[0], y1 - y0, 0.012), (s * (FAIRING_X[0] + FAIRING_X[1]) / 2, mid, FAIRING_Z[0] - 0.004),
                    bevel=0.002),
            ]
        parts += [
            *detail.grille(f'RearFairingVent{s}', m['steel'], m['dark'], (out + s * 0.002, FAIRINGS[1][0] + 0.09, 0.22), 0.1, 0.05, 'X', 3, 0.006),
            # the outriggers' sleeves
            *[box(f'OutriggerSleeve{s}{k}', m['dark'], (0.1, 0.05, 0.05), (s * 0.17, y, OUTRIGGER_HINGE[1]), bevel=0.004)
              for k, y in enumerate(OUTRIGGERS)],
        ]
    return shell, kit.merge('HullDetails', parts)


def outrigger(m, s, y):
    """An outrigger, stowed: a beam in its sleeve that slides out sideways (origin on
    its inner end), with the jack at its outer end whose rod (the second object, its
    child) runs down onto the ground."""
    x0, z = OUTRIGGER_HINGE
    end = s * (x0 + 0.035)
    side = 'R' if s > 0 else 'L'
    end_name = 'F' if y < 0 else 'B'
    arm = kit.merge(f'Outrigger{side}{end_name}', [
        box(f'Arm{s}{y}', m['steel'], (0.16, 0.036, 0.036), (s * (x0 - 0.045), y, z), bevel=0.004),
        cylinder(f'JackHousing{s}{y}', m['steel'], 0.024, 0.09, (end, y, z - 0.01), segments=12),
        cylinder(f'JackCap{s}{y}', m['dark'], 0.026, 0.012, (end, y, z + 0.04), segments=12, bevel=0),
        box(f'JackBrace{s}{y}', m['steel_light'], (0.012, 0.03, 0.07), (end - s * 0.026, y, z - 0.005), bevel=0.002),
        *[box(f'ArmStripe{s}{y}{k}', m['hazard'] if k % 2 == 0 else m['dark'], (0.03, 0.038, 0.038), (s * (x0 - 0.1 + 0.03 * k), y, z), bevel=0)
          for k in range(3)],
    ], (s * (x0 - 0.12), y, z))
    rod = kit.merge(f'Jack{side}{end_name}', [
        cylinder(f'JackRod{s}{y}', m['steel_light'], 0.015, 0.15, (end, y, z + 0.005), segments=10),
        cylinder(f'Pad{s}{y}', m['dark'], 0.036, 0.014, (end, y, z - JACK + 0.007), segments=12),
        *[box(f'PadSpike{s}{y}{k}', m['steel'], (0.012, 0.012, 0.02), (end + 0.025 * math.cos(a), y + 0.025 * math.sin(a), z - JACK + 0.001), bevel=0)
          for k, a in enumerate((0, math.pi / 2, math.pi, 3 * math.pi / 2))],
    ], (end, y, z - JACK))
    kit.parent(rod, arm)
    return arm, rod


def mast(m, body):
    """The telescopic mast in the sensor box: lower section (node Mast, on PIVOT), inner
    section (MastTop), head (Sensor) with its radar panel (Dish, built open) and light;
    all stowed. Returns the nodes and the light."""
    half, length = MAST
    lower = kit.merge('Mast', [
        box('MastTube', m['steel'], (2 * half, 2 * half, length), PIVOT + Vector((0, 0, length / 2)), bevel=0.004),
        box('MastRing', m['steel_light'], (2 * half + 0.014, 2 * half + 0.014, 0.02), PIVOT + Vector((0, 0, length - 0.01)), bevel=0.003),
        *[box(f'MastBand{k}', m['remap'], (2 * half + 0.004, 2 * half + 0.004, 0.02), PIVOT + Vector((0, 0, length - 0.06 - k * 0.06)), bevel=0)
          for k in range(2)],
        beam('MastCable', m['dark'], PIVOT + Vector((half + 0.006, 0, 0.02)), PIVOT + Vector((half + 0.006, 0, length - 0.03)), 0.008),
    ], PIVOT)
    kit.parent(lower, body)
    t_half, t_length, _ = TOP
    upper = kit.merge('MastTop', [
        box('MastTopTube', m['steel_light'], (2 * t_half, 2 * t_half, t_length), PIVOT + Vector((0, 0, TOP_BASE + t_length / 2)), bevel=0.003),
        box('MastTopRing', m['steel'], (2 * t_half + 0.012, 2 * t_half + 0.012, 0.016), PIVOT + Vector((0, 0, TOP_BASE + t_length - 0.008)), bevel=0.003),
    ], PIVOT)
    kit.parent(upper, lower)
    at = PIVOT + Vector((0, 0, TOP_BASE + t_length))
    dome = sphere('SensorDome', m['dome'], 0.075, at + Vector((0, 0, 0.06)), 10)
    dome.scale = (1, 1, 0.8)
    head = kit.merge('Sensor', [
        cylinder('SensorNeck', m['steel'], 0.032, 0.03, at + Vector((0, 0, 0.012)), segments=12),
        dome,
        cylinder('SensorRing', m['steel_light'], 0.079, 0.016, at + Vector((0, 0, 0.055)), segments=20, bevel=0.003),
        cylinder('SensorBand', m['remap'], 0.0805, 0.008, at + Vector((0, 0, 0.055)), segments=20, bevel=0),
        *[beam(f'SensorStub{s}', m['steel'], at + Vector((s * 0.07, 0.0, 0.06)), at + Vector((s * 0.1, 0.0, 0.11)), 0.006) for s in (-1, 1)],
        box('PanelRest', m['steel'], (0.06, 0.02, 0.03), at + Vector((0, 0.09, 0.1)), bevel=0.003),
    ], at)
    kit.parent(head, upper)
    hinge = at + Vector((0, -0.01, 0.118))
    panel = [
        box('PanelBack', m['steel'], (0.2, 0.014, 0.1), hinge + Vector((0, 0.002, 0.055)), bevel=0.004),
        box('PanelFace', m['dish'], (0.185, 0.006, 0.085), hinge + Vector((0, -0.007, 0.055)), bevel=0.002),
        cylinder('PanelHinge', m['steel'], 0.01, 0.06, hinge, rotation=(0, math.pi / 2, 0), segments=8, bevel=0),
    ]
    for k in range(7):  # the elements on its face
        panel.append(box(f'PanelElement{k}', m['dark'], (0.012, 0.004, 0.065), hinge + Vector((-0.075 + k * 0.025, -0.011, 0.055)), bevel=0))
    dish = kit.merge('Dish', panel, hinge)
    kit.parent(dish, head)
    housing, light = kit.beacon('SensorLamp', m, at + Vector((0.055, 0.02, 0.085)), glow='red')
    kit.parent(housing, head)
    kit.parent(light, head)
    return lower, upper, head, dish, light


def build():
    root, body = nod.start('GDISensorArray', 'SensorArray', WALK_SPEED)
    m = materials()
    for obj in truck(m, root):
        kit.parent(obj, body)
    wheels = [kit.parent(nod.wheel(m, f'Wheel{s}{k}', (s * WHEEL_X, y, WHEEL_RADIUS), WHEEL_RADIUS, WHEEL_WIDTH, lugs=14, rim=m['steel_light']), body)
              for s in (-1, 1) for k, y in enumerate(AXLES)]
    legs = []
    for s in (-1, 1):
        for y in OUTRIGGERS:
            arm, rod = outrigger(m, s, y)
            legs.append((s, kit.parent(arm, body), rod))
    lower, upper, head, dish, light = mast(m, body)
    kit.bake_camo(512)
    # folded for the road: legs up, mast down in its box, the panel folded back flat
    folded, opened = Vector((-math.pi / 2, 0, 0)), Vector((math.radians(-12), 0, 0))
    dish.rotation_euler = folded
    nod.drive(body, wheels, WALK_FRAMES, rock=0.004)

    keys = kit.keys
    still, lifted = Vector((0, 0, 0)), Vector((0, 0, LIFT))
    down, up = lower.location.copy(), lower.location + Vector((0, 0, RISE))
    stowed, out = upper.location.copy(), upper.location + Vector((0, 0, TOP[2]))
    # frame → pose; Undeploy plays the same backwards
    poses = {
        'body': (body, 'location', {0: still, 14: still, 22: lifted, DEPLOY_FRAMES: lifted}),
        'mast': (lower, 'location', {0: down, 18: down, 36: up, DEPLOY_FRAMES: up}),
        'top': (upper, 'location', {0: stowed, 34: stowed, 48: out, DEPLOY_FRAMES: out}),
        'dish': (dish, 'rotation_euler', {0: folded, 44: folded, 56: opened, DEPLOY_FRAMES: opened}),
        'head': (head, 'rotation_euler', {0: still, DEPLOY_FRAMES: still}),
    }
    drop = OUTRIGGER_HINGE[1] - JACK + LIFT      # the pads from under the arms onto the ground
    poses_rest = {obj.name: obj.location.copy() for _, arm, rod in legs for obj in (arm, rod)}
    for k, (s, arm, rod) in enumerate(legs):
        poses[f'arm{k}'] = (arm, 'location', {0: arm.location.copy(), 1 + k: arm.location.copy(),
                                               9 + k: arm.location + Vector((s * OUTRIGGER_REACH, 0, 0)),
                                               DEPLOY_FRAMES: arm.location + Vector((s * OUTRIGGER_REACH, 0, 0))})
        poses[f'rod{k}'] = (rod, 'location', {0: rod.location.copy(), 9 + k: rod.location.copy(), 17 + k: rod.location - Vector((0, 0, drop)),
                                               DEPLOY_FRAMES: rod.location - Vector((0, 0, drop))})
    for clip, order in (('Deploy', lambda f: f), ('Undeploy', lambda f: DEPLOY_FRAMES - f)):
        for obj, path, frames in poses.values():
            keys(obj, path, {order(f): v for f, v in frames.items()})
            kit.to_track(obj, clip)
    # Deployed: everything up, the head turns once round, the light blinks
    for obj, path, frames in poses.values():
        if obj is not head:
            walker.hold(obj, path, frames[DEPLOY_FRAMES], kit.IDLE_END, 'Deployed')
    keys(head, 'rotation_euler', {f: Vector((0, 0, 2 * math.pi * f / kit.IDLE_END)) for f in range(0, kit.IDLE_END + 1, 3)}, 'LINEAR')
    kit.to_track(head, 'Deployed')
    kit.blink(light, kit.flashes((0, 8), (30, 8)))
    kit.to_track(light, 'Deployed')
    walker.hide([light], DEPLOY_FRAMES, 'Deploy')
    walker.hide([light], DEPLOY_FRAMES, 'Undeploy')
    # the rest pose: on the road
    body.location, body.rotation_euler = still, still
    for _, arm, rod in legs:
        arm.location = poses_rest[arm.name]
        rod.location = poses_rest[rod.name]
    lower.location = down
    upper.location = stowed
    dish.rotation_euler = folded
    head.rotation_euler = still
    light.scale = (kit.HIDDEN,) * 3
    for w in wheels:
        w.rotation_euler = still
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Deploy': [12, 28, 45, 59], 'Deployed': [10]}, scale=2.2, target=(0, 0, 0.45))
