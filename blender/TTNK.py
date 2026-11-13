"""
Tiberian Fallout – Nod tick tank (TTNK), after Tiberian Sun.

A low, wide tank, from above a flat rectangle: two big armour slabs, their tops
sloping a little outwards, reach down over the tracks on both sides (red, the house
colour, on top; dark skirts down their outer sides with the road wheels showing
under them); between them the hull with two rounded ridges along its back, a broad
grille in its front and a toothed digging lip under the nose. A small, low, eight-
sided turret with a short, thick cannon sits in front of the ridges. Hatches, stowage
boxes and lamps on the slabs, engine grilles in their backs, twin exhausts on the
right one, an antenna on the left.

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
WHEELS_Y = (-0.17, 0.0, 0.17)    # the road wheels between the sprockets (as big as they)
WALK_FRAMES = 28
WALK_SPEED = 2 * math.pi * SPROCKET / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 20
GUN = Vector((0, -0.19, 0.315))  # the cannon's trunnion in the turret's front
BARREL = 0.25
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

# the faces of kit.hexahedron's solids: bottom, top, front, right, back, left
FACES = ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))


def solid(name, verts, mats, bevel=0.012):
    """kit.hexahedron with a material per face (`mats` in the order of FACES): the
    faces nobody sees get a plain one, so the camouflage does not cut them up."""
    unique = list(dict.fromkeys(mats))

    def build(bm):
        v = [bm.verts.new(p) for p in verts]
        for face, mat in zip(FACES, mats):
            bm.faces.new([v[i] for i in face]).material_index = unique.index(mat)

    obj = kit.mesh_object(name, build)
    for mat in unique:
        mat.use_backface_culling = True
        obj.data.materials.append(mat)
    mod = obj.modifiers.new('Bevel', 'BEVEL')      # as kit.finish
    mod.width, mod.segments = bevel, 2
    mod.limit_method, mod.angle_limit, mod.harden_normals = 'ANGLE', math.radians(35), True
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


SLAB_SLOPE = math.atan2(0.032, 0.185)   # the slabs' tops fall outwards


def slab_top(x):
    """The height of a slab's top at x (either side)."""
    return 0.272 - 0.032 * (abs(x) - 0.15) / 0.185


def guards(m):
    """The armour slabs over the tracks: flat, a little lower outside, chamfered in
    front; dark, red on top, with skirts down their outer sides."""
    parts = []
    for s in (-1, 1):
        x0, x1 = s * 0.15, s * 0.335
        parts += [
            solid(f'Slab{s}', (
                (x0, -0.445, 0.13), (x1, -0.445, 0.12), (x1, 0.435, 0.12), (x0, 0.435, 0.13),
                (x0, -0.395, 0.272), (x1 - s * 0.014, -0.395, 0.24), (x1 - s * 0.014, 0.41, 0.24), (x0, 0.41, 0.272)),
                (m['dark'], m['remap'], m['armour_dark'], m['armour_dark'], m['armour_dark'], m['dark']), bevel=0.012),
            # the seam across its red top, a rim along its inner edge
            beam(f'SlabSeam{s}', m['seam'], (x0 + s * 0.01, 0.01, 0.271), (x1 - s * 0.02, 0.01, 0.243), 0.008, 0.006),
            beam(f'SlabRim{s}', m['armour_dark'], (x0 + s * 0.008, -0.39, 0.274), (x0 + s * 0.008, 0.405, 0.274), 0.016, 0.01),
            # the skirt down the outer side, its front sloped, rivets along it
            solid(f'Skirt{s}', (
                (x1 - s * 0.01, -0.4, 0.085), (x1 + s * 0.008, -0.4, 0.085), (x1 + s * 0.008, 0.43, 0.085), (x1 - s * 0.01, 0.43, 0.085),
                (x1 - s * 0.01, -0.435, 0.2), (x1 + s * 0.006, -0.435, 0.2), (x1 + s * 0.006, 0.43, 0.2), (x1 - s * 0.01, 0.43, 0.2)),
                (m['dark'], m['armour'], m['armour'], m['armour'], m['armour'], m['dark']), bevel=0.005),
            *detail.rivets(f'SkirtRivet{s}', m['steel'], (x1 + s * 0.009, -0.37, 0.18), (x1 + s * 0.009, 0.39, 0.18), 9, 0.006, 'X'),
            *[box(f'SkirtRib{s}{k}', m['armour_dark'], (0.012, 0.02, 0.09), (x1 + s * 0.01, y, 0.135), bevel=0.003)
              for k, y in enumerate((-0.12, 0.12))],
            # on top: a hatch, stowage boxes at the back, the headlight on the front corner
            box(f'SlabHatch{s}', m['armour_dark'], (0.075, 0.075, 0.014), (s * 0.235, -0.2, slab_top(0.235) + 0.004), bevel=0.004,
                rotation=(0, s * SLAB_SLOPE, 0)),
            box(f'SlabHatchHinge{s}', m['steel'], (0.06, 0.01, 0.01), (s * 0.235, -0.16, slab_top(0.235) + 0.009), bevel=0.002,
                rotation=(0, s * SLAB_SLOPE, 0)),
            *[box(f'Stowage{s}{k}', m['armour'], (0.07, 0.05, 0.035), (s * x, 0.3 - 0.06 * k, slab_top(x) + 0.014), bevel=0.006,
                  rotation=(0, s * SLAB_SLOPE, 0)) for k, x in enumerate((0.2, 0.26))],
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.29, -0.428, 0.2), (0, -1, 0.4), 0.014),
            box(f'LampGuard{s}', m['steel'], (0.05, 0.008, 0.008), (s * 0.29, -0.442, 0.222), bevel=0.002),
            # the engine grille in its back
            *detail.grille(f'BackGrille{s}', m['steel'], m['dark'], (s * 0.245, 0.44, 0.18), 0.12, 0.07, 'Y', 5, 0.008),
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.32, 0.44, 0.22), (0, 1, 0), 0.009),
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
    """The camouflaged hull between the slabs (returned alone) and its fittings."""
    shell = kit.merge('Hull', [
        solid('HullLow', (
            (-0.16, -0.43, 0.06), (0.16, -0.43, 0.06), (0.16, 0.435, 0.06), (-0.16, 0.435, 0.06),
            (-0.16, -0.43, 0.27), (0.16, -0.43, 0.27), (0.16, 0.435, 0.27), (-0.16, 0.435, 0.27)),
            (m['dark'], m['armour'], m['armour'], m['dark'], m['dark'], m['dark']), bevel=0.012),
        # two rounded ridges along the back, behind the turret
        *[cylinder(f'Ridge{s}', m['armour'], 0.07, 0.36, (s * 0.075, 0.165, 0.27), rotation=(math.pi / 2, 0, 0), segments=18, bevel=0.01)
          for s in (-1, 1)],
    ])
    parts = [
        # the front: a broad grille under the turret, the toothed digging lip under it
        box('GrilleFrame', m['armour_dark'], (0.27, 0.014, 0.13), (0, -0.434, 0.165), bevel=0.004),
        *[box(f'GrilleSlat{k}', m['dark'], (0.25, 0.012, 0.01), (0, -0.441, 0.115 + k * 0.02), bevel=0, rotation=(math.radians(-25), 0, 0))
          for k in range(6)],
        box('GrilleBar', m['steel'], (0.012, 0.016, 0.12), (0, -0.444, 0.165), bevel=0.002),
        kit.hexahedron('Lip', m['steel'], (
            (-0.15, -0.43, 0.035), (0.15, -0.43, 0.035), (0.15, -0.47, 0.035), (-0.15, -0.47, 0.035),
            (-0.15, -0.43, 0.09), (0.15, -0.43, 0.09), (0.15, -0.455, 0.07), (-0.15, -0.455, 0.07)), bevel=0.004),
        *[kit.hexahedron(f'Tooth{k}', m['steel'], (
            (x - 0.012, -0.465, 0.035), (x + 0.012, -0.465, 0.035), (x + 0.006, -0.505, 0.03), (x - 0.006, -0.505, 0.03),
            (x - 0.012, -0.46, 0.06), (x + 0.012, -0.46, 0.06), (x + 0.006, -0.5, 0.042), (x - 0.006, -0.5, 0.042)), bevel=0.002)
          for k, x in enumerate(-0.12 + 0.04 * i for i in range(7))],
        *[box(f'TowHook{s}', m['steel'], (0.025, 0.03, 0.025), (s * 0.135, -0.445, 0.24), bevel=0.005) for s in (-1, 1)],
        # the hull's top in front of the turret: a seam and a driver's hatch with a slit
        box('DriverHatch', m['armour_dark'], (0.07, 0.05, 0.012), (-0.07, -0.37, 0.274), bevel=0.004),
        box('DriverSlit', m['glass'], (0.05, 0.008, 0.01), (-0.07, -0.398, 0.276), bevel=0.002),
        *detail.seam('HullSeam', m['seam'], (-0.15, -0.33, 0.272), (0.15, -0.33, 0.272), 0.006, 0.004),
        # the exhausts: two pipes on the right slab at the back, out of the turret's way
        *[cylinder(f'Exhaust{k}', m['steel_light'], 0.02, 0.15, (0.225 + 0.05 * k, 0.34, 0.272), rotation=(math.pi / 2, 0, 0), segments=10)
          for k in range(2)],
        *[cylinder(f'ExhaustTip{k}', m['dark'], 0.018, 0.012, (0.225 + 0.05 * k, 0.417, 0.272), rotation=(math.pi / 2, 0, 0), segments=10,
                   bevel=0) for k in range(2)],
        box('ExhaustClamp', m['steel'], (0.11, 0.02, 0.035), (0.25, 0.31, 0.262), bevel=0.004),
        # the tail plate the turret sits on when dug in, kept clear in the middle
        box('BackPlate', m['armour_dark'], (0.3, 0.012, 0.18), (0, 0.44, 0.165), bevel=0.003),
        *[box(f'BackBumper{s}', m['steel'], (0.05, 0.025, 0.03), (s * 0.13, 0.452, 0.07), bevel=0.005) for s in (-1, 1)],
        *rails(m),
        box('Hatch', m['armour_dark'], (0.07, 0.07, 0.016), (-0.075, 0.24, 0.343), bevel=0.004),
        box('HatchHandle', m['steel'], (0.04, 0.008, 0.008), (-0.075, 0.215, 0.354), bevel=0.002),
        # the antenna on the left slab, out of the turret's way
        cylinder('AntennaBase', m['steel'], 0.012, 0.02, (-0.29, 0.38, 0.26), segments=8),
        beam('Antenna', m['steel'], (-0.29, 0.38, 0.26), (-0.31, 0.43, 0.56), 0.006),
    ]
    return shell, kit.merge('HullDetails', parts)


def turret(m, body):
    """The small, low turret with the cannon: on its slide (which carries it to the
    tail), turning on the node Turret; returns (slide, barrel, flash)."""
    slide = kit.parent(kit.empty('TurretSlide', TURRET_HOME), body)
    turn = kit.parent(kit.empty('Turret', TURRET_HOME), slide)
    centre = TURRET_HOME + Vector((0, -0.005, 0))
    eight = (0, 0, math.pi / 8)              # a flat face to the front
    kit.parent(kit.merge('TurretBody', [
        cylinder('TurretHull', m['armour_dark'], 0.128, 0.1, centre + Vector((0, 0, 0.05)), rotation=eight, segments=8, bevel=0.012,
                 radius2=0.098),
        # a red band round its foot, a dark roof plate
        cylinder('TurretBand', m['remap'], 0.131, 0.024, centre + Vector((0, 0, 0.03)), rotation=eight, segments=8, bevel=0.004,
                 radius2=0.125),
        cylinder('TurretRoof', m['armour'], 0.085, 0.01, centre + Vector((0, 0, 0.102)), rotation=eight, segments=8, bevel=0.003),
        # the commander's cupola with its periscopes, a vent at the back, a smoke launcher each side
        cylinder('Cupola', m['armour'], 0.032, 0.03, centre + Vector((0.045, 0.03, 0.115)), segments=12),
        box('Periscope', m['glass'], (0.03, 0.01, 0.014), centre + Vector((0.045, 0.0, 0.12)), bevel=0.002),
        *detail.grille('TurretVent', m['steel'], m['dark'], centre + Vector((-0.04, 0.03, 0.108)), 0.05, 0.05, 'Z', 4, 0.006),
        *[cylinder(f'Smoke{s}{k}', m['steel'], 0.009, 0.03, centre + Vector((s * (0.1 + 0.002 * k), -0.03 + 0.022 * k, 0.07)),
                   rotation=(math.radians(-30), s * math.radians(40), 0), segments=8) for s in (-1, 1) for k in range(2)],
        # the carriage under it that runs on the rail
        box('Carriage', m['steel'], (0.2, 0.22, 0.03), TURRET_HOME + Vector((0, 0, -0.005)), bevel=0.006),
    ], TURRET_HOME), turn)
    pivot = kit.parent(kit.empty('Cannon', GUN), turn)
    tip = GUN - Vector((0, BARREL, 0))
    barrel = kit.merge('Barrel', [
        box('Mantlet', m['armour'], (0.09, 0.05, 0.065), GUN - Vector((0, 0.01, 0)), bevel=0.012),
        cylinder('Tube', m['steel'], 0.026, BARREL, GUN - Vector((0, BARREL / 2 + 0.03, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('Sleeve', m['armour_dark'], 0.036, 0.09, GUN - Vector((0, 0.09, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('Evacuator', m['armour_dark'], 0.033, 0.04, GUN - Vector((0, 0.18, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        box('MuzzleBrake', m['steel'], (0.075, 0.05, 0.042), tip - Vector((0, 0.035, 0)), bevel=0.006),
        box('MuzzleSlot', m['dark'], (0.078, 0.012, 0.024), tip - Vector((0, 0.035, 0)), bevel=0),
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
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], 0.12, 12), body)
        # the sprockets and idlers at the ends of the tracks, the road wheels between them
        # (all as big, so they turn together), their lower halves under the skirts
        for k, y in enumerate((TRACK[0] + 0.05, TRACK[1] - 0.05)):
            wheels.append(kit.parent(nod.road_wheel(m, f'Sprocket{s}{k}', (s * (TRACK_X + TRACK_WIDTH / 2 + 0.004), y, SPROCKET + 0.002),
                                                    SPROCKET, 0.02), body))
        for k, y in enumerate(WHEELS_Y):
            wheels.append(kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (s * (TRACK_X + TRACK_WIDTH / 2 + 0.004), y, SPROCKET + 0.002),
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
