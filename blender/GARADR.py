"""
Tiberian Fallout – GDI radar (GARADR), after Tiberian Sun.

A square, stepped camouflaged base (foundation 2 × 2 cells) with a tall radar tower in
its middle, as in the original: a camouflaged block between dark steel pillars, an
open storey of steel columns and cross braces round a dark core with tanks, an
overhanging platform with four antenna spikes on its corners, and a pedestal with a
band in the house colour. On it the turntable and the yoke carrying the big round
dish (ribbed bowl, feed horn on three struts, tilted up). Round the tower the
house-colour parts of the original's base: a generator block with a house-colour
housing at the front left, a low house-colour cabinet in front, a house-colour
vaulted shed with a grey pipe arch on the right; a small sensor dome on legs at the
front right.

Materials as for the barracks (see GAPILE.py): Camo_* is the baked camouflage in a
pale shade of the house colour, Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name; no channel is
shared between them, and nothing Idle animates hangs under a part that Build scales
to almost nothing)
    Build    one-shot, 2.6 s: the base spreads, the tower and the outbuildings rise
             out of the ground, the antenna comes up out of the pedestal, the dish
             unfolds, the spikes grow, the lamps come up
    Idle     loop, 6 s: the dish turns once round (like GARADR_A), the beacons blink,
             the dome's lights run round

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GARADR.py [-- --preview 0,40,78 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -1 … 1 and y -1 … 1.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import gdibuilding as gb  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GARADR.glb')
BLEND = os.path.join(HERE, 'GARADR.blend')

BUILD_END = 78
kit.IDLE_END = 180      # one turn of the antenna

BASE = 0.1              # top of the stepped base
TOWER = (-0.36, -0.12, 0.38, 0.62)    # x0, y0, x1, y1 of the tower block
TOWER_TOP = 0.56
FRAME_TOP = 0.84        # top of the open steel storey
PLATFORM = (-0.48, -0.26, 0.5, 0.76)     # the overhanging platform: x0, y0, x1, y1
PLATFORM_TOP = 0.95
UPPER_TOP = 1.1         # top of the pedestal
AXIS = Vector((0.01, 0.25, UPPER_TOP))   # the turntable's axis, on the pedestal
DISH_R = 0.52           # the dish's radius
FOCUS = 0.4             # its focal length
TILT = math.radians(35) # how far it looks up
TRUNNION = AXIS + Vector((0, 0.0, 0.5))   # where the dish hangs in its yoke
DOME = Vector((0.5, -0.5, BASE))

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m['hazard'] = material('Hazard', srgb('#e2a21c'), 0.6)
    return m


# --------------------------------------------------------------------------- parts

def base(m, root):
    """The stepped base: a dark footing and the camouflaged step with sloped edges."""
    footing = gb.slab('Footing', m['concrete_dark'], gb.chamfered(-0.98, -0.98, 0.98, 0.98, 0.12), 0.04, inset=0.01, bevel=0.004)
    step = gb.camo(gb.slab('Step', m['sand'], gb.chamfered(-0.92, -0.92, 0.92, 0.92, 0.1), BASE - 0.04, inset=0.05, z0=0.04, bevel=0.006), root)
    parts = [footing]
    for k in range(4):  # dark joints over the step
        a = -0.6 + k * 0.4
        parts.append(box(f'JointX{k}', m['concrete_dark'], (0.008, 1.7, 0.003), (a, 0, BASE + 0.0015), bevel=0))
    parts.append(box('Path', m['grating'], (0.3, 0.6, 0.008), (0.0, -0.62, BASE + 0.004), bevel=0))
    return kit.merge('Base', parts), step


def tower(m, root):
    """The tower: the camouflaged lower block, an open storey of steel columns and braces
    round a dark core, the overhanging platform and the pedestal (camouflage) with the
    house-colour band and the antenna spikes on the platform's corners."""
    x0, y0, x1, y1 = TOWER
    px0, py0, px1, py1 = PLATFORM
    body = gb.slab('TowerBody', m['sand'], gb.chamfered(x0, y0, x1, y1, 0.06), TOWER_TOP - BASE, inset=0.04, z0=BASE, bevel=0.01)
    platform = gb.slab('Platform', m['sand'], gb.chamfered(px0, py0, px1, py1, 0.08), PLATFORM_TOP - FRAME_TOP, inset=0.025, z0=FRAME_TOP, bevel=0.008)
    pedestal = gb.slab('Pedestal', m['sand'], gb.chamfered(AXIS.x - 0.22, AXIS.y - 0.22, AXIS.x + 0.22, AXIS.y + 0.22, 0.06), UPPER_TOP - PLATFORM_TOP,
                       inset=0.03, z0=PLATFORM_TOP, bevel=0.008)
    shell = gb.camo(kit.merge('TowerShell', [body, platform, pedestal]), root)
    parts = [box('Ledge', m['steel'], (x1 - x0 - 0.04, y1 - y0 - 0.04, 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, TOWER_TOP + 0.015), bevel=0.006)]
    # dark steel pillars at the corners and in the front of the lower block, a door between them
    for k, (x, y) in enumerate(((x0 + 0.02, y0 + 0.02), (x1 - 0.02, y0 + 0.02), (x1 - 0.02, y1 - 0.02), (-0.1, y0 + 0.02), (0.12, y0 + 0.02))):
        parts.append(box(f'Pillar{k}', m['steel'], (0.07, 0.07, TOWER_TOP - BASE + 0.02), (x, y, (TOWER_TOP + BASE) / 2), bevel=0.006))
    parts.append(box('Door', m['dark'], (0.15, 0.012, 0.2), (0.01, y0 + 0.01, BASE + 0.1), bevel=0.003))
    parts.append(box('DoorHood', m['steel_light'], (0.2, 0.05, 0.015), (0.01, y0 - 0.005, BASE + 0.215), bevel=0.003))
    for k, x in enumerate((-0.26, 0.25)):
        parts.append(box(f'Window{k}', m['window'], (0.08, 0.012, 0.05), (x, y0 + 0.02, 0.4), bevel=0.002))
    for k in range(4):
        parts.append(box(f'SideRib{k}', m['steel'], (0.02, 0.025, TOWER_TOP - BASE - 0.06), (x1 - 0.02, y0 + 0.15 + k * 0.13, (TOWER_TOP + BASE) / 2), bevel=0))
    # the open storey: a dark core, columns, cross braces on the visible faces, machinery
    cx0, cy0, cx1, cy1 = x0 + 0.1, y0 + 0.12, x1 - 0.1, y1 - 0.1
    parts.append(box('Core', m['dark'], (cx1 - cx0, cy1 - cy0, FRAME_TOP - TOWER_TOP), ((cx0 + cx1) / 2, (cy0 + cy1) / 2, (TOWER_TOP + FRAME_TOP) / 2), bevel=0))
    corners = ((x0 + 0.04, y0 + 0.04), (x1 - 0.04, y0 + 0.04), (x1 - 0.04, y1 - 0.04), (x0 + 0.04, y1 - 0.04))
    for k, (x, y) in enumerate(corners):
        parts.append(box(f'Column{k}', m['steel'], (0.06, 0.06, FRAME_TOP - TOWER_TOP + 0.01), (x, y, (TOWER_TOP + FRAME_TOP) / 2), bevel=0.005))
    for k, (a, b) in enumerate(((corners[0], corners[1]), (corners[1], corners[2]))):
        za, zb = TOWER_TOP + 0.04, FRAME_TOP - 0.04
        out = Vector((0, -0.01, 0)) if k == 0 else Vector((0.01, 0, 0))
        pa, pb = Vector((*a, 0)) + out, Vector((*b, 0)) + out
        parts.append(beam(f'BraceA{k}', m['steel_light'], pa + Vector((0, 0, za)), pb + Vector((0, 0, zb)), 0.022))
        parts.append(beam(f'BraceB{k}', m['steel_light'], pa + Vector((0, 0, zb)), pb + Vector((0, 0, za)), 0.022))
    for k, x in enumerate((-0.12, 0.1)):  # tanks in front of the core
        parts.append(cylinder(f'Tank{k}', m['steel_light'], 0.06, FRAME_TOP - TOWER_TOP - 0.08, (x, cy0 - 0.06, (TOWER_TOP + FRAME_TOP) / 2), segments=14, bevel=0.006))
        parts.append(cylinder(f'TankBand{k}', m['remap'], 0.062, 0.03, (x, cy0 - 0.06, TOWER_TOP + 0.16), segments=14, bevel=0))
    parts.append(beam('Riser', m['steel'], (x1 - 0.13, y0 + 0.2, TOWER_TOP), (x1 - 0.13, y0 + 0.2, FRAME_TOP), 0.04))
    # the platform's edge and the house-colour band round the pedestal
    parts.append(box('PlatformEdge', m['steel'], (px1 - px0 - 0.1, 0.02, 0.025), ((px0 + px1) / 2, py0 + 0.012, FRAME_TOP + 0.02), bevel=0.003))
    parts.append(box('PlatformEdgeSide', m['steel'], (0.02, py1 - py0 - 0.1, 0.025), (px1 - 0.012, (py0 + py1) / 2, FRAME_TOP + 0.02), bevel=0.003))
    lean = 0.03 * (UPPER_TOP - 0.06 - PLATFORM_TOP) / (UPPER_TOP - PLATFORM_TOP)   # the pedestal's walls lean in
    parts.append(box('PedestalBandFront', m['remap'], (0.36, 0.012, 0.05), (AXIS.x, AXIS.y - 0.22 + lean - 0.005, UPPER_TOP - 0.06), bevel=0.003))
    parts.append(box('PedestalBandSide', m['remap'], (0.012, 0.36, 0.05), (AXIS.x + 0.22 - lean + 0.005, AXIS.y, UPPER_TOP - 0.06), bevel=0.003))
    parts.append(kit.vent_block('PlatformVent', m, 0.0, -0.12))
    parts[-1].location.z = PLATFORM_TOP
    return shell, kit.merge('TowerDetails', parts)


def spikes(m):
    """The antenna spikes on the platform's corners (each its own object, origin at the foot)."""
    px0, py0, px1, py1 = PLATFORM
    out = []
    for k, (x, y, h) in enumerate(((px0 + 0.05, py0 + 0.05, 0.6), (px1 - 0.05, py0 + 0.05, 0.8), (px1 - 0.05, py1 - 0.05, 0.65), (px0 + 0.05, py1 - 0.05, 0.9))):
        foot = Vector((x, y, PLATFORM_TOP))
        parts = [cylinder(f'SpikeFoot{k}', m['steel'], 0.025, 0.04, foot + Vector((0, 0, 0.02)), segments=10, bevel=0.003),
                 cylinder(f'Spike{k}', m['steel_light'], 0.008, h, foot + Vector((0, 0, h / 2)), segments=6, bevel=0, radius2=0.004)]
        for j in range(2):  # small cross bars
            z = h * (0.45 + 0.25 * j)
            parts.append(box(f'SpikeBar{k}{j}', m['steel'], (0.06 - 0.02 * j, 0.008, 0.008), foot + Vector((0, 0, z)), bevel=0))
        out.append(kit.merge(f'Spike{k}', parts, foot))
    return out


def generator(m, root):
    """The generator block at the front left with its house-colour housing; origin at the foot."""
    c = Vector((-0.56, -0.5, BASE))
    body = gb.camo(gb.slab('GenBody', m['sand'], gb.chamfered(c.x - 0.3, c.y - 0.3, c.x + 0.3, c.y + 0.3, 0.04), 0.14, inset=0.03, z0=BASE, bevel=0.006), root)
    parts = [
        box('GenHousing', m['remap'], (0.4, 0.36, 0.13), c + Vector((0.0, 0.02, 0.14 + 0.065)), bevel=0.03),
        box('GenGrille', m['dark'], (0.28, 0.012, 0.06), c + Vector((0.0, -0.165, 0.2)), bevel=0),
    ]
    for k in range(3):
        parts.append(box(f'GenSlat{k}', m['steel'], (0.26, 0.012, 0.006), c + Vector((0, -0.17, 0.18 + k * 0.02)), bevel=0))
    parts.append(cylinder('GenExhaust', m['steel'], 0.02, 0.12, c + Vector((0.15, 0.14, 0.33)), segments=10))
    details = kit.merge('GenDetails', parts, c)
    group = kit.empty('Generator', c)
    for obj in (body, details):
        kit.parent(obj, group)
    return group


def cabinet(m):
    """A low house-colour cabinet in front of the tower; origin at its foot."""
    c = Vector((-0.08, -0.48, BASE))
    parts = [
        box('CabFoot', m['steel'], (0.34, 0.24, 0.03), c + Vector((0, 0, 0.015)), bevel=0.004),
        box('CabBody', m['remap'], (0.3, 0.2, 0.12), c + Vector((0, 0, 0.09)), bevel=0.025),
        box('CabPanel', m['steel_light'], (0.12, 0.012, 0.06), c + Vector((0.05, -0.1, 0.09)), bevel=0.002),
        beam('CabCable', m['dark'], c + Vector((0.0, 0.1, 0.1)), Vector((-0.05, TOWER[1] + 0.02, 0.25)), 0.02),
    ]
    return kit.merge('Cabinet', parts, c)


def dome(m):
    """The small sensor dome on six legs over a square plinth; returns (group, light ring)."""
    c = DOME
    parts = [
        box('DomePlinth', m['concrete'], (0.42, 0.42, 0.06), c + Vector((0, 0, 0.03)), bevel=0.01),
        box('DomePlinthTop', m['steel'], (0.36, 0.36, 0.012), c + Vector((0, 0, 0.066)), bevel=0.003),
        cylinder('DomeRing', m['steel'], 0.16, 0.03, c + Vector((0, 0, 0.25)), segments=24),
    ]
    for k in range(6):
        a = 2 * math.pi * k / 6
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(beam(f'DomeLeg{k}', m['steel'], c + d * 0.14 + Vector((0, 0, 0.07)), c + d * 0.15 + Vector((0, 0, 0.24)), 0.022))
    parts.append(cylinder('DomeCore', m['dark'], 0.08, 0.17, c + Vector((0, 0, 0.155)), segments=16))
    hemi = gb.lathe('DomeShell', m['sand_light'], [(0.155 * math.cos(t), 0.155 * math.sin(t)) for t in
                                                    (math.radians(a) for a in range(0, 91, 10))][:-1] + [(0.001, 0.155)],
                    c + Vector((0, 0, 0.265)), segments=24)
    parts.append(hemi)
    parts.append(cylinder('DomeTip', m['steel'], 0.012, 0.06, c + Vector((0, 0, 0.45)), segments=8))
    group = kit.merge('Dome', parts, c)
    lights = [sphere(f'DomeLamp{k}', m['lamp_green'], 0.014, c + Vector((math.cos(a) * 0.165, math.sin(a) * 0.165, 0.25)), 8)
              for k, a in enumerate(2 * math.pi * k / 8 for k in range(8))]
    return group, lights


def shed(m):
    """The house-colour vaulted shed on the right with a grey pipe arch; origin at its foot."""
    c = Vector((0.66, 0.24, BASE))
    r = 0.17
    parts = [
        box('ShedFoot', m['concrete_dark'], (0.42, 0.66, 0.04), c + Vector((0, 0, 0.02)), bevel=0.006),
        box('ShedWall', m['steel'], (0.36, 0.6, 0.06), c + Vector((0, 0, 0.07)), bevel=0.004),
        gb.prism('ShedVault', m['remap'], gb.arc((c.x, c.z + 0.1), r, 0, math.pi, 16), c.y - 0.3, c.y + 0.3, 'Y', bevel=0.004),
    ]
    for k in range(4):  # ribs over the vault
        y = c.y - 0.24 + k * 0.16
        rib = gb.arc((c.x, c.z + 0.1), r + 0.01, 0, math.pi, 16) + gb.arc((c.x, c.z + 0.1), r - 0.01, math.pi, 0, 16)
        parts.append(gb.prism(f'ShedRib{k}', m['steel'], rib, y - 0.01, y + 0.01, 'Y'))
    # the pipe arch in front of the shed, grey, from the base up and back down
    pts = [Vector((c.x + 0.05 + 0.18 * math.cos(t), c.y - 0.42, BASE + 0.22 * math.sin(t))) for t in (math.pi * k / 8 for k in range(9))]
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        parts.append(beam(f'Arch{k}', m['steel_light'], a, b, 0.04))
    parts.append(beam('ArchFeed', m['steel_light'], pts[-1], Vector((pts[-1].x, c.y - 0.28, BASE + 0.02)), 0.04))
    return kit.merge('Shed', parts, c)


def antenna(m):
    """The turntable on the pedestal and the head: a yoke carrying the big round dish.
    Returns (turntable, head, dish): the head turns about z (Idle), the dish hangs in
    the yoke on TRUNNION (it unfolds in Build)."""
    table = kit.merge('Turntable', [
        cylinder('TableBase', m['steel'], 0.17, 0.05, AXIS + Vector((0, 0, 0.025)), segments=24),
        cylinder('TableRing', m['remap'], 0.175, 0.015, AXIS + Vector((0, 0, 0.045)), segments=24, bevel=0),
    ], AXIS)
    # the dish in its own frame: concave towards +z, vertex at the origin
    def depth(r):
        return r * r / (4 * FOCUS)
    n = 10
    profile = [(0.002, -0.03)] + [(DISH_R * k / n, depth(DISH_R * k / n) - 0.03) for k in range(1, n + 1)]
    profile += [(DISH_R + 0.012, depth(DISH_R) + 0.004)] + [(DISH_R * k / n, depth(DISH_R * k / n)) for k in range(n, 0, -1)] + [(0.002, 0.0)]
    shell = gb.lathe('DishShell', m['sand_light'], profile, (0, 0, 0), segments=40)
    # the thin bowl confuses the normal recalculation: face the front into the bowl,
    # the back away from it, the rim outwards
    for poly in shell.data.polygons:
        c = poly.center
        r = math.hypot(c.x, c.y)
        if r > DISH_R + 0.001:
            want = Vector((c.x, c.y, 0))
        elif abs(c.z - depth(r)) < abs(c.z - depth(r) + 0.03):
            want = Vector((-c.x, -c.y, 4 * FOCUS))
        else:
            want = Vector((c.x, c.y, -4 * FOCUS))
        if poly.normal.dot(want) < 0:
            poly.flip()
    shell.data.update()
    parts = [shell]
    for k in range(8):   # radial ribs on the face
        a = 2 * math.pi * k / 8 + math.pi / 8
        d = Vector((math.cos(a), math.sin(a), 0))
        pts = [d * r + Vector((0, 0, depth(r) + 0.005)) for r in (0.07, 0.2, 0.32, DISH_R - 0.01)]
        for j, (p, q) in enumerate(zip(pts, pts[1:])):
            parts.append(beam(f'DishRib{k}{j}', m['steel'], p, q, 0.012, 0.008))
    ring = [(DISH_R - 0.004, depth(DISH_R) - 0.012), (DISH_R + 0.016, depth(DISH_R) - 0.012),
            (DISH_R + 0.016, depth(DISH_R) + 0.012), (DISH_R - 0.004, depth(DISH_R) + 0.012)]
    rim = gb.lathe('DishRim', m['steel'], ring + ring[:1], (0, 0, 0), segments=40)
    rim.data.polygons.foreach_set('select', [len(poly.vertices) > 4 for poly in rim.data.polygons])
    bm = bmesh.new()   # a closed ring: without the lathe's two caps (they would cover the bowl)
    bm.from_mesh(rim.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if len(f.verts) > 4], context='FACES_ONLY')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(rim.data)
    bm.free()
    parts.append(rim)
    # the feed: three struts to the horn at the focus
    focus = Vector((0, 0, FOCUS))
    for k in range(3):
        a = 2 * math.pi * k / 3 + math.pi / 2
        foot = Vector((math.cos(a) * (DISH_R - 0.03), math.sin(a) * (DISH_R - 0.03), depth(DISH_R - 0.03)))
        parts.append(beam(f'FeedStrut{k}', m['steel'], foot, focus, 0.012))
    parts.append(cylinder('FeedHorn', m['steel_light'], 0.03, 0.07, focus + Vector((0, 0, -0.01)), segments=12, radius2=0.018))
    parts.append(cylinder('FeedTip', m['remap'], 0.02, 0.02, focus + Vector((0, 0, 0.03)), segments=12, bevel=0))
    # behind it: the hub and the cross bar the yoke holds
    parts.append(cylinder('DishHub', m['steel'], 0.09, 0.1, (0, 0, -0.08), segments=16, bevel=0.006))
    parts.append(cylinder('DishAxle', m['steel_light'], 0.03, 0.36, (0, 0, -0.1), rotation=(0, math.pi / 2, 0), segments=12, bevel=0.003))
    dish = kit.merge('AntennaDish', parts)
    # stand it up (looking along -y), tilt it back, hang it on the trunnion
    dish.rotation_euler = (math.pi / 2 - TILT, 0, 0)
    dish.location = TRUNNION + Vector((0, -math.cos(TILT), math.sin(TILT))) * 0.1
    kit.bake_modifiers(dish)
    dish = kit.merge('AntennaDish', [dish], TRUNNION)
    head = kit.merge('AntennaHead', [
        cylinder('HeadBase', m['steel'], 0.13, 0.05, AXIS + Vector((0, 0, 0.075)), segments=20, bevel=0.005),
        *[kit.hexahedron(f'YokeArm{s}', m['steel'], [AXIS + Vector(p) for p in (
            (s * 0.17 - 0.02, -0.07, 0.09), (s * 0.17 + 0.02, -0.07, 0.09), (s * 0.17 + 0.02, 0.07, 0.09), (s * 0.17 - 0.02, 0.07, 0.09),
            (s * 0.17 - 0.02, -0.03, TRUNNION.z - AXIS.z + 0.04), (s * 0.17 + 0.02, -0.03, TRUNNION.z - AXIS.z + 0.04),
            (s * 0.17 + 0.02, 0.03, TRUNNION.z - AXIS.z + 0.04), (s * 0.17 - 0.02, 0.03, TRUNNION.z - AXIS.z + 0.04))], 0.006) for s in (-1, 1)],
        box('YokeBridge', m['steel'], (0.38, 0.12, 0.04), AXIS + Vector((0, 0, 0.11)), bevel=0.006),
        box('YokeBox', m['remap'], (0.14, 0.12, 0.08), AXIS + Vector((0, 0.1, 0.17)), bevel=0.012),
    ], AXIS)
    kit.parent(dish, head)
    return table, head, dish


# --------------------------------------------------------------------------- model

def rise(obj, start, end, depth):
    """Build: comes up out of the ground (never scaled to nothing: lamps hang on it)."""
    home = Vector(obj.location)
    kit.keys(obj, 'location', {0: home - Vector((0, 0, depth)), start: home - Vector((0, 0, depth)), end - 3: home + Vector((0, 0, 0.01)), end: home})


def build():
    gb.start('GDIRadar', BUILD_END)
    m = materials()
    root = kit.empty('GDIRadar')
    keys = kit.keys
    H = kit.HIDDEN

    # ---- the base spreads
    ground, step = base(m, root)
    ground = kit.parent(ground, root)
    kit.parent(step, ground)
    keys(ground, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 14: Vector((1.03, 1.03, 1)), 17: Vector((1, 1, 1))})

    # ---- the tower rises
    group = kit.parent(kit.empty('TowerGroup'), root)
    for obj in tower(m, root):
        kit.parent(obj, group)
    keys(group, 'location', {0: Vector((0, 0, -1.2)), 6: Vector((0, 0, -1.2)), 34: Vector((0, 0, 0.012)), 38: Vector((0, 0, 0))})
    for k, spike in enumerate(spikes(m)):
        kit.parent(spike, group)
        kit.grow(spike, 56 + 3 * k, 8, 2)

    # ---- the outbuildings come up out of the ground
    gen = kit.parent(generator(m, root), root)
    rise(gen, 18, 30, 0.45)
    cab = kit.parent(cabinet(m), root)
    rise(cab, 24, 34, 0.3)
    dome_obj, dome_lamps = dome(m)
    kit.parent(dome_obj, root)
    rise(dome_obj, 28, 40, 0.6)
    hut = kit.parent(shed(m), root)
    rise(hut, 22, 34, 0.45)

    # ---- the antenna comes up out of the pedestal, the dish unfolds
    table, head, dish = antenna(m)
    lift = kit.parent(kit.empty('AntennaLift', AXIS), group)
    kit.parent(table, lift)
    kit.parent(head, lift)
    keys(lift, 'location', {0: AXIS - Vector((0, 0, 1.15)), 38: AXIS - Vector((0, 0, 1.15)), 52: AXIS + Vector((0, 0, 0.01)), 55: AXIS})
    keys(dish, 'scale', {0: Vector((H, 1, 1)), 52: Vector((H, 1, 1)), 64: Vector((1.04, 1, 1)), 68: Vector((1, 1, 1))})

    # ---- lights (none hangs under a part that Build scales to nothing)
    lights = []
    x0, y0, x1, y1 = TOWER
    px0, py0, px1, py1 = PLATFORM
    for k, (x, y) in enumerate(((px0 + 0.07, py0 + 0.2), (px1 - 0.2, py0 + 0.07), (px1 - 0.07, py1 - 0.2))):
        gb.beacon(f'Corner{k}', m, (x, y, PLATFORM_TOP), 'red', group, 60 + 2 * k, kit.flashes(*((s + 20 * k, 8) for s in range(0, 180, 60))), lights)
    gb.beacon('GenLamp', m, (-0.56 - 0.17, -0.5 + 0.17, BASE + 0.27), 'amber', gen, 66, kit.flashes(*((s, 10) for s in range(0, 180, 30))), lights)
    gb.beacon('ShedLamp', m, (0.66, 0.24 + 0.32, BASE + 0.06), 'green', hut, 68, kit.flashes((0, 150)), lights)
    for k, lamp in enumerate(dome_lamps):
        kit.parent(lamp, dome_obj)
        lights.append((lamp, kit.flashes(*((s + 4 * k, 6) for s in range(0, 180, 32)))))

    gb.clips([(head, lambda o: gb.spin(o, 1))], lights)
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=3.8, target=(0, 0, 0.9))
