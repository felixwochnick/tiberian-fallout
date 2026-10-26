"""
Tiberian Fallout – GDI Wolverine (SMECH), after Tiberian Sun.

A small walker: a boxy armoured torso in desert camouflage, its front sloping back,
with two rows of warning stripes and a vision slit; house-colour shoulder plates; a
six-barrelled gatling gun on each arm, fed by an ammunition belt hanging in a loop;
a whip antenna at the back. Two legs with armoured thighs and shins, house-colour
knee pads and flat feet with toes.

Rig: empties, no armature (see walker.py): Body → torso and arms, Hip → Knee → Ankle.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle    loop, 2 s: the body breathes, the guns drift
    Walk    loop, 1 s (two steps); the root's walkSpeed (glTF extras) is the ground
            speed in cells per second at which the feet do not slide
    Fire    loop, 0.4 s: the barrels spin, the muzzles flash (not used by the game yet)

Run headless:

    Blender -b --factory-startup --python blender/SMECH.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; the walker looks along -Y (glTF +Z). The
origin is on the ground between its feet.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import detail  # noqa: E402
import walker  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'SMECH.glb')
BLEND = os.path.join(HERE, 'SMECH.blend')

HIP_Z = 0.4
HIP_X = 0.08
THIGH = 0.19
SHIN = 0.18
WALK_FRAMES = 30
SWING = 0.32            # hip swing (radians) either way
BEND = 0.7              # knee bend in the middle of a swing
FIRE_FRAMES = 12
GUN = 0.25              # the guns' distance from the middle (x)
GUN_Z = 0.54
SCALE = 0.85            # the whole walker: smaller than the Titan, as in the original

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'brass': material('Brass', srgb('#b8902e'), 0.4, 0.8),
        'pod_dark': material('PodDark', srgb('#2b3036'), 0.6, 0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'flash': material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def stripes(m, name, centre, width, count, height=0.022):
    """A row of warning stripes across the front, yellow and dark in turn."""
    w = width / count
    return [box(f'{name}{k}', m['hazard'] if k % 2 == 0 else m['dark'], (w, 0.01, height),
                centre + Vector((-width / 2 + (k + 0.5) * w, 0, 0)), bevel=0) for k in range(count)]


# --------------------------------------------------------------------------- parts

def torso(m, root):
    """The armoured box with its fittings; returns (shell, details)."""
    shell = camo(kit.merge('Torso', [kit.hexahedron('Torso', m['sand'], (
        (-0.16, -0.12, 0.42), (0.16, -0.12, 0.42), (0.16, 0.13, 0.42), (-0.16, 0.13, 0.42),
        (-0.14, -0.07, 0.76), (0.14, -0.07, 0.76), (0.14, 0.11, 0.76), (-0.14, 0.11, 0.76)), bevel=0.015)]), root)
    parts = [
        box('Pelvis', m['pod_dark'], (0.2, 0.14, 0.08), (0, 0.01, HIP_Z + 0.01), bevel=0.01),
        box('Roof', m['sand_light'], (0.25, 0.15, 0.025), (0, 0.02, 0.772), bevel=0.006),
        box('Slit', m['dark'], (0.18, 0.02, 0.022), (0, -0.078, 0.715), bevel=0.003),
        cylinder('Hatch', m['steel'], 0.04, 0.02, (-0.06, 0.05, 0.79), segments=16),
        box('Backpack', m['pod_dark'], (0.2, 0.06, 0.18), (0, 0.15, 0.58), bevel=0.012),
        beam('Antenna', m['steel'], (0.1, 0.09, 0.76), (0.1, 0.1, 1.08), 0.006),
        sphere('AntennaTip', m['steel_light'], 0.01, (0.1, 0.1, 1.08), 8),
    ]
    parts += stripes(m, 'StripeLow', Vector((0, -0.114, 0.49)), 0.28, 8)
    parts += stripes(m, 'StripeHigh', Vector((0, -0.084, 0.68)), 0.26, 8)
    for s in (-1, 1):
        parts += [
            box(f'Shoulder{s}', m['remap'], (0.07, 0.15, 0.1), (s * 0.18, 0.0, 0.68), bevel=0.012),
            box(f'SideBand{s}', m['remap'], (0.01, 0.2, 0.03), (s * 0.158, 0.0, 0.48), bevel=0.003),
        ]
    parts += torso_details(m)
    return shell, kit.merge('TorsoDetails', parts)


def torso_details(m):
    """Rivets, seams, vents, hip plates, the eye, a searchlight, the backpack's fittings."""
    def front(z):  # the sloping front's surface (y) at height z
        return -0.12 + (z - 0.42) / 0.34 * 0.05 - 0.003

    def side(z):  # the sides' surface (x) at height z
        return 0.16 - (z - 0.42) / 0.34 * 0.02 + 0.002

    parts = []
    for s in (-1, 1):
        parts += detail.rivets(f'FrontRivets{s}', m['steel_light'], (s * 0.135, front(0.52), 0.52), (s * 0.135, front(0.64), 0.64), 4)
        parts += detail.seam(f'SideSeam{s}', m['seam'], (s * side(0.44), 0.06, 0.44), (s * side(0.74), 0.06, 0.74))
        parts += detail.seam(f'SideSeamH{s}', m['seam'], (s * side(0.6), -0.09, 0.6), (s * side(0.6), 0.11, 0.6))
        parts += detail.grille(f'SideVent{s}', m['steel'], m['dark'], (s * side(0.55), -0.02, 0.55), 0.08, 0.06, 'X', 4, 0.008)
        parts.append(box(f'HipPlate{s}', m['sand_light'], (0.09, 0.015, 0.1), (s * 0.12, -0.112, 0.39), bevel=0.004, rotation=(math.radians(8), 0, 0)))
        parts += detail.rivets(f'HipPlateRivet{s}', m['steel'], (s * 0.09, -0.121, 0.41), (s * 0.15, -0.121, 0.41), 3)
        parts += detail.rivets(f'RoofRivets{s}', m['steel_light'], (-0.11, 0.02 + s * 0.065, 0.786), (0.11, 0.02 + s * 0.065, 0.786), 6, axis='Z')
        # the backpack's exhaust stacks
        parts += [cylinder(f'Exhaust{s}', m['steel'], 0.016, 0.1, (s * 0.06, 0.17, 0.7), segments=10),
                  cylinder(f'ExhaustTip{s}', m['dark'], 0.018, 0.012, (s * 0.06, 0.17, 0.752), segments=10, bevel=0)]
    parts += detail.lamp('Eye', m['dark'], m['lamp_red'], (0.08, front(0.585) - 0.004, 0.585), (0, -1, 0), 0.012)
    parts += detail.lamp('Searchlight', m['steel'], m['lamp_white'], (-0.18, -0.085, 0.75), (0, -1, 0), 0.02)
    parts += [
        box('SearchlightMount', m['steel'], (0.03, 0.04, 0.02), (-0.18, -0.055, 0.735), bevel=0.003),
        box('AntennaBase', m['steel'], (0.03, 0.03, 0.03), (0.1, 0.09, 0.775), bevel=0.004),
        cylinder('Canister', m['olive'], 0.025, 0.1, (0.125, 0.16, 0.56), segments=10),
        cylinder('CanisterCap', m['steel'], 0.012, 0.015, (0.125, 0.16, 0.615), segments=8, bevel=0),
    ]
    parts += detail.grille('BackVent', m['steel'], m['dark'], (0, 0.182, 0.55), 0.14, 0.08, 'Y', 5, 0.008)
    return parts


def arm(m, s, body):
    """An arm with its gatling gun, the belt and the flash; returns (arm joint, barrel
    group, flash)."""
    shoulder = Vector((s * 0.2, 0, 0.66))
    pivot = walker.joint(f'Arm{s}', body, shoulder)
    x = s * GUN
    elbow = Vector((x, -0.02, GUN_Z + 0.03))
    parts = [
        sphere(f'ShoulderJoint{s}', m['steel'], 0.04, shoulder, 12),
        beam(f'UpperArm{s}', m['steel'], shoulder, elbow, 0.05),
        cylinder(f'GunBody{s}', m['pod_dark'], 0.048, 0.17, (x, -0.08, GUN_Z), rotation=(math.pi / 2, 0, 0), segments=16),
        cylinder(f'GunBand{s}', m['remap'], 0.051, 0.03, (x, -0.04, GUN_Z), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0),
        box(f'Feeder{s}', m['steel'], (0.04, 0.06, 0.04), (x, -0.07, GUN_Z - 0.055), bevel=0.006),
        # cooling rings, a sight with its lens, an ammunition box, the hose up to the shoulder
        *[cylinder(f'CoolRing{s}{k}', m['steel'], 0.053, 0.012, (x, -0.1 - 0.03 * k, GUN_Z), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0)
          for k in range(3)],
        box(f'Sight{s}', m['steel'], (0.02, 0.06, 0.02), (x, -0.08, GUN_Z + 0.058), bevel=0.003),
        *detail.lamp(f'SightLens{s}', m['dark'], m['lamp_red'], (x, -0.113, GUN_Z + 0.058), (0, -1, 0), 0.007),
        box(f'AmmoBox{s}', m['olive'], (0.05, 0.07, 0.06), (x + s * 0.06, -0.03, GUN_Z - 0.02), bevel=0.006),
        box(f'AmmoBoxLid{s}', m['steel'], (0.052, 0.072, 0.01), (x + s * 0.06, -0.03, GUN_Z + 0.013), bevel=0.002),
        *detail.hose(f'Hose{s}', m['dark'], (x, 0.0, GUN_Z + 0.04), (s * 0.29, 0.08, GUN_Z + 0.12), (s * 0.21, 0.04, 0.66), 0.009),
    ]
    # the ammunition belt hangs from the feeder in a loop back to the arm
    start, ctrl, end = Vector((x, -0.08, GUN_Z - 0.07)), Vector((x, -0.02, GUN_Z - 0.3)), Vector((x - s * 0.01, -0.005, GUN_Z - 0.035))
    points = [(1 - t) ** 2 * start + 2 * (1 - t) * t * ctrl + t * t * end for t in (k / 14 for k in range(15))]
    for k, (p, q) in enumerate(zip(points, points[1:])):  # a closed band of cartridges
        link = box(f'Belt{s}_{k}', m['brass'], (0.028, 0.016, (q - p).length + 0.004), (p + q) / 2, bevel=0.002)
        link.rotation_mode = 'QUATERNION'
        link.rotation_quaternion = (q - p).to_track_quat('Z', 'X')
        parts.append(link)
    kit.parent(kit.merge(f'Arm{s}', parts, shoulder), pivot)

    muzzle = Vector((x, -0.17, GUN_Z))
    group = walker.joint(f'Barrels{s}', pivot, muzzle)
    barrels = [cylinder(f'Barrel{s}_{k}', m['steel_light'], 0.01, 0.13,
                        muzzle + Vector((0.022 * math.cos(math.pi * k / 3), -0.06, 0.022 * math.sin(math.pi * k / 3))),
                        rotation=(math.pi / 2, 0, 0), segments=8, bevel=0) for k in range(6)]
    barrels += [cylinder(f'BarrelRing{s}{k}', m['steel'], 0.036, 0.012, muzzle + Vector((0, -y, 0)), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0)
                for k, y in enumerate((0.01, 0.11))]
    kit.parent(kit.merge(f'Barrels{s}', barrels, muzzle), group)
    tip = muzzle + Vector((0, -0.16, 0))
    flash = kit.merge(f'Flash{s}', [sphere(f'Flash{s}{k}', m['flash'], 0.03 - 0.008 * k, tip + Vector((0, -0.03 * k, 0)), 10) for k in range(3)], tip)
    kit.parent(flash, pivot)
    flash.scale = (kit.HIDDEN,) * 3
    return pivot, group, flash


def leg(m, root, s, body):
    """One leg on its joints, centred under the hip; returns the walker.Leg."""
    hip = Vector((s * HIP_X, 0, HIP_Z))
    joints = walker.Leg(f'Leg{s}', body, hip, THIGH, SHIN)
    knee, ankle = hip - Vector((0, 0, THIGH)), hip - Vector((0, 0, THIGH + SHIN))
    c = hip.x
    thigh = camo(kit.merge(f'Thigh{s}', [kit.hexahedron(f'Thigh{s}', m['sand'], (
        (c - 0.045, -0.06, knee.z + 0.01), (c + 0.045, -0.06, knee.z + 0.01),
        (c + 0.045, 0.05, knee.z + 0.01), (c - 0.045, 0.05, knee.z + 0.01),
        (c - 0.05, -0.07, hip.z), (c + 0.05, -0.07, hip.z),
        (c + 0.05, 0.06, hip.z), (c - 0.05, 0.06, hip.z)), bevel=0.01)], hip), root)
    kit.parent(thigh, joints.hip)

    def out(z):  # the thigh's outer face (x) at height z
        return c + s * (0.045 + 0.005 * (z - knee.z - 0.01) / (hip.z - knee.z - 0.01) + 0.001)

    top, low = hip.z - 0.03, knee.z + 0.04
    kit.parent(kit.merge(f'ThighDetails{s}', [
        box(f'ThighPlate{s}', m['sand_light'], (0.07, 0.012, 0.1), (c, -0.071, hip.z - 0.08), bevel=0.003),
        *detail.rivets(f'ThighRivetsF{s}', m['steel_light'], (out(top), -0.035, top), (out(low), -0.035, low), 4, axis='X'),
        *detail.rivets(f'ThighRivetsB{s}', m['steel_light'], (out(top), 0.03, top), (out(low), 0.03, low), 4, axis='X'),
    ], hip), joints.hip)
    # the hip joint bridges pelvis and thigh
    kit.parent(kit.merge(f'HipJoint{s}', [cylinder(f'HipJoint{s}', m['steel'], 0.045, 0.07, hip - Vector((s * 0.025, 0, 0)),
                                                   rotation=(0, math.pi / 2, 0), segments=14)], hip), joints.hip)
    shin = camo(kit.merge(f'Shin{s}', [kit.hexahedron(f'Shin{s}', m['sand'], (
        (c - 0.04, -0.05, ankle.z + 0.03), (c + 0.04, -0.05, ankle.z + 0.03),
        (c + 0.04, 0.04, ankle.z + 0.03), (c - 0.04, 0.04, ankle.z + 0.03),
        (c - 0.045, -0.065, knee.z), (c + 0.045, -0.065, knee.z),
        (c + 0.045, 0.05, knee.z), (c - 0.045, 0.05, knee.z)), bevel=0.01)], knee), root)
    kit.parent(shin, joints.knee)
    kit.parent(kit.merge(f'Knee{s}', [
        cylinder(f'KneeJoint{s}', m['steel'], 0.035, 0.1, knee, rotation=(0, math.pi / 2, 0), segments=12),
        box(f'KneePad{s}', m['remap'], (0.08, 0.04, 0.07), knee + Vector((0, -0.065, 0.0)), bevel=0.01),
        beam(f'Piston{s}', m['steel_light'], knee + Vector((0, 0.05, -0.02)), ankle + Vector((0, 0.04, 0.05)), 0.016),
        beam(f'PistonSleeve{s}', m['steel'], knee + Vector((0, 0.05, -0.02)), knee + Vector((0, 0.047, -0.09)), 0.024),
        beam(f'Piston2{s}', m['steel'], knee + Vector((s * 0.035, 0.03, -0.03)), ankle + Vector((s * 0.03, 0.025, 0.06)), 0.011),
        *detail.grille(f'ShinVent{s}', m['steel'], m['dark'], (c + s * 0.044, -0.005, knee.z - 0.075), 0.05, 0.05, 'X', 3, 0.006),
        *detail.rivets(f'KneeRivets{s}', m['steel_light'], (c - 0.025, -0.087, knee.z + 0.022), (c + 0.025, -0.087, knee.z + 0.022), 3),
    ], knee), joints.knee)
    foot = [
        box(f'Foot{s}', m['pod_dark'], (0.1, 0.13, 0.035), ankle + Vector((0, -0.01, -0.012)), bevel=0.008),
        box(f'Heel{s}', m['steel'], (0.06, 0.05, 0.025), ankle + Vector((0, 0.07, -0.017)), bevel=0.006),
        cylinder(f'AnkleJoint{s}', m['steel'], 0.025, 0.08, ankle + Vector((0, 0, 0.012)), rotation=(0, math.pi / 2, 0), segments=10),
    ]
    for t in (-1, 1):
        foot.append(box(f'Toe{s}{t}', m['steel'], (0.04, 0.07, 0.025), ankle + Vector((t * 0.028, -0.095, -0.017)),
                        bevel=0.006, rotation=(0, 0, t * 0.15)))
        foot.append(box(f'Claw{s}{t}', m['dark'], (0.026, 0.03, 0.016), ankle + Vector((t * 0.036, -0.135, -0.022)),
                        bevel=0.004, rotation=(math.radians(-15), 0, t * 0.15)))
    foot += detail.rivets(f'FootRivets{s}', m['steel_light'], (c, -0.05, ankle.z + 0.007), (c, 0.03, ankle.z + 0.007), 3, axis='Z')
    kit.parent(kit.merge(f'Foot{s}', foot, ankle), joints.ankle)
    return joints


# --------------------------------------------------------------------------- model

def fire(groups, flashes):
    """The Fire clip: the barrels spin a sixth of a turn per loop (they look the same
    after it), the muzzles flash in turn."""
    for k, group in enumerate(groups):
        kit.keys(group, 'rotation_euler', {0: Vector((0, 0, 0)), FIRE_FRAMES: Vector((0, math.pi / 3, 0))}, 'LINEAR')
        kit.to_track(group, 'Fire')
    for k, flash in enumerate(flashes):
        frames = {}
        for f in range(FIRE_FRAMES + 1):
            on = (f + 2 * k) % 4 < 2
            frames[f] = Vector((1, 1, 1)) * (1.0 if on else kit.HIDDEN)
        kit.keys(flash, 'scale', frames, 'CONSTANT')
        kit.to_track(flash, 'Fire')


def build():
    kit.COLLECTION = 'GDIWolverine'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = kit.IDLE_END

    m = materials()
    root = kit.empty('Wolverine')
    body = walker.joint('Body', root, (0, 0, 0))
    for obj in torso(m, root):
        kit.parent(obj, body)
    arms, groups, flashes = [], [], []
    for s in (-1, 1):
        pivot, group, flash = arm(m, s, body)
        arms.append(pivot)
        groups.append(group)
        flashes.append(flash)
    legs = [leg(m, root, s, body) for s in (-1, 1)]

    speed = walker.walk(legs, body, arms, WALK_FRAMES, SWING, BEND, hidden=flashes)
    walker.idle(body, arms, legs, hidden=flashes)
    fire(groups, flashes)
    walker.rest(body, [*arms, *groups, *[j for g in legs for j in (g.hip, g.knee, g.ankle)]])
    for flash in flashes:
        flash.scale = (kit.HIDDEN,) * 3
    # scaled as a whole at the end (parenting keeps world sizes); the stride scales with it
    root.scale = (SCALE,) * 3
    root['walkSpeed'] = round(speed * SCALE, 4)
    print('walk speed', root['walkSpeed'], 'cells/s', flush=True)
    return len(kit.collection().objects)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(256)
    if '--preview' in args:
        walker.previews(args[args.index('--preview') + 1], {'Idle': [0], 'Walk': [0, 8], 'Fire': [2]})
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    print('export', walker.export(OUT), flush=True)


if __name__ == '__main__' and bpy.app.background:
    main()
