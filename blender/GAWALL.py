"""
Tiberian Fallout – GDI concrete wall (GAWALL), after Tiberian Sun.

A heavy wall of grey concrete blocks on one cell. Like the sandbags (see GASAND.py) it
is made of pieces the game shows or hides to join up with neighbouring walls
(Battlefield.connectWalls):

    Post     the block in the middle of the cell, always shown: sloped sides, rounded
             edges, a sand-coloured coping strip along its ridge
    ArmXP    a joint from the block to the cell's edge towards world +x (glTF)
    ArmXN    … towards -x
    ArmZP    … towards +z (Blender -y)
    ArmZN    … towards -z (Blender +y)

Between two walls the arms of both cells meet to a lower, sand-coloured joint with a
dark groove on top, so a run of wall reads as block, joint, block … like in the
original.

Animations (glTF clips)
    Build    one-shot, 0.6 s: the block and the joints grow up out of the ground

Run headless:

    blender -b --factory-startup --python blender/GAWALL.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; origin in the middle of the cell on the ground.
"""
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import GACTWR as tower  # noqa: E402 – the preview with another camera

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAWALL.glb')
BLEND = os.path.join(HERE, 'GAWALL.blend')

HEIGHT = 0.46           # the block's ridge
HALF = 0.36             # half the block's foot
TOP = 0.19              # half the block's top
JOINT = 0.3             # height of a joint
JOINT_HALF = 0.11       # half the width of a joint (across the wall)

box, srgb, material = kit.box, kit.srgb, kit.material


def materials():
    return {
        'concrete': material('WallConcrete', srgb('#b4b4ae'), 0.92),
        'concrete_light': material('WallConcreteLight', srgb('#c6c5be'), 0.9),
        'concrete_dark': material('WallConcreteDark', srgb('#6c6c66'), 0.95),
        'coping': material('WallCoping', srgb('#c9a85a'), 0.7),
        'coping_dark': material('WallCopingDark', srgb('#8a7038'), 0.8),
        'dark': material('Dark', srgb('#17181a'), 0.9),
    }


def post(m):
    """The block: a frustum with rounded edges, a footing, a coping on its ridge."""
    parts = [
        box('PostFooting', m['concrete_dark'], (2 * HALF + 0.04, 2 * HALF + 0.04, 0.03), (0, 0, 0.015), bevel=0.006),
        kit.frustum('PostBlock', m['concrete'], (2 * HALF, 2 * HALF), (2 * TOP, 2 * TOP), HEIGHT - 0.03, (0, 0, 0.03), bevel=0.035),
        box('PostCoping', m['coping'], (2 * TOP - 0.04, 2 * TOP - 0.04, 0.02), (0, 0, HEIGHT + 0.004), bevel=0.008),
        box('PostCap', m['concrete_dark'], (0.1, 0.1, 0.012), (0, 0, HEIGHT + 0.016), bevel=0.004),
    ]
    # tie rods on the sloped faces (where the joints would hold)
    for x, y in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        r = (HALF + TOP) / 2 + 0.012
        parts.append(kit.cylinder(f'Rod{x}{y}', m['concrete_dark'], 0.02, 0.012, (x * r, y * r, HEIGHT * 0.5),
                                  rotation=(-1.2 * y, 1.2 * x, 0), segments=10, bevel=0))
    return kit.merge('Post', parts)


def arm(name, m, direction):
    """A joint from the block's flank to the cell's edge, along `direction` (unit x or y)."""
    d = Vector(direction)
    along_x = abs(d.x) > 0.5
    start, end = HALF - 0.08, 0.5
    mid = d * (start + end) / 2
    length = end - start

    def size(l, w, h):
        return (l, w, h) if along_x else (w, l, h)

    parts = [
        box(f'{name}Footing', m['concrete_dark'], size(length + 0.02, 2 * JOINT_HALF + 0.07, 0.03), mid + Vector((0, 0, 0.015)), bevel=0.006),
        kit.frustum(f'{name}Body', m['coping'], size(length, 2 * JOINT_HALF + 0.03, 0)[:2], size(length, 2 * JOINT_HALF - 0.05, 0)[:2],
                    JOINT - 0.03, mid + Vector((0, 0, 0.03)), bevel=0.012),
        box(f'{name}Groove', m['coping_dark'], size(length + 0.004, 0.03, 0.01), mid + Vector((0, 0, JOINT - 0.002)), bevel=0),
    ]
    # a dark band round the joint at the cell's edge (where two joints meet)
    p = d * (end - 0.03) + Vector((0, 0, JOINT * 0.45))
    parts.append(box(f'{name}Band', m['coping_dark'], size(0.03, 2 * JOINT_HALF + 0.012, JOINT * 0.5), p, bevel=0.004))
    return kit.merge(name, parts)


def build():
    kit.COLLECTION = 'GDIWall'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = 20
    scene.frame_current = 0

    m = materials()
    root = kit.empty('GDIWall')
    # glTF +x = Blender +x, glTF +z = Blender -y
    parts = [post(m),
             arm('ArmXP', m, (1, 0, 0)), arm('ArmXN', m, (-1, 0, 0)),
             arm('ArmZN', m, (0, 1, 0)),     # Blender +y
             arm('ArmZP', m, (0, -1, 0))]    # Blender -y
    for obj in parts:
        kit.parent(obj, root)

    # Build: everything grows up out of the ground (scaled in z from the ground)
    for k, obj in enumerate(parts):
        kit.keys(obj, 'scale', {0: Vector((1, 1, kit.HIDDEN)), 2 + k: Vector((1, 1, kit.HIDDEN)),
                                12 + k: Vector((1, 1, 1.06)), 16 + k: Vector((1, 1, 1))})
        kit.to_track(obj, 'Build')
    return len(parts)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        tower.preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2],
                      ortho=1.6, target=(0, 0, 0.2))


if __name__ == '__main__' and bpy.app.background:
    main()
