"""
Tiberian Fallout – GDI Disruptor (SONIC), after Tiberian Sun.

A long, broad tracked tank in two armoured blocks, like the original: the front block
with a sloped glacis, a raised driver's plateau with hatches and vision blocks and
headlights; behind a ribbed joint the rear block carrying the turret, an engine deck
with grilles, exhausts and tail lights at the back. Framed side armour hangs over the
tracks, with dark vent strips, rivets and house-colour stripes on the shoulders. On the
round turntable (ringed in the house colour) stands the sonic emitter: a tall curved
reflector, a polished grey sail that rises at the back of the turret and curls forward
over it, bowed across like a dish; a transducer with a pale blue core sits in its
hollow, ribs and two posts with cables hold it from behind over a low generator
housing. The hull and the generator housing are in the light camouflage of the
buildings, tinted with the house colour in the game (GAPILE.camo_material).

Nodes the game uses: "Turret" (turns about its vertical towards the target), "Cannon"
(the reflector, tipped up and down), "Flash" (the muzzle: the glare in front of the
reflector). Clips (see nodvehicle.py for Idle and Walk):
    Idle   loop, 2 s: the engine runs, the hull shivers, the core pulses softly
    Walk   loop: driving, the wheels and sprockets turn, the hull rocks; the root's
           walkSpeed (glTF extras) is the ground speed in cells per second
    Fire   once, 1 s: the core flares, three sound rings run out of the reflector's
           hollow and widen, the reflector shudders back

Run headless:

    blender -b --factory-startup --python blender/SONIC.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'SONIC.glb')
BLEND = os.path.join(HERE, 'SONIC.blend')

TRACK_X = 0.25
TRACK_WIDTH = 0.12
TRACK = (-0.45, 0.43)
TRACK_HEIGHT = 0.12
WHEEL_RADIUS = 0.042
WHEELS_Y = (-0.28, -0.14, 0.0, 0.14, 0.28)
SPROCKET = 0.063                  # 2/3 of a turn per loop (3 bolts: seamless)
WALK_FRAMES = 30
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
FIRE_FRAMES = 30
HALF = 0.33                        # the armour blocks' half width
SHOULDER = 0.13                    # their bottom, over the tracks
FRONT_TOP = 0.255                  # the front block's top (the plateau is higher)
DECK = 0.27                        # the rear block's top
JOINT = (-0.065, -0.015)           # the joint between the blocks (y)
TURRET = Vector((0, 0.19, DECK))   # the turntable's middle (it turns about z here)
FOCUS = Vector((0, 0.11, 0.46))    # the reflector's hollow: where the rings start
SAIL = (0.2, 0.36, -35, 65)        # the reflector: radius of its curl, radius of its bow across, lowest and highest angle (°)
EMITTER = Vector((0, 0.35, 0.44))    # the reflector's trunnion behind it
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = nod.materials()
    m.update({
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#3a6a96'), strength=0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'hood': material('HoodGrey', srgb('#d3d7d8'), 0.32, 0.45),
        'core': material('SonicCore', srgb('#bfefff'), 0.2, emission=srgb('#7fd8ff'), strength=5),
        'wave': material('SonicWave', (0, 0, 0), 1.0, emission=srgb('#a8e6ff'), strength=5, alpha=0.45),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def loft(name, mat, sections, bevel=0.008):
    """A solid through cross-sections: `sections` = [(y, [(x, z), …]), …] from front
    to back, each a convex polygon with the same number of corners; capped at both
    ends."""
    def build(bm):
        rings = [[bm.verts.new((x, y, z)) for x, z in points] for y, points in sections]
        n = len(rings[0])
        for a, b in zip(rings, rings[1:]):
            for i in range(n):
                bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
        bm.faces.new(rings[0])
        bm.faces.new(list(reversed(rings[-1])))

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def block_section(y, top, half=HALF, bottom=SHOULDER, chamfer=0.025):
    """An armour block's cross-section at y: flat sides, chamfered top edges."""
    return y, [(-half, bottom), (half, bottom), (half, top - chamfer), (half - chamfer, top), (-half + chamfer, top), (-half, top - chamfer)]


def deck_grille(name, frame_mat, slat_mat, centre, size, slats=5):
    """A flat vent lying on a deck: a frame and slats across it."""
    centre = Vector(centre)
    sx, sy = size
    parts = [box(f'{name}Frame', frame_mat, (sx + 0.012, sy + 0.012, 0.008), centre, bevel=0.002)]
    parts += [box(f'{name}Slat{k}', slat_mat, (sx, sy / slats * 0.5, 0.006), centre + Vector((0, -sy / 2 + (k + 0.5) * sy / slats, 0.003)),
                  bevel=0) for k in range(slats)]
    return parts


# --------------------------------------------------------------------------- hull

def hull(m, root):
    """The camouflaged hull: the low body between the tracks, the front block with its
    glacis and plateau, the rear block (one mesh)."""
    parts = [
        kit.hexahedron('Lower', m['sand'], (
            (-0.2, -0.44, 0.07), (0.2, -0.44, 0.07), (0.2, 0.44, 0.07), (-0.2, 0.44, 0.07),
            (-0.2, -0.47, SHOULDER + 0.01), (0.2, -0.47, SHOULDER + 0.01), (0.2, 0.45, SHOULDER + 0.01), (-0.2, 0.45, SHOULDER + 0.01)),
            bevel=0.01),
        # the front block: the glacis slopes up from the nose to the top
        loft('FrontBlock', m['sand'], [
            block_section(-0.51, 0.155, HALF - 0.03, SHOULDER, 0.01),
            block_section(-0.37, FRONT_TOP),
            block_section(JOINT[0] - 0.01, FRONT_TOP),
            block_section(JOINT[0], FRONT_TOP - 0.015, HALF - 0.01),
        ], bevel=0.01),
        # the driver's plateau on it
        kit.hexahedron('Plateau', m['sand'], (
            (-0.18, -0.36, FRONT_TOP - 0.005), (0.18, -0.36, FRONT_TOP - 0.005), (0.18, JOINT[0] - 0.01, FRONT_TOP - 0.005),
            (-0.18, JOINT[0] - 0.01, FRONT_TOP - 0.005),
            (-0.16, -0.3, FRONT_TOP + 0.035), (0.16, -0.3, FRONT_TOP + 0.035), (0.16, JOINT[0] - 0.02, FRONT_TOP + 0.035),
            (-0.16, JOINT[0] - 0.02, FRONT_TOP + 0.035)), bevel=0.008),
        # the rear block with the turntable, its back sloping down to the tail
        loft('RearBlock', m['sand'], [
            block_section(JOINT[1], DECK - 0.015, HALF - 0.01),
            block_section(JOINT[1] + 0.01, DECK),
            block_section(0.4, DECK),
            block_section(0.455, DECK - 0.05, HALF - 0.01, SHOULDER + 0.01),
        ], bevel=0.01),
    ]
    return camo(kit.merge('HullShell', parts), root)


def side_panels(m, s, y0, y1, top):
    """Framed armour plates down a block's flank, a dark vent strip over them."""
    x = s * (HALF + 0.004)
    mid, length = (y0 + y1) / 2, y1 - y0
    parts = [
        box(f'Vent{s}{y0:.2f}', m['dark'], (0.008, length - 0.05, 0.022), (x, mid, top - 0.045), bevel=0.002),
        *[box(f'VentSlat{s}{y0:.2f}{k}', m['steel'], (0.01, 0.006, 0.022), (x, y0 + 0.035 + k * (length - 0.07) / 9, top - 0.045), bevel=0)
          for k in range(10)],
    ]
    count = 2
    w = (length - 0.03) / count
    for k in range(count):
        c = y0 + 0.015 + w * (k + 0.5)
        parts += [
            box(f'Plate{s}{y0:.2f}{k}', m['sand_light'], (0.006, w - 0.02, 0.055), (x, c, SHOULDER + 0.04), bevel=0.003),
            *detail.rivets(f'PlateRivets{s}{y0:.2f}{k}', m['steel_light'], (x + s * 0.003, c - w / 2 + 0.02, SHOULDER + 0.075),
                           (x + s * 0.003, c + w / 2 - 0.02, SHOULDER + 0.075), 4, axis='X'),
        ]
    return parts


def hull_details(m):
    plateau = FRONT_TOP + 0.035
    parts = [
        # the plateau: driver's hatch with vision blocks, a second hatch, a periscope
        box('DriverHatch', m['sand_light'], (0.09, 0.08, 0.012), (-0.08, -0.2, plateau + 0.004), bevel=0.004),
        *[box(f'Vision{k}', m['glass'], (0.032, 0.012, 0.014), (-0.115 + 0.035 * k, -0.33, FRONT_TOP + 0.02), bevel=0.002,
              rotation=(math.radians(-34), 0, 0)) for k in range(3)],
        cylinder('Hatch2', m['steel'], 0.035, 0.014, (0.08, -0.18, plateau + 0.006), segments=16),
        box('Periscope', m['steel'], (0.03, 0.02, 0.02), (0.08, -0.225, plateau + 0.012), bevel=0.003),
        *detail.seam('PlateauSeam', m['seam'], (-0.16, -0.12, plateau + 0.001), (0.16, -0.12, plateau + 0.001)),
        # the glacis: tow hooks, a spare track run, a plate between the headlights
        *[box(f'TowHook{s}', m['steel'], (0.03, 0.04, 0.03), (s * 0.12, -0.515, 0.13), bevel=0.005) for s in (-1, 1)],
        *[box(f'SpareLink{k}', m['track'], (0.05, 0.018, 0.035), (-0.075 + 0.05 * k, -0.445, 0.2), bevel=0.004,
              rotation=(math.radians(-40), 0, 0)) for k in range(4)],
        # the joint between the blocks: a dark gap with ribs
        box('Joint', m['dark'], (2 * HALF - 0.04, JOINT[1] - JOINT[0] + 0.01, 0.1), (0, sum(JOINT) / 2, SHOULDER + 0.06), bevel=0.004),
        *[box(f'JointRib{k}', m['steel'], (2 * HALF - 0.06, 0.008, 0.012), (0, sum(JOINT) / 2, SHOULDER + 0.03 + 0.03 * k), bevel=0)
          for k in range(4)],
        # the engine deck behind the turret, exhausts and a plate at the back
        *deck_grille('EngineVent', m['steel'], m['dark'], (0, 0.385, DECK + 0.003), (0.24, 0.05), 5),
        box('BackPlate', m['sand_light'], (0.34, 0.012, 0.09), (0, 0.461, 0.18), bevel=0.004, rotation=(math.radians(20), 0, 0)),
        box('TowHitch', m['steel'], (0.05, 0.03, 0.03), (0, 0.47, 0.12), bevel=0.005),
        beam('Antenna', m['steel'], (0.27, 0.4, DECK), (0.29, 0.44, DECK + 0.3), 0.006),
        cylinder('AntennaBase', m['dark'], 0.014, 0.02, (0.27, 0.4, DECK + 0.01), segments=8, bevel=0),
        box('Stowage', m['olive'], (0.08, 0.1, 0.04), (-0.26, 0.37, DECK + 0.02), bevel=0.008),
        *[beam(f'StowageStrap{k}', m['dark'], (-0.305, 0.35 + 0.04 * k, DECK + 0.042), (-0.215, 0.35 + 0.04 * k, DECK + 0.042), 0.008, 0.004)
          for k in range(2)],
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.23, -0.445, 0.205), (0, -1, 0.7), 0.016),
            *detail.lamp(f'Marker{s}', m['dark'], m['lamp_amber'], (s * 0.29, -0.43, 0.215), (0, -1, 0.7), 0.008),
            # house-colour stripes on the shoulders of both blocks
            box(f'FrontStripe{s}', m['remap'], (0.06, 0.24, 0.005), (s * 0.25, -0.22, FRONT_TOP + 0.002), bevel=0.002),
            box(f'RearStripe{s}', m['remap'], (0.06, 0.12, 0.005), (s * 0.25, 0.32, DECK + 0.002), bevel=0.002),
            # the flanks: framed plates and vent strips, a skirt edge over the track
            *side_panels(m, s, -0.37, JOINT[0] - 0.01, FRONT_TOP),
            *side_panels(m, s, JOINT[1] + 0.01, 0.42, DECK),
            box(f'SkirtEdge{s}', m['steel'], (0.016, 0.9, 0.014), (s * (HALF - 0.004), -0.03, SHOULDER - 0.002), bevel=0.003),
            # shoulder seams, a grab handle, rivets along the deck edges
            *[p for k, y in enumerate((-0.26, -0.15, 0.1, 0.22)) for p in detail.seam(
                f'ShoulderSeam{s}{k}', m['seam'], (s * 0.19, y, (FRONT_TOP if y < 0 else DECK) + 0.001),
                (s * (HALF - 0.025), y, (FRONT_TOP if y < 0 else DECK) + 0.001))],
            beam(f'Handle{s}', m['steel_light'], (s * 0.25, -0.33, FRONT_TOP + 0.012), (s * 0.25, -0.29, FRONT_TOP + 0.012), 0.006),
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (s * 0.26, 0.453, 0.215), (0, 1, 0.3), 0.012),
            cylinder(f'Exhaust{s}', m['steel'], 0.018, 0.1, (s * 0.12, 0.445, DECK + 0.01), segments=10),
            cylinder(f'ExhaustTip{s}', m['dark'], 0.015, 0.012, (s * 0.12, 0.445, DECK + 0.06), segments=10, bevel=0),
            box(f'ExhaustGuard{s}', m['steel_light'], (0.05, 0.012, 0.05), (s * 0.12, 0.425, DECK + 0.02), bevel=0.003),
        ]
    return kit.merge('HullDetails', parts)


# --------------------------------------------------------------------------- reflector

def sail_point(u, angle, out=0.0):
    """A point on the reflector: `angle` up its curl (°, 0 = level with the focus),
    `u` across it (-1 … 1), `out` behind its face."""
    curl, bow, low, high = SAIL
    a = math.radians(angle)
    t = (angle - low) / (high - low)
    half = 0.18 - 0.035 * t * t  # a little narrower towards the top
    x = u * half
    r = curl + out
    return FOCUS + Vector((x, r * math.cos(a) - x * x / (2 * bow), r * math.sin(a)))


def sail(name, mat, thickness=0.014, columns=12, rows=12, across=(-1, 1), up=None, out=0.0):
    """The reflector sail, or a patch of it (`across`: from u to u, `up`: from angle
    to angle): a curved plate `thickness` thick, its face `out` behind the sail's."""
    low, high = up or SAIL[2:]

    def build(bm):
        grid = [[[bm.verts.new(sail_point(across[0] + (across[1] - across[0]) * i / columns, low + (high - low) * j / rows, out + d))
                  for d in (0.0, thickness)] for j in range(rows + 1)] for i in range(columns + 1)]
        for i in range(columns):
            for j in range(rows):
                for d in (0, 1):
                    bm.faces.new((grid[i][j][d], grid[i + 1][j][d], grid[i + 1][j + 1][d], grid[i][j + 1][d]))
        for i in range(columns):  # the bottom and top edges
            for j in (0, rows):
                bm.faces.new((grid[i][j][0], grid[i + 1][j][0], grid[i + 1][j][1], grid[i][j][1]))
        for j in range(rows):  # the side edges
            for i in (0, columns):
                bm.faces.new((grid[i][j][0], grid[i][j + 1][0], grid[i][j + 1][1], grid[i][j][1]))

    return kit.finish(kit.mesh_object(name, build), mat, 0.003)


def turret(m, root, body):
    """The turntable (node Turret) with the generator and the reflector on the Cannon;
    returns (turret, reflector, core, flash, waves)."""
    turn = kit.parent(kit.empty('Turret', TURRET), body)
    z0 = DECK
    housing = camo(kit.merge('TurretShell', [kit.hexahedron('TurretShell', m['sand'], (
        (-0.12, TURRET.y + 0.02, z0 + 0.03), (0.12, TURRET.y + 0.02, z0 + 0.03), (0.12, TURRET.y + 0.17, z0 + 0.03),
        (-0.12, TURRET.y + 0.17, z0 + 0.03),
        (-0.1, TURRET.y + 0.05, z0 + 0.07), (0.1, TURRET.y + 0.05, z0 + 0.07), (0.1, TURRET.y + 0.16, z0 + 0.065),
        (-0.1, TURRET.y + 0.16, z0 + 0.065)), bevel=0.01)], TURRET), root)
    kit.parent(housing, turn)
    parts = [
        # the turntable: a steel ring, a band in the house colour, a light top
        cylinder('TurretRing', m['steel'], 0.155, 0.024, (0, TURRET.y, z0 + 0.008), segments=28),
        cylinder('TurretBand', m['remap'], 0.16, 0.014, (0, TURRET.y, z0 + 0.018), segments=28, bevel=0.002),
        cylinder('TurretTop', m['sand_light'], 0.142, 0.012, (0, TURRET.y, z0 + 0.028), segments=28, bevel=0.003),
        *detail.rivets('TurretBolts', m['steel_light'], (-0.12, TURRET.y - 0.08, z0 + 0.036), (0.12, TURRET.y - 0.08, z0 + 0.036), 7, axis='Z'),
        # the generator: a vent on its roof, a lamp
        *deck_grille('GeneratorVent', m['steel'], m['dark'], (0, TURRET.y + 0.1, z0 + 0.068), (0.12, 0.05), 4),
        *detail.lamp('TurretLight', m['dark'], m['lamp_red'], (-0.1, TURRET.y + 0.17, z0 + 0.05), (0, 1, 0), 0.009),
        # two posts from the generator up to the trunnion, the trunnion between them
        *[box(f'Post{s}', m['steel'], (0.026, 0.04, EMITTER.z - z0 - 0.06), (s * 0.085, EMITTER.y - 0.005, (EMITTER.z + z0 + 0.06) / 2),
              bevel=0.004) for s in (-1, 1)],
        *[cylinder(f'PostCap{s}', m['steel_light'], 0.022, 0.03, EMITTER + Vector((s * 0.085, 0, 0)), rotation=(0, math.pi / 2, 0), segments=12)
          for s in (-1, 1)],
        cylinder('Trunnion', m['steel_light'], 0.016, 0.2, EMITTER, rotation=(0, math.pi / 2, 0), segments=12),
    ]
    for s in (-1, 1):  # cables from the generator's back up into the reflector's hub
        start = Vector((s * 0.05, TURRET.y + 0.15, z0 + 0.06))
        parts += detail.hose(f'Cable{s}', m['dark'], start, start + Vector((s * 0.02, 0.06, 0.06)), EMITTER + Vector((s * 0.035, 0.02, -0.02)),
                             0.008)
    kit.parent(kit.merge('TurretDetails', parts, TURRET), turn)

    pivot = kit.parent(kit.empty('Cannon', EMITTER), turn)
    reflector = [
        sail('Sail', m['hood']),
        # the emitter plate in the hollow (its glowing core is a node of its own)
        sail('EmitterPlate', m['steel'], 0.006, 8, 6, (-0.52, 0.52), (-24, 34), -0.005),
        # ribs on the back, brackets onto the trunnion
        *[beam(f'Rib{k}{j}', m['steel'], sail_point(u, a0, 0.016), sail_point(u, a1, 0.016), 0.014, 0.01)
          for k, u in enumerate((-0.55, 0.0, 0.55)) for j, (a0, a1) in enumerate(zip(range(-30, 60, 15), range(-15, 75, 15)))],
        *[beam(f'Bracket{s}', m['steel'], sail_point(s * 0.3, 0, 0.02), EMITTER + Vector((s * 0.06, 0, 0)), 0.02) for s in (-1, 1)],
        cylinder('Hub', m['steel'], 0.03, 0.03, EMITTER, rotation=(0, math.pi / 2, 0), segments=12),
    ]
    horn = kit.parent(kit.merge('Emitter', reflector, EMITTER), pivot)
    face = sail_point(0, 5, -0.009)
    # the core: three glowing slits across the plate
    core = kit.parent(kit.merge('Core', [sail(f'Core{k}', m['core'], 0.004, 8, 1, (-0.4, 0.4), (a, a + 6), -0.009)
                                         for k, a in enumerate((-15, 2, 19))], face), horn)
    flash = kit.parent(kit.merge('Flash', [sphere('FlashBall', m['wave'], 0.07, FOCUS - Vector((0, 0.02, 0)), 12)], FOCUS), pivot)
    waves = []
    radius = 0.11
    for k in range(3):
        ring = []
        for j in range(16):  # a ring of short glowing segments round the focus
            a0, a1 = 2 * math.pi * j / 16, 2 * math.pi * (j + 1) / 16
            p0 = FOCUS + Vector((radius * math.cos(a0), 0, radius * math.sin(a0)))
            p1 = FOCUS + Vector((radius * math.cos(a1), 0, radius * math.sin(a1)))
            ring.append(beam(f'Wave{k}_{j}', m['wave'], p0, p1, 0.02, 0.014))
        waves.append(kit.parent(kit.merge(f'Wave{k}', ring, FOCUS), pivot))
    return turn, horn, core, flash, waves


# --------------------------------------------------------------------------- clips

def clips(horn, core, flash, waves):
    """Idle: the core pulses; Fire: core flare, rings out, reflector kick."""
    one, hidden = Vector((1, 1, 1)), Vector((kit.HIDDEN,) * 3)
    kit.keys(core, 'scale', {f: Vector((1, 1, 1)) * (0.85 + 0.15 * math.sin(2 * math.pi * f / kit.IDLE_END * 2) ** 2)
                             for f in range(0, kit.IDLE_END + 1, 5)}, 'LINEAR')
    kit.to_track(core, 'Idle')
    kit.keys(core, 'scale', {0: one, 2: Vector((1.3, 1, 1.3)), 8: one, FIRE_FRAMES: one})
    kit.to_track(core, 'Fire')
    walker.hold(core, 'scale', one, WALK_FRAMES, 'Walk')
    # the flash: a glowing ball in the hollow for a few frames
    kit.keys(flash, 'scale', {0: Vector((1, 0.6, 1)), 2: Vector((1.5, 1.2, 1.5)), 5: Vector((1.2, 1, 1.2)), 7: hidden,
                              FIRE_FRAMES: hidden}, 'CONSTANT')
    kit.to_track(flash, 'Fire')
    walker.hide([flash], kit.IDLE_END, 'Idle')
    walker.hide([flash], WALK_FRAMES, 'Walk')
    # the rings run out of the hollow one after another and widen
    for k, ring in enumerate(waves):
        rest = ring.location.copy()
        start = 1 + 4 * k
        kit.keys(ring, 'location', {0: rest, start: rest, start + 14: rest - Vector((0, 0.9, 0)), FIRE_FRAMES: rest - Vector((0, 0.9, 0))},
                 'LINEAR')
        kit.keys(ring, 'scale', {0: hidden, start - 1 if start else 0: hidden, start: Vector((0.9, 1, 0.9)),
                                 start + 13: Vector((2.6, 1, 2.6)), start + 14: hidden, FIRE_FRAMES: hidden}, 'LINEAR')
        kit.to_track(ring, 'Fire')
        walker.hide([ring], kit.IDLE_END, 'Idle')
        walker.hide([ring], WALK_FRAMES, 'Walk')
        walker.hold(ring, 'location', rest, kit.IDLE_END, 'Idle')
        walker.hold(ring, 'location', rest, WALK_FRAMES, 'Walk')
        ring.location, ring.scale = rest, hidden
    # the reflector shudders back on the shot
    rest = horn.location.copy()
    kit.keys(horn, 'location', {0: rest, 2: rest + Vector((0, 0.03, 0)), 6: rest + Vector((0, 0.025, 0)), 16: rest, FIRE_FRAMES: rest})
    kit.to_track(horn, 'Fire')
    walker.hold(horn, 'location', rest, kit.IDLE_END, 'Idle')
    walker.hold(horn, 'location', rest, WALK_FRAMES, 'Walk')
    horn.location, core.scale, flash.scale = rest, one, hidden


def build():
    root, body = nod.start('GDIDisruptor', 'Disruptor', WALK_SPEED)
    m = materials()
    kit.parent(hull(m, root), body)
    kit.parent(hull_details(m), body)
    _, horn, core, flash, waves = turret(m, root, body)
    wheels, sprockets = [], []
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], TRACK_HEIGHT, 22), body)
        x = s * (TRACK_X + TRACK_WIDTH / 2 + 0.004)
        wheels += [kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (x, y, WHEEL_RADIUS + 0.004), WHEEL_RADIUS, 0.02), body)
                   for k, y in enumerate(WHEELS_Y)]
        sprockets += [kit.parent(nod.road_wheel(m, f'Sprocket{s}{k}', (x, y, SPROCKET + 0.004), SPROCKET, 0.022), body)
                      for k, y in enumerate((TRACK[0] + 0.06, TRACK[1] - 0.06))]
    kit.bake_camo(512)
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003, extra=((sprockets, WHEEL_RADIUS / SPROCKET),))
    clips(horn, core, flash, waves)
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels + sprockets:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [6], 'Fire': [3, 9]}, scale=1.5, target=(0, 0, 0.25))
