"""
Tiberian Fallout – Nod gate (NAGATE_A), after Tiberian Sun.

A gate in the Nod wall, three cells long along x (Foundation=3x1; on screen it runs
from the upper left to the lower right). Like the original it is one tall wall that
sinks into the ground: a dark concrete panel below – framed in red (house colour), with
vertical grooves and the Nod emblem in the middle of both faces – and above it a light
grey concrete roof sloping up to a narrow crest. The panel is low at the ends and high
in the middle, the crest high at the ends and lower in the middle, so the light slopes
make big triangles at the ends and a thin band in the middle. It stands on a striped
ground strip with a dark slot it sinks into. Its arms continue the Nod wall's slab
(NAWALL.slab_parts) from the ends to the edges of the foundation.

Nodes:
    Body     carries the gate up out of the ground (Build)
    Door     the wall itself, inside Body (sinks in Open)
    ArmXP    the wall slab from the gate's +x end to the cell's edge, shown by the game
             when an NAWALL joins there (world +x, glTF and Blender +x)
    ArmXN    … at the -x end
    Lamp…    small red lamps on the high ends (housing in Door, the light blinks in Idle)
Animations (glTF clips)
    Build    one-shot, 1.6 s: the strip spreads, the gate rises out of the slot, the
             arms grow
    Idle     loop, 2 s: the red lamps blink
    Open     one-shot, 1 s: the wall sinks into the ground down to a low stub, the
             original's six gate stages (the game holds it; played backwards it shuts)

Run headless:

    blender -b --factory-startup --python blender/NAGATE_A.py [-- --preview <dir>]

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
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402
import NAWALL as wall  # noqa: E402 – the wall's slab for the arms

box, beam = kit.box, kit.beam
HIDDEN = kit.HIDDEN

END = 1.4                 # the gate's body spans |x| <= END; the arms go on to 1.5
FOOT = wall.FOOT          # half the thickness at the foot (as the wall's slab)
CREST = 0.045             # half the crest's width
LOW_PANEL, HIGH_PANEL = 0.17, 0.46    # the dark panel's height at the ends, in the middle
FLAT = 0.5                # the panel is level for |x| <= FLAT
CREST_END, CREST_MID = 0.74, 0.66     # the crest's height at the ends, in the middle
STUB = 0.05               # how much is left above the ground when open
OPEN_FRAMES = 30
STRIP = 0.012             # the ground strip's thickness
LIGHT_GREY = '#b2b2ae'
DARK_GREY = wall.COLOUR


def panel(x):
    """The dark panel's height at x."""
    a = abs(x)
    if a <= FLAT:
        return HIGH_PANEL
    return HIGH_PANEL + (LOW_PANEL - HIGH_PANEL) * (a - FLAT) / (END - FLAT)


def crest(x):
    return CREST_MID + (CREST_END - CREST_MID) * (x / END) ** 2


def stations():
    xs = sorted({round(-END + k * 2 * END / 28, 4) for k in range(29)} | {-FLAT, FLAT})
    return xs


def body(m, root):
    """The dark panel (lower) and the light sloping roof (upper), both in concrete."""
    xs = stations()
    lower = wall.sweep('PanelBody', m['steel'], [[(x, -FOOT, 0), (x, FOOT, 0), (x, FOOT, panel(x)), (x, -FOOT, panel(x))] for x in xs], 0.004)
    upper = wall.sweep('RoofBody', m['steel'], [[(x, -FOOT, panel(x)), (x, FOOT, panel(x)), (x, CREST, crest(x)), (x, -CREST, crest(x))] for x in xs], 0.004)
    dark = nb.concrete('Panel', [lower], root, DARK_GREY)
    light = nb.concrete('Roof', [upper], root, LIGHT_GREY)
    details = []
    y_off = FOOT + 0.003
    for f in (-1, 1):
        y = f * y_off
        # the red frame: a band along the foot, uprights at the ends, a line along the
        # top of the panel where it is level
        details.append(box(f'RedFoot{f}', m['remap'], (2 * END - 0.01, 0.008, 0.04), (0, y, 0.035), bevel=0.002))
        for s in (-1, 1):
            details.append(box(f'RedEnd{f}{s}', m['remap'], (0.035, 0.008, LOW_PANEL - 0.01), (s * (END - 0.02), y, (LOW_PANEL - 0.01) / 2), bevel=0.002))
        details.append(box(f'RedTop{f}', m['remap'], (2 * FLAT, 0.008, 0.025), (0, y, HIGH_PANEL - 0.0125), bevel=0.002))
        # grooves down the panel, the emblem's place left free
        for k in range(-6, 7):
            x = k * 0.2
            if abs(k) <= 1:
                continue
            top = panel(x) - 0.04
            if top > 0.1:
                details.append(box(f'Groove{f}{k}', m['dark'], (0.014, 0.006, top - 0.07), (x, y, (top + 0.07) / 2), bevel=0))
        # the emblem: a red delta with a dark one inside
        zc = 0.25
        for name, size, mat, dy in (('Emblem', 0.2, m['remap'], 0.0), ('EmblemInner', 0.1, m['armour_dark'], 0.004)):
            h = size * math.sqrt(3) / 2
            yy = f * (y_off + 0.002 + dy)
            details.append(kit.hexahedron(f'{name}{f}', mat, (
                (-size / 2, yy - 0.003, zc - h / 3), (size / 2, yy - 0.003, zc - h / 3), (0.001, yy - 0.003, zc + 2 * h / 3), (-0.001, yy - 0.003, zc + 2 * h / 3),
                (-size / 2, yy + 0.003, zc - h / 3), (size / 2, yy + 0.003, zc - h / 3), (0.001, yy + 0.003, zc + 2 * h / 3), (-0.001, yy + 0.003, zc + 2 * h / 3)), bevel=0))
    return dark, light, kit.merge('DoorDetails', details)


def crest_cap(m):
    """Dark plates along the crest, following its curve."""
    xs = stations()
    w = CREST - 0.008
    return wall.sweep('CrestCap', m['armour_dark'], [[(x, -w, crest(x) - 0.004), (x, w, crest(x) - 0.004), (x, w, crest(x) + 0.008), (x, -w, crest(x) + 0.008)] for x in xs[1:-1]], 0)


def strip(m):
    """The striped ground strip under the gate and the dark slot it sinks into."""
    mats = dict(m)
    mats['hazard'] = kit.material('GateStripe', kit.srgb('#8c7c5a'), 0.95)
    mats['hazard']['nodColour'] = '#8c7c5a'
    mats['hazard_dark'] = kit.material('GateStripeDark', kit.srgb('#34302a'), 0.95)
    mats['hazard_dark']['nodColour'] = '#34302a'
    parts = [nb.stripes('Stripes', mats, (0, 0, STRIP / 2), (3.0, 0.9, STRIP), 'X', 22),
             box('Slot', m['dark'], (2 * END + 0.02, 2 * FOOT + 0.03, 0.004), (0, 0, STRIP + 0.001), bevel=0)]
    return kit.merge('Strip', parts)


def arm(name, m, root, side):
    body_parts, details = wall.slab_parts(name, m, END - 0.03, 1.5, END + 0.004)
    obj = nb.concrete(name, body_parts, root, DARK_GREY)
    detail = kit.merge(f'{name}Detail', details)
    if side < 0:
        for o in (obj, detail):
            wall.turned(o, math.pi)
    kit.parent(detail, obj)
    return obj


def build():
    root = nb.start('NodGate', 'NodGate', 48)
    m = nb.materials()
    ground = kit.parent(strip(m), root)
    lift = kit.parent(kit.empty('Body'), root)
    door = kit.parent(kit.empty('Door'), lift)
    dark, light, details = body(m, root)
    for obj in (dark, light, details, crest_cap(m)):
        kit.parent(obj, door)
    lights = []
    for s in (-1, 1):
        at = (s * (END - 0.1), 0, crest(END - 0.1) + 0.008)
        housing, light = nb.beacon(f'Lamp{s}', m, at, 'red')
        kit.parent(housing, door)
        kit.parent(light, door)
        lights.append(light)
    arms = [arm('ArmXP', m, root, 1), arm('ArmXN', m, root, -1)]
    for obj in arms:
        kit.parent(obj, root)

    # Build: the strip spreads, the gate comes up out of its slot, the arms grow
    kit.keys(ground, 'scale', {0: Vector((0.03, 1, 1)), 2: Vector((0.03, 1, 1)), 12: Vector((1.02, 1, 1)), 15: Vector((1, 1, 1))})
    nb.rise(lift, 10, 26, CREST_END + 0.02)
    for k, obj in enumerate(arms):
        nb.grow_z(obj, 30 + 3 * k, 10)
    nb.all_to_build()

    # Idle: the lamps blink in turn
    nb.blinking([(light, kit.flashes((k * 30, 12))) for k, light in enumerate(lights)])

    # Open: the wall sinks, quickly at first and slowing down at the end
    sunk = Vector((0, 0, -(CREST_END - STUB)))
    kit.keys(door, 'location', {0: Vector((0, 0, 0)), 3: Vector((0, 0, 0.008)), OPEN_FRAMES: sunk})
    kit.to_track(door, 'Open')

    ground.scale = (1, 1, 1)
    lift.location = door.location = (0, 0, 0)
    for obj in arms:
        obj.scale = (1, 1, 1)
    for light in lights:
        light.scale = (1, 1, 1)
    return len(kit.collection().objects)


def _rest():
    """Puts back what evaluating a clip other than Build leaves behind (the door sunk,
    the lamps off) – only for the previews; the glTF is not affected."""
    bpy.data.objects['Door'].location = (0, 0, 0)
    for obj in bpy.data.objects:
        if obj.name.startswith('Lamp') and obj.name.endswith('Light'):
            obj.scale = (1, 1, 1)


def _render_and_rest(frames, out_dir, _render=kit.render_preview):
    result = _render(frames, out_dir)
    _rest()
    return result


if __name__ == '__main__':
    kit.render_preview = _render_and_rest
    nb.main(build, 'NAGATE_A', {'Build': [12, 26, 40], 'Idle': [0], 'Open': [10, 20, 30]}, ortho=3.4, target=(0, 0, 0.3), texture=1024)
