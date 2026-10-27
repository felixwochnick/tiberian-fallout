"""
Tiberian Fallout – Nod Weed Eater (WEED), after Tiberian Sun.

A heavy six-wheeled harvester for Tiberium veins: in front, low over the ground, the
wide collector – an armoured housing with red and white (house colour and hazard)
plates on top, its dark mouth with the toothed cutting drum; behind it on the left the
small armoured cab with its slit windscreen and a beacon. Most of it is the hopper: a
big rounded dark tank on the chassis, a red band round it, ribs and an inspection
hatch on top, at its back the dump door. Six huge off-road tyres.

Nodes: "Drum" (the cutting drum), "Hopper" (tips up to unload, pivot at its back
bottom), "DumpDoor" (opens at the back). Clips (see nodvehicle.py for Idle and Walk):
    Idle     loop, 2 s: the engine runs, the beacon blinks
    Walk     loop: driving, the wheels turn; walkSpeed on the root
    Harvest  loop, 1 s: the drum turns, the body shakes
    Unload   once, 3 s: docked with its back at the waste facility, the dump door
             swings open, the hopper tips up and empties, then settles back

Run headless:

    blender -b --factory-startup --python blender/WEED.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'WEED.glb')
BLEND = os.path.join(HERE, 'WEED.blend')

WHEEL_RADIUS = 0.095
WHEEL_WIDTH = 0.085
WHEEL_X = 0.25
AXLES = (-0.3, 0.12, 0.36)
WALK_FRAMES = 30
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
HARVEST_FRAMES = 30
UNLOAD_FRAMES = 90
FRAME_TOP = 0.2                       # the chassis' top: the hopper sits on it
HOPPER = (-0.17, 0.5)                 # the hopper's length (y)
HOPPER_Z = 0.42                       # its axis
HOPPER_R = (0.25, 0.2)                # its half width and half height
PIVOT = Vector((0, HOPPER[1], FRAME_TOP))   # the hopper tips about its back bottom edge
DOOR = Vector((0, HOPPER[1] + 0.012, HOPPER_Z + 0.15))   # the dump door's hinge
DRUM = Vector((0, -0.54, 0.1))
TIP = math.radians(-28)               # the hopper tipped up (front up)
SCALE = 1.0

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def chassis(m):
    parts = [
        box('Frame', m['armour_dark'], (0.3, 0.98, 0.08), (0, -0.02, FRAME_TOP - 0.04), bevel=0.01),
        box('Bumper', m['steel'], (0.36, 0.03, 0.04), (0, 0.5, 0.15), bevel=0.006),
        *detail.lamp('TailLightL', m['dark'], m['lamp_red'], (-0.14, 0.518, 0.15), (0, 1, 0), 0.01),
        *detail.lamp('TailLightR', m['dark'], m['lamp_red'], (0.14, 0.518, 0.15), (0, 1, 0), 0.01),
    ]
    for s in (-1, 1):
        for y in AXLES:
            parts.append(cylinder(f'Axle{s}{y}', m['steel'], 0.022, 0.1, (s * 0.17, y, WHEEL_RADIUS), rotation=(0, math.pi / 2, 0), segments=10))
        # mudguards over the wheel pairs
        parts += [
            kit.hexahedron(f'Guard{s}', m['armour'], (
                (s * 0.2, 0.0, 0.2), (s * 0.3, 0.0, 0.2), (s * 0.3, 0.48, 0.2), (s * 0.2, 0.48, 0.2),
                (s * 0.2, 0.02, 0.225), (s * 0.3, 0.02, 0.225), (s * 0.3, 0.46, 0.225), (s * 0.2, 0.46, 0.225)), bevel=0.006),
            kit.hexahedron(f'FrontGuard{s}', m['armour'], (
                (s * 0.2, -0.42, 0.2), (s * 0.3, -0.42, 0.2), (s * 0.3, -0.18, 0.2), (s * 0.2, -0.18, 0.2),
                (s * 0.2, -0.4, 0.225), (s * 0.3, -0.4, 0.225), (s * 0.3, -0.2, 0.225), (s * 0.2, -0.2, 0.225)), bevel=0.006),
        ]
    return kit.merge('Chassis', parts)


def collector(m):
    """The collector housing in front (fixed) and the cab behind it."""
    parts = [
        kit.hexahedron('Collector', m['armour_dark'], (
            (-0.29, -0.62, 0.05), (0.29, -0.62, 0.05), (0.29, -0.42, 0.07), (-0.29, -0.42, 0.07),
            (-0.28, -0.58, 0.2), (0.28, -0.58, 0.2), (0.28, -0.42, 0.24), (-0.28, -0.42, 0.24)), bevel=0.012),
        # its dark mouth round the drum
        box('Mouth', m['dark'], (0.46, 0.03, 0.1), (0, -0.618, 0.11), bevel=0.006),
        *[box(f'Tine{k}', m['steel_light'], (0.014, 0.08, 0.012), (-0.21 + k * 0.06, -0.65, 0.04), bevel=0.002) for k in range(8)],
        box('TineBar', m['steel'], (0.5, 0.02, 0.02), (0, -0.62, 0.045), bevel=0.004),
        # red and white plates on top, as the original's
        *[kit.hexahedron(f'TopPlate{k}', m['remap'] if k % 2 == 0 else m['steel_light'], (
            (-0.27 + k * 0.108, -0.575, 0.205), (-0.17 + k * 0.108, -0.575, 0.205), (-0.17 + k * 0.108, -0.44, 0.245), (-0.27 + k * 0.108, -0.44, 0.245),
            (-0.27 + k * 0.108, -0.57, 0.215), (-0.17 + k * 0.108, -0.57, 0.215), (-0.17 + k * 0.108, -0.445, 0.253), (-0.27 + k * 0.108, -0.445, 0.253)),
            bevel=0.002) for k in range(5)],
        *[cylinder(f'DrumBearing{s}', m['steel'], 0.035, 0.03, DRUM + Vector((s * 0.28, 0, 0)), rotation=(0, math.pi / 2, 0), segments=12)
          for s in (-1, 1)],
        # the cab on the left
        kit.hexahedron('Cab', m['armour'], (
            (-0.27, -0.42, 0.2), (-0.06, -0.42, 0.2), (-0.06, -0.18, 0.2), (-0.27, -0.18, 0.2),
            (-0.26, -0.36, 0.42), (-0.07, -0.36, 0.42), (-0.07, -0.2, 0.43), (-0.26, -0.2, 0.43)), bevel=0.014),
        kit.hexahedron('Windscreen', m['glass'], (
            (-0.25, -0.405, 0.3), (-0.08, -0.405, 0.3), (-0.08, -0.395, 0.3), (-0.25, -0.395, 0.3),
            (-0.245, -0.37, 0.39), (-0.085, -0.37, 0.39), (-0.085, -0.36, 0.39), (-0.245, -0.36, 0.39)), bevel=0.002),
        box('CabRoof', m['remap'], (0.17, 0.12, 0.012), (-0.165, -0.28, 0.433), bevel=0.003),
        box('Grille', m['armour_dark'], (0.12, 0.1, 0.12), (0.06, -0.33, 0.27), bevel=0.01),
        *detail.grille('EngineGrille', m['steel'], m['dark'], (0.06, -0.382, 0.27), 0.09, 0.08, 'Y', 4, 0.006),
        cylinder('Stack', m['steel_light'], 0.016, 0.2, (0.1, -0.27, 0.4), segments=10),
        cylinder('StackTip', m['dark'], 0.018, 0.01, (0.1, -0.27, 0.5), segments=10, bevel=0),
        beam('Antenna', m['steel'], (-0.24, -0.22, 0.43), (-0.26, -0.2, 0.72), 0.006),
        cylinder('BeaconBase', m['steel'], 0.016, 0.02, (-0.12, -0.25, 0.44), segments=10, bevel=0),
        *detail.lamp('HeadlightL', m['dark'], m['lamp_white'], (-0.22, -0.42, 0.27), (0, -1, 0), 0.013),
        *detail.lamp('HeadlightR', m['dark'], m['lamp_white'], (0.22, -0.42, 0.27), (0, -1, 0), 0.013),
    ]
    return kit.merge('Collector', parts)


def drum(m):
    parts = [cylinder('DrumCore', m['steel'], 0.045, 0.5, DRUM, rotation=(0, math.pi / 2, 0), segments=16)]
    for k in range(8):
        a = 2 * math.pi * k / 8
        d = Vector((0, math.cos(a), math.sin(a)))
        for i in range(5):
            x = -0.2 + i * 0.1 + (0.05 if k % 2 else 0) - 0.025
            parts.append(beam(f'Tooth{k}_{i}', m['steel_light'], DRUM + Vector((x, 0, 0)) + d * 0.04, DRUM + Vector((x, 0, 0)) + d * 0.066, 0.016, 0.01))
    return kit.merge('Drum', parts, DRUM)


def hopper(m):
    """The rounded hopper: a superellipse section along y; its pivot at the back bottom."""
    y0, y1 = HOPPER
    rx, rz = HOPPER_R
    around, n = 40, 3.0

    def point(y, a, out=0.0):
        taper = 1 - 0.18 * ((y - y0) / (y1 - y0) - 0.3) ** 2   # a little fuller in front
        c, s = math.cos(a), math.sin(a)
        x = (rx * taper + out) * math.copysign(abs(s) ** (2 / n), s)
        z = HOPPER_Z + (rz * taper + out) * math.copysign(abs(c) ** (2 / n), c)
        return Vector((x, y, max(z, FRAME_TOP + 0.005)))

    ys = [y0 + (y1 - y0) * k / 16 for k in range(17)]
    band = (0.06, 0.12)

    def build(bm):
        rings = [[bm.verts.new(point(y, 2 * math.pi * i / around)) for i in range(around)] for y in ys]
        for k in range(len(rings) - 1):
            red = band[0] <= (ys[k] + ys[k + 1]) / 2 <= band[1] + 0.03
            for i in range(around):
                j = (i + 1) % around
                bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i])).material_index = 1 if red else 0
        # the ends: concentric rings to the middle (so the camouflage gets a fine grid)
        for ring, y, flip in ((rings[0], ys[0], True), (rings[-1], ys[-1], False)):
            centre = Vector((0, y, (HOPPER_Z + FRAME_TOP) / 2 + 0.05))
            outer = ring
            for t in (0.75, 0.5, 0.25):
                inner = [bm.verts.new(centre.lerp(v.co, t)) for v in ring]
                for i in range(around):
                    j = (i + 1) % around
                    quad = (outer[i], outer[j], inner[j], inner[i])
                    bm.faces.new(quad[::-1] if flip else quad)
                outer = inner
            middle = bm.verts.new(centre)
            for i in range(around):
                tri = (outer[i], outer[(i + 1) % around], middle)
                bm.faces.new(tri[::-1] if flip else tri)

    shell = kit.mesh_object('HopperShell', build)
    shell.data.materials.append(m['armour'])
    kit.finish(shell, m['remap'], 0)
    top = HOPPER_Z + rz
    parts = [
        shell,
        *[beam(f'HopperRib{k}', m['armour_dark'], point(y0 + 0.2 + k * 0.15, -math.radians(80), 0.006),
               point(y0 + 0.2 + k * 0.15, math.radians(80), 0.006), 0.02, 0.012) for k in range(3)],
        cylinder('InspectionHatch', m['armour_dark'], 0.06, 0.02, (0.08, 0.08, top - 0.005), segments=18),
        box('HatchHandle', m['steel'], (0.05, 0.01, 0.01), (0.08, 0.08, top + 0.01), bevel=0.002),
        *detail.grille('HopperVent', m['steel'], m['dark'], (-0.1, 0.3, top - 0.004), 0.1, 0.12, 'Z', 5, 0.006),
        box('Hinge', m['steel'], (0.2, 0.03, 0.03), (0, y1, FRAME_TOP + 0.015), bevel=0.004),
        *[box(f'Ram{s}', m['steel_light'], (0.025, 0.04, 0.12), (s * 0.12, y0 + 0.08, FRAME_TOP + 0.03), bevel=0.004) for s in (-1, 1)],
    ]
    return kit.merge('Hopper', parts, PIVOT)


def door(m):
    """The dump door at the hopper's back, hinged on top."""
    w, h = 0.3, 0.26
    parts = [
        box('DoorPlate', m['armour_dark'], (w, 0.022, h), DOOR + Vector((0, 0.008, -h / 2)), bevel=0.006),
        box('DoorStripe', m['remap'], (w * 0.85, 0.008, 0.03), DOOR + Vector((0, 0.022, -h * 0.35)), bevel=0.002),
        *[box(f'DoorBolt{k}', m['steel'], (0.016, 0.01, 0.016), DOOR + Vector((-0.11 + k * 0.073, 0.022, -h * 0.75)), bevel=0.002) for k in range(4)],
        cylinder('DoorHinge', m['steel'], 0.014, w, DOOR, rotation=(0, math.pi / 2, 0), segments=10),
    ]
    return kit.merge('DumpDoor', parts, DOOR)


def build():
    root, body = nod.start('NodWeedEater', 'WeedEater', WALK_SPEED)
    m = nod.materials()
    kit.parent(chassis(m), body)
    kit.parent(collector(m), body)
    roller = kit.parent(drum(m), body)
    tank = kit.parent(hopper(m), body)
    hatch = kit.parent(door(m), tank)
    lamp = Vector((-0.12, -0.25, 0.465))
    beacon = kit.parent(kit.merge('Beacon', [sphere('BeaconBulb', m['lamp_amber'], 0.018, lamp, 10),
                                             sphere('BeaconHalo', m['glow_amber'], 0.04, lamp, 10)], lamp), body)
    wheels = [kit.parent(nod.wheel(m, f'Wheel{s}{k}', (s * WHEEL_X, y, WHEEL_RADIUS), WHEEL_RADIUS, WHEEL_WIDTH, lugs=16, hub=0.5), root)
              for s in (-1, 1) for k, y in enumerate(AXLES)]
    nod.camouflage(kit.collection().objects)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.004)
    kit.blink(beacon, kit.flashes((0, 10), (30, 10)))
    kit.to_track(beacon, 'Idle')
    keys = kit.keys
    still = Vector((0, 0, 0))
    # Harvest: the drum turns (its teeth bite upwards from the front), the body shakes
    keys(roller, 'rotation_euler', {0: still, HARVEST_FRAMES: Vector((-4 * math.pi, 0, 0))}, 'LINEAR')
    kit.to_track(roller, 'Harvest')
    keys(body, 'location', {f: Vector((0.002 * math.sin(f * 2.1), 0, 0.003 * math.sin(f * 3.3))) for f in range(HARVEST_FRAMES)} |
         {HARVEST_FRAMES: still}, 'LINEAR')
    kit.to_track(body, 'Harvest')
    # Unload: the door swings open, the hopper tips up and empties, both settle back
    tipped = Vector((TIP, 0, 0))
    keys(tank, 'rotation_euler', {0: still, 12: still, 34: tipped, 64: tipped, 84: still, UNLOAD_FRAMES: still})
    kit.to_track(tank, 'Unload')
    keys(hatch, 'rotation_euler', {0: still, 14: Vector((math.radians(70), 0, 0)), 68: Vector((math.radians(70), 0, 0)), 82: still,
                                   UNLOAD_FRAMES: still})
    kit.to_track(hatch, 'Unload')
    for obj in (tank, hatch, roller, body):
        obj.rotation_euler = still
    body.location = still
    for w in wheels:
        w.rotation_euler = still
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Harvest': [7], 'Unload': [45]}, scale=1.8, target=(0, -0.04, 0.28))
