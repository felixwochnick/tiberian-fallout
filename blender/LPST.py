"""
Tiberian Fallout – mobile sensor array (LPST), after Tiberian Sun (GDI's, Nod builds it too).

A four-wheeled truck: a short cab-over cab in front, behind it a low equipment body
with grilles, a generator and a cable drum, and the folded sensor mast lying along the
deck from its A-frame at the back over the cab's roof: a lattice tower with posts in
the house colour, a narrower second section inside it and on its tip the sensor head
(a turning drum with a folded dish, a warning light and a whip antenna). Four
outriggers are stowed in sleeves under the body. The cab and the body are in the light
camouflage of the buildings, tinted with the house colour in the game
(GAPILE.camo_material); the mudguards, the mast's posts and a stripe on the body are
in the house colour.

Deployed (like the original's, it reveals the map around it), the outriggers slide out
and their jacks press down and lift the truck a little, the mast swings upright, its top section runs out,
the dish unfolds, and the head turns round and round, its light blinking.

Nodes: "Mast" (the lower section, on its pivot), "MastTop" (the inner section),
"Sensor" (the head, turning about the mast), "Dish", "Outrigger…" (the arms, sliding out) with "Jack…" (their rods, running down).
Clips (see nodvehicle.py for Idle and Walk):
    Idle       loop, 2 s: the engine runs, the body shivers a little
    Walk       loop: driving, the wheels turn (one turn per loop), the body rocks; the
               root's walkSpeed (glTF extras) is the ground speed in cells per second
    Deploy     once, 2 s: outriggers down, mast up, top section out, dish open
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

WHEEL_RADIUS = 0.08
WHEEL_X = 0.245
WHEEL_WIDTH = 0.07
AXLES = (-0.27, 0.25)
WALK_FRAMES = 28
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
CAB = (-0.47, -0.23, 0.13, 0.3)     # front, back, bottom, top
DECK = (-0.21, 0.44, 0.13, 0.25)    # the equipment body: front, back, bottom, top
PIVOT = Vector((0, 0.35, 0.355))    # the mast's pivot on the A-frame
MAST = (0.045, 0.5)                 # lower section: half width, length
TOP = (0.03, 0.46, 0.3)             # inner section: half width, length, how far it runs out
HEAD = 0.5                          # the head's base above the pivot (inner section stowed)
OUTRIGGERS = (-0.1, 0.4)            # the outriggers' y
OUTRIGGER_HINGE = (0.245, 0.17)     # the stowed jack's x (less its offset), the arm's z
OUTRIGGER_REACH = 0.14              # how far the arms slide out (x)
LIFT = 0.03                         # how much the outriggers lift the truck
DEPLOY_FRAMES = 60
DISH_OPEN = math.radians(60)
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'tyre': material('Tyre', srgb('#25231f'), 0.9, 0.1),
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'dish': material('DishWhite', srgb('#d9d6cc'), 0.5, 0.2),
    })
    return m


def camo(obj, root):
    """The light camouflage (baked; tinted with the house colour in the game)."""
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def lattice(name, post, brace, half, z0, z1, bays):
    """A square lattice tower section standing on PIVOT from z0 to z1 above it:
    corner posts and zigzag braces on its four faces."""
    base = PIVOT
    corners = [Vector((sx * half, sy * half, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    parts = [beam(f'{name}Post{k}', post, base + c + Vector((0, 0, z0)), base + c + Vector((0, 0, z1)), half * 0.32) for k, c in enumerate(corners)]
    step = (z1 - z0) / bays
    for k in range(4):
        a, b = corners[k], corners[(k + 1) % 4]
        for i in range(bays):
            lo, hi = z0 + i * step, z0 + (i + 1) * step
            p, q = (a, b) if i % 2 == 0 else (b, a)
            parts += [beam(f'{name}Brace{k}_{i}', brace, base + p + Vector((0, 0, lo)), base + q + Vector((0, 0, hi)), half * 0.14),
                      beam(f'{name}Rung{k}_{i}', brace, base + a + Vector((0, 0, hi)), base + b + Vector((0, 0, hi)), half * 0.14)]
    return parts


def truck(m, root):
    """Cab and equipment body (camouflaged) and their fittings."""
    f, b, z0, z1 = CAB
    df, db, d0, d1 = DECK
    shell = camo(kit.merge('Hull', [
        kit.hexahedron('Cab', m['sand'], (
            (-0.23, f, z0), (0.23, f, z0), (0.23, b, z0), (-0.23, b, z0),
            (-0.215, f + 0.04, z1), (0.215, f + 0.04, z1), (0.215, b, z1), (-0.215, b, z1)), bevel=0.016),
        kit.hexahedron('Body', m['sand'], (
            (-0.235, df, d0), (0.235, df, d0), (0.235, db, d0), (-0.235, db, d0),
            (-0.225, df, d1), (0.225, df, d1), (0.225, db, d1), (-0.225, db, d1)), bevel=0.012),
    ]), root)
    rake = math.atan2(0.04, z1 - z0)
    parts = [
        box('Frame', m['dark'], (0.3, 0.92, 0.05), (0, -0.02, 0.12), bevel=0.006),
        *[cylinder(f'Axle{k}', m['dark'], 0.018, 2 * WHEEL_X - 0.05, (0, y, WHEEL_RADIUS), rotation=(0, math.pi / 2, 0), segments=8, bevel=0)
          for k, y in enumerate(AXLES)],
        # the cab: windscreen, grille, bumper, lights, mirrors, a roof cradle for the mast's head
        box('Windscreen', m['glass'], (0.38, 0.012, 0.075), (0, f + 0.032, z1 - 0.055), bevel=0.004, rotation=(-rake, 0, 0)),
        box('Pillar', m['dark'], (0.016, 0.014, 0.075), (0, f + 0.031, z1 - 0.055), bevel=0.002, rotation=(-rake, 0, 0)),
        *detail.grille('Grille', m['steel'], m['dark'], (0, f - 0.003, 0.19), 0.24, 0.06, 'Y', 4, 0.01),
        box('Bumper', m['dark'], (0.48, 0.04, 0.05), (0, f - 0.01, 0.12), bevel=0.006),
        *[box(f'BumperStripe{k}', m['hazard'] if k % 2 == 0 else m['dark'], (0.06, 0.006, 0.04), (-0.15 + k * 0.06, f - 0.032, 0.12), bevel=0)
          for k in range(6)],
        box('Cradle', m['steel'], (0.14, 0.03, 0.02), (0, -0.33, z1 + 0.01), bevel=0.004),
        *[box(f'CradleArm{s}', m['steel'], (0.015, 0.03, 0.05), (s * 0.065, -0.33, z1 + 0.03), bevel=0.003) for s in (-1, 1)],
        box('RoofHatch', m['steel'], (0.1, 0.08, 0.012), (0.13, -0.33, z1 + 0.003), bevel=0.003),
        # the body: house-colour stripe, grilles, generator, cable drum, ladder
        box('Generator', m['olive'], (0.16, 0.16, 0.08), (-0.11, -0.05, d1 + 0.04), bevel=0.01),
        *detail.grille('GeneratorVent', m['steel'], m['dark'], (-0.11, -0.131, d1 + 0.04), 0.11, 0.05, 'Y', 3, 0.006),
        cylinder('Exhaust', m['steel'], 0.014, 0.12, (-0.18, -0.12, d1 + 0.09), segments=8),
        cylinder('CableDrum', m['steel'], 0.05, 0.1, (0.12, 0.0, d1 + 0.055), rotation=(0, math.pi / 2, 0), segments=16),
        cylinder('Cable', m['dark'], 0.042, 0.08, (0.12, 0.0, d1 + 0.055), rotation=(0, math.pi / 2, 0), segments=16, bevel=0),
        *[box(f'DrumStand{s}', m['steel'], (0.01, 0.05, 0.06), (0.12 + s * 0.055, 0.0, d1 + 0.03), bevel=0.002) for s in (-1, 1)],
        box('ToolBox', m['steel'], (0.12, 0.1, 0.04), (0.12, 0.17, d1 + 0.02), bevel=0.006),
        # the A-frame carrying the mast's pivot
        *[beam(f'AFrame{s}{k}', m['steel'], (s * 0.13, PIVOT.y + dy, d1), (s * 0.085, PIVOT.y, PIVOT.z), 0.024)
          for s in (-1, 1) for k, dy in enumerate((-0.07, 0.07))],
        cylinder('PivotPin', m['steel_light'], 0.02, 0.21, PIVOT, rotation=(0, math.pi / 2, 0), segments=12),
        cylinder('Ram', m['steel_light'], 0.012, 0.2, (0, 0.2, d1 + 0.06), rotation=(math.radians(70), 0, 0), segments=8),
        *detail.ladder('Ladder', m['steel_light'], (0.15, db + 0.012, 0.12), (0.15, db + 0.012, d1 + 0.01), 0.05, 4, out=(0, 0.008, 0)),
        box('BackPlate', m['dark'], (0.44, 0.01, 0.06), (0, db + 0.004, 0.17), bevel=0.002),
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.17, f - 0.004, 0.2), (0, -1, 0), 0.016),
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.2, db + 0.006, 0.18), (0, 1, 0), 0.012),
            box(f'SideWindow{s}', m['glass'], (0.012, 0.1, 0.06), (s * 0.224, -0.36, z1 - 0.06), bevel=0.003),
            beam(f'MirrorArm{s}', m['steel'], (s * 0.22, f + 0.05, z1 - 0.04), (s * 0.29, f + 0.03, z1 - 0.03), 0.007),
            box(f'Mirror{s}', m['dark'], (0.014, 0.03, 0.05), (s * 0.295, f + 0.03, z1 - 0.05), bevel=0.003),
            box(f'Stripe{s}', m['remap'], (0.008, db - df - 0.04, 0.03), (s * 0.236, (df + db) / 2, d1 - 0.035), bevel=0.002),
            *detail.grille(f'SideGrille{s}', m['steel'], m['dark'], (s * 0.236, 0.07, 0.18), 0.12, 0.05, 'X', 3, 0.008),
            # mudguards in the house colour
            *[box(f'Guard{s}{k}', m['remap'], (0.1, 0.22, 0.016), (s * WHEEL_X, y, WHEEL_RADIUS * 2 + 0.03), bevel=0.005) for k, y in enumerate(AXLES)],
            *[box(f'MudFlap{s}{k}', m['dark'], (0.07, 0.006, 0.07), (s * WHEEL_X, y + 0.11, 0.12), bevel=0.002) for k, y in enumerate(AXLES)],
            # the outriggers' sleeves under the body
            *[box(f'OutriggerSleeve{s}{k}', m['dark'], (0.1, 0.05, 0.05), (s * 0.17, y, OUTRIGGER_HINGE[1]), bevel=0.004)
              for k, y in enumerate(OUTRIGGERS)],
        ]
    return shell, kit.merge('HullDetails', parts)


def outrigger(m, s, y):
    """An outrigger, stowed: a beam in its sleeve under the body that slides out
    sideways (origin on its inner end), with the jack at its outer end whose rod
    (the second object, its child) runs down onto the ground."""
    x0, z = OUTRIGGER_HINGE
    end = s * (x0 + 0.035)
    side = 'R' if s > 0 else 'L'
    end_name = 'F' if y < 0 else 'B'
    arm = kit.merge(f'Outrigger{side}{end_name}', [
        box(f'Arm{s}{y}', m['steel'], (0.16, 0.036, 0.036), (s * (x0 - 0.045), y, z), bevel=0.004),
        cylinder(f'JackHousing{s}{y}', m['steel'], 0.024, 0.09, (end, y, z - 0.01), segments=12),
        cylinder(f'JackCap{s}{y}', m['dark'], 0.026, 0.012, (end, y, z + 0.04), segments=12, bevel=0),
        *[box(f'ArmStripe{s}{y}{k}', m['hazard'] if k % 2 == 0 else m['dark'], (0.03, 0.038, 0.038), (s * (x0 - 0.1 + 0.03 * k), y, z), bevel=0)
          for k in range(3)],
    ], (s * (x0 - 0.12), y, z))
    rod = kit.merge(f'Jack{side}{end_name}', [
        cylinder(f'JackRod{s}{y}', m['steel_light'], 0.015, 0.1, (end, y, z - 0.08), segments=10),
        cylinder(f'Pad{s}{y}', m['dark'], 0.034, 0.014, (end, y, z - 0.13), segments=12),
    ], (end, y, z - 0.137))
    kit.parent(rod, arm)
    return arm, rod


def mast(m, body):
    """The mast: lower section (node Mast, on PIVOT), inner section (MastTop), head
    (Sensor) with its dish (Dish) and light; all built upright. Returns the nodes and
    the light."""
    half, length = MAST
    lower = kit.merge('Mast', [
        *lattice('Lower', m['remap'], m['steel_light'], half, 0.0, length, 5),
        box('MastFoot', m['steel'], (2 * half + 0.03, 2 * half + 0.03, 0.04), PIVOT + Vector((0, 0, 0.0)), bevel=0.005),
        box('MastCollar', m['steel'], (2 * half + 0.02, 2 * half + 0.02, 0.025), PIVOT + Vector((0, 0, length - 0.012)), bevel=0.004),
        # a cable along it
        beam('MastCable', m['dark'], PIVOT + Vector((half + 0.008, 0, 0.03)), PIVOT + Vector((half + 0.008, 0, length - 0.03)), 0.008),
    ], PIVOT)
    kit.parent(lower, body)
    t_half, t_length, _ = TOP
    base = HEAD - t_length
    upper = kit.merge('MastTop', [
        *lattice('Upper', m['remap'], m['steel_light'], t_half, base, HEAD, 4),
        box('TopCap', m['steel'], (2 * t_half + 0.02, 2 * t_half + 0.02, 0.02), PIVOT + Vector((0, 0, HEAD - 0.01)), bevel=0.004),
    ], PIVOT)
    kit.parent(upper, lower)
    at = PIVOT + Vector((0, 0, HEAD))
    head = kit.merge('Sensor', [
        cylinder('SensorDrum', m['steel'], 0.05, 0.05, at + Vector((0, 0, 0.025)), segments=18),
        cylinder('SensorBand', m['remap'], 0.052, 0.012, at + Vector((0, 0, 0.03)), segments=18, bevel=0.002),
        box('SensorArm', m['steel_light'], (0.2, 0.02, 0.014), at + Vector((0, 0.03, 0.055)), bevel=0.003),
        *[box(f'SensorElement{k}', m['dark'], (0.006, 0.006, 0.04), at + Vector((-0.09 + k * 0.03, 0.03, 0.075)), bevel=0) for k in range(7)],
        beam('Whip', m['steel'], at + Vector((-0.035, -0.02, 0.05)), at + Vector((-0.04, -0.02, 0.3)), 0.005),
        cylinder('LightPole', m['steel'], 0.006, 0.04, at + Vector((0.035, -0.03, 0.07)), segments=6, bevel=0),
    ], at)
    kit.parent(head, upper)
    hinge = at + Vector((0, -0.02, 0.06))
    dish = kit.merge('Dish', [
        cylinder('DishShell', m['dish'], 0.03, 0.035, hinge + Vector((0, 0, 0.02)), segments=20, bevel=0.003, radius2=0.09),
        beam('Feed', m['steel'], hinge + Vector((0, 0, 0.03)), hinge + Vector((0, 0, 0.09)), 0.008),
        sphere('FeedHorn', m['dark'], 0.012, hinge + Vector((0, 0, 0.09)), 8),
    ], hinge)
    kit.parent(dish, head)
    housing, light = kit.beacon('SensorLamp', m, at + Vector((0.035, -0.03, 0.09)), glow='red')
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
    # folded for the road: legs up, mast forward along the deck
    lying = Vector((math.pi / 2, 0, 0))
    upright = Vector((0, 0, 0))
    lower.rotation_euler = lying
    nod.drive(body, wheels, WALK_FRAMES, rock=0.004)

    keys = kit.keys
    still, lifted = Vector((0, 0, 0)), Vector((0, 0, LIFT))
    stowed, out = upper.location.copy(), upper.location + Vector((0, 0, TOP[2]))
    closed, opened = Vector((0, 0, 0)), Vector((DISH_OPEN, 0, 0))
    # frame → pose; Undeploy plays the same backwards
    poses = {
        'body': (body, 'location', {0: still, 14: still, 22: lifted, DEPLOY_FRAMES: lifted}),
        'mast': (lower, 'rotation_euler', {0: lying, 16: lying, 40: upright, DEPLOY_FRAMES: upright}),
        'top': (upper, 'location', {0: stowed, 38: stowed, 52: out, DEPLOY_FRAMES: out}),
        'dish': (dish, 'rotation_euler', {0: closed, 50: closed, 58: opened, DEPLOY_FRAMES: opened}),
        'head': (head, 'rotation_euler', {0: still, DEPLOY_FRAMES: still}),
    }
    drop = OUTRIGGER_HINGE[1] - 0.137 + LIFT      # the pads from under the arms onto the ground
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
    lower.rotation_euler = lying
    upper.location = stowed
    dish.rotation_euler = closed
    head.rotation_euler = still
    light.scale = (kit.HIDDEN,) * 3
    for w in wheels:
        w.rotation_euler = still
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Deploy': [12, 28, 45, 59], 'Deployed': [10]}, scale=2.2, target=(0, 0, 0.5))
