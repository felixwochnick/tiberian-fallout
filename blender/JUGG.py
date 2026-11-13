"""
Tiberian Fallout – GDI Juggernaut (JUGG), after Tiberian Sun Firestorm.

A walking artillery piece: a compact, angular head in desert camouflage (chamfered
corners, sides leaning in, a lit window band in its raked front, swept fins on the
roof's corners, a house-colour number plate on each side, a mast with two antennas at
the back) on a short pelvis and two sturdy legs (slanted knee plates, shins widening
down, wide feet with three spread toes and a heel spur). On the head lies a long
cradle reaching far forward with three long barrels side by side: thick breech
sleeves held by clamps, slim tubes, square muzzle blocks. Two folded spades lie under
the head pointing back like a tail.

Like the original it has to set up to fire: the legs crouch, the spades swing down
behind it into the ground, and the cradle raises its three barrels; set up, the head
with the guns turns towards the target.

Rig: empties, no armature (see walker.py): Body → pelvis, spades, Turret (the head)
→ Cradle (raised when deployed) → Cannon (the three barrels); two legs Hip → Knee →
Ankle.

Nodes the game uses: "Turret" (turns about the vertical when deployed), "Cannon" (the
barrels, tipped towards the target), "Flash0"/"Flash1"/"Flash2" (the barrels' muzzle
flashes, in turn).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle          loop, 2 s: the body breathes, the legs stand
    Walk          loop, 1.4 s (two steps); the root's walkSpeed (glTF extras) is the
                  ground speed in cells per second at which the feet do not slide
    Fire          once, 1 s: the three barrels fire one after another and recoil
    Deploy        once, 2 s: crouch, spades down into the ground, barrels up
    Deployed      loop, 2 s: set up
    FireDeployed  once, 1 s: a salvo set up, heavy recoil, the body jolts
    Undeploy      once, 2 s: Deploy backwards

Run headless:

    blender -b --factory-startup --python blender/JUGG.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; the walker looks along -Y (glTF +Z). The
origin is on the ground between its feet.
"""
import math
import os
import sys

import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402 – start(), finish(), main() (rest poses held in every clip)
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'JUGG.glb')
BLEND = os.path.join(HERE, 'JUGG.blend')

ANKLE_Z = 0.03
THIGH = 0.22
SHIN = 0.22
HIP_Z = ANKLE_Z + THIGH + SHIN
HIP_X = 0.14
WALK_FRAMES = 42
SWING = 0.3
BEND = 0.7
FIRE_FRAMES = 30
DEPLOY_FRAMES = 60
CROUCH = 0.75                                   # hip angle when set up (knee twice that)
DROP = (THIGH + SHIN) * (1 - math.cos(CROUCH))  # how far the body sinks
TURRET = Vector((0, 0.02, HIP_Z + 0.07))        # the head's pivot over the pelvis
LOW, TOP = TURRET.z + 0.01, TURRET.z + 0.31     # the head's bottom and roof
FRONT, BACK = -0.17, 0.23
SIDE = 0.2                                      # half the head's width
GUN = Vector((0, -0.04, TOP + 0.035))           # the cradle's trunnion on the roof
BARREL_Z = GUN.z + 0.03                         # the barrels' axis
BARRELS_X = (-0.075, 0.0, 0.075)
BREECH = (0.07, -0.25)                          # the breech sleeves' ends (y)
BARREL = 0.6                                    # from the breech sleeve's front to the muzzle
RAISE = math.radians(-36)
SPADE_HINGE = Vector((0, 0.2, HIP_Z + 0.02))
SPADES_X = (-0.07, 0.07)
SCALE = 1.04                                    # the whole walker: a little bigger than the Titan

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'pod_dark': material('PodDark', srgb('#2b3036'), 0.6, 0.6),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'flash': material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7),
        'plate': plate_material(),
    })
    return m


def plate_material():
    """The camouflage's sand as a plain colour, recoloured like it (extras): armour plates,
    the cradle and the feet, which need no baked pattern of their own."""
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
    """A convex solid around `points`: chamfered blocks, wedges, fins, armour plates."""
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


def ring(half_x, y0, y1, z, chamfer):
    """The corners of a rectangle with chamfered corners (the head's plan) at height z."""
    return [(sx * half_x, y, z) for sx in (-1, 1) for y in (y0 + chamfer, y1 - chamfer)] + \
           [(sx * (half_x - chamfer), y, z) for sx in (-1, 1) for y in (y0, y1)]


def rod(name, mat, p0, p1, radius, segments=10):
    """A round bar from p0 to p1 (pistons)."""
    p0, p1 = Vector(p0), Vector(p1)
    obj = cylinder(name, mat, radius, (p1 - p0).length, (p0 + p1) / 2, segments=segments)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = (p1 - p0).to_track_quat('Z', 'Y')
    return obj


RAKE = math.atan2(0.06, TOP - LOW - 0.045)     # the head's front leans back above its foot


def front(z):
    """The head's raked front (y) at height z."""
    return FRONT + max(z - LOW - 0.045, 0.0) * math.tan(RAKE)


# --------------------------------------------------------------------------- body

def pelvis(m):
    """The pelvis between the hips (it does not turn) and the turret ring on it."""
    return kit.merge('Pelvis', [
        box('PelvisBlock', m['pod_dark'], (0.2, 0.22, 0.1), (0, 0.0, HIP_Z + 0.01), bevel=0.012),
        *[box(f'HipHousing{s}', m['pod_dark'], (0.05, 0.14, 0.09), (s * 0.115, 0.0, HIP_Z + 0.01), bevel=0.01) for s in (-1, 1)],
        cylinder('Ring', m['steel'], 0.13, 0.03, (TURRET.x, TURRET.y, TURRET.z - 0.0), segments=24),
        box('PelvisBand', m['hazard'], (0.204, 0.02, 0.025), (0, -0.105, HIP_Z + 0.03), bevel=0.003),
        *[box(f'PelvisStripe{k}', m['dark'], (0.02, 0.022, 0.026), (-0.08 + 0.04 * k, -0.106, HIP_Z + 0.03), bevel=0) for k in range(5)],
        hull('PelvisPlate', m['plate'], mirrored(((0.06, -0.11, HIP_Z + 0.0), (0.045, -0.12, HIP_Z - 0.09),
                                                  (0.06, -0.09, HIP_Z + 0.0), (0.045, -0.1, HIP_Z - 0.09))), 0.006),
        box('SpadeMount', m['steel'], (0.2, 0.04, 0.04), (0, SPADE_HINGE.y - 0.02, SPADE_HINGE.z), bevel=0.005),
    ])


def cabin(m, root):
    """The head with its fittings; returns (shell, details), origin on the turret's pivot."""
    mid = LOW + 0.045
    shell = camo(kit.merge('Cabin', [hull('Cabin', m['sand'], [
        *ring(SIDE - 0.03, FRONT + 0.035, BACK - 0.035, LOW, 0.025),
        *ring(SIDE, FRONT, BACK, mid, 0.035),
        *ring(SIDE, front(TOP - 0.075), BACK, TOP - 0.075, 0.035),
        *ring(SIDE - 0.035, front(TOP) + 0.015, BACK - 0.03, TOP, 0.025)], 0.01)], TURRET), root)
    zw = LOW + 0.15
    parts = [
        # the lit window band in the raked front, under a brow
        box('Window', m['window'], (0.24, 0.012, 0.04), (0, front(zw) - 0.004, zw), bevel=0.004, rotation=(-RAKE, 0, 0)),
        box('WindowBrow', m['pod_dark'], (0.28, 0.03, 0.016), (0, front(zw + 0.035) - 0.01, zw + 0.035), bevel=0.004),
        *[box(f'WindowBar{k}', m['steel'], (0.01, 0.016, 0.045), (x, front(zw) - 0.007, zw), bevel=0.002, rotation=(-RAKE, 0, 0))
          for k, x in enumerate((-0.04, 0.04))],
        box('FrontBand', m['remap'], (0.3, 0.012, 0.026), (0, front(LOW + 0.07) - 0.006, LOW + 0.07), bevel=0.003, rotation=(-RAKE, 0, 0)),
        *detail.lamp('HeadlightL', m['dark'], m['lamp_white'], (-0.13, front(zw) - 0.004, zw - 0.005), (0, -1, 0), 0.012),
        *detail.lamp('HeadlightR', m['dark'], m['lamp_white'], (0.13, front(zw) - 0.004, zw - 0.005), (0, -1, 0), 0.012),
        # the roof: a plate, the cheeks carrying the cradle's trunnion, a hatch, the mast
        box('Roof', m['sand_light'], (0.22, 0.26, 0.012), (0, 0.04, TOP + 0.003), bevel=0.004),
        *[hull(f'Cheek{s}', m['pod_dark'], [
            (s * 0.13, GUN.y - 0.06, TOP), (s * 0.155, GUN.y - 0.06, TOP), (s * 0.13, GUN.y + 0.08, TOP), (s * 0.155, GUN.y + 0.08, TOP),
            (s * 0.13, GUN.y - 0.035, GUN.z + 0.025), (s * 0.155, GUN.y - 0.035, GUN.z + 0.025),
            (s * 0.13, GUN.y + 0.035, GUN.z + 0.025), (s * 0.155, GUN.y + 0.035, GUN.z + 0.025)], 0.005) for s in (-1, 1)],
        cylinder('Hatch', m['steel'], 0.035, 0.016, (-0.06, 0.14, TOP + 0.012), segments=16),
        cylinder('HatchLid', m['steel_light'], 0.028, 0.01, (-0.06, 0.14, TOP + 0.024), segments=16),
        hull('Mast', m['pod_dark'], [(0.03, BACK - 0.08, TOP), (0.12, BACK - 0.08, TOP), (0.03, BACK - 0.03, TOP), (0.12, BACK - 0.03, TOP),
                                     (0.035, BACK - 0.07, TOP + 0.13), (0.115, BACK - 0.07, TOP + 0.13), (0.035, BACK - 0.035, TOP + 0.13),
                                     (0.115, BACK - 0.035, TOP + 0.13)], 0.006),
        box('MastWindow', m['window'], (0.05, 0.008, 0.03), (0.075, BACK - 0.083, TOP + 0.09), bevel=0.002),
        beam('AntennaL', m['steel'], (0.05, BACK - 0.05, TOP + 0.13), (0.055, BACK - 0.03, TOP + 0.42), 0.006),
        beam('AntennaR', m['steel'], (0.1, BACK - 0.05, TOP + 0.13), (0.11, BACK - 0.03, TOP + 0.38), 0.006),
        *detail.grille('BackVent', m['steel'], m['dark'], (0, BACK + 0.004, LOW + 0.13), 0.18, 0.09, 'Y', 5, 0.008),
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (-0.12, BACK + 0.004, LOW + 0.2), (0, 1, 0), 0.011),
    ]
    for s in (-1, 1):
        # swept fins: forward ones rising back from the roof's front corners, rear ones
        # pointing back and out
        fx, fy = s * (SIDE - 0.032), front(TOP) + 0.03
        parts += [
            hull(f'FinFront{s}', m['plate'], [
                (fx, fy, TOP - 0.03), (fx + s * 0.014, fy, TOP - 0.03), (fx, fy + 0.12, TOP - 0.03), (fx + s * 0.014, fy + 0.12, TOP - 0.03),
                (fx, fy + 0.15, TOP + 0.085), (fx + s * 0.014, fy + 0.15, TOP + 0.085),
                (fx, fy + 0.11, TOP + 0.085), (fx + s * 0.014, fy + 0.11, TOP + 0.085)], 0.003),
            hull(f'FinBack{s}', m['plate'], [
                (fx, BACK - 0.12, TOP - 0.03), (fx + s * 0.014, BACK - 0.12, TOP - 0.03),
                (fx, BACK - 0.02, TOP - 0.03), (fx + s * 0.014, BACK - 0.02, TOP - 0.03),
                (fx + s * 0.04, BACK + 0.07, TOP + 0.035), (fx + s * 0.054, BACK + 0.07, TOP + 0.035),
                (fx + s * 0.03, BACK + 0.03, TOP + 0.035), (fx + s * 0.044, BACK + 0.03, TOP + 0.035)], 0.003),
            # the number plate on the side, bolted on
            box(f'NumberPlate{s}', m['remap'], (0.012, 0.13, 0.075), (s * (SIDE + 0.005), -0.02, LOW + 0.14), bevel=0.003),
            *detail.rivets(f'PlateRivets{s}', m['steel_light'], (s * (SIDE + 0.012), -0.07, LOW + 0.166), (s * (SIDE + 0.012), 0.03, LOW + 0.166), 4,
                           axis='X'),
            *detail.grille(f'SideVent{s}', m['steel'], m['dark'], (s * (SIDE + 0.002), 0.135, LOW + 0.14), 0.08, 0.06, 'X', 4, 0.008),
            *detail.seam(f'SideSeam{s}', m['seam'], (s * (SIDE + 0.002), 0.065, mid + 0.01), (s * (SIDE + 0.002), 0.065, TOP - 0.08)),
            *detail.rivets(f'SideRivets{s}', m['steel_light'], (s * (SIDE + 0.003), -0.13, TOP - 0.085), (s * (SIDE + 0.003), 0.2, TOP - 0.085), 8,
                           axis='X'),
            box(f'Step{s}', m['steel'], (0.03, 0.06, 0.01), (s * (SIDE - 0.02), 0.16, LOW + 0.012), bevel=0.002),
        ]
    return shell, kit.merge('CabinDetails', parts, TURRET)


def gun(m, turret):
    """Cradle → Cannon with the cradle's tray, the three barrels (each its own object,
    they recoil in turn) and their flashes; returns (cradle, barrels, flashes)."""
    cradle = kit.parent(kit.empty('Cradle', GUN), turret)
    pivot = kit.parent(walker.joint('Cannon', None, GUN), cradle)
    back, nose = BREECH[0] + 0.02, BREECH[1] - 0.05
    tray = [
        # the tray under the barrels, its nose bevelled, side walls with ribs
        hull('Tray', m['plate'], mirrored(((0.125, back, GUN.z - 0.03), (0.125, back, GUN.z + 0.02), (0.125, nose + 0.04, GUN.z - 0.03),
                                           (0.125, nose, GUN.z + 0.02), (0.11, nose, GUN.z - 0.005)))),
        cylinder('GunPin', m['steel_light'], 0.022, 0.32, GUN, rotation=(0, math.pi / 2, 0), segments=12),
        box('TrayBand', m['hazard'], (0.254, 0.03, 0.03), (0, nose + 0.035, GUN.z + 0.0), bevel=0.003),
        *[box(f'TrayStripe{k}', m['dark'], (0.018, 0.032, 0.032), (-0.1 + 0.04 * k, nose + 0.035, GUN.z + 0.0), bevel=0) for k in range(6)],
        *detail.rivets('TrayRivetsL', m['steel_light'], (-0.127, back - 0.03, GUN.z - 0.005), (-0.127, nose + 0.08, GUN.z - 0.005), 6, axis='X'),
        *detail.rivets('TrayRivetsR', m['steel_light'], (0.127, back - 0.03, GUN.z - 0.005), (0.127, nose + 0.08, GUN.z - 0.005), 6, axis='X'),
    ]
    # clamps over the breech sleeves
    for k, y in enumerate((BREECH[0] - 0.06, BREECH[1] + 0.06)):
        tray += [box(f'Clamp{k}', m['pod_dark'], (0.26, 0.028, 0.02), (0, y, BARREL_Z + 0.036), bevel=0.004),
                 *[box(f'ClampPost{k}{s}', m['pod_dark'], (0.016, 0.028, 0.07), (s * 0.122, y, BARREL_Z + 0.005), bevel=0.003) for s in (-1, 1)]]
    kit.parent(kit.merge('GunBlock', tray, GUN), pivot)
    barrels, flashes = [], []
    for k, x in enumerate(BARRELS_X):
        at = Vector((x, BREECH[1], BARREL_Z))
        tip = at - Vector((0, BARREL, 0))
        sleeve = BREECH[0] - BREECH[1]
        parts = [
            cylinder(f'Sleeve{k}', m['plate'], 0.033, sleeve, at + Vector((0, sleeve / 2, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
            cylinder(f'SleeveCap{k}', m['steel'], 0.028, 0.012, at + Vector((0, sleeve + 0.004, 0)), rotation=(math.pi / 2, 0, 0), segments=12),
            cylinder(f'Collar{k}', m['steel'], 0.03, 0.03, at - Vector((0, 0.01, 0)), rotation=(math.pi / 2, 0, 0), segments=12),
            cylinder(f'Tube{k}', m['steel_light'], 0.02, BARREL - 0.06, at - Vector((0, (BARREL - 0.06) / 2, 0)), rotation=(math.pi / 2, 0, 0),
                     segments=12),
            cylinder(f'Band{k}', m['steel'], 0.023, 0.02, at - Vector((0, BARREL * 0.5, 0)), rotation=(math.pi / 2, 0, 0), segments=12),
            box(f'Muzzle{k}', m['pod_dark'], (0.058, 0.07, 0.058), tip + Vector((0, 0.035, 0)), bevel=0.006),
            cylinder(f'Bore{k}', m['dark'], 0.013, 0.004, tip - Vector((0, 0.001, 0)), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
        ]
        barrels.append(kit.parent(kit.merge(f'Barrel{k}', parts, at), pivot))
        muzzle = tip - Vector((0, 0.05, 0))
        flash = kit.merge(f'Flash{k}', [sphere(f'Flash{k}_{j}', m['flash'], 0.045 - 0.012 * j, muzzle - Vector((0, 0.045 * j, 0)), 10)
                                        for j in range(3)], muzzle)
        flash.scale = (kit.HIDDEN,) * 3
        flashes.append(kit.parent(flash, pivot))
    return cradle, barrels, flashes


def spade(m, x):
    """A spade, built set up (down and back into the ground behind the crouching
    walker); origin on its hinge. Returns it and its stowed rotation (pointing back,
    a little up, under the head)."""
    hinge = Vector((x, SPADE_HINGE.y, SPADE_HINGE.z))
    foot = Vector((x, SPADE_HINGE.y + 0.24, 0.02 + DROP))   # on the ground once the body has sunk
    d = foot - hinge
    parts = [
        cylinder(f'SpadeKnuckle{x}', m['steel'], 0.022, 0.06, hinge, rotation=(0, math.pi / 2, 0), segments=10),
        beam(f'SpadeArm{x}', m['pod_dark'], hinge, foot, 0.04, 0.03),
        beam(f'SpadeRam{x}', m['steel_light'], hinge.lerp(foot, 0.15), hinge.lerp(foot, 0.75), 0.016),
        kit.hexahedron(f'SpadeBlade{x}', m['steel_light'], (
            (x - 0.045, foot.y - 0.02, foot.z - 0.02), (x + 0.045, foot.y - 0.02, foot.z - 0.02),
            (x + 0.045, foot.y + 0.03, foot.z - 0.02), (x - 0.045, foot.y + 0.03, foot.z - 0.02),
            (x - 0.05, foot.y - 0.04, foot.z + 0.05), (x + 0.05, foot.y - 0.04, foot.z + 0.05),
            (x + 0.05, foot.y + 0.01, foot.z + 0.06), (x - 0.05, foot.y + 0.01, foot.z + 0.06)), bevel=0.004),
        box(f'SpadeStripe{x}', m['hazard'], (0.044, 0.03, 0.03), hinge.lerp(foot, 0.45), bevel=0.002),
    ]
    obj = kit.merge(f'Spade{"R" if x > 0 else "L"}', parts, hinge)
    return obj, Vector((math.radians(8) - math.atan2(d.z, d.y), 0, 0))


# --------------------------------------------------------------------------- legs

def leg(m, root, name, hip, body):
    """One sturdy leg on its joints, centred under the hip; returns the walker.Leg."""
    joints = walker.Leg(name, body, hip, THIGH, SHIN)
    knee, ankle = hip - Vector((0, 0, THIGH)), hip - Vector((0, 0, THIGH + SHIN))
    x, y = hip.x, hip.y
    s = 1 if x > 0 else -1
    thigh = camo(kit.merge(f'{name}Thigh', [hull(f'{name}Thigh', m['sand'], [
        (x - 0.055, y - 0.065, knee.z + 0.02), (x + 0.055, y - 0.065, knee.z + 0.02), (x + 0.055, y + 0.06, knee.z + 0.02), (x - 0.055, y + 0.06, knee.z + 0.02),
        (x - 0.068, y - 0.095, hip.z - 0.07), (x + 0.068, y - 0.095, hip.z - 0.07),
        (x - 0.068, y - 0.075, hip.z + 0.01), (x + 0.068, y - 0.075, hip.z + 0.01), (x + 0.068, y + 0.08, hip.z + 0.01), (x - 0.068, y + 0.08, hip.z + 0.01)],
        0.012)], hip), root)
    kit.parent(thigh, joints.hip)
    out = x + s * 0.069
    top, low = hip.z - 0.04, knee.z + 0.05
    kit.parent(kit.merge(f'{name}ThighDetails', [
        hull(f'{name}ThighPlate', m['plate'], [(out, y - 0.075, hip.z - 0.02), (out, y + 0.07, hip.z - 0.02), (out, y - 0.06, knee.z + 0.05),
                                               (out, y + 0.055, knee.z + 0.05), (out + s * 0.014, y - 0.065, hip.z - 0.03),
                                               (out + s * 0.014, y + 0.06, hip.z - 0.03), (out + s * 0.014, y - 0.05, knee.z + 0.06),
                                               (out + s * 0.014, y + 0.045, knee.z + 0.06)], 0.004),
        *detail.rivets(f'{name}ThighRivetsF', m['steel_light'], (out + s * 0.015, y - 0.045, top), (out + s * 0.015, y - 0.045, low), 4, axis='X'),
        *detail.rivets(f'{name}ThighRivetsB', m['steel_light'], (out + s * 0.015, y + 0.04, top), (out + s * 0.015, y + 0.04, low), 4, axis='X'),
        cylinder(f'{name}HipJoint', m['steel'], 0.058, 0.1, hip, rotation=(0, math.pi / 2, 0), segments=16),
    ], hip), joints.hip)
    shin = camo(kit.merge(f'{name}Shin', [hull(f'{name}Shin', m['sand'], [
        (x - 0.05, y - 0.06, knee.z - 0.02), (x + 0.05, y - 0.06, knee.z - 0.02), (x + 0.05, y + 0.05, knee.z - 0.02), (x - 0.05, y + 0.05, knee.z - 0.02),
        (x - 0.065, y - 0.095, ankle.z + 0.08), (x + 0.065, y - 0.095, ankle.z + 0.08),
        (x - 0.065, y - 0.075, ankle.z + 0.045), (x + 0.065, y - 0.075, ankle.z + 0.045),
        (x + 0.062, y + 0.06, ankle.z + 0.05), (x - 0.062, y + 0.06, ankle.z + 0.05)], 0.012)], knee), root)
    kit.parent(shin, joints.knee)
    kit.parent(kit.merge(f'{name}Knee', [
        cylinder(f'{name}KneeJoint', m['steel'], 0.045, 0.14, knee, rotation=(0, math.pi / 2, 0), segments=14),
        # the slanted knee plate, leaning forward over the joint
        hull(f'{name}KneePlate', m['plate'], [(x - 0.058, y - 0.055, knee.z + 0.065), (x + 0.058, y - 0.055, knee.z + 0.065),
                                              (x - 0.062, y - 0.105, knee.z - 0.01), (x + 0.062, y - 0.105, knee.z - 0.01),
                                              (x - 0.052, y - 0.078, knee.z - 0.065), (x + 0.052, y - 0.078, knee.z - 0.065),
                                              (x - 0.058, y - 0.03, knee.z), (x + 0.058, y - 0.03, knee.z)], 0.008),
        box(f'{name}KneeStripe', m['remap'], (0.112, 0.012, 0.018), (x, y - 0.098, knee.z + 0.018), bevel=0.002, rotation=(math.radians(-58), 0, 0)),
        hull(f'{name}ShinPlate', m['remap'], [(x - 0.042, y - 0.068, knee.z - 0.085), (x + 0.042, y - 0.068, knee.z - 0.085),
                                              (x - 0.05, y - 0.1, ankle.z + 0.09), (x + 0.05, y - 0.1, ankle.z + 0.09),
                                              (x - 0.042, y - 0.056, knee.z - 0.085), (x + 0.042, y - 0.056, knee.z - 0.085),
                                              (x - 0.05, y - 0.088, ankle.z + 0.09), (x + 0.05, y - 0.088, ankle.z + 0.09)], 0.004),
        rod(f'{name}Piston', m['steel_light'], knee + Vector((0, 0.065, -0.02)), ankle + Vector((0, 0.06, 0.06)), 0.012),
        rod(f'{name}PistonSleeve', m['steel'], knee + Vector((0, 0.065, -0.02)), knee + Vector((0, 0.065, -0.1)), 0.018),
        *detail.grille(f'{name}ShinVent', m['steel'], m['dark'], (x + s * 0.058, y - 0.015, knee.z - 0.1), 0.06, 0.06, 'X', 3, 0.008),
    ], knee), joints.knee)
    # the foot: a wide plate, three toes spread forward, a heel spur
    foot = [
        hull(f'{name}Foot', m['plate'], [
            (x - 0.09, -0.11, ankle.z - 0.03), (x + 0.09, -0.11, ankle.z - 0.03), (x + 0.09, 0.1, ankle.z - 0.03), (x - 0.09, 0.1, ankle.z - 0.03),
            (x - 0.075, -0.09, ankle.z + 0.008), (x + 0.075, -0.09, ankle.z + 0.008), (x + 0.075, 0.085, ankle.z + 0.008),
            (x - 0.075, 0.085, ankle.z + 0.008)], 0.008),
        box(f'{name}FootSole', m['pod_dark'], (0.184, 0.214, 0.01), ankle + Vector((0, -0.005, -0.026)), bevel=0.003),
        hull(f'{name}AnkleBlock', m['pod_dark'], [(x - 0.055, -0.065, ankle.z), (x + 0.055, -0.065, ankle.z), (x + 0.055, 0.065, ankle.z),
                                                  (x - 0.055, 0.065, ankle.z), (x - 0.045, -0.045, ankle.z + 0.045), (x + 0.045, -0.045, ankle.z + 0.045),
                                                  (x + 0.045, 0.05, ankle.z + 0.045), (x - 0.045, 0.05, ankle.z + 0.045)], 0.008),
        cylinder(f'{name}AnkleJoint', m['steel'], 0.032, 0.12, ankle + Vector((0, 0, 0.022)), rotation=(0, math.pi / 2, 0), segments=12),
        hull(f'{name}Heel', m['plate'], [(x - 0.03, 0.09, ankle.z - 0.03), (x + 0.03, 0.09, ankle.z - 0.03), (x - 0.02, 0.18, ankle.z - 0.03),
                                         (x + 0.02, 0.18, ankle.z - 0.03), (x - 0.03, 0.085, ankle.z + 0.01), (x + 0.03, 0.085, ankle.z + 0.01),
                                         (x - 0.016, 0.17, ankle.z - 0.012), (x + 0.016, 0.17, ankle.z - 0.012)], 0.005),
    ]
    for t in (-1, 0, 1):
        a = t * 0.25
        d, n = Vector((math.sin(a), -math.cos(a), 0)), Vector((math.cos(a), math.sin(a), 0))
        base = Vector((x + t * 0.055, -0.1, ankle.z))
        tip = base + d * 0.085
        foot += [
            hull(f'{name}Toe{t}', m['plate'], [base + n * 0.027 + Vector((0, 0, -0.03)), base - n * 0.027 + Vector((0, 0, -0.03)),
                                               base + n * 0.025 + Vector((0, 0, 0.004)), base - n * 0.025 + Vector((0, 0, 0.004)),
                                               tip + n * 0.019 + Vector((0, 0, -0.03)), tip - n * 0.019 + Vector((0, 0, -0.03)),
                                               tip + n * 0.017 + Vector((0, 0, -0.014)), tip - n * 0.017 + Vector((0, 0, -0.014))], 0.005),
            hull(f'{name}Claw{t}', m['steel'], [tip + n * 0.017 + Vector((0, 0, -0.03)), tip - n * 0.017 + Vector((0, 0, -0.03)),
                                                tip + n * 0.015 + Vector((0, 0, -0.014)), tip - n * 0.015 + Vector((0, 0, -0.014)),
                                                tip + d * 0.03 + Vector((0, 0, -0.03)), tip + d * 0.026 + Vector((0, 0, -0.025))], 0.003),
        ]
    kit.parent(kit.merge(f'{name}Foot', foot, ankle), joints.ankle)
    return joints


# --------------------------------------------------------------------------- clips

def recoil(barrels, flashes, clip, frames, kick, step):
    """The barrels fire one after another (`step` frames apart) and recoil."""
    hidden = Vector((kit.HIDDEN,) * 3)
    for k, (barrel, flash) in enumerate(zip(barrels, flashes)):
        rest = barrel.location.copy()
        f = k * step
        kit.keys(barrel, 'location', {0: rest, **({f: rest} if f else {}), f + 2: rest + kick, f + 5: rest + kick, f + 16: rest, frames: rest})
        kit.to_track(barrel, clip)
        on = {0: hidden} if f else {}
        kit.keys(flash, 'scale', {**on, f: Vector((1, 1, 1)), f + 2: Vector((1.3, 1.6, 1.3)), f + 4: hidden, frames: hidden}, 'CONSTANT')
        kit.to_track(flash, clip)
        barrel.location = rest
        flash.scale = hidden


def deploy(body, legs, cradle, spades, barrels, flashes):
    """Deploy, Deployed, FireDeployed and Undeploy (Deploy backwards)."""
    level = Vector((0, 0, 0))
    # the crouch keyed frame by frame: the body sinks exactly as far as the bent legs
    # shorten, so the feet stay on the ground
    def bend(f):
        t = min(max((f - 4) / 30, 0.0), 1.0)
        return CROUCH * t * t * (3 - 2 * t)
    frames = list(range(0, DEPLOY_FRAMES + 1, 2))
    poses = []
    for leg in legs:
        for obj, factor in zip((leg.hip, leg.knee, leg.ankle), (-1, 2, -1)):
            poses.append((obj, 'rotation_euler', {f: Vector((factor * bend(f), 0, 0)) for f in frames}))
    poses.append((body, 'location', {f: Vector((0, 0, -(THIGH + SHIN) * (1 - math.cos(bend(f))))) for f in frames}))
    for k, (obj, stowed) in enumerate(spades):
        poses.append((obj, 'rotation_euler', {0: stowed, 10 + 2 * k: stowed, 34 + 2 * k: level, DEPLOY_FRAMES: level}))
    raised = Vector((RAISE, 0, 0))
    poses.append((cradle, 'rotation_euler', {0: level, 32: level, 56: raised, DEPLOY_FRAMES: raised}))
    for clip, order in (('Deploy', lambda f: f), ('Undeploy', lambda f: DEPLOY_FRAMES - f)):
        for obj, path, frames in poses:
            kit.keys(obj, path, {order(f): v for f, v in frames.items()})
            kit.to_track(obj, clip)
    for clip, frames in (('Deploy', DEPLOY_FRAMES), ('Undeploy', DEPLOY_FRAMES), ('Deployed', kit.IDLE_END)):
        walker.hide(flashes, frames, clip)
    for clip, frames in (('Deployed', kit.IDLE_END), ('FireDeployed', FIRE_FRAMES)):
        for obj, path, keyed in poses:
            if obj is body and clip == 'FireDeployed':
                continue
            walker.hold(obj, path, keyed[DEPLOY_FRAMES], frames, clip)
    # the salvo set up: a heavy recoil, the body jolts back and settles on its spades
    recoil(barrels, flashes, 'FireDeployed', FIRE_FRAMES, Vector((0, 0.08, 0)), 3)
    sunk = Vector((0, 0, -DROP))
    kit.keys(body, 'location', {0: sunk, 3: sunk + Vector((0, 0.012, -0.006)), 12: sunk, FIRE_FRAMES: sunk})
    kit.keys(body, 'rotation_euler', {0: level, 3: Vector((math.radians(-2), 0, 0)), 12: Vector((math.radians(0.4), 0, 0)), 18: level,
                                      FIRE_FRAMES: level})
    kit.to_track(body, 'FireDeployed')


def build():
    root, body = nod.start('GDIJuggernaut', 'Juggernaut', 0.0)
    m = materials()
    kit.parent(pelvis(m), body)
    turret = kit.parent(kit.empty('Turret', TURRET), body)
    for obj in cabin(m, root):
        kit.parent(obj, turret)
    cradle, barrels, flashes = gun(m, turret)
    spades = []
    for x in SPADES_X:
        obj, stowed = spade(m, x)
        spades.append((kit.parent(obj, body), stowed))
    legs = [leg(m, root, f'Leg{"R" if s > 0 else "L"}', Vector((s * HIP_X, 0, HIP_Z)), body) for s in (-1, 1)]
    kit.bake_camo(256)
    for obj, stowed in spades:
        obj.rotation_euler = stowed
    speed = walker.walk(legs, body, [], WALK_FRAMES, SWING, BEND, hidden=flashes)
    walker.idle(body, [], legs, sway=0.006, hidden=flashes)
    recoil(barrels, flashes, 'Fire', FIRE_FRAMES, Vector((0, 0.05, 0)), 4)
    deploy(body, legs, cradle, spades, barrels, flashes)
    walker.rest(body, [body, cradle, *[j for g in legs for j in (g.hip, g.knee, g.ankle)]])
    for obj, stowed in spades:
        obj.rotation_euler = stowed
    for flash in flashes:
        flash.scale = (kit.HIDDEN,) * 3
    root['walkSpeed'] = round(speed, 4)
    nod.finish(root, SCALE)
    print('walk speed', root['walkSpeed'], 'cells/s', flush=True)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [10], 'Fire': [1], 'Deploy': [20, 40, 59], 'FireDeployed': [4]},
             scale=1.7, target=(0, -0.15, 0.45))
