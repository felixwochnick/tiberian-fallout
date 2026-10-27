"""
Tiberian Fallout – Nod stealth generator (NASTLH), after Tiberian Sun.

On a foundation of three cells by two (long along x; on screen from the upper left to
the lower right), like the original's: at the -x end a big dark metal ball, pierced
by rows of small holes and girdled by thin red (house colour) rings round its crown,
sits in a craggy mound of stained concrete; from the mound a heavy dark pipe runs
along +x, through three fat red coils with dark collars and grey end caps, to a
small block at the far end.

Materials (see nodstructure.py): Nod_* baked concrete, NodPlate*/NodSteel dark plate
(extra nodColour), Remap the house colour, Lamp* emissive, Glow* additive.

Nodes:
    Mound        the concrete mound (rises in Build)
    Ball         the ball with its rings (rises out of the mound in Build)
    Field        a faint red shell round the ball: the cloaking field, swelling and
                 fading (Idle, the original's NASTLH_A)
    CrownGlow    the glow round the red rings on the crown (Idle)
    Coil0…2      the red coils on the pipe (pop up in Build)
    CoilLamp…    a red lamp on each coil, lit one after the other (Idle)
Animations (glTF clips)
    Build    one-shot, 2.4 s: the mound rises, the ball comes up out of it, the pipe
             grows along the ground, the coils come up one after the other
    Idle     loop, 2 s: the field round the ball swells and fades, the crown glows,
             the coils' lamps run along the pipe

Run headless:

    blender -b --factory-startup --python blender/NASTLH.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The cells are
centred at x = -1, 0, 1 and y = ±0.5; origin in the middle on the ground.
"""
import math
import os
import random
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import nodstructure as nb  # noqa: E402
import NAPOWR as pw  # noqa: E402 – the glowing band

box, cylinder, sphere, beam = kit.box, kit.cylinder, kit.sphere, kit.beam
BUILD_END = 72

BALL = Vector((-0.88, 0.05, 0.62))     # the ball's centre
RADIUS = 0.5
MOUND_TOP = 0.3
PIPE_Z = 0.22
PIPE_END = 1.36
COILS = (0.06, 0.53, 1.0)              # the coils' centres along x
COIL_R, COIL_LEN = 0.22, 0.34
MOUND_CONCRETE = '#8f8778'


def mound(m, root):
    """The craggy mound round the ball's foot (concrete, returned first) and its
    details; origin on the ground."""
    rnd = random.Random(7)
    n = 18
    radii = [1 + rnd.uniform(-0.1, 0.1) for _ in range(n)]

    def ring(r, z, jag=1.0):
        return [(BALL.x + math.cos(2 * math.pi * k / n) * r * (1 + (radii[k] - 1) * jag),
                 BALL.y + math.sin(2 * math.pi * k / n) * r * (1 + (radii[k] - 1) * jag)) for k in range(n)]

    low = nb.prism('MoundLow', m['steel'], ring(0.8, 0), ring(0.66, 0.14), 0, 0.14, bevel=0.01)
    high = nb.prism('MoundHigh', m['steel'], ring(0.66, 0.14), ring(0.47, MOUND_TOP, 0.4), 0.14, MOUND_TOP, bevel=0.01)
    body = nb.concrete('Mound', [low, high], root, MOUND_CONCRETE)
    parts = [nb.prism('MoundDirt', m['dirt'], ring(0.88, 0), ring(0.88, 0), 0, 0.008, bevel=0)]
    # buttresses of dark plate standing out of the mound
    for k, a in enumerate((200, 250, 300, 340, 120)):
        d = Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        foot = Vector((BALL.x, BALL.y, 0)) + d * 0.74
        top = Vector((BALL.x, BALL.y, 0)) + d * 0.5 + Vector((0, 0, MOUND_TOP - 0.02))
        parts.append(beam(f'Buttress{k}', m['nplate_dark'], foot + Vector((0, 0, 0.02)), top, 0.07, 0.05))
    # the ball's seat
    parts.append(cylinder('Seat', m['nplate_dark'], 0.45, 0.05, (BALL.x, BALL.y, MOUND_TOP), segments=32, bevel=0.006))
    return body, kit.merge('MoundDetails', parts)


def ball(m):
    """The ball with its holes and red crown rings; origin at its foot."""
    foot = Vector((BALL.x, BALL.y, MOUND_TOP))
    shell = nb.lathe('BallShell', m['nplate'], [(RADIUS * math.sin(t), -RADIUS * math.cos(t)) for t in
                                                 (0.45 + (math.pi - 0.47) * k / 20 for k in range(21))], BALL, 40)
    parts = [shell]
    # thin red rings round the crown
    for j, t in enumerate((0.1, 0.22, 0.34, 0.46, 0.58)):
        a = t * math.pi / 2         # angle from the pole
        r, z = RADIUS * math.sin(a), RADIUS * math.cos(a)
        parts.append(cylinder(f'Crown{j}', m['remap'], r + 0.006, 0.016, BALL + Vector((0, 0, z)), segments=36, bevel=0))
    # rows of small holes round the middle
    for row, el in enumerate((-0.05, 0.12, 0.29)):
        count = 30 - 4 * row
        for k in range(count):
            az = 2 * math.pi * (k + 0.5 * row) / count
            d = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
            hole = cylinder(f'Hole{row}_{k}', m['dark'], 0.014, 0.01, BALL + d * (RADIUS - 0.002), segments=6, bevel=0)
            hole.rotation_mode = 'QUATERNION'
            hole.rotation_quaternion = d.to_track_quat('Z', 'Y')
            parts.append(hole)
    # red veins down the front (the original's red streaks)
    for k, (az, el0, el1) in enumerate(((-100, 0.1, -0.5), (-70, 0.25, -0.35), (-125, 0.0, -0.4))):
        pts = []
        for i in range(6):
            el = el0 + (el1 - el0) * i / 5
            a = math.radians(az + 6 * math.sin(i * 1.7))
            pts.append(BALL + Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el))) * (RADIUS + 0.002))
        for i, (p, q) in enumerate(zip(pts, pts[1:])):
            parts.append(beam(f'Vein{k}_{i}', m['remap'], p, q, 0.016, 0.008))
    parts.append(cylinder('Pole', m['nplate_dark'], 0.06, 0.03, BALL + Vector((0, 0, RADIUS - 0.004)), segments=16, bevel=0.004))
    return kit.merge('Ball', parts, foot)


def pipe(m):
    """The heavy pipe along the ground to the end block; origin at its start."""
    start = Vector((BALL.x + 0.45, BALL.y, PIPE_Z))
    parts = [
        cylinder('Pipe', m['nplate_dark'], 0.06, PIPE_END - start.x, ((start.x + PIPE_END) / 2, BALL.y, PIPE_Z), rotation=(0, math.pi / 2, 0), segments=14, bevel=0.003),
        box('EndBlock', m['nplate'], (0.12, 0.2, PIPE_Z + 0.08), (PIPE_END + 0.02, BALL.y, (PIPE_Z + 0.08) / 2), bevel=0.012),
        box('EndCap', m['nplate_dark'], (0.1, 0.16, 0.02), (PIPE_END + 0.02, BALL.y, PIPE_Z + 0.09), bevel=0.004),
    ]
    for k, x in enumerate((start.x + 0.12, (COILS[0] + COILS[1]) / 2, (COILS[1] + COILS[2]) / 2)):
        parts.append(box(f'PipeFoot{k}', m['nplate'], (0.06, 0.16, PIPE_Z), (x, BALL.y, PIPE_Z / 2), bevel=0.006))
        parts.append(cylinder(f'PipeClamp{k}', m['nsteel'], 0.07, 0.03, (x, BALL.y, PIPE_Z), rotation=(0, math.pi / 2, 0), segments=14, bevel=0))
    return kit.merge('Pipe', parts, start)


def coil(m, k, x):
    """A fat red coil on the pipe; origin at its foot."""
    c = Vector((x, BALL.y, PIPE_Z))
    rot = (0, math.pi / 2, 0)
    parts = [
        cylinder(f'Coil{k}Body', m['remap'], COIL_R, COIL_LEN, c, rotation=rot, segments=24, bevel=0.06),
        cylinder(f'Coil{k}Core', m['nsteel_light'], COIL_R * 0.55, COIL_LEN + 0.08, c, rotation=rot, segments=20, bevel=0.01),
        box(f'Coil{k}Saddle', m['nplate_dark'], (COIL_LEN * 0.6, 0.26, 0.06), (x, BALL.y, 0.03), bevel=0.01),
    ]
    for s in (-1, 1):
        parts.append(cylinder(f'Coil{k}Collar{s}', m['nplate_dark'], COIL_R * 0.62, 0.03, c + Vector((s * (COIL_LEN / 2 + 0.05), 0, 0)), rotation=rot, segments=20, bevel=0.004))
    return kit.merge(f'Coil{k}', parts, Vector((x, BALL.y, 0)))


def build():
    root = nb.start('NodStealthGenerator', 'NodStealthGenerator', BUILD_END)
    m = nb.materials()
    m['glow_field'] = kit.material('GlowField', (0, 0, 0), 1.0, emission=kit.srgb('#ff4030'), strength=0.8, alpha=0.03)
    keys = kit.keys

    group = kit.parent(kit.empty('MoundGroup'), root)
    body, details = mound(m, root)
    kit.parent(body, group)
    kit.parent(details, body)
    nb.rise(group, 0, 18, MOUND_TOP + 0.05)

    # the ball rises out of the mound (translation: the field and the crown glow ride on it)
    lift = kit.parent(kit.empty('Ball', (BALL.x, BALL.y, MOUND_TOP)), root)
    ball_obj = kit.parent(ball(m), lift)
    crown = pw.ring_glow(m, BALL + Vector((0, 0, RADIUS * 0.8)), RADIUS * 0.66, 0.09, 36)
    crown.name = 'CrownGlow'
    kit.parent(crown, ball_obj)
    field = kit.parent(kit.merge('Field', [sphere('FieldShell', m['glow_field'], RADIUS + 0.06, BALL, 32)], BALL), ball_obj)
    keys(lift, 'location', {0: lift.location - Vector((0, 0, 2 * RADIUS + 0.4)), 14: lift.location - Vector((0, 0, 2 * RADIUS + 0.4)),
                            40: lift.location + Vector((0, 0, 0.012)), 44: Vector(lift.location)})

    # the pipe grows along the ground, the coils come up one after the other
    pipe_obj = kit.parent(pipe(m), root)
    kit.grow(pipe_obj, 34, 12, 0)
    lights = []
    for k, x in enumerate(COILS):
        holder = kit.parent(kit.empty(f'Coil{k}Holder', (x, BALL.y, 0)), root)
        obj = kit.parent(coil(m, k, x), holder)
        nb.rise(holder, 42 + 6 * k, 10, PIPE_Z + COIL_R + 0.05)
        lights.append((nb.lamp(m, obj, f'CoilLamp{k}', (x, BALL.y, PIPE_Z + COIL_R - 0.004), 'red', 56 + 4 * k),
                       kit.flashes((k * 10, 8), (k * 10 + 30, 8))))

    def swell(obj):
        frames = {}
        for f in range(0, kit.IDLE_END + 1, 3):
            t = (math.sin(2 * math.pi * f / kit.IDLE_END) + 1) / 2
            frames[f] = Vector((1, 1, 1)) * (0.97 + 0.16 * t)
        frames[kit.IDLE_END] = frames[0]
        kit.keys(obj, 'scale', frames, 'LINEAR')

    def glow(obj):
        frames = {}
        for f in range(0, kit.IDLE_END + 1, 3):
            t = (math.sin(2 * math.pi * (2 * f / kit.IDLE_END + 0.25)) + 1) / 2
            frames[f] = Vector((1, 1, 0.3 + 0.7 * t))
        frames[kit.IDLE_END] = frames[0]
        kit.keys(obj, 'scale', frames, 'LINEAR')

    nb.clips(lights, [(field, swell), (crown, glow)])
    return len(kit.collection().objects)


if __name__ == '__main__':
    nb.main(build, 'NASTLH', {'Build': [24, 48, BUILD_END], 'Idle': [0, 15]}, ortho=3.4, target=(0, 0, 0.35))
