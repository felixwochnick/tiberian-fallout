"""
Tiberian Fallout – GDI Titan (MMCH), after Tiberian Sun.

A big walker: a wide, flat, faceted torso in desert camouflage with a lit vision
slit in its chin, a small cupola on the roof, a sensor box with a lit window at the
back right and two tall whip antennas. The long cannon lies along the left side on
its mount, an equipment pod with a searchlight on the right; house-colour panels on
both. Two heavy legs: armoured thighs and shins (house-colour shin plates), big knee
joints with pistons, broad feet with three toes and a heel spur.

Rig: empties, no armature (see walker.py): Body → torso and guns, Hip → Knee → Ankle.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle    loop, 2 s: the body breathes
    Walk    loop, 1.6 s (two heavy steps); the root's walkSpeed (glTF extras) is the
            ground speed in cells per second at which the feet do not slide
    Fire    once, 1 s: the cannon fires, its barrel recoils and runs out again
            (not used by the game yet)

Run headless:

    Blender -b --factory-startup --python blender/MMCH.py [-- --preview <dir>]

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
OUT = os.path.join(PROJECT, 'public', 'models', 'MMCH.glb')
BLEND = os.path.join(HERE, 'MMCH.blend')

HIP_Z = 0.58
HIP_X = 0.12
THIGH = 0.28
SHIN = 0.27
WALK_FRAMES = 48
SWING = 0.28
BEND = 0.65
FIRE_FRAMES = 30
CANNON = Vector((-0.34, -0.17, 0.74))   # the barrel's breech, on the left mount
BARREL = 0.62
LOW, TOP = 0.6, 0.88                    # the torso's bottom and roof
SCALE = 1.15                            # the whole walker: bigger than the Wolverine, as in the original

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'pod_dark': material('PodDark', srgb('#2b3036'), 0.6, 0.6),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'flash': material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


# --------------------------------------------------------------------------- parts

def chin_front(z):
    """The chin's sloping front (y) at height z."""
    return -0.17 - (z - LOW) / 0.07 * 0.06


def back(z):
    """The torso's back (y) at height z."""
    return 0.22 - (z - LOW - 0.06) / (TOP - LOW - 0.06) * 0.02


def torso(m, root):
    """The flat faceted torso with its fittings; returns (shell, details)."""
    shell = camo(kit.merge('Torso', [
        kit.hexahedron('Torso', m['sand'], (
            (-0.25, -0.2, LOW + 0.06), (0.25, -0.2, LOW + 0.06), (0.25, 0.22, LOW + 0.06), (-0.25, 0.22, LOW + 0.06),
            (-0.21, -0.12, TOP), (0.21, -0.12, TOP), (0.21, 0.2, TOP), (-0.21, 0.2, TOP)), bevel=0.018),
        # the chin under the front, sloping in towards the hips
        kit.hexahedron('Chin', m['sand'], (
            (-0.17, -0.17, LOW), (0.17, -0.17, LOW), (0.17, 0.16, LOW), (-0.17, 0.16, LOW),
            (-0.22, -0.23, LOW + 0.07), (0.22, -0.23, LOW + 0.07), (0.22, 0.2, LOW + 0.07), (-0.22, 0.2, LOW + 0.07)), bevel=0.012),
    ]), root)
    parts = [
        box('Pelvis', m['pod_dark'], (0.3, 0.2, 0.1), (0, 0.01, HIP_Z + 0.02), bevel=0.012),
        box('Roof', m['sand_light'], (0.36, 0.26, 0.02), (0, 0.04, TOP + 0.008), bevel=0.006),
        # the vision slit in the chin, lit from inside, under a brow
        box('Slit', m['window'], (0.26, 0.04, 0.03), (0, chin_front(LOW + 0.045) - 0.002, LOW + 0.045), bevel=0.004),
        box('Brow', m['pod_dark'], (0.3, 0.04, 0.02), (0, -0.215, LOW + 0.075), bevel=0.004),
        # cupola with a hatch, front left of the roof
        cylinder('Cupola', m['steel'], 0.07, 0.05, (-0.08, -0.02, TOP + 0.03), segments=16),
        cylinder('CupolaHatch', m['steel_light'], 0.05, 0.015, (-0.08, -0.02, TOP + 0.06), segments=16),
        box('CupolaSlit', m['window'], (0.06, 0.01, 0.012), (-0.08, -0.09, TOP + 0.04), bevel=0.002),
        # the sensor box at the back right, its window looking forward
        box('Sensor', m['pod_dark'], (0.12, 0.1, 0.17), (0.12, 0.12, TOP + 0.09), bevel=0.012),
        box('SensorWindow', m['window'], (0.08, 0.01, 0.1), (0.12, 0.068, TOP + 0.1), bevel=0.003),
        box('SensorBand', m['remap'], (0.125, 0.105, 0.025), (0.12, 0.12, TOP + 0.02), bevel=0.004),
        # two whip antennas at the back
        beam('AntennaL', m['steel'], (-0.15, 0.17, TOP), (-0.16, 0.19, TOP + 0.5), 0.007),
        beam('AntennaR', m['steel'], (0.17, 0.17, TOP + 0.17), (0.18, 0.19, TOP + 0.58), 0.007),
        # house-colour band round the torso, vents on the back
        box('BandFront', m['remap'], (0.4, 0.014, 0.03), (0, -0.2 + 0.07 / 0.22 * 0.08 - 0.004, LOW + 0.13), bevel=0.003),
        box('VentBack', m['dark'], (0.26, 0.014, 0.08), (0, back(LOW + 0.14), LOW + 0.14), bevel=0.003),
    ]
    for k in range(4):  # vent ribs
        parts.append(box(f'VentRib{k}', m['steel'], (0.26, 0.016, 0.008), (0, back(LOW + 0.14) + 0.006, LOW + 0.11 + k * 0.02), bevel=0))
    parts += torso_details(m)
    return shell, kit.merge('TorsoDetails', parts)


def torso_details(m):
    """Seams, rivets, vents, smoke dischargers, the roof's rail and kit, chin lights,
    hip plates and hoses to the cannon mount."""
    bottom = LOW + 0.06

    def front(z):  # the sloping front's surface (y) at height z
        return -0.2 + (z - bottom) / (TOP - bottom) * 0.08 - 0.003

    def side(z):  # the sides' surface (x) at height z
        return 0.25 - (z - bottom) / (TOP - bottom) * 0.04 + 0.002

    parts = []
    parts += detail.seam('FrontSeam', m['seam'], (-0.2, front(0.78), 0.78), (0.2, front(0.78), 0.78))
    parts += detail.rivets('FrontRivets', m['steel_light'], (-0.18, front(0.865), 0.865), (0.18, front(0.865), 0.865), 9)
    parts += detail.rivets('ChinRivets', m['steel_light'], (-0.16, chin_front(LOW + 0.064) - 0.002, LOW + 0.064), (0.16, chin_front(LOW + 0.064) - 0.002, LOW + 0.064), 7)
    for s in (-1, 1):
        parts += detail.seam(f'FrontSeamV{s}', m['seam'], (s * 0.08, front(0.68), 0.68), (s * 0.08, front(0.87), 0.87))
        parts += detail.seam(f'SideSeam{s}', m['seam'], (s * side(0.68), 0.19, 0.68), (s * side(0.87), 0.19, 0.87))
        parts += detail.rivets(f'SideRivets{s}', m['steel_light'], (s * side(0.86), -0.1, 0.86), (s * side(0.86), 0.18, 0.86), 6, axis='X')
        parts += detail.grille(f'SideVent{s}', m['steel'], m['dark'], (s * side(0.84), 0.17, 0.84), 0.06, 0.05, 'X', 3, 0.008)
        # three smoke dischargers on each front corner, pointing forward and up
        for k in range(3):
            tube = cylinder(f'Smoke{s}{k}', m['steel'], 0.012, 0.05, (s * (0.12 + 0.025 * k), -0.13, TOP + 0.02),
                            rotation=(math.radians(60), 0, 0), segments=8, bevel=0)
            parts.append(tube)
        parts.append(box(f'SmokeRack{s}', m['pod_dark'], (0.085, 0.03, 0.02), (s * 0.145, -0.11, TOP + 0.005), bevel=0.003))
        # lights under the chin, plates hanging over the hips
        parts += detail.lamp(f'ChinLight{s}', m['dark'], m['lamp_white'], (s * 0.1, chin_front(LOW + 0.025) - 0.004, LOW + 0.025), (0, -1, 0), 0.014)
        parts.append(box(f'HipPlate{s}', m['sand_light'], (0.12, 0.015, 0.1), (s * 0.15, -0.178, HIP_Z - 0.01), bevel=0.004,
                         rotation=(math.radians(6), 0, 0)))
        parts += detail.rivets(f'HipPlateRivets{s}', m['steel'], (s * 0.11, -0.187, HIP_Z + 0.025), (s * 0.19, -0.187, HIP_Z + 0.025), 3)
    # roof: a hand rail round the back, an ammunition box, antenna bases
    roof = TOP + 0.018
    parts += detail.rail('RoofRail', m['steel_light'], [(-0.18, 0.0, roof), (-0.18, 0.17, roof), (0.04, 0.17, roof)], 0.04)
    parts += [
        box('RoofBox', m['olive'], (0.09, 0.06, 0.035), (0.02, 0.08, roof + 0.017), bevel=0.005),
        box('RoofBoxLid', m['steel'], (0.092, 0.062, 0.008), (0.02, 0.08, roof + 0.036), bevel=0.002),
        box('AntennaBaseL', m['steel'], (0.03, 0.03, 0.03), (-0.15, 0.17, TOP + 0.015), bevel=0.004),
        box('AntennaBaseR', m['steel'], (0.03, 0.03, 0.03), (0.17, 0.17, TOP + 0.18), bevel=0.004),
    ]
    parts += detail.rivets('SensorRivets', m['steel_light'], (0.075, 0.067, TOP + 0.17), (0.165, 0.067, TOP + 0.17), 4)
    # hoses from the torso to the cannon mount
    for k in range(2):
        parts += detail.hose(f'MountHose{k}', m['dark'], (-0.23, 0.08 + 0.04 * k, 0.8), (-0.3, 0.16 + 0.03 * k, 0.87),
                             (-0.34, 0.1 + 0.03 * k, 0.805), 0.01)
    return parts


def cannon(m, body):
    """The left mount with the cannon; returns (barrel group, flash). The barrel group's
    origin is the breech (it slides back along +Y when firing)."""
    mount = [
        box('CannonMount', m['pod_dark'], (0.12, 0.3, 0.13), (CANNON.x, 0.0, CANNON.z), bevel=0.014),
        box('MountPanel', m['remap'], (0.012, 0.22, 0.07), (CANNON.x - 0.062, 0.0, CANNON.z), bevel=0.003),
        cylinder('Trunnion', m['steel'], 0.05, 0.1, (CANNON.x + 0.07, 0.0, CANNON.z), rotation=(0, math.pi / 2, 0), segments=14),
        box('Mantlet', m['steel'], (0.1, 0.06, 0.1), (CANNON.x, CANNON.y + 0.03, CANNON.z), bevel=0.012),
    ]
    kit.parent(kit.merge('CannonMount', mount, CANNON), body)
    group = walker.joint('Cannon', body, CANNON)
    tip = CANNON - Vector((0, BARREL, 0))
    barrel = [
        cylinder('Barrel', m['steel_light'], 0.03, BARREL, CANNON - Vector((0, BARREL / 2, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('BarrelSleeve', m['steel'], 0.042, 0.16, CANNON - Vector((0, 0.08, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('Evacuator', m['steel'], 0.04, 0.07, CANNON - Vector((0, BARREL * 0.55, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        box('MuzzleBrake', m['steel'], (0.08, 0.07, 0.05), tip + Vector((0, 0.02, 0)), bevel=0.008),
    ]
    barrel += [cylinder(f'CoolRing{k}', m['steel'], 0.036, 0.012, CANNON - Vector((0, 0.2 + 0.035 * k, 0)), rotation=(math.pi / 2, 0, 0),
                        segments=14, bevel=0) for k in range(4)]
    kit.parent(kit.merge('Barrel', barrel, CANNON), group)
    # a sight on top of the mount
    sight = [
        cylinder('Sight', m['steel'], 0.022, 0.14, (CANNON.x, -0.02, CANNON.z + 0.09), rotation=(math.pi / 2, 0, 0), segments=12),
        box('SightFoot', m['pod_dark'], (0.03, 0.05, 0.03), (CANNON.x, -0.01, CANNON.z + 0.07), bevel=0.003),
        *detail.lamp('SightLens', m['dark'], m['window'], (CANNON.x, -0.092, CANNON.z + 0.09), (0, -1, 0), 0.016),
        *detail.rivets('MountRivets', m['steel_light'], (CANNON.x - 0.061, -0.12, CANNON.z + 0.05), (CANNON.x - 0.061, 0.12, CANNON.z + 0.05), 6,
                       axis='X'),
    ]
    kit.parent(kit.merge('Sight', sight), body)
    muzzle = tip - Vector((0, 0.05, 0))
    flash = kit.merge('Flash', [sphere(f'Flash{k}', m['flash'], 0.06 - 0.015 * k, muzzle - Vector((0, 0.05 * k, 0)), 10) for k in range(3)], muzzle)
    kit.parent(flash, group)
    flash.scale = (kit.HIDDEN,) * 3
    return group, flash


def pod(m):
    """The equipment pod on the right with a searchlight."""
    x = 0.32
    parts = [
        box('Pod', m['pod_dark'], (0.1, 0.28, 0.15), (x, 0.0, 0.74), bevel=0.014),
        cylinder('PodArm', m['steel'], 0.05, 0.1, (x - 0.07, 0.0, 0.74), rotation=(0, math.pi / 2, 0), segments=14),
        box('PodPanel', m['remap'], (0.012, 0.2, 0.08), (x + 0.052, 0.0, 0.74), bevel=0.003),
        cylinder('Searchlight', m['steel'], 0.035, 0.05, (x, -0.16, 0.76), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('SearchlightGlass', m['lamp_white'], 0.027, 0.01, (x, -0.186, 0.76), rotation=(math.pi / 2, 0, 0), segments=14, bevel=0),
        box('PodRack', m['steel'], (0.08, 0.1, 0.03), (x, 0.06, 0.83), bevel=0.004),
        *detail.grille('PodVent', m['steel'], m['dark'], (x + 0.052, 0.1, 0.74), 0.05, 0.06, 'X', 3, 0.006),
        *detail.rivets('PodRivets', m['steel_light'], (x + 0.052, -0.12, 0.8), (x + 0.052, 0.12, 0.8), 6, axis='X'),
    ]
    for k in range(4):  # a rack of rocket tubes under the searchlight
        tx, tz = x - 0.022 + 0.044 * (k % 2), 0.695 + 0.03 * (k // 2)
        parts += [cylinder(f'RocketTube{k}', m['steel'], 0.014, 0.03, (tx, -0.145, tz), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
                  cylinder(f'RocketHole{k}', m['dark'], 0.01, 0.004, (tx, -0.16, tz), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0)]
    return kit.merge('Pod', parts)


def leg(m, root, s, body):
    """One heavy leg on its joints, centred under the hip; returns the walker.Leg."""
    hip = Vector((s * HIP_X, 0, HIP_Z))
    joints = walker.Leg(f'Leg{s}', body, hip, THIGH, SHIN)
    knee, ankle = hip - Vector((0, 0, THIGH)), hip - Vector((0, 0, THIGH + SHIN))
    x = hip.x
    thigh = camo(kit.merge(f'Thigh{s}', [kit.hexahedron(f'Thigh{s}', m['sand'], (
        (x - 0.06, -0.07, knee.z + 0.02), (x + 0.06, -0.07, knee.z + 0.02), (x + 0.06, 0.06, knee.z + 0.02), (x - 0.06, 0.06, knee.z + 0.02),
        (x - 0.07, -0.09, hip.z - 0.02), (x + 0.07, -0.09, hip.z - 0.02), (x + 0.07, 0.08, hip.z - 0.02), (x - 0.07, 0.08, hip.z - 0.02)),
        bevel=0.014)], hip), root)
    kit.parent(thigh, joints.hip)

    def out(z):  # the thigh's outer face (x) at height z
        return x + s * (0.06 + 0.01 * (z - knee.z - 0.02) / (hip.z - knee.z - 0.04) + 0.001)

    top, low = hip.z - 0.04, knee.z + 0.05
    kit.parent(kit.merge(f'ThighDetails{s}', [
        box(f'ThighPlate{s}', m['remap'], (0.1, 0.012, 0.09), (x, -0.088, hip.z - 0.09), bevel=0.003),
        *detail.rivets(f'ThighRivetsF{s}', m['steel_light'], (out(top), -0.05, top), (out(low), -0.05, low), 5, axis='X'),
        *detail.rivets(f'ThighRivetsB{s}', m['steel_light'], (out(top), 0.05, top), (out(low), 0.05, low), 5, axis='X'),
        *detail.seam(f'ThighSeam{s}', m['seam'], (out(hip.z - 0.14), -0.075, hip.z - 0.14), (out(hip.z - 0.14), 0.065, hip.z - 0.14)),
        *detail.hose(f'ThighHose{s}', m['dark'], hip + Vector((s * 0.06, 0.07, -0.02)), hip + Vector((s * 0.072, 0.09, -0.14)),
                     knee + Vector((s * 0.055, 0.055, 0.03)), 0.01),
    ], hip), joints.hip)
    # the hip joint bridges pelvis and thigh
    kit.parent(kit.merge(f'HipJoint{s}', [cylinder(f'HipJoint{s}', m['steel'], 0.06, 0.1, hip - Vector((s * 0.04, 0, 0)),
                                                   rotation=(0, math.pi / 2, 0), segments=16)], hip), joints.hip)
    shin = camo(kit.merge(f'Shin{s}', [kit.hexahedron(f'Shin{s}', m['sand'], (
        (x - 0.065, -0.08, ankle.z + 0.05), (x + 0.065, -0.08, ankle.z + 0.05), (x + 0.065, 0.06, ankle.z + 0.05), (x - 0.065, 0.06, ankle.z + 0.05),
        (x - 0.055, -0.07, knee.z - 0.01), (x + 0.055, -0.07, knee.z - 0.01), (x + 0.055, 0.05, knee.z - 0.01), (x - 0.055, 0.05, knee.z - 0.01)),
        bevel=0.014)], knee), root)
    kit.parent(shin, joints.knee)
    kit.parent(kit.merge(f'Knee{s}', [
        cylinder(f'KneeJoint{s}', m['steel'], 0.05, 0.15, knee, rotation=(0, math.pi / 2, 0), segments=14),
        box(f'KneeCap{s}', m['pod_dark'], (0.11, 0.05, 0.09), knee + Vector((0, -0.075, 0.0)), bevel=0.012),
        box(f'ShinPlate{s}', m['remap'], (0.1, 0.02, 0.12), knee + Vector((0, -0.083, -0.12)), bevel=0.006, rotation=(math.radians(-3), 0, 0)),
        beam(f'Piston{s}', m['steel_light'], knee + Vector((0, 0.065, -0.02)), ankle + Vector((0, 0.06, 0.07)), 0.022),
        beam(f'PistonSleeve{s}', m['steel'], knee + Vector((0, 0.062, -0.02)), knee + Vector((0, 0.062, -0.12)), 0.034),
        beam(f'Piston2{s}', m['steel'], knee + Vector((s * 0.05, 0.04, -0.04)), ankle + Vector((s * 0.05, 0.03, 0.08)), 0.014),
        *detail.grille(f'ShinVent{s}', m['steel'], m['dark'], (x + s * 0.063, -0.01, knee.z - 0.13), 0.07, 0.07, 'X', 4, 0.008),
        *detail.rivets(f'ShinRivets{s}', m['steel_light'], (x - 0.04, -0.094, knee.z - 0.07), (x + 0.04, -0.094, knee.z - 0.07), 3),
        *detail.rivets(f'ShinRivetsLow{s}', m['steel_light'], (x - 0.04, -0.094, knee.z - 0.17), (x + 0.04, -0.094, knee.z - 0.17), 3),
        box(f'AnkleGuard{s}', m['pod_dark'], (0.12, 0.03, 0.05), ankle + Vector((0, -0.088, 0.06)), bevel=0.006),
    ], knee), joints.knee)
    foot = [
        box(f'Foot{s}', m['pod_dark'], (0.15, 0.2, 0.045), ankle + Vector((0, -0.02, -0.008)), bevel=0.01),
        box(f'Heel{s}', m['steel'], (0.08, 0.08, 0.035), ankle + Vector((0, 0.11, -0.013)), bevel=0.008),
        cylinder(f'AnkleJoint{s}', m['steel'], 0.035, 0.12, ankle + Vector((0, 0, 0.02)), rotation=(0, math.pi / 2, 0), segments=12),
    ]
    for t in (-1, 0, 1):
        foot.append(box(f'Toe{s}{t}', m['steel'], (0.045, 0.1, 0.035), ankle + Vector((t * 0.05, -0.15, -0.013)),
                        bevel=0.008, rotation=(0, 0, t * 0.2)))
        foot.append(box(f'Claw{s}{t}', m['dark'], (0.032, 0.04, 0.022), ankle + Vector((t * 0.06, -0.21, -0.02)),
                        bevel=0.005, rotation=(math.radians(-15), 0, t * 0.2)))
    foot += detail.rivets(f'FootRivets{s}', m['steel_light'], (x - 0.05, -0.08, ankle.z + 0.015), (x + 0.05, -0.08, ankle.z + 0.015), 4, axis='Z')
    foot += detail.rivets(f'FootRivetsB{s}', m['steel_light'], (x - 0.05, 0.05, ankle.z + 0.015), (x + 0.05, 0.05, ankle.z + 0.015), 4, axis='Z')
    kit.parent(kit.merge(f'Foot{s}', foot, ankle), joints.ankle)
    return joints


# --------------------------------------------------------------------------- model

def fire(group, flash):
    """The Fire clip: the shot, the barrel recoils and runs out again."""
    kit.keys(group, 'location', {0: CANNON, 2: CANNON + Vector((0, 0.07, 0)), 6: CANNON + Vector((0, 0.07, 0)), 20: CANNON,
                                 FIRE_FRAMES: CANNON})
    kit.to_track(group, 'Fire')
    kit.keys(flash, 'scale', {0: Vector((1, 1, 1)), 2: Vector((1.3, 1.6, 1.3)), 4: Vector((kit.HIDDEN,) * 3),
                              FIRE_FRAMES: Vector((kit.HIDDEN,) * 3)}, 'CONSTANT')
    kit.to_track(flash, 'Fire')


def build():
    kit.COLLECTION = 'GDITitan'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = kit.IDLE_END

    m = materials()
    root = kit.empty('Titan')
    body = walker.joint('Body', root, (0, 0, 0))
    for obj in torso(m, root):
        kit.parent(obj, body)
    kit.parent(pod(m), body)
    group, flash = cannon(m, body)
    legs = [leg(m, root, s, body) for s in (-1, 1)]

    speed = walker.walk(legs, body, [], WALK_FRAMES, SWING, BEND, hidden=[flash])
    walker.idle(body, [], legs, sway=0.008, hidden=[flash])
    walker.hold(group, 'location', CANNON, WALK_FRAMES, 'Walk')
    walker.hold(group, 'location', CANNON, kit.IDLE_END, 'Idle')
    fire(group, flash)
    walker.rest(body, [j for g in legs for j in (g.hip, g.knee, g.ankle)])
    group.location = CANNON
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
        walker.previews(args[args.index('--preview') + 1], {'Idle': [0], 'Walk': [0, 12], 'Fire': [1]}, scale=1.9, target=(0, 0, 0.55))
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    print('export', walker.export(OUT), flush=True)


if __name__ == '__main__' and bpy.app.background:
    main()
