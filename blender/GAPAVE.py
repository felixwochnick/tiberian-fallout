"""
Tiberian Fallout – GDI pavement (GAPAVE), after Tiberian Sun.

A field of concrete plates on 4 × 4 cells (foundation 4 × 4), flat just above the
ground: half-cell plates with bevelled edges in a few slightly different grey tones,
laid on a dark bed that shows in the joints; here and there an oil stain, a patched
plate or a drain. The field's outer edge is a kerb of darker concrete.

Animations (glTF clips)
    Build    one-shot, 1 s: the bed spreads, the rows of plates are laid one after
             another from the back to the front

Run headless:

    blender -b --factory-startup --python blender/GAPAVE.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells are
centred at -1.5 … 1.5 in x and y; origin in the middle on the ground.
"""
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import GACTWR as tower  # noqa: E402 – the preview with another camera

kit.COLLECTION = 'GDIPavement'  # after the imports, which set their own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAPAVE.glb')
BLEND = os.path.join(HERE, 'GAPAVE.blend')

SIZE = 4.0              # cells per side
PLATES = 8              # plates per side (half a cell each)
BED = 0.012             # top of the dark bed
TOP = 0.03              # top of the plates
GAP = 0.012             # width of a joint
BUILD_END = 30

box, cylinder, srgb, material = kit.box, kit.cylinder, kit.srgb, kit.material


def materials():
    tones = ('#9a9c97', '#a3a59f', '#92948f', '#aaa9a1')
    return {
        'plates': [material(f'Pave{k}', srgb(c), 0.93) for k, c in enumerate(tones)],
        'bed': material('PaveBed', srgb('#4c4c48'), 0.95),
        'kerb': material('PaveKerb', srgb('#7c7d78'), 0.92),
        'stain': material('PaveStain', srgb('#6a6a63'), 0.7),
        'patch': material('PavePatch', srgb('#b4b2a8'), 0.95),
        'steel': material('Steel', srgb('#4a4d50'), 0.45, 0.85),
        'dark': material('Dark', srgb('#17181a'), 0.9),
    }


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = BUILD_END + 6
    scene.frame_current = 0

    m = materials()
    rng = random.Random(7)
    root = kit.empty('GDIPavement')
    half = SIZE / 2
    step = SIZE / PLATES

    # ---- the dark bed and the kerb round it
    bed = [box('Bed', m['bed'], (SIZE - 0.02, SIZE - 0.02, BED), (0, 0, BED / 2), bevel=0.004)]
    for k, (sx, sy, x, y) in enumerate(((SIZE, 0.05, 0, half - 0.025), (SIZE, 0.05, 0, -half + 0.025),
                                        (0.05, SIZE - 0.1, half - 0.025, 0), (0.05, SIZE - 0.1, -half + 0.025, 0))):
        bed.append(box(f'Kerb{k}', m['kerb'], (sx - 0.004, sy - 0.004, TOP + 0.004), (x, y, (TOP + 0.004) / 2), bevel=0.008))
    base = kit.parent(kit.merge('Bed', bed), root)
    kit.keys(base, 'scale', {0: Vector((0.05, 0.05, 1)), 1: Vector((0.05, 0.05, 1)), 8: Vector((1, 1, 1))})
    kit.to_track(base, 'Build')

    # ---- the plates, one object per row (along x), laid from the back (+y) to the front
    inner = half - 0.05      # inside the kerb
    for row in range(PLATES):
        y0 = half - row * step
        y = y0 - step / 2
        parts = []
        for col in range(PLATES):
            x = -half + (col + 0.5) * step
            # the outer plates stop at the kerb
            x_lo, x_hi = max(x - step / 2, -inner), min(x + step / 2, inner)
            y_lo, y_hi = max(y - step / 2, -inner), min(y + step / 2, inner)
            cx, cy = (x_lo + x_hi) / 2, (y_lo + y_hi) / 2
            height = TOP - BED + rng.uniform(-0.002, 0.002)
            mat = rng.choice(m['plates'])
            parts.append(box(f'Plate{row}_{col}', mat, (x_hi - x_lo - GAP, y_hi - y_lo - GAP, height),
                             (cx, cy, BED + height / 2), bevel=0.006))
            roll = rng.random()
            if roll < 0.12:    # an oil stain
                r = rng.uniform(0.06, 0.13)
                stain = cylinder(f'Stain{row}_{col}', m['stain'], r, 0.002, (cx + rng.uniform(-0.1, 0.1), cy + rng.uniform(-0.1, 0.1), BED + height + 0.001),
                                 segments=12, bevel=0)
                stain.scale = (1, rng.uniform(0.5, 0.9), 1)
                for poly in stain.data.polygons:
                    poly.use_smooth = False  # flat, not a dome
                parts.append(stain)
            elif roll < 0.2:   # a patched corner
                parts.append(box(f'Patch{row}_{col}', m['patch'], (0.14, 0.12, 0.003),
                                 (cx + rng.choice((-1, 1)) * 0.08, cy + rng.choice((-1, 1)) * 0.08, BED + height + 0.0015), bevel=0))
            elif roll < 0.24:  # a drain
                parts.append(box(f'Drain{row}_{col}', m['steel'], (0.12, 0.12, 0.004), (cx, cy, BED + height + 0.002), bevel=0.002))
                for k in range(3):
                    parts.append(box(f'DrainSlot{row}_{col}_{k}', m['dark'], (0.09, 0.012, 0.002), (cx, cy - 0.03 + k * 0.03, BED + height + 0.004), bevel=0))
        obj = kit.parent(kit.merge(f'Row{row}', parts, (0, y0, 0)), root)
        start = 4 + row * 3
        kit.keys(obj, 'scale', {0: Vector((1, kit.HIDDEN, kit.HIDDEN)), start: Vector((1, kit.HIDDEN, kit.HIDDEN)),
                                start + 5: Vector((1, 1, 1.3)), start + 7: Vector((1, 1, 1))})
        kit.to_track(obj, 'Build')
    return len(kit.collection().objects)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        tower.preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2],
                      ortho=5.5, target=(0, 0, 0))


if __name__ == '__main__' and bpy.app.background:
    main()
