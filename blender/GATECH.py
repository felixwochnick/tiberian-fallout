"""
Tiberian Fallout – GDI tech center (GATECH), after Tiberian Sun.

A low plinth (foundation 3 × 2 cells), a wedge in plan – deep at the right end,
shallow at the left, its back cut off diagonally – in two tiers with sloped,
camouflaged sides, steel edges and dark grooves running round it, a light deck on top;
louvres in its right end, steps in its front. On the deck at the back right the big
geodesic dome: panels in the house colour in a frame of light struts on a steel ring.
At the front left two tall, pointed blades in the house colour stand side by side on
steel mounts, turned edge-on towards the viewer, lights at their tips.

Materials as for the barracks (see GAPILE.py): Camo_* is the baked camouflage in a
pale shade of the house colour, Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.5 s: the plinth spreads and rises, the dome grows out of its
             ring, the fins shoot up, the lights come on
    Idle     loop, 2 s: the beacons blink, the fins' tip lights flash in turn, the
             dome's top light pulses

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GATECH.py [-- --preview 0,40,74 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -1.5 … 1.5 and y -1 … 1.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import gdibuilding as gb  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GATECH.glb')
BLEND = os.path.join(HERE, 'GATECH.blend')

BUILD_END = 74
LOW = 0.13              # top of the lower tier
DECK = 0.27             # top of the plinth
# a wedge in plan: deep at the right end, shallow at the left, the back cut off diagonally
OUTLINE = [(-1.42, -0.95), (1.45, -0.95), (1.45, 0.88), (-0.12, 0.88), (-1.42, -0.42)]
DOME = Vector((0.62, 0.18, DECK))
DOME_RADIUS = 0.5
FINS = ((-0.52, -0.68, 1.1), (-0.12, -0.68, 0.95))   # x, y, height
FIN_TURN = 25           # the blades' turn (degrees) from facing along x: almost edge-on

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m['strut'] = material('Strut', srgb('#a39065'), 0.6, 0.3)
    m['deck'] = material('TechDeck', srgb('#bba673'), 0.8)
    return m


# --------------------------------------------------------------------------- parts

def plinth(m, root):
    """The two tiers (camouflage) and their trims, grooves, louvres and steps."""
    lower = gb.slab('Lower', m['sand'], OUTLINE, LOW, inset=0.05, bevel=0.006)
    upper_outline = gb.offset(OUTLINE, 0.08)
    upper = gb.slab('Upper', m['sand'], upper_outline, DECK - LOW - 0.02, inset=0.05, z0=LOW + 0.02, bevel=0.006)
    shell = gb.camo(kit.merge('Plinth', [lower, upper]), root)

    parts = [gb.slab('Ledge', m['steel'], gb.offset(OUTLINE, 0.05), 0.02, inset=0.0, z0=LOW, bevel=0.003),
             gb.slab('Deck', m['deck'], gb.offset(upper_outline, 0.06), 0.012, inset=0.01, z0=DECK - 0.001, bevel=0.003),
             gb.slab('DeckRim', m['steel_light'], gb.offset(upper_outline, 0.045), 0.008, z0=DECK - 0.004, bevel=0)]
    # dark grooves round the tiers (on the front and right faces, where they are seen)
    x0, y0, x1, y1 = -1.42, -0.95, 1.45, 0.88
    for k, (z, inset) in enumerate(((0.045, 0.017), (0.09, 0.034), (LOW + 0.06, 0.1), (LOW + 0.1, 0.115))):
        parts.append(box(f'GrooveF{k}', m['dark'], (x1 - x0 - 2 * inset - 0.3, 0.01, 0.012), ((x0 + x1) / 2, y0 + inset, z), bevel=0))
        parts.append(box(f'GrooveR{k}', m['dark'], (0.01, y1 - y0 - 2 * inset - 0.3, 0.012), (x1 - inset, (y0 + y1) / 2, z), bevel=0))
    # louvres in the right end
    for k in range(6):
        y = -0.45 + k * 0.18
        parts.append(box(f'Louvre{k}', m['steel'], (0.03, 0.12, 0.17), (x1 - 0.09, y, (LOW + DECK) / 2 + 0.01), bevel=0.003,
                         rotation=(0, math.radians(-20), 0)))
    # steps up the front, a door in the upper tier
    for k in range(3):
        parts.append(box(f'Step{k}', m['concrete'], (0.32, 0.07, 0.09 * (k + 1)), (0.15, y0 + 0.2 - 0.07 * k, 0.045 * (k + 1)), bevel=0.004))
    parts.append(box('Door', m['dark'], (0.22, 0.012, 0.09), (0.15, y0 + 0.17, LOW + 0.06), bevel=0.003))
    parts.append(box('DoorBand', m['remap'], (0.3, 0.014, 0.02), (0.15, y0 + 0.165, LOW + 0.12), bevel=0))
    for k, x in enumerate((-1.2, -0.1, 0.42, 1.0)):
        parts.append(box(f'Window{k}', m['window'], (0.12, 0.012, 0.04), (x, y0 + 0.13, LOW + 0.07), bevel=0.002))
    # on the deck: panel seams, roof vents, a hatch and a short antenna mast at the back left
    for k in range(3):
        x = 0.16 + k * 0.42
        parts.append(box(f'DeckSeam{k}', m['concrete_dark'], (0.01, 1.4, 0.003), (x, -0.03, DECK + 0.0125), bevel=0))
    parts.append(box('DeckSeamY', m['concrete_dark'], (2.4, 0.01, 0.003), (0.05, -0.45, DECK + 0.0125), bevel=0))
    for k, (x, y) in enumerate(((0.35, -0.7), (1.15, -0.7))):
        vent = kit.vent_block(f'Vent{k}', m, x, y)
        vent.location.z = DECK + 0.01
        parts.append(vent)
    parts.append(box('DeckHatch', m['steel'], (0.18, 0.18, 0.02), (-0.75, -0.3, DECK + 0.02), bevel=0.004))
    parts.append(kit.ac_unit('DeckAc', m, -0.2, 0.55))
    parts[-1].location.z = DECK + 0.01
    mast = Vector((-0.42, 0.3, DECK))
    parts += [box('MastFoot', m['steel'], (0.08, 0.08, 0.03), mast + Vector((0, 0, 0.015)), bevel=0.004),
              cylinder('MastPole', m['steel_light'], 0.01, 0.5, mast + Vector((0, 0, 0.25)), segments=8, bevel=0),
              beam('MastBar', m['steel'], mast + Vector((-0.07, 0, 0.38)), mast + Vector((0.07, 0, 0.38)), 0.008)]
    return shell, kit.merge('PlinthDetails', parts)


def hemisphere(bm, radius, subdivisions=2):
    """A geodesic hemisphere (icosphere cut at z = 0) in `bm`."""
    bmesh.ops.create_icosphere(bm, subdivisions=subdivisions, radius=radius)
    # turn it so a ring of vertices lies near the equator, then cut
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=True)


def dome(m):
    """The geodesic dome: house-colour panels and a frame of struts, origin at its foot;
    and the steel ring it stands on."""
    def panels(bm):
        hemisphere(bm, DOME_RADIUS)

    shell = kit.finish(kit.mesh_object('DomePanels', panels), m['remap'], 0)
    for poly in shell.data.polygons:
        poly.use_smooth = False
    shell.location = DOME
    frame = kit.finish(kit.mesh_object('DomeFrame', lambda bm: hemisphere(bm, DOME_RADIUS + 0.008)), m['strut'], 0)
    for poly in frame.data.polygons:
        poly.use_smooth = False
    wire = frame.modifiers.new('Struts', 'WIREFRAME')
    wire.thickness = 0.022
    wire.offset = 0.5
    wire.use_boundary = True
    frame.location = DOME
    top = DOME + Vector((0, 0, DOME_RADIUS))
    parts = [shell, frame, cylinder('DomeCap', m['steel'], 0.07, 0.04, top + Vector((0, 0, 0.0)), segments=16)]
    body = kit.merge('Dome', parts, DOME)
    ring = kit.merge('DomeRing', [
        cylinder('Ring', m['steel'], DOME_RADIUS + 0.05, 0.05, DOME + Vector((0, 0, 0.025)), segments=40),
        cylinder('RingBand', m['remap'], DOME_RADIUS + 0.055, 0.015, DOME + Vector((0, 0, 0.03)), segments=40, bevel=0),
        box('Hatch', m['dark'], (0.16, 0.012, 0.14), DOME + Vector((-0.65, -0.76, 0)) * (DOME_RADIUS + 0.056) + Vector((0, 0, 0.07)), bevel=0.003, rotation=(0, 0, math.radians(-40))),
    ], DOME)
    return body, ring


def fin(m, k, x, y, height):
    """A tall pointed fin in the house colour on its steel mount; origin at its foot (it
    shoots up from there)."""
    foot = Vector((x, y, DECK))
    w = 0.15
    profile = [(y - w, 0), (y + w, 0), (y + w * 0.7, height * 0.62), (y + 0.02, height), (y - w * 0.55, height * 0.8), (y - w * 0.9, height * 0.35)]
    blade = gb.prism(f'Fin{k}', m['remap'], [(u, DECK + 0.05 + v) for u, v in profile], x - 0.022, x + 0.022, 'X', bevel=0.004)
    parts = [blade,
             box(f'FinMount{k}', m['steel'], (0.12, 2 * w + 0.08, 0.07), foot + Vector((0, 0, 0.035)), bevel=0.008),
             beam(f'FinSpine{k}', m['steel_light'], foot + Vector((0.028, 0.0, 0.06)), foot + Vector((0.028, 0.02, height * 0.85)), 0.012)]
    obj = kit.merge(f'Fin{k}', parts, foot)
    obj.rotation_euler = (0, 0, math.radians(FIN_TURN))
    return obj


# --------------------------------------------------------------------------- model

def build():
    gb.start('GDITechCenter', BUILD_END)
    m = materials()
    root = kit.empty('GDITechCenter')
    keys = kit.keys
    H = kit.HIDDEN

    base = kit.parent(kit.empty('PlinthGroup'), root)
    for obj in plinth(m, root):
        kit.parent(obj, base)
    keys(base, 'scale', {0: Vector((0.05, 0.05, H)), 2: Vector((0.05, 0.05, H)), 12: Vector((1.02, 1.02, 0.2)), 14: Vector((1, 1, 0.2)),
                         24: Vector((1, 1, 1.04)), 27: Vector((1, 1, 1))})

    body, ring = dome(m)
    ring = kit.parent(ring, base)
    kit.pop(ring, 24, 6)
    body = kit.parent(body, ring)
    keys(body, 'scale', {0: Vector((H, H, H)), 28: Vector((H, H, H)), 29: Vector((1, 1, 0.05)), 44: Vector((1, 1, 1.05)), 48: Vector((1, 1, 1))})

    # the lights hang from the root, not from the parts that grow out of nothing in
    # Build (a parent scaled to nothing spoils their keys in Idle); their housings pop up
    lights = []

    def lamp(name, at, colour, holder, pop_at, pattern):
        housing, light = kit.beacon(name, m, at, colour)
        housing = kit.parent(kit.merge(name, [housing], at), holder)
        kit.parent(light, root)
        kit.pop(housing, pop_at, 5)
        lights.append((light, pattern))
        return light

    for k, (x, y, height) in enumerate(FINS):
        obj = kit.parent(fin(m, k, x, y, height), base)
        kit.grow(obj, 40 + 5 * k, 10, 2)
        tip = Vector((x, y, 0)) + Matrix.Rotation(math.radians(FIN_TURN), 3, 'Z') @ Vector((0, 0.02, 0)) + Vector((0, 0, DECK + 0.05 + height * 0.97))
        lamp(f'FinTip{k}', tip, 'red', obj, 56 + 2 * k, kit.flashes((30 * k, 6), (30 * k + 10, 6)))

    idle = []
    top = DOME + Vector((0, 0, DOME_RADIUS + 0.02))
    light = lamp('DomeTop', top, 'amber', body, 58, kit.flashes((0, 60)))
    glow = kit.parent(sphere('DomeTopGlow', m['glow_amber'], 0.07, top + Vector((0, 0, 0.03)), 10), root)
    idle.append((glow, lambda o: gb.pulse(o, 0.5, 1.2, 1)))
    for k, (x, y) in enumerate(((-1.2, -0.75), (1.25, -0.75), (1.25, 0.68))):
        lamp(f'Corner{k}', (x, y, DECK + 0.01), 'green' if k == 1 else 'red', base, 62 + 2 * k, kit.flashes((10 + 20 * k, 7)))

    gb.clips(idle, lights)
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=3.8, target=(0, 0, 0.35))
