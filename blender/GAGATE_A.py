"""
Tiberian Fallout – GDI gate (GAGATE_A), after Tiberian Sun.

A gate across three cells along x (foundation 3 × 1): a low camouflaged concrete sill
on a dark footing and, along nearly all of it, the gate itself: a tall, narrow wedge
whose two sloped faces are grilles of light vertical bars in a heavy frame in the house
colour. The gate retracts into a slot in the sill to let units through. Two small
lamps on the sill at the gate's ends blink.

Like the wall (GAWALL.py) the gate shows wall stubs at its ends towards neighbouring
walls and component towers (Battlefield.connectWalls): ArmXP and ArmXN (glTF axes),
each a block of the concrete wall from the gate's end to the joint at the edge of the
foundation.

Materials as for the barracks (see GAPILE.py): Camo_* is the baked desert camouflage,
Remap the house colour, Lamp* emissive, Glow* additive halos.

Nodes: GateRise (scaled by Build: the gate comes up) holds Gate (scaled by Open), which
holds the panel – so no channel belongs to two clips.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 1.6 s: the footing and sill spread out, the wall stubs grow,
             the gate comes up out of the sill, the lamps' housings pop up
    Idle     loop, 2 s: the lamps blink in turn
    Open     one-shot, 1 s: the gate sinks into the sill (played backwards it closes)

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAGATE_A.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells are
centred at x = -1, 0, 1; origin in the middle on the ground.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import GACTWR as tower  # noqa: E402 – the preview with another camera
import GAWALL as wall  # noqa: E402 – the wall stubs

kit.COLLECTION = 'GDIGate'  # after the imports, which set their own
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAGATE_A.glb')
BLEND = os.path.join(HERE, 'GAGATE_A.blend')

BUILD_END = 48
OPEN_END = 30
FOOTING = 0.025
SILL = 0.06             # top of the sill
GATE_HALF = 1.34        # half the gate's length
GATE_TOP = 0.74
GATE_BASE = 0.1         # half the gate's thickness at the sill …
GATE_RIDGE = 0.03       # … and at its top
LAMP_X = 1.43           # the lamps on the sill, beyond the gate's ends

box, cylinder, beam, srgb = kit.box, kit.cylinder, kit.beam, kit.srgb


def camo(obj, root):
    obj = kit.merge(obj.name, [obj])
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def sill(m, root):
    """Footing and camouflaged sill with the dark slot the gate sinks into."""
    footing = box('Footing', m['concrete_dark'], (3.0, 0.7, FOOTING), (0, 0, FOOTING / 2), bevel=0.006)
    body = camo(kit.frustum('Sill', m['sand'], (2.98, 0.64), (2.94, 0.58), SILL - FOOTING, (0, 0, FOOTING), bevel=0.01), root)
    slot = [
        box('Slot', m['dark'], (2 * GATE_HALF + 0.02, 2 * GATE_BASE + 0.02, 0.006), (0, 0, SILL + 0.001), bevel=0),
        *[box(f'SlotLip{s}', m['steel'], (2 * GATE_HALF + 0.04, 0.02, 0.012), (0, s * (GATE_BASE + 0.02), SILL + 0.004), bevel=0.003)
          for s in (-1, 1)],
    ]
    return footing, body, kit.merge('Slot', slot)


def gate(m):
    """The gate: a wedge with grilles of bars on its sloped faces; origin at its foot."""
    h = GATE_TOP - SILL
    parts = [kit.hexahedron('GateCore', m['dark'], [
        (-GATE_HALF, -GATE_BASE, SILL), (GATE_HALF, -GATE_BASE, SILL), (GATE_HALF, GATE_BASE, SILL), (-GATE_HALF, GATE_BASE, SILL),
        (-GATE_HALF, -GATE_RIDGE, GATE_TOP), (GATE_HALF, -GATE_RIDGE, GATE_TOP), (GATE_HALF, GATE_RIDGE, GATE_TOP), (-GATE_HALF, GATE_RIDGE, GATE_TOP),
    ], 0.004)]
    for s in (-1, 1):
        foot = Vector((0, s * (GATE_BASE + 0.006), SILL))
        top = Vector((0, s * (GATE_RIDGE + 0.006), GATE_TOP))
        # the frame: bottom, top and ends, in the house colour
        parts.append(beam(f'FrameBottom{s}', m['remap'], foot + Vector((-GATE_HALF, 0, 0.03)), foot + Vector((GATE_HALF, 0, 0.03)), 0.07, 0.03))
        parts.append(beam(f'FrameTop{s}', m['remap'], top + Vector((-GATE_HALF, 0, -0.03)), top + Vector((GATE_HALF, 0, -0.03)), 0.065, 0.03))
        for e in (-1, 1):
            parts.append(beam(f'FrameEnd{s}{e}', m['remap'], foot + Vector((e * (GATE_HALF - 0.02), 0, 0)),
                              top + Vector((e * (GATE_HALF - 0.03), 0, 0)), 0.065, 0.03))
        # the bars between
        bars = 34
        for k in range(bars):
            x = -GATE_HALF + 0.06 + k * (2 * GATE_HALF - 0.12) / (bars - 1)
            parts.append(beam(f'Bar{s}_{k}', m['bar'], foot + Vector((x, 0, 0.04)), top + Vector((x, 0, -0.04)), 0.026, 0.012))
        parts.append(beam(f'Rail{s}', m['steel'], foot.lerp(top, 0.5) + Vector((-GATE_HALF + 0.03, s * 0.006, 0)),
                          foot.lerp(top, 0.5) + Vector((GATE_HALF - 0.03, s * 0.006, 0)), 0.014, 0.014))
    parts.append(box('Ridge', m['steel'], (2 * GATE_HALF, 2 * GATE_RIDGE + 0.03, 0.02), (0, 0, GATE_TOP + 0.005), bevel=0.004))
    return kit.merge('GatePanel', parts, (0, 0, SILL))


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = BUILD_END + 12
    scene.frame_current = BUILD_END

    m = kit.materials()
    m['bar'] = kit.material('GateBar', srgb('#e2d3b0'), 0.55, 0.0)
    wm = wall.materials()
    root = kit.empty('GDIGate')
    keys = kit.keys

    # ---- footing and sill spread out along the gate
    base = kit.parent(kit.empty('Base'), root)
    for obj in sill(m, root):
        kit.parent(obj, base)
    keys(base, 'scale', {0: Vector((0.05, 1, 1)), 2: Vector((0.05, 1, 1)), 14: Vector((1.02, 1, 1)), 17: Vector((1, 1, 1))})

    # ---- the wall stubs at the ends (towards neighbouring walls and towers) grow up
    for name, side in (('ArmXP', 1), ('ArmXN', -1)):
        stub = kit.parent(wall.arm(name, wm, (side, 0, 0), GATE_HALF + 0.005, 1.503), root)
        keys(stub, 'scale', {0: Vector((1, 1, kit.HIDDEN)), 10: Vector((1, 1, kit.HIDDEN)), 24: Vector((1, 1, 1.05)), 28: Vector((1, 1, 1))})

    # ---- two lamps on the sill beyond the gate's ends; the lights hang from the root
    # (a parent scaled to nothing in Build spoils their keys in Idle)
    lights = []
    for i, side in enumerate((-1, 1)):
        spot = Vector((LAMP_X * side, -0.24, SILL))
        housing, light = kit.beacon(f'Lamp{i}', m, spot, 'amber')
        housing = kit.parent(kit.merge(f'Lamp{i}', [housing], spot), root)
        kit.parent(light, root)
        kit.pop(housing, 40 + i * 2, 5)
        lights.append((light, kit.flashes((i * 30, 15))))

    # ---- the gate comes up out of its slot (GateRise: Build; Gate: Open)
    rise = kit.parent(kit.empty('GateRise', (0, 0, SILL)), root)
    panel = kit.parent(kit.empty('Gate', (0, 0, SILL)), rise)
    kit.parent(gate(m), panel)
    keys(rise, 'scale', {0: Vector((1, 1, kit.HIDDEN)), 24: Vector((1, 1, kit.HIDDEN)), 38: Vector((1, 1, 1.04)), 42: Vector((1, 1, 1))})

    # ---- clips
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    for light, pattern in lights:
        kit.blink(light, pattern)
        kit.to_track(light, 'Idle')
    # Open: the gate sinks into the sill (a little at first, then quickly, slowing down)
    keys(panel, 'scale', {0: Vector((1, 1, 1)), 4: Vector((1, 1, 0.97)), OPEN_END: Vector((1, 1, 0.02))})
    kit.to_track(panel, 'Open')
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
        for obj in kit.collection().objects:  # show the gate closed
            for track in (obj.animation_data.nla_tracks if obj.animation_data else []):
                track.mute = track.name == 'Open'
        tower.preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2],
                      ortho=3.4, target=(0, 0, 0.2))


if __name__ == '__main__' and bpy.app.background:
    main()
