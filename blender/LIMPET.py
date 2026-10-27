"""
Tiberian Fallout – limpet drone (LIMPET), after Tiberian Sun Firestorm.

A small hovering drone built by both sides: a grey metal egg, its point up, with a
dark visor and a red eye in front, house-colour bands round its waist and on the
crown, a sensor mast with a lamp on top, small thruster vents underneath and four
thin spider legs that it splays out to the corners. The shell is plain grey; only
the bands and the eye take the house colour (Remap), so it fits GDI and Nod alike.

It buries itself where it stands and waits, a sensor tip just above the ground,
until an enemy passes over it.

Clips:
    Idle        loop, 2 s: it hovers, bobbing a little, the legs twitch
    Walk        loop, 0.6 s: it skitters over the ground, the legs pattering in
                turn; the root's walkSpeed (glTF extras) is its speed in cells per
                second
    Deploy      once, 1.5 s: the legs dig in under the shell, it spins and sinks
                into the ground, a little mound of earth closes over it
    Deployed    loop, 2 s: buried, the sensor tip's lamp blinks
    Undeploy    once, 1.5 s: Deploy backwards

Run headless:

    blender -b --factory-startup --python blender/LIMPET.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the drone.
"""
import math
import os
import sys

from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'LIMPET.glb')
BLEND = os.path.join(HERE, 'LIMPET.blend')

POD = Vector((0, 0, 0.16))     # the egg's middle
POD_RADIUS = 0.08
POD_STRETCH = 1.35             # the egg is taller than wide
HIP_OUT = 0.06                 # the legs' hips from the middle
KNEE_OUT, KNEE_Z = 0.15, 0.2
FOOT_OUT = 0.21
WALK_FRAMES = 18
STRIDE = 0.18                  # how far it skitters per patter (two per loop; it half glides)
WALK_SPEED = 2 * STRIDE / (WALK_FRAMES / kit.FPS)
DEPLOY_FRAMES = 45
SINK = 0.27                    # how deep it goes: only the sensor tip stays out
FOLD = math.radians(40)        # the legs swung down, digging in under the shell
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'shell': material('LimpetShell', srgb('#a6aaad'), 0.35, 0.8),
        'shell_dark': material('LimpetShellDark', srgb('#5d6266'), 0.4, 0.8),
        'visor': material('Visor', srgb('#14191f'), 0.1, 0.6, emission=srgb('#1d2c3a'), strength=0.3),
        'earth': material('Earth', srgb('#5a4630'), 0.95),
        'thrust': material('ThrustGlow', (0, 0, 0), 1.0, emission=srgb('#8fd0ff'), strength=4, alpha=0.5),
    })
    return m


def egg(name, mat, centre, radius, stretch, segments=20):
    obj = sphere(name, mat, radius, centre, segments)
    c = Vector(centre)
    obj.data.transform(Matrix.Translation(c) @ Matrix.Diagonal((1, 1, stretch, 1)) @ Matrix.Translation(-c))
    return obj


def pod(m):
    """The egg with its fittings (all on the body)."""
    c, r = POD, POD_RADIUS
    top = c.z + r * POD_STRETCH
    parts = [
        egg('Shell', m['shell'], c, r, POD_STRETCH),
        # a waist band and a crown ring in the house colour, a dark skirt below
        cylinder('Band', m['remap'], r * 1.02, 0.026, c + Vector((0, 0, -0.005)), segments=24, bevel=0.004),
        cylinder('Crown', m['remap'], r * 0.55, 0.016, c + Vector((0, 0, r * POD_STRETCH * 0.8)), segments=20, bevel=0.003, radius2=r * 0.45),
        cylinder('Skirt', m['shell_dark'], r * 0.75, 0.03, c + Vector((0, 0, -r * POD_STRETCH * 0.72)), segments=20, bevel=0.006,
                 radius2=r * 0.9),
        # the face: a dark visor and the red eye in it
        box('Visor', m['visor'], (0.07, 0.03, 0.03), c + Vector((0, -r * 0.86, 0.045)), bevel=0.008, rotation=(math.radians(-20), 0, 0)),
        sphere('Eye', m['lamp_red'], 0.014, c + Vector((0, -r * 0.98, 0.012)), 10),
        cylinder('EyeRim', m['remap'], 0.02, 0.012, c + Vector((0, -r * 0.95, 0.012)), rotation=(math.pi / 2, 0, 0), segments=12, bevel=0.002),
        # the sensor mast on top
        cylinder('Mast', m['steel'], 0.006, 0.06, Vector((0, 0, top + 0.02)), segments=8, bevel=0),
        cylinder('MastFoot', m['shell_dark'], 0.016, 0.014, Vector((0, 0, top - 0.004)), segments=10, bevel=0.002),
        # thrusters underneath
        *[cylinder(f'Thruster{k}', m['dark'], 0.016, 0.014, c + Vector((0.035 * math.cos(a), 0.035 * math.sin(a), -r * POD_STRETCH * 0.86)),
                   segments=10, bevel=0) for k, a in enumerate(math.pi / 4 + math.pi / 2 * j for j in range(4))],
        *detail.rivets('BandRivets', m['steel_light'], c + Vector((-r * 0.98, 0.0, 0.012)), c + Vector((-r * 0.98, 0.0, -0.022)), 2, 0.004, 'X'),
    ]
    # hip sockets
    for k in range(4):
        d = leg_dir(k)
        parts.append(sphere(f'HipSocket{k}', m['shell_dark'], 0.022, c + d * HIP_OUT + Vector((0, 0, -0.02)), 10))
    return kit.merge('Pod', parts, c)


def leg_dir(k):
    a = math.pi / 4 + k * math.pi / 2
    return Vector((math.cos(a), math.sin(a), 0))


def leg(m, k, body):
    """A thin spider leg on its hip empty (its local x points outward)."""
    d = leg_dir(k)
    hip = POD + d * HIP_OUT + Vector((0, 0, -0.02))
    pivot = kit.parent(kit.empty(f'Leg{k}', hip), body)
    pivot.rotation_euler = (0, 0, math.atan2(d.y, d.x))
    knee = d * KNEE_OUT + Vector((0, 0, KNEE_Z))
    foot = d * FOOT_OUT + Vector((0, 0, 0.006))
    parts = [
        beam(f'Thigh{k}', m['shell'], hip, knee, 0.022, 0.016),
        sphere(f'Knee{k}', m['steel'], 0.014, knee, 8),
        beam(f'Shin{k}', m['steel_light'], knee, foot, 0.012),
        box(f'ThighStripe{k}', m['remap'], (0.012, 0.012, 0.03), hip.lerp(knee, 0.6) + Vector((0, 0, 0.009)), bevel=0.002),
        sphere(f'Foot{k}', m['shell_dark'], 0.01, foot, 8),
    ]
    kit.parent(kit.merge(f'LegMesh{k}', parts, hip), pivot)
    return pivot


def build():
    root, body = nod.start('LimpetDrone', 'Limpet', WALK_SPEED)
    m = materials()
    kit.parent(pod(m), body)
    legs = [leg(m, k, body) for k in range(4)]
    tip = Vector((0, 0, POD.z + POD_RADIUS * POD_STRETCH + 0.055))
    sensor = kit.parent(kit.merge('Sensor', [sphere('SensorLamp', m['lamp_red'], 0.011, tip, 8),
                                             sphere('SensorHalo', m['glow_red'], 0.024, tip, 8)], tip), body)
    glow = kit.parent(kit.merge('Thrust', [cylinder('Thrust', m['thrust'], 0.05, 0.03, POD - Vector((0, 0, POD_RADIUS * POD_STRETCH + 0.02)),
                                                    segments=14, bevel=0, radius2=0.02)],
                                POD - Vector((0, 0, POD_RADIUS * POD_STRETCH + 0.02))), body)
    mound = kit.parent(kit.merge('Mound', [
        cylinder('Mound', m['earth'], 0.13, 0.03, (0, 0, 0.012), segments=16, bevel=0.012, radius2=0.06),
        *[sphere(f'Clod{k}', m['earth'], 0.016, (0.12 * math.cos(k * 1.3), 0.12 * math.sin(k * 1.3), 0.008), 6) for k in range(5)],
    ]), root)

    one, hidden, zero = Vector((1, 1, 1)), Vector((kit.HIDDEN,) * 3), Vector((0, 0, 0))
    turn = [leg.rotation_euler.z for leg in legs]

    def pose(k, lift, swing=0.0):
        return Vector((0, lift, turn[k] + swing))

    # Idle: hovering, bobbing, the legs twitching; the thrusters glow
    for f in range(0, kit.IDLE_END + 1, 3):
        t = 2 * math.pi * f / kit.IDLE_END
        body.location = (0, 0, 0.008 * math.sin(t))
        body.keyframe_insert('location', frame=f)
        for k, obj in enumerate(legs):
            obj.rotation_euler = pose(k, -0.06 * max(0.0, math.sin(2 * t + k * 1.7)) ** 3)
            obj.keyframe_insert('rotation_euler', frame=f)
    for obj in (body, *legs):
        kit.to_track(obj, 'Idle')
    kit.keys(glow, 'scale', {f: one * (1 + 0.15 * math.sin(4 * math.pi * f / kit.IDLE_END)) for f in range(0, kit.IDLE_END + 1, 5)}, 'LINEAR')
    kit.to_track(glow, 'Idle')
    # Walk: skittering, the legs patter in two pairs, the body sways
    for f in range(WALK_FRAMES + 1):
        t = f / WALK_FRAMES
        body.location = (0, 0, 0.006 * abs(math.sin(2 * math.pi * t)))
        body.rotation_euler = (0.08, 0, 0.03 * math.sin(2 * math.pi * t))   # nose down, hurrying
        body.keyframe_insert('location', frame=f)
        body.keyframe_insert('rotation_euler', frame=f)
        for k, obj in enumerate(legs):
            p = (t + 0.5 * (k % 2)) % 1.0
            lift = -0.3 * math.sin(2 * math.pi * p) if p < 0.5 else 0.0
            swing = 0.25 * math.cos(2 * math.pi * p) * (1 if k in (0, 3) else -1)
            obj.rotation_euler = pose(k, lift, swing)
            obj.keyframe_insert('rotation_euler', frame=f)
    for obj in (body, *legs):
        kit.to_track(obj, 'Walk')
    kit.keys(glow, 'scale', {0: one * 1.3, WALK_FRAMES: one * 1.3}, 'LINEAR')
    kit.to_track(glow, 'Walk')
    # Deploy / Undeploy: legs up, a turn and down into the ground under a mound
    sunk = Vector((0, 0, -SINK))
    poses = [(body, 'location', {0: zero, 12: zero, 40: sunk, DEPLOY_FRAMES: sunk}),
             (body, 'rotation_euler', {0: zero, 12: zero, 40: Vector((0, 0, math.pi)), DEPLOY_FRAMES: Vector((0, 0, math.pi))}),
             (glow, 'scale', {0: one, 10: one * 1.6, 30: hidden, DEPLOY_FRAMES: hidden}),
             (mound, 'scale', {0: hidden, 14: hidden, 22: Vector((0.6, 0.6, 0.6)), 40: one, DEPLOY_FRAMES: one})]
    for k, obj in enumerate(legs):
        poses.append((obj, 'rotation_euler', {0: pose(k, 0), 2 + k: pose(k, 0), 16 + k: pose(k, FOLD), DEPLOY_FRAMES: pose(k, FOLD)}))
    for clip, order in (('Deploy', lambda f: f), ('Undeploy', lambda f: DEPLOY_FRAMES - f)):
        for obj, path, frames in poses:
            kit.keys(obj, path, {order(f): v for f, v in frames.items()})
            kit.to_track(obj, clip)
    for obj, path, keyed in poses:
        walker.hold(obj, path, keyed[DEPLOY_FRAMES], kit.IDLE_END, 'Deployed')
    # Deployed: the sensor tip blinks
    kit.blink(sensor, kit.flashes((0, 6), (30, 6)))
    kit.to_track(sensor, 'Deployed')
    for k, obj in enumerate(legs):
        obj.rotation_euler = pose(k, 0)
    body.location, body.rotation_euler = zero, zero
    glow.scale, mound.scale, sensor.scale = one, hidden, one
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [4], 'Deploy': [20, 45], 'Deployed': [0]}, scale=0.8, target=(0, 0, 0.12))
