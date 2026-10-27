"""
Tiberian Fallout – Nod mutant hijacker (MHIJACK), after Tiberian Sun Firestorm: a
gaunt mutant on the light infantry's rig (E1.py: same clips, via infantry.py), unarmed:
a long, worn olive trench coat with a high collar, a belt and coat tails down to his
knees (they hang from the thighs, so they swing with the legs), shoulder patches in
the house colour, dark trousers and boots; bare, grey-green hands, a pale mutant head
with a white cloth cap, a scar and one glowing eye. His arms hang down and swing as
he walks (like the engineer).

Nodes: Soldier (armature, extras walkSpeed), SoldierBody (skinned mesh), Flash (empty
between his hands as they grab, on hand.R; nothing is fired from it).

Animations (glTF clips, in place; E1's plus his own)
    Idle, Walk, GoProne, Prone, Crawl, Die1, Die2, DieProne   as E1.py
    Fire    once, 0.8 s: the hijack: he crouches, lunges, both hands reach out and
            grab hold of the hatch, wrench it open and he pulls himself up after it

Run headless:

    blender -b --factory-startup --python blender/MHIJACK.py [-- --preview <clip:frame,…> <dir>]

Modelled in metres like E1 (1.8 m tall, scaled to cells by E1.SCALE); Blender Z is up,
he looks along -Y (glTF +Z).
"""
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import infantry as inf  # noqa: E402
from infantry import kit, box, soldier, srgb, material, tween, body_pose, limb, dome, sphere  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), 'public', 'models', 'MHIJACK.glb')
BLEND = os.path.join(HERE, 'MHIJACK.blend')

NOD_RED = '#c42a1c'     # the house colour of the previews (the game sets the player's)
GRAB_FRAMES = 24


def hands():
    """Arms hanging loosely, a little away from the coat."""
    right, left = Vector((-0.26, -0.04, 0.86)), Vector((0.26, -0.04, 0.86))
    return {'R': (right - Vector((0, 0, 0.06)), right, Vector((-0.3, 1.0, 0.0))),
            'L': (left - Vector((0, 0, 0.06)), left, Vector((0.3, 1.0, 0.0)))}


def body(bones):
    m = inf.base_materials()
    coat = material('Coat', srgb('#7d7850'), 0.95)
    m.update({
        'fatigue': coat,
        'coat': coat,
        'coatdark': material('CoatDark', srgb('#5a5838'), 0.95),
        'trousers': material('Trousers', srgb('#2a2a26'), 0.9),
        'skin': material('MutantSkin', srgb('#a4a58a'), 0.75),
        'glove': material('MutantHand', srgb('#8f9278'), 0.8),
        'cloth': material('ClothCap', srgb('#cfcabb'), 0.9),
        'scar': material('Scar', srgb('#7a4a3e'), 0.8),
        'eye': material('MutantEye', srgb('#ffb030'), 0.3, emission=srgb('#ffa020'), strength=7.0),
        'buckle': material('Buckle', srgb('#8a7a52'), 0.4, 0.8),
    })
    parts = []

    def add(bone, *objs):
        parts.extend((obj, bone) for obj in objs)

    # ---- the coat over the body: pelvis, belly, chest, a belt and a high collar
    add('hips',
        kit.frustum('CoatHips', m['coat'], (0.36, 0.24), (0.34, 0.23), 0.14, (0, 0, 0.87), bevel=0.02),
        box('CoatBelt', m['boot'], (0.37, 0.25, 0.04), (0, 0, 1.0), bevel=0.01),
        box('CoatBuckle', m['buckle'], (0.06, 0.012, 0.035), (0, -0.128, 1.0), bevel=0.004))
    add('spine', kit.frustum('CoatBelly', m['coat'], (0.31, 0.21), (0.35, 0.23), 0.2, (0, 0, 1.01), bevel=0.02))
    add('chest',
        kit.frustum('CoatChest', m['coat'], (0.36, 0.24), (0.42, 0.27), 0.27, (0, 0, 1.17), bevel=0.03),
        box('CoatLapelL', m['coatdark'], (0.08, 0.02, 0.22), (0.06, -0.135, 1.33), bevel=0.006),
        box('CoatLapelR', m['coatdark'], (0.08, 0.02, 0.22), (-0.06, -0.135, 1.33), bevel=0.006),
        kit.frustum('CoatCollar', m['coatdark'], (0.3, 0.22), (0.26, 0.2), 0.12, (0, 0.01, 1.42), bevel=0.012),
        box('CoatPocket', m['coatdark'], (0.08, 0.02, 0.07), (0.11, -0.13, 1.24), bevel=0.006),
        box('BackSeam', m['coatdark'], (0.04, 0.02, 0.26), (0, 0.13, 1.3), bevel=0.004))
    # coat tails: one half on each thigh, down to the knee, so they follow the legs
    for side, s in (('L', 1), ('R', -1)):
        x = bones[f'thigh.{side}'][0].x
        add(f'thigh.{side}',
            kit.frustum(f'CoatTail{side}', m['coat'], (0.205, 0.27), (0.19, 0.25), 0.47, (x + s * 0.008, 0, 0.47), bevel=0.012),
            box(f'CoatHem{side}', m['coatdark'], (0.21, 0.275, 0.03), (x + s * 0.008, 0, 0.485), bevel=0.006))

    # ---- head: pale mutant, a white cloth cap, a scar, one glowing eye
    neck_top = bones['head'][0]
    add('neck', limb('Neck', m['skin'], bones['neck'][0], neck_top + Vector((0, 0, 0.03)), 0.05, 0.045))
    centre = neck_top + Vector((0, -0.015, 0.1))
    add('head',
        dome('Face', m['skin'], 0.095, centre, -1.0, (0.85, 0.98, 1.12)),
        box('Jaw', m['skin'], (0.11, 0.09, 0.05), centre + Vector((0, -0.035, -0.08)), bevel=0.018),
        dome('Cap', m['cloth'], 0.1, centre + Vector((0, 0.008, 0.012)), 0.1, (0.9, 1.0, 1.0)),
        box('CapKnot', m['cloth'], (0.04, 0.05, 0.04), centre + Vector((0, 0.1, 0.03)), bevel=0.01),
        box('Scar', m['scar'], (0.012, 0.012, 0.07), centre + Vector((0.04, -0.092, -0.02)), bevel=0.002),
        sphere('EyeL', m['eye'], 0.016, centre + Vector((0.034, -0.088, 0.0)), 8),
        sphere('EyeR', m['boot'], 0.012, centre + Vector((-0.034, -0.086, 0.0)), 8))

    inf.limbs(add, bones, m)
    for obj, _ in parts:
        if obj.name.rstrip('LR') in ('Shin', 'Thigh'):
            obj.data.materials.clear()
            obj.data.materials.append(m['trousers'])
    # no leg pouches under the coat
    for obj, _ in [p for p in parts if p[0].name.startswith('LegPouch')]:
        parts.remove((obj, _))
        bpy.data.objects.remove(obj, do_unlink=True)
    # the house colour: patches on the shoulders (inf.limbs' pads) and cuffs on the sleeves
    for side in ('L', 'R'):
        joint, wrist = bones[f'forearm.{side}'][0], bones[f'hand.{side}'][0]
        add(f'forearm.{side}', limb(f'SleeveCuff{side}', m['coatdark'], joint.lerp(wrist, 0.62), joint.lerp(wrist, 0.78),
                                    0.05, 0.047))
    return parts


def animate(rig, bones, mesh):
    grip = (hands()['R'][0] + hands()['L'][0]) / 2 + Vector((0, -0.45, 0.3))
    inf.flash(rig, 'hand.R', grip)
    keys = [
        (0, {}),
        (5, {'hx': 6, 'sx': 8, 'cx': 10, 'dx': -10, 'ual': 10, 'uar': 10, 'fal': -30, 'far': -30,
             'tl': -28, 'tr': -18, 'kl': 50, 'kr': 36, 'fl': -22, 'fr': -18}),
        (9, {'hx': 10, 'sx': 10, 'cx': 14, 'dx': -14, 'ual': -95, 'uar': -95, 'fal': -10, 'far': -10,
             'tl': -34, 'tr': 6, 'kl': 34, 'kr': 12, 'fl': -2, 'fr': -12}),
        (13, {'hx': 8, 'sx': 6, 'cx': 6, 'dx': -8, 'ual': -80, 'uar': -80, 'fal': -45, 'far': -45,
              'tl': -30, 'tr': 4, 'kl': 30, 'kr': 10, 'fl': 0, 'fr': -10}),
        (17, {'hx': 2, 'sx': -2, 'cx': -6, 'dx': 4, 'ual': -50, 'uar': -50, 'fal': -85, 'far': -85,
              'tl': -14, 'tr': 2, 'kl': 14, 'kr': 6, 'fl': 0, 'fr': -6}),
        (GRAB_FRAMES, {}),
    ]
    inf.clip(rig, 'Fire', GRAB_FRAMES, lambda f: (body_pose(tween(keys, f)), Vector(), {}, 0.0), mesh)


if __name__ == '__main__':
    soldier.HOUSE_COLOUR = inf.soldier.housecamo.HOUSE_COLOUR = NOD_RED
    inf.setup('tools', body, hands)
    inf.run(OUT, BLEND, animate)
