"""
Tiberian Fallout – GDI firestorm wall section (GAFSDF, Firestorm), after the original.

A low emitter post on one cell: a square steel base with cut corners, on it a round
housing with a pale violet rim, a dark bowl and an emitter dome in its middle. Like
the concrete wall (see GAWALL.py) it is made of parts the game shows or hides to join
up with its neighbours (Battlefield.connectWalls):

    Post     always shown: the base and the emitter
    ArmXP    a low ribbed rail from the base to the cell's edge towards world +x
             (glTF), carrying the power line to the next post
    ArmXN    … towards -x
    ArmZP    … towards +z (Blender -y)
    ArmZN    … towards -z (Blender +y)

    FieldXP … FieldZN   the firestorm's energy wall over the rail of the same
             direction, from the emitter to the cell's edge (two neighbours' fields
             meet without a gap): additive glowing planes (materials Glow*), shown by
             the game only while the firestorm is up and towards connected neighbours

Animations (glTF clips)
    Build    one-shot, 0.6 s: the base, the emitter and the rails grow up out of the
             ground (the fields are not animated)

Run headless:

    blender -b --factory-startup --python blender/GAFSDF.py [-- --preview <dir>]

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
import gdibuilding as gb  # noqa: E402 – slabs, preview

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAFSDF.glb')
BLEND = os.path.join(HERE, 'GAFSDF.blend')

BASE = 0.28             # half the base's width
BASE_TOP = 0.08
EMITTER_R = 0.17
EMITTER_TOP = BASE_TOP + 0.09
RAIL_W = 0.11           # half the rail's width
RAIL_TOP = 0.06
EDGE = 0.503            # the cell's edge (a hair over, so neighbours meet)
FIELD_TOP = 0.95

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    return {
        'steel': material('Steel', srgb('#4a4d50'), 0.45, 0.85),
        'plate': material('FsPlate', srgb('#8e92a0'), 0.55, 0.6),
        'plate_dark': material('FsPlateDark', srgb('#5d6170'), 0.6, 0.6),
        'rim': material('RimViolet', srgb('#b9b6d6'), 0.35, 0.8),
        'dark': material('Dark', srgb('#17181a'), 0.9),
        'remap': material('Remap', srgb('#d8b43a'), 0.55, 0.15),
        'emitter': material('LampEmitter', srgb('#a8b4ff'), 0.2, emission=srgb('#6f80ff'), strength=2),
        'field': material('GlowFirestormField', (0, 0, 0), 1.0, emission=srgb('#5d6cff'), strength=4, alpha=0.35),
        'field_core': material('GlowFirestormCore', (0, 0, 0), 1.0, emission=srgb('#c8d0ff'), strength=6, alpha=0.6),
    }


def post(m):
    parts = [
        gb.slab('Base', m['plate'], gb.chamfered(-BASE, -BASE, BASE, BASE, 0.07), BASE_TOP, inset=0.025, bevel=0.004),
        cylinder('Housing', m['plate_dark'], EMITTER_R, EMITTER_TOP - BASE_TOP, (0, 0, (BASE_TOP + EMITTER_TOP) / 2), segments=32, bevel=0.006),
        gb.lathe('Rim', m['rim'], ((EMITTER_R + 0.012, 0), (EMITTER_R + 0.012, 0.02), (EMITTER_R - 0.03, 0.025), (EMITTER_R - 0.035, 0.0)),
                 (0, 0, EMITTER_TOP - 0.01), 32),
        cylinder('Bowl', m['dark'], EMITTER_R - 0.035, 0.01, (0, 0, EMITTER_TOP + 0.006), segments=32, bevel=0),
        gb.lathe('Dome', m['emitter'], ((0.07, 0), (0.06, 0.03), (0.035, 0.05), (0.001, 0.058)), (0, 0, EMITTER_TOP), 20),
    ]
    for k in range(4):  # bolts in the base's corners, a mark in the house colour on two sides
        a = math.pi / 4 + k * math.pi / 2
        p = Vector((math.cos(a), math.sin(a), 0)) * (BASE - 0.06) * math.sqrt(2) * 0.85
        parts.append(cylinder(f'Bolt{k}', m['steel'], 0.018, 0.012, p + Vector((0, 0, BASE_TOP + 0.002)), segments=10, bevel=0.002))
    for s in (-1, 1):
        parts.append(box(f'Mark{s}', m['remap'], (0.12, 0.008, 0.025), (0, s * (BASE - 0.004), BASE_TOP * 0.55), bevel=0))
        parts.append(box(f'MarkX{s}', m['remap'], (0.008, 0.12, 0.025), (s * (BASE - 0.004), 0, BASE_TOP * 0.55), bevel=0))
    return kit.merge('Post', parts)


def rail(name, m, direction):
    """A low ribbed rail from the base's edge to the cell's edge; origin on the ground
    at its inner end."""
    d = Vector(direction)
    across = Vector((-d.y, d.x, 0))
    a0, a1 = BASE - 0.03, EDGE
    mid = d * (a0 + a1) / 2
    length = a1 - a0
    rot = (0, 0, math.atan2(d.y, d.x))
    parts = [box(f'{name}Rail', m['plate_dark'], (length, 2 * RAIL_W, RAIL_TOP), mid + Vector((0, 0, RAIL_TOP / 2)), bevel=0.004, rotation=rot),
             box(f'{name}Line', m['steel'], (length, 0.04, 0.02), mid + Vector((0, 0, RAIL_TOP + 0.01)), bevel=0.003, rotation=rot)]
    for k in range(3):  # ribs across the rail
        p = d * (a0 + 0.05 + k * 0.075)
        parts.append(box(f'{name}Rib{k}', m['plate'], (0.03, 2 * RAIL_W + 0.02, RAIL_TOP + 0.012), p + Vector((0, 0, (RAIL_TOP + 0.012) / 2)), bevel=0.003, rotation=rot))
    return kit.merge(name, parts, d * a0)


def field(name, m, direction):
    """The energy wall over a rail: a glowing sheet from the emitter's axis to the
    cell's edge, with a brighter core band and streaks; origin on the post's axis."""
    d = Vector(direction)
    rot = (0, 0, math.atan2(d.y, d.x))
    mid = d * EDGE / 2
    zm = (RAIL_TOP + FIELD_TOP) / 2
    parts = [box(f'{name}Sheet', m['field'], (EDGE, 0.03, FIELD_TOP - RAIL_TOP), mid + Vector((0, 0, zm)), bevel=0, rotation=rot),
             box(f'{name}Core', m['field_core'], (EDGE, 0.012, 0.18), mid + Vector((0, 0, RAIL_TOP + 0.12)), bevel=0, rotation=rot)]
    for k, z in enumerate((0.38, 0.6, 0.8)):
        parts.append(box(f'{name}Streak{k}', m['field_core'], (EDGE, 0.016, 0.02), mid + Vector((0, 0, z)), bevel=0, rotation=rot))
    return kit.merge(name, parts, (0, 0, 0))


def build():
    kit.COLLECTION = 'GDIFirestormWall'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = 20
    scene.frame_current = 20

    m = materials()
    root = kit.empty('GDIFirestormWall')
    # glTF +x = Blender +x, glTF +z = Blender -y
    dirs = (('XP', (1, 0, 0)), ('XN', (-1, 0, 0)), ('ZN', (0, 1, 0)), ('ZP', (0, -1, 0)))
    parts = [post(m)] + [rail(f'Arm{n}', m, d) for n, d in dirs]
    for obj in parts:
        kit.parent(obj, root)
    for n, d in dirs:
        kit.parent(field(f'Field{n}', m, d), root)

    # Build: base, emitter and rails grow up out of the ground
    for k, obj in enumerate(parts):
        kit.keys(obj, 'scale', {0: Vector((1, 1, kit.HIDDEN)), 2 + k: Vector((1, 1, kit.HIDDEN)),
                                12 + k: Vector((1, 1, 1.06)), 16 + k: Vector((1, 1, 1))})
        kit.to_track(obj, 'Build')
    return len(kit.collection().objects)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    bpy.context.scene.frame_set(20)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        gb.preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2], 1.6, (0, 0, 0.3))


if __name__ == '__main__' and bpy.app.background:
    main()
