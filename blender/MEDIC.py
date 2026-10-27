"""
Tiberian Fallout – GDI medic (MEDIC), after Tiberian Sun: the light infantry's soldier
(E1.py: same rig, camouflage and clips, via infantry.py) in light grey-white armour
with a red cross on chest, back, helmet and armband, shoulder pads in the house
colour, a white helmet with a green visor, a medic's pack on his back and the grey
medical case with red crosses in his right hand; unarmed, his arms hang down and
swing as he walks (like the engineer).

Nodes: Soldier (armature, extras walkSpeed), SoldierBody (skinned mesh).

Animations (glTF clips, in place; E1's plus his own)
    Idle, Walk, GoProne, Prone, Crawl, Die1, Die2, DieProne   as E1.py
    Fire    once, 0.6 s: healing: he bends forward, both hands reach out and tend
            to the wounded, then he straightens up again

Run headless:

    blender -b --factory-startup --python blender/MEDIC.py [-- --preview <clip:frame,…> <dir>]

Modelled in metres like E1 (1.8 m tall, scaled to cells by E1.SCALE); Blender Z is up,
he looks along -Y (glTF +Z).
"""
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import infantry as inf  # noqa: E402
from infantry import box, soldier, srgb, material, tween  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), 'public', 'models', 'MEDIC.glb')
BLEND = os.path.join(HERE, 'MEDIC.blend')
HEAL_FRAMES = 18


def hands():
    """Arms hanging down, the case in the right hand (as the engineer's toolbox)."""
    right, left = Vector((-0.25, -0.03, 0.85)), Vector((0.24, -0.02, 0.87))
    return {'R': (right, right + Vector((0, 0, 0.06)), Vector((-0.3, 1.0, 0.0))),
            'L': (left, left + Vector((0, 0, 0.06)), Vector((0.3, 1.0, 0.0)))}


def body(bones):
    m = inf.base_materials()
    m.update({
        'armour': material('MedicArmour', srgb('#c8ccce'), 0.55, 0.05),
        'trim': material('MedicTrim', srgb('#8d9296'), 0.6, 0.2),
        'cross': material('RedCross', srgb('#c41e1a'), 0.5),
        'medvisor': material('MedicVisor', srgb('#1c3022'), 0.1, 0.4, emission=srgb('#4c8a4a'), strength=0.5),
        'case': material('MedicCase', srgb('#a4a9ad'), 0.45, 0.5),
    })
    # Nod would wear them dark (applyHouseColour), the cross stays red
    for key, colour in (('armour', '#3a3c42'), ('trim', '#25262a'), ('case', '#4a4c52')):
        m[key]['nodColour'] = colour
    parts = []

    def add(bone, *objs):
        parts.extend((obj, bone) for obj in objs)

    inf.torso(add, m, m['armour'])
    for x in (-0.11, 0.11):
        add('hips', box(f'BeltPouch{x}', m['armour'], (0.07, 0.045, 0.065), (x, -0.115, 0.99), bevel=0.01))
    # chest plate with the red cross, side pouches; the medic's pack on the back
    add('chest',
        box('VestPlate', m['armour'], (0.28, 0.035, 0.18), (0, -0.14, 1.31), bevel=0.014),
        box('VestTrim', m['trim'], (0.43, 0.28, 0.025), (0, 0, 1.19), bevel=0.008),
        *inf.cross('ChestCross', m['cross'], (0, -0.16, 1.31), 0.12, 1),
        box('MedPack', m['armour'], (0.3, 0.15, 0.3), (0, 0.2, 1.29), bevel=0.03),
        box('MedPackLid', m['trim'], (0.31, 0.16, 0.04), (0, 0.2, 1.43), bevel=0.012),
        *inf.cross('BackCross', m['cross'], (0, 0.28, 1.27), 0.13, 1),
        box('MedPackSideL', m['trim'], (0.04, 0.1, 0.16), (0.17, 0.2, 1.25), bevel=0.01),
        box('MedPackSideR', m['trim'], (0.04, 0.1, 0.16), (-0.17, 0.2, 1.25), bevel=0.01))
    for i, x in enumerate((-0.14, 0.14)):
        add('chest', box(f'Pouch{i}', m['trim'], (0.07, 0.04, 0.08), (x, -0.145, 1.22), bevel=0.01))

    # white helmet with a green visor and a red cross above it
    centre = inf.helmet_head(add, bones, m, m['armour'], m['medvisor'], stripe=False)
    add('head', *inf.cross('HelmetCross', m['cross'], centre + Vector((0, -0.112, 0.07)), 0.055, 1, 0.01))

    inf.limbs(add, bones, m)
    # an armband with the red cross round the left upper arm
    shoulder, joint = bones['upper_arm.L'][0], bones['forearm.L'][0]
    band = shoulder.lerp(joint, 0.45)
    add('upper_arm.L',
        inf.limb('ArmBand', m['armour'], band - (joint - shoulder).normalized() * 0.03,
                 band + (joint - shoulder).normalized() * 0.03, 0.054, 0.052),
        *inf.cross('ArmCross', m['cross'], band + Vector((0.054, 0, 0)), 0.04, 0, 0.008))

    # the medical case in the right hand, a red cross on either side
    grip = hands()['R'][0]
    lid = grip - Vector((0, 0, 0.05))
    case = lid - Vector((0, 0, 0.085))
    add('hand.R',
        box('MedCase', m['case'], (0.11, 0.3, 0.15), case, bevel=0.015),
        box('MedCaseLid', m['armour'], (0.115, 0.305, 0.03), lid, bevel=0.008),
        box('MedCaseLatchF', m['trim'], (0.12, 0.02, 0.03), lid - Vector((0, 0.1, 0.025)), bevel=0.003),
        box('MedCaseLatchB', m['trim'], (0.12, 0.02, 0.03), lid - Vector((0, -0.1, 0.025)), bevel=0.003),
        box('MedCaseHandle', m['trim'], (0.02, 0.14, 0.02), grip + Vector((0, 0, -0.01)), bevel=0.004),
        *inf.cross('CaseCrossL', m['cross'], case + Vector((0.058, 0, 0)), 0.09, 0, 0.008),
        *inf.cross('CaseCrossR', m['cross'], case - Vector((0.058, 0, 0)), 0.09, 0, 0.008))
    return soldier.finish_parts(parts)


def animate(rig, bones, mesh):
    """Fire: the healing gesture."""
    keys = [
        (0, {}),
        (6, {'sx': 14, 'cx': 20, 'nx': -10, 'dx': -14, 'ual': -62, 'uar': -50, 'fal': -38, 'far': -28,
             'tl': -10, 'tr': -6, 'kl': 18, 'kr': 14, 'fl': -8, 'fr': -8}),
        (10, {'sx': 16, 'cx': 22, 'nx': -10, 'dx': -10, 'ual': -70, 'uar': -52, 'fal': -30, 'far': -30,
              'tl': -12, 'tr': -7, 'kl': 22, 'kr': 16, 'fl': -10, 'fr': -9}),
        (13, {'sx': 15, 'cx': 21, 'nx': -10, 'dx': -12, 'ual': -60, 'uar': -50, 'fal': -42, 'far': -28,
              'tl': -11, 'tr': -6, 'kl': 20, 'kr': 15, 'fl': -9, 'fr': -8}),
        (HEAL_FRAMES, {}),
    ]
    inf.clip(rig, 'Fire', HEAL_FRAMES,
             lambda f: (inf.body_pose(tween(keys, f)), Vector(), {}, 0.0), mesh)


if __name__ == '__main__':
    inf.setup('tools', body, hands)
    inf.run(OUT, BLEND, animate)
