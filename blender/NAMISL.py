"""
Tiberian Fallout – Nod missile silo (NAMISL), after Tiberian Sun.

A low, flat bunker of stained concrete on two cells by two (foundation 2 × 2), like the
original's: sloped walls all round with a long red (house colour) bar on each of the
two faces the camera sees (front -Y, right +X), dark armour plates on the cut corners,
and on its flat top the silo: a long opening lying along the diagonal from the lower
left to the upper right of the screen, shut by two heavy lids that meet in the middle.
Two thin curved aerials rise from the screen's left and right corners; white lamps
sit beside them. Inside, the multi-warhead missile waits below ground.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Nodes:
    Launch     the middle of the silo's opening, at the top of the bunker: where the
               missile leaves
    Missile    the missile (rises out of the silo in Open)
    Silo       the opening's frame (turned 45°), holding the lids and the missile
    LidA/LidB  the two lids' hinges at the opening's long edges (swing open in Open)
    Lamp…      white lamps by the aerials (housing in Build, the light blinks in Idle)
Animations (glTF clips)
    Build    one-shot, 2 s: the bunker rises out of the ground, the red bars and the
             corner plates come on, the aerials grow, the lamps come on
    Idle     loop, 2 s: the white lamps blink (the original's NAMISL_B)
    Open     one-shot, 1.5 s: the lids swing open, then the missile comes up until it
             stands in the opening, ready to launch (the game holds it; played
             backwards the missile sinks and the lids shut)

Run headless:

    blender -b --factory-startup --python blender/NAMISL.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells of the
foundation are centred at (±0.5, ±0.5); origin in the middle on the ground.
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402
import NAPOWR as pw  # noqa: E402 – tubes along curves

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
HIDDEN = kit.HIDDEN

BUILD_END = 60
OPEN_FRAMES = 45
TOP = 0.26                  # the bunker's flat top
HOLE = (1.1, 0.8)           # the opening's length (along the diagonal) and width, in the Silo frame
LID = 0.05                  # the lids' thickness
MISSILE = 0.82              # the missile's length
MISSILE_UP = 0.08           # its foot above the top of the bunker when it stands ready
CONCRETE = '#8e8a80'
DIAG = Vector((1, 1, 0)).normalized()     # the screen's left to right
ACROSS = Vector((-1, 1, 0)).normalized()  # the screen's bottom to top


def bunker(m, root):
    """The bunker (concrete with the opening cut out, returned first) and its details;
    origin on the ground."""
    low = nb.chamfered(0, 0, 1.94, 1.94, 0.36)
    high = nb.chamfered(0, 0, 1.64, 1.64, 0.34)
    body = nb.prism('BunkerBody', m['steel'], low, high, 0, TOP, bevel=0.008)
    cutter = box('Cutter', m['dark'], (HOLE[0], HOLE[1], 1.0), (0, 0, TOP), bevel=0, rotation=(0, 0, math.pi / 4))
    cut = body.modifiers.new('Hole', 'BOOLEAN')
    cut.operation = 'DIFFERENCE'
    cut.object = cutter
    cut.solver = 'EXACT'
    cutter.hide_render = cutter.hide_viewport = True
    concrete = nb.concrete('Bunker', [body], root, CONCRETE)
    bpy.data.objects.remove(cutter, do_unlink=True)
    parts = [nb.prism('Apron', m['dirt'], nb.chamfered(0, 0, 2.0, 2.0, 0.34), nb.chamfered(0, 0, 2.0, 2.0, 0.34), 0, 0.008, bevel=0)]

    def on_slope(name, mat, d, a, b, t0, t1, lift=0.006):
        """A plate on the sloped wall facing `d` (unit axis), from a to b along the wall
        (-1..1 of the wall's length), between t0 and t1 up the slope."""
        side = Vector((-d.y, d.x, 0))
        corners = []
        for t in (t0, t1):
            reach = 0.97 + (0.82 - 0.97) * t
            span = (0.97 - 0.36) + ((0.82 - 0.34) - (0.97 - 0.36)) * t
            for s in (a, b):
                corners.append(d * reach + side * s * span + Vector((0, 0, TOP * t)))
        normal = (corners[1] - corners[0]).cross(corners[2] - corners[0]).normalized()
        if normal.dot(d) < 0:
            normal = -normal
        p0, p1, p2, p3 = corners[0], corners[1], corners[3], corners[2]
        return kit.hexahedron(name, mat, [p + normal * 0.001 for p in (p0, p1, p2, p3)] + [p + normal * lift for p in (p0, p1, p2, p3)], bevel=0)

    reds = [on_slope('RedFront', m['remap'], Vector((0, -1, 0)), -0.8, 0.8, 0.3, 0.62, 0.012),
            on_slope('RedRight', m['remap'], Vector((1, 0, 0)), -0.8, 0.8, 0.3, 0.62, 0.012)]
    for k, d in enumerate((Vector((0, 1, 0)), Vector((-1, 0, 0)))):
        parts.append(on_slope(f'Groove{k}', m['nplate_dark'], d, -0.75, 0.75, 0.35, 0.5, 0.004))
    # dark seams over the top
    for k, (a, b) in enumerate((((-0.7, 0.2), (-0.2, 0.7)), ((0.2, -0.7), (0.7, -0.2)))):
        parts.append(beam(f'Seam{k}', m['nplate_dark'], Vector((*a, TOP + 0.002)), Vector((*b, TOP + 0.002)), 0.03, 0.006))
    corners = []
    for k in range(4):   # dark armour plates over the cut corners
        a = math.radians(45 + 90 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        s = Vector((-d.y, d.x, 0))
        lo, hi = d * 1.115 + Vector((0, 0, 0.0)), d * 0.92 + Vector((0, 0, TOP))
        n = (hi - lo).cross(s).normalized()
        if n.dot(d) < 0:
            n = -n
        plate = kit.hexahedron(f'Corner{k}', m['nplate_dark'], (
            lo - s * 0.2 + n * 0.002, lo + s * 0.2 + n * 0.002, hi + s * 0.2 + n * 0.002, hi - s * 0.2 + n * 0.002,
            lo - s * 0.2 + n * 0.022, lo + s * 0.2 + n * 0.022, hi + s * 0.2 + n * 0.022, hi - s * 0.2 + n * 0.022), bevel=0.004)
        corners.append(kit.merge(f'Corner{k}', [plate], d * 1.0))
    return concrete, kit.merge('BunkerDetails', parts), reds, corners


def silo(m, root):
    """The opening's frame, the pit's walls and the two lids, built in the Silo's
    frame (the opening along x); returns (frame, lid A, lid B)."""
    length, width = HOLE
    parts = []
    for s in (-1, 1):   # the frame round the opening
        parts.append(box(f'FrameL{s}', m['nplate_dark'], (length + 0.1, 0.05, 0.03), (0, s * (width / 2 + 0.025), TOP + 0.012), bevel=0.004))
        parts.append(box(f'FrameS{s}', m['nplate_dark'], (0.05, width, 0.03), (s * (length / 2 + 0.025), 0, TOP + 0.012), bevel=0.004))
        # the pit's walls, down to the ground
        parts.append(box(f'PitL{s}', m['dark'], (length, 0.01, TOP), (0, s * (width / 2 - 0.006), TOP / 2), bevel=0))
        parts.append(box(f'PitS{s}', m['dark'], (0.01, width, TOP), (s * (length / 2 - 0.006), 0, TOP / 2), bevel=0))
        parts.append(box(f'Rail{s}', m['nsteel'], (length - 0.04, 0.02, 0.02), (0, s * (width / 2 - 0.02), TOP - 0.05), bevel=0))
    frame = kit.merge('SiloFrame', parts)
    lids = []
    for k, s in enumerate((-1, 1)):
        # a lid covers half the opening; its hinge is at the opening's long edge
        hinge = Vector((0, s * width / 2, TOP + 0.03))
        half = width / 2
        slab = box(f'Lid{k}Slab', m['steel'], (length + 0.02, half - 0.006, LID), (0, s * (half / 2 + 0.003), TOP + 0.03 + LID / 2 - 0.02), bevel=0.006)
        body = nb.concrete(f'Lid{k}', [slab], root, CONCRETE, hinge)
        details = [box(f'Lid{k}Rib{j}', m['nplate_dark'], (0.035, half - 0.06, 0.016), (x, s * half / 2, TOP + 0.03 + LID - 0.012), bevel=0.003)
                   for j, x in enumerate((-0.38, 0.0, 0.38))]
        details.append(box(f'Lid{k}Edge', m['nplate_dark'], (length - 0.06, 0.03, 0.012), (0, s * 0.03, TOP + 0.03 + LID - 0.014), bevel=0.002))
        details.append(cylinder(f'Lid{k}Hinge', m['nsteel'], 0.022, length * 0.9, hinge, rotation=(0, math.pi / 2, 0), segments=10, bevel=0))
        kit.parent(kit.merge(f'Lid{k}Details', details, hinge), body)
        lids.append(body)
    return frame, lids


def missile(m):
    """The missile, upright, its foot at the origin: a dark body with red bands, four
    fins at the foot and the cluster warhead's grey nose."""
    r = 0.09
    parts = [
        cylinder('MBody', m['nplate'], r, MISSILE * 0.62, (0, 0, MISSILE * 0.31 + 0.04), segments=16, bevel=0.004),
        cylinder('MNozzle', m['nplate_dark'], r * 0.7, 0.05, (0, 0, 0.025), segments=16, bevel=0.003, radius2=r * 0.9),
        cylinder('MWarhead', m['nsteel_light'], r * 1.15, MISSILE * 0.2, (0, 0, MISSILE * 0.72 + 0.04), segments=16, bevel=0.004),
        cylinder('MNose', m['nsteel_light'], r * 1.15, MISSILE * 0.18, (0, 0, MISSILE * 0.91 + 0.04), segments=16, bevel=0.003, radius2=0.01),
    ]
    for j, z in enumerate((0.16, 0.4)):
        parts.append(cylinder(f'MBand{j}', m['remap'], r + 0.004, 0.03, (0, 0, z), segments=16, bevel=0))
    for j in range(4):
        a = math.pi / 4 + j * math.pi / 2
        d = Vector((math.cos(a), math.sin(a), 0))
        parts.append(kit.hexahedron(f'MFin{j}', m['remap'], (
            d * r + Vector((0, 0, 0.05)) + d.cross(Vector((0, 0, 1))) * 0.006, d * (r + 0.06) + Vector((0, 0, 0.04)) + d.cross(Vector((0, 0, 1))) * 0.006,
            d * (r + 0.06) + Vector((0, 0, 0.1)) + d.cross(Vector((0, 0, 1))) * 0.006, d * r + Vector((0, 0, 0.2)) + d.cross(Vector((0, 0, 1))) * 0.006,
            d * r + Vector((0, 0, 0.05)) - d.cross(Vector((0, 0, 1))) * 0.006, d * (r + 0.06) + Vector((0, 0, 0.04)) - d.cross(Vector((0, 0, 1))) * 0.006,
            d * (r + 0.06) + Vector((0, 0, 0.1)) - d.cross(Vector((0, 0, 1))) * 0.006, d * r + Vector((0, 0, 0.2)) - d.cross(Vector((0, 0, 1))) * 0.006),
            bevel=0))
    return kit.merge('Missile', parts)


def aerial(m, k, corner, out):
    """A thin aerial rising from a corner and curling outwards; origin at its foot."""
    foot = corner + Vector((0, 0, 0.0))
    up = Vector((0, 0, 1))
    a, c, b = foot, foot + up * 0.5 - out * 0.05, foot + up * 0.48 + out * 0.22
    pts = [pw.bezier(a, c, b, t / 10) for t in range(11)]
    pts.append(b - up * 0.06 + out * 0.04)
    parts = pw.tube(f'Aerial{k}', m['nplate_dark'], pts, 0.011, 6)
    parts.append(cylinder(f'AerialFoot{k}', m['nsteel'], 0.03, 0.06, foot + Vector((0, 0, 0.03)), segments=10, bevel=0.003))
    return kit.merge(f'Aerial{k}', parts, foot)


def build():
    root = nb.start('NodMissileSilo', 'NodMissileSilo', BUILD_END)
    m = nb.materials()
    m['glow_white'] = kit.material('GlowWhite', (0, 0, 0), 1.0, emission=kit.srgb('#dfe8ff'), strength=3, alpha=0.3)
    keys = kit.keys

    group = kit.parent(kit.empty('BunkerGroup'), root)
    body, details, reds, corners = bunker(m, root)
    kit.parent(body, group)
    kit.parent(details, body)

    # the silo, built along x and turned onto the diagonal
    frame_holder = kit.parent(kit.empty('Silo'), group)
    frame, lids = silo(m, root)
    kit.parent(frame, frame_holder)
    hinges = []
    for k, lid in enumerate(lids):
        hinge = kit.parent(kit.empty(f'Lid{"AB"[k]}', lid.location), frame_holder)
        kit.parent(lid, hinge)
        hinges.append(hinge)
    launch = kit.parent(kit.empty('Launch', (0, 0, TOP)), frame_holder)
    shaft = missile(m)
    shaft.location = (0, 0, -MISSILE - 0.04)
    kit.parent(shaft, frame_holder)
    frame_holder.rotation_euler = (0, 0, math.pi / 4)
    launch.empty_display_size = 0.1

    # aerials on the screen's left and right corners, white lamps beside them
    aerials, lights = [], []
    for k, s in enumerate((-1, 1)):
        corner = DIAG * s * 0.93 + Vector((0, 0, TOP * 0.45))
        obj = kit.parent(aerial(m, k, corner, DIAG * s), group)
        aerials.append(obj)
        at = DIAG * s * 0.78 + ACROSS * 0.16 * s
        housing, light = nb.beacon(f'Lamp{k}', m, (at.x, at.y, TOP), 'white')
        kit.parent(housing, body)
        kit.parent(light, body)
        lights.append((housing, light))

    # Build: the bunker rises, the bars, plates and aerials come on, the lamps last
    nb.rise(group, 0, 20, TOP + 0.06)
    for k, obj in enumerate(reds):
        red = kit.parent(kit.merge(obj.name, [obj], (0, 0, TOP / 2)), body)
        kit.pop(red, 20 + 3 * k, 6)
    for k, obj in enumerate(corners):
        kit.parent(obj, body)
        kit.pop(obj, 24 + 2 * k, 6)
    for k, obj in enumerate(aerials):
        kit.grow(obj, 34 + 4 * k, 12, 2)
    for k, (housing, _) in enumerate(lights):
        kit.pop(housing, 48 + 3 * k, 5)
    nb.all_to_build()
    nb.blinking([(light, kit.flashes((k * 30, 4), (k * 30 + 8, 4))) for k, (_, light) in enumerate(lights)])

    # Open: the lids swing up and out, then the missile rises
    for k, hinge in enumerate(hinges):
        s = -1 if k == 0 else 1
        shut = Euler((0, 0, 0))
        wide = Euler((s * math.radians(-112), 0, 0))
        keys(hinge, 'rotation_euler', {0: shut, 4: Euler((s * math.radians(-4), 0, 0)), 22: wide, 25: Euler((s * math.radians(-108), 0, 0)),
                                       27: wide, OPEN_FRAMES: wide})
        kit.to_track(hinge, 'Open')
        hinge.rotation_euler = shut
    low = Vector(shaft.location)
    high = Vector((0, 0, TOP + MISSILE_UP))
    keys(shaft, 'location', {0: low, 16: low, OPEN_FRAMES - 4: high + Vector((0, 0, 0.01)), OPEN_FRAMES: high})
    kit.to_track(shaft, 'Open')
    shaft.location = low
    return len(kit.collection().objects)


def _rest():
    """Shuts the lids and lowers the missile again after a preview of Open."""
    for name in ('LidA', 'LidB'):
        bpy.data.objects[name].rotation_euler = (0, 0, 0)
    bpy.data.objects['Missile'].location = (0, 0, -MISSILE - 0.04)


def _render_and_rest(frames, out_dir, _render=kit.render_preview):
    result = _render(frames, out_dir)
    _rest()
    return result


if __name__ == '__main__':
    kit.render_preview = _render_and_rest
    nb.main(build, 'NAMISL', {'Build': [20, 40, BUILD_END], 'Idle': [0], 'Open': [12, 24, OPEN_FRAMES]}, ortho=2.8, target=(0, 0, 0.3))
