"""
Tiberian Fallout – Nod war factory (NAWEAP), after Tiberian Sun.

A low, dark concrete bunker with sloped walls and cut corners in the back of its
foundation (4 × 3 cells); every cut corner carries a red strut. Its roof is a lighter,
speckled slab with two grey chimneys and a small crane at the left. The gate is in the
right side (+X, towards the bottom right of the screen, as the original's door overlay
NAWEAP_B and the bib NAWEAPBB show): a wide opening, black inside, shut by one armoured
panel that sinks into the floor; three red oval lamps sit on the roof edge above it.
In front of the gate lies a big pale concrete apron (the original's bib) with a low
ramp in red and black stripes running out of the gate.

Nodes the game uses
    Exit    an empty on the floor inside the gate; its -Y axis points out of the gate
            (+X in Blender: the way the vehicles drive out)

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.5 s: the apron spreads, the bunker rises out of the ground,
             the red struts grow up its corners, chimneys and crane appear, the ramp
             comes, the lamps over the gate pop up
    Idle     loop, 2 s: the three lamps over the gate light up one after another
    Open     one-shot, 1.2 s: the gate's panel sinks into the floor (the game holds
             it open, then plays it backwards to shut it)

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NAWEAP.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -2 … 2 and y -1.5 … 1.5; the bunker stands on x -1.95 … 0.72, the apron
fills the rest towards +X.
"""
import math
import os
import sys

from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nod  # noqa: E402

BUILD_END = 84
OPEN_END = 36

BIB = 0.025                              # the apron's thickness (the gate's floor)
# the bunker: bottom and top outline (centre x, centre y, size x, size y, corner cut)
FOOT = (-0.615, 0.0, 2.67, 2.84, 0.34)
ROOF = (-0.68, 0.02, 1.84, 1.98, 0.18)
HEIGHT = 0.95
X_FOOT = FOOT[0] + FOOT[2] / 2           # the gate wall's foot (x)
X_TOP = ROOF[0] + ROOF[2] / 2            # … and its top
GATE_Y = 0.1                             # the gate's centre (y), a bit to the back like the original
GATE = (0.6, 0.56)                       # half width, height
GATE_BACK = -0.3                         # the opening's back wall (x)
RAMP = (X_FOOT - 0.02, 1.5)              # from x, to x (as wide as the gate)

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def wall_x(z):
    """x of the gate wall (sloped) at height z."""
    return X_FOOT + (X_TOP - X_FOOT) * z / HEIGHT


# --------------------------------------------------------------------------- parts

def apron(m, root):
    """The pale concrete apron in front of the gate: straight under the bunker's foot,
    round towards +X like the original's bib (a half ellipse)."""
    cx, rx, ry = X_FOOT - 0.25, 1.98 - (X_FOOT - 0.25), 1.48
    outline = []
    n = 24
    for k in range(n + 1):
        a = -math.pi / 2 + math.pi * k / n
        outline.append((cx + rx * math.cos(a) ** 0.8 if math.cos(a) > 0 else cx, ry * math.sin(a)))
    inset = [(x - 0.015 if x > cx + 0.01 else x, y * 0.99) for x, y in outline]
    slab = nod.prism('ApronSlab', m['steel'], outline, inset, 0, BIB, 0.004)
    return nod.concrete('Apron', [slab], root, '#a7a397')


def bunker(m, root):
    """The concrete bunker with the gate cut into its right wall."""
    import bpy
    body = nod.prism('BunkerBody', m['steel'], nod.chamfered(*FOOT), nod.chamfered(*ROOF), 0, HEIGHT, 0.015)
    cutter = box('GateCutter', m['dark'], (2.0, 2 * GATE[0], GATE[1] * 2), (GATE_BACK + 1.0, GATE_Y, 0), bevel=0)
    mod = body.modifiers.new('Gate', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    shell = nod.concrete('Bunker', [body], root, '#56575b')
    bpy.data.objects.remove(cutter, do_unlink=True)
    return shell


def roof_slab(m, root):
    """The roof: a lighter, speckled slab a little inside the walls' top."""
    rx, ry, sx, sy, c = ROOF
    slab = nod.prism('RoofSlab', m['steel'], nod.chamfered(rx, ry, sx - 0.06, sy - 0.06, c), nod.chamfered(rx, ry, sx - 0.1, sy - 0.1, c),
                     HEIGHT - 0.005, HEIGHT + 0.035, 0.008)
    deck = nod.prism('RoofDeck', m['steel'], nod.chamfered(-0.45, 0.33, 0.7, 0.8, 0.1), nod.chamfered(-0.45, 0.33, 0.62, 0.72, 0.08),
                     HEIGHT + 0.03, HEIGHT + 0.09, 0.008)
    return nod.concrete('Roof', [slab, deck], root, '#636260')


def gate_lining(m):
    """Inside the gate: dark walls, ceiling, back wall, the floor in plate with the slot
    the panel sinks into."""
    half, height = GATE
    depth = X_FOOT + 0.02 - GATE_BACK
    mid = GATE_BACK + depth / 2
    t = 0.01
    y = GATE_Y
    parts = [
        box('GateBack', m['dark'], (t, 2 * half, height), (GATE_BACK + t / 2, y, height / 2), bevel=0),
        box('GateCeiling', m['dark'], (depth, 2 * half, t), (mid, y, height - t / 2), bevel=0),
        *[box(f'GateWall{s}', m['nplate_dark'], (depth, t, height), (mid, y + s * (half - t / 2), height / 2), bevel=0) for s in (-1, 1)],
        box('GateFloor', m['nplate'], (depth, 2 * half, 0.01), (mid, y, BIB - 0.005), bevel=0),
        box('GateSlot', m['dark'], (0.07, 2 * half - 0.02, 0.004), (door_x(), y, BIB + 0.001), bevel=0),
    ]
    for k in range(4):  # guide rails on the floor
        parts.append(box(f'GateRail{k}', m['nsteel'], (depth - 0.12, 0.025, 0.012), (mid - 0.06, y - 0.45 + k * 0.3, BIB + 0.006), bevel=0))
    for k in range(3):  # ceiling lights, dim
        parts.append(box(f'GateLight{k}', m['lamp_amber'], (0.08, 0.3, 0.008), (GATE_BACK + 0.15 + k * 0.25, y, height - 0.014), bevel=0))
    return kit.merge('GateLining', parts)


def door_x():
    """Where the panel stands: just inside the sloped wall at the opening's top."""
    return wall_x(GATE[1]) - 0.05


def gate_frame(m):
    """The red frame round the opening, on the sloped wall."""
    half, height = GATE
    parts = []
    for s in (-1, 1):
        low = Vector((wall_x(0.0) + 0.02, GATE_Y + s * (half + 0.045), BIB))
        top = Vector((wall_x(height) + 0.02, GATE_Y + s * (half + 0.045), height + 0.045))
        parts.append(beam(f'Jamb{s}', m['remap'], low, top, 0.08, 0.07))
    y = Vector((0, half + 0.09, 0))
    lintel = Vector((wall_x(height + 0.045) + 0.02, GATE_Y, height + 0.045))
    parts.append(beam('Lintel', m['remap'], lintel - y, lintel + y, 0.08, 0.08))
    return kit.merge('GateFrame', parts, Vector((X_FOOT, GATE_Y, 0)))


def panel(m):
    """The armoured panel that shuts the gate (it sinks into the floor slot)."""
    half, height = GATE
    x = door_x()
    c = Vector((x, GATE_Y, height / 2))
    parts = [box('PanelPlate', m['nsteel'], (0.05, 2 * half - 0.01, height - 0.005), c, bevel=0.008)]
    for k in range(4):  # a grid of ribs, like the original's door
        parts.append(box(f'PanelRib{k}', m['nplate'], (0.06, 2 * half - 0.12, 0.03), c + Vector((0.005, 0, -height / 2 + 0.09 + k * 0.125)),
                         bevel=0.004))
    for k in range(5):
        parts.append(box(f'PanelPost{k}', m['nplate'], (0.06, 0.03, height - 0.08), c + Vector((0.005, -half + 0.12 + k * (2 * half - 0.24) / 4, 0)),
                         bevel=0.004))
    for s in (-1, 1):  # red and black chevrons at its sides
        parts.append(box(f'PanelEdge{s}', m['remap'], (0.06, 0.05, height - 0.04), c + Vector((0.008, s * (half - 0.05), 0)), bevel=0.003))
    # origin at the bunker's origin: shut is location 0, which the scene shows outside
    # the Open clip (its strip does not extrapolate)
    return kit.merge('GatePanel', parts)


def corners(m):
    """Red struts up the bunker's cut corners (each its own object, they grow up)."""
    low, high = nod.chamfered(*FOOT), nod.chamfered(*ROOF)
    out = []
    for k in range(1, 8, 2):  # the corner faces are every second side
        j = (k + 1) % 8
        a0, a1 = Vector((*low[k], 0)), Vector((*low[j], 0))
        b0, b1 = Vector((*high[k], HEIGHT)), Vector((*high[j], HEIGHT))
        normal = (a1 - a0).cross(b0 - a0).normalized()
        if normal.dot(a0 - Vector((FOOT[0], 0, 0))) < 0:
            normal = -normal
        parts = []
        for f in (0.12, 0.88):  # two bars each, like the original's double struts
            p, q = a0.lerp(a1, f), b0.lerp(b1, f)
            parts.append(beam(f'Edge{k}Bar{f}', m['remap'], p + normal * 0.03 + Vector((0, 0, 0.02)), q + normal * 0.03 + Vector((0, 0, 0.03)), 0.07, 0.05))
        mid = [a0.lerp(a1, t) for t in (0.2, 0.8)] + [b0.lerp(b1, t) for t in (0.8, 0.2)]
        inner = [p + normal * 0.004 for p in mid]
        outer = [p + normal * 0.018 for p in mid]
        parts.append(kit.hexahedron(f'Edge{k}Plate', m['nplate_dark'], (inner[0], inner[1], outer[1], outer[0], inner[3], inner[2], outer[2], outer[3]),
                                    bevel=0.003))
        out.append(kit.merge(f'Edge{k}', parts, (a0 + a1) / 2))
    return out


def walls(m):
    """Seams, window slits and vents along the long walls (front and back)."""
    parts = []
    y_foot, y_top = FOOT[3] / 2, ROOF[3] / 2 - ROOF[1]
    for s in (-1, 1):
        def on_wall(x, z, off=0.01):
            t = z / HEIGHT
            y = y_foot + (y_top - y_foot) * t + off
            return Vector((x, s * y, z))
        slope = math.atan2(y_foot - y_top, HEIGHT)
        for z in (0.22, 0.6):
            x0, x1 = face_x(z)
            parts.append(beam(f'Seam{s}{z}', m['nplate_dark'], on_wall(x0 + 0.03, z), on_wall(x1 - 0.03, z), 0.02, 0.03))
        x0, x1 = face_x(0.48)
        for k in range(5):
            x = x0 + 0.2 + k * (x1 - x0 - 0.4) / 4
            parts.append(box(f'Slit{s}{k}', m['dark'], (0.22, 0.03, 0.09), on_wall(x, 0.4, 0.0), bevel=0.004, rotation=(-s * slope, 0, 0)))
            parts.append(box(f'SlitHood{s}{k}', m['nplate'], (0.26, 0.06, 0.02), on_wall(x, 0.46, 0.02), bevel=0.004, rotation=(-s * slope, 0, 0)))
    return kit.merge('WallDetails', parts)


def face_x(z):
    """Where the long walls' flat face ends (x) at height z, between the cut corners."""
    t = z / HEIGHT
    lo = FOOT[0] - FOOT[2] / 2 + FOOT[4], FOOT[0] + FOOT[2] / 2 - FOOT[4]
    hi = ROOF[0] - ROOF[2] / 2 + ROOF[4], ROOF[0] + ROOF[2] / 2 - ROOF[4]
    return lo[0] + (hi[0] - lo[0]) * t, lo[1] + (hi[1] - lo[1]) * t


def chimneys(m):
    """Two tall grey chimneys on the roof (the back one taller); origins at their feet."""
    out = []
    for i, (x, y, h, r) in enumerate(((-1.0, 0.6, 0.95, 0.06), (-1.15, -0.05, 0.62, 0.05))):
        foot = Vector((x, y, HEIGHT + 0.035))
        parts = [cylinder(f'Chimney{i}', m['nsteel_light'], r, h, foot + Vector((0, 0, h / 2)), segments=14),
                 cylinder(f'ChimneyFoot{i}', m['nplate_dark'], r * 1.8, 0.07, foot + Vector((0, 0, 0.035)), segments=14),
                 cylinder(f'ChimneyBand{i}', m['nsteel'], r * 1.12, 0.04, foot + Vector((0, 0, h * 0.62)), segments=14, bevel=0)]
        if i == 0:  # the cap with its vent
            parts += [cylinder('ChimneyCap', m['nsteel'], r * 1.35, 0.1, foot + Vector((0, 0, h - 0.08)), segments=14),
                      cylinder('ChimneyVent', m['dark'], r * 0.6, 0.02, foot + Vector((0, 0, h + 0.005)), segments=10, bevel=0)]
        out.append(kit.merge(f'Chimney{i}', parts, foot))
    return out


def crane(m):
    """The small crane / machine on the roof's left: a housing with a jib and a hook,
    in pale steel and rust; origin at its foot."""
    foot = Vector((-1.3, -0.56, HEIGHT + 0.035))
    parts = [
        box('CraneBase', m['nplate_dark'], (0.34, 0.34, 0.06), foot + Vector((0, 0, 0.03)), bevel=0.01),
        box('CraneHouse', m['nsteel_light'], (0.24, 0.22, 0.16), foot + Vector((0, 0, 0.14)), bevel=0.015),
        box('CraneRoof', m['dirt'], (0.26, 0.24, 0.03), foot + Vector((0, 0, 0.235)), bevel=0.006),
        box('CraneWindow', m['dark'], (0.01, 0.14, 0.05), foot + Vector((0.121, 0, 0.17)), bevel=0),
        beam('CraneJib', m['dirt'], foot + Vector((-0.05, 0.0, 0.25)), foot + Vector((0.2, -0.22, 0.36)), 0.035),
        beam('CraneJibBack', m['dirt'], foot + Vector((-0.05, 0.0, 0.25)), foot + Vector((-0.14, 0.12, 0.27)), 0.03),
        box('CraneWeight', m['nplate'], (0.08, 0.08, 0.06), foot + Vector((-0.15, 0.13, 0.25)), bevel=0.008),
        beam('CraneCable', m['dark'], foot + Vector((0.2, -0.22, 0.35)), foot + Vector((0.2, -0.22, 0.2)), 0.008),
        box('CraneHook', m['nsteel'], (0.04, 0.04, 0.04), foot + Vector((0.2, -0.22, 0.18)), bevel=0.006),
        *[cylinder(f'CraneTank{k}', m['nsteel_light'], 0.05, 0.14, foot + Vector((-0.08 + 0.13 * k, 0.2, 0.07)), segments=12) for k in range(2)],
        *[cylinder(f'CraneTankBand{k}', m['dirt'], 0.053, 0.025, foot + Vector((-0.08 + 0.13 * k, 0.2, 0.09)), segments=12, bevel=0) for k in range(2)],
    ]
    return kit.merge('Crane', parts, foot)


def ramp(m):
    """The low ramp out of the gate: a dark wedge with red bars slanting across it."""
    x0, x1 = RAMP
    half = GATE[0] + 0.04
    length = x1 - x0
    hi, lo = 0.045, 0.012
    y = GATE_Y

    def wedge(name, mat, xa, xb, ya, yb, za, zb):
        return kit.hexahedron(name, mat, (
            (xa, ya, BIB - 0.002), (xb, ya, BIB - 0.002), (xb, yb, BIB - 0.002), (xa, yb, BIB - 0.002),
            (xa, ya, BIB + za), (xb, ya, BIB + zb), (xb, yb, BIB + zb), (xa, yb, BIB + za)), bevel=0)

    parts = [wedge('RampBase', m['hazard_dark'], x0, x1, y - half, y + half, hi, lo)]

    def top(x):
        return BIB + hi + (lo - hi) * (x - x0) / length

    step, width = 0.18, 0.09
    for k in range(-8, int(length / step) + 2):  # bars at 45°, cut to the ramp below
        c = x0 + k * step
        corners = [(c + (yy - y) + dx, yy) for yy, dx in ((y - half - 0.1, 0), (y - half - 0.1, width), (y + half + 0.1, width), (y + half + 0.1, 0))]
        low = [(x, yy, top(x) - 0.004) for x, yy in corners]
        high = [(x, yy, top(x) + 0.006) for x, yy in corners]
        parts.append(kit.hexahedron(f'RampBar{k}', m['remap'], low + high, bevel=0))
    obj = kit.merge('Ramp', parts, Vector((x0, y, 0)))
    nod.clip_to(obj, Vector(((x0 + x1) / 2, y, 0.05)), (length, 2 * half, 0.2), (0, 1))
    for s in (-1, 1):  # kerbs
        kerb = box(f'RampKerb{s}', m['nsteel'], (length, 0.05, 0.035), Vector(((x0 + x1) / 2, y + s * (half + 0.025), BIB + 0.017)), bevel=0.006)
        obj = kit.merge('Ramp', [obj, kerb], Vector((x0, y, 0)))
    return obj


# --------------------------------------------------------------------------- model

def build():
    root = nod.start('NodWarFactory', 'NodWarFactory', BUILD_END)
    m = nod.materials()
    keys = kit.keys

    # ---- the apron spreads
    ground = kit.parent(apron(m, root), root)
    keys(ground, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 14: Vector((1.02, 1.02, 1)), 17: Vector((1, 1, 1))})

    # ---- the bunker rises out of the ground (translation only: the panel and the
    # lamps hang on it and are keyed in Open/Idle)
    group = kit.parent(kit.empty('BunkerGroup'), root)
    for obj in (bunker(m, root), roof_slab(m, root), gate_lining(m), walls(m)):
        kit.parent(obj, group)
    keys(group, 'location', {0: Vector((0, 0, -0.9)), 8: Vector((0, 0, -0.9)), 38: Vector((0, 0, 0.012)), 42: Vector((0, 0, 0))})
    door = kit.parent(panel(m), group)
    exit_node = kit.parent(kit.empty('Exit', (GATE_BACK + 0.25, GATE_Y, BIB)), group)
    exit_node.rotation_euler = (0, 0, math.pi / 2)  # -Y out of the gate (+X)
    exit_node.empty_display_size = 0.2
    frame = kit.parent(gate_frame(m), group)
    kit.pop(frame, 40, 8)
    for i, edge in enumerate(corners(m)):
        kit.parent(edge, group)
        kit.grow(edge, 38 + 3 * i, 8, 2)

    # ---- on the roof
    for i, pipe in enumerate(chimneys(m)):
        kit.parent(pipe, group)
        kit.grow(pipe, 48 + 5 * i, 12, 2)
    machine = kit.parent(crane(m), group)
    kit.pop(machine, 56, 8)

    # ---- the ramp
    slope = kit.parent(ramp(m), root)
    keys(slope, 'scale', {0: Vector((kit.HIDDEN, 1, 1)), 30: Vector((kit.HIDDEN, 1, 1)), 46: Vector((1, 1, 1))})

    # ---- three red oval lamps on the roof edge over the gate: the housings pop in
    # (Build), the lights hang on the bunker group and blink (Idle)
    lights = []
    for k, y in enumerate((-0.52, 0.1, 0.72)):
        at = Vector((X_TOP - 0.12, y, HEIGHT + 0.035))
        holder = kit.merge(f'GateLamp{k}', [
            cylinder(f'GateLampRim{k}', m['nsteel_light'], 0.1, 0.035, at + Vector((0, 0, 0.0175)), segments=20, bevel=0.005),
            cylinder(f'GateLampBed{k}', m['nplate_dark'], 0.085, 0.01, at + Vector((0, 0, 0.038)), segments=20, bevel=0)], at)
        holder.data.transform(Matrix.Diagonal((0.75, 1.5, 1, 1)))
        kit.parent(holder, group)
        kit.pop(holder, 64 + 2 * k, 6)
        light = kit.merge(f'GateLamp{k}Light', [
            sphere(f'GateLampBulb{k}', m['lamp_red'], 0.07, at + Vector((0, 0, 0.045)), 16),
            sphere(f'GateLampHalo{k}', m['glow_red'], 0.11, at + Vector((0, 0, 0.05)), 16)], at + Vector((0, 0, 0.045)))
        light.data.transform(Matrix.Diagonal((0.75, 1.5, 0.35, 1)))
        kit.parent(light, group)
        lights.append((light, kit.flashes((k * 10, 14), (30 + k * 10, 14))))
    nod.clips(lights)

    # ---- Open: the panel sinks into the floor slot
    rest = door.location.copy()
    down = rest - Vector((0, 0, GATE[1] + 0.01))
    keys(door, 'location', {0: rest, 4: rest - Vector((0, 0, 0.02)), 30: down, OPEN_END: down})
    kit.to_track(door, 'Open')
    for track in door.animation_data.nla_tracks:  # the scene shows the gate shut
        track.strips[0].extrapolation = 'NOTHING'
    door.location = rest
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, 'NAWEAP', {'Build': [BUILD_END // 3, 2 * BUILD_END // 3, BUILD_END], 'Idle': [0, 30], 'Open': [16, OPEN_END]},
             ortho=4.8, target=(0, -0.1, 0.4))
