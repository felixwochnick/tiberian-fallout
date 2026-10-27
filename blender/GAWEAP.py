"""
Tiberian Fallout – GDI war factory (GAWEAP), after Tiberian Sun.

A massive armoured works on a concrete pad (foundation 4 × 3 cells). On the left the
tall assembly hall: sloped camouflaged walls, a roof deck with two fans and a pipe
run, behind it two big rounded armour blocks in the house colour. In its front the
gate: a dark bay deep into the hall under a steel portal, closed by a slanted door
in the house colour that runs down to the ground like a ramp between steel cheeks.
On the right a lower block with house-colour armour on its roof and an exhaust
stack, in front of it a grey vaulted hangar on a camouflaged plinth; grey pipes on
the left end. In front of the gate an apron in hazard stripes.

Node
    Exit     empty on the floor of the bay, where a finished vehicle stands; its -Y
             axis (glTF +Z) points out of the gate

Materials as for the barracks (see GAPILE.py): Camo_* is the baked camouflage in a
pale shade of the house colour, Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.8 s: the pad spreads, the hall and the right block rise out of
             the ground, the hangar's vault rolls out, the door swings down shut, the
             armour, fans, stack and lights appear
    Idle     loop, 2 s: the fans turn, the beacons blink
    Open     one-shot, 1.2 s: the door swings up and stays open (the game plays it
             backwards to close it)

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAWEAP.py [-- --preview 0,40,84 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -2 … 2 and y -1.5 … 1.5; seen in the game, -X is the left and +X the right.
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
import housecamo  # noqa: E402

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAWEAP.glb')
BLEND = os.path.join(HERE, 'GAWEAP.blend')

BUILD_END = 84
OPEN_END = 36

PAD = 0.03
HALL = (-1.92, -0.8, 0.14, 1.4)     # the assembly hall: x0, y0, x1, y1
HALL_TOP = 0.8
WALL_SLOPE = 0.07                   # how far the walls lean in up to the roof
BLOCK = (0.1, 0.0, 1.92, 1.4)       # the right block
BLOCK_TOP = 0.62
GATE_X = -1.02                      # middle of the gate
GATE_HALF = 0.48
GATE_TOP = 0.66
BAY_BACK = 0.36                     # the bay's back wall
HINGE = Vector((GATE_X, HALL[1] - 0.07, GATE_TOP + 0.07))
DOOR_REACH = 0.56                   # how far in front of the hinge the closed door meets the ground
DOOR_OPEN = math.radians(-100)      # the door's swing about its hinge (x)
HANGAR = (0.24, 1.8, -0.64, 0.17, 0.53)   # x0, x1, axis y, axis z, radius
PLINTH = (0.12, -1.26, 1.92, 0.0)

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'hangar': material('Hangar', srgb('#9a9ea2'), 0.45, 0.7),
        'hazard': material('Hazard', srgb('#e2a21c'), 0.6),
        'remap_dark': housecamo.shade('RemapDark', 0.6, 1.0, 0.6),
    })
    return m


def door_geometry():
    """Direction (unit) and length of the closed door from its hinge down to the ground."""
    drop = HINGE.z - PAD
    length = math.hypot(drop, DOOR_REACH)
    return Vector((0, -DOOR_REACH / length, -drop / length)), length


# --------------------------------------------------------------------------- parts

def pad(m):
    """Concrete pad with chamfered corners, the apron in hazard stripes before the gate."""
    parts = [gb.slab('PadSlab', m['concrete'], gb.chamfered(-1.98, -1.48, 1.98, 1.48, 0.2), PAD, inset=0.01, bevel=0.004)]
    for x in (-1.0, 0.0, 1.0):   # joints between the slabs
        parts.append(box(f'PadJoint{x}', m['concrete_dark'], (0.01, 2.9, 0.003), (x, 0, PAD + 0.0015), bevel=0))
    for y in (-0.6, 0.5):
        parts.append(box(f'PadJointY{y}', m['concrete_dark'], (3.9, 0.01, 0.003), (0, y, PAD + 0.0015), bevel=0))
    y0, y1 = -1.47, HALL[1] - 0.02
    parts.append(box('Apron', m['dark'], (2 * GATE_HALF + 0.2, y1 - y0, 0.006), (GATE_X, (y0 + y1) / 2, PAD + 0.003), bevel=0))
    for k in range(9):
        x = GATE_X - GATE_HALF - 0.02 + k * (2 * GATE_HALF + 0.04) / 8
        parts.append(box(f'ApronStripe{k}', m['hazard'], (0.05, 0.16, 0.008), (x, y0 + 0.1, PAD + 0.004), bevel=0, rotation=(0, 0, math.radians(30))))
    return kit.merge('Pad', parts)


def hall_body(m, root):
    """The assembly hall's camouflaged body with the bay cut into its front."""
    x0, y0, x1, y1 = HALL
    body = gb.slab('HallBody', m['sand'], gb.chamfered(x0, y0, x1, y1, (0.0, 0.0, 0.0, 0.18)), HALL_TOP - PAD, inset=WALL_SLOPE, z0=PAD, bevel=0.012)
    cutter = box('BayCutter', m['dark'], (2 * GATE_HALF, BAY_BACK - y0 + 0.4, GATE_TOP + 0.1), (GATE_X, (BAY_BACK + y0 - 0.4) / 2, (GATE_TOP - 0.1) / 2), bevel=0)
    mod = body.modifiers.new('Bay', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    kit.bake_modifiers(body)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return gb.camo(body, root)


def bay(m):
    """The inside of the bay (dark walls, ceiling, back; a grating floor with guide
    lines) and the steel portal round the gate."""
    y0 = HALL[1] - 0.02
    depth = BAY_BACK - y0
    mid = (BAY_BACK + y0) / 2
    t = 0.01
    parts = [
        box('BayBack', m['dark'], (2 * GATE_HALF, t, GATE_TOP), (GATE_X, BAY_BACK - t / 2, GATE_TOP / 2), bevel=0),
        box('BayCeiling', m['dark'], (2 * GATE_HALF, depth, t), (GATE_X, mid, GATE_TOP - t / 2), bevel=0),
        box('BayFloor', m['grating'], (2 * GATE_HALF, depth, 0.008), (GATE_X, mid, PAD + 0.004), bevel=0),
    ]
    for s in (-1, 1):
        parts.append(box(f'BayWall{s}', m['dark'], (t, depth, GATE_TOP), (GATE_X + s * (GATE_HALF - t / 2), mid, GATE_TOP / 2), bevel=0))
        parts.append(box(f'BayLine{s}', m['hazard'], (0.025, depth - 0.1, 0.004), (GATE_X + s * 0.36, mid, PAD + 0.009), bevel=0))
        # ceiling lamps in the bay
        parts.append(box(f'BayLamp{s}', m['lamp_white'], (0.05, 0.3, 0.008), (GATE_X + s * 0.25, mid + 0.1, GATE_TOP - 0.012), bevel=0))
    # the portal: two posts and a heavy lintel standing out of the front face
    py = HALL[1] - 0.05
    for s in (-1, 1):
        parts.append(box(f'PortalPost{s}', m['steel'], (0.08, 0.1, GATE_TOP + 0.08), (GATE_X + s * (GATE_HALF + 0.04), py, (GATE_TOP + 0.08) / 2), bevel=0.008))
    parts.append(box('PortalLintel', m['steel'], (2 * GATE_HALF + 0.16, 0.12, 0.1), (GATE_X, py, GATE_TOP + 0.05), bevel=0.01))
    parts.append(box('PortalStripe', m['hazard'], (2 * GATE_HALF, 0.006, 0.03), (GATE_X, py - 0.062, GATE_TOP + 0.05), bevel=0))
    return kit.merge('Bay', parts, (GATE_X, mid, 0))


def cheeks(m):
    """Steel cheeks and guide rails on both sides of the slanted door (static)."""
    d, length = door_geometry()
    parts = []
    tip = HINGE + d * length
    for s in (-1, 1):
        x = GATE_X + s * (GATE_HALF + 0.05)
        profile = [(HALL[1] + 0.02, PAD), (tip.y + 0.04, PAD), (HINGE.y, HINGE.z + 0.02), (HALL[1] + 0.02, HINGE.z + 0.02)]
        parts.append(gb.prism(f'Cheek{s}', m['steel'], profile, x - 0.025, x + 0.025, 'X', bevel=0.004))
        top = HINGE - d * 0.18 + Vector((0, 0, 0.0))
        parts.append(beam(f'Rail{s}', m['steel_light'], Vector((x, top.y, top.z)), Vector((x, tip.y - 0.04, PAD + 0.01)), 0.04, 0.05))
        parts.append(box(f'RailFoot{s}', m['concrete_dark'], (0.1, 0.12, 0.04), (x, tip.y - 0.02, PAD + 0.02), bevel=0.006))
    return kit.merge('Cheeks', parts, (GATE_X, HALL[1], 0))


def door(m):
    """The slanted door in the house colour, its origin on the hinge (it swings about x)."""
    d, length = door_geometry()
    normal = Vector((0, d.z, -d.y)) * -1   # out of the door, forward and up
    if normal.z < 0:
        normal = -normal
    width = 2 * GATE_HALF + 0.04
    parts = [beam('DoorLeaf', m['remap'], HINGE, HINGE + d * length, width, 0.04)]
    for k in range(7):  # ribs across
        p = HINGE + d * (length * (k + 0.5) / 7) + normal * 0.024
        parts.append(beam(f'DoorRib{k}', m['remap_dark'], p - Vector((width / 2 - 0.03, 0, 0)), p + Vector((width / 2 - 0.03, 0, 0)), 0.025, 0.012))
    for s in (-1, 1):  # steel edges
        x = Vector((s * (width / 2 - 0.02), 0, 0))
        parts.append(beam(f'DoorEdge{s}', m['steel'], HINGE + x + normal * 0.02, HINGE + d * length + x + normal * 0.02, 0.04, 0.03))
    parts.append(cylinder('DoorHinge', m['steel'], 0.035, width + 0.02, HINGE, rotation=(0, math.pi / 2, 0), segments=12))
    parts.append(box('DoorFoot', m['steel'], (width, 0.05, 0.03), HINGE + d * (length - 0.02) + normal * 0.01, bevel=0.004))
    return kit.merge('Door', parts, HINGE)


def hall_roof(m):
    """Roof deck of the hall: plates, a pipe run, vents, an edge in the house colour."""
    x0, y0, x1, y1 = HALL
    s = WALL_SLOPE
    z = HALL_TOP
    parts = [
        box('RoofWalk', m['grating'], (x1 - x0 - 2 * s - 0.2, 0.2, 0.012), ((x0 + x1) / 2, 0.46, z + 0.006), bevel=0),
        box('RoofHatch', m['steel'], (0.22, 0.16, 0.02), (-0.45, -0.3, z + 0.01), bevel=0.004),
        box('RoofEdge', m['remap'], (x1 - x0 - 2 * s, 0.04, 0.03), ((x0 + x1) / 2, y0 + s + 0.02, z + 0.015), bevel=0.004),
    ]
    for k in range(5):  # roof seams
        x = x0 + 0.3 + k * 0.38
        parts.append(box(f'RoofSeam{k}', m['concrete_dark'], (0.012, 1.1, 0.004), (x, y0 + s + 0.6, z + 0.002), bevel=0))
    # the pipe run across the deck and down the right side
    for k, y in enumerate((0.42, 0.5)):
        parts.append(cylinder(f'RoofPipe{k}', m['steel_light'], 0.025, x1 - x0 - 0.3, ((x0 + x1) / 2, y, z + 0.05), rotation=(0, math.pi / 2, 0), segments=12))
        for j, x in enumerate((x0 + 0.3, (x0 + x1) / 2, x1 - 0.3)):
            parts.append(box(f'PipeStand{k}{j}', m['steel'], (0.03, 0.05, 0.04), (x, y, z + 0.02), bevel=0))
    parts.append(kit.vent_block('VentA', m, -0.2, -0.45))
    parts[-1].location.z = z
    return kit.merge('HallRoof', parts)


def hall_walls(m):
    """Ribs, band and windows on the hall's front face beside the gate, the lights over it."""
    x0, y0, x1, y1 = HALL
    parts = []
    face = y0 + 0.01

    def on_face(z):  # the front face leans in towards the roof
        return face + WALL_SLOPE * (z - PAD) / (HALL_TOP - PAD)

    for k, x in enumerate((-0.42, -0.26, -0.1, 0.04, -1.7, -1.82)):
        parts.append(beam(f'WallRib{k}', m['steel'], Vector((x, on_face(PAD) - 0.012, PAD + 0.01)), Vector((x, on_face(HALL_TOP - 0.06) - 0.012, HALL_TOP - 0.06)), 0.03, 0.02))
    z = 0.62
    parts.append(box('WallBand', m['remap'], (0.58, 0.012, 0.05), (-0.2, on_face(z) - 0.008, z), bevel=0.003, rotation=(math.radians(-5), 0, 0)))
    for k, x in enumerate((-0.38, -0.18, 0.02)):
        parts.append(box(f'Window{k}', m['window'], (0.1, 0.012, 0.05), (x, on_face(0.45) - 0.008, 0.45), bevel=0.002))
    parts.append(box('SideDoor', m['dark'], (0.12, 0.012, 0.2), (-0.24, on_face(0.13) - 0.008, PAD + 0.1), bevel=0.003))
    # the right face of the hall above the right block: ribs
    for k in range(4):
        y = 0.12 + k * 0.32
        parts.append(box(f'HallSideRib{k}', m['steel'], (0.02, 0.03, HALL_TOP - BLOCK_TOP - 0.03), (x1 - WALL_SLOPE * 0.85, y, (HALL_TOP + BLOCK_TOP) / 2), bevel=0))
    # the left end: grey pipes bent out of the wall and back
    for k, (y, h) in enumerate(((-0.45, 0.22), (-0.2, 0.3))):
        xo = x0 - 0.06
        parts += [
            beam(f'LeftPipeA{k}', m['steel_light'], (x0 + 0.03, y - 0.15, h), (xo, y - 0.15, h), 0.035),
            beam(f'LeftPipeB{k}', m['steel_light'], (xo, y - 0.15, h), (xo, y + 0.15, h), 0.035),
            beam(f'LeftPipeC{k}', m['steel_light'], (xo, y + 0.15, h), (x0 + 0.03, y + 0.15, h), 0.035),
            beam(f'LeftPipeLeg{k}', m['steel'], (xo, y, PAD), (xo, y, h), 0.025),
        ]
    return kit.merge('HallWalls', parts)


def armour(m, name, x0, x1, y0, y1, z, height):
    """A rounded armour block in the house colour lying on a roof, its origin at the bottom."""
    parts = [box(name, m['remap'], (x1 - x0, y1 - y0, height), ((x0 + x1) / 2, (y0 + y1) / 2, z + height / 2), bevel=min(0.1, height * 0.45))]
    parts[0].modifiers['Bevel'].segments = 5
    parts[0].modifiers['Bevel'].angle_limit = math.radians(30)
    for k in range(3):  # grooves across
        x = x0 + (k + 1) * (x1 - x0) / 4
        parts.append(box(f'{name}Groove{k}', m['remap_dark'], (0.018, y1 - y0 - 0.1, 0.01), (x, (y0 + y1) / 2, z + height + 0.001), bevel=0))
    parts.append(box(f'{name}Seat', m['steel'], (x1 - x0 + 0.04, y1 - y0 + 0.04, 0.03), ((x0 + x1) / 2, (y0 + y1) / 2, z + 0.015), bevel=0.006))
    return kit.merge(name, parts, ((x0 + x1) / 2, (y0 + y1) / 2, z))


def block_body(m, root):
    x0, y0, x1, y1 = BLOCK
    body = gb.slab('BlockBody', m['sand'], gb.chamfered(x0, y0, x1, y1, (0.0, 0.0, 0.15, 0.0)), BLOCK_TOP - PAD, inset=0.05, z0=PAD, bevel=0.012)
    return gb.camo(body, root)


def block_details(m):
    x0, y0, x1, y1 = BLOCK
    parts = []
    face = x1 - 0.015
    for k in range(6):  # ribs on the right face
        y = y0 + 0.12 + k * 0.2
        parts.append(beam(f'BlockRib{k}', m['steel'], (face + 0.01, y, PAD + 0.02), (face - 0.04, y, BLOCK_TOP - 0.04), 0.025, 0.025))
    parts.append(box('BlockBand', m['remap'], (0.012, 1.1, 0.045), (face - 0.025, 0.68, 0.5), bevel=0.003, rotation=(0, math.radians(5), 0)))
    parts.append(kit.vent_block('BlockVent', m, 0.5, 0.18))
    parts[-1].location.z = BLOCK_TOP
    parts.append(box('BlockDeck', m['grating'], (1.6, 0.3, 0.01), (1.0, 0.18, BLOCK_TOP + 0.005), bevel=0))
    return kit.merge('BlockDetails', parts)


def stack(m):
    """Exhaust stack on the right block, origin at its foot (it grows from there)."""
    foot = Vector((1.62, 0.2, BLOCK_TOP))
    parts = [
        box('StackFoot', m['steel'], (0.14, 0.14, 0.06), foot + Vector((0, 0, 0.03)), bevel=0.006),
        cylinder('Stack', m['steel'], 0.04, 0.42, foot + Vector((0, 0, 0.21)), segments=12),
        cylinder('StackBand', m['remap'], 0.043, 0.03, foot + Vector((0, 0, 0.3)), segments=12, bevel=0),
        cylinder('StackCap', m['dark'], 0.05, 0.03, foot + Vector((0, 0, 0.42)), segments=12),
    ]
    return kit.merge('ExhaustStack', parts, foot)


def plinth(m, root):
    x0, y0, x1, y1 = PLINTH
    body = gb.slab('Plinth', m['sand'], gb.chamfered(x0, y0, x1, y1, (0.08, 0.08, 0.0, 0.0)), HANGAR[3] - PAD, inset=0.03, z0=PAD, bevel=0.01)
    return gb.camo(body, root)


def hangar(m):
    """The grey vault with ribs, its origin at the left end on the axis (it rolls out
    along x from there)."""
    x0, x1, ay, az, r = HANGAR
    shell = gb.prism('Vault', m['hangar'], gb.arc((ay, az), r, 0, math.pi, 24), x0 + 0.05, x1 - 0.05, 'X', bevel=0.004)
    parts = [shell]
    n = 9
    for k in range(n):  # ribs over the vault
        x = x0 + 0.1 + k * (x1 - x0 - 0.2) / (n - 1)
        rib = gb.arc((ay, az), r + 0.012, 0, math.pi, 24) + gb.arc((ay, az), r - 0.01, math.pi, 0, 24)
        parts.append(gb.prism(f'VaultRib{k}', m['steel'], rib, x - 0.012, x + 0.012, 'X'))
    # skylights along the top, a band in the house colour
    parts.append(box('VaultLight', m['window'], (x1 - x0 - 0.4, 0.06, 0.012), ((x0 + x1) / 2, ay, az + r + 0.004), bevel=0))
    return kit.merge('Hangar', parts, (x0, ay, az))


def hangar_ends(m, root):
    """The camouflaged arches closing the vault at both ends."""
    x0, x1, ay, az, r = HANGAR
    profile = gb.arc((ay, az), r + 0.07, 0, math.pi, 20) + gb.arc((ay, az), r - 0.06, math.pi, 0, 20)
    parts = [gb.prism('EndL', m['sand'], profile, x0 - 0.04, x0 + 0.08, 'X', bevel=0.006),
             gb.prism('EndR', m['sand'], profile, x1 - 0.08, x1 + 0.04, 'X', bevel=0.006)]
    return gb.camo(kit.merge('HangarEnds', parts), root)


def hangar_end_details(m):
    x0, x1, ay, az, r = HANGAR
    parts = [gb.prism('EndPlateR', m['steel'], gb.arc((ay, az), r - 0.06, 0, math.pi, 20), x1 - 0.06, x1 + 0.02, 'X'),
             box('EndDoor', m['dark'], (0.012, 0.26, 0.24), (x1 + 0.022, ay, az + 0.12), bevel=0),
             box('EndDoorFrame', m['remap'], (0.01, 0.3, 0.025), (x1 + 0.026, ay, az + 0.25), bevel=0)]
    for k in range(3):
        parts.append(box(f'EndDoorSlat{k}', m['steel'], (0.006, 0.24, 0.01), (x1 + 0.03, ay, az + 0.04 + k * 0.07), bevel=0))
    return kit.merge('HangarEndDetails', parts)


# --------------------------------------------------------------------------- model

def build():
    gb.start('GDIWarFactory', BUILD_END)
    m = materials()
    root = kit.empty('GDIWarFactory')
    keys = kit.keys
    H = kit.HIDDEN

    # ---- the pad spreads
    ground = kit.parent(pad(m), root)
    keys(ground, 'scale', {0: Vector((0.05, 0.05, 1)), 2: Vector((0.05, 0.05, 1)), 14: Vector((1.02, 1.02, 1)), 17: Vector((1, 1, 1))})

    exit_node = kit.parent(kit.empty('Exit', (GATE_X, -0.24, PAD)), root)
    exit_node.empty_display_size = 0.3

    # ---- the hall rises
    hall = kit.parent(kit.empty('HallGroup'), root)
    for obj in (hall_body(m, root), bay(m), hall_roof(m), hall_walls(m)):
        kit.parent(obj, hall)
    keys(hall, 'location', {0: Vector((0, 0, -0.85)), 6: Vector((0, 0, -0.85)), 30: Vector((0, 0, 0.012)), 34: Vector((0, 0, 0))})

    # ---- the right block and the hangar's plinth rise
    block = kit.parent(kit.empty('BlockGroup'), root)
    for obj in (block_body(m, root), block_details(m)):
        kit.parent(obj, block)
    keys(block, 'location', {0: Vector((0, 0, -0.7)), 12: Vector((0, 0, -0.7)), 34: Vector((0, 0, 0.01)), 38: Vector((0, 0, 0))})
    base = kit.parent(kit.empty('PlinthGroup'), root)
    for obj in (plinth(m, root), hangar_ends(m, root), hangar_end_details(m)):
        kit.parent(obj, base)
    keys(base, 'location', {0: Vector((0, 0, -0.75)), 16: Vector((0, 0, -0.75)), 36: Vector((0, 0, 0.01)), 40: Vector((0, 0, 0))})
    vault = kit.parent(hangar(m), base)
    kit.grow(vault, 40, 12, 0)

    # ---- cheeks, then the door swings down shut
    side = kit.parent(cheeks(m), hall)
    kit.pop(side, 34, 6)
    leaf = kit.parent(door(m), hall)
    keys(leaf, 'scale', {0: Vector((H, H, H)), 39: Vector((H, H, H)), 40: Vector((1, 1, 1))}, 'CONSTANT')
    keys(leaf, 'rotation_euler', {0: Vector((DOOR_OPEN, 0, 0)), 40: Vector((DOOR_OPEN, 0, 0)), 56: Vector((0.04, 0, 0)), 59: Vector((0, 0, 0))})

    # ---- armour, fans, stack
    x0, y0, x1, y1 = HALL
    plates = [armour(m, 'ArmourL', x0 + 0.1, -0.92, 0.56, y1 - 0.12, HALL_TOP, 0.24),
              armour(m, 'ArmourM', -0.88, x1 - 0.1, 0.56, y1 - 0.12, HALL_TOP, 0.24)]
    for k, plate in enumerate(plates):
        kit.pop(kit.parent(plate, hall), 44 + 4 * k, 8)
    right = kit.parent(armour(m, 'ArmourR', BLOCK[0] + 0.18, BLOCK[2] - 0.12, 0.48, BLOCK[3] - 0.12, BLOCK_TOP, 0.18), block)
    kit.pop(right, 50, 8)
    idle = []
    for k, (x, y) in enumerate(((-1.5, -0.12), (-0.95, 0.1))):
        housing, blades = gb.fan(f'Fan{k}', m, (x, y, HALL_TOP), 0.15)
        kit.pop(kit.parent(housing, hall), 56 + 3 * k, 6)
        idle.append((blades, lambda o, t=(1 if k == 0 else -1): gb.spin(o, t)))
    chimney = kit.parent(stack(m), block)
    kit.grow(chimney, 58, 10, 2)

    # ---- lights
    lights = []
    gb.beacon('StackTop', m, (1.62, 0.2, BLOCK_TOP + 0.44), 'red', chimney, 68, kit.flashes((0, 10), (30, 10)), lights)
    for k, s in enumerate((-1, 1)):  # amber on the portal's corners, in turn
        at = (GATE_X + s * (GATE_HALF + 0.04), HALL[1] - 0.06, GATE_TOP + 0.1)
        gb.beacon(f'Gate{k}', m, at, 'amber', hall, 64 + 2 * k, kit.flashes((15 * k, 15), (30 + 15 * k, 15)), lights)
    for k, (x, y) in enumerate(((x0 + 0.12, y0 + 0.12), (x1 - 0.12, y0 + 0.12))):
        gb.beacon(f'Corner{k}', m, (x, y, HALL_TOP), 'red', hall, 70 + k, kit.flashes((8 + 30 * k, 6)), lights)
    gb.beacon('Ready', m, (HANGAR[1] + 0.03, HANGAR[2] - 0.2, HANGAR[3] + 0.3), 'green', base, 72, kit.flashes((0, 40)), lights)

    gb.clips(idle, lights)

    # ---- Open: the door swings up (played backwards to close)
    keys(leaf, 'rotation_euler', {0: Vector((0, 0, 0)), 6: Vector((DOOR_OPEN * 0.08, 0, 0)), OPEN_END - 4: Vector((DOOR_OPEN * 1.02, 0, 0)),
                                  OPEN_END: Vector((DOOR_OPEN, 0, 0))})
    kit.to_track(leaf, 'Open')
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=5.2, target=(0, -0.1, 0.5))
