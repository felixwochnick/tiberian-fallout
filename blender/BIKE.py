"""
Tiberian Fallout – Nod attack cycle (BIKE), after Tiberian Sun.

A long armoured motorcycle: a smooth cigar of a body, dark below and at its rounded
nose and pointed tail, red (house colour) on top, rides high between two big hub
wheels; the front wheel hangs on a single arm on its left, the rear one in a
swingarm. The rider lies forward in the cowl in the middle, behind a small
windscreen, his hands on the bars. On a rack above the rear wheel two round rocket
pods side by side, four tubes each facing forward, the missiles' red noses in their
mouths. Under the body a silver engine with cooling fins and two exhausts; a
headlight in the nose, red running lights on its cheeks, a tail light.

Nodes the game uses: "Cannon" (the rocket pods, tipped towards the target),
"FlashLeft" / "FlashRight" (a pod's muzzle flash; the shots take turns). Clips: Idle,
Walk, Fire (see nodvehicle.py).

Run headless:

    blender -b --factory-startup --python blender/BIKE.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'BIKE.glb')
BLEND = os.path.join(HERE, 'BIKE.blend')

FRONT = (-0.27, 0.085, 0.052)   # the front wheel: y, radius, width
REAR = (0.22, 0.085, 0.07)      # the rear wheel
WALK_FRAMES = 14
WALK_SPEED = 2 * math.pi * REAR[1] / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 10
SCALE = 1.25                     # against the harvester and the walkers
PODS = Vector((0, 0.2, 0.258))  # the pods' pivot (between them, over the rear wheel)
POD_X = 0.088
POD_RADIUS = 0.04
POD_LENGTH = 0.15

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam

# the body's cross sections, nose to tail: y, middle height, half width, half height
# (0: a point); it clears the wheels' tops
BODY = (
    (-0.375, 0.196, 0, 0),
    (-0.365, 0.198, 0.022, 0.02),
    (-0.335, 0.203, 0.042, 0.038),
    (-0.275, 0.21, 0.058, 0.052),
    (-0.17, 0.212, 0.069, 0.062),
    (-0.06, 0.21, 0.072, 0.066),
    (0.05, 0.212, 0.068, 0.062),
    (0.15, 0.216, 0.058, 0.052),
    (0.24, 0.222, 0.045, 0.04),
    (0.31, 0.226, 0.028, 0.025),
    (0.35, 0.228, 0, 0),
)


def cigar(name, sections, lower, upper, segments=14, split=0.25, span=(-0.3, 0.27)):
    """A smooth body through elliptic cross sections (`sections` as BODY); the faces
    looking up (normal z over `split`) within `span` (y) get the material `upper`, the
    rest (the pointed ends too) `lower`."""
    angles = [2 * math.pi * (k + 0.5) / segments for k in range(segments)]

    def build(bm):
        rings = []
        for y, z, a, b in sections:
            rings.append([bm.verts.new((0, y, z))] if a == 0 else
                         [bm.verts.new((a * math.cos(t), y, z + b * math.sin(t))) for t in angles])
        for r0, r1 in zip(rings, rings[1:]):
            for i in range(segments):
                j = (i + 1) % segments
                if len(r0) == 1:
                    bm.faces.new((r0[0], r1[i], r1[j]))
                elif len(r1) == 1:
                    bm.faces.new((r0[i], r0[j], r1[0]))
                else:
                    bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        for face in bm.faces:
            face.material_index = 1 if face.normal.z > split and span[0] < face.calc_center_median().y < span[1] else 0
            face.smooth = True

    obj = kit.mesh_object(name, build)
    for mat in (lower, upper):
        mat.use_backface_culling = True
        obj.data.materials.append(mat)
    return obj


def section(y):
    """The body's cross section (middle height, half width, half height) at y."""
    for (y0, *s0), (y1, *s1) in zip(BODY, BODY[1:]):
        if y0 <= y <= y1:
            t = (y - y0) / (y1 - y0)
            return tuple(a + (b - a) * t for a, b in zip(s0, s1))
    return BODY[0][1:] if y < BODY[0][0] else BODY[-1][1:]


def on_top(y, x=0.0, lift=0.0):
    """A point on the body's surface at y, x across (above the middle)."""
    z, a, b = section(y)
    x = min(abs(x), a * 0.98) * (1 if x >= 0 else -1)
    return Vector((x, y, z + b * math.sqrt(max(0.0, 1 - (x / a) ** 2)) + lift if a else z))


def frame(m):
    """Body, cowl, rider, fork, swingarm, engine."""
    fy, fr, fw = FRONT
    ry, rr, rw = REAR
    arm_x = -(fw / 2 + 0.014)        # the front wheel's arm, on its left
    parts = [
        cigar('Body', BODY, m['armour_dark'], m['remap']),
        # a dark keel under the body between the wheels, a seam along each side
        kit.hexahedron('Keel', m['armour_dark'], (
            (-0.035, -0.17, 0.15), (0.035, -0.17, 0.15), (0.035, 0.12, 0.15), (-0.035, 0.12, 0.15),
            (-0.05, -0.2, 0.19), (0.05, -0.2, 0.19), (0.05, 0.15, 0.19), (-0.05, 0.15, 0.19)), bevel=0.012),
        *[beam(f'SideSeam{s}{k}', m['seam'], Vector((s * section(y0)[1] * 0.97, y0, section(y0)[0] + 0.012)),
               Vector((s * section(y1)[1] * 0.97, y1, section(y1)[0] + 0.012)), 0.005, 0.006)
          for s in (-1, 1) for k, (y0, y1) in enumerate(((-0.29, -0.2), (-0.2, -0.09), (-0.09, 0.03), (0.03, 0.13), (0.13, 0.23), (0.23, 0.3)))],
        # the cowl: the windscreen, the rider lying forward in it, the seat's back behind him
        kit.hexahedron('Windscreen', m['glass'], (
            on_top(-0.2, -0.032, -0.004), on_top(-0.2, 0.032, -0.004), on_top(-0.135, 0.04, -0.004), on_top(-0.135, -0.04, -0.004),
            on_top(-0.17, -0.026, 0.02), on_top(-0.17, 0.026, 0.02), on_top(-0.125, 0.032, 0.034), on_top(-0.125, -0.032, 0.034)),
            bevel=0.004),
        sphere('Helmet', m['dark'], 0.03, on_top(-0.075, 0, 0.004), 12),
        box('HelmetVisor', m['glass'], (0.036, 0.012, 0.012), on_top(-0.104, 0, 0.004), bevel=0.003),
        box('HelmetCrest', m['remap'], (0.008, 0.05, 0.008), on_top(-0.07, 0, 0.034), bevel=0.002),
        kit.hexahedron('Shoulders', m['dark'], (
            on_top(-0.06, -0.05, -0.012), on_top(-0.06, 0.05, -0.012), on_top(0.04, 0.045, -0.012), on_top(0.04, -0.045, -0.012),
            on_top(-0.05, -0.042, 0.018), on_top(-0.05, 0.042, 0.018), on_top(0.03, 0.035, 0.012), on_top(0.03, -0.035, 0.012)),
            bevel=0.012),
        *[beam(f'Arm{s}', m['dark'], on_top(-0.045, s * 0.05, 0.0), Vector((s * 0.058, -0.16, 0.255)), 0.02) for s in (-1, 1)],
        beam('Handlebar', m['steel_light'], (-0.075, -0.165, 0.25), (0.075, -0.165, 0.25), 0.011),
        *[sphere(f'Grip{s}', m['dark'], 0.011, (s * 0.075, -0.165, 0.25), 8) for s in (-1, 1)],
        box('SeatBack', m['armour'], (0.07, 0.025, 0.03), on_top(0.075, 0, 0.008), bevel=0.008),
        # the front wheel's single arm on its left, from the hub into the body, and its hub cap
        kit.hexahedron('FrontArm', m['steel_light'], (
            (arm_x - 0.01, fy - 0.015, fr - 0.01), (arm_x + 0.008, fy - 0.015, fr - 0.01), (arm_x + 0.008, fy + 0.02, fr - 0.01),
            (arm_x - 0.01, fy + 0.02, fr - 0.01),
            (arm_x - 0.004, fy + 0.07, 0.2), (arm_x + 0.014, fy + 0.07, 0.2), (arm_x + 0.014, fy + 0.11, 0.2), (arm_x - 0.004, fy + 0.11, 0.2)),
            bevel=0.004),
        beam('FrontShock', m['steel'], (arm_x - 0.012, fy + 0.03, fr + 0.03), (arm_x - 0.004, fy + 0.085, 0.19), 0.014),
        cylinder('FrontAxle', m['steel'], 0.022, 0.016, (arm_x - 0.004, fy, fr), rotation=(0, math.pi / 2, 0), segments=12),
        # the swingarm: both sides from the engine to the rear hub
        *[beam(f'Swingarm{s}', m['steel'], (s * (rw / 2 + 0.01), 0.04, 0.11), (s * (rw / 2 + 0.01), ry, rr), 0.014, 0.022)
          for s in (-1, 1)],
        *[cylinder(f'RearAxle{s}', m['steel'], 0.018, 0.014, (s * (rw / 2 + 0.012), ry, rr), rotation=(0, math.pi / 2, 0), segments=10)
          for s in (-1, 1)],
        beam('Shock', m['steel_light'], (0, 0.07, 0.11), (0, 0.13, 0.17), 0.016),
        # the engine under the body, with fins on its sides and two exhausts out to the back
        box('Engine', m['steel_light'], (0.07, 0.15, 0.06), (0, -0.04, 0.115), bevel=0.012),
        *[box(f'Fin{s}{k}', m['steel'], (0.008, 0.012, 0.05), (s * 0.038, -0.095 + k * 0.024, 0.115), bevel=0.002)
          for s in (-1, 1) for k in range(5)],
        box('Sump', m['dark'], (0.05, 0.08, 0.02), (0, -0.04, 0.078), bevel=0.006),
        *detail.hose('Intake', m['dark'], (0.03, -0.1, 0.13), (0.055, -0.14, 0.16), (0.04, -0.17, 0.19), 0.007, 4),
        *[cylinder(f'Exhaust{s}', m['steel'], 0.011, 0.2, (s * 0.05, 0.11, 0.12), rotation=(math.radians(-80), 0, 0), segments=8)
          for s in (-1, 1)],
        *[cylinder(f'ExhaustTip{s}', m['dark'], 0.009, 0.01, (s * 0.05, 0.208, 0.137), rotation=(math.radians(-80), 0, 0), segments=8,
                   bevel=0) for s in (-1, 1)],
        # lamps: the headlight in the nose, red running lights on its cheeks, the tail light
        *detail.lamp('Headlight', m['dark'], m['lamp_white'], (0, -0.366, 0.199), (0, -1, 0.1), 0.012),
        *[box(f'RunningLight{s}', m['lamp_red'], (0.006, 0.05, 0.007), (s * section(-0.25)[1] * 0.97, -0.25, section(-0.25)[0] + 0.012), bevel=0.001)
          for s in (-1, 1)],
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (0, 0.342, 0.228), (0, 1, 0), 0.008),
    ]
    return kit.merge('Frame', parts)


def pods(m, body):
    """The two rocket pods on their rack over the rear wheel, on the Cannon node;
    returns (node, flashes)."""
    pivot = kit.parent(kit.empty('Cannon', PODS), body)
    front = PODS.y - POD_LENGTH / 2
    turn = (math.pi / 2, 0, 0)
    parts = [
        # the rack: a post from the body's tail, a cross bar under the pods
        kit.hexahedron('RackPost', m['steel'], (
            (-0.02, PODS.y - 0.02, on_top(PODS.y).z - 0.02), (0.02, PODS.y - 0.02, on_top(PODS.y).z - 0.02),
            (0.02, PODS.y + 0.03, on_top(PODS.y).z - 0.02), (-0.02, PODS.y + 0.03, on_top(PODS.y).z - 0.02),
            (-0.016, PODS.y - 0.012, PODS.z - 0.02), (0.016, PODS.y - 0.012, PODS.z - 0.02),
            (0.016, PODS.y + 0.02, PODS.z - 0.02), (-0.016, PODS.y + 0.02, PODS.z - 0.02)), bevel=0.004),
        box('RackBar', m['armour_dark'], (2 * POD_X, 0.04, 0.022), PODS + Vector((0, 0.005, -0.022)), bevel=0.006),
    ]
    flashes = []
    for s, side in ((-1, 'Left'), (1, 'Right')):
        c = Vector((s * POD_X, PODS.y, PODS.z))
        parts += [
            cylinder(f'Pod{s}', m['armour_dark'], POD_RADIUS, POD_LENGTH, c, rotation=turn, segments=16, bevel=0.008),
            cylinder(f'PodTail{s}', m['armour_dark'], POD_RADIUS * 0.92, 0.03, c + Vector((0, POD_LENGTH / 2 + 0.012, 0)), rotation=turn,
                     segments=16, bevel=0.004, radius2=POD_RADIUS * 0.6),
            # red bands, the front one round the face, the tail one at the back
            cylinder(f'PodBand{s}', m['remap'], POD_RADIUS + 0.003, 0.026, c + Vector((0, -POD_LENGTH / 2 + 0.02, 0)), rotation=turn,
                     segments=16, bevel=0.003),
            cylinder(f'PodRing{s}', m['remap'], POD_RADIUS + 0.003, 0.014, c + Vector((0, POD_LENGTH / 2 - 0.03, 0)), rotation=turn,
                     segments=16, bevel=0.002),
            cylinder(f'PodFace{s}', m['armour'], POD_RADIUS - 0.004, 0.01, c + Vector((0, -POD_LENGTH / 2 - 0.004, 0)), rotation=turn,
                     segments=16, bevel=0.002),
            # the clamp on the rack, a fin on the outer side
            box(f'PodClamp{s}', m['steel'], (0.03, 0.05, 0.02), c + Vector((-s * 0.012, 0.005, -POD_RADIUS + 0.004)), bevel=0.004),
            box(f'PodFin{s}', m['armour_dark'], (0.006, 0.06, 0.03), c + Vector((s * (POD_RADIUS + 0.008), 0.04, 0.0)), bevel=0.002),
        ]
        for i in (-1, 1):
            for j in (-1, 1):
                p = c + Vector((i * 0.017, -POD_LENGTH / 2 - 0.01, j * 0.017))
                parts += [cylinder(f'Tube{s}{i}{j}', m['steel'], 0.0135, 0.012, p, rotation=turn, segments=10, bevel=0.002),
                          cylinder(f'Bore{s}{i}{j}', m['dark'], 0.0095, 0.004, p - Vector((0, 0.005, 0)), rotation=turn, segments=10,
                                   bevel=0),
                          cylinder(f'Nose{s}{i}{j}', m['remap'], 0.0075, 0.012, p - Vector((0, 0.003, 0)), rotation=(-math.pi / 2, 0, 0),
                                   segments=8, bevel=0, radius2=0.002)]
        flashes.append(kit.parent(nod.flash(m, f'Flash{side}', (c.x, front - 0.04, c.z), 0.035), pivot))
    kit.parent(kit.merge('Pods', parts, PODS), pivot)
    return pivot, flashes


def build():
    root, body = nod.start('NodAttackCycle', 'AttackCycle', WALK_SPEED)
    m = nod.materials()
    kit.parent(frame(m), body)
    _, flashes = pods(m, body)
    front = kit.parent(nod.wheel(m, 'WheelFront', (0, FRONT[0], FRONT[1]), FRONT[1], FRONT[2], lugs=16, hub=0.66, rim=m['steel']), root)
    rear = kit.parent(nod.wheel(m, 'WheelRear', (0, REAR[0], REAR[1]), REAR[1], REAR[2], lugs=16, hub=0.66, rim=m['steel']), root)
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
