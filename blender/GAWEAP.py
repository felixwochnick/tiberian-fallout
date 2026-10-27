"""
Tiberian Fallout – GDI war factory (GAWEAP), after Tiberian Sun.

Built like the original's sprite (GAWEAP with its door GAWEAP_D, the chaser lights
GAWEAP_A and the buildup GAWEAPMK). A concrete pad with cut corners fills the
foundation (4 × 3 cells); on its left part the works:

- the assembly hall (camouflaged, sloped walls), its far left end and its back edge
  under rounded armour in the house colour, grey pipes bent out of its left end,
  fans, vents and a row of five chaser lights on its roof;
- on its front (-Y) a steep ramp in the house colour between two steel rails, beside
  it a small generator block;
- on its right (+X) the vehicle bay: a grey vault along y between two camouflaged
  arches. Its right half is the door, a curved shell that rolls up over the top of the
  vault; then the bay opens towards +X, where the pad carries a grating in the house
  colour with lane lights – the vehicles roll out to the lower right as in the original.
  Behind the vault a third armour block.

Nodes
    Exit     empty on the floor of the bay, where a finished vehicle stands; its -Y
             axis (glTF +Z) points out of the door, i.e. along +X (it is turned 90°)
    Door     the rolling door, turns about the vault's axis (its y axis)

Materials as for the barracks (see GAPILE.py): Camo_* is the baked camouflage in a
pale shade of the house colour, Remap the house colour, Lamp* emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name; no channel is
shared between them, and nothing that Idle animates hangs under a part that Build
scales to almost nothing)
    Build    one-shot, 2.8 s: the pad spreads, the hall and the vault rise out of the
             ground, the ramp's rails swing down from upright (as in the buildup), the
             ramp, the armour, the generator and the lamps appear
    Idle     loop, 2 s: the fans turn, the chaser lights run along the roof, the
             beacons blink
    Open     one-shot, 1.2 s: the door rolls up over the vault in about nine steps' worth
             of travel and stays open (the game plays it backwards to close it)

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/GAWEAP.py [-- --preview 0,40,84 <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -2 … 2 and y -1.5 … 1.5; seen in the game, -Y faces the lower left and +X the
lower right.
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
HALL = (-1.95, -0.95, -0.34, 1.45)  # the assembly hall: x0, y0, x1, y1
HALL_TOP = 0.6
WALL_SLOPE = 0.06                   # how far the walls lean in up to the roof
AX, AZ, R = 0.25, 0.12, 0.5         # the vault: its axis (x, z) and radius
VY0, VY1 = -1.12, 0.92              # the vault's ends (inside the arches)
ARCH = 0.15                         # thickness of the arches along y
RO, RI = R + 0.09, R - 0.05         # the arches' outer and inner radius
DOOR_IN, DOOR_OUT = R + 0.008, R + 0.033
DOOR_TOP = math.radians(100)        # the closed door runs from the ground up to here
DOOR_OPEN = math.radians(-85)       # its roll about the vault's axis (y) when open
RAMP_X = (-1.42, -0.64)             # the ramp's sides
RAMP_FOOT = -1.45                   # y of the ramp's foot
RAMP_TOP = (HALL[1] + 0.04, HALL_TOP + 0.005)   # (y, z) where it meets the roof edge
GRATE = (0.8, 1.68, -1.05, 0.85)    # the grating in front of the door: x0, x1, y0, y1

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'hangar': material('Hangar', srgb('#9a9ea2'), 0.45, 0.7),
        'hangar_dark': material('HangarInside', srgb('#3c3f42'), 0.8, 0.4),
        'hazard': material('Hazard', srgb('#e2a21c'), 0.6),
        'remap_dark': housecamo.shade('RemapDark', 0.6, 1.0, 0.6),
        'grate': housecamo.shade('RemapGrate', 0.45, 1.0, 0.7),
    })
    return m


def ground_angle(r):
    """Angle (from +x towards +z, about the vault's axis) where radius r meets the pad."""
    return math.asin((PAD - AZ) / r)


def band(name, mat, r0, r1, a0, a1, y0, y1, steps=24, bevel=0.0):
    """A curved shell about the vault's axis: radii r0 … r1, angles a0 … a1, along y."""
    profile = gb.arc((AX, AZ), r1, a0, a1, steps) + gb.arc((AX, AZ), r0, a1, a0, steps)
    return gb.prism(name, mat, profile, y0, y1, 'Y', bevel)


# --------------------------------------------------------------------------- the pad

def pad(m):
    """Concrete pad with cut corners, joints, cracks; the grating with lane lights."""
    parts = [gb.slab('PadSlab', m['concrete'], gb.chamfered(-1.98, -1.48, 1.98, 1.48, (0.15, 0.6, 0.6, 0.15)), PAD, inset=0.01, bevel=0.004)]
    for x in (-1.0, 0.0, 1.0):
        parts.append(box(f'PadJoint{x}', m['concrete_dark'], (0.01, 2.6, 0.003), (x, 0, PAD + 0.0015), bevel=0))
    for y in (-0.5, 0.5):
        parts.append(box(f'PadJointY{y}', m['concrete_dark'], (3.6, 0.01, 0.003), (0, y, PAD + 0.0015), bevel=0))
    # cracks running out from in front of the door
    for k, a in enumerate((-70, -40, -12, 15, 45, 75)):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        start = Vector((1.2, -0.1, PAD + 0.002)) + d * 0.6
        parts.append(beam(f'Crack{k}', m['concrete_dark'], start, start + d * (0.35 + 0.08 * (k % 3)), 0.008, 0.003))
    x0, x1, y0, y1 = GRATE
    parts.append(box('GrateBase', m['grate'], (x1 - x0, y1 - y0, 0.006), ((x0 + x1) / 2, (y0 + y1) / 2, PAD + 0.003), bevel=0))
    for k in range(13):   # slats across the way out
        y = y0 + 0.07 + k * (y1 - y0 - 0.14) / 12
        parts.append(box(f'GrateSlat{k}', m['remap_dark'], (x1 - x0 - 0.06, 0.03, 0.006), ((x0 + x1) / 2, y, PAD + 0.007), bevel=0))
    for k, y in enumerate((-0.8, -0.38, 0.04, 0.46)):  # lane lights along the way out
        parts.append(box(f'LaneLight{k}', m['lamp_white'], (0.5, 0.025, 0.006), (x0 + 0.42, y + 0.1, PAD + 0.011), bevel=0))
    for k, y in enumerate((y0 + 0.02, y1 - 0.02)):   # hazard edges
        parts.append(box(f'GrateEdge{k}', m['hazard'], (x1 - x0, 0.03, 0.008), ((x0 + x1) / 2, y, PAD + 0.006), bevel=0))
    return kit.merge('Pad', parts)


# --------------------------------------------------------------------------- the hall

def hall_body(m, root):
    x0, y0, x1, y1 = HALL
    body = gb.slab('HallBody', m['sand'], gb.chamfered(x0, y0, x1, y1, (0.12, 0.0, 0.0, 0.12)), HALL_TOP - PAD, inset=WALL_SLOPE, z0=PAD, bevel=0.012)
    return gb.camo(body, root)


def on_front(z):
    """y of the hall's front face at height z (it leans in towards the roof)."""
    return HALL[1] + WALL_SLOPE * (z - PAD) / (HALL_TOP - PAD)


def hall_roof(m):
    """Roof deck: plates, seams, a light bar along the right edge, round vents, a pipe run."""
    x0, y0, x1, y1 = HALL
    s = WALL_SLOPE
    z = HALL_TOP
    parts = [
        box('RoofHatch', m['steel'], (0.2, 0.15, 0.02), (-1.05, -0.62, z + 0.01), bevel=0.004),
        box('LightBar', m['steel'], (0.05, 1.75, 0.03), (x1 - s - 0.07, 0.16, z + 0.015), bevel=0.005),
        box('LightBarStripe', m['remap'], (0.052, 1.75, 0.008), (x1 - s - 0.07, 0.16, z + 0.026), bevel=0),
    ]
    for k in range(4):  # roof seams
        x = x0 + 0.45 + k * 0.33
        parts.append(box(f'RoofSeam{k}', m['concrete_dark'], (0.012, y1 - y0 - 0.6, 0.004), (x, 0.0, z + 0.002), bevel=0))
    for k, y in enumerate((-0.55, -0.15, 0.25, 0.65)):  # round vents with dark caps (the original's dark knobs)
        parts += [cylinder(f'VentRim{k}', m['steel'], 0.06, 0.04, (-0.68, y, z + 0.02), segments=16, bevel=0.004),
                  cylinder(f'VentCap{k}', m['dark'], 0.045, 0.03, (-0.68, y, z + 0.055), segments=16, bevel=0.006)]
    # the pipe run across the deck
    for k, y in enumerate((0.84, 0.92)):
        parts.append(cylinder(f'RoofPipe{k}', m['steel_light'], 0.022, 0.82, (-0.97, y, z + 0.045), rotation=(0, math.pi / 2, 0), segments=12))
        for j, x in enumerate((-1.3, -0.97, -0.64)):
            parts.append(box(f'PipeStand{k}{j}', m['steel'], (0.03, 0.05, 0.035), (x, y, z + 0.018), bevel=0))
    parts.append(kit.vent_block('VentA', m, -1.0, 0.45))
    parts[-1].location.z = z
    return kit.merge('HallRoof', parts)


def hall_walls(m):
    """Ribs and windows on the front face left of the ramp, the left end's pipes, ribs
    on the hall's right face above the vault."""
    x0, y0, x1, y1 = HALL
    parts = []
    for k, x in enumerate((-1.84, -1.7, -1.56)):
        parts.append(beam(f'WallRib{k}', m['steel'], Vector((x, on_front(PAD) - 0.012, PAD + 0.01)), Vector((x, on_front(HALL_TOP - 0.05) - 0.012, HALL_TOP - 0.05)), 0.03, 0.02))
    for k, x in enumerate((-1.77, -1.63)):
        parts.append(box(f'Window{k}', m['window'], (0.08, 0.012, 0.05), (x, on_front(0.42) - 0.008, 0.42), bevel=0.002))
    parts.append(box('SideDoor', m['dark'], (0.1, 0.012, 0.18), (-1.7, on_front(0.12) - 0.008, PAD + 0.09), bevel=0.003))
    parts.append(box('WallBand', m['remap'], (0.4, 0.012, 0.04), (-1.7, on_front(0.52) - 0.008, 0.52), bevel=0.003))
    # the left end: grey pipes bent out of the wall and back, near the front
    for k, (y, h) in enumerate(((-0.62, 0.2), (-0.3, 0.3))):
        xo = x0 - 0.06
        parts += [
            beam(f'LeftPipeA{k}', m['steel_light'], (x0 + 0.03, y - 0.12, h), (xo, y - 0.12, h), 0.035),
            beam(f'LeftPipeB{k}', m['steel_light'], (xo, y - 0.12, h), (xo, y + 0.12, h), 0.035),
            beam(f'LeftPipeC{k}', m['steel_light'], (xo, y + 0.12, h), (x0 + 0.03, y + 0.12, h), 0.035),
            beam(f'LeftPipeLeg{k}', m['steel'], (xo, y, PAD), (xo, y, h), 0.025),
        ]
    return kit.merge('HallWalls', parts)


def armour(m, name, x0, x1, y0, y1, z, height, grooves_along_x=True):
    """A rounded armour block in the house colour, its origin at the bottom."""
    parts = [box(name, m['remap'], (x1 - x0, y1 - y0, height), ((x0 + x1) / 2, (y0 + y1) / 2, z + height / 2), bevel=min(0.09, height * 0.4))]
    parts[0].modifiers['Bevel'].segments = 5
    parts[0].modifiers['Bevel'].angle_limit = math.radians(30)
    for k in range(3):  # grooves across
        if grooves_along_x:
            x = x0 + (k + 1) * (x1 - x0) / 4
            parts.append(box(f'{name}Groove{k}', m['remap_dark'], (0.016, y1 - y0 - 0.12, 0.01), (x, (y0 + y1) / 2, z + height + 0.001), bevel=0))
        else:
            y = y0 + (k + 1) * (y1 - y0) / 4
            parts.append(box(f'{name}Groove{k}', m['remap_dark'], (x1 - x0 - 0.12, 0.016, 0.01), ((x0 + x1) / 2, y, z + height + 0.001), bevel=0))
    parts.append(box(f'{name}Seat', m['steel'], (x1 - x0 + 0.03, y1 - y0 + 0.03, 0.025), ((x0 + x1) / 2, (y0 + y1) / 2, z + 0.0125), bevel=0.005))
    return kit.merge(name, parts, ((x0 + x1) / 2, (y0 + y1) / 2, z))


def end_plate(m):
    """The house-colour plate over the hall's sloped left end, under the armour."""
    x0, y0, x1, y1 = HALL
    z0, z1 = 0.24, HALL_TOP - 0.03
    xa = x0 - 0.006 + WALL_SLOPE * (z0 - PAD) / (HALL_TOP - PAD)
    xb = x0 - 0.006 + WALL_SLOPE * (z1 - PAD) / (HALL_TOP - PAD)
    parts = [kit.hexahedron('EndPlate', m['remap'], [
        (xa, y0 + 0.2, z0), (xa - 0.03, y0 + 0.2, z0), (xa - 0.03, y1 - 0.12, z0), (xa, y1 - 0.12, z0),
        (xb, y0 + 0.2, z1), (xb - 0.03, y0 + 0.2, z1), (xb - 0.03, y1 - 0.12, z1), (xb, y1 - 0.12, z1)], 0.008)]
    for k in range(4):
        y = y0 + 0.4 + k * 0.42
        parts.append(box(f'EndPlateRib{k}', m['remap_dark'], (0.012, 0.025, z1 - z0 - 0.04), ((xa + xb) / 2 - 0.036, y, (z0 + z1) / 2), bevel=0,
                         rotation=(0, -math.atan2(xb - xa, z1 - z0), 0)))
    return kit.merge('EndPlate', parts, ((xa + xb) / 2, 0, z0))


# --------------------------------------------------------------------------- the ramp

def ramp_wedge(m):
    """The steep ramp in the house colour against the hall's front, with ribs."""
    x0, x1 = RAMP_X
    ty, tz = RAMP_TOP
    wedge = gb.prism('RampWedge', m['remap'], [(RAMP_FOOT, PAD), (HALL[1] + 0.1, PAD), (HALL[1] + 0.1, tz), (ty, tz)], x0 + 0.03, x1 - 0.03, 'X', bevel=0.006)
    parts = [wedge]
    foot = Vector((0, RAMP_FOOT, PAD))
    top = Vector((0, ty, tz))
    d = (top - foot).normalized()
    normal = Vector((0, -d.z, d.y))
    for k in range(9):   # ribs across
        p = foot + (top - foot) * ((k + 0.6) / 9.6) + normal * 0.006
        parts.append(beam(f'RampRib{k}', m['remap_dark'], p + Vector((x0 + 0.05, 0, 0)), p + Vector((x1 - 0.05, 0, 0)), 0.03, 0.012))
    parts.append(box('RampSill', m['steel'], (x1 - x0 - 0.04, 0.05, 0.02), ((x0 + x1) / 2, RAMP_FOOT + 0.02, PAD + 0.01), bevel=0.004))
    return kit.merge('Ramp', parts, ((x0 + x1) / 2, RAMP_FOOT, PAD))


def ramp_rails(m):
    """The two steel rails and the crossbar over the ramp, origin at the ramp's foot
    (they swing about it); posts at the top."""
    x0, x1 = RAMP_X
    ty, tz = RAMP_TOP
    foot_y = RAMP_FOOT - 0.02
    parts = []
    for k, x in enumerate((x0, x1)):
        parts += [
            beam(f'Rail{k}', m['steel'], (x, foot_y, PAD + 0.02), (x, ty + 0.02, tz + 0.07), 0.035, 0.04),
            beam(f'RailPost{k}', m['steel'], (x, ty + 0.02, tz + 0.07), (x, ty + 0.06, tz + 0.2), 0.03, 0.03),
            box(f'RailFoot{k}', m['concrete_dark'], (0.08, 0.1, 0.035), (x, foot_y + 0.02, PAD + 0.0175), bevel=0.005),
        ]
    parts.append(beam('RailBar', m['steel'], (x0, ty + 0.06, tz + 0.2), (x1, ty + 0.06, tz + 0.2), 0.03, 0.03))
    parts.append(beam('RailBarStripe', m['hazard'], (x0 + 0.03, ty + 0.06, tz + 0.217), (x1 - 0.03, ty + 0.06, tz + 0.217), 0.012, 0.004))
    return kit.merge('RampRails', parts, ((x0 + x1) / 2, foot_y, PAD))


def generator(m):
    """The small red block between the ramp and the vault."""
    x0, x1, y0, y1 = -0.58, -0.4, -1.22, HALL[1] + 0.02
    parts = [box('Generator', m['remap'], (x1 - x0, y1 - y0, 0.17), ((x0 + x1) / 2, (y0 + y1) / 2, PAD + 0.085), bevel=0.02)]
    parts[0].modifiers['Bevel'].segments = 3
    for k in range(3):
        parts.append(box(f'GeneratorRib{k}', m['remap_dark'], (x1 - x0 + 0.004, 0.014, 0.12), ((x0 + x1) / 2, y0 + 0.06 + k * 0.07, PAD + 0.08), bevel=0))
    parts.append(box('GeneratorTop', m['steel'], (0.1, 0.12, 0.025), ((x0 + x1) / 2, (y0 + y1) / 2, PAD + 0.18), bevel=0.004))
    return kit.merge('Generator', parts, ((x0 + x1) / 2, (y0 + y1) / 2, PAD))


# --------------------------------------------------------------------------- the vault

def vault_shell(m):
    """The fixed left half of the vault: the shell from the top down to its back wall,
    the dark inside, the floor of the bay with guide lines and lamps under the roof."""
    parts = [
        band('VaultBack', m['hangar'], R - 0.025, R, math.radians(92), math.pi, VY0, VY1, 20, 0.004),
        box('VaultWall', m['hangar'], (0.03, VY1 - VY0, AZ - PAD + 0.01), (AX - R + 0.0125, (VY0 + VY1) / 2, (AZ + PAD) / 2), bevel=0.004),
        box('BayFloor', m['grating'], (2 * R - 0.06, VY1 - VY0, 0.008), (AX + 0.01, (VY0 + VY1) / 2, PAD + 0.004), bevel=0),
        box('BayBack', m['hangar_dark'], (2 * R - 0.08, 0.01, 0.35), (AX + 0.02, VY1 - 0.005, PAD + 0.175), bevel=0),
    ]
    # the end walls inside the arches, a small door in the front one
    r = RI + 0.012
    disc = gb.arc((AX, AZ), r, ground_angle(r), math.pi, 24) + [(AX - r, PAD)]
    parts.append(gb.prism('EndWallFront', m['hangar'], disc, VY0 - ARCH + 0.03, VY0 - 0.02, 'Y', 0.0))
    parts.append(gb.prism('EndWallBack', m['hangar'], disc, VY1 + 0.02, VY1 + ARCH - 0.03, 'Y', 0.0))
    parts.append(box('EndDoor', m['dark'], (0.16, 0.012, 0.24), (AX - 0.12, VY0 - ARCH + 0.024, PAD + 0.12), bevel=0.003))
    parts.append(box('EndDoorFrame', m['remap'], (0.2, 0.01, 0.025), (AX - 0.12, VY0 - ARCH + 0.022, PAD + 0.255), bevel=0))
    for k in range(3):
        parts.append(box(f'EndDoorSlat{k}', m['steel'], (0.14, 0.006, 0.01), (AX - 0.12, VY0 - ARCH + 0.016, PAD + 0.04 + k * 0.07), bevel=0))
    for k, y in enumerate((-0.5, 0.3)):  # guide lines across the floor towards the door
        parts.append(box(f'BayLine{k}', m['hazard'], (2 * R - 0.1, 0.025, 0.004), (AX + 0.02, y, PAD + 0.01), bevel=0))
    for k in range(3):  # ribs on the fixed half
        y = VY0 + 0.25 + k * (VY1 - VY0 - 0.5) / 2
        parts.append(band(f'VaultBackRib{k}', m['steel'], R - 0.002, R + 0.006, math.radians(93), math.pi, y - 0.015, y + 0.015, 16))
    for k, y in enumerate((-0.7, -0.1, 0.5)):   # lamps under the roof of the bay
        parts.append(box(f'BayLamp{k}', m['lamp_white'], (0.05, 0.3, 0.01), (AX - 0.12, y, AZ + R * math.sin(math.radians(105)) - 0.04), bevel=0,
                         rotation=(0, math.radians(15), 0)))
    return kit.merge('VaultShell', parts, (AX, 0, AZ))


def arches(m, root):
    """The two camouflaged arches closing the vault's ends (they stand on the pad)."""
    def profile():
        a_out, a_in = ground_angle(RO), ground_angle(RI)
        outer = gb.arc((AX, AZ), RO, a_out, math.pi, 24)
        inner = gb.arc((AX, AZ), RI, math.pi, a_in, 24)
        return outer + [(AX - RO, PAD), (AX - RI, PAD)] + inner

    p = profile()
    parts = [gb.prism('ArchFront', m['sand'], p, VY0 - ARCH, VY0, 'Y', 0.008),
             gb.prism('ArchBack', m['sand'], p, VY1, VY1 + ARCH, 'Y', 0.008)]
    return gb.camo(kit.merge('Arches', parts), root)


def arch_details(m):
    """Steel caps on the arches' outer faces, the house-colour band, a hazard step."""
    parts = []
    for name, y in (('Front', VY0 - ARCH - 0.004), ('Back', VY1 + ARCH + 0.004)):
        parts.append(band(f'ArchCap{name}', m['steel'], RO - 0.035, RO - 0.005, math.radians(20), math.radians(160), y - 0.004, y + 0.004, 16))
        parts.append(band(f'ArchBand{name}', m['remap'], RO - 0.003, RO + 0.008, math.radians(60), math.radians(120), y - 0.06 if name == 'Front' else y - 0.09,
                          y + 0.09 if name == 'Front' else y + 0.06, 10))
    parts.append(box('ArchStep', m['hazard'], (0.3, 0.06, 0.01), (AX - 0.05, VY0 - ARCH - 0.04, PAD + 0.005), bevel=0))
    return kit.merge('ArchDetails', parts)


def door(m):
    """The rolling door: the right half of the vault, a shell just outside the fixed
    one, from the pad up over the top; its origin on the vault's axis."""
    a0 = ground_angle(DOOR_IN) + 0.01
    y0, y1 = VY0 + 0.012, VY1 - 0.012
    parts = [band('DoorShell', m['hangar'], DOOR_IN, DOOR_OUT, a0, DOOR_TOP, y0, y1, 26, 0.004)]
    for k in range(6):   # ribs round the door
        y = y0 + 0.12 + k * (y1 - y0 - 0.24) / 5
        parts.append(band(f'DoorRib{k}', m['steel'], DOOR_OUT - 0.002, DOOR_OUT + 0.01, a0 + 0.02, DOOR_TOP - 0.02, y - 0.014, y + 0.014, 22))
    # a seam along the top, a hazard edge at the foot, two handles
    parts.append(band('DoorSeam', m['steel_light'], DOOR_OUT - 0.002, DOOR_OUT + 0.006, math.radians(48), math.radians(52), y0 + 0.05, y1 - 0.05, 2))
    parts.append(band('DoorFoot', m['hazard'], DOOR_OUT - 0.002, DOOR_OUT + 0.008, a0 + 0.005, a0 + 0.07, y0 + 0.04, y1 - 0.04, 2))
    for k, y in enumerate((-0.5, 0.3)):
        parts.append(box(f'DoorHandle{k}', m['steel_light'], (0.02, 0.1, 0.02), (AX + DOOR_OUT * math.cos(a0 + 0.14) + 0.012, y, AZ + DOOR_OUT * math.sin(a0 + 0.14)), bevel=0.003))
    return kit.merge('Door', parts, (AX, 0, AZ))


def back_block(m):
    """Armour in the house colour behind the vault."""
    return armour(m, 'ArmourBack', -0.28, 0.86, VY1 + ARCH + 0.04, 1.44, PAD, 0.5, grooves_along_x=True)


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

    exit_node = kit.parent(kit.empty('Exit', (AX, -0.1, PAD)), root)
    exit_node.rotation_euler = (0, 0, math.pi / 2)   # its -y looks along +x, out of the door
    exit_node.empty_display_size = 0.3

    # ---- the hall rises
    hall = kit.parent(kit.empty('HallGroup'), root)
    for obj in (hall_body(m, root), hall_roof(m), hall_walls(m)):
        kit.parent(obj, hall)
    keys(hall, 'location', {0: Vector((0, 0, -0.75)), 6: Vector((0, 0, -0.75)), 30: Vector((0, 0, 0.012)), 34: Vector((0, 0, 0))})

    # ---- the vault rises, its door closed
    vault = kit.parent(kit.empty('VaultGroup'), root)
    for obj in (vault_shell(m), arches(m, root), arch_details(m), door(m)):
        kit.parent(obj, vault)
    leaf = bpy.data.objects['Door']
    keys(vault, 'location', {0: Vector((0, 0, -0.72)), 12: Vector((0, 0, -0.72)), 36: Vector((0, 0, 0.01)), 40: Vector((0, 0, 0))})

    # ---- the ramp's rails swing down from upright, then the ramp and the generator appear
    rails = kit.parent(ramp_rails(m), root)
    upright = math.atan2(RAMP_TOP[0] - RAMP_FOOT, RAMP_TOP[1] - PAD)
    keys(rails, 'scale', {0: Vector((H, H, H)), 33: Vector((H, H, H)), 34: Vector((1, 1, 1))}, 'CONSTANT')
    keys(rails, 'rotation_euler', {0: Vector((upright, 0, 0)), 38: Vector((upright, 0, 0)), 52: Vector((-0.02, 0, 0)), 55: Vector((0, 0, 0))})
    wedge = kit.parent(ramp_wedge(m), hall)
    keys(wedge, 'scale', {0: Vector((1, 1, H)), 52: Vector((1, 1, H)), 60: Vector((1, 1, 1))})
    kit.pop(kit.parent(generator(m), root), 44, 8)

    # ---- the armour
    x0, y0, x1, y1 = HALL
    s = WALL_SLOPE
    plates = [armour(m, 'ArmourL', x0 + s + 0.01, -1.4, y0 + 0.16, 0.2, HALL_TOP, 0.22, grooves_along_x=False),
              armour(m, 'ArmourM', x0 + s + 0.01, -1.4, 0.26, y1 - s - 0.01, HALL_TOP, 0.22, grooves_along_x=False),
              armour(m, 'ArmourTop', -1.34, x1 - s - 0.2, 1.06, y1 - s - 0.01, HALL_TOP, 0.17)]
    for k, plate in enumerate(plates):
        kit.pop(kit.parent(plate, hall), 46 + 4 * k, 8)
    kit.pop(kit.parent(end_plate(m), hall), 44, 8)
    kit.pop(kit.parent(back_block(m), vault), 50, 8)

    # ---- fans (on the roof from the start; their blades turn in Idle)
    idle = []
    for k, (x, y) in enumerate(((-1.12, -0.2), (-1.12, 0.22))):
        housing, blades = gb.fan(f'Fan{k}', m, (x, y, HALL_TOP), 0.13)
        kit.parent(housing, hall)
        kit.parent(blades, hall)
        idle.append((blades, lambda o, t=(1 if k == 0 else -1): gb.spin(o, t)))

    # ---- lights: the chaser row on the light bar, beacons on the arches and corners
    lights = []
    bar_x = x1 - s - 0.07
    for k in range(5):
        y = -0.6 + k * 0.38
        gb.beacon(f'Chaser{k}', m, (bar_x, y, HALL_TOP + 0.03), 'amber', hall, 62 + k, kit.flashes((k * 12, 12)), lights)
    for k, y in enumerate((VY0 - ARCH / 2, VY1 + ARCH / 2)):
        gb.beacon(f'Arch{k}', m, (AX, y, AZ + RO), 'red', vault, 68 + k, kit.flashes((10 + 30 * k, 8)), lights)
    gb.beacon('Corner', m, (x0 + 0.12, y0 + 0.12, HALL_TOP), 'red', hall, 70, kit.flashes((25, 6), (55, 4)), lights)
    gb.beacon('Ready', m, (GRATE[1] - 0.05, GRATE[2] - 0.06, PAD), 'green', root, 72, kit.flashes((0, 40)), lights)

    gb.clips(idle, lights)

    # ---- Open: the door rolls up over the vault (played backwards to close)
    keys(leaf, 'rotation_euler', {0: Vector((0, 0, 0)), 5: Vector((0, DOOR_OPEN * 0.06, 0)), OPEN_END - 5: Vector((0, DOOR_OPEN * 1.015, 0)),
                                  OPEN_END: Vector((0, DOOR_OPEN, 0))})
    kit.to_track(leaf, 'Open')
    leaf.animation_data.nla_tracks['Open'].strips[0].extrapolation = 'NOTHING'
    leaf.rotation_euler = (0, 0, 0)   # closed at rest
    return len(kit.collection().objects)


if __name__ == '__main__' and bpy.app.background:
    gb.run(build, OUT, BLEND, scale=5.0, target=(0, -0.05, 0.4))
