"""
Tiberian Fallout – GDI service depot (GADEPT), after Tiberian Sun.

A flat repair bay (foundation 3 × 3 cells): a large octagonal pad of blue-grey steel
plates in a ring of the house colour on a concrete footing, its plates marked with
seams and a guide cross; at its left edge (Blender -x) a tall service wall – panels in
the house colour in a steel frame, leaning back – with a control cabin, and two light
grey robot arms on it that reach out over the pad. Vehicles drive onto the pad.

Nodes the game drives
    Pad      empty node in the middle of the pad on its top: where the vehicle stands

Materials as for the barracks (see GAPILE.py): Camo_* is the baked camouflage in a
pale shade of the house colour, Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name; no channel is
shared between them)
    Build    one-shot, 2 s: the footing and the pad spread, the wall rises out of the
             ground, the arms unfold, the lights come on
    Idle     loop, 2 s: the pad's guide lights run round, the lamps blink
    Fire     loop, 1 s (while a vehicle is repaired): the arms swing in and dip their
             tools, sparks fly at the tools

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GADEPT.py [-- --preview 0,30,60 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -1.5 … 1.5 and y -1.5 … 1.5.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import gdibuilding as gb  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GADEPT.glb')
BLEND = os.path.join(HERE, 'GADEPT.blend')

BUILD_END = 60
FIRE_END = 30
FOOT = 0.03
PAD = Vector((0.22, 0.0, 0.07))     # the pad's middle on its top
PAD_R = 1.18                         # to the pad's flat sides
WALL_X = -1.28                       # the wall's front face at its foot
WALL_TOP = 0.62
WALL_Y = (-0.85, 0.85)
ARMS = (-0.42, 0.42)                 # the arms' y
SHOULDER_Z = 0.42

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m['pad'] = material('PadSteel', srgb('#7a8096'), 0.55, 0.6)
    m['pad_dark'] = material('PadSteelDark', srgb('#5a5f72'), 0.6, 0.6)
    m['arm'] = material('ArmWhite', srgb('#c9ccd0'), 0.4, 0.5)
    m['remap_dark'] = material('RemapDark', srgb('#9a7c22'), 0.6, 0.15)
    m['spark'] = material('GlowSpark', (0, 0, 0), 1.0, emission=srgb('#fff0a0'), strength=8, alpha=0.8)
    m['glow_blue'] = material('GlowWeld', (0, 0, 0), 1.0, emission=srgb('#8ab4ff'), strength=6, alpha=0.4)
    return m


def octagon(r, centre=(0, 0)):
    """An octagon with flat sides at distance r (counter-clockwise)."""
    R = r / math.cos(math.pi / 8)
    return [(centre[0] + R * math.cos(math.pi / 8 + k * math.pi / 4), centre[1] + R * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]


# --------------------------------------------------------------------------- parts

def pad(m):
    """Footing, rim in the house colour and the steel plates; origin at the pad's middle."""
    c = (PAD.x, PAD.y)
    parts = [gb.slab('Footing', m['concrete'], octagon(PAD_R + 0.08, c), FOOT + 0.01, inset=0.03, bevel=0.004),
             gb.slab('Rim', m['remap'], octagon(PAD_R, c), PAD.z - FOOT - 0.005, inset=0.02, z0=FOOT, bevel=0.004),
             gb.slab('Plates', m['pad'], octagon(PAD_R - 0.07, c), 0.008, inset=0.0, z0=PAD.z - 0.008, bevel=0.002)]
    # plate seams: a grid, the guide cross darker
    for k in range(-4, 5):
        off = k * 0.25
        span = 2 * math.sqrt(max(0.0, (PAD_R - 0.1) ** 2 - off ** 2)) * 0.93
        mat = m['pad_dark'] if k == 0 else m['steel']
        w = 0.05 if k == 0 else 0.008
        parts.append(box(f'SeamX{k}', mat, (span, w, 0.003), (PAD.x, PAD.y + off, PAD.z + 0.001), bevel=0))
        parts.append(box(f'SeamY{k}', mat, (w, span, 0.003), (PAD.x + off, PAD.y, PAD.z + 0.001), bevel=0))
    return kit.merge('Pad', parts, PAD)


def wall(m, root):
    """The leaning service wall with its frame and panels, the control cabin beside
    it and the arms' mounting rails; origin at its foot."""
    y0, y1 = WALL_Y
    lean = 0.12   # the wall's top leans back (to -x)
    z0 = FOOT
    base = gb.camo(gb.slab('WallBase', m['sand'], [(WALL_X - 0.2, y0 - 0.05), (WALL_X + 0.04, y0 - 0.05), (WALL_X + 0.04, y1 + 0.05), (WALL_X - 0.2, y1 + 0.05)],
                           0.14, inset=0.02, z0=z0, bevel=0.006), root)
    parts = []
    # the frame: posts and the top beam, leaning back
    for k, y in enumerate((y0, 0.0, y1)):
        parts.append(beam(f'Post{k}', m['steel'], (WALL_X - 0.04, y, z0 + 0.1), (WALL_X - 0.04 - lean, y, WALL_TOP), 0.06, 0.06))
    parts.append(beam('TopBeam', m['steel'], (WALL_X - 0.04 - lean, y0 - 0.03, WALL_TOP), (WALL_X - 0.04 - lean, y1 + 0.03, WALL_TOP), 0.07, 0.06))
    # the panels in the house colour between the posts, a dark stripe across them
    slope = math.atan2(lean, WALL_TOP - z0 - 0.1)
    for k, (ya, yb) in enumerate(((y0, 0.0), (0.0, y1))):
        mid = Vector((WALL_X - 0.06 - lean / 2, (ya + yb) / 2, (z0 + 0.1 + WALL_TOP) / 2))
        parts.append(box(f'Panel{k}', m['remap'], (0.03, yb - ya - 0.07, WALL_TOP - z0 - 0.12), mid, bevel=0.006, rotation=(0, -slope, 0)))
        parts.append(box(f'PanelStripe{k}', m['dark'], (0.034, yb - ya - 0.07, 0.03), mid + Vector((0.003, 0, 0.1)), bevel=0, rotation=(0, -slope, 0)))
        parts.append(box(f'PanelRib{k}', m['remap_dark'], (0.036, 0.02, WALL_TOP - z0 - 0.14), mid, bevel=0, rotation=(0, -slope, 0)))
    # the rails the arms are mounted on
    for k, y in enumerate(ARMS):
        parts.append(box(f'Mount{k}', m['steel'], (0.1, 0.14, 0.16), (WALL_X - 0.04, y, SHOULDER_Z), bevel=0.01))
        parts.append(cylinder(f'MountHub{k}', m['steel_light'], 0.05, 0.03, (WALL_X + 0.02, y, SHOULDER_Z), rotation=(0, math.pi / 2, 0), segments=16, bevel=0.003))
    # the control cabin at the back end of the wall, with a window towards the pad
    cy = y1 + 0.27
    parts += [
        box('Cabin', m['steel_light'], (0.34, 0.36, 0.34), (WALL_X - 0.04, cy, z0 + 0.17), bevel=0.02),
        box('CabinRoof', m['steel'], (0.38, 0.4, 0.03), (WALL_X - 0.04, cy, z0 + 0.355), bevel=0.006),
        box('CabinWindow', m['window'], (0.012, 0.24, 0.1), (WALL_X + 0.135, cy, z0 + 0.24), bevel=0.003),
        box('CabinDoor', m['dark'], (0.16, 0.012, 0.22), (WALL_X - 0.04, cy - 0.181, z0 + 0.11), bevel=0.003),
        box('CabinBand', m['remap'], (0.346, 0.366, 0.03), (WALL_X - 0.04, cy, z0 + 0.3), bevel=0),
    ]
    # tool racks and a cable drum at the wall's foot
    parts.append(cylinder('CableDrum', m['remap'], 0.07, 0.08, (WALL_X + 0.08, -0.05, z0 + 0.075), rotation=(math.pi / 2, 0, 0), segments=18, bevel=0.005))
    parts.append(box('ToolBox', m['steel'], (0.12, 0.18, 0.1), (WALL_X + 0.1, y0 + 0.08, z0 + 0.05), bevel=0.006))
    return base, kit.merge('WallFrame', parts, (WALL_X, 0, z0))


def arm(m, k, y):
    """A robot arm on the wall: (shoulder node, elbow node, wrist tip, spark mesh);
    the shoulder turns about z (swings in over the pad), the elbow about y (dips)."""
    s = Vector((WALL_X + 0.04, y, SHOULDER_Z))
    shoulder = kit.empty(f'Shoulder{k}', s)
    upper_len = 0.62
    e = s + Vector((upper_len, 0, 0.06))
    upper = kit.merge(f'UpperArm{k}', [
        cylinder(f'ShoulderJoint{k}', m['steel'], 0.05, 0.08, s + Vector((0.03, 0, 0)), segments=16, bevel=0.004),
        beam(f'UpperBeam{k}', m['arm'], s + Vector((0.03, 0, 0.02)), e, 0.07, 0.06),
        beam(f'UpperStripe{k}', m['remap'], s + Vector((0.1, 0, 0.055)), e + Vector((-0.06, 0, 0.032)), 0.03, 0.012),
        cylinder(f'Hose{k}', m['dark'], 0.012, upper_len - 0.1, (s + e) / 2 + Vector((0, 0.045, -0.02)), rotation=(0, math.pi / 2 - 0.12, 0), segments=8, bevel=0),
    ], s)
    elbow = kit.empty(f'Elbow{k}', e)
    w = e + Vector((0.3, 0, -0.24))
    fore = kit.merge(f'ForeArm{k}', [
        cylinder(f'ElbowJoint{k}', m['steel'], 0.045, 0.09, e, rotation=(math.pi / 2, 0, 0), segments=16, bevel=0.004),
        beam(f'ForeBeam{k}', m['arm'], e, w, 0.05, 0.05),
        cylinder(f'Tool{k}', m['steel'], 0.022, 0.08, w + Vector((0, 0, -0.04)), segments=12, bevel=0.003, radius2=0.01),
        box(f'ToolClamp{k}', m['steel_light'], (0.06, 0.06, 0.03), w, bevel=0.005),
    ], e)
    tip = w + Vector((0, 0, -0.09))
    spark = kit.merge(f'Sparks{k}', [
        sphere(f'WeldGlow{k}', m['glow_blue'], 0.05, tip, 10),
        sphere(f'WeldCore{k}', m['spark'], 0.018, tip, 8),
        *[beam(f'Spark{k}_{j}', m['spark'], tip, tip + Vector((math.cos(a) * 0.09, math.sin(a) * 0.09, 0.03 + 0.02 * (j % 2))), 0.006)
          for j, a in enumerate(math.radians(d) for d in (10, 80, 150, 220, 290))],
    ], tip)
    return shoulder, upper, elbow, fore, spark


# --------------------------------------------------------------------------- model

def build():
    gb.start('GDIServiceDepot', BUILD_END)
    m = materials()
    root = kit.empty('GDIServiceDepot')
    keys = kit.keys
    H = kit.HIDDEN

    base = kit.parent(pad(m), root)
    keys(base, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 14: Vector((1.02, 1.02, 1)), 17: Vector((1, 1, 1))})
    node = kit.parent(kit.empty('Pad', PAD), root)
    node.empty_display_size = 0.3

    # ---- the wall rises out of the ground (moved, never scaled: the arms animate)
    group = kit.parent(kit.empty('WallGroup', (WALL_X, 0, 0)), root)
    for obj in wall(m, root):
        kit.parent(obj, group)
    keys(group, 'location', {0: Vector((WALL_X, 0, -0.75)), 8: Vector((WALL_X, 0, -0.75)), 28: Vector((WALL_X, 0, 0.012)), 32: Vector((WALL_X, 0, 0))})

    # ---- the arms unfold: an unfold node per joint for Build, the joints for Fire
    sparks, joints = [], []
    for k, y in enumerate(ARMS):
        shoulder, upper, elbow, fore, spark = arm(m, k, y)
        unfold = kit.parent(kit.empty(f'ShoulderUnfold{k}', shoulder.location), group)
        kit.parent(shoulder, unfold)
        kit.parent(upper, shoulder)
        bend = kit.parent(kit.empty(f'ElbowUnfold{k}', elbow.location), shoulder)
        kit.parent(elbow, bend)
        kit.parent(fore, elbow)
        kit.parent(spark, elbow)
        start = 30 + 6 * k
        keys(unfold, 'rotation_euler', {0: Vector((0, math.radians(-80), 0)), start: Vector((0, math.radians(-80), 0)),
                                        start + 10: Vector((0, math.radians(3), 0)), start + 13: Vector((0, 0, 0))})
        keys(bend, 'rotation_euler', {0: Vector((0, math.radians(110), 0)), start + 4: Vector((0, math.radians(110), 0)),
                                      start + 14: Vector((0, math.radians(-4), 0)), start + 17: Vector((0, 0, 0))})
        sparks.append(spark)
        joints.append((shoulder, elbow))

    # ---- lamps: on the wall's top, the cabin, and guide lights round the pad
    lights = []
    y0, y1 = WALL_Y
    gb.beacon('WallLampL', m, Vector((WALL_X - 0.16, y0, WALL_TOP + 0.03)), 'amber', group, 44, kit.flashes((0, 10), (30, 10)), lights)
    gb.beacon('WallLampR', m, Vector((WALL_X - 0.16, y1, WALL_TOP + 0.03)), 'amber', group, 46, kit.flashes((15, 10), (45, 10)), lights)
    gb.beacon('CabinLamp', m, Vector((WALL_X - 0.04, y1 + 0.27, FOOT + 0.37)), 'green', group, 48, kit.flashes((0, 45)), lights)
    corners = octagon(PAD_R - 0.035, (PAD.x, PAD.y))
    for k, (x, y) in enumerate(corners):
        at = Vector((x, y, PAD.z - 0.01))
        housing, light = kit.beacon(f'Guide{k}', m, at, 'green')
        housing = kit.parent(kit.merge(f'Guide{k}', [housing], at), root)
        kit.pop(housing, 40 + k, 4)
        kit.parent(light, root)
        lights.append((light, kit.flashes((k * 7, 7), (30 + k * 7, 4))))

    gb.clips([], lights)

    # ---- Fire (a loop): the arms swing in and dip their tools, sparks fly; the
    # first and last frames are the pose at rest, the sparks hidden there
    for k, (shoulder, elbow) in enumerate(joints):
        s = 1 if k == 0 else -1   # both swing in towards the pad's middle line
        phase = 0 if k == 0 else FIRE_END // 2
        sw = {}
        dip = {}
        for f in range(0, FIRE_END + 1, 3):
            t = 2 * math.pi * ((f + phase) % FIRE_END) / FIRE_END
            sw[f] = Vector((0, 0, s * math.radians(14) * (0.5 - 0.5 * math.cos(2 * math.pi * f / FIRE_END))))
            dip[f] = Vector((0, math.radians(12) * (0.5 - 0.5 * math.cos(2 * t)) * (0.5 - 0.5 * math.cos(2 * math.pi * f / FIRE_END)), 0))
        sw[FIRE_END] = Vector((0, 0, 0))
        dip[FIRE_END] = Vector((0, 0, 0))
        keys(shoulder, 'rotation_euler', sw)
        kit.to_track(shoulder, 'Fire')
        keys(elbow, 'rotation_euler', dip)
        kit.to_track(elbow, 'Fire')
    for k, spark in enumerate(sparks):
        on = {f for f in range(1, FIRE_END - 1) if ((f + 3 * k) // 2) % 3 != 2 and 6 <= f <= FIRE_END - 5}
        frames = {}
        for f in range(FIRE_END + 1):
            frames[f] = Vector((1, 1, 1)) * ((0.8 + 0.4 * ((f * 7 + k) % 3) / 2) if f in on else H)
        keys(spark, 'scale', frames, 'CONSTANT')
        kit.to_track(spark, 'Fire')
        spark.scale = (H, H, H)
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=4.0, target=(0, 0, 0.2))
