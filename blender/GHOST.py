"""
Tiberian Fallout – GDI Ghost Stalker (GHOST), after Tiberian Sun: a commando on the
light infantry's rig (E1.py: same clips, via infantry.py), a little taller than the
soldier: a dark close-fitting combat suit, an olive armour vest with pouches, shoulder
pads and an arm band in the house colour, a bare, shaved head with a black headband
and dark goggles, a slim pack on his back with a power cable to the gun; in both hands
the railgun: a long, heavy weapon with two parallel rails, coils between them, a power
cell under the receiver and a shoulder stock. When it fires, the coils glow blue.

Nodes: Soldier (armature, extras walkSpeed), SoldierBody (skinned mesh), Flash (empty
at the rails' mouth, on hand.R). The coils' glow is part of the mesh on the bone
"charge"; its scale is keyed in every clip: hidden, except while firing.

Animations (glTF clips, in place; E1's plus his own)
    Idle, Walk, GoProne, Prone, Crawl, Die1, Die2, DieProne   as E1.py
    Fire    once, 0.5 s: the coils light up, the shot kicks the gun and the shoulders
            back, the glow fades

Run headless:

    blender -b --factory-startup --python blender/GHOST.py [-- --preview <clip:frame,…> <dir>]

Modelled in metres like E1 (1.8 m skeleton), scaled to cells by SCALE; Blender Z is
up, he looks along -Y (glTF +Z).
"""
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import infantry as inf  # noqa: E402
from infantry import box, cylinder, soldier, srgb, material, tween, body_pose, limb, dome  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), 'public', 'models', 'GHOST.glb')
BLEND = os.path.join(HERE, 'GHOST.blend')

SCALE = 0.68 / 1.8      # E1: 0.65 / 1.8
FIRE_FRAMES = 15
BUTT, DIR = soldier.RIFLE_BUTT, soldier.RIFLE_DIR
GUN_LENGTH = 1.12       # from the butt to the rails' mouth
COILS = (0.5, 0.95)     # where the coils run along the gun


def charge_bone(bones):
    return {'charge': (BUTT + DIR * COILS[0], BUTT + DIR * COILS[1], 'hand.R')}


def body(bones):
    m = inf.base_materials()
    m.update({
        'fatigue': material('StalkerSuit', srgb('#2f3134'), 0.85),
        'vest': material('StalkerVest', srgb('#4f6234'), 0.8, 0.05),
        'vestdark': material('StalkerVestDark', srgb('#3a4826'), 0.85),
        'skin': material('StalkerSkin', srgb('#b49480'), 0.7),
        'band': material('Headband', srgb('#1a1a1a'), 0.8),
        'goggle': material('Goggles', srgb('#101418'), 0.15, 0.5, emission=srgb('#2a4a3a'), strength=0.3),
        'rail': material('RailSteel', srgb('#3c4046'), 0.5, 0.6),
        'coil': material('RailCoil', srgb('#8a6a3a'), 0.4, 0.8),
        'glow': material('RailGlow', srgb('#7ad0ff'), 0.4, emission=srgb('#6ac8ff'), strength=12.0),
        'cell': material('RailCell', srgb('#3c5a78'), 0.4, 0.3, emission=srgb('#4a90d0'), strength=1.5),
    })
    for key, colour in (('fatigue', '#1f2023'), ('vest', '#2b2c31'), ('vestdark', '#1c1d21'), ('pack', '#252629')):
        m[key]['nodColour'] = colour
    parts = []

    def add(bone, *objs):
        parts.extend((obj, bone) for obj in objs)

    inf.torso(add, m, m['vest'])
    add('chest',
        box('VestPlate', m['vestdark'], (0.28, 0.035, 0.17), (0, -0.14, 1.31), bevel=0.014),
        box('VestStrap', m['band'], (0.05, 0.03, 0.32), (0.05, -0.15, 1.3), bevel=0.006),
        # the slim pack, power cell and cable
        box('Pack', m['pack'], (0.26, 0.13, 0.3), (0, 0.19, 1.3), bevel=0.025),
        box('PackLid', m['vestdark'], (0.27, 0.14, 0.04), (0, 0.19, 1.44), bevel=0.01),
        box('PackCell', m['cell'], (0.14, 0.02, 0.12), (0, 0.262, 1.3), bevel=0.005),
        box('PackStripe', m['remap'], (0.27, 0.14, 0.03), (0, 0.19, 1.2), bevel=0.006),
        cylinder('PackAntenna', m['rail'], 0.008, 0.3, (0.1, 0.22, 1.58), segments=6, bevel=0))
    for i, x in enumerate((-0.12, -0.04, 0.04, 0.12)):
        add('chest', box(f'Pouch{i}', m['vestdark'], (0.065, 0.04, 0.075), (x, -0.145, 1.21), bevel=0.01))
    for x in (-0.12, 0.12):
        add('hips', box(f'BeltPouch{x}', m['pack'], (0.07, 0.045, 0.065), (x, -0.115, 0.99), bevel=0.01))

    # ---- head: shaved, a black headband, dark goggles, a house-colour stripe on the band
    neck_top = bones['head'][0]
    add('neck', limb('Neck', m['skin'], bones['neck'][0], neck_top + Vector((0, 0, 0.03)), 0.055, 0.05))
    centre = neck_top + Vector((0, -0.01, 0.1))
    add('head',
        dome('Face', m['skin'], 0.1, centre, -1.0, (0.88, 0.98, 1.12)),
        box('Jaw', m['skin'], (0.13, 0.1, 0.06), centre + Vector((0, -0.03, -0.075)), bevel=0.02),
        limb('Headband', m['band'], centre + Vector((0, 0, 0.02)), centre + Vector((0, 0, 0.055)), 0.093, 0.09, 14),
        box('BandStripe', m['remap'], (0.03, 0.012, 0.022), centre + Vector((0.04, -0.105, 0.037)), bevel=0.003),
        box('Goggles', m['goggle'], (0.15, 0.03, 0.04), centre + Vector((0, -0.1, -0.005)), bevel=0.01),
        box('BandTail', m['band'], (0.04, 0.1, 0.02), centre + Vector((0, 0.12, 0.0)), bevel=0.005))

    inf.limbs(add, bones, m)
    # the house colour round the left upper arm
    shoulder, joint = bones['upper_arm.L'][0], bones['forearm.L'][0]
    band = shoulder.lerp(joint, 0.5)
    add('upper_arm.L', limb('ArmBand', m['remap'], band - (joint - shoulder).normalized() * 0.03,
                            band + (joint - shoulder).normalized() * 0.03, 0.054, 0.052))

    # ---- the railgun in both hands: stock, receiver with the power cell, two rails with
    # coils between, a muzzle frame
    add('hand.R',
        inf.along('Stock', m['gun'], (0.05, 0.24, 0.1), BUTT, DIR, 0.12, -0.015),
        inf.along('StockPad', m['band'], (0.055, 0.03, 0.11), BUTT, DIR, 0.0, -0.015),
        inf.along('Receiver', m['gun'], (0.07, 0.32, 0.11), BUTT, DIR, 0.36),
        inf.along('ReceiverBand', m['remap'], (0.074, 0.04, 0.114), BUTT, DIR, 0.44),
        inf.along('Cell', m['cell'], (0.06, 0.14, 0.06), BUTT, DIR, 0.36, -0.09),
        inf.along('PistolGrip', m['gun'], (0.035, 0.04, 0.08), BUTT, DIR, 0.22, -0.07),
        inf.along('ForeGrip', m['gun'], (0.035, 0.04, 0.08), BUTT, DIR, 0.4, -0.08),
        inf.along('Scope', m['gun'], (0.024, 0.16), BUTT, DIR, 0.34, 0.08, cyl=True),
        inf.along('ScopeLens', m['goggle'], (0.02, 0.01), BUTT, DIR, 0.42, 0.08, cyl=True),
        inf.along('RailTop', m['rail'], (0.05, GUN_LENGTH - 0.5, 0.025), BUTT, DIR, (GUN_LENGTH + 0.5) / 2, 0.035),
        inf.along('RailBottom', m['rail'], (0.05, GUN_LENGTH - 0.5, 0.025), BUTT, DIR, (GUN_LENGTH + 0.5) / 2, -0.035),
        inf.along('RailSpine', m['gun'], (0.014, GUN_LENGTH - 0.5, 0.05), BUTT, DIR, (GUN_LENGTH + 0.5) / 2, 0.0),
        inf.along('MuzzleFrame', m['gun'], (0.066, 0.04, 0.11), BUTT, DIR, GUN_LENGTH - 0.02))
    n = 6
    for i in range(n):
        at = COILS[0] + (COILS[1] - COILS[0]) * (i + 0.5) / n
        add('hand.R', inf.along(f'Coil{i}', m['coil'], (0.03, 0.035), BUTT, DIR, at, cyl=True, segments=10))
        add('charge', inf.along(f'CoilGlow{i}', m['glow'], (0.036, 0.022), BUTT, DIR, at, cyl=True, segments=10))
    return parts


def animate(rig, bones, mesh):
    inf.flash(rig, 'hand.R', BUTT + DIR * (GUN_LENGTH + 0.04))
    keys = [(0, {}), (4, {'cx': 1, 'ual': -2, 'uar': -2}),
            (6, {'cx': -7, 'dx': 3, 'ual': -7, 'uar': -7, 'fal': -4, 'far': -4, 'tl': -3, 'kl': 4}),
            (FIRE_FRAMES, {})]
    glow = [(0, {'s': inf.HIDDEN}), (1, {'s': 0.4}), (5, {'s': 1.0}), (9, {'s': 0.8}), (13, {'s': 0.3}),
            (FIRE_FRAMES, {'s': inf.HIDDEN})]
    inf.clip(rig, 'Fire', FIRE_FRAMES,
             lambda f: (body_pose(tween(keys, f)), Vector(), {'charge': tween(glow, f)['s']}, 0.0), mesh)


if __name__ == '__main__':
    inf.setup('rifle', body, extra_bones=charge_bone, scaled=('charge',), scale=SCALE)
    inf.run(OUT, BLEND, animate)
