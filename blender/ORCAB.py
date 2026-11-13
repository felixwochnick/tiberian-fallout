"""
Tiberian Fallout – GDI Orca bomber (ORCAB), after Tiberian Sun.

The heavy brother of the Orca fighter (ORCA.py), bigger and bulkier, a twin-boom
bomber: a broad, deep fuselage with a blunt nose, a short faceted glass canopy (light
frame) over it, two red chin lamps and a sensor in the nose; a raised spine with an
intake grille and a hatch. Two big boxy pods flank the fuselage, slatted intakes in
their fronts and the GDI emblem on their sides. Behind them two round lift fans on
shafts (fan intakes, glowing nozzles, house-colour bands, navigation lights, red left,
green right): level when landed, they swing nose up into the hover position in flight,
their round openings facing down. From the pods two outrigger booms run back to two
tall fins, each holding a ducted fan, a stabiliser between them. Under the belly the
bomb bay: two doors hinged at its sides; four gear legs with pads.

The fuselage, pods, booms, fins, lift fans and bay doors wear the light camouflage of
GDI (baked, tinted with the house colour in the game: GAPILE.camo_material).

Nodes for the game: "Flash" (under the open bomb bay, where the bombs leave); the lift
fans turn on "Engine-1"/"Engine1", the bay doors on "BayDoor-1"/"BayDoor1"; "Bomb"
falls out of the bay in Fire.

Clips (see aircraft.py)
    Idle     loop, 2 s: landed, gear out, lift fans off and level, bay shut
    TakeOff  once, 1 s: the lift fans light up and swing into the hover position, the
             gear comes in
    Fly      loop, 1 s: lift fans glowing in the hover position, a gentle sway
    Land     once, 1 s: the gear goes out, the lift fans swing back level and go out
    Fire     once, 0.8 s: the bay doors swing open, a bomb drops out (the flash under
             the bay), the doors close again (Fly pose)

Run headless:

    blender -b --factory-startup --python blender/ORCAB.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle; landed, the gear's pads touch Z = 0.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import DSHP  # noqa: E402 – decal_material(), quad(), on_side(): the GDI emblem
import ORCA  # noqa: E402 – section_loft(), canopy(), ring(), nacelle()
import aircraft as air  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402 – flash()

OUT = os.path.join(air.PROJECT, 'public', 'models', 'ORCAB.glb')
BLEND = os.path.join(HERE, 'ORCAB.blend')

BELLY = 0.16                       # underside of the fuselage, landed (top of the gear)
ENGINE = Vector((0.37, 0.22, 0.3))  # pivot of the right lift fan (x mirrored for the left)
NACELLE = (0.095, 0.15)            # radius, length
TILT_HOVER = -75                   # degrees about x: the nozzles swing down
BAY = (-0.26, 0.06)                # the bomb bay from y to y
BAY_HALF = 0.085                   # half its width (the doors' hinges)
DOOR_OPEN = 80                     # degrees
FLASH_AT = Vector((0, (BAY[0] + BAY[1]) / 2, BELLY - 0.07))
FIRE_FRAMES = 24
DROP = (6, 18)                     # frames: the bomb leaves the bay … has fallen away

POD = (0.16, 0.33, -0.46, 0.07, 0.2, 0.41)  # the side pods: x from, to; y from, to; z from, to
BOOM_X = 0.21                      # the outrigger booms and their fins
FIN = ((0.52, 0.8, 0.34), (0.64, 0.78, 0.66))  # a fin's leading and trailing edge y, z: at the root, at the top
DUCT = (Vector((BOOM_X, 0.69, 0.53)), 0.072)    # the ducted fan in the right fin: middle, radius of its hole

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
HIDDEN = kit.HIDDEN

# y, right half of the cross section (x, z) from the bottom up: the blunt nose, the
# cockpit, the bay and the tail cone between the booms
HULL = (
    (-0.7, ((0.07, 0.215), (0.11, 0.23), (0.115, 0.31), (0.075, 0.345))),
    (-0.64, ((0.1, 0.18), (0.145, 0.195), (0.152, 0.335), (0.095, 0.385))),
    (-0.55, ((0.11, BELLY), (0.158, 0.178), (0.165, 0.355), (0.1, 0.42))),
    (-0.4, ((0.11, BELLY), (0.165, 0.178), (0.17, 0.37), (0.11, 0.44))),
    (0.2, ((0.11, BELLY), (0.165, 0.178), (0.17, 0.37), (0.11, 0.44))),
    (0.33, ((0.08, 0.2), (0.12, 0.215), (0.125, 0.36), (0.08, 0.415))),
    (0.42, ((0.04, 0.26), (0.06, 0.27), (0.06, 0.35), (0.04, 0.37))),
)
CANOPY = range(1, 4)   # the hull sections the glass runs over


def materials():
    m = ORCA.materials()
    m['bomb'] = material('BombCasing', srgb('#3c4134'), 0.6, 0.4)
    return m


def camo(obj, root, name):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{name}', root))
    return obj


def fin_with_duct(name, mat, s, half, segments=24):
    """The fin over the boom on side s: a plate `half` thick each way round the hole of
    its ducted fan, outlined by FIN (the outline's corners kept sharp)."""
    (a0, b0, z0), (a1, b1, z1) = FIN
    outline = [Vector(p) for p in ((a0, z0), (b0, z0), (b1, z1), (a1, z1))]   # (y, z)
    centre, hole = Vector((DUCT[0].y, DUCT[0].z)), DUCT[1]
    angles = {2 * math.pi * k / segments for k in range(segments)}
    angles |= {math.atan2(p.y - centre.y, p.x - centre.x) % (2 * math.pi) for p in outline}
    angles = sorted(angles)

    def edge(direction):
        """Where the ray from the hole's middle leaves the outline."""
        best = None
        for p, q in zip(outline, outline[1:] + outline[:1]):
            e = q - p
            det = direction.x * -e.y - direction.y * -e.x
            if abs(det) < 1e-9:
                continue
            w = p - centre
            t = (w.x * -e.y - w.y * -e.x) / det
            u = (direction.x * w.y - direction.y * w.x) / det
            if t > 0 and -1e-6 <= u <= 1 + 1e-6:
                best = t if best is None else min(best, t)
        return centre + direction * best

    def build(bm):
        sides = []
        for x in (s * BOOM_X - half, s * BOOM_X + half):
            inner, outer = [], []
            for a in angles:
                d = Vector((math.cos(a), math.sin(a)))
                p, q = centre + d * hole, edge(d)
                inner.append(bm.verts.new((x, p.x, p.y)))
                outer.append(bm.verts.new((x, q.x, q.y)))
            sides.append((inner, outer))
        n = len(angles)
        for k in range(n):
            j = (k + 1) % n
            for inner, outer in sides:
                bm.faces.new((inner[k], inner[j], outer[j], outer[k]))
            (i0, o0), (i1, o1) = sides
            bm.faces.new((o0[k], o0[j], o1[j], o1[k]))
            bm.faces.new((i0[k], i0[j], i1[j], i1[k]))

    obj = kit.mesh_object(name, build)
    kit.finish(obj, mat, 0)
    return obj


def hull(m, root):
    """Fuselage, pods, booms, fins and stabiliser in camouflage (one object), their
    details and the emblems."""
    x0, x1, y0, y1, z0, z1 = POD
    parts = []
    for s in (-1, 1):
        parts += [
            # a boxy pod on each side, its outer face leaning in a little
            kit.hexahedron(f'Pod{s}', m['sand'], (
                (s * x0, y0 + 0.02, z0), (s * x1, y0 + 0.02, z0), (s * x1, y1, z0), (s * x0, y1, z0),
                (s * x0, y0, z1), (s * (x1 - 0.01), y0, z1), (s * (x1 - 0.01), y1, z1 - 0.01), (s * x0, y1, z1)), bevel=0.014),
            # the outrigger boom from the pod back to the fin
            kit.hexahedron(f'Boom{s}', m['sand'], (
                (s * (BOOM_X - 0.032), 0.0, 0.29), (s * (BOOM_X + 0.032), 0.0, 0.29), (s * (BOOM_X + 0.026), 0.81, 0.31),
                (s * (BOOM_X - 0.026), 0.81, 0.31),
                (s * (BOOM_X - 0.032), 0.0, 0.375), (s * (BOOM_X + 0.032), 0.0, 0.375), (s * (BOOM_X + 0.026), 0.81, 0.365),
                (s * (BOOM_X - 0.026), 0.81, 0.365)), bevel=0.01),
            fin_with_duct(f'Fin{s}', m['sand'], s, 0.011),
        ]
    shell = kit.merge('Hull', [
        ORCA.section_loft('Fuselage', m['sand'], HULL),
        *parts,
        # the stabiliser between the booms, at the fins' feet
        kit.hexahedron('Stabiliser', m['sand'], (
            (-BOOM_X, 0.6, 0.335), (BOOM_X, 0.6, 0.335), (BOOM_X, 0.79, 0.335), (-BOOM_X, 0.79, 0.335),
            (-BOOM_X, 0.62, 0.352), (BOOM_X, 0.62, 0.352), (BOOM_X, 0.79, 0.35), (-BOOM_X, 0.79, 0.35)), bevel=0.004),
    ])
    for poly in shell.data.polygons:
        poly.use_smooth = False
    camo(shell, root, 'Hull')

    spine = 0.44
    parts = [
        *ORCA.canopy('Canopy', m, [HULL[k] for k in CANOPY], (2, 3), frame=0.01),
        # the sensor in the blunt nose
        cylinder('NoseSensor', m['dark'], 0.032, 0.02, (0, -0.705, 0.27), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.003),
        cylinder('NoseLens', m['glass'], 0.02, 0.01, (0, -0.716, 0.27), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0),
        box('ChinPanel', m['dark'], (0.16, 0.1, 0.012), (0, -0.48, BELLY - 0.003), bevel=0.003),
        # the raised spine: intake grille, hatch, beacon, antenna
        kit.hexahedron('Spine', m['sand_light'], (
            (-0.085, -0.4, spine - 0.004), (0.085, -0.4, spine - 0.004), (0.085, 0.3, spine - 0.004), (-0.085, 0.3, spine - 0.004),
            (-0.07, -0.35, spine + 0.03), (0.07, -0.35, spine + 0.03), (0.07, 0.26, spine + 0.03), (-0.07, 0.26, spine + 0.03)), bevel=0.005),
        box('IntakeFrame', m['steel'], (0.11, 0.1, 0.012), (0, -0.27, spine + 0.032), bevel=0.003),
        *[box(f'IntakeSlat{k}', m['dark'], (0.094, 0.01, 0.014), (0, -0.308 + 0.019 * k, spine + 0.034), bevel=0) for k in range(5)],
        box('Hatch', m['sand'], (0.09, 0.1, 0.008), (0, -0.07, spine + 0.033), bevel=0.003),
        *detail.seam('HatchSeam', m['dark'], (-0.046, -0.12, spine + 0.038), (0.046, -0.12, spine + 0.038), 0.004, 0.003),
        *[detail.seam(f'SpineSeam{k}', m['dark'], (-0.068, y, spine + 0.031), (0.068, y, spine + 0.031), 0.004, 0.003)[0]
          for k, y in enumerate((0.06, 0.17))],
        box('SpineStripe', m['remap'], (0.1, 0.04, 0.012), (0, 0.22, spine + 0.03), bevel=0.003),
        *detail.lamp('Beacon', m['dark'], m['lamp_red'], (0, 0.12, spine + 0.035), (0, 0, 1), 0.013),
        beam('Antenna', m['steel'], (0.04, 0.0, spine + 0.03), (0.05, 0.06, spine + 0.15), 0.007),
        # the bay: a dark recess under the doors, a light at the tail cone
        box('BayWell', m['dark'], (BAY_HALF * 2, BAY[1] - BAY[0], 0.006), (0, (BAY[0] + BAY[1]) / 2, BELLY - 0.002), bevel=0),
        box('TailGrille', m['dark'], (0.08, 0.012, 0.06), (0, 0.422, 0.315), bevel=0.002),
        box('TailLight', m['lamp_white'], (0.022, 0.012, 0.014), (0, 0.426, 0.36), bevel=0),
        box('StabiliserStripe', m['remap'], (0.2, 0.035, 0.008), (0, 0.72, 0.354), bevel=0.002),
    ]
    for s in (-1, 1):
        x = s * (x0 + x1) / 2
        hole = Vector((s * DUCT[0].x, DUCT[0].y, DUCT[0].z))
        parts += [
            *detail.lamp(f'ChinLamp{s}', m['dark'], m['lamp_red'], (s * 0.07, -0.69, 0.22), (0, -1, -0.3), 0.016),
            box(f'NoseStripe{s}', m['remap'], (0.008, 0.12, 0.024), (s * 0.158, -0.47, 0.27), bevel=0.002),
            # the pod: a slatted intake in front, a hatch on top, rivets, a house-colour band
            box(f'PodIntake{s}', m['steel'], (x1 - x0 - 0.04, 0.012, 0.15), (x, y0 + 0.004, (z0 + z1) / 2 + 0.01), bevel=0.003),
            *[box(f'PodSlat{s}{k}', m['dark'], (0.009, 0.012, 0.13), (x + (k - 2.5) * 0.02, y0 - 0.002, (z0 + z1) / 2 + 0.01), bevel=0)
              for k in range(6)],
            box(f'PodHatch{s}', m['sand_light'], (0.1, 0.16, 0.008), (x, -0.12, z1 + 0.002), bevel=0.003),
            *detail.seam(f'PodSeam{s}', m['dark'], (s * (x0 + 0.01), -0.3, z1 + 0.001), (s * (x1 - 0.02), -0.3, z1 + 0.001), 0.004, 0.003),
            *detail.rivets(f'PodRivets{s}', m['steel'], (s * (x1 - 0.004), -0.42, z1 - 0.025), (s * (x1 - 0.004), 0.03, z1 - 0.025), 8, 0.005, 'X'),
            *detail.rivets(f'PodRivetsLow{s}', m['steel'], (s * (x1 + 0.002), -0.42, z0 + 0.025), (s * (x1 + 0.002), 0.03, z0 + 0.025), 8, 0.005,
                           'X'),
            box(f'PodBand{s}', m['remap'], (0.008, 0.04, z1 - z0 - 0.06), (s * (x1 - 0.002), -0.39, (z0 + z1) / 2), bevel=0.002),
            box(f'PodBay{s}', m['dark'], (0.06, 0.3, 0.008), (x, -0.2, z0 - 0.002), bevel=0.002),
            # the shaft the lift fan swings on, from the boom
            cylinder(f'Shaft{s}', m['steel'], 0.024, 0.07, (s * (BOOM_X + 0.055), ENGINE.y, ENGINE.z), rotation=(0, math.pi / 2, 0), segments=12,
                     bevel=0.003),
            box(f'ShaftFairing{s}', m['sand_light'], (0.03, 0.08, 0.06), (s * (BOOM_X + 0.035), ENGINE.y, ENGINE.z), bevel=0.01),
            # stripes and a seam along the boom
            box(f'BoomStripe{s}', m['remap'], (0.056, 0.04, 0.072), (s * BOOM_X, 0.48, 0.337), bevel=0.003),
            *detail.seam(f'BoomSeam{s}', m['dark'], (s * BOOM_X, 0.12, 0.377), (s * BOOM_X, 0.44, 0.371), 0.004, 0.004),
            # the fin's ducted fan: rim, motor, blades, a stator; a house-colour tip
            ORCA.ring(f'DuctRim{s}', m['sand_light'], hole, DUCT[1] - 0.004, DUCT[1] + 0.008, 0.04, 20, (0, math.pi / 2, 0)),
            cylinder(f'DuctBack{s}', m['dark'], DUCT[1] - 0.004, 0.006, hole, rotation=(0, math.pi / 2, 0), segments=20, bevel=0),
            cylinder(f'DuctMotor{s}', m['steel_light'], 0.016, 0.034, hole, rotation=(0, math.pi / 2, 0), segments=10, bevel=0.003),
            *[beam(f'DuctBlade{s}{k}', m['steel'], hole + Vector((0, math.cos(a), math.sin(a))) * 0.014,
                   hole + Vector((0, math.cos(a), math.sin(a))) * (DUCT[1] - 0.01), 0.004, 0.022)
              for k, a in enumerate(2 * math.pi * (k + 0.25) / 7 for k in range(7))],
            beam(f'DuctStator{s}', m['dark'], hole + Vector((s * 0.012, 0, -DUCT[1])), hole + Vector((s * 0.012, 0, DUCT[1])), 0.008, 0.01),
            kit.hexahedron(f'FinTip{s}', m['remap'], (
                (s * (BOOM_X - 0.014), FIN[1][0] - 0.008, FIN[1][2] - 0.035), (s * (BOOM_X + 0.014), FIN[1][0] - 0.008, FIN[1][2] - 0.035),
                (s * (BOOM_X + 0.014), FIN[1][1] + 0.003, FIN[1][2] - 0.035), (s * (BOOM_X - 0.014), FIN[1][1] + 0.003, FIN[1][2] - 0.035),
                (s * (BOOM_X - 0.014), FIN[1][0], FIN[1][2] + 0.004), (s * (BOOM_X + 0.014), FIN[1][0], FIN[1][2] + 0.004),
                (s * (BOOM_X + 0.014), FIN[1][1] + 0.002, FIN[1][2] + 0.004), (s * (BOOM_X - 0.014), FIN[1][1] + 0.002, FIN[1][2] + 0.004)),
                bevel=0.002),
            box(f'BayRail{s}', m['steel'], (0.012, BAY[1] - BAY[0] + 0.02, 0.012), (s * (BAY_HALF + 0.01), (BAY[0] + BAY[1]) / 2, BELLY - 0.004),
                bevel=0.002),
        ]
    details = kit.merge('HullDetails', parts)

    emblem = DSHP.decal_material()
    emblems = kit.merge('Emblems', [DSHP.on_side(DSHP.quad(f'Emblem{s}', emblem, 0.13, 0.13), s, Vector((s * (x1 - 0.004), -0.17, 0.3)),
                                                 math.atan2(0.01, z1 - z0)) for s in (-1, 1)])
    return shell, details, emblems


def gear(m):
    """Nose legs and main legs with pads; origin at the belly, scaling it in z pulls them in."""
    parts = []
    for name, (x, y) in (('NoseL', (-0.06, -0.5)), ('NoseR', (0.06, -0.5)), ('Left', (-0.1, 0.14)), ('Right', (0.1, 0.14))):
        parts += [
            cylinder(f'Leg{name}', m['steel_light'], 0.015, BELLY, (x, y, BELLY / 2), segments=8, bevel=0),
            cylinder(f'Strut{name}', m['steel'], 0.022, 0.05, (x, y, BELLY - 0.035), segments=8, bevel=0.002),
            beam(f'Link{name}', m['steel'], (x, y + 0.025, BELLY - 0.01), (x, y + 0.006, 0.045), 0.01),
            cylinder(f'Pad{name}', m['dark'], 0.036, 0.014, (x, y, 0.007), segments=12, bevel=0.002),
        ]
    return kit.merge('Gear', parts, (0, 0, BELLY))


def bay_door(m, root, s):
    """A bay door hinged at the bay's side s; turning it about y swings it down."""
    hinge = Vector((s * BAY_HALF, (BAY[0] + BAY[1]) / 2, BELLY - 0.006))
    door = box(f'BayDoorPanel{s}', m['sand'], (BAY_HALF, BAY[1] - BAY[0], 0.008), hinge - Vector((s * BAY_HALF / 2, 0, 0)), bevel=0.002)
    door = kit.merge(f'BayDoor{s}', [door], hinge)
    camo(door, root, f'BayDoor{s}')
    return door


def build():
    root, body = air.start('GDIOrcaBomber', 'OrcaBomber')
    m = materials()
    for obj in hull(m, root):
        kit.parent(obj, body)
    legs = kit.parent(gear(m), body)
    engines, nozzles, plumes = [], [], []
    for s in (-1, 1):
        pivot, parts, nozzle, plume = ORCA.nacelle(m, root, s, ENGINE, NACELLE, plume_length=0.32)
        joint = kit.parent(kit.empty(f'Engine{s}', pivot), body)
        for obj in (*parts, nozzle, plume):
            kit.parent(obj, joint)
        engines.append(joint)
        nozzles.append(nozzle)
        plumes.append(plume)
    doors = [kit.parent(bay_door(m, root, s), body) for s in (-1, 1)]
    bomb_at = Vector((0, (BAY[0] + BAY[1]) / 2, BELLY - 0.04))
    bomb = kit.merge('Bomb', [
        cylinder('BombBody', m['bomb'], 0.03, 0.16, bomb_at, rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.008),
        cylinder('BombNose', m['bomb'], 0.03, 0.05, bomb_at - Vector((0, 0.1, 0)), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0,
                 radius2=0.008),
        cylinder('BombBand', m['remap'], 0.032, 0.02, bomb_at - Vector((0, 0.04, 0)), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0),
        box('BombFinV', m['dark'], (0.006, 0.05, 0.09), bomb_at + Vector((0, 0.09, 0)), bevel=0),
        box('BombFinH', m['dark'], (0.09, 0.05, 0.006), bomb_at + Vector((0, 0.09, 0)), bevel=0),
    ], bomb_at)
    kit.parent(bomb, body)
    flash = kit.parent(nod.flash(m, 'Flash', FLASH_AT, 0.05, facing=(0, 0, -1)), body)

    channels = [(body, 'location'), (body, 'rotation_euler'), (legs, 'scale'), (flash, 'scale'), (bomb, 'location'), (bomb, 'scale')]
    for door in doors:
        channels.append((door, 'rotation_euler'))
    for joint, nozzle, plume in zip(engines, nozzles, plumes):
        channels += [(joint, 'rotation_euler'), (nozzle, 'scale'), (plume, 'scale')]

    rad = math.radians
    hidden = Vector((HIDDEN,) * 3)

    def pose(tilt, thrust, gear_out, pitch=0.0, roll=0.0, lift=0.0, door=0.0):
        v = {
            ('Body', 'location'): Vector((0, 0, lift)),
            ('Body', 'rotation_euler'): Vector((rad(pitch), rad(roll), 0)),
            ('Gear', 'scale'): Vector((1, 1, air.mix(0.02, 1, gear_out))),
            ('Flash', 'scale'): hidden,
            ('Bomb', 'location'): bomb_at.copy(),
            ('Bomb', 'scale'): hidden,
        }
        for d, s in zip(doors, (-1, 1)):
            v[(d.name, 'rotation_euler')] = Vector((0, rad(s * DOOR_OPEN * door), 0))
        for joint, nozzle, plume in zip(engines, nozzles, plumes):
            v[(joint.name, 'rotation_euler')] = Vector((rad(tilt), 0, 0))
            v[(nozzle.name, 'scale')] = Vector((1, 1, 1)) if thrust > 0.05 else hidden
            v[(plume.name, 'scale')] = Vector((1, thrust, 1)) if thrust > 0.05 else hidden
        return v

    def flicker(f):
        return 1 + 0.12 * math.sin(f * 2.3) * math.sin(f * 0.7 + 1)

    def fly(f, frames=air.FLY_FRAMES):
        t = 2 * math.pi * f / frames
        return pose(TILT_HOVER, flicker(f), 0, pitch=-2 + 0.6 * math.sin(2 * t), roll=1.2 * math.sin(t), lift=0.008 * math.sin(t))

    def idle(f):
        return pose(0, 0, 1)

    def take_off(f):
        return pose(air.mix(0, TILT_HOVER, air.span(f, 4, 24)), air.span(f, 0, 10) * flicker(f), 1 - air.span(f, 12, 28),
                    pitch=air.mix(0, -2, air.span(f, 10, 30)))

    def land(f):
        return pose(air.mix(TILT_HOVER, 0, air.span(f, 8, 28)), (1 - air.span(f, 18, 30)) * flicker(f), air.span(f, 0, 16),
                    pitch=air.mix(-2, 0, air.span(f, 0, 20)))

    def fire(f):
        # the Fly loop's sway over the whole clip would not end where Fly goes on: hold its first pose
        v = fly(0)
        door = air.span(f, 0, 5) * (1 - air.span(f, 17, FIRE_FRAMES))
        for d, s in zip(doors, (-1, 1)):
            v[(d.name, 'rotation_euler')] = Vector((0, rad(s * DOOR_OPEN * door), 0))
        if DROP[0] <= f < DROP[1]:
            t = (f - DROP[0]) / (DROP[1] - DROP[0])
            v[('Bomb', 'location')] = bomb_at - Vector((0, -0.04 * t, 0.5 * t * t + 0.03))
            v[('Bomb', 'scale')] = Vector((1, 1, 1))
        if f in (DROP[0], DROP[0] + 1):
            v[('Flash', 'scale')] = Vector((1, 1, 1)) * (1.3 if f > DROP[0] else 1.0)
        v[('Body', 'rotation_euler')].x += rad(1.0 * math.sin(math.pi * air.span(f, DROP[0], DROP[0] + 10)))  # it lifts a little
        return v

    air.clip('Idle', air.IDLE_FRAMES, channels, idle)
    air.clip('TakeOff', air.TAKEOFF_FRAMES, channels, take_off)
    air.clip('Fly', air.FLY_FRAMES, channels, fly)
    air.clip('Land', air.LAND_FRAMES, channels, land)
    air.clip('Fire', FIRE_FRAMES, channels, fire)

    def rest():
        for (name, prop), value in idle(0).items():
            setattr(kit.collection().objects[name], prop, value)

    rest()
    return rest


if __name__ == '__main__':
    air.main(build, OUT, BLEND, {'Idle': [0], 'TakeOff': [15], 'Fly': [0], 'Fire': [10]}, bake=512, scale=2.0, target=(0, 0, 0.25))
