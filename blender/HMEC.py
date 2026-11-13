"""
Tiberian Fallout – GDI Mammoth Mk. II (HMEC), after Tiberian Sun.

GDI's heaviest walker and by far the biggest unit: a long, tall body of slab-sided
armour boxes in desert camouflage carried high on four heavy legs, two pairs well
apart. In front sits the tall head with a lit vision slit under a brow, headlights in
its chin and a stencilled number on its flanks; the two railguns come out under it on
both sides of the chin, long rail housings with glowing blue coils in their flanks
and split muzzles. Behind the head a lower middle section with a dark band round it,
vents and a roof hatch, then the raised rear section: two round vents in the front of
its top block, the box launcher on the roof tipped up with its eight tubes behind red
caps, an equipment box with a whip antenna, house-colour bands along the flanks, tail
lights. Panel seams and rivet rows on the slabs, big hip housings under the body.
Each leg: an armoured thigh, a big knee with its cap, a column-like shin (house-colour
plate in front, a vent, a piston behind) and a broad foot pad with three claws, a heel
spur and two struts down from the shin.

Rig: empties, no armature (see walker.py): Body → hull, Turret (the head) → Cannon
(the railguns); four legs Hip → Knee → Ankle. The legs walk in a trot: the diagonal
pairs (front left with back right) step together.

Nodes the game uses: "Turret" (the head, turns about the vertical), "Cannon" (the
railguns, tipped towards the target), "Flash0"/"Flash1" (the railguns' muzzle
flashes, in turn).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle    loop, 2 s: the body breathes, the legs stand
    Walk    loop, 1.6 s (two heavy steps of each pair); the root's walkSpeed (glTF
            extras) is the ground speed in cells per second at which the feet do
            not slide
    Fire    once, 1 s: both railguns fire, their housings recoil, the muzzles flash
            blue, the body rocks back

Run headless:

    blender -b --factory-startup --python blender/HMEC.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; the walker looks along -Y (glTF +Z). The
origin is on the ground under the middle of the body.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402 – start(), finish(), main() (rest poses held in every clip)
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'HMEC.glb')
BLEND = os.path.join(HERE, 'HMEC.blend')

ANKLE_Z = 0.045
THIGH = 0.32
SHIN = 0.33
HIP_Z = ANKLE_Z + THIGH + SHIN
HIP_X = 0.3
HIPS_Y = (-0.3, 0.44)                   # the front and the back pair
WALK_FRAMES = 48
SWING = 0.22
BEND = 0.6
FIRE_FRAMES = 30
LOW = HIP_Z - 0.03                      # the body's bottom
MID = (-0.43, 0.17, 1.06)               # the middle section: front, back, roof
REAR = (0.15, 0.84, 1.13)               # the rear section: front, back, roof
VENT_TOP = 1.22                         # the rear section's front block with the round vents
HEAD = (-0.9, -0.4, 0.87, 1.27)         # the head's upper block: front, back, bottom, top
CHIN = (-0.86, 0.13, 0.69)              # the chin under it: front (top), half width, bottom
NECK = Vector((0, -0.42, LOW))          # the head's pivot (Turret)
CANNON = Vector((0, -0.62, 0.805))      # the railguns' trunnion, through the chin
RAILS_X = 0.2
MUZZLE_Y = -1.1
SCALE = 0.95                            # the whole walker is scaled by this after building

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'pod_dark': material('PodDark', srgb('#2b3036'), 0.6, 0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'cap': material('MissileCap', srgb('#a3271c'), 0.6),
        'coil': material('RailCoil', srgb('#1d3550'), 0.3, 0.6, emission=srgb('#4fb4ff'), strength=2.5),
        'flash': material('GlowRail', (0, 0, 0), 1.0, emission=srgb('#59b8ff'), strength=7, alpha=0.75),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


SEVEN = {'0': 'abcdef', '1': 'bc', '2': 'abdeg', '3': 'abcdg', '4': 'bcfg', '5': 'acdfg', '6': 'acdefg', '7': 'abc',
         '8': 'abcdefg', '9': 'abcdfg'}
# where a segment sits in its digit (across, up; the digit's half width and height) and
# whether it lies across
SEGMENT = {'a': (0, 0.5, True), 'g': (0, 0, True), 'd': (0, -0.5, True), 'b': (0.5, 0.25, False), 'c': (0.5, -0.25, False),
           'e': (-0.5, -0.25, False), 'f': (-0.5, 0.25, False)}


def number(name, mat, text, centre, height, s):
    """A stencilled number on a flank (facing s·x): seven-segment digits of thin
    plates, `height` tall, reading from the front on the right flank and from the back
    on the left one (as seen from outside)."""
    centre = Vector(centre)
    across = Vector((0, s, 0))
    width, stroke = height * 0.55, height * 0.17
    parts = []
    for k, char in enumerate(text):
        middle = centre + across * ((k - (len(text) - 1) / 2) * (width + height * 0.3))
        for seg in SEVEN[char]:
            u, v, lying = SEGMENT[seg]
            at = middle + across * (u * (width - stroke)) + Vector((0, 0, v * (height - stroke)))
            size = (0.006, width, stroke) if lying else (0.006, stroke, height / 2)
            parts.append(box(f'{name}{k}{seg}', mat, size, at, bevel=0))
    return parts


def roof_vent(name, m, centre, width, length, slats=5):
    """A framed vent lying on a roof: slats across it (x), dark between them."""
    centre = Vector(centre)
    parts = [box(f'{name}Frame', m['steel'], (width + 0.012, length + 0.012, 0.008), centre, bevel=0.002),
             box(f'{name}Hole', m['dark'], (width, length, 0.01), centre, bevel=0)]
    for k in range(slats):
        y = -length / 2 + (k + 0.5) * length / slats
        parts.append(box(f'{name}Slat{k}', m['steel'], (width, length / slats * 0.45, 0.012), centre + Vector((0, y, 0)), bevel=0))
    return parts


def round_vent(name, m, centre, radius, facing_y):
    """A round vent in a face looking along ±y: a steel rim, a dark hole, a cross of bars."""
    centre = Vector(centre)
    turn = (math.pi / 2, 0, 0)
    out = Vector((0, facing_y, 0))
    parts = [cylinder(f'{name}Rim', m['steel'], radius, 0.02, centre, rotation=turn, segments=16, bevel=0.003),
             cylinder(f'{name}Hole', m['dark'], radius * 0.78, 0.024, centre, rotation=turn, segments=16, bevel=0),
             cylinder(f'{name}Hub', m['steel_light'], radius * 0.22, 0.03, centre, rotation=turn, segments=10, bevel=0)]
    for k in range(3):
        a = math.pi * k / 3
        d = Vector((math.cos(a), 0, math.sin(a))) * radius * 0.78
        parts.append(beam(f'{name}Bar{k}', m['steel_light'], centre - d + out * 0.011, centre + d + out * 0.011, 0.012, 0.006))
    return parts


# --------------------------------------------------------------------------- body

def flank(z, rear=False):
    """The body's flank (x) at height z: the slabs lean in a little towards the roof."""
    top = REAR[2] if rear else MID[2]
    half = 0.3 if rear else 0.285
    return half - (z - LOW) / (top - LOW) * 0.015


def body_shell(m, root):
    """The middle and the rear section, the vent block between them (camouflaged)."""
    f, b, top = MID
    rf, rb, rtop = REAR
    return camo(kit.merge('Hull', [
        kit.hexahedron('Middle', m['sand'], (
            (-0.285, f, LOW), (0.285, f, LOW), (0.285, b, LOW), (-0.285, b, LOW),
            (-0.27, f + 0.02, top), (0.27, f + 0.02, top), (0.27, b, top), (-0.27, b, top)), bevel=0.016),
        kit.hexahedron('Rear', m['sand'], (
            (-0.3, rf, LOW), (0.3, rf, LOW), (0.3, rb - 0.05, LOW), (-0.3, rb - 0.05, LOW),
            (-0.285, rf, rtop), (0.285, rf, rtop), (0.285, rb, rtop), (-0.285, rb, rtop)), bevel=0.018),
        kit.hexahedron('VentBlock', m['sand'], (
            (-0.25, rf - 0.01, top - 0.06), (0.25, rf - 0.01, top - 0.06), (0.25, rf + 0.24, top - 0.06), (-0.25, rf + 0.24, top - 0.06),
            (-0.24, rf + 0.01, VENT_TOP), (0.24, rf + 0.01, VENT_TOP), (0.24, rf + 0.24, VENT_TOP), (-0.24, rf + 0.24, VENT_TOP)), bevel=0.014),
        # roof caps, a little wider than the leaning flanks under them
        kit.hexahedron('MiddleCap', m['sand'], (
            (-0.283, f + 0.03, top - 0.025), (0.283, f + 0.03, top - 0.025), (0.283, b, top - 0.025), (-0.283, b, top - 0.025),
            (-0.278, f + 0.04, top + 0.012), (0.278, f + 0.04, top + 0.012), (0.278, b, top + 0.012), (-0.278, b, top + 0.012)), bevel=0.008),
        kit.hexahedron('RearCap', m['sand'], (
            (-0.3, rf + 0.22, rtop - 0.025), (0.3, rf + 0.22, rtop - 0.025), (0.3, rb + 0.012, rtop - 0.025), (-0.3, rb + 0.012, rtop - 0.025),
            (-0.295, rf + 0.23, rtop + 0.012), (0.295, rf + 0.23, rtop + 0.012), (0.295, rb + 0.008, rtop + 0.012), (-0.295, rb + 0.008, rtop + 0.012)),
            bevel=0.008),
        # a low spine along the middle's roof, from the head to the vent block
        kit.hexahedron('Spine', m['sand'], (
            (-0.1, f + 0.06, top - 0.02), (0.1, f + 0.06, top - 0.02), (0.1, rf, top - 0.02), (-0.1, rf, top - 0.02),
            (-0.085, f + 0.09, top + 0.04), (0.085, f + 0.09, top + 0.04), (0.085, rf, top + 0.04), (-0.085, rf, top + 0.04)), bevel=0.01),
    ]), root)


def body_details(m):
    f, b, top = MID
    rf, rb, rtop = REAR
    parts = [
        box('Belly', m['pod_dark'], (0.46, rb - f - 0.12, 0.05), (0, (f + rb) / 2, LOW - 0.012), bevel=0.012),
        # the dark band round the middle section
        box('Band', m['steel'], (0.6, 0.07, top - LOW + 0.03), (0, f + 0.14, (top + LOW) / 2), bevel=0.008),
        box('BandTop', m['steel'], (0.24, 0.07, 0.03), (0, f + 0.14, top + 0.045), bevel=0.006),
        # roof of the middle: vents in the spine, a hatch
        *roof_vent('SpineVent', m, (0, -0.02, top + 0.042), 0.12, 0.2),
        box('MidHatch', m['steel'], (0.13, 0.13, 0.014), (0, f + 0.3, top + 0.045), bevel=0.004),
        # the vent block: two round vents in its front, a hatch on top
        *round_vent('VentL', m, (-0.12, rf - 0.012, (top + VENT_TOP) / 2 + 0.01), 0.055, -1),
        *round_vent('VentR', m, (0.12, rf - 0.012, (top + VENT_TOP) / 2 + 0.01), 0.055, -1),
        box('VentBlockPlate', m['sand_light'], (0.4, 0.16, 0.012), (0, rf + 0.13, VENT_TOP + 0.004), bevel=0.004),
        *detail.rivets('VentBlockRivets', m['steel_light'], (-0.18, rf + 0.13, VENT_TOP + 0.012), (0.18, rf + 0.13, VENT_TOP + 0.012), 7, axis='Z'),
        # the rear roof: the box launcher, an equipment box with the antenna, a hatch
        box('RearHatch', m['steel'], (0.14, 0.12, 0.014), (0.15, rb - 0.12, rtop + 0.018), bevel=0.004),
        box('AntennaBox', m['olive'], (0.1, 0.12, 0.08), (0.2, rf + 0.42, rtop + 0.04), bevel=0.008),
        *detail.grille('AntennaBoxVent', m['steel'], m['dark'], (0.2, rf + 0.359, rtop + 0.04), 0.07, 0.05, 'Y', 3, 0.006),
        beam('Antenna', m['steel'], (0.22, rf + 0.44, rtop + 0.08), (0.235, rf + 0.49, rtop + 0.4), 0.008),
        beam('AntennaShort', m['steel'], (0.17, rf + 0.46, rtop + 0.08), (0.17, rf + 0.48, rtop + 0.22), 0.006),
        # the tail: plate, vent, lights
        box('TailPlate', m['pod_dark'], (0.44, 0.02, 0.18), (0, rb - 0.02, LOW + 0.2), bevel=0.004, rotation=(math.radians(-6), 0, 0)),
        *detail.grille('TailVent', m['steel'], m['dark'], (0, rb - 0.006, LOW + 0.2), 0.28, 0.1, 'Y', 5, 0.008),
        *detail.lamp('TailLightL', m['dark'], m['lamp_red'], (-0.22, rb - 0.012, LOW + 0.3), (0, 1, 0), 0.014),
        *detail.lamp('TailLightR', m['dark'], m['lamp_red'], (0.22, rb - 0.012, LOW + 0.3), (0, 1, 0), 0.014),
        *detail.rivets('TailRivets', m['steel_light'], (-0.24, rb - 0.001, rtop - 0.05), (0.24, rb - 0.001, rtop - 0.05), 9, axis='Y'),
    ]
    parts += launcher(m, Vector((-0.08, rf + 0.42, rtop)))
    for s in (-1, 1):
        mz = (LOW + top) / 2
        parts += [
            # the middle's flank: a vent, seams, a row of rivets under the roof
            *detail.grille(f'MidVent{s}', m['steel'], m['dark'], (s * (flank(mz) + 0.004), -0.02, mz + 0.03), 0.18, 0.1, 'X', 5, 0.008),
            *detail.seam(f'MidSeam{s}', m['seam'], (s * (flank(LOW + 0.2) + 0.002), f + 0.24, LOW + 0.2), (s * (flank(LOW + 0.2) + 0.002), b - 0.03, LOW + 0.2)),
            *detail.seam(f'MidSeamV{s}', m['seam'], (s * (flank(LOW) + 0.002), 0.1, LOW + 0.03), (s * (flank(top) + 0.002), 0.1, top - 0.02)),
            *detail.rivets(f'MidRivets{s}', m['steel_light'], (s * (flank(top - 0.05) + 0.002), f + 0.22, top - 0.05),
                           (s * (flank(top - 0.05) + 0.002), b - 0.04, top - 0.05), 8, axis='X'),
            # the rear section's flank: house-colour band, a vent, a hatch, seams, rivets
            box(f'RearBand{s}', m['remap'], (0.012, rb - rf - 0.12, 0.045), (s * (flank(LOW + 0.1, True) + 0.004), (rf + rb) / 2 - 0.02, LOW + 0.1),
                bevel=0.003),
            *detail.grille(f'RearVent{s}', m['steel'], m['dark'], (s * (flank(LOW + 0.27, True) + 0.004), rb - 0.18, LOW + 0.27), 0.16, 0.1, 'X', 5,
                           0.008),
            box(f'RearDoor{s}', m['sand_light'], (0.012, 0.16, 0.2), (s * (flank(LOW + 0.26, True) + 0.004), rf + 0.2, LOW + 0.26), bevel=0.004),
            box(f'RearDoorHandle{s}', m['steel'], (0.014, 0.05, 0.012), (s * (flank(LOW + 0.26, True) + 0.008), rf + 0.25, LOW + 0.26), bevel=0.002),
            *detail.seam(f'RearSeam{s}', m['seam'], (s * (flank(LOW + 0.4, True) + 0.002), rf + 0.02, LOW + 0.4),
                         (s * (flank(LOW + 0.4, True) + 0.002), rb - 0.04, LOW + 0.4)),
            *detail.seam(f'RearSeamV{s}', m['seam'], (s * (flank(LOW, True) + 0.002), rf + 0.33, LOW + 0.03),
                         (s * (flank(rtop, True) + 0.002), rf + 0.33, rtop - 0.02)),
            *detail.rivets(f'RearRivets{s}', m['steel_light'], (s * (flank(rtop - 0.05, True) + 0.002), rf + 0.04, rtop - 0.05),
                           (s * (flank(rtop - 0.05, True) + 0.002), rb - 0.04, rtop - 0.05), 10, axis='X'),
            *detail.rivets(f'RoofRivets{s}', m['steel_light'], (s * 0.25, f + 0.2, top + 0.014), (s * 0.25, b - 0.04, top + 0.014), 7, axis='Z'),
            *detail.rivets(f'RearRoofRivets{s}', m['steel_light'], (s * 0.265, rf + 0.28, rtop + 0.014), (s * 0.265, rb - 0.03, rtop + 0.014), 8, axis='Z'),
            # the hips' housings under the body, skirt plates low on the flanks
            *[box(f'HipHousing{s}{k}', m['steel'], (0.2, 0.28, 0.12), (s * HIP_X, y, LOW + 0.01), bevel=0.016) for k, y in enumerate(HIPS_Y)],
            *[box(f'HipCap{s}{k}', m['pod_dark'], (0.02, 0.16, 0.08), (s * (HIP_X + 0.1), y, LOW + 0.01), bevel=0.004) for k, y in enumerate(HIPS_Y)],
            *[box(f'Skirt{s}{k}', m['pod_dark'], (0.014, 0.1, 0.07), (s * (flank(LOW) + 0.005), y, LOW + 0.02), bevel=0.003)
              for k, y in enumerate((f + 0.04, b + 0.02, rb - 0.12))],
        ]
    return parts


def launcher(m, at):
    """The box launcher on the rear roof, tipped up: eight tubes in two rows behind red
    caps; `at` is the middle of its foot."""
    tilt = math.radians(-16)                # its front up
    turn = (tilt, 0, 0)
    size = Vector((0.26, 0.22, 0.14))

    def place(p):  # a point in the launcher's own space (origin at its foot) to the model
        p = Vector(p)
        return at + Vector((p.x, p.y * math.cos(tilt) - p.z * math.sin(tilt), p.y * math.sin(tilt) + p.z * math.cos(tilt))) + Vector((0, 0, 0.05))

    parts = [
        box('LauncherFoot', m['steel'], (0.14, 0.14, 0.07), at + Vector((0, 0.02, 0.035)), bevel=0.008),
        box('Launcher', m['olive'], tuple(size), place((0, 0, size.z / 2)), bevel=0.012, rotation=turn),
        box('LauncherBand', m['remap'], (size.x + 0.008, 0.04, size.z + 0.008), place((0, 0.05, size.z / 2)), bevel=0.003, rotation=turn),
        box('LauncherFace', m['pod_dark'], (size.x - 0.02, 0.012, size.z - 0.02), place((0, -size.y / 2 - 0.004, size.z / 2)), bevel=0.003, rotation=turn),
    ]
    for k in range(8):
        x, z = -0.09 + 0.06 * (k % 4), size.z / 2 + (0.032 if k // 4 else -0.032)
        parts.append(cylinder(f'LauncherCap{k}', m['cap'], 0.022, 0.016, place((x, -size.y / 2 - 0.012, z)), rotation=(math.pi / 2 + tilt, 0, 0),
                              segments=10, bevel=0.003))
    return parts


# --------------------------------------------------------------------------- head and guns

def head(m, root):
    """The head on the Turret: the tall upper block, the chin, its fittings; returns
    (shell, details), origins on the neck."""
    f, b, z0, z1 = HEAD
    cf, ch, cz = CHIN
    shell = camo(kit.merge('Head', [
        kit.hexahedron('HeadBlock', m['sand'], (
            (-0.25, f, z0), (0.25, f, z0), (0.25, b, z0), (-0.25, b, z0),
            (-0.235, f + 0.06, z1), (0.235, f + 0.06, z1), (0.235, b - 0.02, z1), (-0.235, b - 0.02, z1)), bevel=0.018),
        kit.hexahedron('Chin', m['sand'], (
            (-ch, cf + 0.03, cz), (ch, cf + 0.03, cz), (ch, b, cz), (-ch, b, cz),
            (-ch, cf, z0 + 0.01), (ch, cf, z0 + 0.01), (ch, b, z0 + 0.01), (-ch, b, z0 + 0.01)), bevel=0.012),
    ], NECK), root)
    slope = math.atan2(0.06, z1 - z0)        # the front face leans back

    def front(z):  # just before the front face at height z
        return f + (z - z0) / (z1 - z0) * 0.06 - 0.003

    def chin(z):
        return cf + (z0 + 0.01 - z) / (z0 + 0.01 - cz) * 0.03 - 0.003

    def side(z):  # the flank (x) at height z
        return 0.25 - (z - z0) / (z1 - z0) * 0.015

    slit, band = z1 - 0.12, z0 + 0.08
    parts = [
        # vision slit under a brow, a remap band across the front
        box('Slit', m['window'], (0.34, 0.02, 0.045), (0, front(slit), slit), bevel=0.004, rotation=(-slope, 0, 0)),
        box('Brow', m['pod_dark'], (0.42, 0.05, 0.028), (0, front(slit + 0.045) - 0.012, slit + 0.045), bevel=0.005, rotation=(-slope, 0, 0)),
        box('HeadBand', m['remap'], (0.47, 0.014, 0.045), (0, front(band), band), bevel=0.003, rotation=(-slope, 0, 0)),
        *detail.rivets('HeadFrontRivets', m['steel_light'], (-0.2, front(band + 0.07), band + 0.07), (0.2, front(band + 0.07), band + 0.07), 7, axis='Y'),
        *detail.seam('HeadFrontSeam', m['seam'], (0, front(band + 0.03), band + 0.03), (0, front(slit - 0.04), slit - 0.04)),
        # chin: headlights, a grille
        *detail.grille('ChinVent', m['steel'], m['dark'], (0, chin(cz + 0.05), cz + 0.05), 0.15, 0.05, 'Y', 3, 0.008),
        box('ChinPlate', m['pod_dark'], (0.2, 0.08, 0.02), (0, cf + 0.06, cz + 0.005), bevel=0.004),
        # roof: a cupola with its hatch, a periscope, a plate, rivets
        cylinder('Cupola', m['steel'], 0.06, 0.035, (0.08, b - 0.15, z1 + 0.015), segments=16),
        cylinder('CupolaHatch', m['steel_light'], 0.045, 0.014, (0.08, b - 0.15, z1 + 0.036), segments=16),
        box('Periscope', m['pod_dark'], (0.06, 0.03, 0.03), (-0.1, f + 0.16, z1 + 0.014), bevel=0.004),
        box('PeriscopeGlass', m['window'], (0.045, 0.006, 0.016), (-0.1, f + 0.144, z1 + 0.016), bevel=0),
        box('HeadRoofPlate', m['sand_light'], (0.16, 0.2, 0.01), (-0.08, b - 0.16, z1 + 0.003), bevel=0.003),
        *[r for s in (-1, 1) for r in detail.rivets(f'HeadRoofRivets{s}', m['steel_light'], (s * 0.205, f + 0.1, z1 + 0.002), (s * 0.205, b - 0.06, z1 + 0.002),
                                                    6, axis='Z')],
    ]
    for s in (-1, 1):
        lamp_z, number_z, vent_z, rivet_z = cz + 0.12, z1 - 0.19, z0 + 0.15, z0 + 0.075
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.075, chin(lamp_z) - 0.004, lamp_z), (0, -1, 0.15), 0.016),
            # the flanks: the number, a vent, seams, a house-colour band low down
            *number(f'Number{s}', m['seam'], '02', (s * (side(number_z) + 0.002), -0.66, number_z), 0.12, s),
            *detail.grille(f'HeadVent{s}', m['steel'], m['dark'], (s * (side(vent_z) + 0.004), b - 0.1, vent_z), 0.1, 0.1, 'X', 5, 0.008),
            box(f'HeadSideBand{s}', m['remap'], (0.012, b - f - 0.05, 0.035), (s * (side(z0 + 0.035) + 0.003), (f + b) / 2, z0 + 0.035), bevel=0.003),
            *detail.seam(f'HeadSeam{s}', m['seam'], (s * (side(z0) + 0.002), f + 0.1, z0 + 0.06), (s * (side(z1) + 0.002), f + 0.1, z1 - 0.02)),
            *detail.seam(f'HeadSeamTop{s}', m['seam'], (s * (side(z1 - 0.05) + 0.002), f + 0.1, z1 - 0.05), (s * (side(z1 - 0.05) + 0.002), b - 0.03, z1 - 0.05)),
            *detail.rivets(f'HeadRivets{s}', m['steel_light'], (s * (side(rivet_z) + 0.002), f + 0.12, rivet_z), (s * (side(rivet_z) + 0.002), b - 0.04, rivet_z),
                           6, axis='X'),
            # the rails' sleeves under the head, beside the chin
            box(f'RailSleeve{s}', m['pod_dark'], (0.14, 0.12, 0.05), (s * RAILS_X, -0.55, z0 - 0.02), bevel=0.008),
        ]
    return shell, kit.merge('HeadDetails', parts, NECK)


def railgun(m, root, s, pivot):
    """One railgun on the Cannon: a long camouflaged housing, the rails' slot along its
    outer flank with the glowing coils, a split muzzle; its group "Rail…" has its origin
    on the trunnion axis (it recoils along +Y)."""
    x = s * RAILS_X
    at = Vector((x, CANNON.y, CANNON.z))
    tip = Vector((x, MUZZLE_Y, CANNON.z))
    back = CANNON.y + 0.14
    group = kit.parent(walker.joint(f'Rail{"R" if s > 0 else "L"}', None, at), pivot)
    w, h = 0.06, 0.06
    shell = camo(kit.merge(f'RailHousing{s}', [kit.hexahedron(f'RailHousing{s}', m['sand'], (
        (x - w, tip.y + 0.07, at.z - h), (x + w, tip.y + 0.07, at.z - h), (x + w, back, at.z - h), (x - w, back, at.z - h),
        (x - w + 0.008, tip.y + 0.09, at.z + h), (x + w - 0.008, tip.y + 0.09, at.z + h), (x + w - 0.008, back - 0.02, at.z + h),
        (x - w + 0.008, back - 0.02, at.z + h)), bevel=0.01)], at), root)
    kit.parent(shell, group)
    length = back - tip.y
    parts = [
        box(f'RailBand{s}', m['remap'], (2 * w + 0.006, 0.04, 2 * h + 0.006), Vector((x, CANNON.y - 0.12, at.z)), bevel=0.004),
        box(f'RailBreech{s}', m['pod_dark'], (2 * w - 0.01, 0.1, 2 * h - 0.01), Vector((x, back + 0.03, at.z)), bevel=0.01),
        box(f'RailTop{s}', m['sand_light'], (0.06, length * 0.5, 0.008), Vector((x, tip.y + 0.12 + length * 0.25, at.z + h + 0.002)), bevel=0.002),
        # the muzzle: a dark block, the two rail ends ahead of it with the bore between
        box(f'RailMuzzle{s}', m['pod_dark'], (2 * w + 0.008, 0.06, 2 * h + 0.008), tip + Vector((0, 0.08, 0)), bevel=0.01),
        *[box(f'RailEnd{s}{t}', m['steel_light'], (0.07, 0.08, 0.018), tip + Vector((0, 0.03, t * 0.03)), bevel=0.003) for t in (-1, 1)],
        box(f'RailBore{s}', m['coil'], (0.03, 0.06, 0.03), tip + Vector((0, 0.035, 0)), bevel=0),
        *detail.rivets(f'RailRivets{s}', m['steel_light'], (x, tip.y + 0.16, at.z + h + 0.004), (x, back - 0.06, at.z + h + 0.004), 6, axis='Z'),
    ]
    # the slot along the outer flank with its coils, glowing blue
    o = x + s * (w + 0.001)
    parts.append(box(f'RailSlot{s}', m['dark'], (0.006, length - 0.24, 0.05), Vector((o, (tip.y + back) / 2 - 0.01, at.z)), bevel=0))
    for k in range(7):
        y = tip.y + 0.14 + k * (length - 0.32) / 6
        parts.append(box(f'Coil{s}{k}', m['coil'], (0.01, 0.03, 0.04), Vector((o + s * 0.002, y, at.z)), bevel=0.002))
    kit.parent(kit.merge(f'RailDetails{s}', parts, at), group)
    return group


def guns(m, root, body):
    """Turret → head, Cannon → the two railguns and their flashes; returns (turret,
    rails, flashes)."""
    turret = kit.parent(kit.empty('Turret', NECK), body)
    for obj in head(m, root):
        kit.parent(obj, turret)
    pivot = kit.parent(walker.joint('Cannon', None, CANNON), turret)
    kit.parent(kit.merge('Trunnion', [cylinder('Trunnion', m['steel'], 0.04, 2 * RAILS_X, CANNON, rotation=(0, math.pi / 2, 0), segments=14)],
                         CANNON), pivot)
    rails, flashes = [], []
    for k, s in enumerate((-1, 1)):
        rails.append(railgun(m, root, s, pivot))
        muzzle = Vector((s * RAILS_X, MUZZLE_Y - 0.05, CANNON.z))
        flash = kit.merge(f'Flash{k}', [sphere(f'Flash{k}_{j}', m['flash'], 0.06 - 0.014 * j, muzzle - Vector((0, 0.06 * j, 0)), 10)
                                        for j in range(3)], muzzle)
        flash.scale = (kit.HIDDEN,) * 3
        flashes.append(kit.parent(flash, pivot))
    return turret, rails, flashes


# --------------------------------------------------------------------------- legs

def leg(m, root, name, hip, body):
    """One heavy leg on its joints, centred under the hip; returns the walker.Leg."""
    joints = walker.Leg(name, body, hip, THIGH, SHIN)
    knee, ankle = hip - Vector((0, 0, THIGH)), hip - Vector((0, 0, THIGH + SHIN))
    x, y = hip.x, hip.y
    s = 1 if x > 0 else -1
    # the thigh: an armoured block, broad at the hip
    thigh = camo(kit.merge(f'{name}Thigh', [kit.hexahedron(f'{name}Thigh', m['sand'], (
        (x - 0.075, y - 0.09, knee.z + 0.03), (x + 0.075, y - 0.09, knee.z + 0.03), (x + 0.075, y + 0.08, knee.z + 0.03), (x - 0.075, y + 0.08, knee.z + 0.03),
        (x - 0.09, y - 0.13, hip.z - 0.02), (x + 0.09, y - 0.13, hip.z - 0.02), (x + 0.09, y + 0.12, hip.z - 0.02), (x - 0.09, y + 0.12, hip.z - 0.02)),
        bevel=0.016)], hip), root)
    kit.parent(thigh, joints.hip)
    ox = x + s * 0.085
    kit.parent(kit.merge(f'{name}ThighDetails', [
        cylinder(f'{name}HipJoint', m['steel'], 0.07, 0.22, hip - Vector((0, 0, 0.01)), rotation=(0, math.pi / 2, 0), segments=16),
        box(f'{name}ThighPlate', m['sand_light'], (0.014, 0.15, 0.16), (ox, y - 0.01, hip.z - 0.13), bevel=0.004),
        *detail.rivets(f'{name}ThighRivets', m['steel_light'], (ox + s * 0.007, y - 0.06, hip.z - 0.07), (ox + s * 0.007, y + 0.04, hip.z - 0.07), 4, axis='X'),
        *detail.seam(f'{name}ThighSeam', m['seam'], (x - 0.08, y - 0.12, hip.z - 0.08), (x + 0.08, y - 0.12, hip.z - 0.08)),
        beam(f'{name}ThighPiston', m['steel_light'], hip + Vector((-s * 0.04, 0.09, -0.04)), knee + Vector((-s * 0.04, 0.075, 0.05)), 0.022),
    ], hip), joints.hip)
    # the shin: a column, wider at its foot
    shin = camo(kit.merge(f'{name}Shin', [kit.hexahedron(f'{name}Shin', m['sand'], (
        (x - 0.09, y - 0.105, ankle.z + 0.06), (x + 0.09, y - 0.105, ankle.z + 0.06), (x + 0.09, y + 0.095, ankle.z + 0.06), (x - 0.09, y + 0.095, ankle.z + 0.06),
        (x - 0.072, y - 0.085, knee.z - 0.02), (x + 0.072, y - 0.085, knee.z - 0.02), (x + 0.072, y + 0.075, knee.z - 0.02), (x - 0.072, y + 0.075, knee.z - 0.02)),
        bevel=0.016)], knee), root)
    kit.parent(shin, joints.knee)
    kit.parent(kit.merge(f'{name}Knee', [
        cylinder(f'{name}KneeJoint', m['steel'], 0.066, 0.2, knee, rotation=(0, math.pi / 2, 0), segments=16),
        box(f'{name}KneeCap', m['sand_light'], (0.17, 0.07, 0.14), knee + Vector((0, -0.085, 0.005)), bevel=0.018),
        box(f'{name}ShinPlate', m['remap'], (0.12, 0.02, 0.1), knee + Vector((0, -0.098, -0.14)), bevel=0.005, rotation=(math.radians(-3), 0, 0)),
        *detail.grille(f'{name}ShinVent', m['steel'], m['dark'], (x + s * 0.084, y, knee.z - 0.14), 0.09, 0.08, 'X', 4, 0.008),
        beam(f'{name}Piston', m['steel_light'], knee + Vector((0, 0.08, -0.03)), ankle + Vector((0, 0.097, 0.08)), 0.024),
        beam(f'{name}PistonSleeve', m['steel'], knee + Vector((0, 0.078, -0.03)), knee + Vector((0, 0.082, -0.13)), 0.036),
        *detail.rivets(f'{name}ShinRivets', m['steel_light'], (x + s * 0.09, y - 0.07, ankle.z + 0.09), (x + s * 0.09, y + 0.06, ankle.z + 0.09), 4, axis='X'),
        box(f'{name}AnkleGuard', m['steel'], (0.19, 0.04, 0.06), ankle + Vector((0, -0.11, 0.085)), bevel=0.006),
    ], knee), joints.knee)
    # the foot: a broad pad, three claws in front, a heel spur, two struts from the shin
    foot = [
        box(f'{name}Pad', m['pod_dark'], (0.22, 0.3, 0.05), ankle + Vector((0, -0.03, -0.02)), bevel=0.012),
        box(f'{name}PadTop', m['steel'], (0.17, 0.22, 0.025), ankle + Vector((0, -0.03, 0.012)), bevel=0.006),
        cylinder(f'{name}AnkleJoint', m['steel'], 0.04, 0.17, ankle + Vector((0, 0, 0.03)), rotation=(0, math.pi / 2, 0), segments=12),
        box(f'{name}Heel', m['steel'], (0.08, 0.08, 0.04), ankle + Vector((0, 0.13, -0.025)), bevel=0.008),
        box(f'{name}Spur', m['dark'], (0.05, 0.05, 0.025), ankle + Vector((0, 0.175, -0.032)), bevel=0.005, rotation=(math.radians(12), 0, 0)),
    ]
    for t in (-1, 0, 1):
        foot += [box(f'{name}Toe{t}', m['steel'], (0.05, 0.1, 0.04), ankle + Vector((t * 0.065, -0.2, -0.025)), bevel=0.008, rotation=(0, 0, t * 0.22)),
                 box(f'{name}Claw{t}', m['dark'], (0.036, 0.05, 0.024), ankle + Vector((t * 0.08, -0.26, -0.033)), bevel=0.005,
                     rotation=(math.radians(-14), 0, t * 0.22))]
    for t in (-1, 1):
        foot += [beam(f'{name}Strut{t}F', m['steel_light'], ankle + Vector((t * 0.07, -0.05, 0.09)), ankle + Vector((t * 0.095, -0.14, 0.0)), 0.016),
                 beam(f'{name}Strut{t}B', m['steel_light'], ankle + Vector((t * 0.07, 0.05, 0.09)), ankle + Vector((t * 0.095, 0.1, 0.0)), 0.016)]
    kit.parent(kit.merge(f'{name}Foot', foot, ankle), joints.ankle)
    return joints


# --------------------------------------------------------------------------- model

def fire(body, rails, flashes):
    """The Fire clip: both railguns fire, recoil and run out again, the body rocks back."""
    kick = Vector((0, 0.07, 0))
    for k, rail in enumerate(rails):
        rest = rail.location.copy()
        kit.keys(rail, 'location', {0: rest, 2 + k: rest + kick, 6 + k: rest + kick, 22: rest, FIRE_FRAMES: rest})
        kit.to_track(rail, 'Fire')
        rail.location = rest
    hidden = Vector((kit.HIDDEN,) * 3)
    for k, flash in enumerate(flashes):
        kit.keys(flash, 'scale', {0: hidden if k else Vector((1, 1, 1)), k: Vector((1, 1, 1)), 2 + k: Vector((1.3, 1.6, 1.3)), 4 + k: hidden,
                                  FIRE_FRAMES: hidden}, 'CONSTANT')
        kit.to_track(flash, 'Fire')
    level = Vector((0, 0, 0))
    kit.keys(body, 'rotation_euler', {0: level, 3: Vector((math.radians(-1.0), 0, 0)), 10: Vector((math.radians(0.25), 0, 0)), 16: level,
                                      FIRE_FRAMES: level})
    kit.keys(body, 'location', {0: level, FIRE_FRAMES: level}, 'CONSTANT')
    kit.to_track(body, 'Fire')


def build():
    root, body = nod.start('GDIMammoth2', 'Mammoth2', 0.0)
    m = materials()
    kit.parent(body_shell(m, root), body)
    kit.parent(kit.merge('HullDetails', body_details(m)), body)
    turret, rails, flashes = guns(m, root, body)
    # the trot: front left and back right step together, then front right and back left
    front, back = HIPS_Y
    legs = [leg(m, root, name, Vector((sx * HIP_X, y, HIP_Z)), body)
            for name, sx, y in (('LegFL', -1, front), ('LegFR', 1, front), ('LegBR', 1, back), ('LegBL', -1, back))]
    kit.bake_camo(256)
    speed = walker.walk(legs, body, [], WALK_FRAMES, SWING, BEND, hidden=flashes)
    walker.idle(body, [], legs, sway=0.006, hidden=flashes)
    fire(body, rails, flashes)
    walker.rest(body, [body, *[j for g in legs for j in (g.hip, g.knee, g.ankle)]])
    for flash in flashes:
        flash.scale = (kit.HIDDEN,) * 3
    root['walkSpeed'] = round(speed, 4)
    nod.finish(root, SCALE)
    print('walk speed', root['walkSpeed'], 'cells/s', flush=True)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [0, 12], 'Fire': [2]}, scale=2.6, target=(0, -0.1, 0.65))
