"""
Tiberian Fallout – Nod wall (NAWALL), after Tiberian Sun.

A tall wall of grey concrete on one cell. Walls join up with their neighbours, so the
model is made of pieces the game shows or hides (see Battlefield.connectWalls), like
the sandbags (GASAND.py):

    Post     the pier in the middle of the cell, always shown: a square column with
             a pointed cap and four sloped blades out to its corners, the jagged
             silhouette of the original
    ArmXP    a slab from the pier to the cell's edge towards world +x (glTF)
    ArmXN    … towards -x
    ArmZP    … towards +z (the screen's lower right; Blender -y)
    ArmZN    … towards -z (Blender +y)

A slab has a chamfered top, vertical grooves on both faces and a dark footing strip;
its details hang on it as "<Arm>Detail".

Animations (glTF clips)
    Build    one-shot, 0.8 s: the pier and then the slabs grow out of the ground

Run headless:

    blender -b --factory-startup --python blender/NAWALL.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; origin in the middle of the cell on the ground.
"""
import math
import os
import sys

from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodbuilding as nb  # noqa: E402

box, beam = kit.box, kit.beam

POST = 0.11            # half the pier's width
POST_TOP = 0.6
ARM_TOP = 0.46
THICK = 0.17           # the slab's thickness at the foot


def turned(obj, angle):
    """Turns a merged object about the vertical (origin stays) and applies it."""
    obj.matrix_world = Matrix.Rotation(angle, 4, 'Z') @ obj.matrix_world
    kit.bake_modifiers(obj)
    return obj


def post(m, root):
    t = THICK / 2
    parts = [
        kit.frustum('Column', m['steel'], (2 * POST + 0.02, 2 * POST + 0.02), (2 * POST, 2 * POST), POST_TOP - 0.1, (0, 0, 0), bevel=0.01),
        kit.frustum('Cap', m['steel'], (2 * POST, 2 * POST), (0.03, 0.03), 0.12, (0, 0, POST_TOP - 0.1), bevel=0.008),
    ]
    for k in range(4):     # the blades out to the corners
        a = math.pi / 4 + k * math.pi / 2
        blade = kit.hexahedron(f'Blade{k}', m['steel'], (
            (POST * 0.8, -0.025, 0), (0.33, -0.025, 0), (0.33, 0.025, 0), (POST * 0.8, 0.025, 0),
            (POST * 0.8, -0.018, POST_TOP - 0.02), (0.33, -0.018, 0.16), (0.33, 0.018, 0.16), (POST * 0.8, 0.018, POST_TOP - 0.02)), bevel=0.008)
        parts.append(turned(blade, a))
    obj = nb.concrete('Post', parts, root, 'grey')
    details = [box(f'PostBand{k}', m['dark'], (2 * POST + 0.004, 2 * POST + 0.004, 0.012), (0, 0, z), bevel=0) for k, z in enumerate((0.14, 0.4))]
    details.append(box('PostFoot', m['armour_dark'], (2 * POST + 0.05, 2 * POST + 0.05, 0.03), (0, 0, 0.015), bevel=0.006))
    return obj, kit.merge('PostDetail', details)


def arm(name, m, root, angle):
    """A slab from the pier to the cell's edge along +x, turned by `angle`."""
    x0, x1 = POST - 0.02, 0.5
    t = THICK / 2
    slab = kit.hexahedron(f'{name}Slab', m['steel'], (
        (x0, -t, 0), (x1, -t, 0), (x1, t, 0), (x0, t, 0),
        (x0, -t * 0.75, ARM_TOP - 0.05), (x1, -t * 0.75, ARM_TOP - 0.05), (x1, t * 0.75, ARM_TOP - 0.05), (x0, t * 0.75, ARM_TOP - 0.05)), bevel=0.006)
    cap = kit.hexahedron(f'{name}Cap', m['steel'], (
        (x0, -t * 0.82, ARM_TOP - 0.06), (x1, -t * 0.82, ARM_TOP - 0.06), (x1, t * 0.82, ARM_TOP - 0.06), (x0, t * 0.82, ARM_TOP - 0.06),
        (x0, -0.02, ARM_TOP), (x1, -0.02, ARM_TOP), (x1, 0.02, ARM_TOP), (x0, 0.02, ARM_TOP)), bevel=0.006)
    obj = turned(nb.concrete(name, [slab, cap], root, 'grey'), angle)
    details = []
    for s in (-1, 1):
        for k, x in enumerate((0.2, 0.3, 0.4)):
            # grooves following the slab's batter
            details.append(beam(f'{name}Groove{s}{k}', m['dark'], (x, s * (t + 0.001), 0.05), (x, s * (t * 0.75 + 0.001), ARM_TOP - 0.07), 0.012, 0.004))
        details.append(box(f'{name}Foot{s}', m['armour_dark'], (x1 - x0, 0.02, 0.03), ((x0 + x1) / 2, s * (t + 0.006), 0.015), bevel=0.004))
    detail = turned(kit.merge(f'{name}Detail', details), angle)
    kit.parent(detail, obj)
    return obj


def build():
    root = nb.start('NodWall', 'NodWall', 30)
    m = nb.materials()
    pier, pier_detail = post(m, root)
    kit.parent(pier, root)
    kit.parent(pier_detail, pier)
    # glTF +x = Blender +x, glTF +z = Blender -y
    arms = [arm(name, m, root, angle) for name, angle in (
        ('ArmXP', 0.0), ('ArmZN', math.pi / 2), ('ArmXN', math.pi), ('ArmZP', -math.pi / 2))]
    for obj in arms:
        kit.parent(obj, root)
    for k, obj in enumerate([pier, *arms]):
        nb.grow_z(obj, 1 + 2 * k, 12)
    nb.all_to_build()
    for obj in [pier, *arms]:
        obj.scale = (1, 1, 1)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAWALL', {'Build': [6, 24]}, scale=1.4, target=(0, 0, 0.25), texture=256)
