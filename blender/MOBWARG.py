"""
Tiberian Fallout – GDI mobile war factory (MOBWARG), after Tiberian Sun Firestorm.

A heavy articulated truck: a squat steel-grey cab-over tractor with a wide windscreen,
a grille, a light bar and exhausts, and behind it a long low trailer carrying the
factory: a box whose long sides are big house-colour panels in frames, a steel roof,
and over it the grey portal of the gantry crane with its trolley. The cab and the
trailer's frame are in the light camouflage of the buildings, tinted with the house
colour in the game (GAPILE.camo_material).

When it deploys it opens up into a war factory: jacks press down onto the ground, the
side panels fold out and down into aprons, showing the assembly line inside (a lit
floor, two robot arms, the conveyor), the gantry crane rises on its posts and the rear
ramp drops. The game then puts the war factory (GAWEAP) in its place.

Clips (see nodvehicle.py for Idle and Walk):
    Idle     loop, 2 s: the engine runs, the beacon on the cab blinks
    Walk     loop: driving, the wheels turn, the body rocks; the root's walkSpeed
             (glTF extras) is the ground speed in cells per second
    Deploy   once, 2 s: jacks down, panels out, crane up, ramp down

Run headless:

    blender -b --factory-startup --python blender/MOBWARG.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'MOBWARG.glb')
BLEND = os.path.join(HERE, 'MOBWARG.blend')

WHEEL_RADIUS = 0.085
WHEEL_X = 0.28
WHEEL_WIDTH = 0.075
AXLES = (-0.56, 0.3, 0.46, 0.62)       # one under the cab, three under the trailer's tail
WALK_FRAMES = 30
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
DEPLOY_FRAMES = 60
CAB = (-0.78, -0.4)                      # the cab's front and back (y)
TRAILER = (-0.34, 0.74)                  # the factory box's front and back (y)
FLOOR = 0.2                              # the trailer's floor
BOX_X = 0.29                             # the box's half width
BOX_TOP = 0.56
PANEL_OPEN = math.radians(90)            # the side panels folded out and down
CRANE_RISE = 0.22
RAMP_HINGE = Vector((0, TRAILER[1] + 0.005, FLOOR))
RAMP_OPEN = math.radians(-105)
SCALE = 0.9

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = nod.materials()
    m.update({
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#3a6a96'), strength=0.6),
        'floor': material('FactoryFloor', srgb('#3c3d3a'), 0.8, 0.3, emission=srgb('#6a6a5a'), strength=0.15),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def chassis(m, root):
    """The frame rails, the fifth wheel, the trailer's floor and frame (camouflaged),
    mudguards, bumpers and lights."""
    y0, y1 = TRAILER
    frame = camo(kit.merge('TrailerFrame', [
        kit.hexahedron('Gooseneck', m['sand'], (
            (-0.25, CAB[1] - 0.06, 0.2), (0.25, CAB[1] - 0.06, 0.2), (0.25, y0, 0.12), (-0.25, y0, 0.12),
            (-0.25, CAB[1] - 0.06, 0.27), (0.25, CAB[1] - 0.06, 0.27), (0.25, y0, FLOOR + 0.02), (-0.25, y0, FLOOR + 0.02)), bevel=0.01),
        box('TrailerFloor', m['sand'], (2 * BOX_X + 0.02, y1 - y0, 0.07), (0, (y0 + y1) / 2, FLOOR - 0.025), bevel=0.008),
        # the front wall and the corner posts of the box
        box('FrontWall', m['sand'], (2 * BOX_X, 0.04, BOX_TOP - FLOOR), (0, y0 + 0.02, (FLOOR + BOX_TOP) / 2), bevel=0.008),
        *[box(f'Post{s}{k}', m['sand'], (0.04, 0.04, BOX_TOP - FLOOR), (s * (BOX_X - 0.02), y, (FLOOR + BOX_TOP) / 2), bevel=0.006)
          for s in (-1, 1) for k, y in enumerate((y0 + 0.02, y1 - 0.02))],
        box('Roof', m['sand'], (2 * BOX_X + 0.02, y1 - y0, 0.035), (0, (y0 + y1) / 2, BOX_TOP), bevel=0.008),
    ]), root)
    parts = [
        *[box(f'Rail{s}', m['dark'], (0.06, 1.38, 0.06), (s * 0.13, -0.06, 0.13), bevel=0.006) for s in (-1, 1)],
        cylinder('FifthWheel', m['steel'], 0.12, 0.03, (0, CAB[1] - 0.02, 0.19), segments=18),
        # the inside: the assembly line, shown when the panels are down
        box('Floor', m['floor'], (2 * BOX_X - 0.06, y1 - y0 - 0.06, 0.006), (0, (y0 + y1) / 2, FLOOR + 0.013), bevel=0),
        box('Conveyor', m['steel'], (0.16, y1 - y0 - 0.12, 0.04), (0, (y0 + y1) / 2, FLOOR + 0.035), bevel=0.004),
        *[cylinder(f'ConveyorRoller{k}', m['steel_light'], 0.012, 0.15, (0, y0 + 0.1 + 0.08 * k, FLOOR + 0.058), rotation=(0, math.pi / 2, 0),
                   segments=8, bevel=0) for k in range(12)],
        *[box(f'Lane{s}', m['hazard'], (0.016, y1 - y0 - 0.1, 0.004), (s * 0.12, (y0 + y1) / 2, FLOOR + 0.018), bevel=0) for s in (-1, 1)],
        *detail.grille('InnerVent', m['steel'], m['dark'], (0, y0 + 0.042, 0.42), 0.3, 0.14, 'Y', 6, 0.008),
        *[p for s in (-1, 1) for p in detail.lamp(f'InnerLamp{s}', m['dark'], m['lamp_white'], (s * 0.18, (y0 + y1) / 2, BOX_TOP - 0.03),
                                                     (0, 0, -1), 0.016)],
        # the roof: vents, a hatch, rivets
        *detail.grille('RoofVent', m['steel'], m['dark'], (-0.12, 0.05, BOX_TOP + 0.02), 0.14, 0.18, 'Z', 5, 0.008),
        cylinder('RoofHatch', m['steel'], 0.045, 0.02, (0.13, -0.15, BOX_TOP + 0.022), segments=16),
        *detail.rivets('RoofRivets', m['steel_light'], (-0.24, y0 + 0.04, BOX_TOP + 0.019), (-0.24, y1 - 0.04, BOX_TOP + 0.019), 10, axis='Z'),
        # rear: a bumper in warning stripes and tail lights
        box('Bumper', m['dark'], (0.56, 0.04, 0.05), (0, y1 + 0.03, 0.1), bevel=0.006),
        *[box(f'BumperStripe{k}', m['hazard'] if k % 2 == 0 else m['dark'], (0.07, 0.006, 0.04), (-0.175 + k * 0.07, y1 + 0.052, 0.1), bevel=0)
          for k in range(6)],
        *[p for s in (-1, 1) for p in detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.25, y1 + 0.052, 0.1), (0, 1, 0), 0.014)],
    ]
    for s in (-1, 1):
        for name, a, b in (('Cab', AXLES[0] - 0.11, AXLES[0] + 0.11), ('Tail', AXLES[1] - 0.11, AXLES[3] + 0.11)):
            parts += [box(f'Guard{name}{s}', m['remap'], (0.1, b - a, 0.02), (s * WHEEL_X, (a + b) / 2, 0.19), bevel=0.005),
                      box(f'MudFlap{name}{s}', m['dark'], (0.08, 0.008, 0.09), (s * WHEEL_X, b - 0.006, 0.1), bevel=0.002)]
        # the jacks' housings under the trailer's front corners
        parts.append(box(f'JackHousing{s}', m['steel'], (0.05, 0.05, 0.06), (s * 0.26, -0.2, FLOOR - 0.07), bevel=0.005))
        parts += detail.rivets(f'SideRivets{s}', m['steel_light'], (s * (BOX_X + 0.012), y0 + 0.06, FLOOR - 0.03),
                               (s * (BOX_X + 0.012), y1 - 0.06, FLOOR - 0.03), 10, axis='X')
    return frame, kit.merge('ChassisDetails', parts)


def cab(m, root):
    """The cab-over tractor (camouflaged shell, fittings)."""
    f, b = CAB
    shell = camo(kit.merge('Cab', [
        kit.hexahedron('Cab', m['sand'], (
            (-0.26, f, 0.13), (0.26, f, 0.13), (0.26, b, 0.13), (-0.26, b, 0.13),
            (-0.24, f + 0.06, 0.46), (0.24, f + 0.06, 0.46), (0.24, b, 0.47), (-0.24, b, 0.47)), bevel=0.016),
    ]), root)

    def front(z):  # the raked front (y) at height z
        return f + 0.06 * (z - 0.13) / 0.33 - 0.004

    parts = [
        box('Windscreen', m['glass'], (0.42, 0.01, 0.12), (0, front(0.37), 0.37), bevel=0.004, rotation=(math.radians(-10), 0, 0)),
        box('WindscreenBar', m['steel'], (0.014, 0.012, 0.12), (0, front(0.37) - 0.002, 0.37), bevel=0.002, rotation=(math.radians(-10), 0, 0)),
        *detail.grille('Grille', m['steel'], m['dark'], (0, front(0.21), 0.21), 0.3, 0.1, 'Y', 6, 0.01),
        box('Bumper', m['dark'], (0.54, 0.05, 0.06), (0, f - 0.02, 0.12), bevel=0.008),
        *[box(f'BumperStripe{k}', m['hazard'] if k % 2 == 0 else m['dark'], (0.07, 0.006, 0.05), (-0.21 + k * 0.07, f - 0.047, 0.12), bevel=0)
          for k in range(7)],
        box('LightBar', m['steel'], (0.36, 0.04, 0.025), (0, f + 0.1, 0.48), bevel=0.005),
        *[p for k, x in enumerate((-0.13, -0.045, 0.045, 0.13)) for p in detail.lamp(f'RoofLight{k}', m['dark'], m['lamp_white'],
                                                                                   (x, f + 0.078, 0.48), (0, -1, 0), 0.011)],
        box('CabRoofPlate', m['remap'], (0.3, 0.16, 0.008), (0, b - 0.12, 0.474), bevel=0.002),
        *[cylinder(f'Exhaust{s}', m['steel_light'], 0.02, 0.22, (s * 0.2, b + 0.02, 0.4), segments=10) for s in (-1, 1)],
        *[cylinder(f'ExhaustTip{s}', m['dark'], 0.018, 0.01, (s * 0.2, b + 0.02, 0.512), segments=10, bevel=0) for s in (-1, 1)],
        cylinder('BeaconBase', m['steel'], 0.018, 0.02, (0.17, b - 0.05, 0.48), segments=10, bevel=0),
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.2, front(0.17) - 0.01, 0.17), (0, -1, 0), 0.016),
            box(f'DoorWindow{s}', m['glass'], (0.008, 0.12, 0.08), (s * 0.247, f + 0.2, 0.38), bevel=0.003),
            detail.seam(f'DoorSeam{s}', m['seam'], (s * 0.255, f + 0.27, 0.16), (s * 0.247, f + 0.27, 0.44))[0],
            box(f'Mirror{s}', m['dark'], (0.02, 0.012, 0.05), (s * 0.31, f + 0.1, 0.38), bevel=0.003),
            beam(f'MirrorArm{s}', m['steel'], (s * 0.25, f + 0.1, 0.38), (s * 0.30, f + 0.1, 0.38), 0.008),
            box(f'Step{s}', m['steel_light'], (0.04, 0.1, 0.012), (s * 0.27, f + 0.24, 0.14), bevel=0.002),
        ]
    return shell, kit.merge('CabDetails', parts)


def panel(m, s):
    """A side panel of the box, hinged at its bottom edge; origin on the hinge."""
    y0, y1 = TRAILER
    hinge = Vector((s * (BOX_X + 0.006), (y0 + y1) / 2, FLOOR + 0.01))
    length, height = y1 - y0 - 0.08, BOX_TOP - FLOOR - 0.04
    parts = [
        box(f'Panel{s}', m['remap'], (0.014, length, height), hinge + Vector((0, 0, height / 2)), bevel=0.004),
        # a frame round it, stiffening ribs, vents with dark louvres
        *[box(f'PanelRib{s}{k}', m['steel'], (0.01, 0.018, height - 0.02), hinge + Vector((s * 0.01, -length / 2 + 0.02 + k * (length - 0.04) / 4,
                                                                                       height / 2)), bevel=0.002) for k in range(5)],
        box(f'PanelTop{s}', m['steel'], (0.012, length, 0.02), hinge + Vector((s * 0.01, 0, height - 0.01)), bevel=0.002),
        *detail.grille(f'PanelVent{s}', m['steel'], m['dark'], hinge + Vector((s * 0.012, -0.12, height * 0.6)), 0.16, 0.08, 'X', 4, 0.006),
        *detail.grille(f'PanelVent2{s}', m['steel'], m['dark'], hinge + Vector((s * 0.012, 0.18, height * 0.6)), 0.16, 0.08, 'X', 4, 0.006),
        cylinder(f'PanelHinge{s}', m['steel'], 0.012, length - 0.04, hinge, rotation=(math.pi / 2, 0, 0), segments=8),
    ]
    return kit.merge(f'Panel{"R" if s > 0 else "L"}', parts, hinge)


def crane(m):
    """The gantry crane: two portal frames on posts at the box's corners, joined by
    beams, with the trolley; origin under it (it rises as a whole)."""
    y0, y1 = TRAILER
    top = BOX_TOP + 0.09
    parts = []
    # the posts run down inside the box's corner posts (they telescope out of them)
    low = BOX_TOP - CRANE_RISE - 0.04
    for k, y in enumerate((y0 + 0.02, y1 - 0.02)):
        parts += [
            *[box(f'CranePost{k}{s}', m['steel_light'], (0.028, 0.028, top - low), (s * (BOX_X - 0.02), y, (top + low) / 2),
                  bevel=0.004) for s in (-1, 1)],
            box(f'CraneBeam{k}', m['steel_light'], (2 * BOX_X - 0.02, 0.045, 0.04), (0, y, top), bevel=0.005),
            *[box(f'CraneBeamStripe{k}{j}', m['hazard'] if j % 2 == 0 else m['dark'], (0.05, 0.047, 0.015), (-0.125 + 0.05 * j, y, top + 0.012),
                  bevel=0) for j in range(6)],
        ]
    for s in (-1, 1):
        parts.append(box(f'CraneRail{s}', m['steel'], (0.03, y1 - y0 - 0.12, 0.03), (s * 0.12, (y0 + y1) / 2, top + 0.005), bevel=0.004))
    parts += [
        box('Trolley', m['remap'], (0.3, 0.12, 0.05), (0, 0.32, top + 0.03), bevel=0.008),
        box('TrolleyCab', m['steel'], (0.08, 0.08, 0.05), (0.1, 0.32, top + 0.07), bevel=0.006),
        box('TrolleyWindow', m['glass'], (0.06, 0.006, 0.025), (0.1, 0.278, top + 0.075), bevel=0.002),
        cylinder('Hoist', m['dark'], 0.025, 0.1, (-0.04, 0.32, top + 0.02), rotation=(0, math.pi / 2, 0), segments=10),
    ]
    origin = Vector((0, (y0 + y1) / 2, BOX_TOP))
    return kit.merge('Crane', parts, origin)


def robot_arm(m, k, x, y):
    """A robot arm on the assembly line (it stands up as the box opens)."""
    base = Vector((x, y, FLOOR + 0.02))
    elbow = base + Vector((0, 0, 0.16))
    tool = elbow + Vector((-math.copysign(0.09, x), 0, -0.04))
    parts = [
        cylinder(f'ArmBase{k}', m['steel'], 0.035, 0.03, base + Vector((0, 0, 0.015)), segments=14),
        beam(f'ArmLower{k}', m['hazard'], base + Vector((0, 0, 0.02)), elbow, 0.03),
        sphere(f'ArmElbow{k}', m['steel'], 0.022, elbow, 10),
        beam(f'ArmUpper{k}', m['hazard'], elbow, tool, 0.024),
        box(f'ArmTool{k}', m['dark'], (0.03, 0.03, 0.04), tool + Vector((0, 0, -0.02)), bevel=0.004),
    ]
    return kit.merge(f'RobotArm{k}', parts, base)


def ramp(m, root):
    """The rear door, hinged at its bottom edge (it drops into a ramp)."""
    h = RAMP_HINGE
    height = BOX_TOP - FLOOR - 0.03
    shell = camo(kit.merge('Ramp', [box('RampPlate', m['sand'], (2 * BOX_X - 0.08, 0.016, height), h + Vector((0, 0.008, height / 2)),
                                        bevel=0.004)], h), root)
    kit.parent(kit.merge('RampFittings', [
        box('RampBand', m['remap'], (2 * BOX_X - 0.12, 0.005, 0.04), h + Vector((0, 0.018, height - 0.06)), bevel=0.001),
        *[box(f'RampTread{k}', m['steel'], (2 * BOX_X - 0.14, 0.006, 0.01), h + Vector((0, -0.003, 0.04 + k * 0.05)), bevel=0) for k in range(6)],
        cylinder('RampKnuckle', m['steel'], 0.014, 0.3, h, rotation=(0, math.pi / 2, 0), segments=10),
    ], h), shell)
    return shell


def jack(m, s):
    at = Vector((s * 0.26, -0.2, 0.07))
    return kit.merge(f'Jack{"R" if s > 0 else "L"}', [
        cylinder(f'JackRod{s}', m['steel_light'], 0.016, 0.08, at + Vector((0, 0, 0.04)), segments=10),
        cylinder(f'JackPad{s}', m['dark'], 0.036, 0.014, at + Vector((0, 0, 0.007)), segments=12),
    ], at)


def build():
    root, body = nod.start('GDIMobileWarFactory', 'MobileWarFactory', WALK_SPEED)
    m = materials()
    for obj in (*chassis(m, root), *cab(m, root)):
        kit.parent(obj, body)
    panels = [kit.parent(panel(m, s), body) for s in (-1, 1)]
    lift = kit.parent(crane(m), body)
    door = kit.parent(ramp(m, root), body)
    jacks = [kit.parent(jack(m, s), body) for s in (-1, 1)]
    arms = [kit.parent(robot_arm(m, k, x, y), body) for k, (x, y) in enumerate(((-0.17, -0.08), (0.17, 0.3)))]
    lamp = Vector((0.17, CAB[1] - 0.05, 0.505))
    beacon = kit.parent(kit.merge('Beacon', [sphere('BeaconBulb', m['lamp_amber'], 0.02, lamp, 10),
                                             sphere('BeaconHalo', m['glow_amber'], 0.042, lamp, 10)], lamp), body)
    wheels = [kit.parent(nod.wheel(m, f'Wheel{s}{k}', (s * WHEEL_X, y, WHEEL_RADIUS), WHEEL_RADIUS, WHEEL_WIDTH, lugs=14, rim=m['steel_light']), body)
              for s in (-1, 1) for k, y in enumerate(AXLES)]
    kit.bake_camo(512)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003)
    kit.blink(beacon, kit.flashes((0, 8), (30, 8)))
    kit.to_track(beacon, 'Idle')

    # Deploy: jacks down, panels out, the arms stand up, the crane rises, the ramp drops
    zero = Vector((0, 0, 0))
    down = Vector((0, 0, -0.06))
    for k, obj in enumerate(jacks):
        rest = obj.location.copy()
        kit.keys(obj, 'location', {0: rest, 2 + k: rest, 12 + k: rest + down, DEPLOY_FRAMES: rest + down})
        kit.to_track(obj, 'Deploy')
    for k, (obj, s) in enumerate(zip(panels, (-1, 1))):
        out = Vector((0, s * PANEL_OPEN, 0))
        kit.keys(obj, 'rotation_euler', {0: zero, 10 + 2 * k: zero, 32 + 2 * k: out, DEPLOY_FRAMES: out})
        kit.to_track(obj, 'Deploy')
    for k, obj in enumerate(arms):
        bowed = Vector((math.radians(70), 0, 0))
        obj.rotation_mode = 'XYZ'
        kit.keys(obj, 'rotation_euler', {0: bowed, 28: bowed, 44: zero, DEPLOY_FRAMES: zero})
        kit.to_track(obj, 'Deploy')
    rest = lift.location.copy()
    kit.keys(lift, 'location', {0: rest, 22: rest, 46: rest + Vector((0, 0, CRANE_RISE)), DEPLOY_FRAMES: rest + Vector((0, 0, CRANE_RISE))})
    kit.to_track(lift, 'Deploy')
    kit.keys(door, 'rotation_euler', {0: zero, 34: zero, 54: Vector((RAMP_OPEN, 0, 0)), DEPLOY_FRAMES: Vector((RAMP_OPEN, 0, 0))})
    kit.to_track(door, 'Deploy')
    # the arms lie folded inside while it drives
    for obj in arms:
        obj.rotation_euler = (math.radians(70), 0, 0)
    for obj in panels:
        obj.rotation_euler = zero
    door.rotation_euler = zero
    lift.location = rest
    for obj in jacks:
        obj.location.z = 0.07
    body.location, body.rotation_euler = zero, zero
    for w in wheels:
        w.rotation_euler = zero
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Deploy': [20, 40, 60]}, scale=2.0, target=(0, 0, 0.3))
