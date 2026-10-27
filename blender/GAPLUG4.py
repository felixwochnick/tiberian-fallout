"""
Tiberian Fallout – GDI drop pod node (GAPLUG4, Firestorm), an upgrade of the upgrade
center (GAPLUG), after the original's GAPLUG_D.

A squat camouflaged housing on a dark drum: its roof slopes down to the front, a
hatch in the house colour lies on it; in its front a dark launch bay in a heavy steel
frame with guide rails, a red marker panel on its left flank, a white floodlight and
a short aerial on its right shoulder. Its foot locks into one of the upgrade center's
places with four pegs; its origin is the middle of the foot, which the game puts onto
a node PlugSlot1 … 3 (see GAPLUG.py).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 1.2 s: the foot locks in, the drum and the housing grow up, the
             hatch closes, the light and the aerial come up
    Idle     loop, 2 s: the bay's guide lights run down in turn, the lamps blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAPLUG4.py [-- --preview 0,20,36 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z).
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import GAPLUG as plug  # noqa: E402 – foot and materials of the upgrades
import gdibuilding as gb  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAPLUG4.glb')
BLEND = os.path.join(HERE, 'GAPLUG4.blend')

BUILD_END = 36
F = plug.FOOT
DRUM_TOP = F + 0.06
W = 0.19                # half the housing's width
FRONT, BACK = -0.2, 0.19
LOW_TOP, HIGH_TOP = DRUM_TOP + 0.3, DRUM_TOP + 0.38   # the roof at the front and at the back

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def housing(m, root):
    """The camouflaged housing: a prism along x, its roof sloping to the front."""
    z0 = DRUM_TOP
    profile = [(FRONT, z0), (BACK, z0), (BACK, HIGH_TOP), (BACK - 0.08, HIGH_TOP + 0.02), (FRONT + 0.06, LOW_TOP), (FRONT, LOW_TOP - 0.05)]
    shell = gb.camo(gb.prism('Housing', m['sand'], profile, -W, W, 'X', bevel=0.012), root)
    slope = math.atan2(HIGH_TOP + 0.02 - LOW_TOP, BACK - 0.08 - FRONT - 0.06)
    mid = Vector((0, (BACK - 0.08 + FRONT + 0.06) / 2, (HIGH_TOP + 0.02 + LOW_TOP) / 2))
    bay = Vector((0, FRONT - 0.005, z0 + 0.14))
    parts = [
        # the launch bay in its frame, with the guide rails
        box('BayFrame', m['steel'], (0.26, 0.03, 0.24), bay, bevel=0.01),
        box('Bay', m['dark'], (0.19, 0.03, 0.18), bay + Vector((0, -0.006, 0)), bevel=0.004),
        *[box(f'Rail{s}', m['steel_light'], (0.014, 0.012, 0.18), bay + Vector((s * 0.07, -0.02, 0)), bevel=0) for s in (-1, 1)],
        box('BayLintel', m['remap'], (0.3, 0.04, 0.03), bay + Vector((0, -0.006, 0.135)), bevel=0.004),
        # the red marker on the left flank, the grille on the right
        box('Marker', m['remap'], (0.008, 0.12, 0.09), (-W - 0.003, 0.0, z0 + 0.22), bevel=0.002),
        *[box(f'Grille{k}', m['dark'], (0.008, 0.16, 0.01), (W + 0.003, 0.02, z0 + 0.08 + k * 0.025), bevel=0) for k in range(4)],
        # seams round the housing
        box('SeamL', m['steel'], (0.006, BACK - FRONT - 0.02, 0.012), (-W - 0.002, (FRONT + BACK) / 2, z0 + 0.04), bevel=0),
        box('SeamR', m['steel'], (0.006, BACK - FRONT - 0.02, 0.012), (W + 0.002, (FRONT + BACK) / 2, z0 + 0.04), bevel=0),
        # the aerial's foot and the floodlight's bracket
        box('AerialFoot', m['steel'], (0.04, 0.04, 0.03), (W - 0.05, BACK - 0.05, HIGH_TOP + 0.01), bevel=0.004),
    ]
    details = kit.merge('HousingDetails', parts, (0, 0, z0))
    hatch = kit.merge('Hatch', [
        box('HatchPlate', m['remap'], (0.22, 0.17, 0.016), mid + Vector((0, 0, 0.01)), bevel=0.004, rotation=(slope, 0, 0)),
        box('HatchSeam', m['remap_dark'], (0.006, 0.16, 0.018), mid + Vector((0, 0, 0.011)), bevel=0, rotation=(slope, 0, 0)),
        *[box(f'Hinge{s}', m['steel'], (0.04, 0.02, 0.02), mid + Vector((s * 0.08, 0.085, 0.03)), bevel=0.003) for s in (-1, 1)],
    ], mid + Vector((0, 0.085, 0.02)))
    return shell, details, hatch


def build():
    gb.start('GDIDropPodNode', BUILD_END)
    m = plug.plug_materials()
    root = kit.empty('GDIDropPodNode')
    keys = kit.keys
    H = kit.HIDDEN
    foot = plug.plug_foot(m, root)
    kit.pop(foot, 0, 5)

    drum = kit.merge('Drum', [
        cylinder('DrumBody', m['pod_dark'], 0.235, DRUM_TOP - F, (0, 0, (F + DRUM_TOP) / 2), segments=32, bevel=0.006),
        cylinder('DrumBand', m['remap'], 0.24, 0.018, (0, 0, DRUM_TOP - 0.018), segments=32, bevel=0),
    ], (0, 0, F))
    kit.parent(drum, root)
    keys(drum, 'scale', {0: Vector((1, 1, H)), 3: Vector((1, 1, H)), 9: Vector((1, 1, 1))})

    # the housing grows up (its lamps and lights hang from the root, not from it)
    group = kit.parent(kit.empty('HousingGroup', (0, 0, DRUM_TOP)), root)
    shell, details, hatch = housing(m, root)
    for obj in (shell, details, hatch):
        kit.parent(obj, group)
    keys(group, 'scale', {0: Vector((0.5, 0.5, H)), 7: Vector((0.5, 0.5, H)), 18: Vector((1.03, 1.03, 1.05)), 21: Vector((1, 1, 1))})
    keys(hatch, 'rotation_euler', {0: Vector((math.radians(-80), 0, 0)), 18: Vector((math.radians(-80), 0, 0)), 26: Vector((math.radians(3), 0, 0)),
                                   28: Vector((0, 0, 0))})

    # aerial (grows) and floodlight on the right shoulder
    a = Vector((W - 0.05, BACK - 0.05, HIGH_TOP + 0.025))
    aerial = kit.merge('Aerial', [cylinder('AerialMast', m['steel'], 0.007, 0.3, a + Vector((0, 0, 0.15)), segments=8, bevel=0),
                                  beam('AerialBar', m['steel'], a + Vector((-0.04, 0, 0.22)), a + Vector((0.04, 0, 0.22)), 0.006)], a)
    kit.parent(aerial, root)
    kit.grow(aerial, 24, 6, 2)
    lights = []
    gb.beacon('AerialLamp', m, a + Vector((0, 0, 0.3)), 'red', root, 30, kit.flashes((0, 8), (30, 8)), lights)
    fl = Vector((W - 0.03, FRONT + 0.06, LOW_TOP + 0.01))
    flood = kit.merge('Floodlight', [
        box('FloodHead', m['steel'], (0.06, 0.05, 0.045), fl + Vector((0, 0, 0.03)), bevel=0.006),
        box('FloodGlass', m['lamp_white'], (0.048, 0.006, 0.032), fl + Vector((0, -0.027, 0.03)), bevel=0.002),
    ], fl)
    kit.parent(flood, root)
    kit.pop(flood, 26, 5)

    # guide lights down the bay's sides: run down in Idle, their mount comes up in Build
    bay = Vector((0, FRONT - 0.035, DRUM_TOP + 0.14))
    mount = kit.parent(kit.empty('GuideMount', bay), root)
    keys(mount, 'location', {0: bay + Vector((0, 0.15, -0.1)), 20: bay + Vector((0, 0.15, -0.1)), 24: bay})
    guides = []
    for k in range(4):
        z = 0.07 - k * 0.045
        bulbs = [sphere(f'Guide{k}{s}', m['lamp_amber'], 0.009, bay + Vector((s * 0.105, 0, z)), 8) for s in (-1, 1)]
        guides.append(kit.parent(kit.merge(f'Guide{k}', bulbs, bay + Vector((0, 0, z))), mount))

    gb.clips([], lights)
    for k, g in enumerate(guides):
        kit.blink(g, kit.flashes((k * 5, 5), (20 + k * 5, 5), (40 + k * 5, 5)))
        kit.to_track(g, 'Idle')
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=1.3, target=(0, 0, 0.25), bake=512)
