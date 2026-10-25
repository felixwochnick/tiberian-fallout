"""
Tiberian Fallout – GDI sandbags (GASAND), after Tiberian Sun.

A low wall of stacked sandbags on one cell. Walls join up with their neighbours, so
the model is made of pieces the game shows or hides (see Battlefield.connectWalls):

    Post     the pile in the middle of the cell, always shown
    ArmXP    a wall from the middle to the cell's edge towards world +x (glTF)
    ArmXN    … towards -x
    ArmZP    … towards +z (the screen's lower right; Blender -y)
    ArmZN    … towards -z (Blender +y)

Two neighbours in a line give a straight wall, two at right angles a corner, three a
T, four a cross; a sandbag cell on its own is just the post.

Each bag is a plump, rounded pillow in one of three sand shades, laid in staggered
courses (four high, two bags deep), with a little random tilt.

Animations (glTF clips)
    Build    one-shot, 0.6 s: the courses are laid one after another

Run headless:

    Blender -b --factory-startup --python blender/GASAND.py

Units: 1 = one map cell. Blender Z is up; origin in the middle of the cell on the ground.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GASAND.glb')
BLEND = os.path.join(HERE, 'GASAND.blend')

BAG = Vector((0.2, 0.14, 0.085))     # length (along the wall), depth, height
COURSES = 4
POST = 0.18                          # half the post's size

srgb, material = kit.srgb, kit.material


def bag(name, mat, centre, along_x, tilt):
    """One sandbag: a subdivided box rounded into a pillow, flattened on top and bottom."""
    lx, ly, lz = BAG if along_x else (BAG.y, BAG.x, BAG.z)

    def build(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
        for v in bm.verts:
            # push towards a superellipsoid: round sides, plump middle
            c = v.co
            r = Vector((c.x * 2, c.y * 2, c.z * 2))
            n = (abs(r.x) ** 3 + abs(r.y) ** 3 + abs(r.z) ** 4) ** (1 / 3.4)
            if n > 0:
                v.co = c / n
            v.co.x *= lx
            v.co.y *= ly
            v.co.z *= lz * (1 - 0.18 * (abs(c.x) * 2) ** 2)  # thinner towards the tied ends

    obj = kit.mesh_object(name, build)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.location = centre
    obj.rotation_euler = tilt
    return obj


def course_bags(rng, mats, x0, x1, y_rows, z, offset, along_x, prefix):
    """A course of bags from x0 to x1 (along the wall), one row per y in y_rows."""
    out = []
    step = BAG.x * 0.97
    for r, y in enumerate(y_rows):
        x = x0 + (offset + r * 0.5) % 1 * step * 0.5
        k = 0
        while x + step * 0.5 <= x1 + 0.03:
            tilt = (rng.uniform(-0.06, 0.06), rng.uniform(-0.05, 0.05), rng.uniform(-0.12, 0.12))
            c = Vector((x + step / 2, y, z)) if along_x else Vector((y, x + step / 2, z))
            out.append(bag(f'{prefix}_{r}_{k}', rng.choice(mats), c, along_x, tilt))
            x += step
            k += 1
    return out


def piece(name, rng, mats, x0, x1, along_x, sign):
    """Courses of bags between x0 and x1 along one axis; `sign` mirrors it."""
    bags = []
    rows = (-BAG.y * 0.52, BAG.y * 0.52)
    for c in range(COURSES):
        z = BAG.z * 0.45 + c * BAG.z * 0.92
        shrink = c * 0.02   # each course a little narrower, like a real stack
        for b in course_bags(rng, mats, x0, x1, [r * (1 - shrink * 3) for r in rows], z, c * 0.5, along_x, f'{name}{c}'):
            if sign < 0:
                b.location = Vector((-b.location.x, -b.location.y, b.location.z))
            bags.append(b)
    return kit.merge(name, bags)


def post(name, rng, mats):
    """The pile in the middle: crossing courses, so arms in any direction meet it."""
    bags = []
    for c in range(COURSES):
        z = BAG.z * 0.45 + c * BAG.z * 0.92
        along_x = c % 2 == 0
        for r, y in enumerate((-BAG.y * 0.52, BAG.y * 0.52)):
            for k, x in enumerate((-BAG.x * 0.48, BAG.x * 0.48)):
                tilt = (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), rng.uniform(-0.15, 0.15))
                centre = Vector((x, y, z)) if along_x else Vector((y, x, z))
                bags.append(bag(f'{name}{c}_{r}_{k}', rng.choice(mats), centre, along_x, tilt))
    return kit.merge(name, bags)


def build():
    kit.COLLECTION = 'GDISandbags'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = 20
    scene.frame_current = 0

    mats = [material(f'Sandbag{k}', srgb(c), 0.95) for k, c in enumerate(('#b8a477', '#a8936a', '#c4b287'))]
    rng = random.Random(4)
    root = kit.empty('GDISandbags')
    parts = [post('Post', rng, mats)]
    # glTF +x = Blender +x, glTF +z = Blender -y
    parts.append(piece('ArmXP', rng, mats, POST - 0.02, 0.5, True, 1))
    parts.append(piece('ArmXN', rng, mats, POST - 0.02, 0.5, True, -1))
    parts.append(piece('ArmZN', rng, mats, POST - 0.02, 0.5, False, 1))   # Blender +y
    parts.append(piece('ArmZP', rng, mats, POST - 0.02, 0.5, False, -1))  # Blender -y
    for obj in parts:
        kit.parent(obj, root)

    # Build: the stack grows up course by course (scaled in z from the ground)
    for k, obj in enumerate(parts):
        kit.keys(obj, 'scale', {0: Vector((1, 1, kit.HIDDEN)), 2 + k: Vector((1, 1, kit.HIDDEN)),
                                12 + k: Vector((1, 1, 1.08)), 16 + k: Vector((1, 1, 1))})
        kit.to_track(obj, 'Build')
    return len(parts)


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)


if __name__ == '__main__' and bpy.app.background:
    main()
