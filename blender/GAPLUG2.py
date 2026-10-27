"""
Tiberian Fallout – GDI seeker control (GAPLUG2), an upgrade of the upgrade center
(GAPLUG), after Tiberian Sun (the original's GAPLUG_E).

A squat camouflaged dome on a dark drum with a band in the house colour, a big white
lens in a steel housing looking out of its front, a small turning tracking dish on
its crown and two thin antennas at its back. Its foot locks into one of the upgrade
center's places with four pegs; its origin is the middle of the foot, which the game
puts onto a node PlugSlot1 … 3 (see GAPLUG.py).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 1.2 s: the foot locks in, the drum and the dome grow up, the lens
             and the dish pop out, the antennas shoot up
    Idle     loop, 2 s: the lens glows and fades, the dish turns, the antenna lamps blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAPLUG2.py [-- --preview 0,20,36 <dir>]

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
OUT = os.path.join(PROJECT, 'public', 'models', 'GAPLUG2.glb')
BLEND = os.path.join(HERE, 'GAPLUG2.blend')

BUILD_END = 36
F = plug.FOOT
DRUM_TOP = F + 0.1
DOME = ((0.25, 0.0), (0.245, 0.06), (0.22, 0.13), (0.17, 0.19), (0.1, 0.225), (0.001, 0.235))
LENS = Vector((0.0, -0.215, DRUM_TOP + 0.06))

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def build():
    gb.start('GDISeekerControl', BUILD_END)
    m = plug.plug_materials()
    root = kit.empty('GDISeekerControl')
    keys = kit.keys
    foot = plug.plug_foot(m, root)
    kit.pop(foot, 0, 5)

    # ---- the drum and the dome
    drum = kit.merge('Drum', [
        cylinder('DrumBody', m['pod_dark'], 0.24, DRUM_TOP - F, (0, 0, (F + DRUM_TOP) / 2), segments=32, bevel=0.006),
        cylinder('DrumBand', m['remap'], 0.245, 0.03, (0, 0, DRUM_TOP - 0.03), segments=32, bevel=0),
        *[box(f'DrumRib{k}', m['steel'], (0.02, 0.012, DRUM_TOP - F - 0.04), (math.cos(a) * 0.243, math.sin(a) * 0.243, F + 0.035),
              bevel=0, rotation=(0, 0, a + math.pi / 2)) for k, a in enumerate(2 * math.pi * (j + 0.5) / 10 for j in range(10))],
    ], (0, 0, F))
    kit.parent(drum, root)
    keys(drum, 'scale', {0: Vector((1, 1, kit.HIDDEN)), 3: Vector((1, 1, kit.HIDDEN)), 11: Vector((1, 1, 1.05)), 13: Vector((1, 1, 1))})
    shell = gb.camo(gb.lathe('Dome', m['sand'], DOME, (0, 0, DRUM_TOP), 40), root)
    seams = [beam(f'DomeSeam{k}', m['sand_light'], (math.cos(a) * 0.235, math.sin(a) * 0.235, DRUM_TOP + 0.08),
                  (math.cos(a) * 0.12, math.sin(a) * 0.12, DRUM_TOP + 0.218), 0.012, 0.008)
             for k, a in enumerate(math.pi / 4 + math.pi / 2 * j for j in range(4))]
    seams.append(cylinder('Crown', m['steel'], 0.06, 0.03, (0, 0, DRUM_TOP + 0.24), segments=20, bevel=0.004))
    dome = kit.merge('DomeTrim', seams, (0, 0, DRUM_TOP))
    group = kit.parent(kit.empty('DomeGroup', (0, 0, DRUM_TOP)), root)
    for obj in (shell, dome):
        kit.parent(obj, group)
    keys(group, 'scale', {0: Vector((0.3, 0.3, kit.HIDDEN)), 8: Vector((0.3, 0.3, kit.HIDDEN)), 18: Vector((1.03, 1.03, 1.05)), 21: Vector((1, 1, 1))})

    # ---- the lens: a white eye in a steel housing (its glow on its own node)
    lens = kit.merge('Lens', [
        cylinder('LensHousing', m['steel'], 0.085, 0.08, LENS + Vector((0, 0.03, 0)), rotation=(math.pi / 2, 0, 0), segments=24, bevel=0.008),
        cylinder('LensRim', m['steel_light'], 0.072, 0.014, LENS + Vector((0, -0.012, 0)), rotation=(math.pi / 2, 0, 0), segments=24, bevel=0.003),
        sphere('LensGlass', m['lamp_white'], 0.058, LENS + Vector((0, -0.004, 0)), 16),
        box('LensHood', m['steel'], (0.17, 0.06, 0.014), LENS + Vector((0, -0.01, 0.085)), bevel=0.003, rotation=(math.radians(-12), 0, 0)),
    ], LENS)
    kit.parent(lens, root)
    kit.pop(lens, 18, 6)
    # the glow comes out of the drum with the lens (moved, not scaled: Idle scales it)
    glow_mount = kit.parent(kit.empty('LensGlowMount', LENS), root)
    keys(glow_mount, 'location', {0: LENS + Vector((0, 0.12, -0.05)), 19: LENS + Vector((0, 0.12, -0.05)), 23: LENS})
    glow = kit.parent(sphere('LensGlow', m['glow_white'], 0.1, LENS + Vector((0, -0.03, 0)), 12), glow_mount)
    glow.scale = (0.6, 0.6, 0.6)

    # ---- the tracking dish on the crown (turns in Idle; Build pops its mount only)
    top = Vector((0, 0, DRUM_TOP + 0.255))
    # (it comes up out of the crown: moved, not scaled, as the dish turns in Idle)
    mount = kit.parent(kit.merge('DishMount', [cylinder('DishPost', m['steel'], 0.014, 0.05, top + Vector((0, 0, 0.025)), segments=10, bevel=0)], top), root)
    keys(mount, 'location', {0: top - Vector((0, 0, 0.12)), 20: top - Vector((0, 0, 0.12)), 26: top + Vector((0, 0, 0.006)), 28: top})
    turner = kit.parent(kit.empty('DishTurn', top + Vector((0, 0, 0.05))), mount)
    hz = top + Vector((0, 0, 0.05))
    dish = kit.merge('Dish', [
        cylinder('DishBowl', m['steel_light'], 0.075, 0.025, hz + Vector((0, -0.01, 0.03)), rotation=(math.radians(-60), 0, 0), segments=20, radius2=0.025),
        beam('DishFeed', m['steel'], hz + Vector((0, -0.01, 0.03)), hz + Vector((0, -0.07, 0.065)), 0.006),
        box('DishYoke', m['steel'], (0.05, 0.02, 0.03), hz + Vector((0, 0, 0.012)), bevel=0.003),
    ], hz)
    kit.parent(dish, turner)

    # ---- the antennas at the back, with lamps
    lights = []
    for k, (x, y, h) in enumerate(((-0.1, 0.17, 0.5), (0.12, 0.15, 0.38))):
        foot_at = Vector((x, y, DRUM_TOP + 0.13))
        mast = kit.merge(f'Antenna{k}', [
            box(f'AntFoot{k}', m['steel'], (0.04, 0.04, 0.04), foot_at + Vector((0, 0, 0.0)), bevel=0.003),
            cylinder(f'AntMast{k}', m['steel'], 0.008, h, foot_at + Vector((0, 0, h / 2)), segments=8, bevel=0),
            beam(f'AntBar{k}', m['steel'], foot_at + Vector((-0.05, 0, h * 0.75)), foot_at + Vector((0.05, 0, h * 0.75)), 0.006),
        ], foot_at)
        kit.parent(mast, root)
        kit.grow(mast, 24 + 3 * k, 7, 2)
        gb.beacon(f'AntLamp{k}', m, foot_at + Vector((0, 0, h)), 'red', root, 30 + 2 * k, kit.flashes((k * 15, 6), (30 + k * 15, 6)), lights)

    idle = [(turner, lambda o: gb.spin(o, 1)), (glow, lambda o: gb.pulse(o, 0.5, 1.0, 2))]
    gb.clips(idle, lights)
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=1.3, target=(0, 0, 0.3), bake=512)
