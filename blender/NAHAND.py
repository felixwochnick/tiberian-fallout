"""
Tiberian Fallout – Hand of Nod (NAHAND), Nod's barracks, after Tiberian Sun.

A giant black hand lying flat on the ground, palm down (foundation 3 × 2 cells): its
four long fingers reach out to the right (+X) and claw into the ground, red rings at
their joints, red contour lines along their edges; the thumb grips the ground at the
front (-Y). From the wrist a wide, low sleeve sweeps back to the left and runs out in a
sharp, curved point at the front left – a cowl striped in red, black and dull khaki,
its rim red. A thin black stepped spire stands at the back of the hand, a blue light
sparkles on the back of the hand by the wrist (the original's NAHAND_A), the spire's
tip blinks (NAHAND_B). The soldiers come out of a low doorway in the front of the
wrist, between the sleeve and the thumb.

Nodes the game uses
    Exit    an empty on the ground before the doorway; its -Y axis points away from
            the building (the way the soldiers walk out)

Materials (see nodstructure.py): Nod_* baked concrete (the back of the hand),
NodPlate*/NodSteel dark plate (extra nodColour), Remap the house colour, Lamp*
emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.5 s: the sleeve rises out of the ground, the hand comes up
             with its fingers stretched out, then they close onto the ground one after
             another, the thumb last; the doorway and the spire come up, the lamps
             appear
    Idle     loop, 2 s: the blue light on the back of the hand sparkles, the spire's
             tip and the doorway lamps blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NAHAND.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The foundation
spans x -1.5 … 1.5 and y -1 … 1.
"""
import math
import os
import sys

from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nod  # noqa: E402

BUILD_END = 78

WRIST = -0.15           # where the sleeve meets the hand
KNUCKLES = 0.5
ARCH = 18               # points round a cross-section of the hand
# the fingers: y, yaw (deg), segment lengths, curl angles (each relative to the one before)
FINGERS = (
    (-0.47, -9, (0.36, 0.28, 0.19), (4, 20, 30)),
    (-0.16, -3, (0.42, 0.31, 0.2), (2, 20, 30)),
    (0.16, 3, (0.41, 0.31, 0.2), (2, 20, 30)),
    (0.47, 9, (0.35, 0.27, 0.19), (4, 20, 30)),
)
KNUCKLE_Z = 0.3
FINGER_WIDTH = 0.16
FINGER_THICK = 0.14
THUMB = (Vector((0.22, -0.5, 0.22)), math.radians(-38), (0.34, 0.26), (16, 42))
DOOR = Vector((-0.12, -0.66, 0))          # the doorway's foot, in the front of the wrist
EXIT = Vector((-0.12, -1.0, 0))
SPIRE = Vector((-0.02, 0.48, 0.27))         # the spire's foot on the back of the hand
SPARK = Vector((-0.02, 0.18, 0.44))        # the blue light

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def arch(x, width, height, power=3.0, z0=0.0, y0=0.0):
    """A cross-section: an arch over y from +width to -width, flat-topped (superellipse)."""
    points = []
    for k in range(ARCH):
        t = math.pi * k / (ARCH - 1)
        c, s = math.cos(t), math.sin(t)
        points.append(Vector((x, y0 + width * math.copysign(abs(c) ** (2 / power), c), z0 + height * abs(s) ** (2 / power))))
    return points


def bezier(a, b, c, u):
    a, b, c = Vector(a), Vector(b), Vector(c)
    return a * (1 - u) ** 2 + b * 2 * u * (1 - u) + c * u * u


# --------------------------------------------------------------------------- parts

TIP = (-1.48, -0.97)
FRONT = ((WRIST + 0.05, -0.68), (-0.75, -1.0), TIP)      # the sleeve's front edge (on the ground)
BACK = ((WRIST + 0.05, 0.72), (-1.3, 1.2), TIP)       # its back edge (a little raised)


def sleeve_point(u, t):
    """A point of the sleeve: u from the wrist (0) to the point (1), t across from the
    front edge (0) to the back edge (1)."""
    f, b = bezier(*FRONT, u), bezier(*BACK, u)
    p = f.lerp(b, t)
    ridge = 0.54 * (1 - u) ** 0.6 + 0.02          # the height of the ridge
    hump = math.sin(math.pi * min(1.0, t / 0.72) * 0.5) ** 0.8 if t < 0.72 else 1 - 0.3 * ((t - 0.72) / 0.28) ** 1.5
    return Vector((p.x, p.y, 0.012 + ridge * max(0.0, hump)))


SLEEVE_ROWS = 20
SLEEVE_COLS = 16
# the bands across the sleeve, front to back (they run together at the point)
BANDS = ('remap', 'remap', 'nplate_dark', 'remap', 'dirt', 'nplate_dark', 'remap', 'remap', 'nplate_dark',
         'nplate_dark', 'remap', 'remap', 'nplate_dark', 'remap', 'remap')


def sleeve(m):
    """The sleeve: a low cowl from the wrist to a sharp point at the front left, its
    surface striped lengthwise; a red rim round its edge on the ground."""
    us = [0.97 * (k / (SLEEVE_ROWS - 1)) ** 0.85 for k in range(SLEEVE_ROWS)]
    sections = [[sleeve_point(u, j / (SLEEVE_COLS - 1)) for j in range(SLEEVE_COLS)] for u in us]
    shell = nod.loft('Sleeve', sections, lambda i, k: m[BANDS[k]], cap=m['nplate_dark'])
    # the rim: a red bead along both edges, low on the ground (one lofted strip each)
    parts = []
    for edge in (0.0, 1.0):
        out = Vector((0, -1 if edge == 0 else 1, 0))
        pts = [sleeve_point(u, edge) for u in us] + [Vector((*TIP, 0.012))]
        strip = []
        for k, p in enumerate(pts):
            q = pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]
            side = Vector((q.y, -q.x, 0)).normalized()
            if side.dot(out) < 0:
                side = -side
            if k == len(pts) - 1:
                side = Vector((-1, 0, 0))
            strip.append([p + side * 0.05 + Vector((0, 0, -0.008)), p + side * 0.02 + Vector((0, 0, 0.03)), p - side * 0.03 + Vector((0, 0, 0.025)),
                          p - side * 0.05 + Vector((0, 0, 0.0))])
        parts.append(nod.loft(f'Rim{edge}', strip, lambda i, k: m['remap'], cap=m['remap']))
    # the cuff: a red band where the sleeve meets the hand
    cuff = [sleeve_point(0, j / (SLEEVE_COLS - 1)) + Vector((-0.02, 0, 0.012)) for j in range(SLEEVE_COLS)]
    for k, (a, b) in enumerate(zip(cuff, cuff[1:])):
        parts.append(beam(f'Cuff{k}', m['remap'], a, b, 0.07, 0.04))
    return shell, kit.merge('SleeveTrim', parts)


def hand_section(x):
    """The cross-section of the back of the hand at x."""
    t = max(0.0, (x - WRIST) / (KNUCKLES - WRIST))
    width = 0.66 + 0.02 * t
    height = 0.46 - 0.12 * t ** 1.5
    return arch(x, width, height, 2.6, 0.0, 0.02 - 0.02 * t)


def palm(m, root):
    """The back of the hand (dark speckled concrete) with red contour lines (tendons
    to each finger) and the knuckle ridge."""
    xs = [WRIST - 0.08 + k * (KNUCKLES + 0.06 - WRIST + 0.08) / 7 for k in range(8)]
    body = nod.loft('PalmShell', [hand_section(x) for x in xs], lambda i, k: m['steel'], cap=m['steel'])
    shell = nod.concrete('Palm', [body], root, '#2c2d31')

    def surface(x, y):
        sec = hand_section(x)
        best = min(sec, key=lambda p: abs(p.y - y))
        return Vector((x, y, best.z))

    parts = []
    for y, yaw, _, _ in FINGERS:  # tendons from the wrist to each finger, red lined
        pts = [surface(WRIST + 0.06 + (KNUCKLES - 0.08 - WRIST - 0.06) * f, y * (0.55 + 0.45 * f)) + Vector((0, 0, 0.004)) for f in (0, 0.25, 0.5, 0.75, 1)]
        for k, (a, b) in enumerate(zip(pts, pts[1:])):
            d = (b - a).normalized() * 0.012
            parts.append(beam(f'Tendon{y}{k}', m['remap'], a - d, b + d, 0.03, 0.025))
    # the contour lines along both sides of the hand
    for s in (-1, 1):
        pts = []
        for x in xs[1:-1]:
            sec = hand_section(x)
            p = sec[4] if s > 0 else sec[-5]
            pts.append(p + Vector((0, 0.012 * s, 0.006)))
        for k, (a, b) in enumerate(zip(pts, pts[1:])):
            d = (b - a).normalized() * 0.012
            parts.append(beam(f'Contour{s}{k}', m['remap'], a - d, b + d, 0.035, 0.025))
    # the knuckle ridge: four bosses, red ringed
    for y, yaw, _, _ in FINGERS:
        at = Vector((KNUCKLES - 0.03, y, KNUCKLE_Z + 0.02))
        parts.append(sphere(f'Knuckle{y}', m['nplate_dark'], 0.085, at, 14))
    return shell, kit.merge('PalmDetails', parts)


def segment(m, name, length, width, thick, tip=False):
    """One finger segment along +X from its joint (the origin), tapered; red trims
    along its top edges and a red ring round its root."""
    w0, w1 = width / 2, width / 2 * 0.88
    t0, t1 = thick / 2, thick / 2 * 0.88
    end = length * (0.78 if tip else 1.0)
    parts = [
        kit.hexahedron(f'{name}Body', m['nplate_dark'], (
            (0, -w0, -t0), (end, -w1, -t1), (end, w1, -t1), (0, w0, -t0),
            (0, -w0, t0), (end, -w1, t1), (end, w1, t1), (0, w0, t0)), bevel=0.018),
        cylinder(f'{name}Joint', m['nplate'], t0 * 0.95, width * 1.02, (0, 0, 0), rotation=(math.pi / 2, 0, 0), segments=14, bevel=0.006),
        box(f'{name}Ring', m['remap'], (0.035, width + 0.02, thick + 0.02), (0.06, 0, 0), bevel=0.006),
    ]
    for s in (-1, 1):
        parts.append(beam(f'{name}Trim{s}', m['remap'], Vector((0.09, s * (w0 - 0.01), t0 + 0.002)),
                          Vector((end - 0.02, s * (w1 - 0.01), t1 + 0.002)), 0.018, 0.012))
    if tip:  # the claw
        parts += [
            kit.hexahedron(f'{name}Claw', m['nplate_dark'], (
                (end, -w1, -t1), (length + 0.03, -w1 * 0.25, -t1 * 0.2), (length + 0.03, w1 * 0.25, -t1 * 0.2), (end, w1, -t1),
                (end, -w1, t1), (length + 0.03, -w1 * 0.25, -t1 * 0.05), (length + 0.03, w1 * 0.25, -t1 * 0.05), (end, w1, t1)), bevel=0.006),
            box(f'{name}ClawRing', m['remap'], (0.03, width * 0.92, thick * 0.92), (end + 0.005, 0, 0), bevel=0.005),
        ]
    return kit.merge(name, parts)


def attach(child, parent_obj, location=(0, 0, 0), rotation=(0, 0, 0)):
    """Parents with a local transform (the joints are built in their final pose)."""
    child.parent = parent_obj
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.location = location
    child.rotation_euler = rotation
    return child


def finger(m, name, hand, root_at, yaw, lengths, angles, width, thick):
    """A finger: a chain of joints (empties) with their segments; returns the joints
    and their final pitch angles."""
    joints = []
    holder = hand
    for k, (length, angle) in enumerate(zip(lengths, angles)):
        joint = kit.empty(f'{name}Joint{k}')
        joint.empty_display_size = 0.05
        attach(joint, holder, root_at if k == 0 else (lengths[k - 1], 0, 0), (0, math.radians(angle), yaw if k == 0 else 0))
        seg = segment(m, f'{name}Seg{k}', length, width * (1 - 0.07 * k), thick * (1 - 0.07 * k), tip=k == len(lengths) - 1)
        attach(seg, joint)
        joints.append((joint, math.radians(angle)))
        holder = joint
    return joints


def doorway(m):
    """The low doorway in the front of the wrist: a sloped hood with a dark opening,
    framed red; origin on the ground."""
    p = DOOR
    parts = [
        nod.prism('DoorHood', m['nplate'], nod.chamfered(p.x, p.y + 0.06, 0.4, 0.22, 0.05), nod.chamfered(p.x, p.y + 0.1, 0.3, 0.12, 0.03),
                  0, 0.26, 0.01),
        box('DoorDark', m['dark'], (0.2, 0.02, 0.19), p + Vector((0, -0.045, 0.095)), bevel=0,
            rotation=(math.radians(-8), 0, 0)),
        box('DoorLintel', m['remap'], (0.28, 0.05, 0.04), p + Vector((0, -0.035, 0.215)), bevel=0.006),
        *[box(f'DoorJamb{s}', m['remap'], (0.04, 0.05, 0.2), p + Vector((s * 0.12, -0.045, 0.1)), bevel=0.006,
              rotation=(math.radians(-8), 0, 0)) for s in (-1, 1)],
        box('DoorStep', m['nsteel'], (0.3, 0.1, 0.02), p + Vector((0, -0.1, 0.01)), bevel=0.004),
    ]
    return kit.merge('Doorway', parts, p)


def spire(m):
    """The thin black stepped spire at the back of the hand; origin at its foot."""
    foot = SPIRE
    parts = [
        box('SpireFoot', m['nplate_dark'], (0.16, 0.16, 0.14), foot + Vector((0, 0, 0.07)), bevel=0.02),
        box('SpireStep1', m['nplate_dark'], (0.1, 0.1, 0.36), foot + Vector((0, 0, 0.32)), bevel=0.012),
        box('SpireStep2', m['nplate_dark'], (0.06, 0.06, 0.4), foot + Vector((0, 0, 0.7)), bevel=0.008),
        cylinder('SpireNeedle', m['nplate_dark'], 0.02, 0.3, foot + Vector((0, 0, 1.05)), segments=8, bevel=0, radius2=0.006),
        *[box(f'SpireFin{s}', m['nplate_dark'], (0.02, 0.05, 0.22), foot + Vector((0, s * 0.07, 0.3)), bevel=0.004) for s in (-1, 1)],
        box('SpireBand', m['remap'], (0.11, 0.11, 0.03), foot + Vector((0, 0, 0.48)), bevel=0.004),
    ]
    return kit.merge('Spire', parts, foot), foot + Vector((0, 0, 0.9))


def spark(m):
    """The blue light on the back of the hand: a bright core and a cross of rays."""
    at = SPARK
    parts = [sphere('SparkCore', m['lamp_pulse'], 0.025, at, 12), sphere('SparkHalo', m['glow_pulse'], 0.05, at, 12)]
    for k in range(2):
        parts.append(box(f'SparkRay{k}', m['glow_pulse'], (0.16, 0.008, 0.008), at, bevel=0, rotation=(0, 0, math.radians(45 + 90 * k))))
    return kit.merge('Spark', parts, at)


# --------------------------------------------------------------------------- model

def build():
    root = nod.start('NodHand', 'HandOfNod', BUILD_END)
    m = nod.materials()
    keys = kit.keys

    # ---- the sleeve rises out of the ground
    sleeve_group = kit.parent(kit.empty('SleeveGroup'), root)
    shell, trim = sleeve(m)
    kit.parent(shell, sleeve_group)
    kit.parent(trim, sleeve_group)
    nod.rise(sleeve_group, 0, 20, 0.6)

    # ---- the hand comes up, fingers stretched out (translation only: the lamps hang on it)
    hand = kit.parent(kit.empty('Hand'), root)
    shell, details = palm(m, root)
    kit.parent(shell, hand)
    kit.parent(details, hand)
    nod.rise(hand, 8, 20, 0.6)
    chains = []
    for i, (y, yaw, lengths, angles) in enumerate(FINGERS):
        chains.append(finger(m, f'Finger{i}', hand, (KNUCKLES, y, KNUCKLE_Z), math.radians(yaw), lengths, angles, FINGER_WIDTH, FINGER_THICK))
    at, yaw, lengths, angles = THUMB
    chains.append(finger(m, 'Thumb', hand, at, yaw, lengths, angles, FINGER_WIDTH * 1.1, FINGER_THICK * 1.05))

    # ---- the fingers close onto the ground one after another, the thumb last
    for i, chain in enumerate(chains):
        start = 28 + i * 5
        for k, (joint, angle) in enumerate(chain):
            rest = joint.rotation_euler.copy()
            open_ = rest.copy()
            open_.y = -0.12 if k == 0 else 0.0
            over = rest.copy()
            over.y = angle * 1.08
            keys(joint, 'rotation_euler', {0: open_, start + k * 2: open_, start + 14 + k * 2: over, start + 18 + k * 2: rest})

    # ---- doorway, spire (they slide up: their lamps blink in Idle)
    entrance = kit.parent(doorway(m), root)
    nod.rise(entrance, 36, 12, 0.3)
    exit_node = kit.parent(kit.empty('Exit', EXIT), root)
    exit_node.empty_display_size = 0.15
    pole, top = spire(m)
    kit.parent(pole, hand)
    nod.rise(pole, 48, 16, 1.2)

    lights = [(nod.lamp(m, pole, 'SpireLamp', top, 'red', 66), kit.flashes((0, 6), (12, 6), (36, 6)))]
    for s in (-1, 1):
        at = DOOR + Vector((s * 0.17, -0.05, 0.22))
        lights.append((nod.lamp(m, entrance, f'DoorLamp{s}', at, 'red', 70 + s), kit.flashes((15 + 15 * s, 8), (45 + 15 * s, 8))))
    light = kit.parent(spark(m), hand)
    idle = [(light, lambda o: sparkle(o))]
    nod.clips(lights, idle)
    return len(kit.collection().objects)


def sparkle(obj):
    """The blue light flickers: quick swells and fades, turning a little (scale only,
    the rays' cross turns by the scale's ratio)."""
    base = Vector(obj.scale)
    pattern = (1.0, 0.55, 1.25, 0.7, 1.4, 0.5, 1.1, 0.8, 1.3, 0.6, 1.0)
    frames = kit.IDLE_END
    keyed = {round(k * frames / (len(pattern) - 1)): base * v for k, v in enumerate(pattern)}
    kit.keys(obj, 'scale', keyed, 'LINEAR')


if __name__ == '__main__':
    nod.main(build, 'NAHAND', {'Build': [BUILD_END // 3, 2 * BUILD_END // 3, BUILD_END], 'Idle': [0, 24]}, ortho=3.6, target=(0.0, 0, 0.3))
