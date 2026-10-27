"""
Tiberian Fallout – Nod mobile repair vehicle (REPAIR), after Tiberian Sun.

A tracked workshop: a boxy dark hull over the tracks, its sloped front with a small
armoured cab and a slit window on the left, red (house colour) bands over the
fenders and round the deck; tool lockers, a spare-parts rack and a beacon on the
deck. Behind the middle on a turntable the repair crane, folded like a Z: the lower
boom rises up and back to the elbow, the upper boom reaches forward over the cab,
the welding head with its claw at its end pointing down.

Nodes the game uses: "Turret" (the turntable, not animated), "Cannon" (the crane's
base, tipped towards the target), "Flash" (the welding sparks at the head). The
crane's own joints: "ArmLower", "ArmUpper", "ArmHead". Clips (see nodvehicle.py):
    Idle    loop, 2 s: the engine runs, the beacon turns its light round
    Walk    loop: driving, the wheels turn; walkSpeed on the root
    Fire    once, 1 s: the crane swings forward and down, the head welds (sparks
            flicker), the crane folds back

Run headless:

    blender -b --factory-startup --python blender/REPAIR.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'REPAIR.glb')
BLEND = os.path.join(HERE, 'REPAIR.blend')

TRACK_X = 0.235
TRACK_WIDTH = 0.12
TRACK = (-0.4, 0.4)
WHEEL = 0.048
WHEELS_Y = (-0.32, -0.19, -0.065, 0.065, 0.19, 0.32)
WALK_FRAMES = 22
WALK_SPEED = 2 * math.pi * WHEEL / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 30
DECK = 0.27
BASE = Vector((0, 0.17, DECK + 0.03))     # the turntable's top: the crane's pivot
ELBOW = Vector((0, 0.3, 0.6))
HEAD = Vector((0, -0.2, 0.5))             # the upper boom's end: the head's pivot
SCALE = 1.0

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def hull(m):
    parts = [
        kit.hexahedron('Hull', m['armour'], (
            (-0.3, -0.38, 0.1), (0.3, -0.38, 0.1), (0.3, 0.42, 0.1), (-0.3, 0.42, 0.1),
            (-0.28, -0.24, DECK), (0.28, -0.24, DECK), (0.28, 0.41, DECK), (-0.28, 0.41, DECK)), bevel=0.014),
        kit.hexahedron('Belly', m['armour_dark'], (
            (-0.17, -0.42, 0.06), (0.17, -0.42, 0.06), (0.17, 0.42, 0.06), (-0.17, 0.42, 0.06),
            (-0.17, -0.38, 0.12), (0.17, -0.38, 0.12), (0.17, 0.42, 0.12), (-0.17, 0.42, 0.12)), bevel=0.01),
        # the cab on the left of the front, a slit window in its face
        kit.hexahedron('Cab', m['armour_dark'], (
            (-0.27, -0.24, DECK - 0.01), (-0.05, -0.24, DECK - 0.01), (-0.05, -0.05, DECK - 0.01), (-0.27, -0.05, DECK - 0.01),
            (-0.25, -0.18, DECK + 0.09), (-0.07, -0.18, DECK + 0.09), (-0.07, -0.06, DECK + 0.09), (-0.25, -0.06, DECK + 0.09)), bevel=0.012),
        kit.hexahedron('CabWindow', m['glass'], (
            (-0.235, -0.225, DECK + 0.03), (-0.085, -0.225, DECK + 0.03), (-0.085, -0.212, DECK + 0.03), (-0.235, -0.212, DECK + 0.03),
            (-0.232, -0.198, DECK + 0.07), (-0.088, -0.198, DECK + 0.07), (-0.088, -0.186, DECK + 0.07), (-0.232, -0.186, DECK + 0.07)), bevel=0.002),
        box('CabRoof', m['remap'], (0.15, 0.09, 0.01), (-0.16, -0.12, DECK + 0.093), bevel=0.003),
        # lockers and a parts rack on the right of the deck
        box('LockerFront', m['armour_dark'], (0.16, 0.14, 0.08), (0.17, -0.13, DECK + 0.04), bevel=0.008),
        *[box(f'LockerLid{k}', m['steel'], (0.065, 0.12, 0.008), (0.13 + 0.08 * k, -0.13, DECK + 0.083), bevel=0.002) for k in range(2)],
        box('Rack', m['steel'], (0.12, 0.16, 0.01), (0.19, 0.31, DECK + 0.005), bevel=0.002),
        *[cylinder(f'Drum{k}', m['remap'] if k == 1 else m['armour_dark'], 0.026, 0.06, (0.16 + (k % 2) * 0.06, 0.27 + (k // 2) * 0.07, DECK + 0.04),
                   segments=12) for k in range(4)],
        *[beam(f'RackPost{k}', m['steel'], (0.13 + (k % 2) * 0.12, 0.23 + (k // 2) * 0.16, DECK), (0.13 + (k % 2) * 0.12, 0.23 + (k // 2) * 0.16, DECK + 0.07),
               0.01) for k in range(4)],
        # the spare track links and the hatch on the left of the deck
        box('Hatch', m['armour_dark'], (0.1, 0.1, 0.014), (-0.18, 0.3, DECK + 0.006), bevel=0.004),
        *detail.track_links('SpareLinks', m['steel'], -0.18, 0.1, 0.05, 0.2, DECK + 0.006, 6),
        box('BackPlate', m['armour_dark'], (0.5, 0.012, 0.13), (0, 0.426, 0.18), bevel=0.003),
        *[cylinder(f'Exhaust{s}', m['steel_light'], 0.016, 0.1, (s * 0.24, 0.39, DECK + 0.05), segments=10) for s in (-1, 1)],
        beam('Antenna', m['steel'], (-0.26, 0.38, DECK), (-0.28, 0.42, 0.68), 0.006),
        cylinder('BeaconBase', m['steel'], 0.02, 0.02, (-0.2, -0.02, DECK + 0.01), segments=10, bevel=0),
    ]
    for s in (-1, 1):
        parts += [
            # red bands over the fenders and down the front corners
            kit.hexahedron(f'Band{s}', m['remap'], (
                (s * 0.28, -0.24, DECK - 0.002), (s * 0.302, -0.24, DECK - 0.002), (s * 0.302, 0.41, DECK - 0.002), (s * 0.28, 0.41, DECK - 0.002),
                (s * 0.28, -0.24, DECK + 0.012), (s * 0.302, -0.24, DECK + 0.012), (s * 0.302, 0.41, DECK + 0.012), (s * 0.28, 0.41, DECK + 0.012)),
                bevel=0.003),
            box(f'SideBand{s}', m['remap'], (0.008, 0.5, 0.03), (s * 0.302, 0.08, 0.2), bevel=0.002),
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.2, -0.33, 0.2), (0, -1, 0.5), 0.014),
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.2, 0.434, 0.21), (0, 1, 0), 0.01),
            *[box(f'SkirtBolt{s}{k}', m['steel'], (0.008, 0.014, 0.014), (s * 0.305, -0.2 + k * 0.1, 0.14), bevel=0.002) for k in range(6)],
        ]
    return kit.merge('Hull', parts)


def beacon(m, body):
    """The amber beacon by the cab; its light (a bar) turns round in Idle."""
    at = Vector((-0.2, -0.02, DECK + 0.02))
    kit.parent(kit.merge('BeaconGlass', [cylinder('BeaconDome', m['lamp_amber'], 0.016, 0.03, at + Vector((0, 0, 0.015)), segments=12, bevel=0)], at), body)
    light = kit.parent(kit.merge('BeaconLight', [box('BeaconBar', m['glow_amber'], (0.075, 0.012, 0.02), at + Vector((0, 0, 0.018)), bevel=0)], at), body)
    kit.keys(light, 'rotation_euler', {0: Vector((0, 0, 0)), kit.IDLE_END: Vector((0, 0, 4 * math.pi))}, 'LINEAR')
    kit.to_track(light, 'Idle')
    light.rotation_euler = (0, 0, 0)
    return light


def crane(m, body):
    """The turntable and the Z-folded crane; returns (joints, flash)."""
    turret = kit.parent(kit.empty('Turret', BASE), body)
    kit.parent(kit.merge('Turntable', [
        cylinder('Ring', m['armour_dark'], 0.085, 0.03, BASE - Vector((0, 0, 0.015)), segments=20),
        box('Yoke', m['armour'], (0.11, 0.1, 0.05), BASE + Vector((0, 0, 0.02)), bevel=0.008),
        *[box(f'Cheek{s}', m['remap'], (0.012, 0.08, 0.06), BASE + Vector((s * 0.058, 0, 0.03)), bevel=0.003) for s in (-1, 1)],
    ], BASE), turret)
    cannon = kit.parent(kit.empty('Cannon', BASE), turret)
    pivot = BASE + Vector((0, 0, 0.035))
    lower = kit.parent(walker.joint('ArmLower', None, pivot), cannon)
    kit.parent(kit.merge('LowerBoom', [
        cylinder('LowerPin', m['steel'], 0.03, 0.12, pivot, rotation=(0, math.pi / 2, 0), segments=14),
        *[beam(f'LowerRail{s}', m['armour_dark'], pivot + Vector((s * 0.03, 0, 0)), ELBOW + Vector((s * 0.03, 0, 0)), 0.026, 0.05) for s in (-1, 1)],
        beam('LowerStripe', m['remap'], pivot.lerp(ELBOW, 0.25) + Vector((0, 0.018, 0)), pivot.lerp(ELBOW, 0.8) + Vector((0, 0.018, 0)), 0.05, 0.012),
        *detail.hose('LowerHose', m['dark'], pivot + Vector((0, 0.04, 0.02)), pivot.lerp(ELBOW, 0.5) + Vector((0, 0.07, 0)), ELBOW + Vector((0, 0.03, -0.03)), 0.008),
        # the ram that lifts the boom
        beam('Ram', m['steel_light'], pivot + Vector((0, -0.05, 0.0)), pivot.lerp(ELBOW, 0.55) + Vector((0, -0.025, 0)), 0.018),
    ], pivot), lower)
    upper = kit.parent(walker.joint('ArmUpper', None, ELBOW), lower)
    kit.parent(kit.merge('UpperBoom', [
        cylinder('ElbowPin', m['steel'], 0.03, 0.1, ELBOW, rotation=(0, math.pi / 2, 0), segments=14),
        beam('UpperBeam', m['armour'], ELBOW, HEAD, 0.04, 0.045),
        beam('UpperStripe', m['remap'], ELBOW.lerp(HEAD, 0.15) + Vector((0, 0, 0.024)), ELBOW.lerp(HEAD, 0.85) + Vector((0, 0, 0.024)), 0.03, 0.006),
        *[beam(f'Truss{k}', m['steel'], ELBOW.lerp(HEAD, 0.1 + 0.2 * k) + Vector((0, 0, -0.02)),
               ELBOW.lerp(HEAD, 0.2 + 0.2 * k) + Vector((0, 0, -0.05)), 0.01) for k in range(4)],
        beam('UpperChord', m['steel'], ELBOW.lerp(HEAD, 0.1) + Vector((0, 0, -0.05)), ELBOW.lerp(HEAD, 0.95) + Vector((0, 0, -0.05)), 0.012),
    ], ELBOW), upper)
    head = kit.parent(walker.joint('ArmHead', None, HEAD), upper)
    tip = HEAD + Vector((0, -0.02, -0.11))
    kit.parent(kit.merge('Head', [
        cylinder('HeadPin', m['steel'], 0.026, 0.07, HEAD, rotation=(0, math.pi / 2, 0), segments=12),
        box('HeadBody', m['armour_dark'], (0.06, 0.06, 0.07), HEAD + Vector((0, 0, -0.045)), bevel=0.008),
        cylinder('Torch', m['steel_light'], 0.01, 0.05, HEAD + Vector((0, -0.01, -0.095)), segments=10),
        cylinder('TorchTip', m['lamp_amber'], 0.006, 0.012, tip + Vector((0, 0, 0.006)), segments=8, bevel=0),
        *[beam(f'Claw{s}', m['steel'], HEAD + Vector((s * 0.03, 0, -0.07)), HEAD + Vector((s * 0.04, -0.03, -0.12)), 0.01) for s in (-1, 1)],
    ], HEAD), head)
    flash = kit.parent(nod.flash(m, 'Flash', tip + Vector((0, 0, -0.01)), 0.03, facing=(0, 0, -1)), head)
    return (lower, upper, head), flash


def work(joints, flash):
    """Fire: the crane swings forward and down, the head welds, the crane folds back."""
    lower, upper, head = joints
    x = lambda a: Vector((a, 0, 0))  # noqa: E731
    poses = {0: (0, 0, 0), 8: (0.45, -0.15, -0.5), 22: (0.45, -0.15, -0.5), FIRE_FRAMES: (0, 0, 0)}
    for k, obj in enumerate(joints):
        kit.keys(obj, 'rotation_euler', {f: x(p[k]) for f, p in poses.items()})
        kit.to_track(obj, 'Fire')
        obj.rotation_euler = (0, 0, 0)
    hidden, on, big = Vector((kit.HIDDEN,) * 3), Vector((1, 1, 1)), Vector((1.4, 1.4, 1.4))
    sparks = {0: hidden}
    for f in range(9, 22):
        sparks[f] = (big if f % 3 == 0 else on) if f % 4 != 2 else hidden
    sparks[22] = hidden
    sparks[FIRE_FRAMES] = hidden
    kit.keys(flash, 'scale', sparks, 'CONSTANT')
    kit.to_track(flash, 'Fire')
    flash.scale = hidden


def build():
    root, body = nod.start('NodRepairVehicle', 'RepairVehicle', WALK_SPEED)
    m = nod.materials()
    kit.parent(hull(m), body)
    beacon(m, body)
    joints, flash = crane(m, body)
    wheels = []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], 0.12, 20), body)
        for k, y in enumerate(WHEELS_Y):
            wheels.append(kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (s * (TRACK_X + TRACK_WIDTH / 2 + 0.004), y, WHEEL + 0.006), WHEEL, 0.018), body))
    nod.camouflage(kit.collection().objects)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003)
    work(joints, flash)
    walker.hide([flash], kit.IDLE_END, 'Idle')
    walker.hide([flash], WALK_FRAMES, 'Walk')
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Fire': [12]}, scale=1.5, target=(0, -0.02, 0.3))
