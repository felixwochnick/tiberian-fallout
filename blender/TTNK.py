"""
Tiberian Fallout – Nod tick tank (TTNK), after Tiberian Sun.

A broad, flat tank: two big wedge-shaped guards over the tracks, red (house colour)
on top and on their sloped fronts, dark armour down their sides,
between them the dark hull with two
rounded ridges along its back, a low turret with a short, thick cannon in front, a
toothed roller with two blades under the nose (it digs the tank in) and twin exhaust
pipes at the back. The tracks show under the guards' ends.

It drives and fires with its turret in front. Like the original it digs in where it
stands: the turret runs back along the hull on its rail and swings over onto the
tail, then the tank tips forward and drives its nose into the ground until it stands
upright, its tail with the turret up; the turret turns all round. Digging out is the
same backwards.

Nodes the game uses: "Cannon" (the gun, tipped towards the target), "Flash" (its
muzzle flash), "Turret" (turned about its vertical towards the target while dug in;
it sits on "TurretSlide", which carries it to the tail). Clips (see nodvehicle.py for
Idle, Walk, Fire):
    Deploy         once, 3 s: the turret runs to the tail, the tank digs in
    Deployed       loop: dug in
    FireDeployed   once: a shot, dug in
    Undeploy       once, 3 s: Deploy backwards

Run headless:

    Blender -b --factory-startup --python blender/TTNK.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'TTNK.glb')
BLEND = os.path.join(HERE, 'TTNK.blend')

TRACK_X = 0.245
TRACK_WIDTH = 0.13
TRACK = (-0.4, 0.4)
SPROCKET = 0.058
WALK_FRAMES = 28
WALK_SPEED = 2 * math.pi * SPROCKET / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 20
GUN = Vector((0, -0.16, 0.36))   # the cannon's trunnion in the turret's front
BARREL = 0.34
DEPLOY_FRAMES = 90
# dug in: the hull turned upright about x (nose down, tail up), shifted so the part
# above the ground stands over the origin, a little sunk
DEPLOYED_TURN = math.radians(90)
DEPLOYED_AT = Vector((0, 0.15, -0.05))
# the turret's base (its origin) on the way to the tail: in front on the hull, lifted
# onto its rail, along the rail to the back, round the rail's bend (RAIL_BEND, radius
# RAIL_RADIUS) over the edge of the tail, down onto the middle of the tail plate
TURRET_HOME = Vector((0, -0.075, 0.26))
RAIL_TOP = 0.36
RAIL_RADIUS = 0.1
RAIL_X = 0.1                        # the two rails, on the ridges
TAIL_Y = 0.445
RAIL_BEND = Vector((0, TAIL_Y - RAIL_RADIUS, RAIL_TOP - RAIL_RADIUS))
TURRET_TAIL = Vector((0, TAIL_Y, 0.165))
SCALE = 1.0

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def guards(m):
    """The track guards: wedges, low and sloped in front, square at the back; red,
    with dark armour skirts down their outer sides."""
    parts = []
    for s in (-1, 1):
        x0, x1 = s * 0.155, s * 0.335
        parts += [
            kit.hexahedron(f'Skirt{s}', m['armour_dark'], (
                (x1 - s * 0.012, -0.41, 0.09), (x1 + s * 0.006, -0.41, 0.09), (x1 + s * 0.006, 0.43, 0.05), (x1 - s * 0.012, 0.43, 0.05),
                (x1 - s * 0.012, -0.33, 0.2), (x1 + s * 0.004, -0.33, 0.2), (x1 + s * 0.004, 0.43, 0.21), (x1 - s * 0.012, 0.43, 0.21)), bevel=0.006),
            *[box(f'SkirtBolt{s}{k}', m['steel'], (0.008, 0.014, 0.014), (x1 + s * 0.008, -0.25 + k * 0.1, 0.17), bevel=0.002) for k in range(7)],
            box(f'BackPlate{s}', m['armour_dark'], (0.17, 0.012, 0.16), ((x0 + x1) / 2, 0.425, 0.15), bevel=0.003),
            kit.hexahedron(f'Guard{s}', m['remap'], (
                (x0, -0.44, 0.1), (x1, -0.44, 0.1), (x1, 0.42, 0.06), (x0, 0.42, 0.06),
                (x0, -0.3, 0.25), (x1 - s * 0.01, -0.3, 0.24), (x1 - s * 0.01, 0.42, 0.25), (x0, 0.42, 0.26)), bevel=0.012),
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.3, -0.33, 0.24), (0, -1, 0.5), 0.016),
            box(f'GuardLamp{s}', m['armour_dark'], (0.05, 0.04, 0.025), (s * 0.29, 0.38, 0.27), bevel=0.006),
        ]
    return kit.merge('Guards', parts)


def rails(m):
    """The two rails the turret runs on: along the ridges, round the bend over the
    tail's edge and down the tail plate."""
    under = 0.015                     # the rails' middle below the turret's base
    path = [Vector((0, -0.02, RAIL_TOP - under)), Vector((0, RAIL_BEND.y, RAIL_TOP - under))]
    for k in range(1, 7):
        a = math.radians(90) * k / 6
        path.append(RAIL_BEND + Vector((0, (RAIL_RADIUS - under) * math.sin(a), (RAIL_RADIUS - under) * math.cos(a))))
    path.append(Vector((0, TAIL_Y - under, 0.09)))
    parts = []
    for s in (-1, 1):
        side = Vector((s * RAIL_X, 0, 0))
        parts += [beam(f'Rail{s}_{k}', m['steel'], a + side, b + side, 0.022, 0.016) for k, (a, b) in enumerate(zip(path, path[1:]))]
        parts += [box(f'RailFoot{s}{k}', m['armour_dark'], (0.03, 0.03, 0.02), path[0].lerp(path[1], t) + side - Vector((0, 0, 0.015)), bevel=0.004)
                  for k, t in enumerate((0.2, 0.6, 0.95))]
    return parts


def hull(m):
    """The camouflaged hull between the guards (returned alone) and its fittings."""
    shell = kit.merge('Hull', [
        kit.hexahedron('HullLow', m['armour'], (
            (-0.16, -0.42, 0.06), (0.16, -0.42, 0.06), (0.16, 0.42, 0.06), (-0.16, 0.42, 0.06),
            (-0.16, -0.3, 0.27), (0.16, -0.3, 0.27), (0.16, 0.42, 0.27), (-0.16, 0.42, 0.27)), bevel=0.01),
        # two rounded ridges along the back, behind the turret
        *[cylinder(f'Ridge{s}', m['armour'], 0.07, 0.44, (s * 0.075, 0.09, 0.27), rotation=(math.pi / 2, 0, 0), segments=18, bevel=0.01)
          for s in (-1, 1)],
    ])
    parts = [
        # the roller with its teeth and the two blades under the nose
        cylinder('Roller', m['steel_light'], 0.05, 0.22, (0, -0.45, 0.08), rotation=(0, math.pi / 2, 0), segments=16),
        *[box(f'RollerRib{k}', m['steel'], (0.008, 0.012, 0.11), (-0.1 + k * 0.025, -0.45, 0.08), bevel=0, rotation=(math.radians(k * 25), 0, 0))
          for k in range(9)],
        *[kit.hexahedron(f'Blade{s}', m['steel_light'], (
            (s * 0.115, -0.42, 0.04), (s * 0.135, -0.42, 0.04), (s * 0.135, -0.56, 0.01), (s * 0.115, -0.56, 0.01),
            (s * 0.115, -0.42, 0.13), (s * 0.135, -0.42, 0.13), (s * 0.135, -0.5, 0.05), (s * 0.115, -0.5, 0.05)), bevel=0.003)
          for s in (-1, 1)],
        # the exhausts: two pipes on the right guard at the back, out of the turret's way
        *[cylinder(f'Exhaust{k}', m['steel_light'], 0.022, 0.16, (0.225 + 0.05 * k, 0.33, 0.285), rotation=(math.pi / 2, 0, 0), segments=10)
          for k in range(2)],
        *[cylinder(f'ExhaustTip{k}', m['dark'], 0.02, 0.012, (0.225 + 0.05 * k, 0.413, 0.285), rotation=(math.pi / 2, 0, 0), segments=10,
                   bevel=0) for k in range(2)],
        box('ExhaustClamp', m['steel'], (0.11, 0.02, 0.04), (0.25, 0.3, 0.275), bevel=0.004),
        box('BackPlate', m['armour_dark'], (0.3, 0.012, 0.16), (0, 0.426, 0.17), bevel=0.003),
        *rails(m),
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (-0.1, 0.433, 0.22), (0, 1, 0), 0.01),
        box('Hatch', m['armour_dark'], (0.08, 0.08, 0.016), (-0.075, 0.24, 0.343), bevel=0.004),
        # the antenna on the left guard, out of the turret's way
        beam('Antenna', m['steel'], (-0.29, 0.38, 0.26), (-0.31, 0.43, 0.56), 0.006),
    ]
    return shell, kit.merge('HullDetails', parts)


def turret(m, body):
    """The low turret with the cannon: on its slide (which carries it to the tail),
    turning on the node Turret; returns (slide, barrel, flash)."""
    slide = kit.parent(kit.empty('TurretSlide', TURRET_HOME), body)
    turn = kit.parent(kit.empty('Turret', TURRET_HOME), slide)
    kit.parent(kit.merge('TurretBody', [
        kit.hexahedron('TurretHull', m['armour_dark'], (
            (-0.14, -0.23, 0.26), (0.14, -0.23, 0.26), (0.15, 0.08, 0.26), (-0.15, 0.08, 0.26),
            (-0.1, -0.19, 0.42), (0.1, -0.19, 0.42), (0.11, 0.06, 0.42), (-0.11, 0.06, 0.42)), bevel=0.02),
        # red cheeks beside the gun and a red band round the back, like the original's
        *[kit.hexahedron(f'Cheek{s}', m['remap'], (
            (s * 0.055, -0.25, 0.28), (s * 0.15, -0.22, 0.28), (s * 0.15, -0.06, 0.28), (s * 0.055, -0.09, 0.28),
            (s * 0.055, -0.22, 0.41), (s * 0.11, -0.2, 0.4), (s * 0.11, -0.08, 0.4), (s * 0.055, -0.11, 0.41)), bevel=0.01) for s in (-1, 1)],
        kit.hexahedron('TurretBand', m['remap'], (
            (-0.152, 0.0, 0.3), (0.152, 0.0, 0.3), (0.152, 0.085, 0.3), (-0.152, 0.085, 0.3),
            (-0.13, 0.0, 0.37), (0.13, 0.0, 0.37), (0.13, 0.072, 0.37), (-0.13, 0.072, 0.37)), bevel=0.006),
        cylinder('Cupola', m['armour'], 0.04, 0.035, (0.045, -0.03, 0.435), segments=14),
        box('Periscope', m['glass'], (0.035, 0.01, 0.016), (0.045, -0.072, 0.44), bevel=0.002),
        *detail.grille('TurretVent', m['steel'], m['dark'], (-0.05, 0.0, 0.424), 0.06, 0.07, 'Y', 4, 0.006),
        # the carriage under it that runs on the rail
        box('Carriage', m['steel'], (0.2, 0.22, 0.03), TURRET_HOME + Vector((0, 0, -0.005)), bevel=0.006),
    ], TURRET_HOME), turn)
    pivot = kit.parent(kit.empty('Cannon', GUN), turn)
    tip = GUN - Vector((0, BARREL, 0))
    barrel = kit.merge('Barrel', [
        cylinder('Mantlet', m['armour'], 0.05, 0.06, GUN - Vector((0, 0.06, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('Tube', m['steel'], 0.024, BARREL, GUN - Vector((0, BARREL / 2 + 0.05, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('Sleeve', m['armour_dark'], 0.034, 0.1, GUN - Vector((0, 0.13, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        box('MuzzleBrake', m['steel'], (0.07, 0.05, 0.04), tip - Vector((0, 0.04, 0)), bevel=0.006),
    ], GUN)
    kit.parent(barrel, pivot)
    flash = kit.parent(nod.flash(m, 'Flash', tip - Vector((0, 0.09, 0)), 0.06), pivot)
    return slide, barrel, flash


def dig(body, slide, barrel, flash):
    """The clips Deploy, Deployed, FireDeployed and Undeploy (Deploy backwards)."""
    still = Vector((0, 0, 0))
    turned = Vector((DEPLOYED_TURN, 0, 0))
    lurch = (Vector((0, -0.03, 0.01)), Vector((math.radians(8), 0, 0)))
    tilt = Vector((math.radians(-90), 0, 0))   # the turret on the tail: its top towards the tail
    level = Vector((0, 0, 0))
    # frame: (body location, body rotation, turret location, turret rotation)
    poses = {
        0: (still, still, TURRET_HOME, level),
        8: (still, still, Vector((0, TURRET_HOME.y, RAIL_TOP)), level),
        30: (still, still, Vector((0, RAIL_BEND.y, RAIL_TOP)), level),
    }
    # round the bend: the base stays on the rail, the turret turns with it
    for k in range(1, 5):
        a = math.radians(90) * k / 4
        poses[30 + 4 * k] = (still, still, RAIL_BEND + Vector((0, RAIL_RADIUS * math.sin(a), RAIL_RADIUS * math.cos(a))), tilt * (k / 4))
    poses |= {
        54: (still, still, TURRET_TAIL, tilt),
        60: (still, still, TURRET_TAIL, tilt),
        68: (*lurch, TURRET_TAIL, tilt),
        84: (DEPLOYED_AT, turned, TURRET_TAIL, tilt),
        DEPLOY_FRAMES: (DEPLOYED_AT, turned, TURRET_TAIL, tilt),
    }
    for clip, order in (('Deploy', lambda f: f), ('Undeploy', lambda f: DEPLOY_FRAMES - f)):
        for k, (obj, path) in enumerate(((body, 'location'), (body, 'rotation_euler'), (slide, 'location'), (slide, 'rotation_euler'))):
            # the turret on its rail evenly (no overshoot round the bend), the hull eased
            kit.keys(obj, path, {order(f): pose[k] for f, pose in poses.items()}, 'LINEAR' if obj is slide else 'BEZIER')
        kit.to_track(body, clip)
        kit.to_track(slide, clip)
    # no muzzle flash meanwhile
    walker.hide([flash], DEPLOY_FRAMES, 'Deploy')
    walker.hide([flash], DEPLOY_FRAMES, 'Undeploy')
    walker.hide([flash], kit.IDLE_END, 'Deployed')
    # dug in, idle and firing: the pose held; the shot as when driving
    for clip, frames in (('Deployed', kit.IDLE_END), ('FireDeployed', FIRE_FRAMES)):
        walker.hold(body, 'location', DEPLOYED_AT, frames, clip)
        walker.hold(body, 'rotation_euler', turned, frames, clip)
        walker.hold(slide, 'location', TURRET_TAIL, frames, clip)
        walker.hold(slide, 'rotation_euler', tilt, frames, clip)
    rest = barrel.location.copy()
    kit.keys(barrel, 'location', {0: rest, 2: rest + Vector((0, 0.05, 0)), 5: rest + Vector((0, 0.05, 0)), 16: rest, FIRE_FRAMES: rest})
    kit.to_track(barrel, 'FireDeployed')
    hidden = Vector((kit.HIDDEN,) * 3)
    kit.keys(flash, 'scale', {0: Vector((1, 1, 1)), 2: Vector((1.3, 1.5, 1.3)), 4: hidden, FIRE_FRAMES: hidden}, 'CONSTANT')
    kit.to_track(flash, 'FireDeployed')
    barrel.location = rest
    flash.scale = hidden
    slide.location, slide.rotation_euler = TURRET_HOME, level


def build():
    root, body = nod.start('NodTickTank', 'TickTank', WALK_SPEED)
    m = nod.materials()
    kit.parent(guards(m), body)
    for obj in hull(m):
        kit.parent(obj, body)
    slide, barrel, flash = turret(m, body)
    wheels = []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], 0.12, 20), body)
        # the sprockets and idlers at the ends of the tracks, out of the guards
        for k, y in enumerate((TRACK[0] + 0.05, TRACK[1] - 0.05)):
            wheels.append(kit.parent(nod.road_wheel(m, f'Sprocket{s}{k}', (s * (TRACK_X + TRACK_WIDTH / 2 + 0.004), y, SPROCKET + 0.002),
                                                    SPROCKET, 0.02), body))
    nod.camouflage(kit.collection().objects)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003)
    nod.fire([flash], FIRE_FRAMES, (barrel, barrel.location.copy(), Vector((0, 0.05, 0))), WALK_FRAMES)
    dig(body, slide, barrel, flash)
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Deploy': [20, 38, 46, 60, 74, 89], 'FireDeployed': [1]}, scale=1.4, target=(0, -0.05, 0.25))
