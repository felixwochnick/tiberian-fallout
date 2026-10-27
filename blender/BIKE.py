"""
Tiberian Fallout – Nod attack cycle (BIKE), after Tiberian Sun.

A long, low armoured motorcycle like the original: a black body on a silver frame, a
big front wheel on a long silver fork, a broad rear wheel; the rider lies forward
under a dark red hump of armour. At the back, on both sides of the rear wheel, a big
red (house colour) rocket pod with two tubes, their mouths facing forward.

Nodes the game uses: "Cannon" (the rocket pods, tipped towards the target),
"FlashLeft" / "FlashRight" (a pod's muzzle flash; the shots take turns). Clips: Idle,
Walk, Fire (see nodvehicle.py).

Run headless:

    Blender -b --factory-startup --python blender/BIKE.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'BIKE.glb')
BLEND = os.path.join(HERE, 'BIKE.blend')

FRONT = (-0.25, 0.085, 0.05)    # the front wheel: y, radius, width
REAR = (0.2, 0.085, 0.075)      # the rear wheel
WALK_FRAMES = 14
WALK_SPEED = 2 * math.pi * REAR[1] / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 10
SCALE = 1.25                     # against the harvester and the walkers
PODS = Vector((0, 0.15, 0.17))  # the pods' pivot (between them, beside the rear wheel)
POD_X = 0.1

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def frame(m):
    """Body, armour hump, rider, fork, swingarm."""
    fy, fr, _ = FRONT
    ry, rr, _ = REAR
    parts = [
        # the body: long and low, black, a beak over the front wheel
        kit.hexahedron('Body', m['armour_dark'], (
            (-0.045, -0.2, 0.11), (0.045, -0.2, 0.11), (0.05, 0.14, 0.11), (-0.05, 0.14, 0.11),
            (-0.04, -0.17, 0.2), (0.04, -0.17, 0.2), (0.045, 0.14, 0.22), (-0.045, 0.14, 0.22)), bevel=0.018),
        kit.hexahedron('Beak', m['armour_dark'], (
            (-0.04, -0.34, 0.17), (0.04, -0.34, 0.17), (0.045, -0.17, 0.15), (-0.045, -0.17, 0.15),
            (-0.03, -0.33, 0.2), (0.03, -0.33, 0.2), (0.04, -0.17, 0.22), (-0.04, -0.17, 0.22)), bevel=0.014),
        kit.hexahedron('Tail', m['armour_dark'], (
            (-0.04, 0.12, 0.17), (0.04, 0.12, 0.17), (0.035, 0.33, 0.2), (-0.035, 0.33, 0.2),
            (-0.04, 0.12, 0.23), (0.04, 0.12, 0.23), (0.03, 0.32, 0.23), (-0.03, 0.32, 0.23)), bevel=0.012),
        # the dark red hump of armour over the rider
        kit.hexahedron('Hump', m['hump'], (
            (-0.055, -0.12, 0.2), (0.055, -0.12, 0.2), (0.055, 0.12, 0.21), (-0.055, 0.12, 0.21),
            (-0.035, -0.06, 0.29), (0.035, -0.06, 0.29), (0.04, 0.08, 0.28), (-0.04, 0.08, 0.28)), bevel=0.03),
        # the rider's helmet and arms in front of it
        sphere('Helmet', m['dark'], 0.032, (0, -0.135, 0.255), 12),
        box('HelmetVisor', m['glass'], (0.04, 0.012, 0.014), (0, -0.164, 0.258), bevel=0.003),
        *[beam(f'Arm{s}', m['dark'], (s * 0.045, -0.1, 0.24), (s * 0.05, -0.2, 0.22), 0.022) for s in (-1, 1)],
        beam('Handlebar', m['steel_light'], (-0.07, -0.21, 0.22), (0.07, -0.21, 0.22), 0.012),
        # the silver frame under the body: engine, fork, swingarm
        box('Engine', m['steel_light'], (0.08, 0.14, 0.06), (0, -0.02, 0.085), bevel=0.014),
        *detail.grille('EngineFins', m['steel'], m['dark'], (0, -0.092, 0.085), 0.07, 0.045, 'Y', 4, 0.006),
        *[beam(f'Fork{s}', m['steel_light'], (s * 0.033, fy, fr), (s * 0.036, -0.2, 0.22), 0.016) for s in (-1, 1)],
        *[beam(f'ForkSleeve{s}', m['steel'], (s * 0.036, -0.215, 0.14), (s * 0.036, -0.2, 0.21), 0.024) for s in (-1, 1)],
        *[beam(f'Swingarm{s}', m['steel_light'], (s * 0.048, 0.04, 0.09), (s * 0.048, ry, rr), 0.022) for s in (-1, 1)],
        beam('Shock', m['steel_light'], (0, 0.06, 0.1), (0, 0.13, 0.19), 0.018),
        *[cylinder(f'Exhaust{s}', m['steel'], 0.012, 0.14, (s * 0.06, 0.14, 0.1), rotation=(math.radians(-82), 0, 0), segments=8) for s in (-1, 1)],
        *detail.lamp('Headlight', m['dark'], m['lamp_white'], (0, -0.342, 0.185), (0, -1, 0), 0.016),
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (0, 0.33, 0.215), (0, 1, 0), 0.01),
        box('FrontGuard', m['armour_dark'], (FRONT[2] + 0.02, 0.12, 0.012), (0, fy - 0.005, 2 * fr + 0.01), bevel=0.004),
    ]
    return kit.merge('Frame', parts)


def pods(m, body):
    """The two rocket pods beside the rear wheel on the Cannon node; returns (node, flashes)."""
    pivot = kit.parent(kit.empty('Cannon', PODS), body)
    parts = []
    flashes = []
    for s, side in ((-1, 'Left'), (1, 'Right')):
        x = s * POD_X
        parts += [
            beam(f'PodArm{s}', m['steel'], (s * 0.04, PODS.y, PODS.z + 0.03), (x, PODS.y, PODS.z + 0.03), 0.02),
            kit.hexahedron(f'Pod{s}', m['remap'], (
                (x - 0.035, PODS.y - 0.09, PODS.z - 0.045), (x + 0.035, PODS.y - 0.09, PODS.z - 0.045),
                (x + 0.035, PODS.y + 0.09, PODS.z - 0.045), (x - 0.035, PODS.y + 0.09, PODS.z - 0.045),
                (x - 0.03, PODS.y - 0.07, PODS.z + 0.05), (x + 0.03, PODS.y - 0.07, PODS.z + 0.05),
                (x + 0.03, PODS.y + 0.08, PODS.z + 0.05), (x - 0.03, PODS.y + 0.08, PODS.z + 0.05)), bevel=0.014),
            box(f'PodBand{s}', m['armour_dark'], (0.074, 0.02, 0.098), (x, PODS.y + 0.03, PODS.z), bevel=0.005),
            box(f'PodFace{s}', m['armour_dark'], (0.06, 0.01, 0.07), (x, PODS.y - 0.09, PODS.z - 0.002), bevel=0.004),
        ]
        for k in (-1, 1):
            tube = Vector((x, PODS.y - 0.095, PODS.z + k * 0.018))
            parts += [cylinder(f'Tube{s}{k}', m['steel'], 0.014, 0.012, tube, rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
                      cylinder(f'TubeHole{s}{k}', m['dark'], 0.009, 0.004, tube - Vector((0, 0.006, 0)), rotation=(math.pi / 2, 0, 0),
                               segments=10, bevel=0)]
        flashes.append(kit.parent(nod.flash(m, f'Flash{side}', (x, PODS.y - 0.12, PODS.z), 0.035), pivot))
    kit.parent(kit.merge('Pods', parts, PODS), pivot)
    return pivot, flashes


def build():
    root, body = nod.start('NodAttackCycle', 'AttackCycle', WALK_SPEED)
    m = nod.materials()
    m['hump'] = kit.material('HumpRed', kit.srgb('#5a1c1c'), 0.45, 0.4)
    kit.parent(frame(m), body)
    _, flashes = pods(m, body)
    front = kit.parent(nod.wheel(m, 'WheelFront', (0, FRONT[0], FRONT[1]), FRONT[1], FRONT[2], lugs=14, hub=0.62, rim=m['steel_light']), root)
    rear = kit.parent(nod.wheel(m, 'WheelRear', (0, REAR[0], REAR[1]), REAR[1], REAR[2], lugs=14, hub=0.62, rim=m['steel_light']), root)
    # (the front wheel is a little smaller; one turn a loop as well, so the loop has no jump)
    nod.camouflage(kit.collection().objects)
    nod.drive(body, [front, rear], WALK_FRAMES, rock=0.004)
    nod.fire(flashes, FIRE_FRAMES, walk_frames=WALK_FRAMES)
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in (front, rear):
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Fire': [1]}, scale=1.2, target=(0, 0, 0.2))
