"""
Tiberian Fallout – GDI Mammoth Mk. II (HMEC), after Tiberian Sun.

GDI's heaviest walker, on four legs: a long, low hull in desert camouflage with an
armoured cockpit in its nose (a lit vision slit under a brow), vents and stowage on
the flanks, house-colour bands along its sides. On top a flat gun house that turns:
the two long railguns lie side by side along it, their coils glowing blue, and a
missile pod hangs on each side of it with six tubes in front and a house-colour cap
on its front edge. Four heavy legs with armoured thighs and shins, big knee joints
with pistons, house-colour shin plates and broad feet with three toes.

Rig: empties, no armature (see walker.py): Body → hull, Turret (the gun house with
the pods) → Cannon (the railguns); four legs Hip → Knee → Ankle. The legs walk in a
trot: the diagonal pairs (front left with back right) step together.

Nodes the game uses: "Turret" (turns about the vertical), "Cannon" (the railguns,
tipped towards the target), "Flash0"/"Flash1" (the railguns' muzzle flashes, in
turn).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle    loop, 2 s: the body breathes, the legs stand
    Walk    loop, 1.6 s (two heavy steps of each pair); the root's walkSpeed (glTF
            extras) is the ground speed in cells per second at which the feet do
            not slide
    Fire    once, 1 s: both railguns fire, their barrels recoil, the muzzles flash
            blue, the body rocks back

Run headless:

    blender -b --factory-startup --python blender/HMEC.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; the walker looks along -Y (glTF +Z). The
origin is on the ground under the middle of the hull.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402 – start(), finish(), main() (rest poses held in every clip)
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'HMEC.glb')
BLEND = os.path.join(HERE, 'HMEC.blend')

ANKLE_Z = 0.03
THIGH = 0.23
SHIN = 0.23
HIP_Z = ANKLE_Z + THIGH + SHIN
HIP_X = 0.25
HIP_Y = 0.3                             # front and back hips (±)
WALK_FRAMES = 48
SWING = 0.24
BEND = 0.6
FIRE_FRAMES = 30
LOW, TOP = HIP_Z - 0.04, HIP_Z + 0.2    # the hull's bottom and roof
NOSE, TAIL = -0.5, 0.46
TURRET = Vector((0, 0.06, TOP))         # the gun house's pivot on the roof
HOUSE_TOP = TOP + 0.13
CANNON = Vector((0, 0.12, HOUSE_TOP + 0.06))  # the railguns' trunnion
RAILS_X = 0.085
RAIL = 0.92                             # from the trunnion to the muzzle
POD_X = 0.27
SCALE = 1.1

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'pod_dark': material('PodDark', srgb('#2b3036'), 0.6, 0.6),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'coil': material('RailCoil', srgb('#1d3550'), 0.3, 0.6, emission=srgb('#4fb4ff'), strength=2.5),
        'flash': material('GlowRail', (0, 0, 0), 1.0, emission=srgb('#59b8ff'), strength=7, alpha=0.75),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


# --------------------------------------------------------------------------- hull

def side(z):
    """The hull's flank (x) at height z: it leans in towards the roof."""
    return 0.27 - (z - LOW) / (TOP - LOW) * 0.05


def hull(m, root):
    """The long hull with the cockpit in its nose; returns (shell, details)."""
    shell = camo(kit.merge('Hull', [
        kit.hexahedron('Hull', m['sand'], (
            (-0.27, NOSE + 0.08, LOW), (0.27, NOSE + 0.08, LOW), (0.27, TAIL, LOW), (-0.27, TAIL, LOW),
            (-0.22, NOSE + 0.14, TOP), (0.22, NOSE + 0.14, TOP), (0.22, TAIL - 0.04, TOP), (-0.22, TAIL - 0.04, TOP)), bevel=0.018),
        # the cockpit, a wedge in the nose
        kit.hexahedron('Cockpit', m['sand'], (
            (-0.17, NOSE, LOW + 0.02), (0.17, NOSE, LOW + 0.02), (0.17, NOSE + 0.12, LOW), (-0.17, NOSE + 0.12, LOW),
            (-0.14, NOSE + 0.06, TOP - 0.03), (0.14, NOSE + 0.06, TOP - 0.03), (0.14, NOSE + 0.18, TOP - 0.01), (-0.14, NOSE + 0.18, TOP - 0.01)),
            bevel=0.014),
    ]), root)
    front_y = NOSE + 0.03  # the cockpit's front face, about the slit's height
    parts = [
        box('Belly', m['pod_dark'], (0.42, 0.8, 0.06), (0, 0.0, LOW - 0.01), bevel=0.012),
        box('Slit', m['window'], (0.22, 0.03, 0.03), (0, front_y + 0.002, LOW + 0.1), bevel=0.004, rotation=(math.radians(-25), 0, 0)),
        box('Brow', m['pod_dark'], (0.26, 0.04, 0.02), (0, front_y + 0.02, LOW + 0.13), bevel=0.004, rotation=(math.radians(-25), 0, 0)),
        box('NoseBand', m['remap'], (0.3, 0.02, 0.03), (0, NOSE + 0.005, LOW + 0.045), bevel=0.003),
        box('RoofPlate', m['sand_light'], (0.36, 0.5, 0.012), (0, 0.06, TOP + 0.004), bevel=0.004),
        box('TailPlate', m['pod_dark'], (0.4, 0.02, 0.14), (0, TAIL + 0.004, LOW + 0.1), bevel=0.004),
        *detail.grille('TailVent', m['steel'], m['dark'], (0, TAIL + 0.016, LOW + 0.1), 0.24, 0.08, 'Y', 5, 0.008),
        *detail.lamp('TailLightL', m['dark'], m['lamp_red'], (-0.17, TAIL + 0.016, LOW + 0.14), (0, 1, 0), 0.012),
        *detail.lamp('TailLightR', m['dark'], m['lamp_red'], (0.17, TAIL + 0.016, LOW + 0.14), (0, 1, 0), 0.012),
        beam('Antenna', m['steel'], (0.17, TAIL - 0.08, TOP), (0.19, TAIL, TOP + 0.45), 0.007),
        box('AntennaBase', m['steel'], (0.04, 0.04, 0.03), (0.17, TAIL - 0.08, TOP + 0.01), bevel=0.004),
        # the turret ring
        cylinder('Ring', m['steel'], 0.2, 0.02, (TURRET.x, TURRET.y, TOP + 0.01), segments=24),
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.12, NOSE - 0.002, LOW + 0.05), (0, -1, 0), 0.014),
            # house-colour bands along the flanks, between the hips
            box(f'SideBand{s}', m['remap'], (0.012, 0.36, 0.035), (s * (side(LOW + 0.06) + 0.003), 0.0, LOW + 0.06), bevel=0.003,
                rotation=(0, -s * 0.24, 0)),
            *detail.grille(f'SideVent{s}', m['steel'], m['dark'], (s * (side(LOW + 0.13) + 0.004), -0.02, LOW + 0.13), 0.14, 0.06, 'X', 4, 0.008),
            box(f'Stowage{s}', m['olive'], (0.05, 0.16, 0.06), (s * (side(LOW + 0.13) + 0.02), 0.25, LOW + 0.13), bevel=0.008),
            *[box(f'StowageStrap{s}{k}', m['dark'], (0.054, 0.008, 0.064), (s * (side(LOW + 0.13) + 0.02), 0.21 + 0.08 * k, LOW + 0.13), bevel=0)
              for k in range(2)],
            *detail.rivets(f'RoofRivets{s}', m['steel_light'], (s * 0.2, NOSE + 0.2, TOP + 0.004), (s * 0.2, TAIL - 0.08, TOP + 0.004), 9, axis='Z'),
            *detail.seam(f'FlankSeam{s}', m['seam'], (s * (side(LOW + 0.1) + 0.002), -0.3, LOW + 0.1), (s * (side(LOW + 0.1) + 0.002), -0.3, TOP - 0.02)),
            # the hips' housings under the flanks
            box(f'HipHousingF{s}', m['pod_dark'], (0.06, 0.16, 0.1), (s * 0.235, -HIP_Y, HIP_Z + 0.01), bevel=0.01),
            box(f'HipHousingB{s}', m['pod_dark'], (0.06, 0.16, 0.1), (s * 0.235, HIP_Y, HIP_Z + 0.01), bevel=0.01),
        ]
    return shell, kit.merge('HullDetails', parts)


# --------------------------------------------------------------------------- guns

def gun_house(m, root):
    """The flat gun house on the turret ring, its trunnion block and the two pods;
    returns the objects, origin on the pivot."""
    z0, z1 = TOP + 0.02, HOUSE_TOP
    shell = camo(kit.merge('GunHouse', [kit.hexahedron('GunHouse', m['sand'], (
        (-0.2, -0.2, z0), (0.2, -0.2, z0), (0.2, 0.34, z0), (-0.2, 0.34, z0),
        (-0.17, -0.14, z1), (0.17, -0.14, z1), (0.17, 0.32, z1), (-0.17, 0.32, z1)), bevel=0.014)], TURRET), root)
    parts = [
        # the trunnion block between the rails
        box('Trunnion', m['pod_dark'], (0.08, 0.2, 0.08), (0, CANNON.y, HOUSE_TOP + 0.03), bevel=0.01),
        *[box(f'TrunnionCheek{s}', m['pod_dark'], (0.03, 0.14, 0.09), (s * (RAILS_X + 0.065), CANNON.y, HOUSE_TOP + 0.035), bevel=0.006)
          for s in (-1, 1)],
        cylinder('Cupola', m['steel'], 0.045, 0.03, (0.0, 0.27, HOUSE_TOP + 0.012), segments=16),
        cylinder('CupolaHatch', m['steel_light'], 0.034, 0.012, (0.0, 0.27, HOUSE_TOP + 0.03), segments=16),
        box('HouseBand', m['remap'], (0.36, 0.014, 0.03), (0, -0.172, (z0 + z1) / 2), bevel=0.003, rotation=(math.radians(-25), 0, 0)),
        *detail.grille('HouseVent', m['steel'], m['dark'], (0, 0.337, (z0 + z1) / 2), 0.2, 0.06, 'Y', 4, 0.008),
    ]
    pods = []
    for s in (-1, 1):
        x = s * POD_X
        z = HOUSE_TOP - 0.01
        parts += [
            # the arm from the house to the pod
            cylinder(f'PodArm{s}', m['steel'], 0.035, 0.1, (s * 0.21, 0.06, z), rotation=(0, math.pi / 2, 0), segments=12),
            box(f'PodFace{s}', m['pod_dark'], (0.11, 0.012, 0.15), (x, -0.136, z), bevel=0.004),
            # its house-colour cap over the front edge, as in the original
            kit.hexahedron(f'PodCap{s}', m['remap'], (
                (x - 0.064, -0.126, z + 0.04), (x + 0.064, -0.126, z + 0.04), (x + 0.064, -0.04, z + 0.04), (x - 0.064, -0.04, z + 0.04),
                (x - 0.064, -0.118, z + 0.088), (x + 0.064, -0.118, z + 0.088), (x + 0.064, -0.04, z + 0.088), (x - 0.064, -0.04, z + 0.088)),
                bevel=0.006),
            box(f'PodStripe{s}', m['hazard'], (0.008, 0.18, 0.02), (x + s * 0.062, 0.06, z - 0.04), bevel=0.002),
            *detail.rivets(f'PodRivets{s}', m['steel_light'], (x + s * 0.062, -0.08, z + 0.02), (x + s * 0.062, 0.2, z + 0.02), 6, axis='X'),
        ]
        pods.append(camo(kit.merge(f'Pod{s}', [kit.hexahedron(f'Pod{s}', m['sand'], (
            (x - 0.06, -0.13, z - 0.08), (x + 0.06, -0.13, z - 0.08), (x + 0.06, 0.24, z - 0.08), (x - 0.06, 0.24, z - 0.08),
            (x - 0.06, -0.12, z + 0.08), (x + 0.06, -0.12, z + 0.08), (x + 0.06, 0.22, z + 0.08), (x - 0.06, 0.22, z + 0.08)), bevel=0.012)],
            TURRET), root))
        for k in range(6):  # six tubes in front, two rows
            tx, tz = x - 0.032 + 0.032 * (k % 3), z - 0.045 + 0.05 * (k // 3)
            parts += [cylinder(f'PodTube{s}{k}', m['steel'], 0.016, 0.03, (tx, -0.14, tz), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
                      cylinder(f'PodHole{s}{k}', m['dark'], 0.011, 0.004, (tx, -0.156, tz), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0)]
    return [shell, *pods, kit.merge('GunHouseDetails', parts, TURRET)]


def railgun(m, root, s, pivot):
    """One railgun on the Cannon: a long camouflaged housing, the rails' slot along its
    flank with the glowing coils, a dark muzzle; its group "Rail…" has its origin on
    the trunnion axis (it recoils along +Y)."""
    x = s * RAILS_X
    at = Vector((x, CANNON.y, CANNON.z))
    tip = at - Vector((0, RAIL, 0))
    group = kit.parent(walker.joint(f'Rail{"R" if s > 0 else "L"}', None, at), pivot)
    shell = camo(kit.merge(f'RailHousing{s}', [kit.hexahedron(f'RailHousing{s}', m['sand'], (
        (x - 0.045, tip.y + 0.03, at.z - 0.045), (x + 0.045, tip.y + 0.03, at.z - 0.045), (x + 0.045, at.y + 0.14, at.z - 0.045),
        (x - 0.045, at.y + 0.14, at.z - 0.045),
        (x - 0.04, tip.y + 0.06, at.z + 0.045), (x + 0.04, tip.y + 0.06, at.z + 0.045), (x + 0.04, at.y + 0.12, at.z + 0.045),
        (x - 0.04, at.y + 0.12, at.z + 0.045)), bevel=0.01)], at), root)
    kit.parent(shell, group)
    length = at.y + 0.1 - tip.y
    parts = [
        box(f'RailBand{s}', m['remap'], (0.096, 0.04, 0.096), at + Vector((0, 0.06, 0)), bevel=0.004),
        box(f'RailTop{s}', m['sand_light'], (0.06, RAIL * 0.55, 0.008), at - Vector((0, RAIL * 0.4, -0.047)), bevel=0.002),
        # the muzzle: a dark block with the bore between the rail ends
        box(f'RailMuzzle{s}', m['pod_dark'], (0.096, 0.05, 0.096), tip + Vector((0, 0.02, 0)), bevel=0.01),
        *[box(f'RailEnd{s}{t}', m['steel_light'], (0.016, 0.03, 0.08), tip + Vector((t * 0.024, -0.016, 0)), bevel=0.003) for t in (-1, 1)],
        box(f'RailBore{s}', m['coil'], (0.03, 0.006, 0.05), tip - Vector((0, 0.005, 0)), bevel=0),
        *detail.rivets(f'RailRivets{s}', m['steel_light'], (x, tip.y + 0.12, at.z + 0.049), (x, at.y - 0.1, at.z + 0.049), 8, axis='Z'),
    ]
    # the slot along the outer flank with its coils, glowing blue
    o = x + s * 0.046
    parts.append(box(f'RailSlot{s}', m['dark'], (0.006, length - 0.2, 0.04), Vector((o, (tip.y + at.y) / 2 + 0.02, at.z)), bevel=0))
    for k in range(7):
        y = tip.y + 0.12 + k * (length - 0.28) / 6
        parts.append(box(f'Coil{s}{k}', m['coil'], (0.01, 0.03, 0.034), Vector((o + s * 0.001, y, at.z)), bevel=0.002))
    kit.parent(kit.merge(f'RailDetails{s}', parts, at), group)
    return group


def guns(m, root, body):
    """Turret → gun house, pods, Cannon → the two railguns and their flashes; returns
    (turret, rails, flashes)."""
    turret = kit.parent(kit.empty('Turret', TURRET), body)
    for obj in gun_house(m, root):
        kit.parent(obj, turret)
    pivot = kit.parent(walker.joint('Cannon', None, CANNON), turret)
    rails, flashes = [], []
    for k, s in enumerate((-1, 1)):
        rails.append(railgun(m, root, s, pivot))
        muzzle = Vector((s * RAILS_X, CANNON.y - RAIL - 0.05, CANNON.z + 0.005))
        flash = kit.merge(f'Flash{k}', [sphere(f'Flash{k}_{j}', m['flash'], 0.05 - 0.012 * j, muzzle - Vector((0, 0.05 * j, 0)), 10)
                                        for j in range(3)], muzzle)
        flash.scale = (kit.HIDDEN,) * 3
        flashes.append(kit.parent(flash, pivot))
    return turret, rails, flashes


# --------------------------------------------------------------------------- legs

def leg(m, root, name, hip, body):
    """One heavy leg on its joints, centred under the hip; returns the walker.Leg."""
    joints = walker.Leg(name, body, hip, THIGH, SHIN)
    knee, ankle = hip - Vector((0, 0, THIGH)), hip - Vector((0, 0, THIGH + SHIN))
    x, y = hip.x, hip.y
    s = 1 if x > 0 else -1
    thigh = camo(kit.merge(f'{name}Thigh', [kit.hexahedron(f'{name}Thigh', m['sand'], (
        (x - 0.055, y - 0.065, knee.z + 0.02), (x + 0.055, y - 0.065, knee.z + 0.02), (x + 0.055, y + 0.055, knee.z + 0.02), (x - 0.055, y + 0.055, knee.z + 0.02),
        (x - 0.065, y - 0.085, hip.z - 0.02), (x + 0.065, y - 0.085, hip.z - 0.02), (x + 0.065, y + 0.075, hip.z - 0.02), (x - 0.065, y + 0.075, hip.z - 0.02)),
        bevel=0.014)], hip), root)
    kit.parent(thigh, joints.hip)
    top, low = hip.z - 0.04, knee.z + 0.05
    ox = x + s * 0.062
    kit.parent(kit.merge(f'{name}ThighDetails', [
        box(f'{name}ThighPlate', m['sand_light'], (0.09, 0.012, 0.08), (x, y - 0.083, hip.z - 0.09), bevel=0.003),
        *detail.rivets(f'{name}ThighRivetsF', m['steel_light'], (ox, y - 0.045, top), (ox, y - 0.045, low), 4, axis='X'),
        *detail.rivets(f'{name}ThighRivetsB', m['steel_light'], (ox, y + 0.045, top), (ox, y + 0.045, low), 4, axis='X'),
        cylinder(f'{name}HipJoint', m['steel'], 0.055, 0.09, hip, rotation=(0, math.pi / 2, 0), segments=16),
    ], hip), joints.hip)
    shin = camo(kit.merge(f'{name}Shin', [kit.hexahedron(f'{name}Shin', m['sand'], (
        (x - 0.06, y - 0.075, ankle.z + 0.05), (x + 0.06, y - 0.075, ankle.z + 0.05), (x + 0.06, y + 0.055, ankle.z + 0.05), (x - 0.06, y + 0.055, ankle.z + 0.05),
        (x - 0.05, y - 0.065, knee.z - 0.01), (x + 0.05, y - 0.065, knee.z - 0.01), (x + 0.05, y + 0.045, knee.z - 0.01), (x - 0.05, y + 0.045, knee.z - 0.01)),
        bevel=0.014)], knee), root)
    kit.parent(shin, joints.knee)
    kit.parent(kit.merge(f'{name}Knee', [
        cylinder(f'{name}KneeJoint', m['steel'], 0.045, 0.14, knee, rotation=(0, math.pi / 2, 0), segments=14),
        box(f'{name}KneeCap', m['pod_dark'], (0.1, 0.05, 0.08), knee + Vector((0, -0.07, 0.0)), bevel=0.012),
        box(f'{name}ShinPlate', m['remap'], (0.09, 0.02, 0.1), knee + Vector((0, -0.077, -0.11)), bevel=0.006, rotation=(math.radians(-3), 0, 0)),
        beam(f'{name}Piston', m['steel_light'], knee + Vector((0, 0.06, -0.02)), ankle + Vector((0, 0.055, 0.07)), 0.02),
        beam(f'{name}PistonSleeve', m['steel'], knee + Vector((0, 0.057, -0.02)), knee + Vector((0, 0.057, -0.1)), 0.03),
        *detail.grille(f'{name}ShinVent', m['steel'], m['dark'], (x + s * 0.058, y - 0.01, knee.z - 0.11), 0.06, 0.06, 'X', 3, 0.008),
        box(f'{name}AnkleGuard', m['pod_dark'], (0.11, 0.03, 0.05), ankle + Vector((0, -0.082, 0.06)), bevel=0.006),
    ], knee), joints.knee)
    foot = [
        box(f'{name}Foot', m['pod_dark'], (0.14, 0.18, 0.045), ankle + Vector((0, -0.02, -0.008)), bevel=0.01),
        box(f'{name}Heel', m['steel'], (0.07, 0.07, 0.035), ankle + Vector((0, 0.1, -0.013)), bevel=0.008),
        cylinder(f'{name}AnkleJoint', m['steel'], 0.032, 0.11, ankle + Vector((0, 0, 0.02)), rotation=(0, math.pi / 2, 0), segments=12),
    ]
    for t in (-1, 0, 1):
        foot.append(box(f'{name}Toe{t}', m['steel'], (0.04, 0.09, 0.035), ankle + Vector((t * 0.045, -0.135, -0.013)), bevel=0.008, rotation=(0, 0, t * 0.2)))
        foot.append(box(f'{name}Claw{t}', m['dark'], (0.03, 0.035, 0.022), ankle + Vector((t * 0.055, -0.19, -0.02)), bevel=0.005,
                        rotation=(math.radians(-15), 0, t * 0.2)))
    kit.parent(kit.merge(f'{name}Foot', foot, ankle), joints.ankle)
    return joints


# --------------------------------------------------------------------------- model

def fire(body, rails, flashes):
    """The Fire clip: both railguns fire, recoil and run out again, the body rocks back."""
    kick = Vector((0, 0.06, 0))
    for k, rail in enumerate(rails):
        rest = rail.location.copy()
        kit.keys(rail, 'location', {0: rest, 2 + k: rest + kick, 6 + k: rest + kick, 22: rest, FIRE_FRAMES: rest})
        kit.to_track(rail, 'Fire')
        rail.location = rest
    hidden = Vector((kit.HIDDEN,) * 3)
    for k, flash in enumerate(flashes):
        kit.keys(flash, 'scale', {0: hidden if k else Vector((1, 1, 1)), k: Vector((1, 1, 1)), 2 + k: Vector((1.3, 1.6, 1.3)), 4 + k: hidden,
                                  FIRE_FRAMES: hidden}, 'CONSTANT')
        kit.to_track(flash, 'Fire')
    level = Vector((0, 0, 0))
    kit.keys(body, 'rotation_euler', {0: level, 3: Vector((math.radians(-1.2), 0, 0)), 10: Vector((math.radians(0.3), 0, 0)), 16: level,
                                      FIRE_FRAMES: level})
    kit.keys(body, 'location', {0: level, FIRE_FRAMES: level}, 'CONSTANT')
    kit.to_track(body, 'Fire')


def build():
    root, body = nod.start('GDIMammoth2', 'Mammoth2', 0.0)
    m = materials()
    for obj in hull(m, root):
        kit.parent(obj, body)
    turret, rails, flashes = guns(m, root, body)
    # the trot: front left and back right step together, then front right and back left
    legs = [leg(m, root, name, Vector((sx * HIP_X, sy * HIP_Y, HIP_Z)), body)
            for name, sx, sy in (('LegFL', -1, -1), ('LegFR', 1, -1), ('LegBR', 1, 1), ('LegBL', -1, 1))]
    kit.bake_camo(256)
    speed = walker.walk(legs, body, [], WALK_FRAMES, SWING, BEND, hidden=flashes)
    walker.idle(body, [], legs, sway=0.006, hidden=flashes)
    fire(body, rails, flashes)
    walker.rest(body, [body, *[j for g in legs for j in (g.hip, g.knee, g.ankle)]])
    for flash in flashes:
        flash.scale = (kit.HIDDEN,) * 3
    root['walkSpeed'] = round(speed, 4)
    nod.finish(root, SCALE)
    print('walk speed', root['walkSpeed'], 'cells/s', flush=True)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [0, 12], 'Fire': [2]}, scale=2.0, target=(0, -0.1, 0.5))
