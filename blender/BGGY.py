"""
Tiberian Fallout – Nod attack buggy (BGGY), after Tiberian Sun.

A fast, light four-wheeler like the original: four huge black off-road tyres on a
wide stance, standing free on long suspension arms; between them a narrow, low, dark
body like a dragster, a red (house colour) stripe along its flanks, the driver in
the open cockpit behind a small windscreen. At the back the raised engine deck with
the machine-gun turret on top (red on its back and sides), a tall whip antenna
behind it.

Nodes the game uses: "Cannon" (the gun, tipped towards the target), "Flash" (its
muzzle flash). Clips: Idle, Walk, Fire (see nodvehicle.py).

Run headless:

    Blender -b --factory-startup --python blender/BGGY.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'BGGY.glb')
BLEND = os.path.join(HERE, 'BGGY.blend')

WHEEL_RADIUS = 0.105
WHEEL_WIDTH = 0.09
WHEEL_X = 0.215
AXLES = (-0.22, 0.22)
WALK_FRAMES = 18        # one turn of the wheels: a fast vehicle
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 8
SCALE = 1.2                     # against the harvester and the walkers
GUN = Vector((0, 0.14, 0.33))           # the gun's pivot in the turret
BARREL = 0.17

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def hull(m):
    """The narrow body, cockpit, engine deck with the turret's base, suspension."""
    parts = [
        # the body: long, narrow and low, its nose drawn out between the front wheels
        kit.hexahedron('Body', m['armour_dark'], (
            (-0.085, -0.36, 0.09), (0.085, -0.36, 0.09), (0.1, 0.34, 0.08), (-0.1, 0.34, 0.08),
            (-0.07, -0.33, 0.15), (0.07, -0.33, 0.15), (0.1, 0.32, 0.2), (-0.1, 0.32, 0.2)), bevel=0.014),
        # the engine deck at the back, raised, the turret's base on it
        kit.hexahedron('EngineDeck', m['armour'], (
            (-0.12, 0.04, 0.15), (0.12, 0.04, 0.15), (0.12, 0.34, 0.15), (-0.12, 0.34, 0.15),
            (-0.1, 0.07, 0.26), (0.1, 0.07, 0.26), (0.1, 0.33, 0.26), (-0.1, 0.33, 0.26)), bevel=0.014),
        *detail.grille('EngineGrille', m['steel'], m['dark'], (0, 0.344, 0.2), 0.16, 0.07, 'Y', 4, 0.006),
        # the open cockpit: seat, driver, a small windscreen
        box('Seat', m['dark'], (0.1, 0.08, 0.04), (0, -0.02, 0.17), bevel=0.012),
        box('Torso', m['armour_dark'], (0.08, 0.06, 0.08), (0, 0.0, 0.215), bevel=0.02),
        sphere('Helmet', m['dark'], 0.036, (0, -0.02, 0.27), 12),
        box('HelmetVisor', m['glass'], (0.045, 0.015, 0.016), (0, -0.05, 0.272), bevel=0.004),
        box('Windscreen', m['glass'], (0.13, 0.008, 0.06), (0, -0.12, 0.2), bevel=0.003, rotation=(math.radians(-30), 0, 0)),
        box('Dash', m['armour'], (0.13, 0.06, 0.035), (0, -0.1, 0.16), bevel=0.008),
        # the nose: a bumper bar and headlights
        beam('Bumper', m['steel'], (-0.1, -0.38, 0.1), (0.1, -0.38, 0.1), 0.02),
        # the whip antenna behind the turret
        beam('Antenna', m['steel'], (0.08, 0.3, 0.26), (0.085, 0.31, 0.68), 0.006),
        cylinder('AntennaBase', m['dark'], 0.012, 0.02, (0.08, 0.3, 0.27), segments=8, bevel=0),
    ]
    for s in (-1, 1):
        parts += [
            # a red stripe along each flank, red at the back of the deck
            kit.hexahedron(f'Stripe{s}', m['remap'], (
                (s * 0.086, -0.3, 0.115), (s * 0.1, -0.3, 0.115), (s * 0.113, 0.3, 0.13), (s * 0.099, 0.3, 0.13),
                (s * 0.083, -0.3, 0.14), (s * 0.097, -0.3, 0.14), (s * 0.11, 0.3, 0.17), (s * 0.096, 0.3, 0.17)), bevel=0.003),
            box(f'DeckPanel{s}', m['remap'], (0.012, 0.18, 0.06), (s * 0.115, 0.2, 0.2), bevel=0.003),
            # suspension: two arms and a shock to every hub
            *[beam(f'Arm{s}{y}{d}', m['steel'], (s * 0.09, y + d * 0.04, 0.11), (s * (WHEEL_X - WHEEL_WIDTH / 2), y, WHEEL_RADIUS), 0.016)
              for y in AXLES for d in (-1, 1)],
            *[beam(f'Shock{s}{y}', m['remap'], (s * 0.09, y, 0.2 if y > 0 else 0.15), (s * (WHEEL_X - WHEEL_WIDTH / 2 - 0.01), y, WHEEL_RADIUS + 0.03),
                   0.018) for y in AXLES],
            *[cylinder(f'Hub{s}{y}', m['steel'], 0.028, 0.03, (s * (WHEEL_X - WHEEL_WIDTH / 2 - 0.01), y, WHEEL_RADIUS), rotation=(0, math.pi / 2, 0),
                       segments=10) for y in AXLES],
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.05, -0.36, 0.13), (0, -1, 0), 0.014),
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.09, 0.345, 0.24), (0, 1, 0), 0.01),
            cylinder(f'Exhaust{s}', m['steel'], 0.012, 0.08, (s * 0.06, 0.36, 0.13), rotation=(math.radians(75), 0, 0), segments=8),
        ]
    return kit.merge('Hull', parts)


def gun(m, body):
    """The small turret with the machine gun; returns (barrel, flash)."""
    kit.parent(kit.merge('Turret', [
        cylinder('TurretRing', m['armour_dark'], 0.07, 0.02, (0, GUN.y, 0.27), segments=16),
        kit.hexahedron('TurretBody', m['armour'], (
            (-0.06, GUN.y - 0.07, 0.275), (0.06, GUN.y - 0.07, 0.275), (0.065, GUN.y + 0.07, 0.275), (-0.065, GUN.y + 0.07, 0.275),
            (-0.045, GUN.y - 0.05, 0.36), (0.045, GUN.y - 0.05, 0.36), (0.05, GUN.y + 0.06, 0.36), (-0.05, GUN.y + 0.06, 0.36)), bevel=0.01),
        box('TurretBack', m['remap'], (0.1, 0.02, 0.06), (0, GUN.y + 0.07, 0.315), bevel=0.004),
        *[box(f'TurretSide{s}', m['remap'], (0.008, 0.08, 0.04), (s * 0.058, GUN.y + 0.01, 0.315), bevel=0.003) for s in (-1, 1)],
        box('Sight', m['glass'], (0.03, 0.01, 0.014), (0.025, GUN.y - 0.055, 0.35), bevel=0.002),
    ]), body)
    pivot = kit.parent(kit.empty('Cannon', GUN), body)
    tip = GUN - Vector((0, BARREL, 0))
    barrel = kit.merge('Barrel', [
        *[cylinder(f'BarrelTube{s}', m['steel'], 0.01, BARREL, GUN + Vector((s * 0.018, -BARREL / 2, 0)), rotation=(math.pi / 2, 0, 0), segments=10)
          for s in (-1, 1)],
        box('Mantlet', m['armour_dark'], (0.07, 0.03, 0.04), GUN - Vector((0, 0.06, 0)), bevel=0.006),
        *[cylinder(f'FlashHider{s}', m['dark'], 0.013, 0.025, tip + Vector((s * 0.018, 0.01, 0)), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0)
          for s in (-1, 1)],
    ], GUN)
    kit.parent(barrel, pivot)
    flash = kit.parent(nod.flash(m, 'Flash', tip - Vector((0, 0.02, 0)), 0.035), pivot)
    return barrel, flash


def build():
    root, body = nod.start('NodBuggy', 'Buggy', WALK_SPEED)
    m = nod.materials()
    kit.parent(hull(m), body)
    barrel, flash = gun(m, body)
    wheels = [kit.parent(nod.wheel(m, f'Wheel{s}{k}', (s * WHEEL_X, y, WHEEL_RADIUS), WHEEL_RADIUS, WHEEL_WIDTH, lugs=16, hub=0.5), root)
              for s in (-1, 1) for k, y in enumerate(AXLES)]
    nod.camouflage(kit.collection().objects)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.005)
    nod.fire([flash], FIRE_FRAMES, (barrel, barrel.location.copy(), Vector((0, 0.025, 0))), WALK_FRAMES)
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [4], 'Fire': [1]}, scale=1.4, target=(0, 0, 0.22))
