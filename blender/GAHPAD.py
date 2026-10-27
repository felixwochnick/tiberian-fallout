"""
Tiberian Fallout – GDI helipad (GAHPAD), after Tiberian Sun.

An octagonal landing deck in the desert camouflage on a dark footing (foundation 2 × 2
cells), its sloped rim set with landing lights; on the deck a dark landing circle with
a yellow ring and a yellow cross. At the back corner a small control booth with a
window band, a beacon and an antenna, and beside it fuel tanks in the house colour on
a cradle, joined to the deck by a hose.

The empty node Pad marks where an aircraft lands, in the middle of the circle on the
deck; its -Y is the direction the aircraft faces when it stands on the pad.

Materials as for the barracks (see GAPILE.py): Camo_* is the baked desert camouflage,
Remap the house colour, Lamp* emissive, Glow* additive halos.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2 s: the footing spreads, the deck rises, the circle is painted,
             booth, tanks and lights come up
    Idle     loop, 2 s: the landing lights run round the rim (twice), the booth's
             beacon blinks

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAHPAD.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); seen in the game, (-0.5, 0.5) is the top one.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import GAPOWR as plant  # noqa: E402 – lathe()
import GACTWR as tower  # noqa: E402 – octagon(), the preview with another camera

kit.COLLECTION = 'GDIHelipad'  # after the imports, which set their own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAHPAD.glb')
BLEND = os.path.join(HERE, 'GAHPAD.blend')

BUILD_END = 60
FOOTING = 0.025
DECK = 0.1              # top of the deck: where an aircraft stands
DECK_R = 0.86           # corner radius of the octagonal deck at the top
CENTRE = Vector((0.12, -0.12, 0))   # the landing circle, moved off the booth's corner
BOOTH = Vector((-0.68, 0.68, 0))

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = plant.materials()
    m['paint'] = material('PaintYellow', srgb('#e0b840'), 0.6)
    m['paint_white'] = material('PaintWhite', srgb('#d8d6cc'), 0.6)
    m['pad_dark'] = material('PadDark', srgb('#2c2e2f'), 0.85)
    return m


def deck(m, root):
    """The camouflaged deck: an octagon with sloped sides (one material, baked)."""
    obj = tower.octagon('Deck', m['sand'], ((DECK_R + 0.06, 0), (DECK_R + 0.06, 0.012), (DECK_R, DECK - FOOTING)), FOOTING, 0.006)
    obj = kit.merge('Deck', [obj])
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material('Camo_Deck', root))
    return obj


def markings(m):
    """The landing circle with its ring and cross, and a few seams in the deck."""
    c = CENTRE + Vector((0, 0, DECK))
    parts = [
        cylinder('Circle', m['pad_dark'], 0.5, 0.006, c + Vector((0, 0, 0.003)), segments=48, bevel=0),
        plant.lathe('Ring', m['paint'], ((0.53, 0), (0.53, 0.008), (0.47, 0.008)), c, 48),
        cylinder('RingInner', m['pad_dark'], 0.47, 0.009, c + Vector((0, 0, 0.0045)), segments=48, bevel=0),
    ]
    for k, a in enumerate((0, math.pi / 2)):
        d = Vector((math.cos(a), math.sin(a), 0)) * 0.36
        parts.append(beam(f'Cross{k}', m['paint'], c - d + Vector((0, 0, 0.01)), c + d + Vector((0, 0, 0.01)), 0.07, 0.004))
    # a grating ring inside the circle
    for k in range(16):
        a = 2 * math.pi * k / 16
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'Grate{k}', m['grating'], c + d * 0.4 + Vector((0, 0, 0.008)), c + d * 0.45 + Vector((0, 0, 0.008)), 0.03, 0.004))
    # seams of the deck plates
    flat = DECK_R * math.cos(math.pi / 8) - 0.04   # stay inside the octagon
    for k, (along_x, at) in enumerate(((True, -0.35), (True, 0.45), (False, -0.4), (False, 0.65))):
        reach = min(flat, flat * math.sqrt(2) - abs(at))
        a, b = ((-reach, at), (reach, at)) if along_x else ((at, -reach), (at, reach))
        parts.append(beam(f'Seam{k}', m['concrete_dark'], (*a, DECK + 0.001), (*b, DECK + 0.001), 0.012, 0.003))
    return kit.merge('Markings', parts, c)


def booth(m):
    """The control booth on its own footing in the back corner; origin at its foot."""
    b = BOOTH
    face = math.atan2(-b.y, -b.x)  # looks towards the pad
    parts = [
        box('BoothFooting', m['concrete_dark'], (0.34, 0.34, FOOTING), b + Vector((0, 0, FOOTING / 2)), bevel=0.004, rotation=(0, 0, face)),
        box('BoothBody', m['sand'], (0.26, 0.24, 0.2), b + Vector((0, 0, FOOTING + 0.1)), bevel=0.012, rotation=(0, 0, face)),
        box('BoothBand', m['remap'], (0.265, 0.245, 0.02), b + Vector((0, 0, FOOTING + 0.04)), bevel=0, rotation=(0, 0, face)),
        box('BoothRoof', m['steel'], (0.3, 0.28, 0.025), b + Vector((0, 0, FOOTING + 0.212)), bevel=0.006, rotation=(0, 0, face)),
        box('BoothCab', m['sand_light'], (0.16, 0.14, 0.09), b + Vector((0, 0, FOOTING + 0.27)), bevel=0.01, rotation=(0, 0, face)),
    ]
    d = Vector((math.cos(face), math.sin(face), 0))
    side = Vector((-d.y, d.x, 0))
    # window bands on the cab (towards the pad and both sides) and a door
    parts.append(box('CabWindow', m['window'], (0.012, 0.13, 0.04), b + d * 0.08 + Vector((0, 0, FOOTING + 0.28)), bevel=0, rotation=(0, 0, face)))
    for s in (-1, 1):
        parts.append(box(f'CabWindow{s}', m['window'], (0.12, 0.012, 0.04), b + side * 0.07 * s + Vector((0, 0, FOOTING + 0.28)), bevel=0, rotation=(0, 0, face)))
    parts.append(box('Door', m['dark'], (0.012, 0.08, 0.13), b + d * 0.131 + Vector((0, 0, FOOTING + 0.075)), bevel=0.002, rotation=(0, 0, face)))
    parts.append(box('CabRoof', m['steel'], (0.18, 0.16, 0.015), b + Vector((0, 0, FOOTING + 0.322)), bevel=0.004, rotation=(0, 0, face)))
    parts.append(beam('Antenna', m['steel'], b - d * 0.05 + Vector((0, 0, FOOTING + 0.33)), b - d * 0.05 + Vector((0, 0, FOOTING + 0.55)), 0.006))
    # a small dish on the roof
    parts.append(cylinder('Dish', m['steel_light'], 0.05, 0.02, b + side * 0.1 + Vector((0, 0, FOOTING + 0.25)),
                          rotation=(math.radians(50), 0, face), segments=16, radius2=0.015))
    return kit.merge('Booth', parts, b)


def tanks(m):
    """Two fuel tanks in the house colour on a cradle along the back left edge."""
    centre = Vector((-0.66, -0.05, 0))
    parts = [box('Cradle', m['concrete_dark'], (0.24, 0.46, 0.04), centre + Vector((0, 0, 0.02)), bevel=0.006)]
    for k, x in enumerate((-0.06, 0.06)):
        p = centre + Vector((x, 0, 0.1))
        parts += [
            cylinder(f'Tank{k}', m['remap'], 0.055, 0.36, p, rotation=(math.pi / 2, 0, 0), segments=20, bevel=0.01),
            *[cylinder(f'TankCap{k}{s}', m['steel'], 0.04, 0.03, p + Vector((0, 0.19 * s, 0)), rotation=(math.pi / 2, 0, 0), segments=16, bevel=0.006)
              for s in (-1, 1)],
            *[cylinder(f'TankStrap{k}{y}', m['steel'], 0.058, 0.014, p + Vector((0, y, 0)), rotation=(math.pi / 2, 0, 0), segments=20, bevel=0)
              for y in (-0.11, 0.11)],
            *[box(f'TankLeg{k}{y}', m['steel'], (0.1, 0.03, 0.06), p + Vector((0, y, -0.05)), bevel=0.004) for y in (-0.11, 0.11)],
        ]
    parts.append(cylinder('Valve', m['steel_light'], 0.012, 0.06, centre + Vector((0, -0.25, 0.08)), segments=8, bevel=0))
    parts.append(beam('Pipe', m['steel'], centre + Vector((0, -0.25, 0.05)), centre + Vector((0.2, -0.25, 0.05)), 0.016))
    return kit.merge('Tanks', parts, centre)


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = BUILD_END + 12
    scene.frame_current = BUILD_END

    m = materials()
    root = kit.empty('GDIHelipad')
    keys = kit.keys

    # ---- the footing spreads, the deck rises
    footing = kit.parent(tower.octagon('Footing', m['concrete_dark'], ((DECK_R + 0.1, 0), (DECK_R + 0.1, FOOTING)), 0, 0.004), root)
    keys(footing, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 14: Vector((1.02, 1.02, 1)), 17: Vector((1, 1, 1))})
    deck_group = kit.parent(kit.empty('DeckGroup'), root)
    kit.parent(deck(m, root), deck_group)
    keys(deck_group, 'location', {0: Vector((0, 0, -0.1)), 10: Vector((0, 0, -0.1)), 24: Vector((0, 0, 0.004)), 27: Vector((0, 0, 0))})

    # ---- the landing circle is painted; the pad node on it
    marks = kit.parent(markings(m), deck_group)
    keys(marks, 'scale', {0: Vector((1, 1, 1)) * kit.HIDDEN, 24: Vector((1, 1, 1)) * kit.HIDDEN, 34: Vector((1.04, 1.04, 1)), 37: Vector((1, 1, 1))})
    pad = kit.parent(kit.empty('Pad', CENTRE + Vector((0, 0, DECK))), deck_group)
    pad.empty_display_size = 0.3

    # ---- booth and tanks
    hut = kit.parent(booth(m), root)
    kit.grow(hut, 28, 12, 2)
    fuel = kit.parent(tanks(m), root)
    kit.pop(fuel, 36, 8)

    # ---- landing lights round the rim and the booth's beacon
    lights = []
    flat = math.cos(math.pi / 8)
    for k in range(8):
        a = 2 * math.pi * k / 8
        p = Vector((math.cos(a), math.sin(a), 0)) * (DECK_R * flat - 0.05) + Vector((0, 0, DECK))
        colour = 'green' if k % 2 else 'amber'
        housing, light = kit.beacon(f'Rim{k}', m, p, colour)
        housing = kit.parent(kit.merge(f'Rim{k}', [housing], p), deck_group)
        kit.parent(light, housing)
        kit.pop(housing, 40 + k * 2, 5)
        # running round the rim twice a loop
        lights.append((light, kit.flashes((k * 30 // 8, 5), (30 + k * 30 // 8, 5))))
    p = BOOTH + Vector((0, 0, FOOTING + 0.33))
    housing, light = kit.beacon('Beacon', m, p, 'red')
    housing = kit.parent(kit.merge('Beacon', [housing], p), hut)
    kit.parent(light, housing)
    kit.pop(housing, 44, 5)
    lights.append((light, kit.flashes((0, 15))))

    # ---- clips
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    for light, pattern in lights:
        kit.blink(light, pattern)
        kit.to_track(light, 'Idle')
    return len(kit.collection().objects)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(1024)
    bpy.context.scene.frame_set(BUILD_END)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        tower.preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2],
                      ortho=2.9, target=(0, 0, 0.2))


if __name__ == '__main__' and bpy.app.background:
    main()
