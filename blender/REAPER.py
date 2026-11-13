"""
Tiberian Fallout – Nod Cyborg Reaper (REAPER), after Tiberian Sun: Firestorm.

The massive upper body of a cyborg on a four-legged walking base, after the original
and Tiberium Essence's Reaper. The cyborg hunches: a barrel chest with a red (house
colour) plate in front where the emblem goes and two red lights under it, huge
rounded pauldrons with red trim, the small head with a red visor sunk low between
them behind a high collar, a power pack on the back carrying a glowing green
Tiberium canister. On each shoulder sits a box launcher of the QuadLauncher, tipped
back, four red-headed missiles in its face and louvres on its sides; the arms hang
heavy and end in ribbed forearm guns with a red glow in the muzzle. The base is an
octagonal hip block with armoured caps over the four hips and an armour plate
hanging in front (the web launcher, its second weapon, a squat wide-mouthed drum,
under it). The four legs splay diagonally: a heavy armoured thigh rising to the knee,
then a big flat blade (faceted, sharp edged, a red glowing panel on each face) that
reaches down to its point on the ground, hydraulic rams under the thigh.

Nod's colours (nodvehicle.camouflage): the armour near black blotched with dark grey
and dark red; plates, trim and missile heads red (house colour).

Nodes the game uses: "Turret" (the torso's mount, not animated), "Cannon" (on it at
shoulder height, tipped towards the target; it carries the arms), "FlashL"/"FlashR"
(the shoulder launchers' muzzle flashes, used in turn). Rig: empties, no armature:
Body (bobs) → chassis, Turret → torso, Cannon → ArmL/ArmR (at the shoulders; the arm
and its gun) → PodL/PodR (the shoulder launchers, recoil); each leg
Leg<FL|FR|BL|BR>Hip (turns about the vertical: the step) → …Lift (tips the leg up
while it swings forward).

Clips
    Idle    loop, 2 s: the body breathes, the arms drift, the legs stand
    Walk    loop, 1 s: the diagonal pairs of legs step in turn (the feet on the ground
            move back evenly, the others swing forward lifted), the body bobs, the
            arms sway; the root's walkSpeed (glTF extras) is the matching ground speed
    Fire    once, 0.5 s: the left launcher fires, then the right one; each kicks back
            and its muzzle flashes

Run headless:

    blender -b --factory-startup --python blender/REAPER.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the walker.
"""
import math
import os
import sys

import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'REAPER.glb')
BLEND = os.path.join(HERE, 'REAPER.blend')

HIP_Z = 0.32                 # the hips' height on the chassis
HIP_XY = 0.12                # their offset from the middle (x and y)
KNEE = Vector((0.18, 0, 0.12))  # in a leg's frame: the hip at 0, the leg along +x
FOOT = Vector((0.4, 0, -HIP_Z))
# the blade (the lower leg) in the leg's frame, x and z: from its inner edge by the
# knee up to the spike, down the outer edge to the point on the ground (FOOT), back up
BLADE = ((0.15, 0.1), (0.25, 0.24), (0.36, 0.1), (0.415, -0.1), (FOOT.x, FOOT.z), (0.3, -0.08))
BLADE_THICKNESS = 0.04
LEGS = (('FL', -1, -1), ('FR', 1, -1), ('BL', -1, 1), ('BR', 1, 1))
WALK_FRAMES = 30
SWING = 0.3                  # the hips' turn either way (radians)
LIFT = -0.2                  # the leg tipped up in the middle of its swing
FIRE_FRAMES = 15
SHOULDER = Vector((0.21, 0, 0.7))
ELBOW = Vector((0.275, 0.02, 0.565))
GUN_Y = (0.07, -0.2)         # the forearm gun's back and muzzle
POD = Vector((0.205, 0.05, 0.845))  # the shoulder launcher's middle
POD_SIZE = Vector((0.12, 0.15, 0.1))
POD_TILT = -0.26             # tipped back: its face looks forward and up
CANNON = Vector((0, 0, 0.66))
TURRET = Vector((0, 0, 0.44))
SCALE = 1.0

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def chassis(m):
    """The octagonal hip block with the armoured hip caps, the plate in front and the
    web launcher under it."""
    flat = math.radians(22.5)
    parts = [
        cylinder('Chassis', m['armour'], 0.17, 0.12, (0, 0, 0.34), rotation=(0, 0, flat), segments=8, bevel=0.012),
        cylinder('ChassisTop', m['armour_dark'], 0.16, 0.05, (0, 0, 0.425), rotation=(0, 0, flat), segments=8, bevel=0.008, radius2=0.11),
        cylinder('Belly', m['armour_dark'], 0.1, 0.07, (0, 0, 0.255), rotation=(0, 0, flat), segments=8, bevel=0.008, radius2=0.16),
        *detail.lamp('BellyLight', m['dark'], m['lamp_red'], (0, 0, 0.218), (0, 0, -1), 0.016),
        # the armour plate hanging in front, the emblem's red field on it
        kit.hexahedron('FrontPlate', m['armour'], (
            (-0.05, -0.2, 0.25), (0.05, -0.2, 0.25), (0.05, -0.16, 0.25), (-0.05, -0.16, 0.25),
            (-0.075, -0.19, 0.44), (0.075, -0.19, 0.44), (0.075, -0.14, 0.44), (-0.075, -0.14, 0.44)), bevel=0.008),
        kit.hexahedron('Emblem', m['remap'], (
            (-0.025, -0.204, 0.3), (0.025, -0.204, 0.3), (0.025, -0.19, 0.3), (-0.025, -0.19, 0.3),
            (-0.05, -0.197, 0.41), (0.05, -0.197, 0.41), (0.05, -0.183, 0.41), (-0.05, -0.183, 0.41)), bevel=0.004),
        *detail.rivets('FrontRivets', m['steel_light'], (-0.055, -0.196, 0.425), (0.055, -0.196, 0.425), 4, 0.005, 'Y'),
        # the web launcher: a squat drum with a wide dark mouth under the plate
        cylinder('WebDrum', m['steel'], 0.045, 0.08, (0, -0.17, 0.205), rotation=(math.pi / 2, 0, 0), segments=16),
        cylinder('WebMouth', m['dark'], 0.036, 0.012, (0, -0.21, 0.205), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0),
        cylinder('WebRing', m['remap'], 0.05, 0.018, (0, -0.195, 0.205), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0.003),
        *[box(f'WebVane{k}', m['steel_light'], (0.008, 0.03, 0.03), (0.038 * math.cos(a), -0.17, 0.205 + 0.038 * math.sin(a)),
              rotation=(0, -a, 0), bevel=0.002) for k, a in enumerate(math.radians(d) for d in (30, 150, 270))],
    ]
    # vents and lamps on the flats at the sides and the back
    for k, a in enumerate(math.radians(d) for d in (90, 180, 270)):
        d = Vector((math.sin(a), -math.cos(a), 0))
        parts.append(box(f'Plate{k}', m['remap'], (0.1, 0.012, 0.05), d * 0.162 + Vector((0, 0, 0.35)), bevel=0.004, rotation=(0, 0, a)))
        parts += detail.lamp(f'PlateLamp{k}', m['dark'], m['lamp_red'], d * 0.168 + Vector((0, 0, 0.39)), d, 0.008)
    for name, sx, sy in LEGS:
        hip = Vector((sx * HIP_XY, sy * HIP_XY, HIP_Z))
        out = Vector((sx, sy, 0)).normalized()
        yaw = math.atan2(sy, sx)
        parts += [
            # an armoured cap over the hip, a red plate on it
            kit.hexahedron(f'HipCap{name}', m['armour_dark'], [
                hip + Matrix.Rotation(yaw, 3, 'Z') @ Vector(p) for p in (
                    (-0.06, -0.075, 0.0), (0.07, -0.07, -0.02), (0.07, 0.07, -0.02), (-0.06, 0.075, 0.0),
                    (-0.05, -0.065, 0.1), (0.05, -0.055, 0.075), (0.05, 0.055, 0.075), (-0.05, 0.065, 0.1))], bevel=0.01),
            box(f'HipPlate{name}', m['remap'], (0.07, 0.08, 0.012), hip + out * 0.01 + Vector((0, 0, 0.092)), bevel=0.003,
                rotation=(0, 0.2, yaw)),
        ]
    return kit.merge('Chassis', parts)


def torso(m):
    """The cyborg's hunched torso and head (fixed on the Turret)."""
    parts = [
        cylinder('Spine', m['steel'], 0.065, 0.08, (0, 0.01, 0.47), segments=14),
        cylinder('WaistRing', m['lamp_red'], 0.07, 0.012, (0, 0.01, 0.47), segments=16, bevel=0),
        kit.hexahedron('Abdomen', m['armour_dark'], (
            (-0.09, -0.07, 0.49), (0.09, -0.07, 0.49), (0.09, 0.07, 0.49), (-0.09, 0.07, 0.49),
            (-0.12, -0.095, 0.575), (0.12, -0.095, 0.575), (0.12, 0.08, 0.575), (-0.12, 0.08, 0.575)), bevel=0.014),
        *[box(f'AbRib{k}', m['steel'], (0.17 - 0.02 * k, 0.012, 0.014), (0, -0.075 - 0.008 * k, 0.51 + 0.025 * k), bevel=0.002) for k in range(2)],
        # the barrel chest: wider and deeper at the top, the shoulders hunched forward
        kit.hexahedron('ChestLow', m['armour'], (
            (-0.12, -0.1, 0.55), (0.12, -0.1, 0.55), (0.12, 0.08, 0.55), (-0.12, 0.08, 0.55),
            (-0.175, -0.14, 0.65), (0.175, -0.14, 0.65), (0.175, 0.1, 0.65), (-0.175, 0.1, 0.65)), bevel=0.016),
        kit.hexahedron('ChestHigh', m['armour'], (
            (-0.175, -0.14, 0.65), (0.175, -0.14, 0.65), (0.175, 0.1, 0.65), (-0.175, 0.1, 0.65),
            (-0.15, -0.105, 0.765), (0.15, -0.105, 0.765), (0.15, 0.125, 0.765), (-0.15, 0.125, 0.765)), bevel=0.016),
        # the red plate where the emblem goes, the two red lights under it
        kit.hexahedron('ChestPlate', m['remap'], (
            (-0.045, -0.147, 0.62), (0.045, -0.147, 0.62), (0.045, -0.12, 0.62), (-0.045, -0.12, 0.62),
            (-0.085, -0.133, 0.74), (0.085, -0.133, 0.74), (0.085, -0.1, 0.74), (-0.085, -0.1, 0.74)), bevel=0.006),
        *[part for s in (-1, 1) for part in detail.lamp(f'ChestLight{s}', m['dark'], m['lamp_red'], (s * 0.055, -0.13, 0.598), (0, -1, -0.3), 0.014)],
        *detail.seam('ChestSeam', m['seam'], (-0.17, -0.143, 0.652), (0.17, -0.143, 0.652), 0.006),
        # the high collar round the neck, the head sunk in it
        kit.hexahedron('Collar', m['armour_dark'], (
            (-0.11, -0.07, 0.74), (0.11, -0.07, 0.74), (0.11, 0.11, 0.74), (-0.11, 0.11, 0.74),
            (-0.1, -0.03, 0.81), (0.1, -0.03, 0.81), (0.1, 0.11, 0.825), (-0.1, 0.11, 0.825)), bevel=0.012),
        cylinder('Neck', m['steel'], 0.03, 0.05, (0, -0.04, 0.765), segments=12),
        box('Head', m['armour_dark'], (0.075, 0.085, 0.075), (0, -0.065, 0.79), bevel=0.024),
        box('Skull', m['steel'], (0.05, 0.06, 0.016), (0, -0.058, 0.83), bevel=0.006),
        box('Visor', m['lamp_red'], (0.06, 0.01, 0.014), (0, -0.108, 0.798), bevel=0.003),
        box('Jaw', m['steel'], (0.048, 0.022, 0.024), (0, -0.103, 0.765), bevel=0.005),
        *detail.hose('HoseL', m['dark'], (-0.04, -0.04, 0.745), (-0.06, -0.09, 0.73), (-0.03, -0.105, 0.76), 0.007),
        *detail.hose('HoseR', m['dark'], (0.04, -0.04, 0.745), (0.06, -0.09, 0.73), (0.03, -0.105, 0.76), 0.007),
        # the power pack on the back and the Tiberium canister in its cage
        box('Pack', m['armour_dark'], (0.2, 0.09, 0.17), (0, 0.16, 0.66), bevel=0.014),
        *detail.grille('PackVent', m['steel'], m['dark'], (0, 0.207, 0.64), 0.12, 0.08, 'Y', 4, 0.008),
        cylinder('CanisterBase', m['steel'], 0.04, 0.02, (0, 0.16, 0.755), segments=12, bevel=0.003),
        cylinder('Canister', m['lamp_green'], 0.03, 0.1, (0, 0.16, 0.815), segments=12, bevel=0.004),
        cylinder('CanisterCap', m['steel'], 0.036, 0.016, (0, 0.16, 0.872), segments=12, bevel=0.003),
        *[beam(f'CanisterBar{k}', m['steel'], (0.035 * math.cos(a), 0.16 + 0.035 * math.sin(a), 0.76),
               (0.035 * math.cos(a), 0.16 + 0.035 * math.sin(a), 0.868), 0.007) for k, a in enumerate(math.radians(d) for d in (45, 135, 225, 315))],
        *detail.hose('CanisterHose', m['dark'], (0.03, 0.18, 0.76), (0.09, 0.2, 0.72), (0.12, 0.12, 0.72), 0.008),
    ]
    for s in (-1, 1):
        parts += [
            # the huge pauldron, its red trim and rivets
            kit.hexahedron(f'Pauldron{s}', m['armour'], (
                (s * 0.12, -0.12, 0.7), (s * 0.29, -0.12, 0.64), (s * 0.29, 0.13, 0.64), (s * 0.12, 0.13, 0.7),
                (s * 0.12, -0.1, 0.8), (s * 0.25, -0.1, 0.77), (s * 0.25, 0.11, 0.77), (s * 0.12, 0.11, 0.8)), bevel=0.02),
            beam(f'PauldronTrim{s}', m['remap'], (s * 0.14, -0.122, 0.79), (s * 0.282, -0.122, 0.65), 0.014, 0.012),
            beam(f'PauldronEdge{s}', m['remap'], (s * 0.29, -0.1, 0.645), (s * 0.29, 0.11, 0.645), 0.012, 0.014),
            *detail.rivets(f'PauldronRivets{s}', m['steel_light'], (s * 0.27, -0.06, 0.765), (s * 0.27, 0.07, 0.765), 3, 0.005, 'Z'),
            # the launcher's mount on the pauldron
            box(f'PodMount{s}', m['steel'], (0.07, 0.09, 0.03), (s * POD.x, POD.y - 0.01, 0.785), bevel=0.004),
        ]
    return kit.merge('Torso', parts, TURRET)


def arm(m, s, cannon):
    """An arm with its forearm gun and the launcher on its shoulder: (arm joint, pod,
    flash)."""
    side = 'L' if s < 0 else 'R'
    shoulder = Vector((s * SHOULDER.x, SHOULDER.y, SHOULDER.z))
    elbow = Vector((s * ELBOW.x, ELBOW.y, ELBOW.z))
    gun_x, gun_z = s * (ELBOW.x + 0.005), ELBOW.z - 0.005
    back, muzzle = GUN_Y
    length = back - muzzle
    pivot = walker.joint(f'Arm{side}', cannon, shoulder)
    along = (math.pi / 2, 0, 0)
    parts = [
        sphere(f'ShoulderJoint{side}', m['steel'], 0.05, shoulder, 12),
        beam(f'UpperArm{side}', m['steel'], shoulder, elbow, 0.06),
        kit.hexahedron(f'ArmPlate{side}', m['armour_dark'], (
            shoulder + Vector((s * 0.035, -0.04, -0.04)), elbow + Vector((s * 0.04, -0.04, 0.03)),
            elbow + Vector((s * 0.04, 0.045, 0.03)), shoulder + Vector((s * 0.035, 0.04, -0.04)),
            shoulder + Vector((s * 0.06, -0.035, -0.03)), elbow + Vector((s * 0.06, -0.035, 0.04)),
            elbow + Vector((s * 0.06, 0.04, 0.04)), shoulder + Vector((s * 0.06, 0.035, -0.03))), bevel=0.006),
        beam(f'ArmPiston{side}', m['steel_light'], shoulder + Vector((-s * 0.02, 0.045, -0.02)), elbow + Vector((-s * 0.02, 0.05, 0.01)), 0.016),
        sphere(f'Elbow{side}', m['steel'], 0.04, elbow, 12),
        # the forearm gun: a heavy ribbed barrel, louvres on its outside, the red glow in the muzzle
        cylinder(f'Gun{side}', m['armour_dark'], 0.05, length, (gun_x, (back + muzzle) / 2, gun_z), rotation=along, segments=12, bevel=0.006),
        *[cylinder(f'GunRib{side}{k}', m['steel'], 0.056, 0.016, (gun_x, back - 0.04 - 0.055 * k, gun_z), rotation=along, segments=12,
                   bevel=0.003) for k in range(4)],
        cylinder(f'GunMuzzle{side}', m['steel'], 0.04, 0.04, (gun_x, muzzle - 0.012, gun_z), rotation=along, segments=12, bevel=0.004),
        cylinder(f'GunBore{side}', m['dark'], 0.03, 0.042, (gun_x, muzzle - 0.013, gun_z), rotation=along, segments=12, bevel=0),
        cylinder(f'GunGlow{side}', m['lamp_red'], 0.018, 0.044, (gun_x, muzzle - 0.012, gun_z), rotation=along, segments=10, bevel=0),
        *detail.grille(f'GunVent{side}', m['steel'], m['dark'], (gun_x + s * 0.048, -0.05, gun_z), 0.1, 0.04, 'X', 3, 0.008),
        box(f'GunStripe{side}', m['remap'], (0.03, 0.06, 0.012), (gun_x, back - 0.03, gun_z + 0.05), bevel=0.003),
        box(f'Grip{side}', m['steel'], (0.03, 0.04, 0.05), (gun_x - s * 0.04, -0.02, gun_z - 0.02), bevel=0.005),
    ]
    kit.parent(kit.merge(f'UpperArm{side}', parts, shoulder), pivot)
    pod = Vector((s * POD.x, POD.y, POD.z))
    pod_parts = [
        box(f'PodBody{side}', m['armour_dark'], POD_SIZE, pod, bevel=0.012),
        box(f'PodTop{side}', m['remap'], (POD_SIZE.x - 0.03, POD_SIZE.y - 0.04, 0.012), pod + Vector((0, 0.01, POD_SIZE.z / 2)), bevel=0.003),
        box(f'PodFace{side}', m['steel'], (POD_SIZE.x - 0.012, 0.012, POD_SIZE.z - 0.012), pod - Vector((0, POD_SIZE.y / 2, 0)), bevel=0.002),
        *detail.grille(f'PodLouvre{side}', m['steel'], m['dark'], pod + Vector((s * POD_SIZE.x / 2, 0.01, 0)), POD_SIZE.y - 0.04,
                       POD_SIZE.z - 0.035, 'X', 4, 0.008),
    ]
    for k in range(4):
        c = pod + Vector(((k % 2 - 0.5) * 0.05, -POD_SIZE.y / 2, (k // 2 - 0.5) * 0.045))
        pod_parts += [
            cylinder(f'Tube{side}{k}', m['dark'], 0.019, 0.016, c, rotation=along, segments=12, bevel=0),
            sphere(f'Warhead{side}{k}', m['remap'], 0.016, c + Vector((0, -0.004, 0)), 10),
        ]
    body = kit.merge(f'Pod{side}', pod_parts, pod)
    body.data.transform(Matrix.Rotation(POD_TILT, 4, 'X'))  # tipped back about its middle
    kit.parent(body, pivot)
    facing = Matrix.Rotation(POD_TILT, 3, 'X') @ Vector((0, -1, 0))
    flash = kit.parent(nod.flash(m, f'Flash{side}', pod + facing * (POD_SIZE.y / 2 + 0.05), 0.045, facing), pivot)
    return pivot, body, flash


def blade(m, name):
    """The leg's blade in its frame's xz plane: sharp edges, faceted faces sloping up to
    the middle, a glowing red panel on each face."""
    points = [Vector((x, 0, z)) for x, z in BLADE]
    centre = sum(points, Vector()) / len(points)
    half = BLADE_THICKNESS / 2

    def inset(p, t, y):
        q = p.lerp(centre, t)
        return Vector((q.x, y, q.z))

    def build(bm):
        edge = [bm.verts.new(p) for p in points]
        n = len(points)
        for side in (-1, 1):
            face = [bm.verts.new(inset(p, 0.24, side * half)) for p in points]
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((edge[i], edge[j], face[j], face[i]))
            bm.faces.new(face)
            # the glowing panel: a thin slab on the face
            low = [bm.verts.new(inset(p, 0.5, side * (half - 0.004))) for p in points]
            high = [bm.verts.new(inset(p, 0.5, side * (half + 0.004))) for p in points]
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((low[i], low[j], high[j], high[i])).material_index = 1
            bm.faces.new(low).material_index = 1
            bm.faces.new(high).material_index = 1
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])

    obj = kit.mesh_object(f'{name}Blade', build)
    obj.data.materials.append(m['armour_dark'])
    obj.data.materials.append(m['lamp_red'])
    for poly in obj.data.polygons:
        poly.use_smooth = False
    return obj


def leg(m, name, sx, sy, body):
    """One leg, built along +x from the hip at the origin, then turned and moved onto
    its socket; returns (hip, lift, rest yaw)."""
    hip = kit.empty(f'Leg{name}Hip')
    hip.empty_display_size = 0.05
    lift = kit.parent(kit.empty(f'Leg{name}Lift'), hip)
    lift.empty_display_size = 0.05
    knee = KNEE
    across = (math.pi / 2, 0, 0)
    parts = [
        cylinder(f'{name}HipJoint', m['steel'], 0.045, 0.11, (0, 0, 0), rotation=across, segments=14),
        beam(f'{name}Thigh', m['armour'], Vector((0.0, 0, 0.0)), knee, 0.085, 0.08),
        beam(f'{name}ThighPlate', m['remap'], Vector((0.03, 0, 0.055)), knee + Vector((-0.035, 0, 0.042)), 0.07, 0.014),
        *detail.rivets(f'{name}ThighRivets', m['steel_light'], (0.04, 0.044, 0.02), (0.13, 0.044, 0.08), 3, 0.005, 'Y'),
        *detail.rivets(f'{name}ThighRivetsBack', m['steel_light'], (0.04, -0.044, 0.02), (0.13, -0.044, 0.08), 3, 0.005, 'Y'),
        cylinder(f'{name}Knee', m['armour_dark'], 0.05, 0.1, knee, rotation=across, segments=14),
        cylinder(f'{name}KneeCap', m['steel'], 0.034, 0.108, knee, rotation=across, segments=12, bevel=0.003),
        cylinder(f'{name}KneeGlow', m['lamp_red'], 0.016, 0.112, knee, rotation=across, segments=10, bevel=0),
        blade(m, name),
    ]
    for side in (-1, 1):  # the rams under the thigh, either side of the blade
        y = side * 0.034
        start, end = Vector((0.05, y, -0.045)), Vector((0.22, y, 0.0))
        parts += [
            beam(f'{name}Ram{side}', m['steel_light'], start, end, 0.014),
            beam(f'{name}RamSleeve{side}', m['steel'], start, start.lerp(end, 0.5), 0.024),
        ]
    kit.parent(kit.merge(f'Leg{name}', parts), lift)
    yaw = math.atan2(sy, sx)
    hip.location = (sx * HIP_XY, sy * HIP_XY, HIP_Z)
    hip.rotation_euler = (0, 0, yaw)
    kit.parent(hip, body)
    return hip, lift, yaw


def walk(legs, body, arms):
    """The Walk clip: FL+BR swing while FR+BL stand, then the other way round. A
    standing foot moves back (+y) evenly: its hip turns from -SWING to +SWING (mirrored
    for the back legs, whose feet move back when the hip turns the other way)."""
    for f in range(WALK_FRAMES + 1):
        t = f / WALK_FRAMES
        for k, (name, (hip, lift, yaw)) in enumerate(legs.items()):
            pair = 0 if name in ('FL', 'BR') else 1
            p = (t + 0.5 * pair) % 1.0
            if p < 0.5:
                turn, up = -SWING + 2 * SWING * p / 0.5, 0.0
            else:
                s = (p - 0.5) / 0.5
                turn, up = SWING * math.cos(math.pi * s), LIFT * math.sin(math.pi * s)
            sign = 1 if math.cos(yaw) > 0 else -1  # which way the foot moves back
            hip.rotation_euler = (0, 0, yaw + sign * turn)
            hip.keyframe_insert('rotation_euler', frame=f)
            lift.rotation_euler = (0, up, 0)
            lift.keyframe_insert('rotation_euler', frame=f)
        body.location = (0, 0, 0.006 * math.sin(4 * math.pi * t))
        body.keyframe_insert('location', frame=f)
        for k, a in enumerate(arms):
            a.rotation_euler = (0.05 * math.sin(2 * math.pi * t + math.pi * k), 0, 0)
            a.keyframe_insert('rotation_euler', frame=f)
    for hip, lift, _ in legs.values():
        for obj in (hip, lift):
            for fc in kit._fcurves(obj):
                for point in fc.keyframe_points:
                    point.interpolation = 'LINEAR'
            kit.to_track(obj, 'Walk')
    for obj in (body, *arms):
        kit.to_track(obj, 'Walk')
    # the foot's way back while it stands, over half the loop
    radius = FOOT.x
    stride = 2 * radius * abs(math.cos(math.radians(45))) * math.sin(SWING)
    return stride / (WALK_FRAMES / 2 / kit.FPS)


def idle(body, arms):
    for f in range(0, kit.IDLE_END + 1, 2):
        t = 2 * math.pi * f / kit.IDLE_END
        body.location = (0, 0, 0.004 * math.sin(t))
        body.keyframe_insert('location', frame=f)
        for k, a in enumerate(arms):
            a.rotation_euler = (0.03 * math.sin(t + k), 0, 0)
            a.keyframe_insert('rotation_euler', frame=f)
    for obj in (body, *arms):
        kit.to_track(obj, 'Idle')


def fire(pods, flashes):
    """The left launcher fires at once, the right one a third of a second later; each
    pod kicks back along its length."""
    hidden, on = Vector((kit.HIDDEN,) * 3), Vector((1, 1, 1))
    for k, (pod, flash) in enumerate(zip(pods, flashes)):
        start = 5 * k
        rest = pod.location.copy()
        kick = rest + Vector((0, 0.035, 0))
        kit.keys(pod, 'location', {0: rest, start: rest, start + 2: kick, start + 4: kick, min(start + 10, FIRE_FRAMES): rest, FIRE_FRAMES: rest})
        kit.to_track(pod, 'Fire')
        frames = {0: hidden, FIRE_FRAMES: hidden} | {start: on, start + 2: Vector((1.3, 1.5, 1.3)), start + 4: hidden}
        if start == 0:
            frames[0] = on
        kit.keys(flash, 'scale', frames, 'CONSTANT')
        kit.to_track(flash, 'Fire')
        pod.location = rest
    walker.hide(flashes, kit.IDLE_END, 'Idle')
    walker.hide(flashes, WALK_FRAMES, 'Walk')
    for flash in flashes:
        flash.scale = hidden


def build():
    root, body = nod.start('NodCyborgReaper', 'CyborgReaper', 0.0)
    m = nod.materials()
    kit.parent(chassis(m), body)
    turret = kit.parent(kit.empty('Turret', TURRET), body)
    kit.parent(torso(m), turret)
    cannon = kit.parent(kit.empty('Cannon', CANNON), turret)
    arms, pods, flashes = [], [], []
    for s in (-1, 1):
        a, p, f = arm(m, s, cannon)
        arms.append(a)
        pods.append(p)
        flashes.append(f)
    legs = {name: leg(m, name, sx, sy, body) for name, sx, sy in LEGS}
    nod.camouflage(kit.collection().objects, max_edge=0.05)
    speed = walk(legs, body, arms)
    idle(body, arms)
    fire(pods, flashes)
    body.location = (0, 0, 0)
    for a in arms:
        a.rotation_euler = (0, 0, 0)
    for hip, lift, yaw in legs.values():
        hip.rotation_euler = (0, 0, yaw)
        lift.rotation_euler = (0, 0, 0)
    root['walkSpeed'] = round(speed, 4)
    nod.finish(root, SCALE)
    print('walk speed', root['walkSpeed'], flush=True)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [0, 8, 15], 'Fire': [1, 6]}, scale=1.5, target=(0, 0, 0.4))
