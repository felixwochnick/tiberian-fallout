"""
Tiberian Fallout – GDI ion cannon uplink (GAPLUG3), an upgrade of the upgrade center
(GAPLUG), after Tiberian Sun (the original's GAPLUG_F).

A tall camouflaged column standing in a round cage of steel bars on a dark drum, a
collar in the house colour at the cage's top; on the column's head a yoke carrying a
large parabolic dish with its feed horn, tilted towards the front. Its foot locks into
one of the upgrade center's places with four pegs; its origin is the middle of the
foot, which the game puts onto a node PlugSlot1 … 3 (see GAPLUG.py).

Animations (glTF clips, merged from the NLA tracks of the same name; no channel is
shared between them)
    Build    one-shot, 1.4 s: the foot locks in, the drum and the cage come up, the
             column grows, the head with the dish rises onto it
    Idle     loop, 2 s: the head sweeps a little to and fro, the lamps blink
    Fire     one-shot, 1.5 s (the ion cannon fires): the dish swings up to the sky,
             its feed glows bright blue, then it swings back and the glow fades

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAPLUG3.py [-- --preview 0,20,42 <dir>]

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
OUT = os.path.join(PROJECT, 'public', 'models', 'GAPLUG3.glb')
BLEND = os.path.join(HERE, 'GAPLUG3.blend')

BUILD_END = 42
FIRE_END = 45
F = plug.FOOT
DRUM_TOP = F + 0.07
CAGE_TOP = 0.42
COLUMN_TOP = 0.62
HEAD = Vector((0, 0, COLUMN_TOP))
DISH_PIVOT = HEAD + Vector((0, 0, 0.09))
REST_TILT = math.radians(50)    # the dish looks this far down from straight up, to the front
DISH_R = 0.22

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def dish(m, root):
    """The parabolic dish about DISH_PIVOT, looking straight up (Z): (bowl, feed glow)."""
    c = DISH_PIVOT
    profile = [(0.03, 0.0), (0.08, 0.012), (0.14, 0.035), (0.19, 0.065), (DISH_R, 0.088), (DISH_R + 0.012, 0.092)]
    inner = [(r - 0.012, z + 0.012) for r, z in profile]

    bowl = gb.lathe('DishBowl', m['steel_light'], [(0.001, -0.02)] + profile, c + Vector((0, 0, 0.02)), 40)
    face = gb.lathe('DishFace', m['plate'], [(0.001, -0.005)] + inner, c + Vector((0, 0, 0.022)), 40)
    parts = [bowl, face,
             cylinder('DishRim', m['remap'], DISH_R + 0.016, 0.012, c + Vector((0, 0, 0.115)), segments=40, bevel=0),
             cylinder('DishHub', m['steel'], 0.045, 0.04, c + Vector((0, 0, 0.01)), segments=16, bevel=0.004)]
    feed = c + Vector((0, 0, 0.24))
    for k in range(3):  # the struts carrying the feed horn
        a = math.pi / 2 + 2 * math.pi * k / 3
        parts.append(beam(f'FeedStrut{k}', m['steel'], c + Vector((math.cos(a) * 0.19, math.sin(a) * 0.19, 0.105)), feed, 0.008))
    parts.append(cylinder('FeedHorn', m['steel'], 0.022, 0.05, feed + Vector((0, 0, -0.01)), segments=12, bevel=0.003, radius2=0.012))
    parts.append(sphere('FeedTip', m['lamp_blue'], 0.014, feed + Vector((0, 0, -0.04)), 10))
    body = kit.merge('Dish', parts, c)
    glow = kit.merge('FeedGlow', [sphere('FeedGlowCore', m['glow_blue'], 0.06, feed + Vector((0, 0, -0.04)), 12),
                                  sphere('FeedGlowHalo', m['glow_white'], 0.11, feed + Vector((0, 0, -0.04)), 12),
                                  cylinder('BeamStub', m['glow_blue'], 0.025, 0.4, feed + Vector((0, 0, 0.17)), segments=10, bevel=0, radius2=0.002)],
                     feed + Vector((0, 0, -0.04)))
    return body, glow


def build():
    gb.start('GDIIonUplink', BUILD_END)
    m = plug.plug_materials()
    root = kit.empty('GDIIonUplink')
    keys = kit.keys
    H = kit.HIDDEN
    foot = plug.plug_foot(m, root)
    kit.pop(foot, 0, 5)

    # ---- drum and cage
    drum = kit.merge('Drum', [
        cylinder('DrumBody', m['pod_dark'], 0.235, DRUM_TOP - F, (0, 0, (F + DRUM_TOP) / 2), segments=32, bevel=0.006),
        cylinder('DrumBand', m['remap'], 0.24, 0.02, (0, 0, DRUM_TOP - 0.02), segments=32, bevel=0),
    ], (0, 0, F))
    kit.parent(drum, root)
    keys(drum, 'scale', {0: Vector((1, 1, H)), 3: Vector((1, 1, H)), 9: Vector((1, 1, 1))})
    bars = []
    for k in range(12):
        a = 2 * math.pi * (k + 0.5) / 12
        d = Vector((math.cos(a), math.sin(a), 0))
        bars.append(beam(f'CageBar{k}', m['steel'], d * 0.21 + Vector((0, 0, DRUM_TOP)), d * 0.2 + Vector((0, 0, CAGE_TOP)), 0.022, 0.016))
    for k, z in enumerate((DRUM_TOP + 0.12, DRUM_TOP + 0.24)):
        bars.append(plug.ring(f'CageHoop{k}', m['steel_light'], ((0.205, -0.004), (0.222, -0.004), (0.222, 0.014), (0.205, 0.014)), (0, 0, z), 32))
    bars.append(plug.ring('Collar', m['remap'], ((0.17, 0), (0.235, 0.0), (0.235, 0.04), (0.17, 0.04)), (0, 0, CAGE_TOP - 0.02), 32, 0.003))
    cage = kit.parent(kit.merge('Cage', bars, (0, 0, DRUM_TOP)), root)
    keys(cage, 'scale', {0: Vector((1, 1, H)), 6: Vector((1, 1, H)), 16: Vector((1, 1, 1.04)), 19: Vector((1, 1, 1))})

    # ---- the column (camouflage), with its trims
    column = gb.camo(gb.lathe('Column', m['sand'], ((0.11, 0), (0.11, 0.2), (0.095, 0.4), (0.085, COLUMN_TOP - DRUM_TOP)), (0, 0, DRUM_TOP), 24), root)
    trims = kit.merge('ColumnTrim', [
        cylinder('ColumnRing0', m['steel'], 0.115, 0.02, (0, 0, DRUM_TOP + 0.2), segments=24, bevel=0.002),
        cylinder('ColumnRing1', m['steel'], 0.1, 0.02, (0, 0, COLUMN_TOP - 0.01), segments=24, bevel=0.002),
        box('ColumnHatch', m['steel_light'], (0.07, 0.01, 0.12), (0, -0.108, DRUM_TOP + 0.09), bevel=0.003),
        box('ColumnCable', m['dark'], (0.018, 0.018, 0.4), (0.07, 0.07, DRUM_TOP + 0.25), bevel=0, rotation=(0, 0, math.pi / 4)),
    ], (0, 0, DRUM_TOP))
    col_group = kit.parent(kit.empty('ColumnGroup', (0, 0, DRUM_TOP)), root)
    for obj in (column, trims):
        kit.parent(obj, col_group)
    keys(col_group, 'scale', {0: Vector((0.6, 0.6, H)), 10: Vector((0.6, 0.6, H)), 24: Vector((1, 1, 1.03)), 27: Vector((1, 1, 1))})

    # ---- the head rises onto the column (moved, never scaled: it sweeps in Idle and
    # the dish tilts in Fire)
    lift = kit.parent(kit.empty('HeadLift', HEAD), root)
    head = kit.parent(kit.empty('Head', HEAD), lift)
    yoke = kit.merge('Yoke', [
        cylinder('Turntable', m['pod_dark'], 0.09, 0.03, HEAD + Vector((0, 0, 0.015)), segments=24, bevel=0.004),
        *[box(f'YokeArm{s}', m['steel'], (0.025, 0.06, 0.1), HEAD + Vector((s * 0.075, 0, 0.055)), bevel=0.005) for s in (-1, 1)],
        cylinder('Trunnion', m['steel_light'], 0.02, 0.18, DISH_PIVOT, rotation=(0, math.pi / 2, 0), segments=12, bevel=0.002),
    ], HEAD)
    kit.parent(yoke, head)
    tilt = kit.parent(kit.empty('Dish', DISH_PIVOT), head)
    body, glow = dish(m, root)
    kit.parent(body, tilt)
    kit.parent(glow, tilt)
    tilt.rotation_euler = (REST_TILT, 0, 0)   # +x rotation turns the dish's face to -Y (the front)
    keys(lift, 'location', {0: HEAD + Vector((0, 0, -0.55)), 18: HEAD + Vector((0, 0, -0.55)), 32: HEAD + Vector((0, 0, 0.01)), 35: HEAD})

    # ---- lamps on the collar
    lights = []
    for k, a in enumerate((math.radians(-60), math.radians(120))):
        at = Vector((math.cos(a) * 0.215, math.sin(a) * 0.215, CAGE_TOP + 0.03))
        gb.beacon(f'CollarLamp{k}', m, at, 'red' if k else 'amber', root, 30 + 3 * k, kit.flashes((k * 30, 10)), lights)

    # ---- clips
    def sweep(o):
        frames = {f: Vector((0, 0, math.radians(18) * math.sin(2 * math.pi * f / kit.IDLE_END))) for f in range(0, kit.IDLE_END + 1, 3)}
        keys(o, 'rotation_euler', frames, 'LINEAR')

    gb.clips([(head, sweep)], lights)
    # Fire: the dish swings up (to the sky) and glows, then back
    rest = Vector((REST_TILT, 0, 0))
    up = Vector((0, 0, 0))
    keys(tilt, 'rotation_euler', {0: rest, 12: up, 33: up, FIRE_END: rest})
    kit.to_track(tilt, 'Fire')
    glow_frames = {0: Vector((H, H, H)), 10: Vector((H, H, H)), 15: Vector((1.3, 1.3, 1.3)), 18: Vector((0.9, 0.9, 0.9)),
                   22: Vector((1.2, 1.2, 1.2)), 26: Vector((0.9, 0.9, 0.9)), 30: Vector((1.1, 1.1, 1.1)), 36: Vector((H, H, H)), FIRE_END: Vector((H, H, H))}
    keys(glow, 'scale', glow_frames)
    kit.to_track(glow, 'Fire')
    glow.scale = (H, H, H)  # hidden at rest
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=1.5, target=(0, 0, 0.45), bake=512)
