"""
Tiberian Fallout – Nod artillery (ART2), after Tiberian Sun.

A long, low tracked gun carrier: a flat dark hull between two long track guards whose
fronts run out past the hull as two prongs (red lights in their noses), the gun's
cradle behind the middle (the original's TurretOffset) and the very long barrel
lying forward over the hull in a travel lock between the prongs. Red (house colour)
stripes on the guards and the cradle's cheeks, vents, hatches, a stowed spade on
each side of the tail, exhausts and an antenna.

Like the original it digs in to fire at long range: the travel lock folds down, the
two spades at the back swing down into the ground, jacks in the prongs press down,
and the cradle raises the barrel.

Nodes the game uses: "Cannon" (the gun, tipped towards the target; it sits on
"Cradle", which the clips raise when deployed), "Flash" (its muzzle flash). Clips (see
nodvehicle.py for Idle, Walk, Fire):
    Deploy         once, 2 s: travel lock down, spades and jacks down, barrel up
    Deployed       loop: dug in, the barrel raised
    FireDeployed   once: a shot, dug in, with a heavy recoil
    Undeploy       once, 2 s: Deploy backwards

Run headless:

    blender -b --factory-startup --python blender/ART2.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'ART2.glb')
BLEND = os.path.join(HERE, 'ART2.blend')

TRACK_X = 0.225
TRACK_WIDTH = 0.11
TRACK = (-0.44, 0.44)
WHEEL_RADIUS = 0.045
WHEELS_Y = (-0.3, -0.16, -0.02, 0.12, 0.26)
SPROCKET = 0.058
WALK_FRAMES = 26
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 24
GUN = Vector((0, 0.27, 0.34))      # the barrel's trunnion in the cradle, behind the middle
BARREL = 0.92                      # from the trunnion to the muzzle
DEPLOY_FRAMES = 60
RAISE = math.radians(-32)          # the cradle when deployed: the barrel up
LOCK = Vector((0, -0.3, 0.24))     # the travel lock's hinge
SPADE_HINGE = 0.47                 # y of the spades' hinges, at the tail
SPADES_X = (-0.2, 0.2)
SCALE = 1.0

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def hull(m):
    """The dark hull, the guards with their prongs and their fittings."""
    parts = [
        kit.hexahedron('Hull', m['armour_dark'], (
            (-0.16, -0.42, 0.07), (0.16, -0.42, 0.07), (0.16, 0.46, 0.07), (-0.16, 0.46, 0.07),
            (-0.15, -0.36, 0.24), (0.15, -0.36, 0.24), (0.15, 0.46, 0.25), (-0.15, 0.46, 0.25)), bevel=0.01),
        # the cradle's block behind the middle, its cheeks red
        kit.hexahedron('CradleBase', m['armour'], (
            (-0.14, 0.12, 0.24), (0.14, 0.12, 0.24), (0.14, 0.44, 0.24), (-0.14, 0.44, 0.24),
            (-0.12, 0.16, 0.3), (0.12, 0.16, 0.3), (0.12, 0.42, 0.3), (-0.12, 0.42, 0.3)), bevel=0.01),
        box('Hatch', m['armour'], (0.08, 0.08, 0.016), (-0.08, -0.2, 0.245), bevel=0.004),
        box('Hatch2', m['armour'], (0.06, 0.06, 0.016), (0.08, -0.1, 0.25), bevel=0.004),
        *detail.grille('Vent', m['steel'], m['dark'], (0.0, 0.0, 0.252), 0.14, 0.1, 'Z', 5, 0.008),
        box('BackPlate', m['armour_dark'], (0.3, 0.012, 0.15), (0, 0.464, 0.16), bevel=0.003),
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (0.0, 0.472, 0.2), (0, 1, 0), 0.011),
        beam('Antenna', m['steel'], (-0.11, 0.4, 0.3), (-0.13, 0.46, 0.62), 0.006),
        *[cylinder(f'Exhaust{k}', m['steel_light'], 0.018, 0.12, (0.06 + 0.045 * k, 0.4, 0.33), rotation=(math.pi / 2, 0, 0), segments=10)
          for k in range(2)],
        *[cylinder(f'ExhaustTip{k}', m['dark'], 0.016, 0.01, (0.06 + 0.045 * k, 0.462, 0.33), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0)
          for k in range(2)],
        box('ExhaustClamp', m['steel'], (0.1, 0.02, 0.03), (0.08, 0.38, 0.315), bevel=0.003),
    ]
    for s in (-1, 1):
        x0, x1 = s * 0.16, s * 0.3
        parts += [
            # the guard, running out in front as a prong
            kit.hexahedron(f'Guard{s}', m['armour'], (
                (x0, -0.6, 0.11), (x1, -0.6, 0.11), (x1, 0.46, 0.09), (x0, 0.46, 0.09),
                (x0, -0.52, 0.22), (x1 - s * 0.01, -0.52, 0.21), (x1 - s * 0.01, 0.46, 0.22), (x0, 0.46, 0.23)), bevel=0.012),
            kit.hexahedron(f'Skirt{s}', m['armour_dark'], (
                (x1 - s * 0.01, -0.5, 0.1), (x1 + s * 0.006, -0.5, 0.1), (x1 + s * 0.006, 0.45, 0.07), (x1 - s * 0.01, 0.45, 0.07),
                (x1 - s * 0.01, -0.48, 0.2), (x1 + s * 0.004, -0.48, 0.2), (x1 + s * 0.004, 0.45, 0.21), (x1 - s * 0.01, 0.45, 0.21)), bevel=0.005),
            # red stripes on top of the guard and a red tip on the prong
            kit.hexahedron(f'GuardStripe{s}', m['remap'], (
                (s * 0.19, -0.3, 0.224), (s * 0.27, -0.3, 0.219), (s * 0.27, 0.42, 0.224), (s * 0.19, 0.42, 0.229),
                (s * 0.19, -0.3, 0.234), (s * 0.27, -0.3, 0.229), (s * 0.27, 0.42, 0.234), (s * 0.19, 0.42, 0.239)), bevel=0.002),
            kit.hexahedron(f'ProngTip{s}', m['remap'], (
                (x0 - s * 0.002, -0.605, 0.108), (x1 + s * 0.002, -0.605, 0.108), (x1 + s * 0.002, -0.46, 0.106), (x0 - s * 0.002, -0.46, 0.106),
                (x0 - s * 0.002, -0.525, 0.226), (x1 - s * 0.008, -0.525, 0.216), (x1 - s * 0.008, -0.46, 0.216), (x0 - s * 0.002, -0.46, 0.226)),
                bevel=0.008),
            *[box(f'SkirtBolt{s}{k}', m['steel'], (0.008, 0.014, 0.014), (x1 + s * 0.008, -0.38 + k * 0.11, 0.17), bevel=0.002) for k in range(8)],
            *detail.lamp(f'ProngLight{s}', m['dark'], m['lamp_red'], ((x0 + x1) / 2, -0.605, 0.15), (0, -1, 0), 0.016),
            *detail.lamp(f'GuardLight{s}', m['dark'], m['lamp_white'], (s * 0.27, -0.42, 0.225), (0, -1, 0.5), 0.012),
            box(f'CradleCheek{s}', m['remap'], (0.012, 0.22, 0.04), (s * 0.135, 0.29, 0.27), bevel=0.003),
            *detail.grille(f'SideVent{s}', m['steel'], m['dark'], (s * 0.13, 0.05, 0.25), 0.1, 0.03, 'Z', 3, 0.006),
            # the jacks' housings in the prongs and the spades' hinge blocks
            cylinder(f'JackHousing{s}', m['steel'], 0.026, 0.05, (s * 0.23, -0.53, 0.235), segments=12),
            box(f'SpadeMount{s}', m['steel'], (0.06, 0.03, 0.04), (s * SPADES_X[1], SPADE_HINGE - 0.005, 0.14), bevel=0.004),
        ]
    return kit.merge('Hull', parts)


def gun(m, body):
    """The cradle (raised when deployed), on it the Cannon with the barrel and the
    flash; returns (cradle, barrel, flash)."""
    cradle = kit.parent(kit.empty('Cradle', GUN), body)
    kit.parent(kit.merge('CradleBody', [
        *[kit.hexahedron(f'Trunnion{s}', m['armour'], (
            (s * 0.06, GUN.y - 0.08, 0.28), (s * 0.11, GUN.y - 0.08, 0.28), (s * 0.11, GUN.y + 0.1, 0.28), (s * 0.06, GUN.y + 0.1, 0.28),
            (s * 0.06, GUN.y - 0.04, GUN.z + 0.05), (s * 0.1, GUN.y - 0.04, GUN.z + 0.05), (s * 0.1, GUN.y + 0.06, GUN.z + 0.05),
            (s * 0.06, GUN.y + 0.06, GUN.z + 0.05)), bevel=0.008) for s in (-1, 1)],
        cylinder('TrunnionPin', m['steel_light'], 0.022, 0.24, GUN, rotation=(0, math.pi / 2, 0), segments=12),
        # the elevating rams under the gun
        *[cylinder(f'Ram{s}', m['steel_light'], 0.012, 0.1, GUN + Vector((s * 0.04, -0.07, -0.05)), rotation=(math.radians(-60), 0, 0), segments=8)
          for s in (-1, 1)],
    ], GUN), cradle)
    pivot = kit.parent(kit.empty('Cannon', GUN), cradle)
    tip = GUN - Vector((0, BARREL, 0))
    barrel = kit.merge('Barrel', [
        # the breech behind the trunnion, the mantlet, the long tube with its sleeves
        box('Breech', m['armour_dark'], (0.1, 0.16, 0.09), GUN + Vector((0, 0.04, 0)), bevel=0.012),
        box('BreechBand', m['remap'], (0.104, 0.03, 0.094), GUN + Vector((0, 0.09, 0)), bevel=0.004),
        cylinder('Mantlet', m['armour'], 0.055, 0.1, GUN - Vector((0, 0.07, 0)), rotation=(math.pi / 2, 0, 0), segments=16),
        cylinder('Recuperator', m['steel'], 0.02, 0.32, GUN + Vector((0, -0.26, 0.05)), rotation=(math.pi / 2, 0, 0), segments=10),
        cylinder('Sleeve', m['armour'], 0.04, 0.24, GUN - Vector((0, 0.24, 0)), rotation=(math.pi / 2, 0, 0), segments=16),
        cylinder('Tube', m['steel'], 0.026, BARREL - 0.1, GUN - Vector((0, (BARREL - 0.1) / 2 + 0.1, 0)), rotation=(math.pi / 2, 0, 0), segments=16),
        cylinder('Collar', m['armour_dark'], 0.032, 0.03, GUN - Vector((0, 0.45, 0)), rotation=(math.pi / 2, 0, 0), segments=16),
        cylinder('Evacuator', m['steel'], 0.036, 0.08, GUN - Vector((0, 0.76, 0)), rotation=(math.pi / 2, 0, 0), segments=16),
        box('MuzzleBrake', m['steel'], (0.08, 0.07, 0.05), tip + Vector((0, 0.03, 0)), bevel=0.008),
        *[box(f'BrakeSlot{s}', m['dark'], (0.004, 0.04, 0.03), tip + Vector((s * 0.04, 0.03, 0)), bevel=0) for s in (-1, 1)],
        cylinder('Bore', m['dark'], 0.016, 0.006, tip - Vector((0, 0.005, 0)), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
    ], GUN)
    kit.parent(barrel, pivot)
    flash = kit.parent(nod.flash(m, 'Flash', tip - Vector((0, 0.06, 0)), 0.08), pivot)
    return cradle, barrel, flash


def travel_lock(m):
    """The travel lock: a post with a U-shaped rest for the barrel; origin on its
    hinge (it folds forward, about x)."""
    top = GUN.z - 0.035
    parts = [
        box('LockFoot', m['steel'], (0.08, 0.04, 0.03), LOCK, bevel=0.004),
        beam('LockPost', m['steel'], LOCK, Vector((0, LOCK.y, top - 0.02)), 0.03),
        box('LockRest', m['steel_light'], (0.08, 0.03, 0.015), (0, LOCK.y, top - 0.01), bevel=0.003),
        *[box(f'LockFork{s}', m['steel_light'], (0.012, 0.03, 0.05), (s * 0.038, LOCK.y, top + 0.012), bevel=0.002) for s in (-1, 1)],
        box('LockStripe', m['hazard'], (0.032, 0.032, 0.02), Vector((0, LOCK.y, LOCK.z + 0.05)), bevel=0),
    ]
    return kit.merge('TravelLock', parts, LOCK)


def spade(m, x):
    """A spade at the tail, built dug in (down and back into the ground); origin on
    its hinge. Returns it and its stowed rotation (folded up against the tail)."""
    hinge = Vector((x, SPADE_HINGE, 0.14))
    blade = Vector((x, SPADE_HINGE + 0.15, -0.04))
    d = blade - hinge
    parts = [
        cylinder(f'SpadeKnuckle{x}', m['steel'], 0.018, 0.07, hinge, rotation=(0, math.pi / 2, 0), segments=10),
        beam(f'SpadeArm{x}', m['armour_dark'], hinge, blade, 0.05, 0.025),
        kit.hexahedron(f'SpadeBlade{x}', m['steel_light'], (
            (x - 0.05, blade.y - 0.02, blade.z - 0.02), (x + 0.05, blade.y - 0.02, blade.z - 0.02),
            (x + 0.05, blade.y + 0.02, blade.z - 0.02), (x - 0.05, blade.y + 0.02, blade.z - 0.02),
            (x - 0.06, blade.y - 0.05, blade.z + 0.05), (x + 0.06, blade.y - 0.05, blade.z + 0.05),
            (x + 0.06, blade.y + 0.0, blade.z + 0.06), (x - 0.06, blade.y + 0.0, blade.z + 0.06)), bevel=0.004),
        box(f'SpadeStripe{x}', m['remap'], (0.052, 0.012, 0.03), hinge.lerp(blade, 0.4), bevel=0.002),
    ]
    obj = kit.merge(f'Spade{"R" if x > 0 else "L"}', parts, hinge)
    return obj, Vector((math.atan2(d.y, d.z), 0, 0))


def jack(m, s):
    """A jack in a prong: its rod runs down onto the ground; origin at its foot."""
    at = Vector((s * 0.23, -0.53, 0.1))
    return kit.merge(f'Jack{"R" if s > 0 else "L"}', [
        cylinder(f'JackRod{s}', m['steel_light'], 0.016, 0.12, at + Vector((0, 0, 0.07)), segments=10),
        cylinder(f'JackPad{s}', m['dark'], 0.034, 0.014, at + Vector((0, 0, 0.007)), segments=12),
    ], at)


def deploy(body, cradle, barrel, flash, lock, spades, jacks):
    """The clips Deploy, Deployed, FireDeployed and Undeploy (Deploy backwards)."""
    level, raised = Vector((0, 0, 0)), Vector((RAISE, 0, 0))
    folded = Vector((math.radians(-100), 0, 0))     # the lock forward, flat on the hull's nose
    down = Vector((0, 0, -0.1))                      # the jacks' pads on the ground
    poses = [
        (lock, 'rotation_euler', {0: level, 4: level, 16: folded, DEPLOY_FRAMES: folded}),
        (cradle, 'rotation_euler', {0: level, 26: level, 54: raised, DEPLOY_FRAMES: raised}),
    ]
    for k, (obj, stowed) in enumerate(spades):
        poses.append((obj, 'rotation_euler', {0: stowed, 8 + 2 * k: stowed, 26 + 2 * k: level, DEPLOY_FRAMES: level}))
    for k, obj in enumerate(jacks):
        rest = obj.location.copy()
        poses.append((obj, 'location', {0: rest, 14 + k: rest, 26 + k: rest + down, DEPLOY_FRAMES: rest + down}))
    for clip, order in (('Deploy', lambda f: f), ('Undeploy', lambda f: DEPLOY_FRAMES - f)):
        for obj, path, frames in poses:
            kit.keys(obj, path, {order(f): v for f, v in frames.items()})
            kit.to_track(obj, clip)
    walker.hide([flash], DEPLOY_FRAMES, 'Deploy')
    walker.hide([flash], DEPLOY_FRAMES, 'Undeploy')
    walker.hide([flash], kit.IDLE_END, 'Deployed')
    for clip, frames in (('Deployed', kit.IDLE_END), ('FireDeployed', FIRE_FRAMES)):
        for obj, path, keyed in poses:
            walker.hold(obj, path, keyed[DEPLOY_FRAMES], frames, clip)
    # the shot dug in: a heavy recoil, the hull jolts back on its spades
    rest = barrel.location.copy()
    kick = Vector((0, 0.1, 0))
    kit.keys(barrel, 'location', {0: rest, 2: rest + kick, 6: rest + kick, 20: rest, FIRE_FRAMES: rest})
    kit.to_track(barrel, 'FireDeployed')
    kit.keys(body, 'rotation_euler', {0: level, 2: Vector((math.radians(-1.5), 0, 0)), 8: Vector((math.radians(0.4), 0, 0)), 14: level,
                                      FIRE_FRAMES: level})
    kit.to_track(body, 'FireDeployed')
    hidden = Vector((kit.HIDDEN,) * 3)
    kit.keys(flash, 'scale', {0: Vector((1, 1, 1)), 2: Vector((1.5, 1.8, 1.5)), 5: hidden, FIRE_FRAMES: hidden}, 'CONSTANT')
    kit.to_track(flash, 'FireDeployed')
    barrel.location = rest
    flash.scale = hidden
    body.rotation_euler = level
    lock.rotation_euler = level
    cradle.rotation_euler = level
    for obj, stowed in spades:
        obj.rotation_euler = stowed
    for obj, path, keyed in poses:
        if obj in jacks:
            obj.location = keyed[0]


def build():
    root, body = nod.start('NodArtillery', 'Artillery', WALK_SPEED)
    m = nod.materials()
    kit.parent(hull(m), body)
    cradle, barrel, flash = gun(m, body)
    lock = kit.parent(travel_lock(m), body)
    spades = []
    for x in SPADES_X:
        obj, stowed = spade(m, x)
        spades.append((kit.parent(obj, body), stowed))
    jacks = [kit.parent(jack(m, s), body) for s in (-1, 1)]
    wheels, sprockets = [], []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], 0.11, 20), body)
        x = s * (TRACK_X + TRACK_WIDTH / 2 + 0.004)
        wheels += [kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (x, y, WHEEL_RADIUS + 0.004), WHEEL_RADIUS, 0.02), body)
                   for k, y in enumerate(WHEELS_Y)]
        sprockets += [kit.parent(nod.road_wheel(m, f'Sprocket{s}{k}', (x, y, SPROCKET + 0.002), SPROCKET, 0.02), body)
                      for k, y in enumerate((TRACK[0] + 0.05, TRACK[1] - 0.05))]
    nod.camouflage(kit.collection().objects, max_edge=0.05)
    for obj, stowed in spades:
        obj.rotation_euler = stowed
    nod.drive(body, wheels + sprockets, WALK_FRAMES, rock=0.003)
    nod.fire([flash], FIRE_FRAMES, (barrel, barrel.location.copy(), Vector((0, 0.06, 0))), WALK_FRAMES)
    deploy(body, cradle, barrel, flash, lock, spades, jacks)
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels + sprockets:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Deploy': [12, 30, 59], 'FireDeployed': [2]}, scale=1.6, target=(0, -0.05, 0.25))
