"""
Tiberian Fallout – Hand of Nod (NAHAND), Nod's barracks, after Tiberian Sun.

A giant black armoured hand lying on the ground, palm down (foundation 3 × 2 cells):
its four fingers reach out to the right (+X) and grip the ground, the thumb on the
front side; at the back (-X) the wide sleeve flares low to a point, striped in the
house colour and black like layered scales. A thin black mast stands on the back of
the hand. The soldiers come out of a porch in the sleeve's front side.

Nodes the game uses
    Exit    an empty on the ground in front of the porch; its -Y axis points away
            from the building (the way the soldiers walk out)

Materials (see nodstructure.py): Nod_* baked concrete (the back of the hand),
NodPlate*/NodSteel dark plate (extra nodColour), Remap the house colour, Lamp*
emissive, Glow* additive.

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.6 s: the sleeve rises out of the ground, the hand comes up
             with its fingers stretched out, then they close onto the ground one after
             another, the thumb last; the porch and the mast appear, the lights come on
    Idle     loop, 2 s: the glow slits in the cuff swell and fade, the mast's beacon
             and the porch lamps blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    blender -b --factory-startup --python blender/NAHAND.py [-- --preview 0,30,78 <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'NAHAND.glb')
BLEND = os.path.join(HERE, 'NAHAND.blend')
BUILD_END = 78

WRIST = -0.32           # where the sleeve ends and the hand begins
KNUCKLES = 0.52
ARCH = 18               # points round a cross-section
# the fingers: y, segment lengths, curl angles (each relative to the one before)
FINGERS = (
    (-0.39, (0.34, 0.28, 0.22), (6, 30, 52)),
    (-0.13, (0.4, 0.32, 0.24), (4, 28, 50)),
    (0.13, (0.41, 0.33, 0.24), (4, 28, 50)),
    (0.39, (0.36, 0.29, 0.22), (6, 30, 52)),
)
KNUCKLE_Z = 0.44
FINGER_WIDTH = 0.17
FINGER_THICK = 0.15
THUMB = (Vector((0.05, -0.5, 0.3)), math.radians(-62), (0.3, 0.25), (22, 58))
PORCH = Vector((-0.75, -0.72, 0))
EXIT = Vector((-0.75, -0.95, 0))

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam


def arch(x, width, height, power=3.0, z0=0.0):
    """A cross-section: an arch over y from +width to -width, flat-topped (superellipse)."""
    points = []
    for k in range(ARCH):
        t = math.pi * k / (ARCH - 1)
        c, s = math.cos(t), math.sin(t)
        points.append(Vector((x, width * math.copysign(abs(c) ** (2 / power), c), z0 + height * abs(s) ** (2 / power))))
    return points


# --------------------------------------------------------------------------- parts

def sleeve(m):
    """The flared sleeve: low and pointed at the back, rising to the wrist; striped red
    and black along its length (the stripes run together at the point like the
    original's layered scales), on a flat red brim."""
    profile = ((-1.47, 0.08, 0.02), (-1.36, 0.32, 0.07), (-1.18, 0.52, 0.16), (-0.98, 0.64, 0.26), (-0.78, 0.7, 0.36),
               (-0.6, 0.71, 0.45), (-0.46, 0.7, 0.52), (WRIST - 0.04, 0.68, 0.56))
    sections = [arch(x, w, h, 2.2, 0.03) for x, w, h in profile]
    bands = {0: 'nplate_dark', 1: 'remap', 2: 'nplate_dark', 3: 'nplate_dark', 4: 'remap', 5: 'nplate_dark', 6: 'remap', 7: 'nplate_dark',
             8: 'nplate'}

    def material(i, k):
        edge = min(k, ARCH - 2 - k)
        return m[bands.get(edge, 'nplate')]

    shell = nod.loft('Sleeve', sections, material, cap=m['nplate_dark'])
    # the brim: a flat red leaf round the sleeve's foot, pointed at the back
    outline = [(x, -w - 0.07) for x, w, _ in profile] + [(x, w + 0.07) for x, w, _ in reversed(profile)]
    outline[0] = (profile[0][0] - 0.06, 0)
    outline = outline[:len(profile)] + outline[len(profile) + 1:]
    brim = nod.prism('Brim', m['remap'], outline, outline, 0, 0.035, 0.006)
    parts = [brim]
    # the cuff at the wrist: a red band
    cuff = arch(WRIST - 0.02, 0.72, 0.6, 2.2, 0.03)
    for k, (a, b) in enumerate(zip(cuff, cuff[1:])):
        parts.append(beam(f'Cuff{k}', m['remap'], a, b, 0.07, 0.04))
    return shell, kit.merge('SleeveTrim', parts)


def palm(m, root):
    """The back of the hand (concrete, dark) with its red tendons and knuckle plate."""
    profile = ((WRIST - 0.06, 0.64, 0.55), (WRIST + 0.2, 0.62, 0.57), (0.2, 0.58, 0.56), (KNUCKLES, 0.55, 0.5), (KNUCKLES + 0.06, 0.5, 0.44))
    sections = [arch(x, w, h, 2.3) for x, w, h in profile]
    body = nod.loft('PalmShell', sections, lambda i, k: m['steel'], cap=m['steel'])
    shell = nod.concrete('Palm', [body], root, '#3d3e42')
    parts = []
    for y, _, _ in FINGERS:  # tendons from the wrist to each finger
        top = lambda x: 0.57 - 0.07 * max(0.0, (x - WRIST) / (KNUCKLES - WRIST)) ** 2  # noqa: E731
        a = Vector((WRIST + 0.12, y * 0.7, top(WRIST + 0.12) + 0.008))
        b = Vector((KNUCKLES - 0.02, y, top(KNUCKLES) - 0.01))
        parts.append(beam(f'Tendon{y}', m['remap'], a, b, 0.035, 0.03))
        parts.append(beam(f'TendonL{y}', m['nplate_dark'], a + Vector((0, 0.035, -0.01)), b + Vector((0, 0.04, -0.01)), 0.03, 0.03))
    parts.append(box('KnucklePlate', m['nplate'], (0.14, 1.08, 0.08), (KNUCKLES - 0.02, 0, 0.47), bevel=0.02))
    # dirt round the hand, like the original's sandy edge
    parts.append(box('Dirt', m['dirt'], (2.5, 1.5, 0.01), (-0.15, 0, 0.005), bevel=0.2))
    return shell, kit.merge('PalmDetails', parts)


def segment(m, name, length, width, thick, tip=False):
    """One finger segment along +X from its joint (the origin), tapered; red trims
    along its top edges and a red band round its root."""
    w0, w1 = width / 2, width / 2 * 0.9
    t0, t1 = thick / 2, thick / 2 * 0.9
    end = length * (0.85 if tip else 1.0)
    parts = [
        kit.hexahedron(f'{name}Body', m['nplate_dark'], (
            (0, -w0, -t0), (end, -w1, -t1), (end, w1, -t1), (0, w0, -t0),
            (0, -w0, t0), (end, -w1, t1), (end, w1, t1), (0, w0, t0)), bevel=0.02),
        cylinder(f'{name}Joint', m['nplate'], t0 * 0.95, width * 1.04, (0, 0, 0), rotation=(math.pi / 2, 0, 0), segments=14, bevel=0.006),
        box(f'{name}Band', m['remap'], (0.035, width + 0.016, thick + 0.016), (0.07, 0, 0), bevel=0.006),
    ]
    for s in (-1, 1):
        parts.append(beam(f'{name}Trim{s}', m['remap'], Vector((0.1, s * (w0 - 0.012), t0 + 0.004)),
                          Vector((end - 0.03, s * (w1 - 0.012), t1 + 0.004)), 0.022, 0.014))
    if tip:  # the blunt fingertip with its nail
        parts += [
            kit.hexahedron(f'{name}Tip', m['nplate_dark'], (
                (end, -w1, -t1), (length, -w1 * 0.7, -t1 * 0.6), (length, w1 * 0.7, -t1 * 0.6), (end, w1, -t1),
                (end, -w1, t1), (length, -w1 * 0.7, t1 * 0.3), (length, w1 * 0.7, t1 * 0.3), (end, w1, t1)), bevel=0.012),
            kit.hexahedron(f'{name}Nail', m['remap'], (
                (end - 0.04, -w1 * 0.6, t1 - 0.01), (length + 0.01, -w1 * 0.45, t1 * 0.1), (length + 0.01, w1 * 0.45, t1 * 0.1),
                (end - 0.04, w1 * 0.6, t1 - 0.01),
                (end - 0.04, -w1 * 0.6, t1 + 0.012), (length + 0.012, -w1 * 0.45, t1 * 0.3), (length + 0.012, w1 * 0.45, t1 * 0.3),
                (end - 0.04, w1 * 0.6, t1 + 0.012)), bevel=0.004),
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
        seg = segment(m, f'{name}Seg{k}', length, width * (1 - 0.06 * k), thick * (1 - 0.06 * k), tip=k == len(lengths) - 1)
        attach(seg, joint)
        joints.append((joint, math.radians(angle)))
        holder = joint
    return joints


def porch(m):
    """The entrance in the sleeve's front side: a sloped block with a dark doorway
    framed red; origin on the ground."""
    p = PORCH
    parts = [
        nod.prism('PorchBody', m['nplate'], nod.chamfered(p.x, p.y, 0.36, 0.3, 0.05), nod.chamfered(p.x, p.y + 0.06, 0.28, 0.18, 0.04),
                  0, 0.3, 0.012),
        box('PorchDoor', m['dark'], (0.18, 0.02, 0.2), p + Vector((0, -0.145, 0.1)), bevel=0),
        box('PorchLintel', m['remap'], (0.26, 0.05, 0.04), p + Vector((0, -0.14, 0.215)), bevel=0.006),
        *[box(f'PorchJamb{s}', m['remap'], (0.04, 0.05, 0.2), p + Vector((s * 0.11, -0.14, 0.1)), bevel=0.006) for s in (-1, 1)],
        box('PorchStep', m['nsteel'], (0.26, 0.08, 0.02), p + Vector((0, -0.2, 0.01)), bevel=0.004),
    ]
    return kit.merge('Porch', parts, p)


def mast(m):
    """The thin black mast on the back of the hand; origin at its foot."""
    foot = Vector((0.0, 0.3, 0.57))
    parts = [
        box('MastFoot', m['nplate_dark'], (0.1, 0.1, 0.06), foot + Vector((0, 0, 0.03)), bevel=0.01),
        cylinder('Mast', m['nplate_dark'], 0.018, 0.62, foot + Vector((0, 0, 0.36)), segments=8, bevel=0, radius2=0.008),
        cylinder('MastSleeve', m['nplate'], 0.028, 0.18, foot + Vector((0, 0, 0.15)), segments=8, bevel=0),
        beam('MastSpar', m['nplate_dark'], foot + Vector((-0.05, 0, 0.5)), foot + Vector((0.05, 0, 0.5)), 0.008),
    ]
    return kit.merge('Mast', parts, foot), foot + Vector((0, 0, 0.67))


# --------------------------------------------------------------------------- model

def build():
    root = nod.start('NodHand', 'HandOfNod', BUILD_END)
    m = nod.materials()
    keys = kit.keys

    # ---- the sleeve rises out of the ground
    sleeve_group = kit.parent(kit.empty('SleeveGroup'), root)
    shell, ridges = sleeve(m)
    kit.parent(shell, sleeve_group)
    kit.parent(ridges, sleeve_group)
    nod.rise(sleeve_group, 0, 20, 0.75)

    # ---- the hand comes up, fingers stretched out
    hand = kit.parent(kit.empty('Hand'), root)
    shell, details = palm(m, root)
    kit.parent(shell, hand)
    kit.parent(details, hand)
    nod.rise(hand, 8, 20, 0.7)
    chains = []
    for i, (y, lengths, angles) in enumerate(FINGERS):
        chains.append(finger(m, f'Finger{i}', hand, (KNUCKLES, y, KNUCKLE_Z), 0, lengths, angles, FINGER_WIDTH, FINGER_THICK))
    at, yaw, lengths, angles = THUMB
    chains.append(finger(m, 'Thumb', hand, at, yaw, lengths, angles, FINGER_WIDTH * 1.05, FINGER_THICK))

    # ---- the fingers close onto the ground one after another, the thumb last
    for i, chain in enumerate(chains):
        start = 28 + i * 5
        for k, (joint, angle) in enumerate(chain):
            rest = joint.rotation_euler.copy()
            open_ = rest.copy()
            open_.y = -0.15 if k == 0 else 0.0
            over = rest.copy()
            over.y = angle * 1.08
            keys(joint, 'rotation_euler', {0: open_, start + k * 2: open_, start + 14 + k * 2: over, start + 18 + k * 2: rest})

    # ---- porch, mast, lights
    entrance = kit.parent(porch(m), sleeve_group)
    kit.pop(entrance, 40, 8)
    exit_node = kit.parent(kit.empty('Exit', EXIT), root)
    exit_node.empty_display_size = 0.15
    pole, top = mast(m)
    kit.parent(pole, hand)
    kit.grow(pole, 56, 12, 2)

    lights = [(nod.lamp(m, pole, 'MastLamp', top, 'red', 66), kit.flashes((0, 10), (30, 10)))]
    for s in (-1, 1):
        at = PORCH + Vector((s * 0.15, -0.16, 0.24))
        lights.append((nod.lamp(m, entrance, f'PorchLamp{s}', at, 'amber', 70 + s), kit.flashes((15 + 15 * s, 6), (45 + 15 * s, 6))))
    # glow slits in the cuff, swelling and fading in turn
    idle = []
    for k, y in enumerate((-0.42, -0.14, 0.14, 0.42)):
        z = 0.03 + 0.6 * abs(math.sin(math.acos(max(-1.0, min(1.0, y / 0.72))))) ** (2 / 2.2)
        at = Vector((WRIST - 0.12, y, z + 0.01))
        slit = kit.merge(f'Slit{k}', [box(f'SlitCore{k}', m['ember'], (0.1, 0.05, 0.012), at, bevel=0),
                                       box(f'SlitHalo{k}', m['glow_red'], (0.14, 0.08, 0.03), at, bevel=0)], at)
        kit.parent(slit, sleeve_group)
        idle.append((slit, lambda o, k=k: nod.pulse(o, kit.IDLE_END, 0.4, 1.1, phase=k * 0.18)))

    nod.clips(lights, idle)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, ortho=3.6, target=(0.0, 0, 0.3))
