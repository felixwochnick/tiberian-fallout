"""
Tiberian Fallout – GDI Hover MLRS (HVR), after Tiberian Sun.

A catamaran on an air cushion, like the original: two long pontoon hulls with flat,
sloped wedge noses, joined by a lower centre deck. At the front of the deck sits a
small glazed cockpit, behind it a low spine runs back to the turret ring. On the ring
turns the launcher: a squat turret with a target-laser eye carrying, on short arms, two
box launchers side by side, each with 2 × 4 tubes and red warheads. Lift fans turn in
round ducts on the pontoons' backs, louvred thrust nozzles close their sterns; panel
seams, rivets, intake grilles and lamps cover the hulls. Under each pontoon the air
cushion glows pale blue. The hulls, turret and launchers are in the light camouflage of
the buildings, tinted with the house colour in the game (GAPILE.camo_material); panels
on the pontoons' flanks, the fan ducts and bands on the launchers are in the house
colour.

Nodes the game uses: "Turret" (turns about its vertical towards the target),
"Cannon" (the launchers, tipped up and down), "Flash0"/"Flash1" (the launchers'
muzzles, used in turn). Clips:
    Idle   loop, 2 s: hovering on the spot, the hull bobs, the cushion glows, the
           lift fans turn slowly
    Walk   loop, 1 s: gliding, the hull leans back a little and sways, the fans
           race, the cushion glows brighter; the root's walkSpeed (glTF extras) is
           the speed the sway is made for (nothing touches the ground)
    Fire   once, 1 s: both launchers fire a rocket, flashes and a kick back

Run headless:

    blender -b --factory-startup --python blender/HVR.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'HVR.glb')
BLEND = os.path.join(HERE, 'HVR.blend')

WALK_FRAMES = 30
WALK_SPEED = 0.8                    # cells per second the glide is made for
FIRE_FRAMES = 30
LIFT = 0.07                         # the skirts' bottom over the ground
PONTOON = (0.125, 0.305)            # a pontoon's inner and outer side (|x|)
KEEL = 0.085                        # the pontoons' bottom
TOP = 0.25                          # the pontoons' top
DECK = 0.19                         # the centre deck's top, between the pontoons
NOSE = -0.48                        # the pontoons' tips
STERN = 0.47
TURRET = Vector((0, 0.12, DECK))
LAUNCHER = Vector((0, 0.14, 0.345))  # the launchers' trunnion
POD_X = 0.155
POD = (0.14, 0.11, 0.32)             # a launcher box: width, height, length
FANS = ((-0.215, 0.35, TOP), (0.215, 0.35, TOP))
FAN_RADIUS = 0.046
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material
ALONG_Y = (math.pi / 2, 0, 0)


def materials():
    m = nod.materials()
    m.update({
        'glass': material('Windscreen', srgb('#1a2632'), 0.1, 0.6, emission=srgb('#3a6a96'), strength=0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'skirt': material('Skirt', srgb('#2a2926'), 0.9, 0.05),
        'warhead': material('Warhead', srgb('#b3261c'), 0.45, 0.3),
        'cushion': material('HoverGlow', (0, 0, 0), 1.0, emission=srgb('#8fd6ff'), strength=3, alpha=0.3),
        'laser': material('LaserEye', srgb('#ff3020'), 0.2, emission=srgb('#ff2a10'), strength=10),
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


def ring(name, mat, inner, outer, z0, z1, centre, segments=24):
    """A flat annulus about the vertical (a duct's lip), from z0 to z1."""
    cx, cy = centre

    def build(bm):
        rims = [[bm.verts.new((cx + r * math.cos(2 * math.pi * k / segments), cy + r * math.sin(2 * math.pi * k / segments), z))
                 for k in range(segments)] for r, z in ((inner, z0), (outer, z0), (outer, z1), (inner, z1))]
        for a, b in zip(rims, rims[1:] + rims[:1]):
            for k in range(segments):
                bm.faces.new((a[k], a[(k + 1) % segments], b[(k + 1) % segments], b[k]))

    return kit.finish(kit.mesh_object(name, build), mat, 0.002)


def deck_grille(name, frame_mat, slat_mat, centre, size, slats=5, across='X'):
    """A flat vent lying on a deck: a frame and slats (running along `across`)."""
    centre = Vector(centre)
    sx, sy = size
    parts = [box(f'{name}Frame', frame_mat, (sx + 0.012, sy + 0.012, 0.008), centre, bevel=0.002)]
    for k in range(slats):
        if across == 'X':
            p, s = centre + Vector((0, -sy / 2 + (k + 0.5) * sy / slats, 0.003)), (sx, sy / slats * 0.5, 0.006)
        else:
            p, s = centre + Vector((-sx / 2 + (k + 0.5) * sx / slats, 0, 0.003)), (sx / slats * 0.5, sy, 0.006)
        parts.append(box(f'{name}Slat{k}', slat_mat, s, p, bevel=0))
    return parts


# --------------------------------------------------------------------------- hull

def pontoon_section(s, y, bottom, top, narrow=0.0):
    """A pontoon's cross-section at y: flat bottom and top, the flank leaning in a
    little, chamfered outer edges."""
    xi, xo = s * (PONTOON[0] + narrow / 2), s * (PONTOON[1] - narrow)
    h = top - bottom
    lo, hi = min(0.04, 0.3 * h), min(0.035, 0.3 * h)
    lean = s * 0.02 * h / (TOP - KEEL)  # the flank leans in towards the top
    return y, [(xi, bottom), (xo - s * lo * 0.7, bottom), (xo, bottom + lo), (xo - lean, top - hi), (xo - lean - s * hi, top), (xi, top)]


def flank(s, z, out=0.0):
    """The x of a pontoon's leaning flank at height z (`out` off its face)."""
    t = min(max((z - KEEL - 0.04) / (TOP - 0.035 - KEEL - 0.04), 0.0), 1.0)
    return s * (PONTOON[1] - 0.02 * t + out)


FLANK_TILT = math.atan2(0.02, TOP - 0.035 - KEEL - 0.04)


def nose_top(y):
    """The pontoons' top on the sloped nose plate (and behind it)."""
    return min(TOP, 0.165 + (y - NOSE) * 0.5)


def hull(m, root):
    """The pontoons, the centre deck and the spine (one camouflaged mesh)."""
    parts = []
    for s in (-1, 1):
        parts.append(loft(f'Pontoon{s}', m['sand'], [
            pontoon_section(s, NOSE, 0.135, nose_top(NOSE), 0.02),
            pontoon_section(s, -0.37, 0.09, nose_top(-0.37), 0.004),
            pontoon_section(s, -0.31, KEEL, TOP),
            pontoon_section(s, 0.44, KEEL, TOP),
            pontoon_section(s, STERN, 0.1, TOP - 0.018, 0.012),
        ], bevel=0.01))
    w = PONTOON[0] + 0.01
    parts += [
        loft('Deck', m['sand'], [(y, [(-w, bottom), (w, bottom), (w, top), (-w, top)]) for y, bottom, top in (
            (-0.42, 0.115, 0.135), (-0.355, 0.1, DECK), (0.45, 0.1, DECK), (0.465, 0.11, DECK - 0.012))], bevel=0.008),
        # the low spine from the cockpit back to the turret ring
        kit.hexahedron('Spine', m['sand'], (
            (-0.07, -0.21, DECK - 0.004), (0.07, -0.21, DECK - 0.004), (0.07, 0.02, DECK - 0.004), (-0.07, 0.02, DECK - 0.004),
            (-0.055, -0.18, DECK + 0.026), (0.055, -0.18, DECK + 0.026), (0.055, 0.0, DECK + 0.026), (-0.055, 0.0, DECK + 0.026)), bevel=0.006),
    ]
    return camo(kit.merge('HullShell', parts), root)


def hull_details(m):
    parts = [
        # the cockpit at the front of the deck: a light block, its sloped glass front
        kit.hexahedron('Cockpit', m['sand_light'], (
            (-0.07, -0.37, DECK - 0.006), (0.07, -0.37, DECK - 0.006), (0.07, -0.215, DECK - 0.006), (-0.07, -0.215, DECK - 0.006),
            (-0.058, -0.31, DECK + 0.052), (0.058, -0.31, DECK + 0.052), (0.058, -0.225, DECK + 0.052), (-0.058, -0.225, DECK + 0.052)),
            bevel=0.006),
        kit.hexahedron('Canopy', m['glass'], (
            (-0.056, -0.366, DECK + 0.003), (0.056, -0.366, DECK + 0.003), (0.056, -0.357, DECK - 0.002), (-0.056, -0.357, DECK - 0.002),
            (-0.047, -0.313, DECK + 0.05), (0.047, -0.313, DECK + 0.05), (0.047, -0.304, DECK + 0.045), (-0.047, -0.304, DECK + 0.045)), bevel=0),
        box('CanopyBar', m['steel'], (0.008, 0.06, 0.006), (0, -0.336, DECK + 0.03), bevel=0, rotation=(math.radians(-50), 0, 0)),
        *[box(f'SideWindow{s}', m['glass'], (0.006, 0.05, 0.022), (s * 0.066, -0.29, DECK + 0.026), bevel=0) for s in (-1, 1)],
        box('CockpitHatch', m['steel'], (0.06, 0.05, 0.008), (0, -0.262, DECK + 0.055), bevel=0.003),
        # the spine: a hatch, a vent, a box of electronics; a tow eye on the lip
        box('SpineHatch', m['sand_light'], (0.07, 0.06, 0.008), (0, -0.12, DECK + 0.028), bevel=0.003),
        *deck_grille('SpineVent', m['steel'], m['dark'], (0, -0.04, DECK + 0.028), (0.07, 0.05), 4),
        cylinder('TowEye', m['steel'], 0.012, 0.02, (0, -0.425, 0.125), rotation=(0, math.pi / 2, 0), segments=10, bevel=0),
        # the rear deck behind the turret: a stowage box, vents, a light
        box('Stowage', m['olive'], (0.1, 0.05, 0.032), (-0.05, 0.4, DECK + 0.016), bevel=0.008),
        *deck_grille('RearVent', m['steel'], m['dark'], (0.06, 0.4, DECK + 0.004), (0.07, 0.06), 4),
        *detail.lamp('DeckLight', m['dark'], m['lamp_red'], (0, 0.46, DECK - 0.01), (0, 1, 0), 0.01),
    ]
    for s in (-1, 1):
        xi, xo = s * PONTOON[0], s * PONTOON[1]
        mid = s * (PONTOON[0] + PONTOON[1]) / 2
        parts += [
            # the skirt under the pontoon, a rubbing strake along its flank
            kit.hexahedron(f'Skirt{s}', m['skirt'], (
                (xi + s * 0.012, -0.36, LIFT), (xo - s * 0.02, -0.36, LIFT), (xo - s * 0.02, 0.44, LIFT), (xi + s * 0.012, 0.44, LIFT),
                (xi + s * 0.008, -0.38, KEEL + 0.006), (xo - s * 0.012, -0.38, KEEL + 0.006), (xo - s * 0.012, 0.455, KEEL + 0.006),
                (xi + s * 0.008, 0.455, KEEL + 0.006)), bevel=0.006),
            box(f'Strake{s}', m['steel'], (0.012, 0.72, 0.014), (xo + s * 0.002, 0.06, KEEL + 0.045), bevel=0.003),
            # a house-colour panel on the flank behind the nose, a stripe on the nose plate
            box(f'FlankPanel{s}', m['remap'], (0.006, 0.26, 0.07), (flank(s, 0.168, 0.002), -0.17, 0.168), bevel=0.002,
                rotation=(0, -s * FLANK_TILT, 0)),
            box(f'NoseStripe{s}', m['remap'], (0.12, 0.03, 0.005), (mid, -0.4, nose_top(-0.4) + 0.003), bevel=0,
                rotation=(math.atan(0.5), 0, 0)),
            # panel seams over the top and down the flank, the crease at the nose plate
            *detail.seam(f'NoseCrease{s}', m['seam'], (xi + s * 0.004, -0.31, TOP + 0.001), (xo - s * 0.057, -0.31, TOP + 0.001)),
            *[p for k, y in enumerate((-0.16, 0.06, 0.27)) for p in detail.seam(
                f'TopSeam{s}{k}', m['seam'], (xi + s * 0.004, y, TOP + 0.001), (xo - s * 0.057, y, TOP + 0.001))],
            *detail.seam(f'RidgeSeam{s}', m['seam'], (mid + s * 0.035, -0.31, TOP + 0.001), (mid + s * 0.035, 0.27, TOP + 0.001)),
            *[p for k, y in enumerate((-0.03, 0.2)) for p in detail.seam(
                f'FlankSeam{s}{k}', m['seam'], (flank(s, KEEL + 0.05, 0.001), y, KEEL + 0.05), (flank(s, TOP - 0.04, 0.001), y, TOP - 0.04))],
            *detail.rivets(f'FlankRivets{s}', m['steel_light'], (flank(s, TOP - 0.05, 0.002), 0.0, TOP - 0.05),
                           (flank(s, TOP - 0.05, 0.002), 0.42, TOP - 0.05), 8, axis='X'),
            # intake grilles on the top, a hatch, the step at the inner edge
            *deck_grille(f'Intake{s}', m['steel'], m['dark'], (mid, -0.07, TOP + 0.003), (0.07, 0.1), 5),
            box(f'TopHatch{s}', m['sand_light'], (0.06, 0.06, 0.008), (mid, 0.17, TOP + 0.003), bevel=0.003),
            box(f'Kerb{s}', m['steel'], (0.01, 0.62, 0.012), (xi + s * 0.004, 0.08, TOP + 0.004), bevel=0.002),
            # headlights in the nose, a marker at the corner
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (mid - s * 0.03, NOSE - 0.002, 0.152), (0, -1, 0.3), 0.012),
            *detail.lamp(f'Marker{s}', m['dark'], m['lamp_amber'], (mid + s * 0.045, NOSE + 0.004, 0.153), (0, -1, 0.3), 0.007),
            # the stern: a louvred thrust nozzle with rudder vanes, a tail light
            box(f'Nozzle{s}', m['dark'], (0.13, 0.03, 0.1), (mid, STERN, 0.165), bevel=0.006),
            box(f'NozzleFrame{s}', m['steel'], (0.142, 0.022, 0.112), (mid, STERN - 0.008, 0.165), bevel=0.004),
            *[box(f'Vane{s}{k}', m['steel_light'], (0.006, 0.03, 0.09), (mid + (k - 1.5) * 0.03, STERN + 0.012, 0.165), bevel=0,
                  rotation=(0, 0, math.radians(15))) for k in range(4)],
            *detail.lamp(f'TailLight{s}', m['dark'], m['lamp_red'], (xo - s * 0.02, STERN + 0.004, 0.225), (0, 1, 0), 0.008),
        ]
    for k, (x, y, z) in enumerate(FANS):
        # the lift fan's duct: a house-colour lip, the dark well, a guard bar over it
        parts += [
            ring(f'Duct{k}', m['remap'], FAN_RADIUS + 0.002, FAN_RADIUS + 0.016, z - 0.004, z + 0.012, (x, y)),
            ring(f'DuctLip{k}', m['steel'], FAN_RADIUS, FAN_RADIUS + 0.006, z - 0.002, z + 0.015, (x, y)),
            cylinder(f'Well{k}', m['dark'], FAN_RADIUS + 0.002, 0.006, (x, y, z - 0.014), segments=20, bevel=0),
            beam(f'Guard{k}', m['steel_light'], (x, y - FAN_RADIUS - 0.004, z + 0.012), (x, y + FAN_RADIUS + 0.004, z + 0.012), 0.006),
        ]
    return kit.merge('HullDetails', parts)


def fan(m, k):
    """A lift fan in its duct turning about z; origin on its hub."""
    c = Vector(FANS[k]) - Vector((0, 0, 0.004))
    parts = [cylinder(f'FanHub{k}', m['steel_light'], 0.014, 0.012, c, segments=12)]
    for j in range(6):
        a = 2 * math.pi * j / 6
        d = Vector((math.cos(a), math.sin(a), 0))
        # pitched about its own length, then turned round the hub
        parts.append(box(f'FanBlade{k}{j}', m['steel'], (FAN_RADIUS - 0.014, 0.016, 0.003), c + d * (FAN_RADIUS / 2 + 0.006), bevel=0,
                         rotation=(0.45, 0, a)))
    return kit.merge(f'Fan{k}', parts, c)


def cushion(m):
    """The glowing air cushion: an oval under each pontoon, just peeking out round its
    skirt, and a fainter one under the deck."""
    parts = []
    for s in (-1, 1):
        x = s * (PONTOON[0] + PONTOON[1]) / 2
        for name, (w, l), z in (('Glow', (0.24, 0.86), LIFT - 0.008), ('Core', (0.16, 0.76), LIFT - 0.028)):
            disc = cylinder(f'Cushion{name}{s}', m['cushion'], 0.5, 0.003, (x, 0.04, z), segments=24, bevel=0)
            disc.scale = (w, l, 1)
            parts.append(disc)
    disc = cylinder('CushionMiddle', m['cushion'], 0.5, 0.003, (0, 0.02, LIFT - 0.018), segments=24, bevel=0)
    disc.scale = (0.2, 0.72, 1)
    parts.append(disc)
    return kit.merge('Cushion', parts, (0, 0, LIFT))


# --------------------------------------------------------------------------- launcher

def launcher(m, root, body):
    """The turret with the two launchers on the Cannon; returns (pods, flashes)."""
    turn = kit.parent(kit.empty('Turret', TURRET), body)
    top = 0.3
    y0, y1 = TURRET.y - 0.1, TURRET.y + 0.13
    kit.parent(camo(kit.merge('TurretShell', [kit.hexahedron('TurretShell', m['sand'], (
        (-0.088, y0, DECK + 0.012), (0.088, y0, DECK + 0.012), (0.088, y1, DECK + 0.012), (-0.088, y1, DECK + 0.012),
        (-0.072, y0 + 0.045, top), (0.072, y0 + 0.045, top), (0.072, y1 - 0.02, top), (-0.072, y1 - 0.02, top)), bevel=0.012)], TURRET),
        root), turn)
    kit.parent(kit.merge('TurretDetails', [
        cylinder('TurretRing', m['steel'], 0.112, 0.024, (0, TURRET.y, DECK + 0.008), segments=24),
        cylinder('TurretRingTop', m['steel_light'], 0.1, 0.006, (0, TURRET.y, DECK + 0.022), segments=24, bevel=0),
        # the target laser's eye in front, a sensor box and a hatch on the roof
        box('EyeHousing', m['steel'], (0.05, 0.03, 0.04), (0, y0 + 0.015, top - 0.045), bevel=0.006,
            rotation=(math.radians(-25), 0, 0)),
        *detail.lamp('Eye', m['dark'], m['laser'], (0, y0, top - 0.05), (0, -1, 0), 0.012),
        box('Sensor', m['steel'], (0.05, 0.05, 0.026), (-0.03, TURRET.y + 0.02, top + 0.013), bevel=0.006),
        box('SensorGlass', m['glass'], (0.034, 0.008, 0.014), (-0.03, TURRET.y - 0.006, top + 0.015), bevel=0.002),
        cylinder('Hatch', m['steel'], 0.026, 0.012, (0.03, TURRET.y + 0.05, top + 0.004), segments=14),
        *detail.seam('TurretSeam', m['seam'], (-0.072, TURRET.y - 0.02, top + 0.001), (0.072, TURRET.y - 0.02, top + 0.001)),
        # the launchers' trunnion through the cheeks, a whip antenna at the back
        cylinder('Trunnion', m['steel_light'], 0.022, 2 * POD_X - POD[0] + 0.01, LAUNCHER, rotation=(0, math.pi / 2, 0), segments=12),
        *[box(f'Cheek{s}', m['steel'], (0.02, 0.07, 0.07), (s * 0.08, LAUNCHER.y, LAUNCHER.z - 0.025), bevel=0.005) for s in (-1, 1)],
        cylinder('AntennaBase', m['dark'], 0.01, 0.02, (0.05, y1 - 0.03, top + 0.008), segments=8, bevel=0),
        beam('Antenna', m['steel'], (0.05, y1 - 0.03, top), (0.06, y1 + 0.02, top + 0.22), 0.005),
        box('AmmoFeed', m['steel'], (0.1, 0.04, 0.05), (0, y1 - 0.005, DECK + 0.05), bevel=0.006),
    ], TURRET), turn)

    pivot = kit.parent(kit.empty('Cannon', LAUNCHER), turn)
    width, height, length = POD
    pods, flashes = [], []
    for k, s in enumerate((-1, 1)):
        c = Vector((s * POD_X, LAUNCHER.y - 0.02, LAUNCHER.z + 0.01))
        front, back = c.y - length / 2 - 0.01, c.y + length / 2 - 0.01
        x0, x1 = c.x - width / 2, c.x + width / 2
        z0, z1 = c.z - height / 2, c.z + height / 2
        shell = camo(kit.merge(f'PodShell{k}', [kit.hexahedron(f'PodShell{k}', m['sand'], (
            (x0, front, z0), (x1, front, z0), (x1, back, z0 + 0.012), (x0, back, z0 + 0.012),
            (x0, front, z1), (x1, front, z1), (x1 - 0.004, back - 0.02, z1 - 0.006), (x0 + 0.004, back - 0.02, z1 - 0.006)),
            bevel=0.01)], c), root)
        pod = kit.parent(kit.empty(f'Pod{k}', c), pivot)
        kit.parent(shell, pod)
        parts = [
            box(f'PodFace{k}', m['steel'], (width - 0.01, 0.012, height - 0.01), (c.x, front - 0.004, c.z), bevel=0.004),
            box(f'PodBand{k}', m['remap'], (width + 0.008, 0.035, height + 0.008), (c.x, c.y + 0.06, c.z + 0.001), bevel=0.003),
            box(f'PodArm{k}', m['steel'], (POD_X - width / 2 - 0.07, 0.08, 0.034), (s * (0.07 + (POD_X - width / 2 - 0.07) / 2), LAUNCHER.y,
                                                                                 LAUNCHER.z), bevel=0.004),
            box(f'PodHatch{k}', m['sand_light'], (width - 0.04, 0.08, 0.006), (c.x, c.y - 0.05, z1 + 0.002), bevel=0.002),
            *detail.seam(f'PodSeam{k}', m['seam'], (x0 + 0.004, c.y + 0.01, z1 + 0.001), (x1 - 0.004, c.y + 0.01, z1 + 0.001)),
            *detail.rivets(f'PodRivets{k}', m['steel_light'], (c.x + s * (width / 2 + 0.002), c.y - 0.12, c.z - 0.03),
                           (c.x + s * (width / 2 + 0.002), c.y + 0.0, c.z - 0.03), 4, axis='X'),
        ]
        for i in range(4):
            for j in range(2):
                t = Vector((c.x + (i - 1.5) * 0.029, front - 0.006, c.z + (j - 0.5) * 0.042))
                parts += [cylinder(f'Tube{k}{i}{j}', m['dark'], 0.0125, 0.012, t, rotation=ALONG_Y, segments=10, bevel=0),
                          cylinder(f'Warhead{k}{i}{j}', m['warhead'], 0.0095, 0.018, t - Vector((0, 0.002, 0)), rotation=ALONG_Y,
                                   segments=10, bevel=0, radius2=0.003)]
        kit.parent(kit.merge(f'PodDetails{k}', parts, c), pod)
        tip = Vector((c.x, front - 0.04, c.z))
        flashes.append(kit.parent(nod.flash(m, f'Flash{k}', tip, 0.045), pivot))
        pods.append(pod)
    return pods, flashes


# --------------------------------------------------------------------------- clips

def clips(body, fans, glow, pods, flashes):
    one, hidden = Vector((1, 1, 1)), Vector((kit.HIDDEN,) * 3)
    n = kit.IDLE_END
    # Idle: bobbing on the cushion, glow breathing
    kit.keys(body, 'location', {f: Vector((0, 0, 0.008 * math.sin(2 * math.pi * f / n))) for f in range(0, n + 1, 3)}, 'LINEAR')
    kit.keys(body, 'rotation_euler', {f: Vector((0.01 * math.sin(2 * math.pi * f / n + 1), 0.008 * math.sin(4 * math.pi * f / n), 0))
                                      for f in range(0, n + 1, 3)}, 'LINEAR')
    kit.to_track(body, 'Idle')
    kit.keys(glow, 'scale', {f: Vector((1, 1, 1)) * (0.9 + 0.1 * math.sin(4 * math.pi * f / n) ** 2) for f in range(0, n + 1, 5)}, 'LINEAR')
    kit.to_track(glow, 'Idle')
    # Walk: gliding, leaning back, swaying, glow brighter (wider)
    w = WALK_FRAMES
    kit.keys(body, 'location', {f: Vector((0, 0, 0.012 + 0.006 * math.sin(2 * math.pi * f / w))) for f in range(0, w + 1, 2)}, 'LINEAR')
    kit.keys(body, 'rotation_euler', {f: Vector((0.035 + 0.01 * math.sin(2 * math.pi * f / w), 0.015 * math.sin(2 * math.pi * f / w + 1), 0))
                                      for f in range(0, w + 1, 2)}, 'LINEAR')
    kit.to_track(body, 'Walk')
    kit.keys(glow, 'scale', {f: Vector((1.06, 1.08, 1)) * (1.0 + 0.06 * math.sin(4 * math.pi * f / w) ** 2) for f in range(0, w + 1, 3)}, 'LINEAR')
    kit.to_track(glow, 'Walk')
    # the lift fans: slowly on the spot, racing while gliding
    for obj in fans:
        kit.keys(obj, 'rotation_euler', {f: Vector((0, 0, 2 * math.pi * f / n)) for f in range(0, n + 1, 2)}, 'LINEAR')
        kit.to_track(obj, 'Idle')
        kit.keys(obj, 'rotation_euler', {f: Vector((0, 0, 6 * math.pi * f / w)) for f in range(0, w + 1)}, 'LINEAR')
        kit.to_track(obj, 'Walk')
    # Fire: the left launcher, then the right one; each kicks back and flashes
    for k, (pod, flash) in enumerate(zip(pods, flashes)):
        rest = pod.location.copy()
        t = 6 * k
        kick = rest + Vector((0, 0.03, 0))
        kit.keys(pod, 'location', {0: rest, t: rest, t + 2: kick, t + 5: kick, t + 14: rest, FIRE_FRAMES: rest})
        kit.to_track(pod, 'Fire')
        frames = {0: hidden, t: Vector((1, 1, 1)), t + 2: Vector((1.3, 1.6, 1.3)), t + 4: hidden, FIRE_FRAMES: hidden}
        if t == 0:
            frames[0] = Vector((1, 1, 1))
        kit.keys(flash, 'scale', frames, 'CONSTANT')
        kit.to_track(flash, 'Fire')
        walker.hide([flash], n, 'Idle')
        walker.hide([flash], w, 'Walk')
        pod.location, flash.scale = rest, hidden
    body.location, body.rotation_euler, glow.scale = (0, 0, 0), (0, 0, 0), one
    for f in fans:
        f.rotation_euler = (0, 0, 0)


def build():
    root, body = nod.start('GDIHoverMLRS', 'HoverMLRS', WALK_SPEED)
    m = materials()
    kit.parent(hull(m, root), body)
    kit.parent(hull_details(m), body)
    fans = [kit.parent(fan(m, k), body) for k in range(len(FANS))]
    glow = kit.parent(cushion(m), body)
    pods, flashes = launcher(m, root, body)
    kit.bake_camo(512)
    clips(body, fans, glow, pods, flashes)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [8], 'Fire': [1, 7]}, scale=1.5, target=(0, 0, 0.22))
