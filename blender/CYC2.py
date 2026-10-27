"""
Tiberian Fallout – Nod cyborg commando (CYC2), after Tiberian Sun: a towering
half-machine, bigger than the cyborg (CYBORG.py), on the light infantry's rig (E1.py,
via infantry.py; broad shoulders and hips): a heavy chest armour and huge pauldrons in
the house colour, a power pack with two cooling fins on the back, a helmeted head with
a red visor slit, mechanical legs with pistons and broad feet; the left arm armoured,
the right forearm a plasma cannon: a heavy housing with cooling rings and a short,
wide barrel, a glowing core in its slots when it fires. The dark metal turns darker
still for Nod (nodColour), the armour keeps the house colour (nodAccent).

Nodes: Soldier (armature, extras walkSpeed), SoldierBody (skinned mesh), Flash (empty
at the cannon's muzzle, on forearm.R). The cannon's glow is part of the mesh on the
bone "charge"; its scale is keyed in every clip: hidden, except while firing.

Animations (glTF clips, in place; E1's plus his own)
    Idle, Walk, GoProne, Prone, Crawl, Die1, Die2, DieProne   as E1.py
    Fire    once, 0.6 s: the core glows up in the cannon's slots, the shot throws the
            arm and the shoulders back, he leans into it and the glow dies away

Run headless:

    blender -b --factory-startup --python blender/CYC2.py [-- --preview <clip:frame,…> <dir>]

Modelled in metres like E1 (1.8 m skeleton), scaled to cells by SCALE (a fifth bigger
than the soldier, a little bigger than the cyborg); Blender Z is up, he looks along
-Y (glTF +Z).
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import infantry as inf  # noqa: E402
from infantry import kit, box, cylinder, sphere, dome, limb, soldier, srgb, material, tween, body_pose  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), 'public', 'models', 'CYC2.glb')
BLEND = os.path.join(HERE, 'CYC2.blend')

NOD_RED = '#c42a1c'     # the house colour of the previews (the game sets the player's)
SCALE = 0.8 / 1.8       # E1: 0.65 / 1.8, CYBORG: 0.72 / 1.8
SHOULDER, HIP = 0.27, 0.13
FIRE_FRAMES = 18
CANNON_LENGTH = 0.5     # from the wrist to the muzzle


def hands():
    """The right forearm (the cannon) held forward level; the left arm down by his side."""
    right = Vector((-0.29, -0.33, 1.1))
    left = Vector((0.33, -0.08, 0.9))
    return {'R': (right + Vector((0, -0.06, 0)), right, Vector((-0.4, 1.0, -1.0))),
            'L': (left - Vector((0, 0, 0.05)), left, Vector((0.4, 1.0, 0.0)))}


def cannon_axis(bones):
    joint, wrist = bones['forearm.R'][0], bones['hand.R'][0]
    return joint, wrist, (wrist - joint).normalized()


def charge_bone(bones):
    _, wrist, axis = cannon_axis(bones)
    return {'charge': (wrist - axis * 0.1, wrist + axis * (CANNON_LENGTH - 0.12), 'forearm.R')}


def body(bones):
    m = inf.base_materials()
    m.update({
        'metal': material('CyborgMetal', srgb('#80848a'), 0.5, 0.35),
        'dark': material('CyborgDark', srgb('#45474d'), 0.55, 0.3),
        'armour': inf.soldier.house_shade('CyborgArmour', 0.9, 0.95, 0.5),
        'armourdark': inf.soldier.house_shade('CyborgArmourDark', 0.55, 0.8, 0.55),
        'eye': material('CyborgEye', srgb('#ff2a1a'), 0.3, emission=srgb('#ff3020'), strength=8.0),
        'cable': material('Cable', srgb('#1e1e1c'), 0.7),
        'white': material('CommandoWhite', srgb('#d6d6d0'), 0.5, 0.2),
        'plasma': material('PlasmaGlow', srgb('#ff8a3a'), 0.4, emission=srgb('#ff7a2a'), strength=10.0),
        'core': material('PlasmaCore', srgb('#fff0c0'), 0.4, emission=srgb('#fff2c8'), strength=14.0),
    })
    for key, colour in (('metal', '#62656b'), ('dark', '#2b2c31'), ('white', '#8a8c90')):
        m[key]['nodColour'] = colour
    for key in ('armour', 'armourdark'):
        m[key]['nodAccent'] = True
    parts = []

    def add(bone, *objs):
        parts.extend((obj, bone) for obj in objs)

    # ---- hips and a segmented spine
    add('hips',
        kit.frustum('CcPelvis', m['dark'], (0.44, 0.27), (0.42, 0.26), 0.16, (0, 0, 0.84), bevel=0.02),
        box('CcGroin', m['metal'], (0.18, 0.05, 0.15), (0, -0.14, 0.9), bevel=0.015),
        box('CcBelt', m['metal'], (0.46, 0.29, 0.045), (0, 0, 1.0), bevel=0.01))
    for side, s in (('L', 1), ('R', -1)):
        add('hips', cylinder(f'CcHipJoint{side}', m['metal'], 0.08, 0.07, (s * HIP * 1.25, 0, 0.93),
                             rotation=(0, math.pi / 2, 0), segments=14, bevel=0.006))
    for i in range(3):
        add('spine', kit.frustum(f'CcSpine{i}', m['dark'] if i % 2 else m['metal'], (0.34, 0.22), (0.36, 0.23), 0.065,
                                 (0, 0, 1.02 + 0.065 * i), bevel=0.012))

    # ---- chest: massive armour, a white stripe down the middle, the power pack with fins
    add('chest',
        kit.frustum('CcChest', m['armour'], (0.46, 0.31), (0.6, 0.36), 0.25, (0, 0, 1.19), bevel=0.04),
        kit.frustum('CcChestTop', m['armour'], (0.6, 0.36), (0.4, 0.27), 0.06, (0, 0, 1.44), bevel=0.02),
        box('CcChestStripe', m['white'], (0.07, 0.04, 0.24), (0, -0.175, 1.3), bevel=0.012),
        box('CcChestPlateL', m['armourdark'], (0.13, 0.04, 0.15), (0.12, -0.17, 1.33), bevel=0.015),
        box('CcChestPlateR', m['armourdark'], (0.13, 0.04, 0.15), (-0.12, -0.17, 1.33), bevel=0.015),
        box('CcAbsPlate', m['metal'], (0.22, 0.04, 0.08), (0, -0.16, 1.2), bevel=0.012),
        cylinder('CcCollar', m['dark'], 0.11, 0.06, (0, 0, 1.5), segments=14, bevel=0.008),
        box('CcPowerPack', m['metal'], (0.4, 0.18, 0.34), (0, 0.26, 1.32), bevel=0.03),
        box('CcPowerCore', m['dark'], (0.26, 0.04, 0.22), (0, 0.36, 1.31), bevel=0.01),
        box('CcPowerLight', m['eye'], (0.18, 0.012, 0.025), (0, 0.382, 1.39), bevel=0.003))
    for i in range(3):
        add('chest', box(f'CcVent{i}', m['dark'], (0.3, 0.02, 0.018), (0, 0.382, 1.23 + 0.04 * i), bevel=0.003))
    for side, s in (('L', 1), ('R', -1)):
        add('chest',
            box(f'CcFin{side}', m['armourdark'], (0.025, 0.16, 0.26), (s * 0.13, 0.3, 1.58), bevel=0.008),
            cylinder(f'CcExhaust{side}', m['dark'], 0.035, 0.1, (s * 0.06, 0.3, 1.52), segments=10, bevel=0.005))

    # ---- head: a closed helmet in the house colour with white stripes and a red visor slit
    neck_top = bones['head'][0]
    add('neck',
        limb('CcNeck', m['dark'], bones['neck'][0], neck_top + Vector((0, 0, 0.03)), 0.07, 0.062, 10),
        limb('CcNeckCableL', m['cable'], (0.055, 0.03, 1.47), (0.04, 0.02, 1.6), 0.013, 0.013, 6),
        limb('CcNeckCableR', m['cable'], (-0.055, 0.03, 1.47), (-0.04, 0.02, 1.6), 0.013, 0.013, 6))
    centre = neck_top + Vector((0, -0.02, 0.1))
    add('head',
        dome('CcHelmet', m['armour'], 0.12, centre, -0.75, (0.95, 1.05, 1.08)),
        box('CcJaw', m['dark'], (0.17, 0.1, 0.07), centre + Vector((0, -0.06, -0.08)), bevel=0.015),
        box('CcVisor', m['dark'], (0.17, 0.04, 0.045), centre + Vector((0, -0.105, 0.0)), bevel=0.01),
        box('CcVisorSlit', m['eye'], (0.13, 0.012, 0.014), centre + Vector((0, -0.126, 0.002)), bevel=0.002),
        box('CcHelmetStripeL', m['white'], (0.022, 0.24, 0.02), centre + Vector((0.035, 0.0, 0.123)), bevel=0.006),
        box('CcHelmetStripeR', m['white'], (0.022, 0.24, 0.02), centre + Vector((-0.035, 0.0, 0.123)), bevel=0.006))

    # ---- arms: huge pauldrons, metal upper arms; the left one armoured with a fist
    for side, s in (('L', 1), ('R', -1)):
        shoulder, joint, wrist = bones[f'upper_arm.{side}'][0], bones[f'forearm.{side}'][0], bones[f'hand.{side}'][0]
        add(f'upper_arm.{side}',
            dome(f'CcPauldron{side}', m['armour'], 0.14, shoulder + Vector((s * 0.035, 0, 0.01)), -0.25, (1.0, 1.1, 0.85)),
            box(f'CcPauldronStripe{side}', m['white'], (0.03, 0.24, 0.03), shoulder + Vector((s * 0.06, 0, 0.115)), bevel=0.008),
            box(f'CcPauldronRim{side}', m['armourdark'], (0.05, 0.25, 0.06), shoulder + Vector((s * 0.14, 0, -0.03)), bevel=0.01),
            limb(f'CcUpperArm{side}', m['metal'], shoulder, joint, 0.075, 0.065, 10),
            sphere(f'CcElbow{side}', m['dark'], 0.07, joint, 12))
        if side == 'L':
            add('forearm.L',
                limb('CcForearmL', m['dark'], joint, wrist, 0.062, 0.054, 10),
                limb('CcBracerL', m['metal'], joint.lerp(wrist, 0.25), joint.lerp(wrist, 0.9), 0.075, 0.066, 8))
            add('hand.L', box('CcFistL', m['metal'], (0.09, 0.1, 0.11), (wrist + bones['hand.L'][1]) / 2, bevel=0.02))

    # ---- legs: armoured thighs, big knee joints, pistons, broad feet
    for side, s in (('L', 1), ('R', -1)):
        hip, knee, ankle = bones[f'thigh.{side}'][0], bones[f'shin.{side}'][0], bones[f'foot.{side}'][0]
        add(f'thigh.{side}',
            limb(f'CcThigh{side}', m['metal'], hip, knee, 0.11, 0.085, 10),
            box(f'CcThighPlate{side}', m['armourdark'], (0.13, 0.05, 0.24), hip.lerp(knee, 0.45) + Vector((0, -0.085, 0)), bevel=0.015))
        add(f'shin.{side}',
            cylinder(f'CcKnee{side}', m['dark'], 0.075, 0.18, knee, rotation=(0, math.pi / 2, 0), segments=14, bevel=0.008),
            box(f'CcKneeCap{side}', m['metal'], (0.12, 0.05, 0.11), knee + Vector((0, -0.08, 0.01)), bevel=0.018),
            limb(f'CcShin{side}', m['dark'], knee, ankle + Vector((0, 0, 0.06)), 0.075, 0.064, 10),
            box(f'CcShinGuard{side}', m['metal'], (0.13, 0.05, 0.3), knee.lerp(ankle, 0.45) + Vector((0, -0.07, 0)), bevel=0.016),
            limb(f'CcPiston{side}', m['steel'], knee + Vector((0, 0.075, -0.04)), ankle + Vector((0, 0.075, 0.06)), 0.019, 0.019, 8),
            limb(f'CcPistonSleeve{side}', m['dark'], knee + Vector((0, 0.075, -0.02)), knee.lerp(ankle, 0.5) + Vector((0, 0.075, 0)),
                 0.032, 0.032, 8),
            cylinder(f'CcAnkle{side}', m['metal'], 0.052, 0.15, ankle, rotation=(0, math.pi / 2, 0), segments=12, bevel=0.006))
        add(f'foot.{side}',
            box(f'CcFoot{side}', m['metal'], (0.16, 0.31, 0.08), ankle + Vector((0, -0.06, -0.05)), bevel=0.02),
            box(f'CcToe{side}', m['dark'], (0.17, 0.08, 0.06), ankle + Vector((0, -0.21, -0.06)), bevel=0.015),
            box(f'CcHeel{side}', m['dark'], (0.13, 0.06, 0.06), ankle + Vector((0, 0.09, -0.06)), bevel=0.015))

    # ---- the plasma cannon over the right forearm: a round housing with an armour
    # saddle, cooling rings, a short wide barrel; between the rings glow bands on the
    # bone "charge" come out of the housing when it fires
    joint, wrist, axis = cannon_axis(bones)
    fore = (wrist - joint).length
    total = fore + CANNON_LENGTH
    add('forearm.R',
        inf.along('CnHousing', m['dark'], (0.085, total - 0.1), joint, axis, (total - 0.1) / 2, cyl=True, segments=14),
        inf.along('CnHousingTop', m['armour'], (0.12, fore * 0.85, 0.05), joint, axis, fore * 0.5, 0.085),
        inf.along('CnHousingStripe', m['white'], (0.03, fore * 0.85, 0.055), joint, axis, fore * 0.5, 0.088),
        inf.along('CnCell', m['metal'], (0.12, 0.16, 0.08), joint, axis, fore * 0.4, -0.1),
        inf.along('CnCellLight', m['eye'], (0.124, 0.02, 0.03), joint, axis, fore * 0.4, -0.1),
        inf.along('CnCable', m['cable'], (0.035, 0.18, 0.035), joint, axis, fore * 0.75, -0.09),
        inf.along('CnBarrel', m['metal'], (0.075, 0.16), joint, axis, total - 0.06, cyl=True, segments=14),
        inf.along('CnMuzzle', m['dark'], (0.09, 0.04), joint, axis, total + 0.02, cyl=True, segments=14),
        inf.along('CnBore', m['cable'], (0.05, 0.012), joint, axis, total + 0.036, cyl=True, segments=12))
    for i in range(4):
        add('forearm.R', inf.along(f'CnRing{i}', m['metal'], (0.102, 0.03), joint, axis, fore + 0.04 + 0.08 * i,
                                   cyl=True, segments=14))
    for i in range(3):
        add('charge', inf.along(f'PlasmaBand{i}', m['plasma'], (0.092, 0.044), joint, axis, fore + 0.08 + 0.08 * i,
                                cyl=True, segments=14))
    add('charge', inf.along('PlasmaMuzzle', m['core'], (0.052, 0.012), joint, axis, total + 0.034, cyl=True, segments=12))
    return parts


def animate(rig, bones, mesh):
    joint, _, axis = cannon_axis(bones)
    fore = (bones['hand.R'][0] - joint).length
    inf.flash(rig, 'forearm.R', joint + axis * (fore + CANNON_LENGTH + 0.08))

    keys = [(0, {}), (5, {'cx': 2, 'uar': -3}),
            (7, {'hx': -3, 'cx': -9, 'cz': -6, 'dx': 4, 'uar': -14, 'far': -8, 'tl': -5, 'kl': 6, 'tr': 4}),
            (11, {'hx': -1, 'cx': -4, 'cz': -3, 'dx': 2, 'uar': -5, 'far': -3, 'tl': -3, 'kl': 4, 'tr': 2}),
            (FIRE_FRAMES, {})]
    glow = [(0, {'s': inf.HIDDEN}), (1, {'s': 0.3}), (6, {'s': 1.0}), (12, {'s': 0.9}), (16, {'s': 0.3}),
            (FIRE_FRAMES, {'s': inf.HIDDEN})]

    def shot(f):
        return body_pose(tween(keys, f)), Vector(), {'charge': tween(glow, f)['s']}, 0.0

    inf.clip(rig, 'Fire', FIRE_FRAMES, shot, mesh)


if __name__ == '__main__':
    soldier.HOUSE_COLOUR = inf.soldier.housecamo.HOUSE_COLOUR = NOD_RED
    inf.setup('rifle', body, hands, shoulder=SHOULDER, hip=HIP, extra_bones=charge_bone, scaled=('charge',), scale=SCALE)
    inf.run(OUT, BLEND, animate)
