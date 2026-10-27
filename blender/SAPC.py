"""
Tiberian Fallout – Nod subterranean APC (SAPC), after Tiberian Sun.

A long, low tracked carrier that digs through the ground, rounded all over like a
loaf: grey, wider than high, its back highest behind the middle; towards the front it
narrows smoothly into a round red collar that carries the drill, a round cone with
spiral flutes, as big as the collar and fixed to it. A red cap rounds off the tail.
The hull covers the tracks but for their bottom run; dark slots along its lower
sides, a hatch, lights and an antenna.

It travels under the ground: it digs straight down where it stands, goes across the
map below it and digs its way up again, nose first, where it comes out.

Clips (see nodvehicle.py for Idle and Walk):
    Burrow       once, 2 s: it tips over onto its drill and digs straight down, out of
                 sight
    Underground  loop: down there (hidden in the game while it travels)
    Surface      once, 2 s: up nose first out of the ground, then down onto its tracks

Run headless:

    Blender -b --factory-startup --python blender/SAPC.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'SAPC.glb')
BLEND = os.path.join(HERE, 'SAPC.blend')

BELLY = 0.085                         # the hull's flat underside: below it the tracks show
# the hull's shape along its length: (y, half width, half height, height of the middle,
# roundness: 2 a circle or ellipse, higher squarer); smoothly blended in between
STATIONS = (
    (-0.33, 0.125, 0.125, 0.18, 2.0),  # the collar: round, as the drill
    (-0.28, 0.15, 0.13, 0.185, 2.3),
    (-0.17, 0.235, 0.125, 0.19, 3.2),
    (0.0, 0.25, 0.13, 0.19, 3.6),
    (0.28, 0.25, 0.145, 0.19, 3.6),
    (0.4, 0.24, 0.135, 0.19, 3.3),
    (0.46, 0.2, 0.1, 0.19, 2.8),
    (0.485, 0.11, 0.05, 0.19, 2.4),
)
RED = (-0.21, 0.36)                   # red in front of the first, behind the second (y)
DRILL_LENGTH = 0.26
WHEEL_RADIUS = 0.045
TRACK_X = 0.17
TRACK_WIDTH = 0.1
TRACK = (-0.26, 0.42)
WHEELS_Y = (-0.2, -0.08, 0.04, 0.16, 0.28, 0.37)
WALK_FRAMES = 24
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
BURROW_FRAMES = 60
DOWN = math.radians(88)               # how steeply it digs (nose down; up: the other way)
DEPTH = 0.75                          # how deep it goes: all of it under the ground
SCALE = 1.15

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def section(y):
    """The hull's cross-section at y, blended between the stations."""
    if y <= STATIONS[0][0]:
        return STATIONS[0][1:]
    for a, b in zip(STATIONS, STATIONS[1:]):
        if y <= b[0]:
            t = (y - a[0]) / (b[0] - a[0])
            t = t * t * (3 - 2 * t)
            return tuple(p + (q - p) * t for p, q in zip(a[1:], b[1:]))
    return STATIONS[-1][1:]


def surface(y, u, out=0.0):
    """A point on the hull at y, `u` the angle round it (0 on top, positive to the right)."""
    width, height, middle, n = section(y)
    c, s = math.cos(u), math.sin(u)
    x = (width + out) * math.copysign(abs(s) ** (2 / n), s)
    z = middle + (height + out) * math.copysign(abs(c) ** (2 / n), c)
    return Vector((x, y, max(z, BELLY)))


def shell(m):
    """The hull's skin, grey with the red collar in front and the red tail."""
    around = 48
    ys = [STATIONS[0][0] + k * 0.015 for k in range(int((STATIONS[-1][0] - STATIONS[0][0]) / 0.015) + 1)] + [STATIONS[-1][0]]

    def build(bm):
        rings = [[bm.verts.new(surface(y, 2 * math.pi * i / around)) for i in range(around)] for y in ys]
        for k in range(len(rings) - 1):
            red = not RED[0] <= (ys[k] + ys[k + 1]) / 2 <= RED[1]
            for i in range(around):
                j = (i + 1) % around
                face = bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
                face.material_index = 1 if red else 0
        bm.faces.new(rings[0][::-1]).material_index = 1
        bm.faces.new(rings[-1]).material_index = 1

    obj = kit.mesh_object('Shell', build)
    obj.data.materials.append(m['hull'])
    kit.finish(obj, m['remap'], 0)
    return obj


def drill(m):
    """The drill: a round cone on the collar, as big as it, with three spiral flutes
    winding round it to the point. Fixed to the hull."""
    y0 = STATIONS[0][0]
    radius, _, middle, _ = STATIONS[0][1:]
    rings, around = 12, 32

    def point(a, t, out=1.0):
        r = radius * (1 - t ** 1.2) * out
        return Vector((r * math.sin(a), y0 - t * DRILL_LENGTH, middle + r * math.cos(a)))

    def build(bm):
        verts = [[bm.verts.new(point(2 * math.pi * i / around, k / rings)) for i in range(around)] for k in range(rings)]
        tip = bm.verts.new(point(0, 1))
        for k in range(rings - 1):
            for i in range(around):
                j = (i + 1) % around
                bm.faces.new((verts[k][i], verts[k][j], verts[k + 1][j], verts[k + 1][i]))
        for i in range(around):
            bm.faces.new((verts[-1][i], verts[-1][(i + 1) % around], tip))
        bm.faces.new(verts[0][::-1])

    parts = [kit.finish(kit.mesh_object('DrillCone', build), m['armour_dark'], 0)]
    steps = 24
    for k in range(3):
        points = [point(2 * math.pi * (k / 3 + (i / steps) * 1.5), (i / steps) * 0.95, 1.04) for i in range(steps + 1)]
        parts += [beam(f'Flute{k}_{i}', m['steel_light'], a, b, 0.024 * (1 - i / steps * 0.6), 0.02) for i, (a, b) in enumerate(zip(points, points[1:]))]
    return kit.merge('Drill', parts)


def hull(m):
    parts = [shell(m), drill(m)]
    top = lambda y: surface(y, 0).z  # noqa: E731
    parts += [
        # on top: a hatch, a vent, the antenna
        cylinder('Hatch', m['hull_dark'], 0.05, 0.03, (0.07, 0.16, top(0.16) - 0.008), segments=18),
        box('HatchHinge', m['steel'], (0.03, 0.02, 0.012), (0.07, 0.215, top(0.215) + 0.005), bevel=0.003),
        *detail.grille('Vent', m['steel'], m['dark'], (-0.08, 0.06, top(0.06) - 0.002), 0.08, 0.1, 'Y', 5, 0.008),
        beam('Antenna', m['steel'], (-0.13, 0.34, top(0.34) - 0.03), (-0.15, 0.4, 0.62), 0.006),
        *detail.lamp('Searchlight', m['dark'], m['lamp_white'], surface(-0.2, 0, 0.004), (0, -1, 0.4), 0.016),
    ]
    for s in (-1, 1):
        # dark slots along the lower sides
        for k in range(8):
            y = -0.14 + k * 0.06
            p = surface(y, s * math.radians(98), 0.002)
            parts.append(box(f'Slot{s}{k}', m['hull_dark'], (0.012, 0.024, 0.06), p, bevel=0.004, rotation=(0, -s * 0.5, 0)))
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], surface(-0.25, s * math.radians(50), 0.004), (s * 0.3, -1, 0.2), 0.014),
            # a pair of red lights on the flanks, as on the original's side
            *[part for k in range(2) for part in detail.lamp(f'SideLight{s}{k}', m['dark'], m['lamp_red'],
                                                             surface(-0.08 + k * 0.05, s * math.radians(72), 0.002), (s, 0, 0.3), 0.012)],
            cylinder(f'Exhaust{s}', m['steel'], 0.014, 0.05, surface(0.44, s * math.radians(105), -0.01) + Vector((0, 0.03, 0)),
                     rotation=(math.pi / 2, 0, 0), segments=8),
        ]
    return kit.merge('Hull', parts)


def build():
    root, body = nod.start('NodSubterraneanAPC', 'SubterraneanAPC', WALK_SPEED)
    m = nod.materials()
    # the hull in the camouflage of the armour (nodvehicle.camouflage)
    m['hull'] = m['armour']
    m['hull_dark'] = m['armour_dark']
    kit.parent(hull(m), body)
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], 0.1, 18), body)
    wheels = [kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (s * (TRACK_X + TRACK_WIDTH / 2 + 0.005), y, WHEEL_RADIUS + 0.004), WHEEL_RADIUS,
                                        0.02), body)
              for s in (-1, 1) for k, y in enumerate(WHEELS_Y)]
    nod.camouflage(kit.collection().objects)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003)
    keys = kit.keys
    still = Vector((0, 0, 0))
    nose_down, nose_up = Vector((DOWN, 0, 0)), Vector((-DOWN, 0, 0))
    below = Vector((0, 0, -DEPTH))
    # down: over onto the drill, then straight down
    keys(body, 'location', {0: still, 12: Vector((0, 0, -0.02)), 30: Vector((0, 0, -0.1)), BURROW_FRAMES: below})
    keys(body, 'rotation_euler', {0: still, 12: Vector((math.radians(30), 0, 0)), 30: nose_down, BURROW_FRAMES: nose_down})
    kit.to_track(body, 'Burrow')
    walker.hold(body, 'location', below, kit.IDLE_END, 'Underground')
    walker.hold(body, 'rotation_euler', nose_down, kit.IDLE_END, 'Underground')
    # up: nose first out of the ground, then down onto the tracks
    keys(body, 'location', {0: Vector((0, 0, -1.7 * DEPTH)), 30: Vector((0, 0, -0.05)), 48: still, BURROW_FRAMES: still})
    keys(body, 'rotation_euler', {0: nose_up, 30: nose_up, 48: Vector((math.radians(-20), 0, 0)), BURROW_FRAMES: still})
    kit.to_track(body, 'Surface')
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Burrow': [20, 40], 'Surface': [36]}, scale=1.7, target=(0, -0.02, 0.2))
