"""
Tiberian Fallout – Nod Cyborg Reaper (REAPER), after Tiberian Sun: Firestorm.

The upper body of a cyborg on a four-legged walking base, like the original: an
octagonal chassis in Nod's dark camouflage with red (house colour) plates on its
flats, four long mechanical legs splayed diagonally from its corners, each rising to a
knee with a glowing cyan ring and reaching down to a pointed foot. On the chassis the
cyborg: a segmented waist with a cyan ring, a broad chest with an amber light, red
pauldrons, a power pack with exhausts on the back, a head with a cyan visor. Its arms
end in the two launchers of the QuadLauncher, two tubes each; the web launcher (its
second weapon), a squat wide-mouthed drum, sits in the chassis' front under the chest.

Nodes the game uses: "Turret" (the torso's mount, not animated), "Cannon" (on it at
shoulder height, tipped towards the target; it carries the arms), "FlashL"/"FlashR"
(the launchers' muzzle flashes, used in turn). Rig: empties, no armature: Body (bobs)
→ chassis, Turret → torso, Cannon → ArmL/ArmR → PodL/PodR (recoil); each leg
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

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'REAPER.glb')
BLEND = os.path.join(HERE, 'REAPER.blend')

HIP_Z = 0.34                 # the hips' height on the chassis
HIP_XY = 0.12                # their offset from the middle (x and y)
KNEE = Vector((0.2, 0, 0.1))  # in a leg's frame: the hip at 0, the leg along +x
FOOT = Vector((0.4, 0, -HIP_Z))
LEGS = (('FL', -1, -1), ('FR', 1, -1), ('BL', -1, 1), ('BR', 1, 1))
WALK_FRAMES = 30
SWING = 0.3                  # the hips' turn either way (radians)
LIFT = -0.2                  # the leg tipped up in the middle of its swing
FIRE_FRAMES = 15
SHOULDER = Vector((0.17, 0, 0.71))
POD = Vector((0.21, -0.08, 0.6))
POD_LENGTH = 0.17
CANNON = Vector((0, 0, 0.66))
TURRET = Vector((0, 0, 0.44))
SCALE = 1.0

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def chassis(m):
    """The octagonal chassis with the hip sockets and the web launcher in front."""
    flat = math.radians(22.5)
    parts = [
        cylinder('Chassis', m['armour'], 0.19, 0.12, (0, 0, 0.36), rotation=(0, 0, flat), segments=8, bevel=0.01),
        cylinder('ChassisTop', m['armour_dark'], 0.18, 0.04, (0, 0, 0.44), rotation=(0, 0, flat), segments=8, bevel=0.008, radius2=0.13),
        cylinder('Belly', m['armour_dark'], 0.13, 0.07, (0, 0, 0.27), rotation=(0, 0, flat), segments=8, bevel=0.008, radius2=0.18),
        cylinder('BellyLight', m['signal'], 0.03, 0.01, (0, 0, 0.233), segments=12, bevel=0),
        # the web launcher: a squat drum with a wide dark mouth
        cylinder('WebDrum', m['steel'], 0.05, 0.09, (0, -0.2, 0.34), rotation=(math.pi / 2, 0, 0), segments=16),
        cylinder('WebMouth', m['dark'], 0.04, 0.012, (0, -0.242, 0.34), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0),
        cylinder('WebRing', m['remap'], 0.056, 0.02, (0, -0.225, 0.34), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0.003),
        *[box(f'WebVane{k}', m['steel_light'], (0.008, 0.03, 0.035), (0.042 * math.cos(a), -0.2, 0.34 + 0.042 * math.sin(a)),
              rotation=(0, -a, 0), bevel=0.002) for k, a in enumerate(math.radians(d) for d in (30, 150, 270))],
    ]
    # red plates on the flats between the legs (front, back, sides)
    for k, a in enumerate(math.radians(d) for d in (0, 90, 180, 270)):
        d = Vector((math.sin(a), -math.cos(a), 0))
        if k == 0:
            continue  # the front carries the web launcher
        plate = box(f'Plate{k}', m['remap'], (0.11, 0.012, 0.06), d * 0.178 + Vector((0, 0, 0.37)), bevel=0.004, rotation=(0, 0, a))
        parts.append(plate)
        parts += detail.lamp(f'PlateLamp{k}', m['dark'], m['lamp_red'], d * 0.186 + Vector((0, 0, 0.405)), d, 0.008)
    for name, sx, sy in LEGS:
        hip = Vector((sx * HIP_XY, sy * HIP_XY, HIP_Z))
        parts.append(sphere(f'Socket{name}', m['steel'], 0.05, hip, 14))
    return kit.merge('Chassis', parts)


def torso(m):
    """The cyborg's torso and head (fixed on the Turret)."""
    parts = [
        cylinder('Spine', m['steel'], 0.05, 0.09, (0, 0.01, 0.48), segments=14),
        cylinder('WaistRing', m['signal'], 0.056, 0.014, (0, 0.01, 0.48), segments=16, bevel=0),
        kit.hexahedron('Abdomen', m['armour_dark'], (
            (-0.075, -0.06, 0.5), (0.075, -0.06, 0.5), (0.075, 0.07, 0.5), (-0.075, 0.07, 0.5),
            (-0.095, -0.075, 0.57), (0.095, -0.075, 0.57), (0.095, 0.075, 0.57), (-0.095, 0.075, 0.57)), bevel=0.012),
        kit.hexahedron('Chest', m['armour'], (
            (-0.1, -0.085, 0.56), (0.1, -0.085, 0.56), (0.1, 0.075, 0.56), (-0.1, 0.075, 0.56),
            (-0.14, -0.06, 0.73), (0.14, -0.06, 0.73), (0.14, 0.085, 0.73), (-0.14, 0.085, 0.73)), bevel=0.016),
        kit.hexahedron('ChestPlate', m['remap'], (
            (-0.06, -0.09, 0.6), (0.06, -0.09, 0.6), (0.06, -0.06, 0.6), (-0.06, -0.06, 0.6),
            (-0.09, -0.068, 0.71), (0.09, -0.068, 0.71), (0.09, -0.04, 0.71), (-0.09, -0.04, 0.71)), bevel=0.006),
        *detail.lamp('ChestLight', m['dark'], m['lamp_amber'], (0, -0.086, 0.645), (0, -1, 0.15), 0.014),
        *[box(f'Rib{k}', m['steel'], (0.13 - 0.01 * k, 0.012, 0.012), (0, -0.07, 0.52 + 0.022 * k), bevel=0.002) for k in range(2)],
        # the power pack on the back with two exhausts
        box('Pack', m['armour_dark'], (0.17, 0.07, 0.14), (0, 0.115, 0.64), bevel=0.012),
        *detail.grille('PackVent', m['steel'], m['dark'], (0, 0.151, 0.63), 0.1, 0.07, 'Y', 4, 0.006),
        *[cylinder(f'Stack{s}', m['steel_light'], 0.016, 0.1, (s * 0.06, 0.13, 0.74), segments=10) for s in (-1, 1)],
        *[cylinder(f'StackTip{s}', m['dark'], 0.014, 0.01, (s * 0.06, 0.13, 0.791), segments=10, bevel=0) for s in (-1, 1)],
        # neck and head with the cyan visor
        cylinder('Neck', m['steel'], 0.032, 0.07, (0, -0.005, 0.755), segments=12),
        box('Head', m['armour_dark'], (0.085, 0.095, 0.085), (0, -0.015, 0.815), bevel=0.026),
        box('Skull', m['steel'], (0.06, 0.07, 0.02), (0, -0.005, 0.858), bevel=0.008),
        box('Visor', m['signal'], (0.064, 0.012, 0.018), (0, -0.062, 0.822), bevel=0.004),
        box('Jaw', m['steel'], (0.05, 0.02, 0.025), (0, -0.058, 0.786), bevel=0.005),
        *detail.hose('HoseL', m['dark'], (-0.05, 0.08, 0.7), (-0.08, 0.04, 0.8), (-0.04, 0.0, 0.8), 0.008),
        *detail.hose('HoseR', m['dark'], (0.05, 0.08, 0.7), (0.08, 0.04, 0.8), (0.04, 0.0, 0.8), 0.008),
    ]
    for s in (-1, 1):
        parts.append(kit.hexahedron(f'Pauldron{s}', m['remap'], (
            (s * 0.11, -0.07, 0.69), (s * 0.2, -0.065, 0.68), (s * 0.2, 0.08, 0.68), (s * 0.11, 0.085, 0.69),
            (s * 0.11, -0.055, 0.77), (s * 0.17, -0.05, 0.755), (s * 0.17, 0.07, 0.755), (s * 0.11, 0.07, 0.77)), bevel=0.01))
    return kit.merge('Torso', parts, TURRET)


def arm(m, s, cannon):
    """An arm ending in a launcher: (arm joint, pod, flash)."""
    side = 'L' if s < 0 else 'R'
    shoulder = Vector((s * SHOULDER.x, SHOULDER.y, SHOULDER.z))
    pod = Vector((s * POD.x, POD.y, POD.z))
    elbow = pod + Vector((0, 0.07, 0.02))
    pivot = walker.joint(f'Arm{side}', cannon, shoulder)
    kit.parent(kit.merge(f'UpperArm{side}', [
        sphere(f'ShoulderJoint{side}', m['steel'], 0.04, shoulder, 12),
        beam(f'UpperArm{side}', m['steel'], shoulder, elbow, 0.045),
        beam(f'ArmPiston{side}', m['steel_light'], shoulder + Vector((s * 0.03, 0.03, -0.01)), elbow + Vector((s * 0.03, 0.02, 0.0)), 0.014),
        sphere(f'Elbow{side}', m['steel'], 0.03, elbow, 12),
        cylinder(f'ElbowGlow{side}', m['signal'], 0.033, 0.01, elbow, rotation=(0, math.pi / 2, 0), segments=14, bevel=0),
    ], shoulder), pivot)
    front = pod - Vector((0, POD_LENGTH / 2, 0))
    parts = [
        box(f'PodBody{side}', m['armour_dark'], (0.085, POD_LENGTH, 0.08), pod, bevel=0.012),
        box(f'PodStripe{side}', m['remap'], (0.087, 0.05, 0.082), pod + Vector((0, 0.03, 0)), bevel=0.01),
        box(f'PodSight{side}', m['steel'], (0.016, 0.05, 0.016), pod + Vector((-s * 0.03, -0.02, 0.048)), bevel=0.003),
    ]
    for k, dz in enumerate((-0.019, 0.019)):
        c = front + Vector((0, 0, dz))
        parts += [
            cylinder(f'Tube{side}{k}', m['steel'], 0.018, 0.04, c + Vector((0, -0.012, 0)), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.002),
            cylinder(f'Mouth{side}{k}', m['dark'], 0.013, 0.004, c + Vector((0, -0.033, 0)), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0),
            sphere(f'Seeker{side}{k}', m['lamp_red'], 0.007, c + Vector((0, -0.028, 0)), 8),
        ]
    body = kit.parent(kit.merge(f'Pod{side}', parts, pod), pivot)
    flash = kit.parent(nod.flash(m, f'Flash{side}', front - Vector((0, 0.06, 0)), 0.045), pivot)
    return pivot, body, flash


def leg(m, name, sx, sy, body):
    """One leg, built along +x from the hip at the origin, then turned and moved onto
    its socket; returns (hip, lift, rest yaw)."""
    hip = kit.empty(f'Leg{name}Hip')
    hip.empty_display_size = 0.05
    lift = kit.parent(kit.empty(f'Leg{name}Lift'), hip)
    lift.empty_display_size = 0.05
    knee, foot = KNEE, FOOT
    ankle = foot + Vector((-0.02, 0, 0.09))
    middle = knee.lerp(ankle, 0.5)
    parts = [
        cylinder(f'{name}HipJoint', m['steel'], 0.035, 0.09, (0, 0, 0), rotation=(math.pi / 2, 0, 0), segments=14),
        beam(f'{name}Thigh', m['armour'], Vector((0.03, 0, 0.01)), knee, 0.075, 0.06),
        beam(f'{name}ThighPlate', m['remap'], Vector((0.06, 0, 0.05)), knee + Vector((-0.03, 0, 0.034)), 0.05, 0.012),
        cylinder(f'{name}Knee', m['steel'], 0.04, 0.09, knee, rotation=(math.pi / 2, 0, 0), segments=14),
        cylinder(f'{name}KneeGlow', m['signal'], 0.043, 0.012, knee, rotation=(math.pi / 2, 0, 0), segments=16, bevel=0),
        beam(f'{name}Shin', m['armour_dark'], knee + Vector((0.01, 0, -0.02)), middle, 0.065, 0.055),
        beam(f'{name}ShinLow', m['steel'], middle, ankle, 0.04, 0.035),
        beam(f'{name}Piston', m['steel_light'], Vector((0.1, 0, -0.01)), middle + Vector((-0.03, 0, 0)), 0.016),
        beam(f'{name}PistonSleeve', m['steel'], Vector((0.1, 0, -0.01)), Vector((0.1, 0, -0.01)).lerp(middle, 0.45), 0.026),
        sphere(f'{name}Ankle', m['steel'], 0.026, ankle, 12),
        cylinder(f'{name}Foot', m['steel_light'], 0.004, 0.09, ankle.lerp(foot, 0.5), segments=10, bevel=0, radius2=0.026),
        cylinder(f'{name}FootCollar', m['armour_dark'], 0.03, 0.02, ankle - Vector((0, 0, 0.02)), segments=10),
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
    nod.camouflage(kit.collection().objects)
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
