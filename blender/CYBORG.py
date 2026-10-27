"""
Tiberian Fallout – Nod cyborg (CYBORG), after Tiberian Sun: a hulking half-machine on
the light infantry's rig (E1.py, via infantry.py; wider shoulders and hips, a head
taller than the soldier): a massive chest armour in the house colour with big
pauldrons, a power pack on the back, a segmented metal spine, mechanical legs with
pistons and broad feet, a bald head with a metal skull plate and a glowing red eye;
the left arm armoured, the right forearm a Vulcan gatling with six barrels and an
ammunition drum. The dark metal turns darker still for Nod (nodColour).

Nodes: Soldier (armature, extras walkSpeed), SoldierBody (skinned mesh), Flash (empty
at the gatling's muzzle, on the bone gatling that carries the spinning barrels).

Animations (glTF clips, in place; E1's plus his own)
    Idle, Walk, GoProne, Prone, Crawl, Die1, Die2, DieProne   as E1.py
    Fire    once, 0.4 s: a burst: the barrels spin, the arm shakes, the body leans
            into the recoil

Run headless:

    blender -b --factory-startup --python blender/CYBORG.py [-- --preview <clip:frame,…> <dir>]

Modelled in metres like E1 (1.8 m skeleton), scaled to cells by SCALE (a tenth bigger
than the soldier); Blender Z is up, he looks along -Y (glTF +Z).
"""
import math
import os
import sys

from mathutils import Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import infantry as inf  # noqa: E402
from infantry import kit, box, cylinder, sphere, dome, limb, soldier, srgb, material, tween, body_pose  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), 'public', 'models', 'CYBORG.glb')
BLEND = os.path.join(HERE, 'CYBORG.blend')

NOD_RED = '#c42a1c'     # the house colour of the previews (the game sets the player's)
SCALE = 0.72 / 1.8      # E1: 0.65 / 1.8
SHOULDER, HIP = 0.25, 0.12
BURST_FRAMES = 12
SPIN = 40               # degrees per frame (60 would alias with the six barrels)
GATLING_LENGTH = 0.42


def hands():
    """The right forearm held forward level, the gatling on it; the left arm down by
    his side, the fist a little forward."""
    right = Vector((-0.27, -0.33, 1.08))
    left = Vector((0.3, -0.1, 0.9))
    return {'R': (right + Vector((0, -0.06, 0)), right, Vector((-0.4, 1.0, -1.0))),
            'L': (left - Vector((0, 0, 0.05)), left, Vector((0.4, 1.0, 0.0)))}


def gatling_bone(bones):
    joint, wrist = bones['forearm.R'][0], bones['hand.R'][0]
    axis = (wrist - joint).normalized()
    return {'gatling': (wrist, wrist + axis * GATLING_LENGTH, 'forearm.R')}


def gatling_axis(bones):
    head, tail, _ = bones['gatling']
    return head, (tail - head).normalized()


def body(bones):
    m = inf.base_materials()
    m.update({
        'metal': material('CyborgMetal', srgb('#80848a'), 0.5, 0.35),
        'dark': material('CyborgDark', srgb('#45474d'), 0.55, 0.3),
        'armour': inf.soldier.house_shade('CyborgArmour', 0.9, 0.95, 0.5),
        'armourdark': inf.soldier.house_shade('CyborgArmourDark', 0.55, 0.8, 0.55),
        'eye': material('CyborgEye', srgb('#ff2a1a'), 0.3, emission=srgb('#ff3020'), strength=8.0),
        'cable': material('Cable', srgb('#1e1e1c'), 0.7),
        'skin': material('CyborgSkin', srgb('#b08a72'), 0.65),
    })
    # Nod's own unit: darker metal for Nod (applyHouseColour); the armour's shades are
    # accents, they keep the house colour for Nod instead of turning near black
    for key, colour in (('metal', '#62656b'), ('dark', '#2b2c31')):
        m[key]['nodColour'] = colour
    for key in ('armour', 'armourdark'):
        m[key]['nodAccent'] = True
    parts = []

    def add(bone, *objs):
        parts.extend((obj, bone) for obj in objs)

    # ---- hips and spine: dark metal pelvis, hip joints, a segmented spine
    add('hips',
        kit.frustum('CyPelvis', m['dark'], (0.4, 0.25), (0.38, 0.24), 0.15, (0, 0, 0.85), bevel=0.02),
        box('CyGroin', m['metal'], (0.16, 0.05, 0.14), (0, -0.13, 0.9), bevel=0.015),
        box('CyBelt', m['metal'], (0.42, 0.27, 0.04), (0, 0, 1.0), bevel=0.01))
    for side, s in (('L', 1), ('R', -1)):
        add('hips', cylinder(f'CyHipJoint{side}', m['metal'], 0.075, 0.07, (s * HIP * 1.25, 0, 0.93),
                             rotation=(0, math.pi / 2, 0), segments=14, bevel=0.006))
    for i in range(3):
        add('spine', kit.frustum(f'CySpine{i}', m['dark'] if i % 2 else m['metal'], (0.32, 0.21), (0.34, 0.22), 0.065,
                                 (0, 0, 1.02 + 0.065 * i), bevel=0.012))

    # ---- chest: massive armour in the house colour, plates, a power pack on the back
    add('chest',
        kit.frustum('CyChest', m['armour'], (0.44, 0.3), (0.56, 0.34), 0.25, (0, 0, 1.19), bevel=0.04),
        kit.frustum('CyChestTop', m['armour'], (0.56, 0.34), (0.38, 0.26), 0.06, (0, 0, 1.44), bevel=0.02),
        box('CyChestPlateL', m['armourdark'], (0.15, 0.04, 0.16), (0.09, -0.17, 1.33), bevel=0.015),
        box('CyChestPlateR', m['armourdark'], (0.15, 0.04, 0.16), (-0.09, -0.17, 1.33), bevel=0.015),
        box('CyAbsPlate', m['metal'], (0.2, 0.04, 0.08), (0, -0.155, 1.21), bevel=0.012),
        cylinder('CyCollar', m['dark'], 0.1, 0.06, (0, 0, 1.5), segments=14, bevel=0.008),
        box('CyPowerPack', m['metal'], (0.36, 0.17, 0.32), (0, 0.24, 1.32), bevel=0.03),
        box('CyPowerCore', m['dark'], (0.24, 0.04, 0.2), (0, 0.33, 1.32), bevel=0.01),
        box('CyPowerLight', m['eye'], (0.16, 0.012, 0.025), (0, 0.352, 1.38), bevel=0.003))
    for i in range(3):
        add('chest', box(f'CyVent{i}', m['dark'], (0.28, 0.02, 0.018), (0, 0.352, 1.25 + 0.04 * i), bevel=0.003))
    for side, s in (('L', 1), ('R', -1)):
        add('chest', cylinder(f'CyExhaust{side}', m['dark'], 0.035, 0.12, (s * 0.13, 0.27, 1.52), segments=10, bevel=0.005))

    # ---- head: bald, a metal plate over one side of the skull, a red eye, a jaw guard
    neck_top = bones['head'][0]
    add('neck',
        limb('CyNeck', m['dark'], bones['neck'][0], neck_top + Vector((0, 0, 0.03)), 0.065, 0.058, 10),
        limb('CyNeckCableL', m['cable'], (0.05, 0.03, 1.47), (0.035, 0.02, 1.6), 0.012, 0.012, 6),
        limb('CyNeckCableR', m['cable'], (-0.05, 0.03, 1.47), (-0.035, 0.02, 1.6), 0.012, 0.012, 6))
    centre = neck_top + Vector((0, -0.02, 0.1))
    add('head',
        dome('CyFace', m['skin'], 0.095, centre, -1.0, (0.88, 0.98, 1.1)),
        dome('CySkullPlate', m['metal'], 0.1, centre + Vector((-0.012, 0.012, 0.012)), -0.1, (0.82, 0.98, 1.05)),
        box('CyJaw', m['dark'], (0.15, 0.08, 0.05), centre + Vector((0, -0.06, -0.075)), bevel=0.012),
        box('CyEyePiece', m['metal'], (0.06, 0.04, 0.045), centre + Vector((-0.035, -0.085, 0.015)), bevel=0.008),
        sphere('CyEye', m['eye'], 0.016, centre + Vector((-0.035, -0.108, 0.015)), 8),
        box('CyBrowStripe', m['armour'], (0.025, 0.2, 0.02), centre + Vector((0, 0.0, 0.1)), bevel=0.006))

    # ---- arms: big pauldrons in the house colour, metal upper arms
    for side, s in (('L', 1), ('R', -1)):
        shoulder, joint, wrist = bones[f'upper_arm.{side}'][0], bones[f'forearm.{side}'][0], bones[f'hand.{side}'][0]
        add(f'upper_arm.{side}',
            dome(f'CyPauldron{side}', m['armour'], 0.12, shoulder + Vector((s * 0.03, 0, 0.01)), -0.25, (1.0, 1.1, 0.85)),
            box(f'CyPauldronRim{side}', m['armourdark'], (0.05, 0.22, 0.05), shoulder + Vector((s * 0.12, 0, -0.02)), bevel=0.01),
            limb(f'CyUpperArm{side}', m['metal'], shoulder, joint, 0.07, 0.06, 10),
            sphere(f'CyElbow{side}', m['dark'], 0.065, joint, 12))
        if side == 'L':
            add('forearm.L',
                limb('CyForearmL', m['dark'], joint, wrist, 0.058, 0.05, 10),
                limb('CyBracerL', m['metal'], joint.lerp(wrist, 0.25), joint.lerp(wrist, 0.9), 0.07, 0.062, 8))
            add('hand.L', box('CyFistL', m['metal'], (0.08, 0.09, 0.1), (wrist + bones['hand.L'][1]) / 2, bevel=0.018))

    # ---- legs: mechanical: armoured thighs, big knee joints, pistons, broad feet
    for side, s in (('L', 1), ('R', -1)):
        hip, knee, ankle = bones[f'thigh.{side}'][0], bones[f'shin.{side}'][0], bones[f'foot.{side}'][0]
        add(f'thigh.{side}',
            limb(f'CyThigh{side}', m['metal'], hip, knee, 0.105, 0.08, 10),
            box(f'CyThighPlate{side}', m['dark'], (0.13, 0.05, 0.24), hip.lerp(knee, 0.45) + Vector((0, -0.08, 0)), bevel=0.015))
        add(f'shin.{side}',
            cylinder(f'CyKnee{side}', m['dark'], 0.07, 0.17, knee, rotation=(0, math.pi / 2, 0), segments=14, bevel=0.008),
            box(f'CyKneeCap{side}', m['metal'], (0.11, 0.05, 0.1), knee + Vector((0, -0.075, 0.01)), bevel=0.018),
            limb(f'CyShin{side}', m['dark'], knee, ankle + Vector((0, 0, 0.06)), 0.07, 0.06, 10),
            box(f'CyShinGuard{side}', m['metal'], (0.12, 0.05, 0.3), knee.lerp(ankle, 0.45) + Vector((0, -0.065, 0)), bevel=0.016),
            limb(f'CyPiston{side}', m['steel'], knee + Vector((0, 0.07, -0.04)), ankle + Vector((0, 0.07, 0.06)), 0.018, 0.018, 8),
            limb(f'CyPistonSleeve{side}', m['dark'], knee + Vector((0, 0.07, -0.02)), knee.lerp(ankle, 0.5) + Vector((0, 0.07, 0)),
                 0.03, 0.03, 8),
            cylinder(f'CyAnkle{side}', m['metal'], 0.05, 0.14, ankle, rotation=(0, math.pi / 2, 0), segments=12, bevel=0.006))
        add(f'foot.{side}',
            box(f'CyFoot{side}', m['metal'], (0.15, 0.3, 0.08), ankle + Vector((0, -0.06, -0.05)), bevel=0.02),
            box(f'CyToe{side}', m['dark'], (0.16, 0.08, 0.06), ankle + Vector((0, -0.2, -0.06)), bevel=0.015),
            box(f'CyHeel{side}', m['dark'], (0.12, 0.06, 0.06), ankle + Vector((0, 0.09, -0.06)), bevel=0.015))

    # ---- the gatling: housing over the right forearm with the drum, the barrels in front
    joint, wrist = bones['forearm.R'][0], bones['hand.R'][0]
    head, axis = gatling_axis(bones)
    fore = (wrist - joint).length
    add('forearm.R',
        inf.along('GunHousing', m['dark'], (0.085, fore + 0.06), joint, axis, fore / 2 + 0.02, cyl=True, segments=12),
        inf.along('GunHousingTop', m['metal'], (0.1, fore * 0.8, 0.05), joint, axis, fore * 0.55, 0.07),
        inf.along('GunDrum', m['metal'], (0.1, 0.12, 0.13), joint, axis, fore * 0.45, -0.1),
        inf.along('GunDrumBand', m['armour'], (0.105, 0.03, 0.135), joint, axis, fore * 0.45, -0.1),
        inf.along('GunFeed', m['cable'], (0.04, 0.12, 0.04), joint, axis, fore * 0.75, -0.06),
        inf.along('GunMotor', m['metal'], (0.075, 0.06), joint, axis, fore + 0.02, cyl=True, segments=12))
    add('gatling',
        inf.along('GunSpindle', m['dark'], (0.02, GATLING_LENGTH), head, axis, GATLING_LENGTH / 2, cyl=True, segments=8),
        inf.along('GunClampRear', m['metal'], (0.068, 0.04), head, axis, 0.08, cyl=True, segments=12),
        inf.along('GunClampFront', m['metal'], (0.064, 0.035), head, axis, GATLING_LENGTH - 0.03, cyl=True, segments=12))
    # the barrels round the spindle (one marked in the house colour, so the spin shows)
    side_dir = axis.cross(Vector((0, 0, 1))).normalized()
    up_dir = side_dir.cross(axis).normalized()
    for i in range(6):
        a = 2 * math.pi * i / 6
        offset = side_dir * (0.042 * math.cos(a)) + up_dir * (0.042 * math.sin(a))
        start = head + offset + axis * 0.04
        add('gatling', limb(f'GunBarrel{i}', m['armour'] if i == 0 else m['gun'], start, start + axis * (GATLING_LENGTH - 0.02),
                            0.014, 0.014, 6))
    return parts


def animate(rig, bones, mesh):
    head, axis = gatling_axis(bones)
    inf.flash(rig, 'gatling', head + axis * (GATLING_LENGTH + 0.02))

    lean = [(0, {}), (3, {'hx': 2, 'cx': -5, 'cz': -4, 'dx': 2, 'tl': -4, 'kl': 4, 'tr': 3}),
            (BURST_FRAMES - 3, {'hx': 2, 'cx': -6, 'cz': -4, 'dx': 2, 'tl': -4, 'kl': 4, 'tr': 3}), (BURST_FRAMES, {})]

    def burst(f):
        v = tween(lean, f)
        shake = 1.6 * (1 if f % 2 else -1) if 0 < f < BURST_FRAMES else 0.0
        v['uar'] = v.get('uar', 0.0) + shake
        v['far'] = v.get('far', 0.0) - shake
        deltas = body_pose(v)
        # the barrels spin all through the burst
        deltas['gatling'] = Quaternion(axis, math.radians(SPIN * f))
        return deltas, Vector(), {}, None

    inf.clip(rig, 'Fire', BURST_FRAMES, burst)


if __name__ == '__main__':
    soldier.HOUSE_COLOUR = inf.soldier.housecamo.HOUSE_COLOUR = NOD_RED
    inf.setup('rifle', body, hands, shoulder=SHOULDER, hip=HIP, extra_bones=gatling_bone, scale=SCALE)
    inf.run(OUT, BLEND, animate)
