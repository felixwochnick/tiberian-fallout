"""
Tiberian Fallout – GDI concrete wall (GAWALL), after Tiberian Sun.

A heavy wall of grey concrete blocks on one cell: each piece is two separate blocks
with a trapezoid cross-section (sloped flanks, rounded ridge) with a groove between
them; where two pieces meet, a sand-coloured joint clamps the ends of their blocks,
standing on a dark footing that spreads out to both sides. Like the sandbags (see
GASAND.py) the wall is made of parts the game shows or hides to join up with its
neighbours (Battlefield.connectWalls):

    Post     always shown: the two blocks of a lone piece – a square hump split in
             two by a groove, its ends sloped. Slightly smaller than the arms' blocks,
             so where arms are shown it lies inside them
    ArmXP    a block from the middle of the cell to the joint at its edge towards
             world +x (glTF), and that half of the joint
    ArmXN    … towards -x
    ArmZP    … towards +z (Blender -y)
    ArmZN    … towards -z (Blender +y)

So a straight run shows two blocks per cell (the groove in the middle of the cell, a
joint at its edge), like the original; a corner, T-piece or crossing joins its blocks
in the middle of the cell. The arm pieces (arm()) are also used by the component
tower (GACTWR) and the gate (GAGATE_A) to run into a wall.

Animations (glTF clips)
    Build    one-shot, 0.6 s: the blocks and joints grow up out of the ground

Run headless:

    blender -b --factory-startup --python blender/GAWALL.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; origin in the middle of the cell on the ground.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAWALL.glb')
BLEND = os.path.join(HERE, 'GAWALL.blend')

HEIGHT = 0.58           # a block's ridge
FOOT = 0.44             # half a block's width at the ground
SHOULDER = (0.35, 0.38)  # (half width, height) where the flank turns towards the ridge
RIDGE = 0.14            # half the width of the ridge
GROOVE = 0.02           # half the groove between the two blocks of a cell
JOINT = 0.06            # length of half a joint (each cell brings one half)
INSET = 0.035           # the post lies this much inside the arms' blocks

box, srgb, material = kit.box, kit.srgb, kit.material


def materials():
    return {
        'concrete': material('WallConcrete', srgb('#a9a9a3'), 0.92),
        'concrete_dark': material('WallConcreteDark', srgb('#5f5f5a'), 0.95),
        'coping': material('WallCoping', srgb('#b8944a'), 0.75),
        'coping_dark': material('WallCopingDark', srgb('#7d6431'), 0.8),
    }


def profile(grow=0.0):
    """Cross-section of a block (across, up), counter-clockwise from the bottom left;
    `grow` moves it outwards (negative: inwards)."""
    (sx, sz), h = SHOULDER, HEIGHT + grow
    return [(-FOOT - grow, 0), (FOOT + grow, 0), (sx + grow, sz + grow * 0.5), (RIDGE + grow, h),
            (-RIDGE - grow, h), (-sx - grow, sz + grow * 0.5)]


def section(along_x, a0, a1, prof, name, mat, bevel):
    """A prism of a cross-section from a0 to a1 along x (or along y)."""
    def build(bm):
        rings = []
        for a in (a0, a1):
            rings.append([bm.verts.new((a, u, v) if along_x else (u, a, v)) for u, v in prof])
        bm.faces.new(rings[0])
        bm.faces.new(rings[1][::-1])
        n = len(prof)
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((rings[0][k], rings[0][j], rings[1][j], rings[1][k]))

    return kit.finish(kit.mesh_object(name, build), mat, bevel, 2)


def arm(name, m, direction, start=GROOVE, end=0.503):
    """A block from `start` (distance from the middle of the cell) to the joint and
    that half of the joint, reaching `end` (the cell's edge), along `direction` (unit
    vector along x or y). The joint: a sand-coloured clamp a little proud of the
    block, on a dark footing spreading to both sides. Origin on the ground under the
    block's inner end."""
    d = Vector(direction)
    along_x = abs(d.x) > 0.5
    sign = d.x if along_x else d.y
    joint = end - JOINT

    def span(a0, a1):
        return (min(a0, a1) * sign, max(a0, a1) * sign) if sign > 0 else (-max(a0, a1), -min(a0, a1))

    parts = [section(along_x, *span(start, joint), profile(), f'{name}Block', m['concrete'], 0.02)]
    parts.append(section(along_x, *span(joint, end), profile(0.018), f'{name}Joint', m['coping'], 0.01))
    # the footing under the joint: a dark plinth that tapers out to both sides
    across = Vector((0, 1, 0)) if along_x else Vector((1, 0, 0))
    a = Vector(direction) * joint
    b = Vector(direction) * end
    for s in (-1, 1):
        o = across * s
        inner, outer = FOOT + 0.004, FOOT + 0.06
        corners = [a + o * inner, b + o * inner, b + o * outer, a + o * (inner + 0.02)]
        top = [a + o * inner + Vector((0, 0, 0.1)), b + o * inner + Vector((0, 0, 0.1)),
               b + o * (inner + 0.015) + Vector((0, 0, 0.025)), a + o * (inner + 0.015) + Vector((0, 0, 0.025))]
        verts = [tuple(v) for v in corners + top]
        parts.append(kit.hexahedron(f'{name}Fin{s}', m['concrete_dark'], verts, 0.004))
    # a dark seam where the joint's half meets the neighbour's (only at the cell's edge)
    parts.append(section(along_x, *span(end - 0.008, end), profile(0.022), f'{name}Seam', m['coping_dark'], 0))
    origin = Vector(direction) * start
    return kit.merge(name, parts, (origin.x, origin.y, 0))


def post(m):
    """The two blocks of a lone piece: a square hump split by a groove across x."""
    foot, ridge, h = FOOT - INSET, RIDGE - INSET * 0.6, HEIGHT - INSET
    sx, sz = SHOULDER[0] - INSET, SHOULDER[1] - INSET * 0.5
    halves = []
    for s in (-1, 1):
        def build(bm, s=s):
            # three rings across the hump (foot, shoulder, ridge), each from the groove
            # to the sloped end: (half width, end, z)
            levels = ((foot, foot, 0), (sx, sx, sz), (ridge, ridge, h))
            rings = []
            for w, e, z in levels:
                xs = (s * GROOVE, s * e)
                rings.append([bm.verts.new((x, y, z)) for x, y in ((xs[0], -w), (xs[1], -w), (xs[1], w), (xs[0], w))])
            bm.faces.new(rings[0])
            bm.faces.new(rings[-1])
            for lo, hi in zip(rings, rings[1:]):
                for k in range(4):
                    j = (k + 1) % 4
                    bm.faces.new((lo[k], lo[j], hi[j], hi[k]))

        halves.append(kit.finish(kit.mesh_object(f'PostHalf{s}', build), m['concrete'], 0.02, 2))
    return kit.merge('Post', halves)


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
    bpy.context.scene.frame_set(20)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        import gdibuilding
        gdibuilding.preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2],
                            1.6, (0, 0, 0.25))


if __name__ == '__main__' and bpy.app.background:
    main()
