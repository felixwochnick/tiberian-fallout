"""
Tiberian Fallout – small detail parts shared by the vehicle and walker scripts
(HARV, SMECH, MMCH): rivets, panel seams, grilles, hoses, lamps, ladders, rails and
track links. Each returns a list of objects for kit.merge(); all positions are in the
model's space (Blender Z up, -Y the front).
"""
import math

from mathutils import Vector

import GAPILE as kit


def rivets(name, mat, start, end, count, radius=0.006, axis='Y'):
    """A row of round rivet heads from start to end; `axis` is where their faces look
    ('X', 'Y' or 'Z', the sign from the vector's own direction is not needed: the
    heads are short cylinders, visible from both sides)."""
    start, end = Vector(start), Vector(end)
    rotation = {'X': (0, math.pi / 2, 0), 'Y': (math.pi / 2, 0, 0), 'Z': (0, 0, 0)}[axis]
    return [kit.cylinder(f'{name}{k}', mat, radius, radius * 0.8, start.lerp(end, k / max(count - 1, 1)), rotation=rotation, segments=6, bevel=0)
            for k in range(count)]


def seam(name, mat, start, end, width=0.005, depth=0.004):
    """A panel line: a thin dark strip on a surface."""
    return [kit.beam(name, mat, Vector(start), Vector(end), width, depth)]


def grille(name, frame_mat, slat_mat, centre, width, height, normal='Y', slats=5, depth=0.012):
    """A framed vent with horizontal slats; `normal` is the axis it faces along."""
    centre = Vector(centre)
    if normal == 'Y':
        frame, size = (width + 0.012, depth, height + 0.012), (width, depth + 0.004, height / slats * 0.45)
    else:
        frame, size = (depth, width + 0.012, height + 0.012), (depth + 0.004, width, height / slats * 0.45)
    parts = [kit.box(f'{name}Frame', frame_mat, frame, centre, bevel=0.002)]
    for k in range(slats):
        z = -height / 2 + (k + 0.5) * height / slats
        parts.append(kit.box(f'{name}Slat{k}', slat_mat, size, centre + Vector((0, 0, z)), bevel=0))
    return parts


def hose(name, mat, start, control, end, radius=0.008, segments=8):
    """A flexible hose along a quadratic curve, as short cylinders."""
    start, control, end = Vector(start), Vector(control), Vector(end)
    points = [(1 - t) ** 2 * start + 2 * (1 - t) * t * control + t * t * end for t in (k / segments for k in range(segments + 1))]
    parts = []
    for k, (a, b) in enumerate(zip(points, points[1:])):
        part = kit.cylinder(f'{name}{k}', mat, radius, (b - a).length + radius, (a + b) / 2, segments=6, bevel=0)
        part.rotation_mode = 'QUATERNION'
        part.rotation_quaternion = (b - a).to_track_quat('Z', 'Y')
        parts.append(part)
    return parts


def lamp(name, housing_mat, lamp_mat, centre, facing, radius=0.016):
    """A small lamp in a housing, its glass facing along `facing` (a unit vector)."""
    centre, facing = Vector(centre), Vector(facing).normalized()
    housing = kit.cylinder(f'{name}Housing', housing_mat, radius * 1.3, radius * 1.2, centre, segments=10, bevel=0)
    glass = kit.cylinder(f'{name}Glass', lamp_mat, radius, radius * 0.4, centre + facing * radius * 0.7, segments=10, bevel=0)
    for part in (housing, glass):
        part.rotation_mode = 'QUATERNION'
        part.rotation_quaternion = facing.to_track_quat('Z', 'Y')
    return [housing, glass]


def ladder(name, mat, bottom, top, width=0.05, rungs=5, out=(0, 0, 0)):
    """Two rails and rungs from bottom to top; `out` offsets it off the wall."""
    bottom, top, out = Vector(bottom), Vector(top), Vector(out)
    up = (top - bottom).normalized()
    side = up.cross(out.normalized() if out.length else Vector((1, 0, 0))).normalized() * width / 2
    if side.length < 1e-6:
        side = Vector((width / 2, 0, 0))
    parts = [kit.beam(f'{name}Rail{s}', mat, bottom + out + side * s, top + out + side * s, 0.006) for s in (-1, 1)]
    for k in range(rungs):
        p = bottom.lerp(top, (k + 0.5) / rungs) + out
        parts.append(kit.beam(f'{name}Rung{k}', mat, p - side, p + side, 0.005))
    return parts


def rail(name, mat, points, height=0.04, post_every=1):
    """A hand rail on posts along `points` (on a surface)."""
    points = [Vector(p) for p in points]
    up = Vector((0, 0, height))
    parts = [kit.beam(f'{name}Bar{k}', mat, a + up, b + up, 0.006) for k, (a, b) in enumerate(zip(points, points[1:]))]
    for k, p in enumerate(points[::post_every]):
        parts.append(kit.beam(f'{name}Post{k}', mat, p, p + up, 0.006))
    return parts


def track_links(name, mat, x, width, y0, y1, z, count, side=None):
    """Tread bars across a track's run at height z (top or bottom), or, with `side`
    (+1/-1), standing on its outer face at x."""
    parts = []
    for k in range(count):
        y = y0 + (k + 0.5) * (y1 - y0) / count
        if side is None:
            parts.append(kit.box(f'{name}{k}', mat, (width, 0.018, 0.012), (x, y, z), bevel=0.002))
        else:
            parts.append(kit.box(f'{name}{k}', mat, (0.01, 0.018, width), (x + side * 0.005, y, z), bevel=0.002))
    return parts
