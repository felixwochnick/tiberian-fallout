"""
Tiberian Fallout – Nod wall (NAWALL), after Tiberian Sun.

A tall wall of dark grey concrete on one cell. Walls join up with their neighbours
(NAWALL and the gate NAGATE_A), so the model is made of pieces the game shows or hides
(see Battlefield.connectWalls), like the sandbags (GASAND.py):

    Post     the pier in the middle of the cell, always shown: a square column with a
             pointed cap and a sloped fin towards each side – where no slab hides it,
             the fin gives the jagged silhouette of the original's lone wall ends
    ArmXP    a slab from the pier to the cell's edge towards world +x (glTF; Blender +x)
    ArmXN    … towards -x
    ArmZP    … towards +z (Blender -y, the screen's lower left)
    ArmZN    … towards -z (Blender +y)

A slab is battered (wider at the foot), with a chamfered top, vertical grooves and
light streaks below the top on both faces and a dark footing strip; its details hang
on it as "<Arm>Detail". A fin lies wholly inside the slab on its side, so with the arm
shown only the slab is seen. The slab's cross-section (slab_parts) is shared with the
gate's arms (NAGATE_A.py), so wall and gate meet without a step or a gap.

Animations (glTF clips)
    Build    one-shot, 1 s: the pier and then the slabs grow out of the ground

Run headless:

    blender -b --factory-startup --python blender/NAWALL.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; origin in the middle of the cell on the ground.
"""
import math
import os
import sys

from mathutils import Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402

box, beam = kit.box, kit.beam

POST = 0.15            # half the pier's width
POST_TOP = 0.68        # the column's top (the cap's point is higher)
# the slab's cross-section: half widths at the foot, at the shoulder, on the top
FOOT, SHOULDER, CREST = 0.15, 0.115, 0.05
SHOULDER_Z, TOP = 0.52, 0.6
COLOUR = '#595a5d'     # the wall's dark grey concrete


def turned(obj, angle):
    """Turns a merged object about the vertical (origin stays) and applies it."""
    obj.matrix_world = Matrix.Rotation(angle, 4, 'Z') @ obj.matrix_world
    kit.bake_modifiers(obj)
    return obj


def profile():
    """The slab's cross-section (y, z), counter-clockwise seen from +x."""
    return [(-FOOT, 0), (FOOT, 0), (SHOULDER, SHOULDER_Z), (CREST, TOP), (-CREST, TOP), (-SHOULDER, SHOULDER_Z)]


def sweep(name, mat, sections, bevel=0.006):
    """A closed solid through cross-sections (lists of equal count of 3D points, each a
    closed loop), both ends capped."""
    def build(bm):
        rings = [[bm.verts.new(p) for p in s] for s in sections]
        for a, b in zip(rings, rings[1:]):
            n = len(a)
            for k in range(n):
                j = (k + 1) % n
                bm.faces.new((a[k], a[j], b[j], b[k]))
        bm.faces.new(rings[0][::-1])
        bm.faces.new(rings[-1])

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def streak_material():
    mat = kit.material('NodStreak', kit.srgb('#86878a'), 0.85)
    mat['nodColour'] = '#86878a'
    return mat


def slab_parts(name, m, x0, x1, details_from=None):
    """The slab along +x from x0 to x1 (centred on y = 0): (body parts in concrete,
    detail parts); the details start at `details_from` (default x0)."""
    streak = streak_material()
    body = sweep(f'{name}Slab', m['steel'], [[(x, y, z) for y, z in profile()] for x in (x0, x1)])
    details = []
    x0 = x0 if details_from is None else details_from
    length = x1 - x0
    count = max(1, round(length / 0.12))
    for s in (-1, 1):
        def on_face(z):
            """y of the face at height z (below the shoulder), just outside it."""
            return s * (FOOT + (SHOULDER - FOOT) * z / SHOULDER_Z + 0.0015)
        for k in range(count):
            x = x0 + (k + 0.5) * length / count
            # a groove following the batter, a light streak running down from the top
            details.append(beam(f'{name}Groove{s}{k}', m['dark'], (x, on_face(0.05), 0.05), (x, on_face(SHOULDER_Z - 0.03), SHOULDER_Z - 0.03), 0.012, 0.003))
            xs = x + 0.5 * length / count
            if xs < x1 - 0.02:
                details.append(beam(f'{name}Streak{s}{k}', streak, (xs, on_face(SHOULDER_Z - 0.16), SHOULDER_Z - 0.16), (xs, on_face(SHOULDER_Z - 0.02), SHOULDER_Z - 0.02), 0.016, 0.003))
        details.append(box(f'{name}Foot{s}', m['armour_dark'], (length, 0.02, 0.03), ((x0 + x1) / 2, s * (FOOT + 0.006), 0.015), bevel=0.004))
    return [body], details


def post(m, root):
    parts = [
        kit.frustum('Column', m['steel'], (2 * POST, 2 * POST), (2 * POST - 0.03, 2 * POST - 0.03), POST_TOP, (0, 0, 0), bevel=0.01),
        kit.frustum('Cap', m['steel'], (2 * POST - 0.03, 2 * POST - 0.03), (0.03, 0.03), 0.1, (0, 0, POST_TOP), bevel=0.008),
    ]
    for k in range(4):     # the fins towards the sides (inside the slabs when shown)
        fin = kit.hexahedron(f'Fin{k}', m['steel'], (
            (POST - 0.02, -0.035, 0), (0.46, -0.035, 0), (0.46, 0.035, 0), (POST - 0.02, 0.035, 0),
            (POST - 0.02, -0.03, SHOULDER_Z - 0.04), (0.46, -0.03, 0.08), (0.46, 0.03, 0.08), (POST - 0.02, 0.03, SHOULDER_Z - 0.04)), bevel=0.006)
        parts.append(turned(fin, k * math.pi / 2))
    obj = nb.concrete('Post', parts, root, COLOUR)
    details = [box(f'PostBand{k}', m['dark'], (2 * POST - 0.01, 2 * POST - 0.01, 0.016), (0, 0, z), bevel=0)
               for k, z in enumerate((0.2, POST_TOP - 0.06))]
    details.append(box('PostFoot', m['armour_dark'], (2 * POST + 0.04, 2 * POST + 0.04, 0.03), (0, 0, 0.015), bevel=0.006))
    return obj, kit.merge('PostDetail', details)


def arm(name, m, root, angle):
    """A slab from the pier to the cell's edge along +x, turned by `angle`."""
    body, details = slab_parts(name, m, POST - 0.03, 0.5)
    obj = turned(nb.concrete(name, body, root, COLOUR), angle)
    detail = turned(kit.merge(f'{name}Detail', details), angle)
    kit.parent(detail, obj)
    return obj


def build():
    root = nb.start('NodWall', 'NodWall', 30, 30)
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
        nb.grow_z(obj, 1 + 3 * k, 12)
    nb.all_to_build()
    for obj in [pier, *arms]:
        obj.scale = (1, 1, 1)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NAWALL', {'Build': [6, 30]}, ortho=1.6, target=(0, 0, 0.3), texture=256)
