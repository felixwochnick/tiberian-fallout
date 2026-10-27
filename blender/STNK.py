"""
Tiberian Fallout – Nod stealth tank (STNK), after Tiberian Sun.

A low, flat, fast tank: a narrow dark hull between the tracks, its nose a long
wedge, a flat sensor dome on its back; broad dark fenders over the tracks with a red
(house colour) stripe along each. On a pylon over each fender a box-shaped rocket pod
with four tubes, the missiles' cyan seeker heads glowing in their mouths; at the back
two round engine nacelles at the corners with cyan exhaust rings, like the original.
The game fades it out while it is cloaked.

Nodes the game uses: "Turret" (the pods' mount, not animated), "Cannon" (the pods,
tipped towards the target), "FlashL"/"FlashR" (the pods' muzzle flashes; the game
fires from them in turn). Clips (see nodvehicle.py):
    Idle    loop, 2 s: the engine runs, the hull shivers
    Walk    loop: driving, the wheels turn; walkSpeed on the root
    Fire    once, 0.6 s: the left pod fires, then the right one; each kicks back

Run headless:

    blender -b --factory-startup --python blender/STNK.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'STNK.glb')
BLEND = os.path.join(HERE, 'STNK.blend')

TRACK_X = 0.235
TRACK_WIDTH = 0.11
TRACK = (-0.38, 0.36)
WHEEL = 0.045
WHEELS_Y = (-0.3, -0.18, -0.06, 0.06, 0.18, 0.29)
WALK_FRAMES = 20
WALK_SPEED = 2 * math.pi * WHEEL / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 18
MOUNT = Vector((0, -0.02, 0.31))   # the pods' pivot (Turret, Cannon)
POD_X = 0.215
POD = (0.11, 0.3, 0.1)             # a pod's size (x, y, z), its middle at the pivot's height
SCALE = 1.0

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def hull(m):
    """The hull, fenders, engine nacelles and fittings."""
    parts = [
        # the hull: a long wedge nose rising to a flat back deck
        kit.hexahedron('Hull', m['armour'], (
            (-0.16, -0.44, 0.07), (0.16, -0.44, 0.07), (0.17, 0.4, 0.07), (-0.17, 0.4, 0.07),
            (-0.12, -0.2, 0.25), (0.12, -0.2, 0.25), (0.14, 0.38, 0.25), (-0.14, 0.38, 0.25)), bevel=0.014),
        kit.hexahedron('Nose', m['armour_dark'], (
            (-0.15, -0.47, 0.06), (0.15, -0.47, 0.06), (0.16, -0.42, 0.06), (-0.16, -0.42, 0.06),
            (-0.13, -0.45, 0.11), (0.13, -0.45, 0.11), (0.15, -0.4, 0.12), (-0.15, -0.4, 0.12)), bevel=0.008),
        # the sensor dome on the back deck and the dark canopy slit in front of it
        cylinder('DomeBase', m['armour_dark'], 0.085, 0.03, (0, 0.14, 0.262), segments=20),
        cylinder('Dome', m['armour'], 0.075, 0.035, (0, 0.14, 0.29), segments=20, radius2=0.045),
        kit.hexahedron('Canopy', m['glass'], (
            (-0.07, -0.19, 0.245), (0.07, -0.19, 0.245), (0.075, -0.07, 0.25), (-0.075, -0.07, 0.25),
            (-0.055, -0.17, 0.265), (0.055, -0.17, 0.265), (0.06, -0.08, 0.272), (-0.06, -0.08, 0.272)), bevel=0.004),
        *detail.grille('DeckVent', m['steel'], m['dark'], (0, 0.31, 0.252), 0.14, 0.08, 'Z', 5, 0.006),
        box('BackPlate', m['armour_dark'], (0.26, 0.012, 0.14), (0, 0.405, 0.16), bevel=0.004),
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (0.08, 0.413, 0.2), (0, 1, 0), 0.01),
    ]
    for s in (-1, 1):
        x0, x1 = s * 0.165, s * 0.305
        parts += [
            # the fender over the track, sloped down in front
            kit.hexahedron(f'Fender{s}', m['armour_dark'], (
                (x0, -0.42, 0.12), (x1, -0.42, 0.12), (x1, 0.38, 0.13), (x0, 0.38, 0.13),
                (x0, -0.32, 0.19), (x1, -0.32, 0.18), (x1, 0.38, 0.18), (x0, 0.38, 0.19)), bevel=0.01),
            # its red stripe
            kit.hexahedron(f'Stripe{s}', m['remap'], (
                (s * 0.2, -0.36, 0.17), (s * 0.255, -0.36, 0.165), (s * 0.255, 0.3, 0.186), (s * 0.2, 0.3, 0.191),
                (s * 0.2, -0.32, 0.193), (s * 0.255, -0.32, 0.187), (s * 0.255, 0.3, 0.192), (s * 0.2, 0.3, 0.197)), bevel=0.002),
            # a red line down the hull's flank
            box(f'HullLine{s}', m['remap'], (0.012, 0.42, 0.025), (s * 0.155, 0.08, 0.215), bevel=0.003),
            # the pylon that carries the pod
            kit.hexahedron(f'Pylon{s}', m['armour'], (
                (s * 0.17, -0.1, 0.18), (s * 0.27, -0.1, 0.18), (s * 0.27, 0.08, 0.18), (s * 0.17, 0.08, 0.18),
                (s * 0.18, -0.07, 0.25), (s * 0.25, -0.07, 0.25), (s * 0.25, 0.05, 0.25), (s * 0.18, 0.05, 0.25)), bevel=0.006),
            # the engine nacelle at the back corner, a cyan exhaust ring in its tail
            cylinder(f'Nacelle{s}', m['armour'], 0.06, 0.2, (s * 0.24, 0.3, 0.2), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0.01),
            cylinder(f'NacelleCap{s}', m['remap'], 0.062, 0.04, (s * 0.24, 0.22, 0.2), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0.004),
            cylinder(f'Exhaust{s}', m['signal'], 0.045, 0.012, (s * 0.24, 0.402, 0.2), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0),
            cylinder(f'ExhaustCone{s}', m['dark'], 0.03, 0.016, (s * 0.24, 0.408, 0.2), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0),
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.1, -0.44, 0.105), (0, -1, 0.3), 0.012),
            *[box(f'FenderBolt{s}{k}', m['steel'], (0.008, 0.012, 0.012), (s * 0.308, -0.25 + k * 0.1, 0.155), bevel=0.002) for k in range(6)],
        ]
    return kit.merge('Hull', parts)


def pod(m, s, cannon):
    """One rocket pod on the Cannon node; returns (pod, flash)."""
    centre = Vector((s * POD_X, MOUNT.y, MOUNT.z))
    w, l, h = POD
    front = centre.y - l / 2
    parts = [
        kit.hexahedron(f'PodBox{s}', m['armour_dark'], (
            (centre.x - w / 2, front, centre.z - h / 2), (centre.x + w / 2, front, centre.z - h / 2),
            (centre.x + w / 2, front + l, centre.z - h / 2), (centre.x - w / 2, front + l, centre.z - h / 2),
            (centre.x - w / 2, front, centre.z + h / 2), (centre.x + w / 2, front, centre.z + h / 2),
            (centre.x + w / 2, front + l - 0.04, centre.z + h / 2), (centre.x - w / 2, front + l - 0.04, centre.z + h / 2)), bevel=0.012),
        # red band round the middle, a red cap on top
        box(f'PodBand{s}', m['remap'], (w + 0.006, 0.04, h + 0.006), centre + Vector((0, 0.03, 0)), bevel=0.004),
        box(f'PodTop{s}', m['remap'], (w * 0.6, l * 0.4, 0.008), centre + Vector((0, -0.07, h / 2 + 0.003)), bevel=0.002),
        box(f'PodFace{s}', m['steel'], (w - 0.012, 0.012, h - 0.012), (centre.x, front - 0.004, centre.z), bevel=0.003),
        box(f'PodHinge{s}', m['steel'], (0.05, 0.08, 0.03), centre + Vector((-s * 0.03, 0.02, -h / 2 - 0.012)), bevel=0.004),
    ]
    for i in (-1, 1):
        for j in (-1, 1):
            p = Vector((centre.x + i * w * 0.24, front - 0.008, centre.z + j * h * 0.24))
            parts += [cylinder(f'Tube{s}{i}{j}', m['dark'], 0.019, 0.012, p, rotation=(math.pi / 2, 0, 0), segments=12, bevel=0),
                      cylinder(f'Seeker{s}{i}{j}', m['signal'], 0.012, 0.01, p + Vector((0, 0.002, 0)), rotation=(math.pi / 2, 0, 0),
                               segments=10, bevel=0, radius2=0.004)]
    body = kit.parent(kit.merge(f'Pod{"L" if s < 0 else "R"}', parts, centre), cannon)
    flash = kit.parent(nod.flash(m, f'Flash{"L" if s < 0 else "R"}', (centre.x, front - 0.04, centre.z), 0.05), cannon)
    return body, flash


def build():
    root, body = nod.start('NodStealthTank', 'StealthTank', WALK_SPEED)
    m = nod.materials()
    kit.parent(hull(m), body)
    turret = kit.parent(kit.empty('Turret', MOUNT), body)
    cannon = kit.parent(kit.empty('Cannon', MOUNT), turret)
    pods = [pod(m, s, cannon) for s in (-1, 1)]
    wheels = []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], 0.11, 18), body)
        for k, y in enumerate(WHEELS_Y):
            wheels.append(kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (s * (TRACK_X + TRACK_WIDTH / 2 + 0.004), y, WHEEL + 0.006), WHEEL, 0.018), body))
    nod.camouflage(kit.collection().objects)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003)
    # Fire: the left pod, then the right one (the game's two shots of a burst)
    hidden = Vector((kit.HIDDEN,) * 3)
    for k, (obj, flash) in enumerate(pods):
        start = k * 6
        kit.keys(flash, 'scale', {0: hidden, start: Vector((1, 1, 1)), start + 2: Vector((1.3, 1.5, 1.3)), start + 4: hidden,
                                  FIRE_FRAMES: hidden}, 'CONSTANT')
        kit.to_track(flash, 'Fire')
        rest = obj.location.copy()
        kick = rest + Vector((0, 0.035, 0))
        kit.keys(obj, 'location', {0: rest, start: rest, start + 2: kick, start + 4: kick, start + 11: rest, FIRE_FRAMES: rest})
        kit.to_track(obj, 'Fire')
        obj.location = rest
        flash.scale = hidden
    flashes = [f for _, f in pods]
    walker.hide(flashes, kit.IDLE_END, 'Idle')
    walker.hide(flashes, WALK_FRAMES, 'Walk')
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Fire': [1, 7]}, scale=1.3, target=(0, -0.02, 0.18))
