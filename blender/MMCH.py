"""
Tiberian Fallout – GDI Titan (MMCH), after Tiberian Sun.

A tall walker, about 1.3 times the Wolverine's height: a wide, angular torso in desert
camouflage. Its upper part overhangs the chest like a hat: the front bevelled back,
the flat top sloping back, vents in its sides, three smoke dischargers on each front
corner, a hatch, a stubby sensor mast with a red beacon and two tall whip antennas
behind it. Below, the chest with a dark front panel and a lit vision block, a shoulder
box on the left with another vision block and a searchlight. The long cannon lies
along the right side (-x, upper left on screen) on a long mount with a sight and
house-colour panels. Two legs: armoured thighs, slanted knee plates, shins widening
down with house-colour plates, pistons behind, and wide flat feet with three toes and
a heel spur.

Rig: empties, no armature (see walker.py): Body → torso and gun, Hip → Knee → Ankle.

Nodes the game uses: "Cannon" (the barrel, tipped towards the target; its origin is
the breech), "Flash" (the muzzle).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle    loop, 2 s: the body breathes
    Walk    loop, 1.6 s (two heavy steps); the root's walkSpeed (glTF extras) is the
            ground speed in cells per second at which the feet do not slide
    Fire    once, 1 s: the cannon fires, its barrel recoils and runs out again
            (not used by the game yet)

Run headless:

    blender -b --factory-startup --python blender/MMCH.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; the walker looks along -Y (glTF +Z). The
origin is on the ground between its feet.
"""
import math
import os
import sys

import bmesh
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

HIP_Z = 0.6
HIP_X = 0.13
THIGH = 0.28
SHIN = 0.285
WALK_FRAMES = 48
SWING = 0.27
BEND = 0.65
FIRE_FRAMES = 30
LOW = 0.58                              # the chest's bottom
HAT = 0.83                              # where the overhanging upper torso begins
TOP = 0.98                              # its roof at the front edge, sloping back
FRONT, BACK = -0.18, 0.2                # the chest's front and back
HALF = 0.2                              # half the chest's width
CANNON = Vector((-0.29, -0.2, 0.71))    # the barrel's breech, on the mount at the right (-x)
BARREL = 0.52
SCALE = 0.86                            # the whole walker: about 1.3 times the Wolverine's height

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'pod_dark': material('PodDark', srgb('#2b3036'), 0.6, 0.6),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'vision': material('VisionBlock', srgb('#8fa6b4'), 0.15, 0.2, emission=srgb('#a8c8dc'), strength=1.2),
        'flash': material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7),
        'plate': plate_material(),
    })
    return m


def plate_material():
    """The camouflage's sand as a plain colour, recoloured like it (extras): armour plates
    and feet that need no baked pattern of their own."""
    mat = material('PlateSand', srgb(kit.CAMO['sand']), 0.8)
    mat['remapLightness'] = kit.CAMO_LIGHTNESS
    mat['remapSaturation'] = kit.CAMO_SATURATION
    mat['remapLuminance'] = kit.CAMO_LUMINANCE
    return mat


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


# --------------------------------------------------------------------------- shapes

def hull(name, mat, points, bevel=0.008):
    """A convex solid around `points`: chamfered blocks, wedges, armour plates."""
    def build(bm):
        result = bmesh.ops.convex_hull(bm, input=[bm.verts.new(p) for p in points])
        loose = {v for v in result['geom_interior'] + result['geom_unused'] if isinstance(v, bmesh.types.BMVert)}
        bmesh.ops.delete(bm, geom=list(loose), context='VERTS')
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), verts=bm.verts[:], edges=bm.edges[:])

    obj = kit.finish(kit.mesh_object(name, build), mat, bevel)
    if bevel:  # every edge left is a real one: bevelled (hardened normals), so the facets stay flat
        obj.modifiers['Bevel'].angle_limit = math.radians(5)
    return obj


def mirrored(points):
    """The points and their mirror images across x = 0."""
    return [(s * x, y, z) for x, y, z in points for s in (-1, 1)]


def rod(name, mat, p0, p1, radius, segments=10):
    """A round bar from p0 to p1 (pistons, tubes)."""
    p0, p1 = Vector(p0), Vector(p1)
    obj = cylinder(name, mat, radius, (p1 - p0).length, (p0 + p1) / 2, segments=segments)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = (p1 - p0).to_track_quat('Z', 'Y')
    return obj


def vision_block(name, m, centre, width, height):
    """A lit vision block in a dark frame on a front face (looking along -y)."""
    centre = Vector(centre)
    return [box(f'{name}Frame', m['pod_dark'], (width + 0.02, 0.014, height + 0.02), centre + Vector((0, 0.004, 0)), bevel=0.004),
            box(f'{name}Glass', m['vision'], (width, 0.012, height), centre - Vector((0, 0.002, 0)), bevel=0.003)]


# --------------------------------------------------------------------------- parts

def roof(y):
    """The roof's height at y: it slopes back from the front edge."""
    return TOP - (y + 0.13) / 0.3 * 0.02


def bevel(z):
    """The hat's bevelled front (y) at height z."""
    (y0, z0), (y1, z1) = (FRONT - 0.03, HAT + 0.035), (-0.13, TOP)   # its lower and upper edge
    return y0 + (z - z0) / (z1 - z0) * (y1 - y0)


def torso(m, root):
    """The chest, the overhanging upper torso and the left shoulder box; returns
    (shell, details)."""
    chest = hull('Chest', m['sand'], mirrored((
        (HALF - 0.05, FRONT + 0.04, LOW), (HALF - 0.05, BACK - 0.04, LOW),
        (HALF, FRONT, LOW + 0.06), (HALF, BACK, LOW + 0.06),
        (HALF, FRONT, HAT + 0.01), (HALF, BACK, HAT + 0.01))), 0.014)
    hat = hull('Hat', m['sand'], mirrored((
        (HALF + 0.04, FRONT - 0.03, HAT), (HALF + 0.04, BACK + 0.015, HAT),
        (HALF + 0.04, FRONT - 0.03, HAT + 0.035), (HALF + 0.04, BACK + 0.015, TOP - 0.06),
        (HALF, -0.13, TOP), (HALF, 0.17, roof(0.17)))), 0.012)
    shoulder = hull('ShoulderBox', m['sand'], [
        (HALF - 0.01, -0.15, 0.66), (HALF - 0.01, 0.14, 0.66), (HALF + 0.1, -0.14, 0.67), (HALF + 0.1, 0.13, 0.67),
        (HALF - 0.01, -0.16, HAT - 0.005), (HALF - 0.01, 0.14, HAT - 0.005), (HALF + 0.1, -0.15, HAT - 0.02), (HALF + 0.1, 0.13, HAT - 0.02),
        (HALF + 0.11, -0.13, 0.69), (HALF + 0.11, 0.12, 0.69), (HALF + 0.11, -0.14, HAT - 0.04), (HALF + 0.11, 0.12, HAT - 0.04)], 0.012)
    shell = camo(kit.merge('Torso', [chest, hat, shoulder]), root)
    return shell, kit.merge('TorsoDetails', torso_details(m))


def torso_details(m):
    """The front panel and vision blocks, the hat's fittings (dischargers, vents, mast,
    antennas, hatch), the shoulder box's lamp and panel, the pelvis and hip plates."""
    hat_face = FRONT - 0.03 - 0.003
    parts = [
        # pelvis between the hips and the armoured plate in front of it
        box('Pelvis', m['pod_dark'], (0.3, 0.2, 0.1), (0, 0.01, HIP_Z + 0.0), bevel=0.012),
        hull('CrotchPlate', m['plate'], mirrored(((0.06, FRONT + 0.02, LOW + 0.01), (0.045, FRONT + 0.045, LOW - 0.11),
                                                  (0.06, FRONT + 0.05, LOW + 0.01), (0.045, FRONT + 0.07, LOW - 0.11))), 0.006),
        # the dark front panel of the chest with a vision block, a band over it
        box('FrontPanel', m['pod_dark'], (0.26, 0.012, 0.15), (0, FRONT - 0.004, 0.735), bevel=0.004),
        *vision_block('Vision', m, (-0.07, FRONT - 0.012, 0.77), 0.07, 0.05),
        *detail.grille('FrontVent', m['steel'], m['dark'], (0.06, FRONT - 0.012, 0.7), 0.1, 0.05, 'Y', 4, 0.008),
        box('ChestBand', m['remap'], (0.4, 0.014, 0.025), (0, FRONT - 0.004, LOW + 0.045), bevel=0.003),
        *detail.lamp('ChestLight', m['dark'], m['lamp_green'], (0.02, FRONT - 0.012, 0.785), (0, -1, 0), 0.008),
        # the hat's bevelled front: a seam, rivets, a lit strip
        *detail.rivets('HatRivets', m['steel_light'], (-0.2, hat_face, HAT + 0.018), (0.2, hat_face, HAT + 0.018), 11),
        box('HatStrip', m['dark'], (0.16, 0.01, 0.016), (0.04, bevel(0.915) - 0.003, 0.915), bevel=0.002,
            rotation=(-math.atan2(0.08, TOP - HAT - 0.035), 0, 0)),
        # roof: the mast with its dark window and red beacon, a hatch, two antennas, a box
        hull('Mast', m['plate'], mirrored(((0.055, 0.02, roof(0.02) - 0.01), (0.055, 0.15, roof(0.15) - 0.01),
                                           (0.05, 0.05, TOP + 0.12), (0.05, 0.15, TOP + 0.15))), 0.008),
        box('MastWindow', m['dark'], (0.07, 0.01, 0.07), (0, 0.032, TOP + 0.06), bevel=0.003, rotation=(-math.atan2(0.03, 0.13), 0, 0)),
        cylinder('BeaconBase', m['steel'], 0.02, 0.012, (0, 0.11, TOP + 0.15), segments=12, bevel=0.002),
        sphere('Beacon', m['lamp_red'], 0.016, (0, 0.11, TOP + 0.162), 12),
        box('AntennaBaseL', m['steel'], (0.03, 0.03, 0.03), (-0.085, 0.17, roof(0.17) + 0.012), bevel=0.004),
        box('AntennaBaseR', m['steel'], (0.03, 0.03, 0.03), (0.085, 0.17, roof(0.17) + 0.012), bevel=0.004),
        beam('AntennaL', m['steel'], (-0.085, 0.17, roof(0.17)), (-0.09, 0.19, TOP + 0.4), 0.007),
        beam('AntennaR', m['steel'], (0.085, 0.17, roof(0.17)), (0.09, 0.19, TOP + 0.34), 0.007),
        cylinder('Hatch', m['steel'], 0.05, 0.02, (-0.12, -0.04, roof(-0.04) + 0.006), segments=16),
        cylinder('HatchLid', m['steel_light'], 0.038, 0.012, (-0.12, -0.04, roof(-0.04) + 0.02), segments=16),
        box('RoofBox', m['olive'], (0.08, 0.06, 0.035), (0.13, 0.08, roof(0.08) + 0.016), bevel=0.005),
        box('RoofBoxLid', m['steel'], (0.082, 0.062, 0.008), (0.13, 0.08, roof(0.08) + 0.035), bevel=0.002),
        box('RoofPlate', m['sand_light'], (0.012, 0.2, 0.01), (-0.07, 0.05, roof(0.05)), bevel=0.002),
        *detail.rail('RoofRail', m['steel_light'], [(-0.2, 0.06, roof(0.06)), (-0.2, 0.18, roof(0.18)), (-0.1, 0.18, roof(0.18))], 0.035),
        # the shoulder box on the left: a vision block, a searchlight, a house-colour panel
        *vision_block('ShoulderVision', m, (HALF + 0.05, -0.16, 0.765), 0.06, 0.05),
        cylinder('Searchlight', m['steel'], 0.026, 0.04, (HALF + 0.05, -0.155, 0.69), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('SearchlightGlass', m['lamp_white'], 0.02, 0.008, (HALF + 0.05, -0.177, 0.69), rotation=(math.pi / 2, 0, 0), segments=14, bevel=0),
        box('ShoulderPanel', m['remap'], (0.012, 0.18, 0.07), (HALF + 0.112, -0.01, 0.745), bevel=0.003),
        *detail.grille('ShoulderVent', m['steel'], m['dark'], (HALF + 0.112, 0.09, 0.745), 0.05, 0.06, 'X', 3, 0.006),
        *detail.rivets('ShoulderRivets', m['steel_light'], (HALF + 0.113, -0.12, 0.8), (HALF + 0.113, 0.1, 0.8), 6, axis='X'),
        *detail.lamp('ShoulderLight', m['dark'], m['lamp_green'], (HALF + 0.09, -0.16, 0.81), (0, -1, 0), 0.007),
        # vents in the chest's back
        *detail.grille('BackVent', m['steel'], m['dark'], (0, BACK + 0.004, 0.72), 0.24, 0.1, 'Y', 5, 0.008),
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (0.15, BACK + 0.005, 0.79), (0, 1, 0), 0.01),
    ]
    for s in (-1, 1):
        side = s * (HALF + 0.042)
        parts += [
            # three smoke dischargers on each front corner of the roof, pointing forward and out
            box(f'SmokeRack{s}', m['pod_dark'], (0.08, 0.04, 0.025), (s * 0.15, -0.1, roof(-0.1) + 0.008), bevel=0.003),
            *[rod(f'Smoke{s}{k}', m['steel'], (s * (0.125 + 0.025 * k), -0.1, roof(-0.1) + 0.01),
                  (s * (0.15 + 0.03 * k), -0.16, roof(-0.1) + 0.07), 0.011, 8) for k in range(3)],
            # vents and rivets in the hat's sides
            *[box(f'HatSlat{s}{k}', m['dark'], (0.008, 0.16, 0.008), (side, 0.07, HAT + 0.025 + 0.02 * k), bevel=0) for k in range(4)],
            *detail.rivets(f'HatSideRivets{s}', m['steel_light'], (side, -0.17, HAT + 0.015), (side, -0.04, HAT + 0.015), 4, axis='X'),
            # plates hanging over the hips
            hull(f'HipPlate{s}', m['plate'], [
                (s * 0.12, FRONT + 0.02, LOW + 0.02), (s * 0.21, FRONT + 0.02, LOW + 0.02),
                (s * 0.12, FRONT, LOW - 0.08), (s * 0.2, FRONT, LOW - 0.08),
                (s * 0.12, FRONT + 0.04, LOW + 0.02), (s * 0.21, FRONT + 0.04, LOW + 0.02),
                (s * 0.12, FRONT + 0.02, LOW - 0.08), (s * 0.2, FRONT + 0.02, LOW - 0.08)], 0.005),
            *detail.rivets(f'HipPlateRivets{s}', m['steel'], (s * 0.135, FRONT + 0.008, LOW), (s * 0.19, FRONT + 0.008, LOW), 3),
            *detail.seam(f'ChestSeam{s}', m['seam'], (s * (HALF + 0.002), 0.08, LOW + 0.06), (s * (HALF + 0.002), 0.08, HAT)),
        ]
    # hoses from the chest to the cannon mount
    for k in range(2):
        parts += detail.hose(f'MountHose{k}', m['dark'], (-HALF, 0.06 + 0.04 * k, 0.8), (-0.27, 0.12 + 0.03 * k, 0.84),
                             (-0.3, 0.08 + 0.03 * k, 0.775), 0.01)
    return parts


def cannon(m, body):
    """The mount on the right with the cannon; returns (barrel group, flash). The barrel
    group's origin is the breech (it slides back along +Y when firing)."""
    x, z = CANNON.x, CANNON.z
    mount = [
        hull('CannonMount', m['pod_dark'], [
            (-HALF + 0.01, CANNON.y + 0.02, z - 0.07), (-HALF + 0.01, 0.17, z - 0.07), (x - 0.06, CANNON.y + 0.04, z - 0.07), (x - 0.06, 0.16, z - 0.07),
            (-HALF + 0.01, CANNON.y, z + 0.05), (-HALF + 0.01, 0.17, z + 0.06), (x - 0.06, CANNON.y + 0.02, z + 0.05), (x - 0.06, 0.16, z + 0.06),
            (x - 0.075, CANNON.y + 0.05, z - 0.04), (x - 0.075, 0.14, z - 0.04), (x - 0.075, CANNON.y + 0.04, z + 0.03),
            (x - 0.075, 0.14, z + 0.03)], 0.01),
        box('MountPanel', m['remap'], (0.012, 0.24, 0.05), (x - 0.077, -0.02, z - 0.005), bevel=0.003),
        *detail.rivets('MountRivets', m['steel_light'], (x - 0.079, -0.14, z + 0.032), (x - 0.079, 0.12, z + 0.032), 6, axis='X'),
        *detail.grille('MountVent', m['steel'], m['dark'], (x - 0.077, 0.13, z - 0.005), 0.04, 0.05, 'X', 3, 0.006),
        box('Mantlet', m['steel'], (0.1, 0.05, 0.1), (x, CANNON.y + 0.01, z), bevel=0.012),
        # a sight on top of the mount
        cylinder('Sight', m['steel'], 0.02, 0.12, (x, CANNON.y + 0.08, z + 0.085), rotation=(math.pi / 2, 0, 0), segments=12),
        box('SightFoot', m['pod_dark'], (0.03, 0.05, 0.03), (x, CANNON.y + 0.09, z + 0.065), bevel=0.003),
        *detail.lamp('SightLens', m['dark'], m['vision'], (x, CANNON.y + 0.018, z + 0.085), (0, -1, 0), 0.014),
    ]
    kit.parent(kit.merge('CannonMount', mount, CANNON), body)
    group = walker.joint('Cannon', body, CANNON)
    tip = CANNON - Vector((0, BARREL, 0))
    barrel = [
        cylinder('Barrel', m['steel_light'], 0.028, BARREL, CANNON - Vector((0, BARREL / 2, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('BarrelSleeve', m['steel'], 0.042, 0.16, CANNON - Vector((0, 0.08, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder('Evacuator', m['steel'], 0.038, 0.07, CANNON - Vector((0, BARREL * 0.55, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
        box('MuzzleBrake', m['steel'], (0.075, 0.07, 0.05), tip + Vector((0, 0.02, 0)), bevel=0.008),
        box('MuzzleSlot', m['dark'], (0.077, 0.02, 0.026), tip + Vector((0, 0.02, 0)), bevel=0),
    ]
    barrel += [cylinder(f'CoolRing{k}', m['steel'], 0.034, 0.012, CANNON - Vector((0, 0.2 + 0.035 * k, 0)), rotation=(math.pi / 2, 0, 0),
                        segments=14, bevel=0) for k in range(4)]
    kit.parent(kit.merge('Barrel', barrel, CANNON), group)
    muzzle = tip - Vector((0, 0.05, 0))
    flash = kit.merge('Flash', [sphere(f'Flash{k}', m['flash'], 0.06 - 0.015 * k, muzzle - Vector((0, 0.05 * k, 0)), 10) for k in range(3)], muzzle)
    kit.parent(flash, group)
    flash.scale = (kit.HIDDEN,) * 3
    return group, flash


def leg(m, root, s, body):
    """One heavy leg on its joints, centred under the hip; returns the walker.Leg."""
    hip = Vector((s * HIP_X, 0, HIP_Z))
    joints = walker.Leg(f'Leg{s}', body, hip, THIGH, SHIN)
    knee, ankle = hip - Vector((0, 0, THIGH)), hip - Vector((0, 0, THIGH + SHIN))
    x = hip.x
    thigh = camo(kit.merge(f'Thigh{s}', [hull(f'Thigh{s}', m['sand'], [
        (x - 0.055, -0.07, knee.z + 0.03), (x + 0.055, -0.07, knee.z + 0.03), (x + 0.055, 0.065, knee.z + 0.03), (x - 0.055, 0.065, knee.z + 0.03),
        (x - 0.07, -0.095, hip.z - 0.08), (x + 0.07, -0.095, hip.z - 0.08),
        (x - 0.07, -0.075, hip.z + 0.01), (x + 0.07, -0.075, hip.z + 0.01), (x + 0.07, 0.085, hip.z + 0.01), (x - 0.07, 0.085, hip.z + 0.01)],
        0.012)], hip), root)
    kit.parent(thigh, joints.hip)

    out = x + s * 0.071
    top, low = hip.z - 0.04, knee.z + 0.06
    kit.parent(kit.merge(f'ThighDetails{s}', [
        hull(f'ThighPlate{s}', m['plate'], [(out, -0.075, hip.z - 0.03), (out, 0.07, hip.z - 0.03), (out, -0.06, knee.z + 0.06), (out, 0.055, knee.z + 0.06),
                                            (out + s * 0.014, -0.065, hip.z - 0.04), (out + s * 0.014, 0.06, hip.z - 0.04),
                                            (out + s * 0.014, -0.05, knee.z + 0.07), (out + s * 0.014, 0.045, knee.z + 0.07)], 0.004),
        *detail.rivets(f'ThighRivetsF{s}', m['steel_light'], (out + s * 0.015, -0.045, top), (out + s * 0.015, -0.045, low), 5, axis='X'),
        *detail.rivets(f'ThighRivetsB{s}', m['steel_light'], (out + s * 0.015, 0.04, top), (out + s * 0.015, 0.04, low), 5, axis='X'),
        box(f'ThighFront{s}', m['remap'], (0.1, 0.012, 0.06), (x, -0.097, hip.z - 0.12), bevel=0.003, rotation=(math.radians(-6), 0, 0)),
        *detail.hose(f'ThighHose{s}', m['dark'], hip + Vector((s * 0.06, 0.085, -0.02)), hip + Vector((s * 0.075, 0.1, -0.14)),
                     knee + Vector((s * 0.05, 0.06, 0.03)), 0.01),
    ], hip), joints.hip)
    # the hip joint bridges pelvis and thigh
    kit.parent(kit.merge(f'HipJoint{s}', [
        cylinder(f'HipJoint{s}', m['steel'], 0.065, 0.11, hip - Vector((s * 0.04, 0, 0)), rotation=(0, math.pi / 2, 0), segments=16),
        cylinder(f'HipCap{s}', m['remap'], 0.045, 0.012, hip + Vector((s * 0.072, 0, 0.0)), rotation=(0, math.pi / 2, 0), segments=16),
    ], hip), joints.hip)
    # the shin widens down towards the foot, its front leaning forward
    shin = camo(kit.merge(f'Shin{s}', [hull(f'Shin{s}', m['sand'], [
        (x - 0.05, -0.06, knee.z - 0.02), (x + 0.05, -0.06, knee.z - 0.02), (x + 0.05, 0.055, knee.z - 0.02), (x - 0.05, 0.055, knee.z - 0.02),
        (x - 0.065, -0.1, ankle.z + 0.09), (x + 0.065, -0.1, ankle.z + 0.09),
        (x - 0.065, -0.075, ankle.z + 0.05), (x + 0.065, -0.075, ankle.z + 0.05),
        (x + 0.062, 0.065, ankle.z + 0.06), (x - 0.062, 0.065, ankle.z + 0.06)], 0.012)], knee), root)
    kit.parent(shin, joints.knee)
    kit.parent(kit.merge(f'Knee{s}', [
        cylinder(f'KneeJoint{s}', m['steel'], 0.05, 0.15, knee, rotation=(0, math.pi / 2, 0), segments=14),
        # the slanted knee plate, leaning forward over the joint
        hull(f'KneePlate{s}', m['plate'], [(x - 0.06, -0.06, knee.z + 0.075), (x + 0.06, -0.06, knee.z + 0.075),
                                           (x - 0.065, -0.115, knee.z - 0.01), (x + 0.065, -0.115, knee.z - 0.01),
                                           (x - 0.055, -0.085, knee.z - 0.07), (x + 0.055, -0.085, knee.z - 0.07),
                                           (x - 0.06, -0.035, knee.z + 0.0), (x + 0.06, -0.035, knee.z + 0.0)], 0.008),
        box(f'KneeStripe{s}', m['remap'], (0.12, 0.012, 0.02), (x, -0.107, knee.z + 0.02), bevel=0.002, rotation=(math.radians(-58), 0, 0)),
        hull(f'ShinPlate{s}', m['remap'], [(x - 0.045, -0.068, knee.z - 0.09), (x + 0.045, -0.068, knee.z - 0.09),
                                           (x - 0.052, -0.105, ankle.z + 0.1), (x + 0.052, -0.105, ankle.z + 0.1),
                                           (x - 0.045, -0.055, knee.z - 0.09), (x + 0.045, -0.055, knee.z - 0.09),
                                           (x - 0.052, -0.092, ankle.z + 0.1), (x + 0.052, -0.092, ankle.z + 0.1)], 0.004),
        rod(f'Piston{s}', m['steel_light'], knee + Vector((0, 0.07, -0.02)), ankle + Vector((0, 0.065, 0.07)), 0.013),
        rod(f'PistonSleeve{s}', m['steel'], knee + Vector((0, 0.07, -0.02)), knee + Vector((0, 0.07, -0.12)), 0.02),
        rod(f'Piston2{s}', m['steel'], knee + Vector((s * 0.05, 0.045, -0.04)), ankle + Vector((s * 0.05, 0.045, 0.08)), 0.008),
        *detail.grille(f'ShinVent{s}', m['steel'], m['dark'], (x + s * 0.06, -0.015, knee.z - 0.11), 0.06, 0.06, 'X', 4, 0.008),
        *detail.rivets(f'ShinRivets{s}', m['steel_light'], (x - 0.035, -0.105, ankle.z + 0.12), (x + 0.035, -0.105, ankle.z + 0.12), 3),
    ], knee), joints.knee)
    # the foot: a wide flat plate, three toes, a heel spur
    foot = [
        hull(f'Foot{s}', m['plate'], [
            (x - 0.1, -0.13, ankle.z - 0.035), (x + 0.1, -0.13, ankle.z - 0.035), (x + 0.1, 0.12, ankle.z - 0.035), (x - 0.1, 0.12, ankle.z - 0.035),
            (x - 0.085, -0.11, ankle.z + 0.005), (x + 0.085, -0.11, ankle.z + 0.005), (x + 0.085, 0.1, ankle.z + 0.005),
            (x - 0.085, 0.1, ankle.z + 0.005)], 0.008),
        box(f'FootSole{s}', m['pod_dark'], (0.204, 0.254, 0.012), ankle + Vector((0, -0.005, -0.03)), bevel=0.003),
        hull(f'AnkleBlock{s}', m['pod_dark'], [(x - 0.06, -0.07, ankle.z), (x + 0.06, -0.07, ankle.z), (x + 0.06, 0.07, ankle.z), (x - 0.06, 0.07, ankle.z),
                                              (x - 0.05, -0.05, ankle.z + 0.05), (x + 0.05, -0.05, ankle.z + 0.05),
                                              (x + 0.05, 0.055, ankle.z + 0.05), (x - 0.05, 0.055, ankle.z + 0.05)], 0.008),
        cylinder(f'AnkleJoint{s}', m['steel'], 0.035, 0.13, ankle + Vector((0, 0, 0.025)), rotation=(0, math.pi / 2, 0), segments=12),
        hull(f'Heel{s}', m['plate'], [(x - 0.035, 0.11, ankle.z - 0.035), (x + 0.035, 0.11, ankle.z - 0.035), (x - 0.025, 0.2, ankle.z - 0.035),
                                      (x + 0.025, 0.2, ankle.z - 0.035), (x - 0.035, 0.1, ankle.z + 0.01), (x + 0.035, 0.1, ankle.z + 0.01),
                                      (x - 0.02, 0.19, ankle.z - 0.015), (x + 0.02, 0.19, ankle.z - 0.015)], 0.005),
    ]
    for t in (-1, 0, 1):
        a = t * 0.16
        d, n = Vector((math.sin(a), -math.cos(a), 0)), Vector((math.cos(a), math.sin(a), 0))
        base = Vector((x + t * 0.064, -0.12, ankle.z))
        tip = base + d * 0.075
        foot += [
            hull(f'Toe{s}{t}', m['plate'], [base + n * 0.031 + Vector((0, 0, -0.035)), base - n * 0.031 + Vector((0, 0, -0.035)),
                                            base + n * 0.029 + Vector((0, 0, 0.0)), base - n * 0.029 + Vector((0, 0, 0.0)),
                                            tip + n * 0.026 + Vector((0, 0, -0.035)), tip - n * 0.026 + Vector((0, 0, -0.035)),
                                            tip + n * 0.024 + Vector((0, 0, -0.016)), tip - n * 0.024 + Vector((0, 0, -0.016))], 0.005),
            hull(f'Claw{s}{t}', m['steel'], [tip + n * 0.022 + Vector((0, 0, -0.035)), tip - n * 0.022 + Vector((0, 0, -0.035)),
                                             tip + n * 0.02 + Vector((0, 0, -0.016)), tip - n * 0.02 + Vector((0, 0, -0.016)),
                                             tip + d * 0.025 + n * 0.012 + Vector((0, 0, -0.035)), tip + d * 0.025 - n * 0.012 + Vector((0, 0, -0.035)),
                                             tip + d * 0.02 + n * 0.01 + Vector((0, 0, -0.028)), tip + d * 0.02 - n * 0.01 + Vector((0, 0, -0.028))], 0.003),
        ]
    foot += detail.rivets(f'FootRivets{s}', m['steel_light'], (x - 0.075, -0.09, ankle.z + 0.007), (x - 0.075, 0.08, ankle.z + 0.007), 4, axis='Z')
    foot += detail.rivets(f'FootRivetsR{s}', m['steel_light'], (x + 0.075, -0.09, ankle.z + 0.007), (x + 0.075, 0.08, ankle.z + 0.007), 4, axis='Z')
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
