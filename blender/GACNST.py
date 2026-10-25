"""
Tiberian Fallout – GDI construction yard (GACNST), after Tiberian Sun: the hall.

The deployed MCV (MCV.vehicle()): its rear half sinks into the slab, its front half
drives to the front of the grey end wall as the crane; the grey boom turns towards
the gate, rises and lets its hook down in front of it. Frame 0
of the Build clip shows exactly the MCV in the middle, so the game can swap the vehicle for
the yard.

A long hall along y on a grey concrete slab (foundation 3 × 3 cells, origin in the
middle), open at the front (-y, seen into from the lower left in the game). Its
cross-section follows the original (help/buildings/GDI/GACNST/Frame 1.svg): on the
left the roof rises round from the ground to a short, gently rising stretch up to the
ridge; from there it falls away in a straight slope to the right, with the box of
the ventilation shaft sitting on it; below that a short upright wall and two low
steps down to the ground. The shell is in the desert camouflage (baked), with bands
in the house colour (Remap) on the wall and the chimney: light ribs with grey
corrugated panels between them over the round part up to the ridge, the lamps along the ridge, three
fans in the slope, a thick chimney and a thin pipe on the back of the round part.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 3.3 s (deploy): the slab spreads, the right side (slope, shaft,
             wall and steps) rises, the ribs swing up over the round part one after
             another from the back, the panels spread between them, the back wall
             and the front frame close the hall, fans, lamps and chimney appear
    Idle     loop, 2 s: the fans turn, a light runs along the lamps
    Deliver  one-shot, 4.7 s (played when a structure is placed): the crane takes the
             next crate from the hall's gate, swings it over the hatch, the striped
             covers slide open, the crate goes down into it, the hatch closes

Run headless:

    Blender -b --factory-startup --python blender/GACNST.py

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z).
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import MCV as mcv  # noqa: E402 – the vehicle

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GACNST.glb')
BLEND = os.path.join(HERE, 'GACNST.blend')

BUILD_END = 112
# the MCV deploys in the middle of the foundation, facing the front (-y) as it drives;
# then its front half (the crane) drives to CRANE_SPOT in front of the grey end wall
# (the game drives the MCV to the middle and turns it to the front, see deploy() in
# app/lib/game/battlefield.ts)
CRANE_SPOT = Vector((0.6, -0.62, 0))
CRANE_PIVOT = Vector((-0.1, 0.0, 0.38))   # where the boom moves to on the crane (vehicle's space)
DELIVER_END = 140                    # frames of the Deliver clip
CRATE = 0.22                         # edge of a crate
CLAW = 0.18                          # from the claw's top to the tips of its fingers
REST_CABLE = 0.45                    # cable length while the crane waits
PICK = Vector((-0.62, -0.42, 0))     # the next crate, in the hall's gate (on the ground)


def boom_tip(slew, pitch):
    """End of the boom (yard space) for the crane's slew and pitch (degrees)."""
    turn = Euler((math.radians(pitch), 0, math.radians(slew))).to_matrix()
    return CRANE_SPOT + CRANE_PIVOT + turn @ Vector((0, -mcv.BOOM_LENGTH, 0))


def reach(target):
    """Slew and pitch (degrees) that put the boom's end straight above `target`."""
    way = target - (CRANE_SPOT + CRANE_PIVOT)
    way.z = 0
    slew = math.degrees(math.atan2(-way.x, way.y)) - 180   # boom points along -y at slew 0
    slew = (slew + 180) % 360 - 180
    pitch = -math.degrees(math.acos(min(1.0, way.length / mcv.BOOM_LENGTH)))
    return slew, pitch


# the hatch, well in front of the gate (clear of the next crate); the crane rests with
# its boom's end right above it
HATCH = Vector((-0.45, -1.0, 0))
BOOM_SLEW, BOOM_PITCH = reach(HATCH)
IDLE_END = kit.IDLE_END
HIDDEN = kit.HIDDEN

SLAB = 0.04
FRONT, BACK = -0.45, 1.4              # ends of the hall (y); the front is open (room for the crane in front)
RIBS = [FRONT + i * (BACK - FRONT) / 5 for i in range(6)]


def P(x, z):
    return Vector((x, 0, z))


# the cross-section (x, z), after the sketch, angles smoothed
FOOT = P(-1.4, 0)                     # left foot of the round part
SHOULDER = P(-0.42, 1.0)              # the round part ends here (its top)
RIDGE = P(-0.08, 1.1)                 # the highest point
SLOPE = [RIDGE, P(0.2, 0.86), P(0.74, 0.5)]   # the roof falls away to the right
WALL_TOP, WALL_X = P(0.8, 0.46), 0.8  # short upright wall below the slope
WALL_FOOT = P(0.8, 0.31)
STEPS = [WALL_FOOT, P(1.1, 0.21), P(1.1, 0.145), P(1.4, 0.07), P(1.4, 0)]   # two low steps
# the ventilation shaft on the slope: a grey hood sticking out, over a house-colour
# body with the long dark slot in its front
HOOD = [P(0.3, 0.795), P(0.36, 0.875), P(0.64, 0.875), P(0.75, 0.81), P(0.77, 0.73), P(0.6, 0.73)]
SHAFT_BODY = [P(0.42, 0.71), P(0.42, 0.74), P(0.72, 0.74), P(0.72, 0.522)]


def round_part(grow=0.0, steps=16):
    """The round part from the foot up to the shoulder: a quarter ellipse."""
    ax, az = SHOULDER.x - FOOT.x + grow, SHOULDER.z + grow
    return [P(SHOULDER.x - ax * math.cos(math.pi / 2 * k / steps), az * math.sin(math.pi / 2 * k / steps)) for k in range(steps + 1)]


def roof(grow=0.0):
    """The whole roof line from the left foot over the ridge down to the wall."""
    return round_part(grow) + [RIDGE + P(0, grow), *[p + P(grow * 0.6, grow * 0.8) for p in SLOPE[1:]], WALL_TOP + P(grow, 0)]


def outline():
    """The closed cross-section of the hall (for the back wall)."""
    return roof() + [WALL_FOOT, *STEPS[1:]]


box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = mcv.materials()
    m.update({
        'crate': material('Crate', srgb('#80603a'), 0.85),
        'crate_frame': material('CrateFrame', srgb('#4f3a22'), 0.9),
        'panel': material('RoofPanel', srgb('#8b8d88'), 0.55, 0.6),
        'slab': material('Slab', srgb('#9a9a96'), 0.9),
        'inside': material('Inside', srgb('#55575a'), 0.85, 0.2),
    })
    return m


def attach(child, parent_obj, location=(0, 0, 0), rotation=None):
    child.parent = parent_obj
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.location = location
    if rotation is not None:
        child.rotation_euler = rotation
    return child


MIDDLE = Vector((-0.2, 0.35))
ROOT = [None]  # the model's root, the space the camouflage is laid out in (set in build)  # a point inside the hall's cross-section (x, z)


def strip(name, mat, points, y0, y1, outward=True):
    """A surface along y from y0 to y1 through a polyline of (x, z) points, its faces
    pointing away from (or towards) the inside of the hall."""
    def build(bm):
        a = [bm.verts.new((p.x, y0, p.z)) for p in points]
        b = [bm.verts.new((p.x, y1, p.z)) for p in points]
        for k in range(len(points) - 1):
            bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))

    obj = kit.mesh_object(name, build)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        away = Vector((poly.center.x, poly.center.z)) - MIDDLE
        if (Vector((poly.normal.x, poly.normal.z)).dot(away) > 0) != outward:
            poly.flip()
    return obj


def prism(name, mat, points, y0, y1, bevel=0.0):
    """A solid with the (x, z) polygon `points` as its cross-section, from y0 to y1."""
    def build(bm):
        a = [bm.verts.new((p.x, y0, p.z)) for p in points]
        b = [bm.verts.new((p.x, y1, p.z)) for p in points]
        bm.faces.new(a)
        bm.faces.new(b)
        for k in range(len(points)):
            j = (k + 1) % len(points)
            bm.faces.new((a[k], a[j], b[j], b[k]))

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def camo(obj, root):
    """Gives an object (one material) the baked desert camouflage, laid out in the
    space of `root` so the pattern runs on across the parts."""
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def normal_of(a, b):
    """Outward normal (x, z) of the roof segment a → b (the roof runs left to right)."""
    d = (b - a).normalized()
    n = Vector((-d.z, 0, d.x))
    return n if n.z >= 0 else -n


# --------------------------------------------------------------------------- parts

def slab(m):
    """The dark concrete slab (like under the barracks and the power plant), its front corners chamfered (the back ones are
    square: the hall stands right up to them)."""
    half, cut = 1.47, 0.42
    outline = [(-half + cut, -half), (half - cut, -half), (half, -half + cut), (half, half),
               (-half, half), (-half, -half + cut)]

    def build(bm):
        low = [bm.verts.new((x, y, 0)) for x, y in outline]
        top = [bm.verts.new((x * 0.985, y * 0.985, SLAB)) for x, y in outline]
        bm.faces.new(low)
        bm.faces.new(top)
        for k in range(len(outline)):
            j = (k + 1) % len(outline)
            bm.faces.new((low[k], low[j], top[j], top[k]))

    return kit.merge('Slab', [kit.finish(kit.mesh_object('Slab', build), m['concrete_dark'], 0.008)])


def right_side(m, root):
    """The right side of the hall: the slope from the ridge down, the shaft on it, the
    upright wall and the two steps. Returns (camouflaged shell, camouflaged shaft body,
    details)."""
    length = BACK - FRONT
    mid = (BACK + FRONT) / 2
    body = [RIDGE, *SLOPE[1:], WALL_TOP, WALL_FOOT, *STEPS[1:], P(RIDGE.x, 0)]
    shell = camo(kit.merge('RightSide', [prism('RightSide', m['sand'], body, FRONT, BACK)]), root)
    # the shaft: a body with the dark slot in its front, under a grey hood with
    # corrugation across it
    shaft = camo(kit.merge('ShaftBody', [prism('ShaftBody', m['sand'], SHAFT_BODY, FRONT + 0.22, BACK - 0.12, bevel=0.006)]), root)
    parts = [prism('Hood', m['panel'], HOOD, FRONT + 0.18, BACK - 0.08, bevel=0.01)]
    slot_len = length - 0.56
    parts.append(box('Shaft', m['dark'], (0.02, slot_len, 0.1), (SHAFT_BODY[2].x + 0.004, mid + 0.05, 0.665), bevel=0))
    for k in range(5):
        parts.append(box(f'Louvre{k}', m['steel'], (0.012, slot_len - 0.04, 0.006), (SHAFT_BODY[2].x + 0.012, mid + 0.05, 0.63 + k * 0.018), bevel=0))
    for k in range(22):   # corrugation across the hood
        y = FRONT + 0.24 + k * (length - 0.4) / 21
        parts.append(beam(f'HoodRib{k}', m['steel'], HOOD[1] + Vector((0, y, 0.006)), HOOD[2] + Vector((0, y, 0.006)), 0.01, 0.006))
        parts.append(beam(f'HoodRibFront{k}', m['steel'], HOOD[2] + Vector((0, y, 0.006)), HOOD[3] + Vector((0.004, y, 0.004)), 0.01, 0.006))
    # grey edges along the two steps
    for k, (a, b) in enumerate(((STEPS[0], STEPS[1]), (STEPS[2], STEPS[3]))):
        tread = (a + b) / 2
        angle = -math.atan2(a.z - b.z, b.x - a.x)
        parts.append(box(f'Tread{k}', m['panel'], (math.hypot(b.x - a.x, b.z - a.z) + 0.02, length, 0.025), tread + Vector((0, mid, 0.012)),
                         bevel=0.004, rotation=(0, -angle, 0)))
    # ridge cap and the steps' gratings
    parts.append(box('RidgeCap', m['panel'], (0.08, length + 0.02, 0.03), (RIDGE.x, mid, RIDGE.z + 0.01), bevel=0.006))
    # the front end of the right side is plain grey (a plate over the camouflaged shell)
    parts.append(prism('FrontEnd', m['panel'], body, FRONT - 0.012, FRONT - 0.002))
    parts.append(prism('ShaftFrontEnd', m['panel'], SHAFT_BODY, FRONT + 0.208, FRONT + 0.218))
    # a band in the house colour, so the yard shows whose it is
    parts.append(box('WallBand', m['remap'], (0.012, length, 0.04), (WALL_X + 0.006, mid, WALL_TOP.z - 0.05), bevel=0))
    return shell, shaft, kit.merge('RightSideDetails', parts)


def rib(m, i, y):
    """A rib over the round part and on to the ridge; origin on its left foot (it swings
    up about y)."""
    points = round_part(0.02, steps=12) + [RIDGE + P(0, 0.02)]
    parts = [beam(f'Rib{i}_{k}', m['sand_light'], a + Vector((0, y, 0)), b + Vector((0, y, 0)), 0.05, 0.045)
             for k, (a, b) in enumerate(zip(points, points[1:]))]
    parts.append(box(f'RibFoot{i}', m['steel'], (0.1, 0.1, 0.04), FOOT + Vector((0, y, SLAB + 0.02)), bevel=0.005))
    return kit.merge(f'Rib{i}', parts, FOOT + Vector((0, y, 0)))


def bay(m, i, y0, y1):
    """The round part between two ribs: grey corrugated panels from the foot up to the
    ridge's rail, dark inside; origin on the back rib (it spreads forwards from there)."""
    panel = strip(f'Panel{i}', m['panel'], round_part() + [RIDGE], y0, y1)
    ridges = []
    for k in range(1, 4):   # corrugation: low ridges along the panel
        line = round_part(0.008) + [RIDGE + P(0, 0.008)]
        yy = y0 + (y1 - y0) * k / 4
        ridges += [beam(f'Corrugation{i}_{k}_{j}', m['panel'], a + Vector((0, yy, 0)), b + Vector((0, yy, 0)), 0.012, 0.012)
                   for j, (a, b) in enumerate(zip(line, line[1:]))]
    outer = kit.merge(f'Bay{i}', [panel, *ridges], Vector((0, y1, 0)))
    inner = kit.merge(f'BayInside{i}', [strip(f'BayInside{i}', m['inside'], round_part(-0.03) + [RIDGE - P(0, 0.03)], y0, y1, outward=False)],
                      Vector((0, y1, 0)))
    return outer, inner


def front_frame(m):
    """The thick frame round the open front end (the gate), in the house colour, and its foot."""
    points = roof(0.03)
    parts = [beam(f'Frame{k}', m['remap'], a + Vector((0, FRONT, 0)), b + Vector((0, FRONT, 0)), 0.1, 0.09)
             for k, (a, b) in enumerate(zip(points, points[1:]))]
    frame = kit.merge('FrontFrame', parts, Vector((0, FRONT, 0)))
    foot = kit.merge('FrameFoot', [box('FrameFoot', m['steel'], (0.14, 0.12, 0.08), FOOT + Vector((0.03, FRONT, SLAB + 0.04)), bevel=0.006)])
    return frame, foot


def back_wall(m):
    """Closes the back end (camouflaged), with a door; origin on the ground (it grows up)."""
    wall = camo(kit.merge('BackWall', [prism('BackWall', m['sand'], outline(), BACK, BACK + 0.05)], Vector((0, BACK, 0))), ROOT[0])
    door = kit.merge('BackDoor', [box('BackDoor', m['dark'], (0.45, 0.04, 0.32), (-0.6, BACK + 0.05, SLAB + 0.16), bevel=0.004)])
    return wall, door


def fan(m, k, y):
    """A big round fan high in the slope: a dark octagonal ring with eight spokes;
    returns (housing, blades): the blades turn about the housing's z axis."""
    a, b = SLOPE[0], SLOPE[1]
    normal = normal_of(a, b)
    centre = a.lerp(b, 0.5) + Vector((0, y, 0)) + normal * 0.012
    housing = kit.merge(f'Fan{k}', [
        cylinder(f'FanRing{k}', m['dark'], 0.13, 0.045, (0, 0, 0), segments=8, bevel=0.008),
        cylinder(f'FanRim{k}', m['panel'], 0.105, 0.012, (0, 0, 0.022), segments=24, bevel=0),
        cylinder(f'FanHole{k}', m['dark'], 0.095, 0.01, (0, 0, 0.026), segments=24, bevel=0),
    ])
    housing.rotation_euler = (0, 0, math.pi / 8)
    kit.bake_modifiers(housing)
    housing.location = centre
    housing.rotation_mode = 'QUATERNION'
    housing.rotation_quaternion = normal.to_track_quat('Z', 'Y')
    blades = [cylinder(f'FanHub{k}', m['steel_light'], 0.024, 0.02, (0, 0, 0), segments=12, bevel=0)]
    for j in range(8):
        c = math.pi / 4 * j
        blades.append(beam(f'Spoke{k}{j}', m['steel_light'], (math.cos(c) * 0.02, math.sin(c) * 0.02, 0),
                           (math.cos(c) * 0.09, math.sin(c) * 0.09, 0), 0.014, 0.006))
    blades = kit.merge(f'FanBlades{k}', blades)
    attach(blades, housing, (0, 0, 0.03))
    return housing, blades


def chimney(m):
    """A thick chimney and a thin pipe on the back of the round part; origin at the foot."""
    line = round_part()
    foot = line[11] + Vector((0, BACK - 0.3, -0.03))
    pipe_foot = line[9] + Vector((0, BACK - 0.45, -0.03))
    parts = [
        cylinder('Chimney', m['steel_light'], 0.075, 0.32, foot + Vector((0, 0, 0.16)), segments=20),
        cylinder('ChimneyBand', m['remap'], 0.078, 0.05, foot + Vector((0, 0, 0.22)), segments=20, bevel=0),
        cylinder('ChimneyCap', m['panel'], 0.085, 0.04, foot + Vector((0, 0, 0.32)), segments=20),
        cylinder('ChimneyHole', m['dark'], 0.06, 0.01, foot + Vector((0, 0, 0.342)), segments=20, bevel=0),
        cylinder('Pipe', m['steel_light'], 0.025, 0.36, pipe_foot + Vector((0, 0, 0.18)), segments=12),
        cylinder('PipeCap', m['panel'], 0.032, 0.03, pipe_foot + Vector((0, 0, 0.36)), segments=12),
        # antennas on top
        beam('Antenna', m['steel'], foot + Vector((0.03, 0, 0.34)), foot + Vector((0.03, 0, 0.62)), 0.008),
        beam('PipeAntenna', m['steel'], pipe_foot + Vector((0, 0, 0.37)), pipe_foot + Vector((0, 0, 0.55)), 0.006),
    ]
    return kit.merge('Chimney', parts, foot)


def crane_hook(m):
    """Hook block hanging under the boom: cable (origin on top, 1 long downwards) and
    the claw (origin on top)."""
    cable = kit.merge('Cable', [cylinder('Cable', m['steel'], 0.008, 1.0, (0, 0, -0.5), segments=8, bevel=0)])
    claw = [box('ClawBlock', m['steel_light'], (0.08, 0.08, 0.06), (0, 0, -0.03), bevel=0.006)]
    for j in range(3):
        a = 2 * math.pi * j / 3
        d = Vector((math.cos(a), math.sin(a), 0))
        claw.append(beam(f'ClawFinger{j}', m['steel'], d * 0.03 + Vector((0, 0, -0.05)), d * 0.07 + Vector((0, 0, -0.13)), 0.014))
        claw.append(beam(f'ClawTip{j}', m['steel'], d * 0.07 + Vector((0, 0, -0.13)), d * 0.04 + Vector((0, 0, -0.18)), 0.012))
    return cable, kit.merge('Claw', claw)


def crate(m, name, centre):
    """A wooden crate: boards with darker battens along the edges and across the sides."""
    h = CRATE / 2
    parts = [box(f'{name}Box', m['crate'], (CRATE, CRATE, CRATE), centre, bevel=0.006)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(box(f'{name}Post{sx}{sy}', m['crate_frame'], (0.028, 0.028, CRATE + 0.004), centre + Vector((sx * h, sy * h, 0)), bevel=0))
        for sz in (-1, 1):
            parts.append(box(f'{name}EdgeX{sx}{sz}', m['crate_frame'], (0.028, CRATE + 0.004, 0.028), centre + Vector((sx * h, 0, sz * h)), bevel=0))
            parts.append(box(f'{name}EdgeY{sx}{sz}', m['crate_frame'], (CRATE + 0.004, 0.028, 0.028), centre + Vector((0, sx * h, sz * h)), bevel=0))
    for sx in (-1, 1):   # a batten across each side
        parts.append(box(f'{name}CrossX{sx}', m['crate_frame'], (0.006, 0.018, CRATE), centre + Vector((sx * (h + 0.002), 0, 0)), bevel=0))
        parts.append(box(f'{name}CrossY{sx}', m['crate_frame'], (0.018, 0.006, CRATE), centre + Vector((0, sx * (h + 0.002), 0)), bevel=0))
    return kit.merge(name, parts, centre)


def crate_pile(m):
    """Crates stacked in the hall, under the round roof."""
    stacks = ((-1.0, -0.1, 2), (-0.78, 0.14, 3), (-0.45, -0.05, 1), (-1.05, 0.42, 2), (-0.55, 0.45, 2),
              (-0.88, 0.75, 1), (-0.35, 0.95, 2), (-1.0, 1.05, 1))
    crates = []
    for k, (x, y, n) in enumerate(stacks):
        for level in range(n):
            crates.append(crate(m, f'Crate{k}_{level}', Vector((x, y, SLAB + CRATE / 2 + level * CRATE))))
    return kit.merge('CratePile', crates)


def hatch(m, centre):
    """The hatch under the crane: a frame with yellow and black stripes round a dark
    hole, and two covers in the same stripes that slide apart (x). Returns (frame,
    covers); the covers' origins are at the middle of the hatch."""
    size = 0.44
    top = SLAB + 0.004
    parts = [box('HatchHole', m['dark'], (size, size, 0.004), centre + Vector((0, 0, top)), bevel=0)]
    n = 8
    for side in range(4):   # the frame's four sides, striped
        for k in range(n):
            t = -size / 2 - 0.02 + (k + 0.5) * (size + 0.04) / n
            colour = m['hazard'] if k % 2 == 0 else m['dark']
            if side < 2:
                p = centre + Vector((t, (size / 2 + 0.01) * (1 if side else -1), top + 0.004))
                parts.append(box(f'HatchFrame{side}{k}', colour, ((size + 0.04) / n, 0.02, 0.008), p, bevel=0))
            else:
                p = centre + Vector(((size / 2 + 0.01) * (1 if side == 3 else -1), t, top + 0.004))
                parts.append(box(f'HatchFrame{side}{k}', colour, (0.02, (size + 0.04) / n, 0.008), p, bevel=0))
    frame = kit.merge('HatchFrame', parts, centre)
    covers = []
    for s in (-1, 1):
        plate = [box(f'Cover{s}', m['steel'], (size / 2, size, 0.012), centre + Vector((s * size / 4, 0, top + 0.01)), bevel=0.002)]
        for k in range(5):   # diagonal-looking stripes: alternating bands across the cover
            if k % 2 == 0:
                plate.append(box(f'CoverStripe{s}{k}', m['hazard'], (size / 2 - 0.01, size / 5 - 0.01, 0.002),
                                 centre + Vector((s * size / 4, -size / 2 + (k + 0.5) * size / 5, top + 0.017)), bevel=0))
        covers.append(kit.merge(f'HatchCover{s}', plate, centre))
    return frame, covers


# --------------------------------------------------------------------------- model

def build():
    kit.COLLECTION = 'GDIConstructionYard'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = BUILD_END + 12
    scene.frame_current = 0  # parenting reads the evaluated pose: parent before keying

    m = materials()
    root = kit.empty('GDIConstructionYard')
    ROOT[0] = root
    keys, pop = kit.keys, kit.pop
    rad = math.radians
    one, hidden = Vector((1, 1, 1)), Vector((HIDDEN,) * 3)

    # ---- the vehicle (exactly the MCV) at its dock
    vehicle = kit.parent(kit.empty('Vehicle'), root)
    parts = mcv.vehicle(m, vehicle)   # camouflage laid out on the vehicle, like on the MCV itself
    rear = kit.parent(kit.empty('VehicleRear'), vehicle)
    for obj in (*parts['hull'], *parts['details'], parts['boom'], parts['beacon'], *parts['wheels']):
        kit.parent(obj, vehicle)
    for obj in parts['rear']:
        kit.parent(obj, rear)
    kit.parent(parts['boom_details'], parts['boom'])
    # the front half drives forward to its spot in front of the grey end wall
    keys(vehicle, 'location', {0: Vector((0, 0, 0)), 4: Vector((0, 0, 0)), 24: CRANE_SPOT.copy()})

    # ---- the slab spreads from the middle
    floor = kit.parent(slab(m), root)
    keys(floor, 'scale', {0: hidden, 1: Vector((0.15, 0.15, 1)), 14: Vector((1.02, 1.02, 1)), 17: one})

    # ---- the right side (slope, shaft, wall, steps) rises out of the ground
    side = kit.parent(kit.empty('RightSideGroup'), root)
    for obj in right_side(m, root):
        kit.parent(obj, side)
    keys(side, 'location', {0: Vector((0, 0, -1.2)), 8: Vector((0, 0, -1.2)), 26: Vector((0, 0, 0.012)), 29: Vector((0, 0, 0))})

    # ---- the ribs swing up over the round part from the left, one after another from
    # the back (folded: the rib lies flat to the left of the hall, partly below ground)
    chord = math.degrees(math.atan2(RIDGE.z, RIDGE.x - FOOT.x))
    fold = chord - 180   # turned about y until the chord points left (-x)
    ribs = [kit.parent(rib(m, i, y), root) for i, y in enumerate(RIBS)]
    starts = {}
    for order, i in enumerate(reversed(range(len(RIBS)))):
        start = 22 + order * 6
        starts[i] = start
        obj = ribs[i]
        keys(obj, 'scale', {0: hidden, start - 1: hidden, start: one}, 'CONSTANT')
        keys(obj, 'rotation_euler', {0: Vector((0, rad(fold), 0)), start: Vector((0, rad(fold), 0)),
                                     start + 11: Vector((0, rad(-3), 0)), start + 14: Vector((0, 0, 0))})
    for i in range(len(RIBS) - 1):
        outer, inner = bay(m, i, RIBS[i], RIBS[i + 1])
        kit.parent(outer, root)
        kit.parent(inner, outer)
        start = starts[i] + 12
        keys(outer, 'scale', {0: hidden, start - 1: hidden, start: Vector((1, HIDDEN, 1)), start + 9: one})

    # ---- the back wall and the front frame close the hall
    back, door = back_wall(m)
    kit.parent(back, root)
    kit.parent(door, back)
    keys(back, 'scale', {0: hidden, 21: hidden, 22: Vector((1, 1, HIDDEN)), 34: one})
    frame, frame_foot = front_frame(m)
    kit.parent(frame, root)
    kit.parent(frame_foot, frame)
    keys(frame, 'scale', {0: hidden, 63: hidden, 64: Vector((1, 1, HIDDEN)), 74: Vector((1, 1, 1.04)), 77: one})

    # ---- fans, lamps along the ridge, chimney
    fans = []
    for k, y in enumerate((0.03, 0.48, 0.93)):
        housing, blades = fan(m, k, y)
        kit.parent(housing, root)
        pop(housing, 74 + k * 3, 7)
        fans.append(blades)
    lamps = []
    for k, y in enumerate(RIBS):
        y = min(max(y, FRONT + 0.08), BACK - 0.08)
        p = RIDGE + Vector((0.07, y, 0.0))
        housing, light = kit.beacon(f'Lamp{k}', m, p, 'amber')
        housing = kit.merge(f'Lamp{k}', [housing], p)
        kit.parent(housing, root)
        kit.parent(light, housing)
        pop(housing, 80 + k * 2, 6)
        lamps.append(light)
    stack = kit.parent(chimney(m), root)
    kit.grow(stack, 82, 12, 2)

    # ---- only the front half of the vehicle stays as the crane: the rear half sinks into
    # the slab, the boom slides forward onto the crane, rises and lets its hook down
    keys(rear, 'location', {0: Vector((0, 0, 0)), 4: Vector((0, 0, 0)), 22: Vector((0, 0, -0.45))})
    keys(rear, 'scale', {0: one, 21: one, 22: hidden}, 'CONSTANT')
    turntable = kit.merge('CraneTurntable', [cylinder('CraneTurntable', m['steel'], 0.1, 0.05, CRANE_PIVOT + Vector((0, 0.02, -0.06)), segments=20)],
                          CRANE_PIVOT)
    attach(turntable, vehicle, CRANE_PIVOT)
    pop(turntable, 16, 6)
    boom = parts['boom']
    # the boom hangs in a mount at its pivot on the crane; Deliver turns the mount (the
    # turn relative to the boom's resting pose), Build moves the boom itself
    mount = attach(kit.empty('CraneMount'), vehicle, CRANE_PIVOT)   # (the vehicle is keyed already: no kit.parent)
    mount.rotation_mode = 'QUATERNION'
    kit.parent(boom, mount)
    raised = Vector((rad(BOOM_PITCH), 0, rad(BOOM_SLEW)))
    keys(boom, 'location', {0: mcv.BOOM_PIVOT - CRANE_PIVOT, 4: mcv.BOOM_PIVOT - CRANE_PIVOT, 22: Vector((0, 0, 0))})  # with the rear half
    # it turns towards the gate as soon as it stands (so it lies on the slab, not beyond
    # it), and rises when the hall is up
    keys(boom, 'rotation_euler', {0: Vector((0, 0, 0)), 20: Vector((0, 0, 0)), 34: Vector((0, 0, rad(BOOM_SLEW))),
                                  92: Vector((0, 0, rad(BOOM_SLEW))), 106: raised + Vector((rad(-4), 0, 0)), BUILD_END - 2: raised})
    rest_tip = boom_tip(BOOM_SLEW, BOOM_PITCH)
    hook = kit.empty('Hook', rest_tip)            # at the boom's end; Build shows it
    kit.parent(hook, root)
    hook_move = kit.parent(kit.empty('HookMove', rest_tip), hook)   # Deliver moves it with the boom
    cable, claw = crane_hook(m)
    attach(cable, hook_move)
    attach(claw, hook_move, (0, 0, -REST_CABLE))
    cable.scale = (1, 1, REST_CABLE)
    keys(hook, 'scale', {0: hidden, 103: hidden, BUILD_END: one})

    # ---- crates in the hall, the next one in the gate; the hatch under the crane
    pile = kit.parent(crate_pile(m), root)
    pop(pile, 78, 8)
    next_mount = kit.parent(kit.empty('NextCrateMount', PICK), root)
    next_crate = crate(m, 'NextCrate', PICK + Vector((0, 0, SLAB + CRATE / 2)))
    kit.parent(next_crate, next_mount)
    pop(next_mount, 84, 6)
    hatch_at = Vector((rest_tip.x, rest_tip.y, 0))
    hatch_frame, covers = hatch(m, hatch_at)
    kit.parent(hatch_frame, floor)
    for cover in covers:
        kit.parent(cover, floor)
    carried = kit.parent(crate(m, 'CarriedCrate', Vector((0, 0, 0))), root)
    carried.scale = hidden

    # ---- clips
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    for k, blades in enumerate(fans):  # an eighth of a turn looks the same: eight spokes
        keys(blades, 'rotation_euler', {f: Vector((0, 0, (2 * math.pi * 2 + math.pi / 4) * f / IDLE_END * (1 if k % 2 else -1)))
                                        for f in range(0, IDLE_END + 1, 2)}, 'LINEAR')
        kit.to_track(blades, 'Idle')
    for k, light in enumerate(lamps):   # a light running along the lamps, front to back
        kit.blink(light, kit.flashes((k * 5, 5), (30 + k * 5, 5)))
        kit.to_track(light, 'Idle')
    kit.blink(parts['beacon'], kit.flashes((0, 10), (30, 10)))
    kit.to_track(parts['beacon'], 'Idle')

    deliver(mount, raised, hook_move, rest_tip, cable, claw, carried, next_crate, covers, hatch_at)
    return len(kit.collection().objects)


def deliver(mount, raised, hook_move, rest_tip, cable, claw, carried, next_crate, covers, hatch_at):
    """The Deliver clip: the crane takes the next crate from the gate, swings it over
    the hatch, the hatch slides open, the crate is let down into it, the hatch closes."""
    rest = (BOOM_SLEW, BOOM_PITCH)
    pick = reach(PICK)
    q_rest = Euler(raised).to_quaternion()

    def ease(t):
        t = min(1.0, max(0.0, t))
        return t * t * (3 - 2 * t)

    def span(f, a, b):
        return ease((f - a) / (b - a))

    pick_top = SLAB + CRATE                                     # top of the crate in the gate
    pick_cable = boom_tip(*pick).z - CLAW - pick_top
    lift_cable = 0.25
    sink = REST_CABLE + 0.75                                    # the crate goes deep into the hole

    def pose(f):
        if f < 24:
            t = span(f, 0, 24)
            boom = (rest[0] + (pick[0] - rest[0]) * t, rest[1] + (pick[1] - rest[1]) * t)
            cable_len = REST_CABLE + (pick_cable - REST_CABLE) * t
        elif f < 52:
            boom = pick
            cable_len = pick_cable if f < 40 else pick_cable + (lift_cable - pick_cable) * span(f, 40, 52)
            if f < 36:
                cable_len = pick_cable
        elif f < 80:
            t = span(f, 52, 80)
            boom = (pick[0] + (rest[0] - pick[0]) * t, pick[1] + (rest[1] - pick[1]) * t)
            cable_len = lift_cable + (REST_CABLE - lift_cable) * t
        else:
            boom = rest
            if f < 92:
                cable_len = REST_CABLE
            elif f < 114:
                cable_len = REST_CABLE + (sink - REST_CABLE) * span(f, 92, 112)
            else:
                cable_len = sink + (REST_CABLE - sink) * span(f, 116, 132)
        carrying = 36 <= f < 114
        opening = span(f, 80, 92) if f < 118 else 1 - span(f, 118, 132)
        return boom, cable_len, carrying, opening

    prefs = bpy.context.preferences.edit
    prefs.keyframe_new_interpolation_type = 'LINEAR'
    for obj in (mount, hook_move, cable, claw, carried, next_crate, *covers):
        obj.animation_data_create().action = bpy.data.actions.new(f'Deliver_{obj.name}')
    hidden, one = Vector((HIDDEN,) * 3), Vector((1, 1, 1))
    previous = None
    for f in range(DELIVER_END + 1):
        (slew, pitch), cable_len, carrying, opening = pose(f)
        q = Euler((math.radians(pitch), 0, math.radians(slew))).to_quaternion() @ q_rest.inverted()
        if previous is not None and previous.dot(q) < 0:
            q.negate()
        previous = q
        mount.rotation_quaternion = q
        mount.keyframe_insert('rotation_quaternion', frame=f)
        tip = boom_tip(slew, pitch)
        hook_move.location = tip - rest_tip
        hook_move.keyframe_insert('location', frame=f)
        cable.scale = (1, 1, cable_len)
        cable.keyframe_insert('scale', frame=f)
        claw.location = (0, 0, -cable_len)
        claw.keyframe_insert('location', frame=f)
        carried.location = tip - Vector((0, 0, cable_len + CLAW + CRATE / 2))
        carried.scale = one if carrying else hidden
        carried.keyframe_insert('location', frame=f)
        carried.keyframe_insert('scale', frame=f)
        # the crate in the gate is the one taken; a new one is there again at the end
        next_crate.scale = hidden if 36 <= f < 134 else one
        next_crate.keyframe_insert('scale', frame=f)
        for s, cover in zip((-1, 1), covers):
            cover.location = hatch_at + Vector((s * 0.23 * opening, 0, 0.008 * opening))
            cover.keyframe_insert('location', frame=f)
    for obj in (mount, hook_move, cable, claw, carried, next_crate, *covers):
        kit.to_track(obj, 'Deliver')


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(512)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)


if __name__ == '__main__' and bpy.app.background:
    main()
