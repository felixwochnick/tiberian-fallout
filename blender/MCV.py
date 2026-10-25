"""
Tiberian Fallout – GDI mobile construction vehicle (MCV), after Tiberian Sun.

A low tracked carrier: four armoured track pods outside a narrow camouflaged hull,
the narrow cab with its windscreen and steps at the front right, a bumper in warning
stripes at the front left, and the long grey segmented crane boom lying along the left
half of the roof
(it is raised over the construction yard when the vehicle deploys, see GACNST.py,
which builds the same vehicle with vehicle()).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle     loop, 2 s: the beacon on the cab blinks
    Walk     loop: driving, the road wheels turn (one turn per loop), the hull rocks a
             little; the root's custom property walkSpeed (glTF extras) is the ground
             speed in cells per second at which the wheels do not slip

Run headless:

    Blender -b --factory-startup --python blender/MCV.py

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'MCV.glb')
BLEND = os.path.join(HERE, 'MCV.blend')

WHEEL_RADIUS = 0.06
WALK_FRAMES = 26        # one turn of the wheels
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
BOOM_PIVOT = Vector((-0.1, 0.62, 0.38))
BOOM_LENGTH = 1.2
POD_Y = (-0.34, 0.42)   # the track pods' centres (y)
SPLIT = 0.04            # where the front half (the crane in the yard) ends

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'track': material('Track', srgb('#25231f'), 0.85, 0.2),
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#22384a'), strength=0.4),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'crane': material('CraneGrey', srgb('#9c9e9a'), 0.6, 0.2),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def wheel(m, name, centre):
    """A road wheel turning about x, with spokes so the turning shows."""
    parts = [cylinder(f'{name}Tyre', m['track'], WHEEL_RADIUS, 0.04, centre, rotation=(0, math.pi / 2, 0), segments=16, bevel=0.004),
             cylinder(f'{name}Hub', m['steel_light'], WHEEL_RADIUS * 0.55, 0.046, centre, rotation=(0, math.pi / 2, 0), segments=12, bevel=0.003)]
    for k in range(3):
        a = math.pi * k / 3
        d = Vector((0, math.cos(a), math.sin(a))) * WHEEL_RADIUS * 0.5
        parts.append(beam(f'{name}Spoke{k}', m['steel'], centre - d + Vector((0.025 * (1 if centre.x > 0 else -1), 0, 0)),
                          centre + d + Vector((0.025 * (1 if centre.x > 0 else -1), 0, 0)), 0.012, 0.012))
    return kit.merge(name, parts, centre)


def vehicle(m, root, prefix=''):
    """The vehicle; returns the parts by role (all unparented, in place):
    hull (camouflaged objects), details, wheels, boom (origin at BOOM_PIVOT), beacon.

    Like the original: a low, narrow hull with the crane boom along its left half, the
    narrow cab at the front right, and four armoured track pods outside the hull."""
    p = prefix
    hull = []
    # the hull in two halves: the front one stays as the crane when the MCV deploys
    front_hull = kit.hexahedron(f'{p}HullFront', m['sand'], (
        (0.27, -0.62, 0.12), (-0.27, -0.62, 0.12), (-0.27, SPLIT, 0.12), (0.27, SPLIT, 0.12),
        (0.23, -0.56, 0.33), (-0.23, -0.56, 0.33), (-0.23, SPLIT, 0.33), (0.23, SPLIT, 0.33)), bevel=0.015)
    body = kit.hexahedron(f'{p}HullRear', m['sand'], (
        (0.27, SPLIT, 0.12), (-0.27, SPLIT, 0.12), (-0.27, 0.74, 0.12), (0.27, 0.74, 0.12),
        (0.23, SPLIT, 0.33), (-0.23, SPLIT, 0.33), (-0.23, 0.7, 0.33), (0.23, 0.7, 0.33)), bevel=0.015)
    cab = kit.hexahedron(f'{p}Cab', m['sand'], (
        (0.29, -0.84, 0.14), (0.05, -0.84, 0.14), (0.05, -0.5, 0.14), (0.29, -0.5, 0.14),
        (0.27, -0.75, 0.44), (0.07, -0.75, 0.44), (0.07, -0.52, 0.45), (0.27, -0.52, 0.45)), bevel=0.012)
    hull_rear = [camo(kit.merge(f'{p}HullRear', [body]), root)]
    hull += [camo(kit.merge(f'{p}HullFront', [front_hull]), root), camo(kit.merge(f'{p}Cab', [cab]), root)]

    # four armoured track pods outside the hull, sloped at front and back
    pods = {POD_Y[0]: [], POD_Y[1]: []}
    for s in (-1, 1):
        for y in POD_Y:
            x0, x1 = s * 0.29, s * 0.53
            pods[y].append(kit.hexahedron(f'{p}Pod{s}{y}', m['sand'], (
                (x0, y - 0.3, 0.1), (x1, y - 0.3, 0.1), (x1, y + 0.3, 0.1), (x0, y + 0.3, 0.1),
                (x0, y - 0.22, 0.27), (x1 - s * 0.03, y - 0.22, 0.27), (x1 - s * 0.03, y + 0.24, 0.27), (x0, y + 0.24, 0.27)), bevel=0.02))
    hull.append(camo(kit.merge(f'{p}PodsFront', pods[POD_Y[0]]), root))
    hull_rear.append(camo(kit.merge(f'{p}PodsRear', pods[POD_Y[1]]), root))

    parts = [
        box(f'{p}Chassis', m['steel'], (0.5, SPLIT + 0.6, 0.08), (0, (SPLIT - 0.6) / 2, 0.1), bevel=0.01),
        # windscreen and side window of the cab
        kit.hexahedron(f'{p}Windscreen', m['glass'], (
            (0.25, -0.807, 0.31), (0.09, -0.807, 0.31), (0.09, -0.797, 0.31), (0.25, -0.797, 0.31),
            (0.24, -0.767, 0.41), (0.1, -0.767, 0.41), (0.1, -0.757, 0.41), (0.24, -0.757, 0.41)), bevel=0),
        box(f'{p}SideWindow', m['glass'], (0.01, 0.12, 0.06), (0.283, -0.64, 0.36), bevel=0.003),
        # bumper with warning stripes at the front left, under the boom's tip
        box(f'{p}Bumper', m['dark'], (0.3, 0.05, 0.07), (-0.13, -0.66, 0.17), bevel=0.008),
        # crane turntable at the back, an antenna, a vent row, a house-colour band
        box(f'{p}VentRowFront', m['dark'], (0.14, 0.3, 0.012), (0.13, -0.25, 0.335), bevel=0.003),
        beam(f'{p}Antenna', m['steel'], (0.25, -0.55, 0.45), (0.26, -0.53, 0.66), 0.007),
        box(f'{p}Band', m['remap'], (0.47, 0.05, 0.03), (0, -0.1, 0.28), bevel=0.004),
    ]
    rear = [
        box(f'{p}ChassisRear', m['steel'], (0.5, 0.7 - SPLIT, 0.08), (0, (SPLIT + 0.7) / 2, 0.1), bevel=0.01),
        cylinder(f'{p}Turntable', m['steel'], 0.11, 0.05, BOOM_PIVOT + Vector((0, 0.02, -0.06)), segments=20),
        box(f'{p}VentRow', m['dark'], (0.14, 0.3, 0.012), (0.13, 0.35, 0.335), bevel=0.003),
    ]
    for k in range(4):  # steps up the front of the cab
        parts.append(box(f'{p}Step{k}', m['steel_light'], (0.16, 0.05, 0.012), (0.17, -0.87 + k * 0.012, 0.16 + k * 0.045), bevel=0.002))
    for s in (-1, 1):
        parts.append(sphere(f'{p}Headlight{s}', m['lamp_white'], 0.018, (0.17 + s * 0.105, -0.84, 0.27), 10))
        # the tracks under the pods, with tread bars on top of their run
        for y in POD_Y:
            (parts if y == POD_Y[0] else rear).append(box(f'{p}Track{s}{y}', m['track'], (0.2, 0.62, 0.14), (s * 0.41, y, 0.07), bevel=0.05))
    for k in range(4):
        colour = m['hazard'] if k % 2 == 0 else m['dark']
        parts.append(box(f'{p}Hazard{k}', colour, (0.075, 0.012, 0.05), (-0.245 + k * 0.077, -0.687, 0.17), bevel=0))
    details = kit.merge(f'{p}Details', parts)
    details_rear = kit.merge(f'{p}DetailsRear', rear)

    # road wheels on the outside of the tracks, below the pods
    wheels, wheels_rear = [], []
    for s in (-1, 1):
        for y in POD_Y:
            for k in (-1, 0, 1):
                (wheels if y == POD_Y[0] else wheels_rear).append(wheel(m, f'{p}Wheel{s}{y}{k}', Vector((s * 0.52, y + k * 0.18, WHEEL_RADIUS))))

    # the crane boom lies along the left half of the roof, forward from its pivot
    segments = []
    for k in range(5):
        w = 0.19 - k * 0.01
        y0 = BOOM_PIVOT.y - 0.03 - k * 0.24
        segments.append(box(f'{p}BoomSeg{k}', m['crane'], (w, 0.22, 0.09 - k * 0.005), (BOOM_PIVOT.x, y0 - 0.11, BOOM_PIVOT.z), bevel=0.012))
    boom_shell = kit.merge(f'{p}Boom', segments, BOOM_PIVOT)   # grey, like the original
    ribs = [box(f'{p}BoomRib{k}', m['steel'], (0.2 - k * 0.01, 0.022, 0.1 - k * 0.005), (BOOM_PIVOT.x, BOOM_PIVOT.y - 0.03 - k * 0.24, BOOM_PIVOT.z), bevel=0.004)
            for k in range(5)]
    ribs.append(cylinder(f'{p}BoomTip', m['steel'], 0.03, 0.16, BOOM_PIVOT + Vector((0, -BOOM_LENGTH, 0)), rotation=(0, math.pi / 2, 0), segments=12))
    boom_details = kit.merge(f'{p}BoomDetails', ribs, BOOM_PIVOT)

    lamp = Vector((0.17, -0.6, 0.47))
    beacon = kit.merge(f'{p}Beacon', [sphere(f'{p}BeaconBulb', m['lamp_amber'], 0.02, lamp, 10),
                                      sphere(f'{p}BeaconHalo', m['glow_amber'], 0.045, lamp, 10)], lamp)
    beacon_base = cylinder(f'{p}BeaconBase', m['steel'], 0.018, 0.03, lamp - Vector((0, 0, 0.02)), segments=10, bevel=0)
    # the front half (hull, details, wheels) stays as the crane in the construction yard,
    # the rear half (rear: hull, details and wheels) goes into the hall
    return {'hull': hull, 'details': [details, beacon_base], 'wheels': wheels,
            'rear': [*hull_rear, details_rear, *wheels_rear],
            'boom': boom_shell, 'boom_details': boom_details, 'beacon': beacon}


def build():
    kit.COLLECTION = 'GDIMCV'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = kit.IDLE_END

    m = materials()
    root = kit.empty('MCV')
    root['walkSpeed'] = round(WALK_SPEED, 4)
    body = kit.parent(kit.empty('Body'), root)   # rocks while driving
    parts = vehicle(m, root)
    for obj in (*parts['hull'], *parts['details'], *[o for o in parts['rear'] if 'Wheel' not in o.name], parts['boom'], parts['beacon']):
        kit.parent(obj, body)
    kit.parent(parts['boom_details'], parts['boom'])
    parts['wheels'] += [o for o in parts['rear'] if 'Wheel' in o.name]
    for w in parts['wheels']:
        kit.parent(w, root)

    keys = kit.keys
    kit.blink(parts['beacon'], kit.flashes((0, 10), (30, 10)))
    kit.to_track(parts['beacon'], 'Idle')
    for w in parts['wheels']:
        # positive about x: the top of the wheel moves forward (-y)
        keys(w, 'rotation_euler', {f: Vector((2 * math.pi * f / WALK_FRAMES, 0, 0)) for f in range(0, WALK_FRAMES + 1, 2)} |
             {WALK_FRAMES: Vector((2 * math.pi, 0, 0))}, 'LINEAR')
        kit.to_track(w, 'Walk')
    keys(body, 'location', {f: Vector((0, 0, 0.005 * math.sin(4 * math.pi * f / WALK_FRAMES))) for f in range(WALK_FRAMES + 1)}, 'LINEAR')
    kit.to_track(body, 'Walk')
    return len(kit.collection().objects)


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(512)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)


if __name__ == '__main__' and bpy.app.background:
    main()
