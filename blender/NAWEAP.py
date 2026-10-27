"""
Tiberian Fallout – Nod war factory (NAWEAP), after Tiberian Sun.

A low, wide concrete bunker with steeply sloped walls and cut corners (foundation
4 × 3 cells), the corners edged in the house colour. The gate is in its right side
(+X, towards the bottom right of the screen): a square opening, black inside, shut by
two armoured leaves; three red lamps sit on the edge above it, a ramp in red and black
stripes runs down from it to the edge of the foundation. On the flat roof: a raised
deck at the back with a caged dome, two tall pipes, a fan; dark window slits and
seams run along the long front wall.

Nodes the game uses
    Exit    an empty on the floor inside the gate; its -Y axis points out of the gate
            (+X in Blender: the way the vehicles drive out)

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.8 s: the pad spreads, the bunker rises out of the ground,
             the red edges, the roof deck, dome, pipes and fan appear, the ramp's
             stripes come, the lights come on
    Idle     loop, 2 s: the lamps over the gate light up one after another, the fan
             turns, the ramp lamps blink
    Open     one-shot, 1.2 s: the gate's leaves slide apart into the walls (played
             backwards it shuts)

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NAWEAP.py [-- --preview 0,30,84 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -2 … 2 and y -1.5 … 1.5; seen in the game, -X is the left and +X the right.
"""
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodbuilding  # noqa: E402 – clip_to()
import nodstructure as nod  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'NAWEAP.glb')
BLEND = os.path.join(HERE, 'NAWEAP.blend')
BUILD_END = 84
OPEN_END = 36

PAD = 0.02
# the bunker: bottom and top outline (centre x, centre y, size x, size y, corner cut)
CX = -0.55
FOOT = (CX, 0, 2.8, 2.8, 0.32)
ROOF = (CX + 0.05, 0.02, 2.06, 2.1, 0.2)
HEIGHT = 0.9
X_FOOT = CX + FOOT[2] / 2               # the gate wall's foot (x)
X_TOP = ROOF[0] + ROOF[2] / 2           # … and its top
GATE = (0.6, 0.62)                      # half width, height
GATE_BACK = 0.12                        # the opening's back wall (x)
LEAF_X = 0.58                           # where the leaves stand
RAMP = (X_FOOT, 1.98, 0.68)             # from x, to x, half width

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def wall_x(z):
    """x of the gate wall (sloped) at height z."""
    return X_FOOT + (X_TOP - X_FOOT) * z / HEIGHT


def outline(spec):
    return nod.chamfered(*spec)


# --------------------------------------------------------------------------- parts

def pad(m, root):
    """A low dark concrete pad under the bunker and the ramp."""
    slab = nod.prism('PadSlab', m['steel'], nod.chamfered(-0.02, 0, 3.96, 2.96, 0.3), nod.chamfered(-0.02, 0, 3.92, 2.92, 0.28), 0, PAD, 0.004)
    return nod.concrete('Pad', [slab], root, nod.DARK_GREY)


def bunker(m, root):
    """The concrete bunker with the gate cut into its right wall."""
    body = nod.prism('BunkerBody', m['steel'], outline(FOOT), outline(ROOF), PAD, HEIGHT, 0.015)
    cutter = box('GateCutter', m['dark'], (2.0, 2 * GATE[0], GATE[1] * 2), (GATE_BACK + 1.0, 0, 0), bevel=0)
    mod = body.modifiers.new('Gate', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    shell = nod.concrete('Bunker', [body], root, nod.GREY)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return shell


def gate_lining(m):
    """Inside the gate: dark walls, ceiling, back wall, the floor in plate."""
    half, height = GATE
    depth = X_FOOT + 0.02 - GATE_BACK
    mid = GATE_BACK + depth / 2
    t = 0.01
    parts = [
        box('GateBack', m['dark'], (t, 2 * half, height), (GATE_BACK + t / 2, 0, height / 2), bevel=0),
        box('GateCeiling', m['dark'], (depth, 2 * half, t), (mid, 0, height - t / 2), bevel=0),
        *[box(f'GateWall{s}', m['nplate_dark'], (depth, t, height), (mid, s * (half - t / 2), height / 2), bevel=0) for s in (-1, 1)],
        box('GateFloor', m['nplate'], (depth, 2 * half, 0.01), (mid, 0, PAD + 0.005), bevel=0),
    ]
    for k in range(4):  # guide rails on the floor
        parts.append(box(f'GateRail{k}', m['nsteel'], (depth, 0.025, 0.012), (mid, -0.45 + k * 0.3, PAD + 0.012), bevel=0))
    for k in range(3):  # ceiling lights, dim
        parts.append(box(f'GateLight{k}', m['lamp_amber'], (0.08, 0.3, 0.008), (GATE_BACK + 0.12 + k * 0.17, 0, height - 0.012), bevel=0))
    return kit.merge('GateLining', parts)


def gate_frame(m):
    """The red frame round the opening, on the sloped wall."""
    half, height = GATE
    parts = []
    for s in (-1, 1):
        low = Vector((wall_x(0.0) + 0.02, s * (half + 0.04), PAD))
        top = Vector((wall_x(height) + 0.02, s * (half + 0.04), height + 0.04))
        parts.append(beam(f'Jamb{s}', m['remap'], low, top, 0.08, 0.07))
    y = Vector((0, half + 0.08, 0))
    lintel = Vector((wall_x(height + 0.04) + 0.02, 0, height + 0.04))
    parts.append(beam('Lintel', m['remap'], lintel - y, lintel + y, 0.08, 0.08))
    parts.append(beam('LintelDark', m['nplate_dark'], lintel - y * 0.95 + Vector((0.02, 0, 0.06)), lintel + y * 0.95 + Vector((0.02, 0, 0.06)),
                      0.05, 0.04))
    return kit.merge('GateFrame', parts, Vector((X_FOOT, 0, 0)))


def leaves(m):
    """The two armoured leaves that shut the gate; each its own object (they slide)."""
    half, height = GATE
    out = []
    for s in (-1, 1):
        c = Vector((LEAF_X, s * half / 2, height / 2))
        parts = [box(f'Leaf{s}Plate', m['nplate'], (0.05, half, height - 0.01), c, bevel=0.008)]
        for k in range(4):
            parts.append(box(f'Leaf{s}Rib{k}', m['nplate_dark'], (0.06, half - 0.06, 0.03), c + Vector((0.005, 0, -height / 2 + 0.1 + k * 0.14)),
                             bevel=0.004))
        parts.append(box(f'Leaf{s}Stripe', m['remap'], (0.06, 0.04, height - 0.06), c + Vector((0.008, -s * (half / 2 - 0.03), 0)), bevel=0.003))
        # origin at the bunker's origin: shut is location 0, what the scene shows outside the clip
        out.append(kit.merge(f'Leaf{s}', parts))
    return out


def corners(m):
    """Red strips up the bunker's cut corners (each its own object, they grow up)."""
    low, high = outline(FOOT), outline(ROOF)
    out = []
    for k in range(1, 8, 2):  # the corner faces are every second side
        j = (k + 1) % 8
        a0, a1 = Vector((*low[k], PAD)), Vector((*low[j], PAD))
        b0, b1 = Vector((*high[k], HEIGHT)), Vector((*high[j], HEIGHT))
        normal = (a1 - a0).cross(b0 - a0).normalized()
        if normal.dot(a0 - Vector((CX, 0, 0))) < 0:
            normal = -normal
        pts = [a0.lerp(a1, 0.2), a0.lerp(a1, 0.8), b0.lerp(b1, 0.8), b0.lerp(b1, 0.2)]
        inner = [p + normal * 0.004 for p in pts]
        outer = [p + normal * 0.03 for p in pts]
        strip = kit.hexahedron(f'Edge{k}', m['remap'], (inner[0], inner[1], outer[1], outer[0], inner[3], inner[2], outer[2], outer[3]), bevel=0.004)
        out.append(kit.merge(f'Edge{k}', [strip], (a0 + a1) / 2))
    return out


def walls(m):
    """Window slits and seams along the long walls (front and back), vents on the left."""
    parts = []
    y0f, y0t = -FOOT[3] / 2, ROOF[1] - ROOF[3] / 2
    for s in (-1, 1):
        def on_wall(x, z, off=0.01):
            t = (z - PAD) / (HEIGHT - PAD)
            y = (y0f + (y0t - y0f) * t) * (1 if s < 0 else -1)
            return Vector((x, y + s * off * -1, z))
        for z in (0.3, 0.62):
            parts.append(beam(f'Seam{s}{z}', m['nplate_dark'], on_wall(CX - 0.9, z), on_wall(CX + 0.9, z), 0.02, 0.03))
        for k in range(4):
            x = CX - 0.9 + k * 0.5
            slit = box(f'Slit{s}{k}', m['dark'], (0.26, 0.03, 0.08), on_wall(x, 0.46, 0.0), bevel=0.004,
                       rotation=(math.radians(-21 * s), 0, 0))
            parts.append(slit)
            parts.append(box(f'SlitHood{s}{k}', m['nplate'], (0.3, 0.06, 0.02), on_wall(x, 0.52, 0.02), bevel=0.004,
                             rotation=(math.radians(-21 * s), 0, 0)))
    return kit.merge('WallDetails', parts)


def roof(m, root):
    """The raised deck at the back with its parts; returns (deck, dome, pipes, fan, fan mount)."""
    deck = nod.prism('DeckBody', m['steel'], nod.chamfered(-1.0, 0.35, 1.0, 1.1, 0.14), nod.chamfered(-1.0, 0.35, 0.9, 1.0, 0.12),
                     HEIGHT - 0.01, HEIGHT + 0.12, 0.01)
    deck = nod.concrete('Deck', [deck], root, nod.DARK_GREY)
    top = HEIGHT + 0.12
    dome_at = Vector((-1.1, -0.45, HEIGHT))
    dome = kit.merge('Dome', [
        cylinder('DomeBase', m['nplate_dark'], 0.17, 0.06, dome_at + Vector((0, 0, 0.03)), segments=20),
        sphere('DomeGlass', m['nsteel_light'], 0.13, dome_at + Vector((0, 0, 0.1)), 20),
        cylinder('DomeRing', m['remap'], 0.14, 0.025, dome_at + Vector((0, 0, 0.08)), segments=20, bevel=0),
        *[beam(f'DomeCage{k}', m['nplate_dark'], dome_at + Vector((math.cos(a) * 0.15, math.sin(a) * 0.15, 0.05)),
               dome_at + Vector((math.cos(a) * 0.06, math.sin(a) * 0.06, 0.24)), 0.014) for k, a in enumerate(i * math.pi / 3 for i in range(6))],
        cylinder('DomeCap', m['nplate'], 0.05, 0.03, dome_at + Vector((0, 0, 0.245)), segments=12),
    ], dome_at)
    pipes = []
    for i, (x, y, h, r) in enumerate(((-0.6, 0.55, 0.78, 0.04), (-0.35, 0.15, 0.55, 0.032))):
        foot = Vector((x, y, top if i == 0 else HEIGHT))
        parts = [cylinder(f'Pipe{i}', m['nsteel_light'], r, h, foot + Vector((0, 0, h / 2)), segments=12),
                 cylinder(f'PipeFoot{i}', m['nplate_dark'], r * 2, 0.06, foot + Vector((0, 0, 0.03)), segments=12),
                 cylinder(f'PipeBand{i}', m['remap'], r * 1.15, 0.03, foot + Vector((0, 0, h * 0.7)), segments=12, bevel=0)]
        if i == 0:
            parts.append(cylinder('PipeCap', m['nsteel'], r * 1.4, 0.07, foot + Vector((0, 0, h - 0.06)), segments=12))
        pipes.append(kit.merge(f'Pipe{i}', parts, foot))
    fan_at = Vector((-1.25, 0.55, top))
    housing = kit.merge('FanHousing', [
        cylinder('FanRing', m['nplate_dark'], 0.15, 0.05, fan_at + Vector((0, 0, 0.025)), segments=20),
        cylinder('FanHole', m['dark'], 0.125, 0.01, fan_at + Vector((0, 0, 0.051)), segments=20, bevel=0),
    ], fan_at)
    blades = kit.merge('Fan', [box(f'FanBlade{k}', m['nsteel'], (0.22, 0.04, 0.008), fan_at + Vector((0, 0, 0.045)), bevel=0,
                                   rotation=(math.radians(15), 0, k * math.pi / 3)) for k in range(3)] +
                       [cylinder('FanHub', m['nsteel_light'], 0.025, 0.02, fan_at + Vector((0, 0, 0.05)), segments=10)], fan_at)
    return deck, dome, pipes, housing, blades


def ramp(m):
    """The ramp in front of the gate: dark plate with red and black chevrons, kerbs."""
    x0, x1, half = RAMP
    length = x1 - x0
    mid = Vector(((x0 + x1) / 2, 0, PAD))
    parts = [box('RampPlate', m['nplate_dark'], (length, 2 * half, 0.012), mid + Vector((0, 0, 0.006)), bevel=0)]
    for k in range(5):
        x = x0 + 0.12 + k * 0.2
        for s in (-1, 1):  # chevrons pointing out of the gate
            parts.append(box(f'Chevron{k}{s}', m['remap'], (0.07, half * 0.95, 0.008), Vector((x + 0.12, s * half * 0.48, PAD + 0.014)), bevel=0,
                             rotation=(0, 0, s * math.radians(-28))))
    for s in (-1, 1):
        parts.append(box(f'Kerb{s}', m['nsteel'], (length, 0.05, 0.04), Vector((mid.x, s * (half + 0.02), PAD + 0.02)), bevel=0.006))
    obj = kit.merge('Ramp', parts, Vector((x0, 0, 0)))
    # the chevrons stick out of the plate at its sides: cut them to it
    nodbuilding.clip_to(obj, mid + Vector((0, 0, 0.02)), (length, 2 * half + 0.1, 0.06))
    return obj


# --------------------------------------------------------------------------- model

def build():
    root = nod.start('NodWarFactory', 'NodWarFactory', BUILD_END)
    m = nod.materials()
    keys = kit.keys

    # ---- the pad spreads
    ground = kit.parent(pad(m, root), root)
    keys(ground, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 14: Vector((1.02, 1.02, 1)), 17: Vector((1, 1, 1))})

    # ---- the bunker rises out of the ground, with its gate
    group = kit.parent(kit.empty('BunkerGroup'), root)
    for obj in (bunker(m, root), gate_lining(m), walls(m)):
        kit.parent(obj, group)
    keys(group, 'location', {0: Vector((0, 0, -0.95)), 8: Vector((0, 0, -0.95)), 38: Vector((0, 0, 0.012)), 42: Vector((0, 0, 0))})
    shut = leaves(m)
    for leaf in shut:
        kit.parent(leaf, group)
    exit_node = kit.parent(kit.empty('Exit', (GATE_BACK + 0.2, 0, PAD)), group)
    exit_node.rotation_euler = (0, 0, math.pi / 2)  # -Y out of the gate (+X)
    exit_node.empty_display_size = 0.2
    frame = kit.parent(gate_frame(m), group)
    kit.pop(frame, 40, 8)
    for i, edge in enumerate(corners(m)):
        kit.parent(edge, group)
        kit.grow(edge, 38 + 3 * i, 8, 2)

    # ---- the roof
    deck, dome, pipes, housing, fan = roof(m, root)
    kit.parent(deck, group)
    kit.pop(deck, 44, 8)
    kit.parent(dome, deck)
    kit.pop(dome, 54, 8)
    for i, pipe in enumerate(pipes):
        kit.parent(pipe, group)
        kit.grow(pipe, 52 + 5 * i, 12, 2)
    kit.parent(housing, deck)
    kit.pop(housing, 58, 6)
    kit.parent(fan, housing)

    # ---- the ramp
    slope = kit.parent(ramp(m), root)
    keys(slope, 'scale', {0: Vector((kit.HIDDEN, 1, 1)), 30: Vector((kit.HIDDEN, 1, 1)), 46: Vector((1, 1, 1))})

    # ---- lights: three red lamps over the gate, amber ones at the ramp's end
    lights = []
    for k, y in enumerate((-0.42, 0.0, 0.42)):
        at = Vector((X_TOP - 0.06, y, HEIGHT))
        holder = kit.merge(f'GateLamp{k}', [
            cylinder(f'GateLampBase{k}', m['nplate_dark'], 0.08, 0.03, at + Vector((0, 0, 0.015)), segments=16, bevel=0.004)], at)
        holder.data.transform(Matrix.Diagonal((1, 1.4, 1, 1)))
        kit.parent(holder, group)
        kit.pop(holder, 64 + 2 * k, 6)
        light = kit.merge(f'GateLamp{k}Light', [
            sphere(f'GateLampBulb{k}', m['lamp_red'], 0.06, at + Vector((0, 0, 0.03)), 14),
            sphere(f'GateLampHalo{k}', m['glow_red'], 0.1, at + Vector((0, 0, 0.03)), 14)], at + Vector((0, 0, 0.03)))
        light.data.transform(Matrix.Diagonal((1, 1.4, 0.45, 1)))
        kit.parent(light, holder)
        lights.append((light, kit.flashes((k * 10, 14), (30 + k * 10, 14))))
    for s in (-1, 1):
        at = Vector((RAMP[1] - 0.06, s * (RAMP[2] + 0.02), PAD + 0.04))
        lights.append((nod.lamp(m, slope, f'RampLamp{s}', at, 'amber', 70 + s), kit.flashes((0 if s < 0 else 30, 10))))
    nod.clips(lights, [(fan, lambda o: nod.spin(o, kit.IDLE_END, 2, 2))])

    # ---- Open: the leaves slide apart into the walls
    half = GATE[0]
    for s, leaf in zip((-1, 1), shut):
        rest = leaf.location.copy()
        keys(leaf, 'location', {0: rest, 4: rest + Vector((0, s * 0.02, 0)), 30: rest + Vector((0, s * (half + 0.02), 0)),
                                OPEN_END: rest + Vector((0, s * (half + 0.02), 0))})
        kit.to_track(leaf, 'Open')
        for track in leaf.animation_data.nla_tracks:  # the scene shows the gate shut
            track.strips[0].extrapolation = 'NOTHING'
        leaf.location = rest
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, ortho=4.8, target=(0, -0.1, 0.4))
