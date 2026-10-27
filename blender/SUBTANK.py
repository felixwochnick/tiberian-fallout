"""
Tiberian Fallout – Nod Devil's Tongue (SUBTANK), after Tiberian Sun.

A long, low subterranean flame tank: the tracks run its whole length under ribbed
armour skirts, between them the flat dark hull, its nose a wedge with two drill cones
at its corners to dig with; on the deck a raised spine with red (house colour) armour
panels, behind it two napalm tanks lying along the back with red bands. In the nose
the flame projector: an armoured housing with the nozzle, a pilot light in its mouth.

It travels under the ground like the subterranean APC (SAPC): it digs straight down
where it stands, crosses the map below it and comes up nose first where it surfaces.

Nodes the game uses: "Turret" (the projector's mount, not animated), "Cannon" (the
projector, tipped towards the target), "Flash" (the flame at the nozzle). Clips (see
nodvehicle.py for Idle and Walk):
    Idle         loop, 2 s: the engine runs, the hull shivers
    Walk         loop: driving, the wheels turn; walkSpeed on the root
    Fire         once, 0.7 s: a gout of flame from the nozzle, the projector kicks
    Burrow       once, 2 s: it tips onto its nose and digs straight down, out of sight
    Underground  loop: down there (hidden in the game while it travels)
    Surface      once, 2 s: up nose first out of the ground, then down onto its tracks

Run headless:

    blender -b --factory-startup --python blender/SUBTANK.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'SUBTANK.glb')
BLEND = os.path.join(HERE, 'SUBTANK.blend')

TRACK_X = 0.2
TRACK_WIDTH = 0.11
TRACK = (-0.42, 0.44)
WHEEL = 0.042
WHEELS_Y = (-0.34, -0.2, -0.06, 0.08, 0.22, 0.36)
WALK_FRAMES = 22
WALK_SPEED = 2 * math.pi * WHEEL / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 22
BURROW_FRAMES = 60
DOWN = math.radians(88)
DEPTH = 0.85
DECK = 0.2
GUN = Vector((0, -0.36, 0.2))     # the projector's pivot
NOZZLE = Vector((0, -0.54, 0.2))
SCALE = 1.0

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def drill(m, name, base, radius, length):
    """A small drill cone pointing forward (-y) with a spiral rib."""
    base = Vector(base)
    parts = [cylinder(f'{name}Cone', m['steel_light'], radius, length, base - Vector((0, length / 2, 0)), rotation=(math.pi / 2, 0, 0),
                      segments=14, bevel=0, radius2=0.004)]
    steps = 10
    points = []
    for i in range(steps + 1):
        t = i / steps * 0.9
        a = 2 * math.pi * 1.5 * i / steps
        r = radius * (1 - t) * 1.05 + 0.002
        points.append(base + Vector((r * math.sin(a), -t * length, r * math.cos(a))))
    parts += [beam(f'{name}Rib{i}', m['steel'], a, b, 0.01, 0.008) for i, (a, b) in enumerate(zip(points, points[1:]))]
    parts.append(cylinder(f'{name}Collar', m['armour_dark'], radius * 1.15, 0.03, base + Vector((0, 0.012, 0)), rotation=(math.pi / 2, 0, 0), segments=14))
    return parts


def hull(m):
    parts = [
        # the hull: flat, its nose a wedge
        kit.hexahedron('Hull', m['armour'], (
            (-0.15, -0.44, 0.06), (0.15, -0.44, 0.06), (0.15, 0.45, 0.06), (-0.15, 0.45, 0.06),
            (-0.15, -0.3, DECK), (0.15, -0.3, DECK), (0.15, 0.44, DECK), (-0.15, 0.44, DECK)), bevel=0.012),
        # the spine on the deck with its red panels
        kit.hexahedron('Spine', m['armour_dark'], (
            (-0.1, -0.24, DECK - 0.01), (0.1, -0.24, DECK - 0.01), (0.1, 0.2, DECK - 0.01), (-0.1, 0.2, DECK - 0.01),
            (-0.08, -0.18, DECK + 0.07), (0.08, -0.18, DECK + 0.07), (0.08, 0.18, DECK + 0.07), (-0.08, 0.18, DECK + 0.07)), bevel=0.012),
        *[kit.hexahedron(f'Panel{k}', m['remap'], (
            (-0.075, y0, DECK + 0.068), (0.075, y0, DECK + 0.068), (0.075, y1, DECK + 0.068), (-0.075, y1, DECK + 0.068),
            (-0.065, y0 + 0.01, DECK + 0.082), (0.065, y0 + 0.01, DECK + 0.082), (0.065, y1 - 0.01, DECK + 0.082), (-0.065, y1 - 0.01, DECK + 0.082)),
            bevel=0.004) for k, (y0, y1) in enumerate(((-0.16, -0.02), (0.02, 0.16)))],
        box('Periscope', m['glass'], (0.05, 0.01, 0.018), (-0.04, -0.2, DECK + 0.05), bevel=0.002, rotation=(math.radians(-25), 0, 0)),
        *detail.grille('Vent', m['steel'], m['dark'], (0, 0.4, DECK + 0.002), 0.16, 0.06, 'Z', 4, 0.006),
        box('BackPlate', m['armour_dark'], (0.28, 0.012, 0.12), (0, 0.455, 0.14), bevel=0.003),
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (-0.09, 0.463, 0.17), (0, 1, 0), 0.01),
        beam('Antenna', m['steel'], (0.12, 0.42, DECK), (0.13, 0.46, 0.5), 0.006),
    ]
    for s in (-1, 1):
        x0, x1 = s * 0.145, s * 0.27
        parts += [
            # the napalm tank on the back, a red band round it
            cylinder(f'Tank{s}', m['armour_dark'], 0.045, 0.2, (s * 0.075, 0.31, DECK + 0.04), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0.012),
            cylinder(f'TankBand{s}', m['remap'], 0.047, 0.03, (s * 0.075, 0.31, DECK + 0.04), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0.003),
            box(f'TankStrap{s}', m['steel'], (0.1, 0.016, 0.012), (s * 0.075, 0.24, DECK + 0.002), bevel=0.002),
            # the armour skirt over the track, ribbed
            kit.hexahedron(f'Skirt{s}', m['armour'], (
                (x0, -0.43, 0.07), (x1, -0.43, 0.07), (x1, 0.45, 0.06), (x0, 0.45, 0.06),
                (x0, -0.36, 0.18), (x1, -0.36, 0.17), (x1, 0.45, 0.17), (x0, 0.45, 0.18)), bevel=0.01),
            *[kit.hexahedron(f'Rib{s}{k}', m['steel_light'], (
                (x1 + s * 0.001, -0.3 + k * 0.1, 0.07), (x1 + s * 0.012, -0.3 + k * 0.1, 0.07),
                (x1 + s * 0.012, -0.27 + k * 0.1, 0.07), (x1 + s * 0.001, -0.27 + k * 0.1, 0.07),
                (x1 + s * 0.001, -0.25 + k * 0.1, 0.165), (x1 + s * 0.012, -0.25 + k * 0.1, 0.165),
                (x1 + s * 0.012, -0.22 + k * 0.1, 0.165), (x1 + s * 0.001, -0.22 + k * 0.1, 0.165)), bevel=0.002) for k in range(7)],
            box(f'SkirtStripe{s}', m['remap'], (0.1, 0.5, 0.008), (s * 0.207, 0.12, 0.177), bevel=0.002),
            # a drill cone at the nose's corner
            *drill(m, f'Drill{s}', (s * 0.2, -0.42, 0.12), 0.05, 0.14),
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.1, -0.385, 0.15), (0, -1, 0.6), 0.012),
        ]
    return kit.merge('Hull', parts)


def projector(m, body):
    """The flame projector in the nose on Turret → Cannon; returns (barrel, flash)."""
    turret = kit.parent(kit.empty('Turret', GUN), body)
    cannon = kit.parent(kit.empty('Cannon', GUN), turret)
    kit.parent(kit.merge('ProjectorHousing', [
        kit.hexahedron('Housing', m['armour_dark'], (
            (-0.07, -0.42, 0.13), (0.07, -0.42, 0.13), (0.075, -0.28, 0.15), (-0.075, -0.28, 0.15),
            (-0.055, -0.42, 0.25), (0.055, -0.42, 0.25), (0.06, -0.28, 0.26), (-0.06, -0.28, 0.26)), bevel=0.012),
        box('HousingStripe', m['remap'], (0.08, 0.1, 0.008), (0, -0.35, 0.262), bevel=0.002),
    ], GUN), turret)
    barrel = kit.merge('Nozzle', [
        cylinder('NozzleTube', m['steel'], 0.026, 0.12, GUN - Vector((0, 0.11, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('NozzleBell', m['steel_light'], 0.024, 0.04, NOZZLE + Vector((0, 0.03, 0)), rotation=(math.pi / 2, 0, 0), segments=14,
                 radius2=0.034),
        cylinder('NozzleMouth', m['dark'], 0.026, 0.006, NOZZLE + Vector((0, 0.008, 0)), rotation=(math.pi / 2, 0, 0), segments=14, bevel=0),
        cylinder('PilotLight', m['lamp_amber'], 0.008, 0.008, NOZZLE + Vector((0, 0.004, -0.014)), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0),
        *[cylinder(f'FuelLine{s}', m['dark'], 0.008, 0.1, GUN + Vector((s * 0.032, -0.13, -0.02)), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0)
          for s in (-1, 1)],
    ], GUN)
    kit.parent(barrel, cannon)
    flash = kit.parent(nod.flash(m, 'Flash', NOZZLE - Vector((0, 0.04, 0)), 0.065), cannon)
    return barrel, flash


def burn(barrel, flash):
    """Fire: the flame bursts from the nozzle and flickers, the projector kicks a little."""
    hidden = Vector((kit.HIDDEN,) * 3)
    flame = {0: hidden, 1: Vector((0.8, 1.2, 0.8))}
    for f in range(3, 15, 2):
        flame[f] = Vector((1.2, 1.9, 1.2)) if f % 4 == 1 else Vector((1.0, 1.6, 1.0))
    flame |= {15: Vector((0.7, 1.1, 0.7)), 17: hidden, FIRE_FRAMES: hidden}
    kit.keys(flash, 'scale', flame, 'CONSTANT')
    kit.to_track(flash, 'Fire')
    rest = barrel.location.copy()
    kick = rest + Vector((0, 0.02, 0))
    kit.keys(barrel, 'location', {0: rest, 2: kick, 14: kick, 19: rest, FIRE_FRAMES: rest})
    kit.to_track(barrel, 'Fire')
    barrel.location = rest
    flash.scale = hidden


def tunnel(body):
    """Burrow, Underground and Surface as the SAPC's."""
    keys = kit.keys
    still = Vector((0, 0, 0))
    nose_down, nose_up = Vector((DOWN, 0, 0)), Vector((-DOWN, 0, 0))
    below = Vector((0, 0, -DEPTH))
    keys(body, 'location', {0: still, 12: Vector((0, 0, -0.02)), 30: Vector((0, 0, -0.1)), BURROW_FRAMES: below})
    keys(body, 'rotation_euler', {0: still, 12: Vector((math.radians(30), 0, 0)), 30: nose_down, BURROW_FRAMES: nose_down})
    kit.to_track(body, 'Burrow')
    walker.hold(body, 'location', below, kit.IDLE_END, 'Underground')
    walker.hold(body, 'rotation_euler', nose_down, kit.IDLE_END, 'Underground')
    keys(body, 'location', {0: Vector((0, 0, -1.7 * DEPTH)), 30: Vector((0, 0, -0.05)), 48: still, BURROW_FRAMES: still})
    keys(body, 'rotation_euler', {0: nose_up, 30: nose_up, 48: Vector((math.radians(-20), 0, 0)), BURROW_FRAMES: still})
    kit.to_track(body, 'Surface')


def build():
    root, body = nod.start('NodDevilsTongue', 'DevilsTongue', WALK_SPEED)
    m = nod.materials()
    kit.parent(hull(m), body)
    barrel, flash = projector(m, body)
    wheels = []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], 0.1, 20), body)
        for k, y in enumerate(WHEELS_Y):
            wheels.append(kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (s * (TRACK_X + TRACK_WIDTH / 2 + 0.004), y, WHEEL + 0.005), WHEEL, 0.018), body))
    nod.camouflage(kit.collection().objects)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003)
    burn(barrel, flash)
    walker.hide([flash], kit.IDLE_END, 'Idle')
    walker.hide([flash], WALK_FRAMES, 'Walk')
    tunnel(body)
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Fire': [5], 'Burrow': [20, 40], 'Surface': [36]}, scale=1.6, target=(0, -0.04, 0.18))
