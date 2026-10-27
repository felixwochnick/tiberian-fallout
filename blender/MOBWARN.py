"""
Tiberian Fallout – Fist of Nod (MOBWARN), the mobile Nod war factory, after Tiberian
Sun Firestorm.

A big eight-wheeled truck as long as the MCV: in front the light grey cab with its
windscreen, grille and bumper, a beacon on its roof; behind it the folded factory, a
long red (house colour) box ribbed in dark armour under a grey roof of two halves; at
the back a grey box with the ramp door and over it a grey gantry frame, as in the
original's cameo.

When it deploys the ramp drops behind it, the two roof halves fold out and down the
sides, the dark hall of the war factory rises out of the box with its red corner
struts and lamps, and the chimneys come up; then the game puts the war factory
(NAWEAP) in its place.

Nodes: "Ramp", "Roof-1"/"Roof1" (the roof halves), "Hall", "Chimney0"/"Chimney1",
"Beacon". Clips (see nodvehicle.py for Idle and Walk; Idle also blinks the beacon):
    Deploy   once, 2 s: ramp, roof, hall, chimneys

Run headless:

    blender -b --factory-startup --python blender/MOBWARN.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'MOBWARN.glb')
BLEND = os.path.join(HERE, 'MOBWARN.blend')

WHEEL_RADIUS = 0.12
WHEEL_WIDTH = 0.1
WHEEL_X = 0.44
AXLES = (-0.64, -0.14, 0.2, 0.52)
WALK_FRAMES = 36
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
FLOOR = 0.22                 # the top of the chassis
BOX = (-0.46, 0.55)          # the factory box (y)
BOX_X = 0.34
BOX_TOP = 0.54
ROOF_TOP = 0.565
REAR = (0.58, 0.8)           # the grey rear box (y)
REAR_TOP = 0.5
RAMP = 0.28                  # the ramp door's height
RAMP_DOWN = -(math.pi - math.acos((FLOOR - 0.012) / RAMP))
ROOF_FOLD = math.radians(270)  # over, out and down the side (right side; mirrored left)
HALL_RISE = 0.17
CHIMNEY_RISE = 0.17
DEPLOY_FRAMES = 60
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = nod.materials()
    m['grey'] = material('NodGrey', srgb('#8c8e91'), 0.6, 0.3)
    m['grey_dark'] = material('NodGreyDark', srgb('#5c5e62'), 0.65, 0.3)
    return m


def cab(m):
    parts = [
        kit.hexahedron('CabLow', m['grey'], (
            (-0.36, -0.84, 0.17), (0.36, -0.84, 0.17), (0.36, -0.49, 0.17), (-0.36, -0.49, 0.17),
            (-0.36, -0.83, 0.36), (0.36, -0.83, 0.36), (0.36, -0.49, 0.36), (-0.36, -0.49, 0.36)), bevel=0.014),
        kit.hexahedron('CabHigh', m['grey'], (
            (-0.35, -0.82, 0.36), (0.35, -0.82, 0.36), (0.35, -0.49, 0.36), (-0.35, -0.49, 0.36),
            (-0.32, -0.72, 0.52), (0.32, -0.72, 0.52), (0.32, -0.5, 0.52), (-0.32, -0.5, 0.52)), bevel=0.014),
        box('Windscreen', m['glass'], (0.56, 0.01, 0.15), (0, -0.773, 0.44), bevel=0.004, rotation=(math.atan2(0.1, 0.16), 0, 0)),
        *detail.grille('Grille', m['steel'], m['dark'], (0, -0.842, 0.27), 0.3, 0.11, 'Y', 6, 0.008),
        beam('Bumper', m['armour_dark'], (-0.37, -0.86, 0.2), (0.37, -0.86, 0.2), 0.05, 0.05),
        box('CabRoofBox', m['grey_dark'], (0.28, 0.12, 0.03), (0, -0.6, 0.535), bevel=0.006),
        box('CabStripe', m['remap'], (0.72, 0.3, 0.025), (0, -0.66, 0.36), bevel=0.004),
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.27, -0.845, 0.28), (0, -1, 0), 0.022),
            box(f'SideWindow{s}', m['glass'], (0.01, 0.12, 0.08), (s * 0.345, -0.6, 0.44), bevel=0.003),
            box(f'Door{s}', m['grey_dark'], (0.006, 0.16, 0.16), (s * 0.362, -0.62, 0.27), bevel=0.003),
            beam(f'MirrorArm{s}', m['steel'], (s * 0.34, -0.74, 0.44), (s * 0.42, -0.76, 0.46), 0.012),
            box(f'Mirror{s}', m['dark'], (0.02, 0.012, 0.07), (s * 0.43, -0.76, 0.46), bevel=0.003),
            box(f'Step{s}', m['steel'], (0.04, 0.1, 0.012), (s * 0.37, -0.62, 0.15), bevel=0.002),
        ]
    return kit.merge('Cab', parts)


def chassis(m):
    parts = [box('Frame', m['armour_dark'], (0.64, 1.62, 0.1), (0, -0.0, 0.17), bevel=0.01)]
    for s in (-1, 1):
        for k, y in enumerate(AXLES):
            if k == 0:
                continue   # the cab covers the front axle
            parts += [
                box(f'Fender{s}{k}', m['armour_dark'], (0.13, 0.28, 0.02), (s * WHEEL_X, y, 2 * WHEEL_RADIUS + 0.018), bevel=0.005),
                box(f'FenderStrut{s}{k}', m['steel'], (0.034, 0.02, 0.03), (s * (BOX_X + 0.043), y, 2 * WHEEL_RADIUS + 0.005), bevel=0.003),
            ]
        parts.append(cylinder(f'Axle{s}', m['steel'], 0.02, 1.3, (s * 0.33, 0, WHEEL_RADIUS), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0))
    return kit.merge('Chassis', parts)


def factory_box(m):
    """The red box (fixed): red walls ribbed in dark armour, the dark opening on top
    under the roof halves, the grey rear box with the ramp's opening and the gantry."""
    y0, y1 = BOX
    parts = [
        kit.hexahedron('BoxCore', m['remap'], (
            (-BOX_X, y0, FLOOR), (BOX_X, y0, FLOOR), (BOX_X, y1, FLOOR), (-BOX_X, y1, FLOOR),
            (-BOX_X, y0, BOX_TOP), (BOX_X, y0, BOX_TOP), (BOX_X, y1, BOX_TOP), (-BOX_X, y1, BOX_TOP)), bevel=0.008),
        box('Opening', m['dark'], (2 * BOX_X - 0.04, y1 - y0 - 0.04, 0.004), (0, (y0 + y1) / 2, BOX_TOP + 0.001), bevel=0),
        box('FrontPlate', m['armour_dark'], (2 * BOX_X - 0.02, 0.012, BOX_TOP - FLOOR - 0.04), (0, y0 - 0.005, (FLOOR + BOX_TOP) / 2), bevel=0.003),
        # the rear box and the dark opening behind the ramp
        kit.hexahedron('RearBox', m['grey'], (
            (-BOX_X, REAR[0], FLOOR), (BOX_X, REAR[0], FLOOR), (BOX_X, REAR[1] - 0.026, FLOOR), (-BOX_X, REAR[1] - 0.026, FLOOR),
            (-BOX_X, REAR[0], REAR_TOP), (BOX_X, REAR[0], REAR_TOP), (BOX_X, REAR[1] - 0.026, REAR_TOP), (-BOX_X, REAR[1] - 0.026, REAR_TOP)),
            bevel=0.008),
        box('RampOpening', m['dark'], (0.34, 0.004, RAMP - 0.02), (0, REAR[1] - 0.026, FLOOR + RAMP / 2), bevel=0),
        box('Neck', m['armour_dark'], (2 * BOX_X - 0.06, REAR[0] - BOX[1] + 0.01, 0.2), (0, (BOX[1] + REAR[0]) / 2, FLOOR + 0.1), bevel=0.004),
        # the gantry over the rear box
        *[beam(f'GantryPost{s}', m['steel_light'], (s * (BOX_X + 0.04), 0.67, FLOOR - 0.04), (s * (BOX_X + 0.02), 0.67, 0.74), 0.04, 0.04)
          for s in (-1, 1)],
        beam('GantryBeam', m['steel_light'], (-BOX_X - 0.04, 0.67, 0.74), (BOX_X + 0.04, 0.67, 0.74), 0.05, 0.05),
        box('GantryHoist', m['grey_dark'], (0.1, 0.07, 0.06), (0.1, 0.67, 0.69), bevel=0.006),
        beam('GantryCable', m['dark'], (0.1, 0.67, 0.66), (0.1, 0.67, REAR_TOP + 0.03), 0.006),
        box('GantryHook', m['steel'], (0.05, 0.03, 0.03), (0.1, 0.67, REAR_TOP + 0.02), bevel=0.004),
        *detail.lamp('TailLightL', m['dark'], m['lamp_red'], (-0.3, REAR[1] - 0.024, 0.3), (0, 1, 0), 0.014),
        *detail.lamp('TailLightR', m['dark'], m['lamp_red'], (0.3, REAR[1] - 0.024, 0.3), (0, 1, 0), 0.014),
    ]
    for s in (-1, 1):
        for k in range(9):
            y = y0 + 0.06 + k * (y1 - y0 - 0.12) / 8
            parts.append(box(f'Rib{s}{k}', m['armour_dark'], (0.016, 0.03, BOX_TOP - FLOOR - 0.06), (s * (BOX_X + 0.006), y, (FLOOR + BOX_TOP) / 2),
                             bevel=0.003))
        parts.append(box(f'Rail{s}', m['armour_dark'], (0.02, y1 - y0, 0.03), (s * (BOX_X + 0.008), (y0 + y1) / 2, FLOOR + 0.02), bevel=0.003))
    return kit.merge('FactoryBox', parts)


def roof_half(m, body, s):
    """A roof half on its hinge at the box's top outer edge; folds over and down."""
    y0, y1 = BOX
    hinge = Vector((s * BOX_X, (y0 + y1) / 2, ROOF_TOP))
    node = kit.parent(kit.empty(f'Roof{s}', hinge), body)
    width = BOX_X
    plate = kit.merge(f'RoofPlate{s}', [
        box(f'RoofTop{s}', m['grey'], (width - 0.004, y1 - y0, 0.018), (s * width / 2, (y0 + y1) / 2, ROOF_TOP - 0.009), bevel=0.004),
        box(f'RoofUnder{s}', m['armour_dark'], (width - 0.03, y1 - y0 - 0.03, 0.008), (s * width / 2, (y0 + y1) / 2, ROOF_TOP - 0.021), bevel=0.002),
        *[box(f'RoofSeam{s}{k}', m['grey_dark'], (width - 0.04, 0.012, 0.006), (s * width / 2, y0 + 0.2 + k * 0.25, ROOF_TOP + 0.002), bevel=0)
          for k in range(4)],
        box(f'RoofHinge{s}', m['steel'], (0.02, y1 - y0 - 0.1, 0.02), (s * (BOX_X - 0.008), (y0 + y1) / 2, ROOF_TOP - 0.002), bevel=0.003),
    ], hinge)
    kit.parent(plate, node)
    return node


def hall(m, body):
    """The dark hall of the war factory, inside the box at rest; its chimneys."""
    y0, y1 = BOX
    node = kit.parent(kit.empty('Hall', (0, 0, 0)), body)
    lo, hi = FLOOR + 0.01, BOX_TOP - 0.012
    x0, x1 = BOX_X - 0.05, BOX_X - 0.1
    ya, yb = y0 + 0.05, y1 - 0.05
    parts = [
        kit.hexahedron('HallBody', m['armour'], (
            (-x0, ya, lo), (x0, ya, lo), (x0, yb, lo), (-x0, yb, lo),
            (-x1, ya + 0.04, hi), (x1, ya + 0.04, hi), (x1, yb - 0.04, hi), (-x1, yb - 0.04, hi)), bevel=0.01),
        box('HallRoof', m['steel'], (2 * x1 - 0.04, yb - ya - 0.14, 0.012), (0, (ya + yb) / 2, hi + 0.004), bevel=0.003),
        box('HallCrane', m['grey_dark'], (0.06, 0.18, 0.04), (0.1, ya + 0.2, hi + 0.02), bevel=0.006),
    ]
    # the red double struts on its corners, as on the war factory
    for sx in (-1, 1):
        for sy, y in ((-1, ya), (1, yb)):
            for d in (-0.02, 0.02):
                bottom = Vector((sx * x0, y + sy * -0.0 + d * 0, lo + 0.01))
                top = Vector((sx * x1, y - sy * 0.04, hi))
                off = Vector((0, d, 0)) if True else Vector()
                parts.append(beam(f'Strut{sx}{sy}{d}', m['remap'], bottom + off + Vector((sx * 0.012, -sy * 0.03, 0)),
                                  top + off + Vector((sx * 0.012, -sy * 0.0, 0)), 0.018))
    # three red lamps along its right top edge, as over the war factory's gate
    for k in range(3):
        parts += detail.lamp(f'HallLamp{k}', m['dark'], m['lamp_red'], (x1 + 0.012, -0.12 + k * 0.14, hi - 0.03), (1, 0, 0.5), 0.016)
    kit.parent(kit.merge('HallMesh', parts), node)
    chimneys = []
    for k, (x, y) in enumerate(((-0.12, 0.12), (-0.12, 0.26))):
        c = kit.parent(kit.empty(f'Chimney{k}', (x, y, hi - 0.2)), node)
        kit.parent(kit.merge(f'ChimneyMesh{k}', [
            cylinder(f'Stack{k}', m['steel_light'], 0.024, 0.19, (x, y, hi - 0.105), segments=12, bevel=0.002),
            cylinder(f'StackTop{k}', m['dark'], 0.028, 0.02, (x, y, hi - 0.012), segments=12, bevel=0.002),
        ], (x, y, hi - 0.2)), c)
        chimneys.append(c)
    return node, chimneys


def ramp(m, body):
    """The rear door: shut it is the box's back, dropped it is the ramp (stripes inside)."""
    hinge = Vector((0, REAR[1], FLOOR))
    node = kit.parent(kit.empty('Ramp', hinge), body)
    parts = [box('RampPlate', m['grey'], (0.4, 0.024, RAMP), hinge + Vector((0, -0.012, RAMP / 2)), bevel=0.004)]
    for k in range(6):
        parts.append(kit.hexahedron(f'RampStripe{k}', m['remap'] if k % 2 == 0 else m['dark'], tuple(
            hinge + Vector((x, -0.0265, z)) for x, z in (
                (-0.18, 0.02 + k * 0.042), (0.18, 0.02 + k * 0.042 + 0.0), (0.18, 0.062 + k * 0.042), (-0.18, 0.062 + k * 0.042))) + tuple(
            hinge + Vector((x, -0.0235, z)) for x, z in (
                (-0.18, 0.02 + k * 0.042), (0.18, 0.02 + k * 0.042 + 0.0), (0.18, 0.062 + k * 0.042), (-0.18, 0.062 + k * 0.042))), bevel=0))
    parts.append(cylinder('RampHinge', m['steel'], 0.016, 0.42, hinge + Vector((0, -0.012, 0.0)), rotation=(0, math.pi / 2, 0), segments=10, bevel=0))
    kit.parent(kit.merge('RampMesh', parts, hinge), node)
    return node


def beacon(m, body):
    node = kit.parent(kit.empty('Beacon', (0.18, -0.6, 0.56)), body)
    kit.parent(cylinder('BeaconHousing', m['steel'], 0.02, 0.03, (0.18, -0.6, 0.535), segments=10, bevel=0), body)
    kit.parent(kit.merge('BeaconLamp', [sphere('BeaconBulb', m['lamp_red'], 0.02, (0.18, -0.6, 0.56), 10),
                                        sphere('BeaconHalo', m['glow_red'], 0.04, (0.18, -0.6, 0.56), 10)], (0.18, -0.6, 0.56)), node)
    return node


def deploy(ramp_node, roofs, hall_node, chimneys):
    keys = kit.keys
    end = DEPLOY_FRAMES
    zero = Vector((0, 0, 0))
    keys(ramp_node, 'rotation_euler', {0: zero, 2: zero, 20: Vector((RAMP_DOWN, 0, 0)), end: Vector((RAMP_DOWN, 0, 0))})
    kit.to_track(ramp_node, 'Deploy')
    for k, (node, s) in enumerate(roofs):
        folded = Vector((0, s * ROOF_FOLD, 0))
        keys(node, 'rotation_euler', {0: zero, 6 + 3 * k: zero, 32 + 3 * k: folded, end: folded})
        kit.to_track(node, 'Deploy')
    keys(hall_node, 'location', {0: zero, 30: zero, 48: Vector((0, 0, HALL_RISE)), end: Vector((0, 0, HALL_RISE))})
    kit.to_track(hall_node, 'Deploy')
    for k, c in enumerate(chimneys):
        rest = c.location.copy()
        keys(c, 'location', {0: rest, 42 + 4 * k: rest, 54 + 4 * k: rest + Vector((0, 0, CHIMNEY_RISE)), end: rest + Vector((0, 0, CHIMNEY_RISE))})
        kit.to_track(c, 'Deploy')
        c.location = rest
    ramp_node.rotation_euler = zero
    hall_node.location = zero
    for node, _ in roofs:
        node.rotation_euler = zero


def build():
    root, body = nod.start('NodMobileWarFactory', 'MobileWarFactory', WALK_SPEED)
    m = materials()
    for obj in (cab(m), chassis(m), factory_box(m)):
        kit.parent(obj, body)
    roofs = [(roof_half(m, body, s), s) for s in (-1, 1)]
    hall_node, chimneys = hall(m, body)
    ramp_node = ramp(m, body)
    lamp = beacon(m, body)
    wheels = [kit.parent(nod.wheel(m, f'Wheel{s}{k}', (s * WHEEL_X, y, WHEEL_RADIUS), WHEEL_RADIUS, WHEEL_WIDTH, lugs=16, hub=0.5), root)
              for s in (-1, 1) for k, y in enumerate(AXLES)]
    nod.camouflage([o for o in kit.collection().objects if o.name not in ('RampMesh',)], frequency=5.0, max_edge=0.07)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003)
    kit.blink(lamp, kit.flashes((0, 8), (30, 8)))
    kit.to_track(lamp, 'Idle')
    deploy(ramp_node, roofs, hall_node, chimneys)
    lamp.scale = (1, 1, 1)
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Deploy': [16, 26, 40, 59]}, scale=2.0, target=(0, 0, 0.3))
