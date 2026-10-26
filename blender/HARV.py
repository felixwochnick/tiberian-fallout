"""
Tiberian Fallout – GDI harvester (HARV), after Tiberian Sun.

A heavy truck on five axles, made of two parts, like the original:
  * the tractor in front: a tall cab-over cab, as high as the container, with a wide
    windscreen, doors with windows, mirrors, a light bar and a beacon on the roof,
    exhaust stacks behind it. Low in its nose the dark mouth of the collector with
    the toothed drum, in front of it a rake of tines over the ground between two
    skids;
  * the container behind it on a flat bed with rollers: a big grey box with a
    corrugated roof, dark side panels in frames, house-colour posts at the back
    corners and double doors. At the refinery it is swapped: the full container
    rolls off backwards into the refinery's gate, an empty one rolls forward onto
    the bed.
The cab is in the light camouflage of the buildings, tinted with the house colour in
the game (GAPILE.camo_material); the mudguards and the container's corner posts are
in the house colour.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle     loop, 2 s: the beacon blinks
    Walk     loop: driving, the wheels turn (one turn per loop), the body rocks a
             little; the root's walkSpeed (glTF extras) is the ground speed in cells
             per second at which the wheels do not slip
    Harvest  loop, 1 s: the drum turns, the body shakes (not used by the game yet)
    Unload   once, 4.5 s: docked with its back in the refinery's gate, the container
             lifts off its locks, rolls back into the refinery, and a new one rolls
             forward onto the bed (not used by the game yet)

Run headless:

    Blender -b --factory-startup --python blender/HARV.py [-- --preview <dir>]

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
import walker  # noqa: E402 – hold(), export(), previews()

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'HARV.glb')
BLEND = os.path.join(HERE, 'HARV.blend')

WHEEL_RADIUS = 0.08
WHEEL_X = 0.27                          # the wheels' middle (x)
WHEEL_WIDTH = 0.07
AXLES = (-0.42, -0.25, 0.1, 0.28, 0.46)  # two under the cab, three under the container
WALK_FRAMES = 30        # one turn of the wheels
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
HARVEST_FRAMES = 30
UNLOAD_FRAMES = 135
DRUM = Vector((0, -0.64, 0.125))      # in the collector's mouth
CAB_FRONT = -0.56
NOSE = -0.62                           # the collector's front, low in the cab's nose
CAB_BACK = -0.2
BED = (-0.19, 0.6, 0.15, 0.19)          # flat bed: front, back, bottom, top
CONTAINER = (-0.17, 0.6, 0.19, 0.47)    # front, back, bottom, top
SWAP = 1.35             # how far the container rolls back: all of it into the refinery
ROUND = 0.04            # radius of the rounded top edges of the cab and the container

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'tyre': material('Tyre', srgb('#25231f'), 0.9, 0.1),
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'hold': material('HoldGrey', srgb('#8f918c'), 0.6, 0.3),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'mirror': material('Mirror', srgb('#9fb3c2'), 0.15, 0.9),
    })
    return m


def round_top(obj, radius=ROUND, bevel=0.012):
    """Rounds the edges round the top face of a solid made without a bevel, then
    bevels the other edges a little, as finish() does."""
    mesh = obj.data
    top = max(v.co.z for v in mesh.vertices)
    weight = mesh.attributes.new('bevel_weight_edge', 'FLOAT', 'EDGE')
    for edge in mesh.edges:
        weight.data[edge.index].value = float(all(mesh.vertices[i].co.z > top - 1e-5 for i in edge.vertices))
    mod = obj.modifiers.new('Round', 'BEVEL')
    mod.width, mod.segments, mod.limit_method = radius, 5, 'WEIGHT'
    mod = obj.modifiers.new('Bevel', 'BEVEL')
    mod.width, mod.segments, mod.limit_method, mod.angle_limit = bevel, 2, 'ANGLE', math.radians(35)
    mod.harden_normals = True
    return obj


def wheel(m, name, centre):
    """A big tyre with tread lugs and a bolted rim, turning about x."""
    s = 1 if centre.x > 0 else -1
    face = Vector((s * WHEEL_WIDTH / 2, 0, 0))
    parts = [cylinder(f'{name}Tyre', m['tyre'], WHEEL_RADIUS - 0.007, WHEEL_WIDTH, centre, rotation=(0, math.pi / 2, 0), segments=20,
                      bevel=0.008),
             cylinder(f'{name}Rim', m['steel_light'], WHEEL_RADIUS * 0.55, WHEEL_WIDTH + 0.004, centre, rotation=(0, math.pi / 2, 0),
                      segments=14, bevel=0.003),
             cylinder(f'{name}Cap', m['steel'], 0.016, WHEEL_WIDTH + 0.014, centre, rotation=(0, math.pi / 2, 0), segments=10, bevel=0.002)]
    for k in range(14):  # lugs across the tread
        a = 2 * math.pi * k / 14
        d = Vector((0, math.cos(a), math.sin(a)))
        parts.append(box(f'{name}Lug{k}', m['tyre'], (WHEEL_WIDTH - 0.01, 0.016, 0.014), centre + d * (WHEEL_RADIUS - 0.007), bevel=0.002,
                         rotation=(a, 0, 0)))
    for k in range(5):  # wheel nuts round the cap, so the turning shows
        a = 2 * math.pi * k / 5
        d = Vector((0, math.cos(a), math.sin(a)))
        parts.append(cylinder(f'{name}Nut{k}', m['dark'], 0.006, 0.012, centre + face + d * 0.026, rotation=(0, math.pi / 2, 0), segments=6,
                              bevel=0))
    return kit.merge(name, parts, centre)


# --------------------------------------------------------------------------- parts

def chassis(m):
    """Frame, axles, springs, the flat bed with rollers and locks, mudguards, bumper."""
    front, back, bottom, top = BED
    parts = [
        *[box(f'Rail{s}', m['dark'], (0.06, 1.18, 0.06), (s * 0.12, 0.0, 0.13), bevel=0.006) for s in (-1, 1)],
        *[box(f'CrossMember{k}', m['dark'], (0.3, 0.04, 0.04), (0, y, 0.13), bevel=0.004) for k, y in enumerate((-0.5, -0.1, 0.2, 0.55))],
        box('Bed', m['steel'], (0.5, back - front, top - bottom), (0, (front + back) / 2, (top + bottom) / 2), bevel=0.006),
    ]
    for k, y in enumerate(AXLES):
        parts += [
            cylinder(f'Axle{k}', m['dark'], 0.018, 2 * WHEEL_X - 0.04, (0, y, WHEEL_RADIUS), rotation=(0, math.pi / 2, 0), segments=8, bevel=0),
            *[box(f'Spring{k}{s}', m['steel'], (0.04, 0.13, 0.02), (s * 0.16, y, WHEEL_RADIUS + 0.028), bevel=0.003) for s in (-1, 1)],
            *[beam(f'Hanger{k}{s}', m['steel'], (s * 0.16, y, WHEEL_RADIUS + 0.03), (s * 0.13, y, 0.13), 0.02) for s in (-1, 1)],
        ]
    # rollers in the bed, guide rails along its edges, twist locks at the corners
    for k in range(6):
        y = front + 0.07 + k * (back - front - 0.14) / 5
        parts.append(cylinder(f'Roller{k}', m['steel_light'], 0.012, 0.44, (0, y, top - 0.004), rotation=(0, math.pi / 2, 0), segments=8,
                              bevel=0))
    for s in (-1, 1):
        parts.append(box(f'GuideRail{s}', m['steel_light'], (0.012, back - front, 0.03), (s * 0.268, (front + back) / 2, top + 0.01),
                         bevel=0.002))
        for y in (front + 0.04, back - 0.04):
            parts.append(box(f'Lock{s}{y:.2f}', m['hazard'], (0.03, 0.03, 0.02), (s * 0.235, y, top + 0.005), bevel=0.003))
    # mudguards over the wheels in the house colour, with an apron down the outside
    for name, y0, y1 in (('Cab', -0.5, -0.165), ('Bed', 0.0, 0.56)):
        for s in (-1, 1):
            parts += [
                box(f'Guard{name}{s}', m['remap'], (0.11, y1 - y0, 0.02), (s * WHEEL_X, (y0 + y1) / 2, 0.177), bevel=0.005),
                box(f'Apron{name}{s}', m['remap'], (0.012, y1 - y0 - 0.02, 0.05), (s * (WHEEL_X + 0.052), (y0 + y1) / 2, 0.158), bevel=0.003),
                box(f'GuardStrut{name}{s}', m['dark'], (0.06, 0.02, 0.02), (s * 0.19, (y0 + y1) / 2, 0.168), bevel=0.002),
            ]
            parts.append(box(f'MudFlap{name}{s}', m['dark'], (0.08, 0.008, 0.09), (s * WHEEL_X, y1 - 0.006, 0.1), bevel=0.002))
    # the rear bumper in warning stripes, tail lights at its ends, a tow hook
    parts.append(box('Bumper', m['dark'], (0.5, 0.04, 0.05), (0, 0.6, 0.1), bevel=0.006))
    for k in range(4):
        parts.append(box(f'BumperStripe{k}', m['hazard'] if k % 2 == 0 else m['dark'], (0.075, 0.006, 0.04), (-0.1125 + k * 0.075, 0.622, 0.1),
                         bevel=0))
    for s in (-1, 1):
        parts += detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.2, 0.622, 0.1), (0, 1, 0), 0.014)
    parts.append(cylinder('TowHook', m['steel'], 0.018, 0.04, (0, 0.63, 0.065), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0))
    return kit.merge('Chassis', parts)


def tractor(m, root):
    """The cab (camouflaged) and its fittings, the collector's mouth, rake and skids;
    returns (cab, details). The drum turns on its own."""
    _, _, _, top = CONTAINER
    cab = kit.merge('Cab', [
        # cab-over: a tall block with a slightly raked front, as high as the container
        round_top(kit.hexahedron('Cab', m['remap'], (
            (-0.27, CAB_FRONT, 0.17), (0.27, CAB_FRONT, 0.17), (0.27, CAB_BACK, 0.17), (-0.27, CAB_BACK, 0.17),
            (-0.26, CAB_FRONT + 0.03, top), (0.26, CAB_FRONT + 0.03, top), (0.26, CAB_BACK, top), (-0.26, CAB_BACK, top)), bevel=0), bevel=0.014),
        # the nose round the collector, low in front of the cab
        kit.hexahedron('Nose', m['remap'], (
            (-0.26, NOSE, 0.035), (0.26, NOSE, 0.035), (0.26, -0.5, 0.035), (-0.26, -0.5, 0.035),
            (-0.26, NOSE + 0.02, 0.3), (0.26, NOSE + 0.02, 0.3), (0.26, CAB_FRONT + 0.01, 0.3), (-0.26, CAB_FRONT + 0.01, 0.3)), bevel=0.012),
    ])
    cab.data.materials.clear()
    cab.data.materials.append(kit.camo_material('Camo_Cab', root))

    def front(z):  # the cab's raked front (y) at height z
        return CAB_FRONT + (z - 0.17) / (top - 0.17) * 0.03

    rake = math.atan2(0.03, top - 0.17)
    parts = [
        box('RoofHatch', m['steel'], (0.16, 0.13, 0.016), (0.1, -0.31, top + 0.006), bevel=0.004),
        box('CabBack', m['dark'], (0.44, 0.012, 0.22), (0, CAB_BACK + 0.004, 0.32), bevel=0.003),
        # the collector's dark mouth, the rake of tines over the ground, skids at its sides
        box('Mouth', m['dark'], (0.42, 0.03, 0.17), (0, NOSE - 0.003, 0.155), bevel=0.004),
        box('MouthLip', m['steel'], (0.46, 0.04, 0.025), (0, NOSE - 0.01, 0.255), bevel=0.004),
        box('RakeBar', m['steel'], (0.48, 0.04, 0.03), (0, NOSE - 0.03, 0.045), bevel=0.005),
    ]
    for k in range(7):  # the tines, turned up a little at their tips
        x = -0.21 + k * 0.07
        parts += [box(f'Tine{k}', m['steel_light'], (0.028, 0.2, 0.022), (x, NOSE - 0.13, 0.03), bevel=0.004),
                  box(f'TineTip{k}', m['steel_light'], (0.024, 0.05, 0.02), (x, NOSE - 0.245, 0.042), bevel=0.004,
                      rotation=(math.radians(-25), 0, 0))]
    for s in (-1, 1):
        parts += [
            kit.hexahedron(f'Skid{s}', m['steel'], (
                (s * 0.24, NOSE + 0.02, 0.01), (s * 0.27, NOSE + 0.02, 0.01), (s * 0.27, NOSE - 0.26, 0.03), (s * 0.24, NOSE - 0.26, 0.03),
                (s * 0.24, NOSE + 0.02, 0.2), (s * 0.27, NOSE + 0.02, 0.2), (s * 0.27, NOSE - 0.2, 0.09), (s * 0.24, NOSE - 0.2, 0.09)), bevel=0.004),
            *detail.rivets(f'SkidBolts{s}', m['steel_light'], (s * 0.272, NOSE - 0.01, 0.15), (s * 0.272, NOSE - 0.13, 0.09), 3, axis='X'),
            # headlights at the nose's top corners, above the mouth
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.215, NOSE - 0.002, 0.28), (0, -1, 0), 0.016),
            # windscreen in two panes, a door with its window on each side
            box(f'Window{s}', m['glass'], (0.22, 0.012, 0.085), (s * 0.12, front(0.4) - 0.003, 0.4), bevel=0.004, rotation=(-rake, 0, 0)),
            box(f'SideWindow{s}', m['glass'], (0.012, 0.13, 0.075), (s * 0.262, -0.42, 0.4), bevel=0.003),
            *detail.seam(f'DoorFront{s}', m['seam'], (s * 0.266, -0.5, 0.2), (s * 0.262, -0.5, 0.44)),
            *detail.seam(f'DoorBack{s}', m['seam'], (s * 0.266, -0.32, 0.2), (s * 0.262, -0.32, 0.44)),
            *detail.seam(f'DoorTop{s}', m['seam'], (s * 0.262, -0.5, 0.44), (s * 0.262, -0.32, 0.44)),
            box(f'DoorHandle{s}', m['steel_light'], (0.012, 0.04, 0.01), (s * 0.272, -0.36, 0.33), bevel=0.002),
            box(f'Step{s}', m['steel_light'], (0.04, 0.07, 0.01), (s * 0.29, -0.335, 0.2), bevel=0.002),
            beam(f'Handrail{s}', m['steel_light'], (s * 0.275, -0.31, 0.22), (s * 0.275, -0.31, 0.42), 0.008),
            # mirrors on arms at the front corners
            beam(f'MirrorArm{s}', m['steel'], (s * 0.26, front(0.42) + 0.02, 0.42), (s * 0.33, front(0.42) - 0.01, 0.44), 0.008),
            box(f'Mirror{s}', m['dark'], (0.015, 0.035, 0.06), (s * 0.335, front(0.42) - 0.01, 0.42), bevel=0.003),
            box(f'MirrorGlass{s}', m['mirror'], (0.004, 0.028, 0.05), (s * 0.335, front(0.42) - 0.019, 0.42), bevel=0, rotation=(0, 0, math.pi / 2)),
            beam(f'Wiper{s}', m['dark'], (s * 0.04, front(0.36) - 0.01, 0.365), (s * 0.18, front(0.43) - 0.01, 0.43), 0.006),
            # exhaust stacks at the cab's back corners, up past the roof
            cylinder(f'Exhaust{s}', m['steel'], 0.022, 0.32, (s * 0.21, CAB_BACK - 0.025, top - 0.0), segments=10),
            cylinder(f'ExhaustTip{s}', m['dark'], 0.026, 0.02, (s * 0.21, CAB_BACK - 0.025, top + 0.165), segments=10, bevel=0),
            *[cylinder(f'HeatShield{s}{k}', m['steel_light'], 0.027, 0.025, (s * 0.21, CAB_BACK - 0.025, z), segments=10, bevel=0)
              for k, z in enumerate((top + 0.04, top + 0.11))],
        ]
    parts += [
        # a pillar between the panes, a sun visor over them, the grille below
        box('Pillar', m['dark'], (0.02, 0.014, 0.09), (0, front(0.4) - 0.004, 0.4), bevel=0.002, rotation=(-rake, 0, 0)),
        box('Visor', m['steel'], (0.5, 0.06, 0.012), (0, front(top - ROUND) - 0.02, top - ROUND - 0.006), bevel=0.003),
        *detail.grille('Grille', m['steel'], m['dark'], (0, front(0.33) - 0.004, 0.33), 0.3, 0.05, 'Y', 4, 0.01),
        # on the roof: light bar, antenna, air conditioner
        box('LightBar', m['dark'], (0.3, 0.04, 0.02), (0, -0.46, top + 0.01), bevel=0.003),
        *[part for k in range(4) for part in detail.lamp(f'RoofLight{k}', m['steel'], m['lamp_white'], (-0.105 + k * 0.07, -0.484, top + 0.012),
                                                           (0, -1, 0), 0.011)],
        beam('Antenna', m['steel'], (-0.19, -0.27, top + 0.01), (-0.2, -0.25, top + 0.33), 0.005),
        cylinder('AntennaBase', m['dark'], 0.012, 0.02, (-0.19, -0.27, top + 0.02), segments=8, bevel=0),
        box('AirCon', m['steel'], (0.1, 0.08, 0.04), (-0.1, -0.32, top + 0.02), bevel=0.005),
        *detail.grille('AirConGrille', m['steel'], m['dark'], (-0.1, -0.361, top + 0.02), 0.08, 0.03, 'Y', 3, 0.006),
    ]
    return cab, kit.merge('CabDetails', parts)


def container(m):
    """The swappable container; origin in the middle of its floor (it rolls along y)."""
    front, back, bottom, top = CONTAINER
    parts = [
        round_top(kit.hexahedron('Container', m['hold'], (
            (-0.26, front, bottom), (0.26, front, bottom), (0.26, back, bottom), (-0.26, back, bottom),
            (-0.25, front, top), (0.25, front, top), (0.25, back, top), (-0.25, back, top)), bevel=0), bevel=0.01),
        # double doors at the back, with locking bars and a warning stripe
        box('DoorSeam', m['seam'], (0.006, 0.006, top - bottom - ROUND - 0.02), (0, back + 0.002, (top + bottom - ROUND) / 2), bevel=0),
        box('DoorStripe', m['hazard'], (0.42, 0.006, 0.03), (0, back + 0.003, bottom + 0.05), bevel=0),
    ]
    for k, x in enumerate((-0.15, -0.05, 0.05, 0.15)):
        parts += [beam(f'LockBar{k}', m['steel_light'], (x, back + 0.01, bottom + 0.02), (x, back + 0.01, top - ROUND), 0.01),
                  box(f'LockHandle{k}', m['steel'], (0.012, 0.014, 0.04), (x + 0.012, back + 0.016, bottom + 0.13), bevel=0.002)]
    # the corrugated roof: ridges across it from end to end
    count = 11
    for k in range(count):
        y = front + ROUND + 0.02 + k * (back - front - 2 * ROUND - 0.04) / (count - 1)
        parts.append(box(f'Ridge{k}', m['steel_light'], (0.5 - 2 * ROUND - 0.01, 0.03, 0.026), (0, y, top + 0.008), bevel=0.006))
    # house-colour posts at the back corners, grey ones at the front
    for s in (-1, 1):
        parts += [
            box(f'BackPost{s}', m['remap'], (0.04, 0.04, top - bottom - ROUND), (s * 0.244, back - 0.016, (top + bottom - ROUND) / 2), bevel=0.005),
            box(f'FrontPost{s}', m['steel'], (0.035, 0.035, top - bottom - ROUND), (s * 0.245, front + 0.016, (top + bottom - ROUND) / 2), bevel=0.005),
        ]
        # a dark side panel in two fields, framed in grey, rivets along the bottom
        x = s * 0.259
        y0, y1 = front + 0.06, back - 0.07
        mid = (y0 + y1) / 2
        parts += [
            box(f'Panel{s}', m['dark'], (0.008, y1 - y0, 0.17), (x, mid, 0.33), bevel=0.002),
            box(f'FrameTop{s}', m['steel'], (0.016, y1 - y0 + 0.03, 0.022), (x, mid, 0.425), bevel=0.003),
            box(f'FrameLow{s}', m['steel'], (0.016, y1 - y0 + 0.03, 0.022), (x, mid, 0.235), bevel=0.003),
            *[box(f'FramePost{s}{k}', m['steel'], (0.016, 0.026, 0.19), (x, y, 0.33), bevel=0.003) for k, y in enumerate((y0, mid, y1))],
            *[box(f'PanelRib{s}{k}', m['steel'], (0.012, 0.016, 0.15), (x, y, 0.33), bevel=0.002)
              for k, y in enumerate((y0 + (mid - y0) / 3, y0 + 2 * (mid - y0) / 3, mid + (y1 - mid) / 3, mid + 2 * (y1 - mid) / 3))],
            box(f'Plate{s}', m['remap'], (0.006, 0.12, 0.03), (s * 0.262, front + 0.13, 0.205), bevel=0.002),
        ]
        parts += detail.rivets(f'RivetLow{s}', m['steel_light'], (s * 0.262, front + 0.05, bottom + 0.022), (s * 0.262, back - 0.05, bottom + 0.022),
                               12, axis='X')
    # corner castings at the bottom (where the locks take hold)
    for x in (-0.245, 0.245):
        for y in (front + 0.02, back - 0.02):
            parts.append(box(f'Corner{x}{y}', m['dark'], (0.042, 0.042, 0.03), (x, y, bottom + 0.015), bevel=0.004))
    # a ladder up the back right
    parts += detail.ladder('Ladder', m['steel_light'], (0.2, back + 0.02, bottom + 0.03), (0.2, back + 0.02, top - 0.01), 0.05, 6, out=(0, 0.012, 0))
    return kit.merge('Container', parts, (0, (front + back) / 2, bottom))


def drum(m):
    """The collector drum with its rows of teeth; origin on its axle (it turns about x)."""
    parts = [cylinder('Drum', m['steel'], 0.045, 0.38, DRUM, rotation=(0, math.pi / 2, 0), segments=16),
             cylinder('DrumAxle', m['dark'], 0.02, 0.42, DRUM, rotation=(0, math.pi / 2, 0), segments=10, bevel=0)]
    for k in range(8):
        a = 2 * math.pi * k / 8
        d = Vector((0, math.cos(a), math.sin(a)))
        for i in range(4):
            x = -0.15 + i * 0.1 + (0.05 if k % 2 else 0)
            parts.append(beam(f'Tooth{k}_{i}', m['steel_light'], DRUM + Vector((x, 0, 0)) + d * 0.04, DRUM + Vector((x, 0, 0)) + d * 0.068, 0.018, 0.012))
    return kit.merge('Drum', parts, DRUM)


# --------------------------------------------------------------------------- model

def build():
    kit.COLLECTION = 'GDIHarvester'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = kit.IDLE_END

    m = materials()
    root = kit.empty('Harvester')
    root['walkSpeed'] = round(WALK_SPEED, 4)
    body = kit.parent(kit.empty('Body'), root)   # rocks while driving, shakes while harvesting
    kit.parent(chassis(m), body)
    for obj in tractor(m, root):
        kit.parent(obj, body)
    roller = kit.parent(drum(m), body)
    load = kit.parent(container(m), body)
    rest = load.location.copy()
    lamp = Vector((0.1, -0.31, CONTAINER[3] + 0.045))
    kit.parent(cylinder('BeaconBase', m['steel'], 0.018, 0.03, lamp - Vector((0, 0, 0.02)), segments=10, bevel=0), body)
    beacon = kit.parent(kit.merge('Beacon', [sphere('BeaconBulb', m['lamp_amber'], 0.02, lamp, 10),
                                             sphere('BeaconHalo', m['glow_amber'], 0.045, lamp, 10)], lamp), body)
    wheels = []
    for s in (-1, 1):
        for k, y in enumerate(AXLES):
            wheels.append(kit.parent(wheel(m, f'Wheel{s}{k}', Vector((s * WHEEL_X, y, WHEEL_RADIUS))), root))

    keys = kit.keys
    still = Vector((0, 0, 0))
    # Idle: the beacon blinks
    kit.blink(beacon, kit.flashes((0, 10), (30, 10)))
    kit.to_track(beacon, 'Idle')
    # Walk: the wheels turn, the body rocks
    for w in wheels:
        # positive about x: the top of the wheel moves forward (-y)
        keys(w, 'rotation_euler', {f: Vector((2 * math.pi * f / WALK_FRAMES, 0, 0)) for f in range(0, WALK_FRAMES + 1, 2)} |
             {WALK_FRAMES: Vector((2 * math.pi, 0, 0))}, 'LINEAR')
        kit.to_track(w, 'Walk')
    keys(body, 'location', {f: Vector((0, 0, 0.005 * math.sin(4 * math.pi * f / WALK_FRAMES))) for f in range(WALK_FRAMES + 1)}, 'LINEAR')
    kit.to_track(body, 'Walk')
    # Harvest: the drum turns against the driving direction, the body shakes
    keys(roller, 'rotation_euler', {0: still, HARVEST_FRAMES: Vector((-2 * math.pi, 0, 0))}, 'LINEAR')
    kit.to_track(roller, 'Harvest')
    keys(body, 'location', {f: Vector((0.002 * math.sin(f * 2.1), 0, 0.003 * math.sin(f * 3.3))) for f in range(HARVEST_FRAMES)} |
         {HARVEST_FRAMES: still}, 'LINEAR')
    kit.to_track(body, 'Harvest')
    # Unload: the container lifts off its locks, rolls back into the refinery (out of
    # sight there), the next one rolls forward and settles on the locks
    lift, away = Vector((0, 0, 0.012)), Vector((0, SWAP, 0.012))
    keys(load, 'location', {0: rest, 6: rest + lift, 50: rest + away, 70: rest + away, 114: rest + lift, 120: rest, UNLOAD_FRAMES: rest})
    kit.to_track(load, 'Unload')
    # the container sits on the bed in the other clips (the exporter's pose would leak in otherwise)
    for clip, frames in (('Idle', kit.IDLE_END), ('Walk', WALK_FRAMES), ('Harvest', HARVEST_FRAMES)):
        walker.hold(load, 'location', rest, frames, clip)
    load.location = rest
    roller.rotation_euler = still
    body.location = still
    for w in wheels:
        w.rotation_euler = still
    return len(kit.collection().objects)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(512)
    if '--preview' in args:
        walker.previews(args[args.index('--preview') + 1], {'Idle': [0], 'Unload': [30, 60]}, scale=1.9, target=(0, 0.2, 0.25))
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    print('export', walker.export(OUT), flush=True)


if __name__ == '__main__' and bpy.app.background:
    main()
