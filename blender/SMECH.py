"""
Tiberian Fallout – GDI Wolverine (SMECH), after Tiberian Sun.

A small walker: a tall, boxy armoured torso in desert camouflage under a hood-like
roof that overhangs the front and slopes back, a dark vision slit with two green
sensor lights in the hood's face and a searchlight on its corner, warning stripes
framing the front plate, armour plates hanging over the hips in front and at the
sides. Big rounded house-colour pads sit on square shoulder blocks; the arms hang
down from them to long camouflaged forearms with a house-colour band that end in
six-barrelled gatling guns, each fed by a golden ammunition belt looping down under
the forearm. At the back a pack with vertical cooling fins and a grid of amber
lights, a whip antenna on the roof. Two sturdy legs: armoured thighs, angular
house-colour knee caps, angular shins widening towards the wide flat feet (two toes
in front, a heel behind).

Rig: empties, no armature (see walker.py): Body → torso and arms, Hip → Knee → Ankle.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle    loop, 2 s: the body breathes, the guns drift
    Walk    loop, 1 s (two steps); the root's walkSpeed (glTF extras) is the ground
            speed in cells per second at which the feet do not slide
    Fire    loop, 0.4 s: the barrels spin, the muzzles flash (not used by the game yet)

Run headless:

    blender -b --factory-startup --python blender/SMECH.py [-- --preview <dir>]

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
OUT = os.path.join(PROJECT, 'public', 'models', 'SMECH.glb')
BLEND = os.path.join(HERE, 'SMECH.blend')

HIP_Z = 0.4
HIP_X = 0.1
THIGH = 0.19
SHIN = 0.18
WALK_FRAMES = 30
SWING = 0.32            # hip swing (radians) either way
BEND = 0.7              # knee bend in the middle of a swing
FIRE_FRAMES = 12
LOW = 0.43              # the torso's bottom
HOOD = 0.7              # where the hood sits on the torso
TOP = 0.8               # the hood's front edge; it slopes back from there
FRONT, BACK = -0.13, 0.14
HALF = 0.165            # half the torso's width
GUN = 0.26              # the guns' distance from the middle (x)
GUN_Z = 0.49
MUZZLE_Y = -0.19        # where the barrels start
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


def octagon(centre, width, height, chamfer, y):
    """A chamfered rectangle across y (the cross-section of a forearm)."""
    cx, cz = centre
    w, h, c = width / 2, height / 2, chamfer
    return [(cx + dx, y, cz + dz) for dx, dz in ((-w + c, -h), (w - c, -h), (w, -h + c), (w, h - c),
                                                 (w - c, h), (-w + c, h), (-w, h - c), (-w, -h + c))]


def dome(name, mat, radius, height, location, rotation=(0, 0, 0), stretch=1.0, segments=16):
    """A rounded cap (half an ellipsoid on a flat base, `stretch` longer along y): the
    shoulder pads."""
    def build(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=8, radius=radius)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -1e-4], context='VERTS')
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary])
        for v in bm.verts:
            v.co.y *= stretch
            v.co.z *= height / radius

    obj = kit.mesh_object(name, build)
    obj.location = location
    obj.rotation_euler = rotation
    return kit.finish(obj, mat, 0.004)


def rod(name, mat, p0, p1, radius, segments=10):
    """A round bar from p0 to p1 (arms, pistons)."""
    p0, p1 = Vector(p0), Vector(p1)
    obj = cylinder(name, mat, radius, (p1 - p0).length, (p0 + p1) / 2, segments=segments)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = (p1 - p0).to_track_quat('Z', 'Y')
    return obj


def stripes(m, name, centre, width, count, height=0.022):
    """A row of warning stripes across the front, yellow and dark in turn."""
    w = width / count
    return [box(f'{name}{k}', m['hazard'] if k % 2 == 0 else m['dark'], (w, 0.01, height),
                centre + Vector((-width / 2 + (k + 0.5) * w, 0, 0)), bevel=0) for k in range(count)]


# --------------------------------------------------------------------------- parts

def torso(m, root):
    """The armoured box under its hood, the shoulder blocks; returns (shell, details)."""
    body = hull('TorsoBody', m['sand'], mirrored((
        (HALF - 0.035, FRONT + 0.035, LOW), (HALF - 0.035, BACK - 0.035, LOW),
        (HALF, FRONT, LOW + 0.05), (HALF, BACK, LOW + 0.05),
        (HALF, FRONT, HOOD + 0.02), (HALF, BACK, HOOD + 0.02))), 0.012)
    # the hood: overhangs the front, its roof slopes back from the front edge
    hood = hull('Hood', m['sand'], mirrored((
        (HALF + 0.008, FRONT - 0.024, HOOD), (HALF + 0.008, BACK + 0.008, HOOD),
        (HALF + 0.008, FRONT - 0.024, TOP - 0.035), (HALF - 0.012, FRONT - 0.006, TOP),
        (HALF - 0.012, BACK - 0.03, TOP - 0.028), (HALF + 0.008, BACK + 0.008, TOP - 0.06))), 0.01)
    parts = [body, hood]
    for s in (-1, 1):  # the square shoulder blocks the pads sit on
        parts.append(hull(f'ShoulderBlock{s}', m['sand'], [
            (s * (HALF - 0.01), -0.085, 0.57), (s * (HALF - 0.01), 0.1, 0.57),
            (s * (HALF + 0.045), -0.075, 0.6), (s * (HALF + 0.045), 0.09, 0.6),
            (s * (HALF + 0.045), -0.075, 0.72), (s * (HALF + 0.045), 0.09, 0.72),
            (s * (HALF - 0.01), -0.085, 0.75), (s * (HALF - 0.01), 0.1, 0.75)], 0.01))
    shell = camo(kit.merge('Torso', parts), root)
    return shell, kit.merge('TorsoDetails', torso_details(m))


def torso_details(m):
    """Slit, sensor lights, searchlight, stripes, pads, hip plates, the back pack, the
    antenna, vents, seams and rivets."""
    face = FRONT - 0.024 - 0.003      # the hood's front face
    plate = FRONT - 0.003             # the front plate under it

    def roof(y):  # the hood's roof (z) at y: it falls 0.028 from front to back
        return TOP + 0.002 - 0.028 * (y - FRONT) / (BACK - FRONT)

    parts = [
        box('Pelvis', m['pod_dark'], (0.24, 0.14, 0.08), (0, 0.01, HIP_Z + 0.01), bevel=0.01),
        # the vision slit across the hood's face, green sensor lights beside it
        box('SlitFrame', m['pod_dark'], (0.22, 0.008, 0.036), (0, face + 0.002, HOOD + 0.033), bevel=0.003),
        box('Slit', m['dark'], (0.19, 0.008, 0.02), (0, face - 0.001, HOOD + 0.033), bevel=0.002),
        *detail.lamp('SensorL', m['dark'], m['lamp_green'], (-0.14, face, HOOD + 0.033), (0, -1, 0), 0.008),
        *detail.lamp('SensorR', m['dark'], m['lamp_green'], (0.14, face, HOOD + 0.033), (0, -1, 0), 0.008),
        # the searchlight on the hood's front right corner
        *detail.lamp('Searchlight', m['steel'], m['lamp_white'], (-0.12, FRONT + 0.005, roof(FRONT + 0.03) + 0.026), (0, -1, 0), 0.02),
        box('SearchlightMount', m['steel'], (0.03, 0.04, 0.02), (-0.12, FRONT + 0.03, roof(FRONT + 0.03) + 0.008), bevel=0.003),
        # roof: two plates, a hatch, the antenna at the back
        box('RoofPlate', m['sand_light'], (0.14, 0.012, 0.012), (0.02, FRONT + 0.03, roof(FRONT + 0.03)), bevel=0.003),
        box('RoofPlate2', m['sand_light'], (0.012, 0.09, 0.012), (0.1, 0.0, roof(0.0)), bevel=0.003),
        cylinder('Hatch', m['steel'], 0.04, 0.016, (-0.05, 0.05, roof(0.05) + 0.004), segments=16),
        cylinder('HatchLid', m['steel_light'], 0.03, 0.01, (-0.05, 0.05, roof(0.05) + 0.014), segments=16),
        box('AntennaBase', m['steel'], (0.03, 0.03, 0.03), (0.09, BACK - 0.04, roof(BACK - 0.04) + 0.01), bevel=0.004),
        beam('Antenna', m['steel'], (0.09, BACK - 0.04, roof(BACK - 0.04)), (0.1, BACK - 0.03, 1.08), 0.006),
        sphere('AntennaTip', m['steel_light'], 0.01, (0.1, BACK - 0.03, 1.08), 8),
        # the back pack: cooling fins and a grid of amber lights
        hull('Pack', m['pod_dark'], mirrored(((0.11, BACK - 0.01, 0.49), (0.09, BACK + 0.055, 0.5),
                                              (0.11, BACK - 0.01, 0.68), (0.09, BACK + 0.055, 0.66))), 0.01),
        *detail.lamp('PackLight', m['dark'], m['lamp_amber'], (0.0, BACK + 0.056, 0.645), (0, 1, 0), 0.008),
    ]
    for k in range(5):
        parts.append(box(f'PackFin{k}', m['steel'], (0.01, 0.012, 0.13), (-0.075 + k * 0.022, BACK + 0.06, 0.56), bevel=0.002))
    for k in range(6):
        parts += detail.lamp(f'PackLamp{k}', m['dark'], m['lamp_amber'], (0.04 + 0.025 * (k % 2), BACK + 0.058, 0.53 + 0.035 * (k // 2)),
                             (0, 1, 0), 0.006)
    # warning stripes framing the front plate
    parts += stripes(m, 'StripeHigh', Vector((0, plate, HOOD - 0.012)), 0.3, 11)
    parts += stripes(m, 'StripeLow', Vector((0, plate, LOW + 0.07)), 0.3, 11)
    parts += detail.seam('FrontSeam', m['seam'], (0.0, plate, LOW + 0.09), (0.0, plate, HOOD - 0.03))
    parts.append(box('FrontHatch', m['sand_light'], (0.1, 0.01, 0.1), (0.06, plate - 0.002, 0.57), bevel=0.003))
    parts.append(box('FrontHatchHandle', m['steel'], (0.04, 0.012, 0.008), (0.06, plate - 0.007, 0.6), bevel=0.002))
    parts += detail.rivets('HatchRivets', m['steel_light'], (0.02, plate - 0.008, 0.53), (0.1, plate - 0.008, 0.53), 4)
    parts += detail.rivets('HoodRivets', m['steel_light'], (-0.15, face - 0.002, HOOD + 0.008), (0.15, face - 0.002, HOOD + 0.008), 9)
    for s in (-1, 1):
        side = s * (HALF + 0.002)
        skirt = s * (HALF + 0.017)  # clear of the thigh plates swinging under it
        parts += [
            # the big rounded pad over the shoulder, tilted outwards
            dome(f'ShoulderPad{s}', m['remap'], 0.095, 0.07, (s * (HALF + 0.04), 0.005, 0.7), (0, s * 0.62, 0), 1.12),
            # the front plate's edges, stripes down its sides
            box(f'StripeSide{s}', m['hazard'], (0.016, 0.01, 0.16), (s * 0.14, plate, 0.585), bevel=0),
            *[box(f'StripeSideDark{s}{k}', m['dark'], (0.017, 0.011, 0.016), (s * 0.14, plate, 0.525 + 0.04 * k), bevel=0) for k in range(4)],
            # armoured plates hanging over the hips
            hull(f'HipPlate{s}', m['plate'], [
                (s * 0.035, FRONT - 0.005, LOW + 0.03), (s * 0.155, FRONT - 0.005, LOW + 0.03),
                (s * 0.035, FRONT - 0.03, LOW - 0.07), (s * 0.15, FRONT - 0.03, LOW - 0.07),
                (s * 0.035, FRONT + 0.01, LOW + 0.03), (s * 0.155, FRONT + 0.01, LOW + 0.03),
                (s * 0.035, FRONT - 0.015, LOW - 0.07), (s * 0.15, FRONT - 0.015, LOW - 0.07)], 0.005),
            hull(f'HipSkirt{s}', m['plate'], [
                (skirt, -0.09, LOW + 0.03), (skirt, 0.1, LOW + 0.03), (skirt + s * 0.01, -0.08, LOW - 0.06), (skirt + s * 0.01, 0.09, LOW - 0.06),
                (skirt + s * 0.012, -0.09, LOW + 0.03), (skirt + s * 0.012, 0.1, LOW + 0.03), (skirt + s * 0.022, -0.08, LOW - 0.06),
                (skirt + s * 0.022, 0.09, LOW - 0.06)], 0.005),
            box(f'SkirtHinge{s}', m['steel'], (0.02, 0.17, 0.014), (s * (HALF + 0.008), 0.005, LOW + 0.025), bevel=0.003),
            *detail.rivets(f'HipPlateRivet{s}', m['steel'], (s * 0.06, FRONT - 0.016, LOW + 0.01), (s * 0.13, FRONT - 0.016, LOW + 0.01), 3),
            # sides: a vent, seams, rivets along the hood
            *detail.grille(f'SideVent{s}', m['steel'], m['dark'], (side, 0.04, 0.5), 0.09, 0.06, 'X', 4, 0.008),
            *detail.seam(f'SideSeam{s}', m['seam'], (side, 0.1, LOW + 0.06), (side, 0.1, 0.56)),
            *detail.seam(f'SideSeamH{s}', m['seam'], (side, -0.12, 0.56), (side, 0.13, 0.56)),
            *detail.rivets(f'HoodSideRivets{s}', m['steel_light'], (s * (HALF + 0.011), -0.13, HOOD + 0.012),
                           (s * (HALF + 0.011), 0.13, HOOD + 0.012), 7, axis='X'),
            *detail.rivets(f'BlockRivets{s}', m['steel_light'], (s * (HALF + 0.047), -0.05, 0.62), (s * (HALF + 0.047), 0.07, 0.62), 4, axis='X'),
        ]
    return parts


def arm(m, root, s, body):
    """An arm with its gatling gun, the belt and the flash; returns (arm joint, barrel
    group, flash)."""
    shoulder = Vector((s * 0.2, 0, 0.66))
    pivot = walker.joint(f'Arm{s}', body, shoulder)
    x = s * GUN
    elbow = Vector((x - s * 0.005, 0.03, GUN_Z + 0.055))
    back, front = 0.075, MUZZLE_Y + 0.035
    # the forearm, camouflaged like the torso
    forearm = hull(f'Forearm{s}', m['sand'], [
        *octagon((x, GUN_Z), 0.085, 0.08, 0.02, back),
        *octagon((x, GUN_Z), 0.1, 0.1, 0.024, back - 0.04),
        *octagon((x, GUN_Z), 0.1, 0.1, 0.024, front + 0.02),
        *octagon((x, GUN_Z), 0.11, 0.11, 0.026, front)], 0.008)
    kit.parent(camo(kit.merge(f'Forearm{s}', [forearm], elbow), root), pivot)
    parts = [
        cylinder(f'ShoulderAxle{s}', m['steel'], 0.035, 0.06, shoulder + Vector((s * 0.02, 0, 0)), rotation=(0, math.pi / 2, 0), segments=12),
        rod(f'UpperArm{s}', m['steel'], shoulder + Vector((s * 0.04, 0, 0)), elbow, 0.03, 12),
        rod(f'UpperArmSleeve{s}', m['steel_light'], shoulder + Vector((s * 0.042, 0, -0.03)), shoulder.lerp(elbow, 0.55) + Vector((s * 0.02, 0, 0)),
            0.036, 12),
        cylinder(f'Elbow{s}', m['pod_dark'], 0.034, 0.08, elbow, rotation=(0, math.pi / 2, 0), segments=12),
        # the gun's housing at the front of the forearm, a sight on top
        cylinder(f'GunHousing{s}', m['pod_dark'], 0.05, 0.05, (x, MUZZLE_Y + 0.02, GUN_Z), rotation=(math.pi / 2, 0, 0), segments=16),
        cylinder(f'GunRing{s}', m['steel'], 0.054, 0.012, (x, MUZZLE_Y + 0.004, GUN_Z), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0),
        box(f'Sight{s}', m['steel'], (0.02, 0.05, 0.02), (x, front + 0.03, GUN_Z + 0.063), bevel=0.003),
        *detail.lamp(f'SightLens{s}', m['dark'], m['lamp_green'], (x, front + 0.003, GUN_Z + 0.063), (0, -1, 0), 0.007),
        # cooling slats on the forearm's top, a vent and an armour band on its outside
        *[box(f'TopSlat{s}{k}', m['dark'], (0.05, 0.008, 0.006), (x, -0.045 + 0.022 * k, GUN_Z + 0.052), bevel=0) for k in range(4)],
        *detail.grille(f'ArmVent{s}', m['steel'], m['dark'], (x + s * 0.051, 0.0, GUN_Z), 0.06, 0.05, 'X', 3, 0.006),
        box(f'ArmBand{s}', m['remap'], (0.112, 0.025, 0.112), (x, front + 0.06, GUN_Z), bevel=0.006),
        *detail.rivets(f'ArmRivets{s}', m['steel_light'], (x + s * 0.052, -0.12, GUN_Z + 0.03), (x + s * 0.052, -0.06, GUN_Z + 0.03), 3, axis='X'),
        box(f'Feeder{s}', m['steel'], (0.04, 0.05, 0.03), (x, -0.07, GUN_Z - 0.058), bevel=0.005),
        box(f'BeltGuide{s}', m['steel'], (0.04, 0.03, 0.025), (x, back - 0.03, GUN_Z - 0.05), bevel=0.004),
        *detail.hose(f'Hose{s}', m['dark'], (x - s * 0.04, 0.05, GUN_Z + 0.03), (s * 0.2, 0.09, GUN_Z + 0.04), (s * 0.19, 0.06, 0.6), 0.009),
    ]
    # the ammunition belt sags from the feeder in a loop back up to the forearm's end
    start, end = Vector((x, -0.07, GUN_Z - 0.075)), Vector((x, back - 0.03, GUN_Z - 0.065))
    sag = Vector((s * 0.008, 0, -0.2))
    points = [(1 - t) ** 3 * start + 3 * (1 - t) ** 2 * t * (start + sag) + 3 * (1 - t) * t * t * (end + sag) + t ** 3 * end
              for t in (k / 18 for k in range(19))]
    for k, (p, q) in enumerate(zip(points, points[1:])):  # cartridges side by side on a band
        link = box(f'Belt{s}_{k}', m['brass'], (0.036, 0.014, (q - p).length * 0.8), (p + q) / 2, bevel=0.002)
        link.rotation_mode = 'QUATERNION'
        link.rotation_quaternion = (q - p).to_track_quat('Z', 'X')
        band = box(f'BeltBand{s}_{k}', m['pod_dark'], (0.04, 0.008, (q - p).length + 0.002), (p + q) / 2, bevel=0)
        band.rotation_mode = 'QUATERNION'
        band.rotation_quaternion = (q - p).to_track_quat('Z', 'X')
        parts += [link, band]
    kit.parent(kit.merge(f'Arm{s}', parts, shoulder), pivot)

    muzzle = Vector((x, MUZZLE_Y, GUN_Z))
    group = walker.joint(f'Barrels{s}', pivot, muzzle)
    barrels = [cylinder(f'Barrel{s}_{k}', m['steel_light'], 0.011, 0.12,
                        muzzle + Vector((0.025 * math.cos(math.pi * k / 3), -0.06, 0.025 * math.sin(math.pi * k / 3))),
                        rotation=(math.pi / 2, 0, 0), segments=8, bevel=0) for k in range(6)]
    barrels += [cylinder(f'BarrelRing{s}{k}', m['steel'], 0.04, 0.014, muzzle + Vector((0, -y, 0)), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0)
                for k, y in enumerate((0.012, 0.1))]
    barrels += [cylinder(f'Spindle{s}', m['dark'], 0.012, 0.13, muzzle + Vector((0, -0.065, 0)), rotation=(math.pi / 2, 0, 0), segments=8, bevel=0)]
    barrels += [cylinder(f'Bore{s}_{k}', m['dark'], 0.006, 0.004,
                         muzzle + Vector((0.025 * math.cos(math.pi * k / 3), -0.121, 0.025 * math.sin(math.pi * k / 3))),
                         rotation=(math.pi / 2, 0, 0), segments=6, bevel=0) for k in range(6)]
    kit.parent(kit.merge(f'Barrels{s}', barrels, muzzle), group)
    tip = muzzle + Vector((0, -0.14, 0))
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
    # the thigh: wider at the hip, its front bevelled back
    thigh = camo(kit.merge(f'Thigh{s}', [hull(f'Thigh{s}', m['sand'], [
        (c - 0.045, -0.055, knee.z + 0.01), (c + 0.045, -0.055, knee.z + 0.01), (c + 0.045, 0.05, knee.z + 0.01), (c - 0.045, 0.05, knee.z + 0.01),
        (c - 0.055, -0.08, hip.z - 0.06), (c + 0.055, -0.08, hip.z - 0.06),
        (c - 0.055, -0.06, hip.z), (c + 0.055, -0.06, hip.z), (c + 0.055, 0.065, hip.z), (c - 0.055, 0.065, hip.z)], 0.01)], hip), root)
    kit.parent(thigh, joints.hip)

    out = c + s * 0.056
    top, low = hip.z - 0.04, knee.z + 0.04
    kit.parent(kit.merge(f'ThighDetails{s}', [
        hull(f'ThighPlate{s}', m['plate'], [(out, -0.06, hip.z - 0.02), (out, 0.05, hip.z - 0.02), (out, -0.05, knee.z + 0.05), (out, 0.04, knee.z + 0.05),
                                            (out + s * 0.012, -0.05, hip.z - 0.03), (out + s * 0.012, 0.04, hip.z - 0.03),
                                            (out + s * 0.012, -0.04, knee.z + 0.06), (out + s * 0.012, 0.03, knee.z + 0.06)], 0.004),
        *detail.rivets(f'ThighRivets{s}', m['steel_light'], (out + s * 0.013, -0.03, top), (out + s * 0.013, -0.03, low), 4, axis='X'),
        *detail.rivets(f'ThighRivetsB{s}', m['steel_light'], (out + s * 0.013, 0.025, top), (out + s * 0.013, 0.025, low), 4, axis='X'),
        box(f'ThighFront{s}', m['remap'], (0.08, 0.012, 0.05), (c, -0.078, hip.z - 0.085), bevel=0.003, rotation=(math.radians(-8), 0, 0)),
    ], hip), joints.hip)
    # the hip joint bridges pelvis and thigh
    kit.parent(kit.merge(f'HipJoint{s}', [cylinder(f'HipJoint{s}', m['steel'], 0.048, 0.08, hip - Vector((s * 0.03, 0, 0)),
                                                   rotation=(0, math.pi / 2, 0), segments=14)], hip), joints.hip)
    # the shin: angular, widening down towards the foot, its front leaning forward
    shin = camo(kit.merge(f'Shin{s}', [hull(f'Shin{s}', m['sand'], [
        (c - 0.045, -0.055, knee.z - 0.005), (c + 0.045, -0.055, knee.z - 0.005), (c + 0.045, 0.045, knee.z - 0.005), (c - 0.045, 0.045, knee.z - 0.005),
        (c - 0.058, -0.085, ankle.z + 0.07), (c + 0.058, -0.085, ankle.z + 0.07),
        (c - 0.058, -0.06, ankle.z + 0.035), (c + 0.058, -0.06, ankle.z + 0.035),
        (c + 0.055, 0.055, ankle.z + 0.04), (c - 0.055, 0.055, ankle.z + 0.04)], 0.01)], knee), root)
    kit.parent(shin, joints.knee)
    kit.parent(kit.merge(f'Knee{s}', [
        cylinder(f'KneeJoint{s}', m['steel'], 0.036, 0.11, knee, rotation=(0, math.pi / 2, 0), segments=12),
        # an angular knee cap in the house colour
        hull(f'KneePad{s}', m['remap'], [(c - 0.04, -0.05, knee.z + 0.04), (c + 0.04, -0.05, knee.z + 0.04),
                                         (c - 0.045, -0.085, knee.z), (c + 0.045, -0.085, knee.z),
                                         (c - 0.04, -0.065, knee.z - 0.05), (c + 0.04, -0.065, knee.z - 0.05),
                                         (c - 0.04, -0.03, knee.z), (c + 0.04, -0.03, knee.z)], 0.006),
        # a plate down the shin's front
        hull(f'ShinPlate{s}', m['plate'], [(c - 0.035, -0.062, knee.z - 0.06), (c + 0.035, -0.062, knee.z - 0.06),
                                           (c - 0.045, -0.09, ankle.z + 0.065), (c + 0.045, -0.09, ankle.z + 0.065),
                                           (c - 0.035, -0.05, knee.z - 0.06), (c + 0.035, -0.05, knee.z - 0.06),
                                           (c - 0.045, -0.078, ankle.z + 0.065), (c + 0.045, -0.078, ankle.z + 0.065)], 0.004),
        rod(f'Piston{s}', m['steel_light'], knee + Vector((0, 0.05, -0.02)), ankle + Vector((0, 0.05, 0.06)), 0.01),
        rod(f'PistonSleeve{s}', m['steel'], knee + Vector((0, 0.05, -0.02)), knee + Vector((0, 0.05, -0.09)), 0.015),
        *detail.grille(f'ShinVent{s}', m['steel'], m['dark'], (c + s * 0.052, -0.005, knee.z - 0.07), 0.05, 0.05, 'X', 3, 0.006),
        *detail.rivets(f'ShinRivets{s}', m['steel_light'], (c - 0.025, -0.07, knee.z - 0.075), (c + 0.025, -0.07, knee.z - 0.075), 3),
    ], knee), joints.knee)
    # the foot: a wide flat plate, two toes with a gap between them, a heel
    foot = [
        hull(f'Foot{s}', m['plate'], [
            (c - 0.075, -0.12, ankle.z - 0.03), (c + 0.075, -0.12, ankle.z - 0.03), (c + 0.075, 0.1, ankle.z - 0.03), (c - 0.075, 0.1, ankle.z - 0.03),
            (c - 0.065, -0.1, ankle.z + 0.002), (c + 0.065, -0.1, ankle.z + 0.002), (c + 0.065, 0.085, ankle.z + 0.002),
            (c - 0.065, 0.085, ankle.z + 0.002)], 0.006),
        box(f'FootSole{s}', m['pod_dark'], (0.154, 0.224, 0.01), ankle + Vector((0, -0.01, -0.026)), bevel=0.003),
        hull(f'AnkleBlock{s}', m['pod_dark'], [(c - 0.045, -0.06, ankle.z), (c + 0.045, -0.06, ankle.z), (c + 0.045, 0.06, ankle.z), (c - 0.045, 0.06, ankle.z),
                                              (c - 0.04, -0.04, ankle.z + 0.035), (c + 0.04, -0.04, ankle.z + 0.035),
                                              (c + 0.04, 0.045, ankle.z + 0.035), (c - 0.04, 0.045, ankle.z + 0.035)], 0.006),
        cylinder(f'AnkleJoint{s}', m['steel'], 0.026, 0.1, ankle + Vector((0, 0, 0.016)), rotation=(0, math.pi / 2, 0), segments=10),
        box(f'Heel{s}', m['plate'], (0.09, 0.05, 0.03), ankle + Vector((0, 0.115, -0.015)), bevel=0.006),
        box(f'ToeGap{s}', m['steel'], (0.02, 0.07, 0.02), ankle + Vector((0, -0.15, -0.019)), bevel=0.003),
    ]
    for t in (-1, 1):
        foot += [
            hull(f'Toe{s}{t}', m['plate'], [(c + t * 0.015, -0.115, ankle.z - 0.03), (c + t * 0.072, -0.115, ankle.z - 0.03),
                                            (c + t * 0.015, -0.19, ankle.z - 0.03), (c + t * 0.068, -0.19, ankle.z - 0.03),
                                            (c + t * 0.015, -0.115, ankle.z + 0.002), (c + t * 0.07, -0.115, ankle.z + 0.002),
                                            (c + t * 0.015, -0.17, ankle.z - 0.006), (c + t * 0.066, -0.17, ankle.z - 0.006)], 0.005),
            box(f'Claw{s}{t}', m['steel'], (0.05, 0.016, 0.014), ankle + Vector((t * 0.043, -0.195, -0.022)), bevel=0.003),
        ]
    foot += detail.rivets(f'FootRivets{s}', m['steel_light'], (c - 0.05, -0.08, ankle.z + 0.004), (c - 0.05, 0.07, ankle.z + 0.004), 3, axis='Z')
    foot += detail.rivets(f'FootRivetsR{s}', m['steel_light'], (c + 0.05, -0.08, ankle.z + 0.004), (c + 0.05, 0.07, ankle.z + 0.004), 3, axis='Z')
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
        pivot, group, flash = arm(m, root, s, body)
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
