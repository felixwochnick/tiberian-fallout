"""
Tiberian Fallout – Nod mobile stealth generator (SGEN), after Tiberian Sun Firestorm.

A low, dark tracked carrier with big road wheels showing along its sides: a wedge of
armour in front, the driver's slit and headlights in its slope; behind the middle the
emitter on a round collar in black and white zebra stripes with a red (house colour)
ring, under a glowing blue glass dome. The tail slopes down, striped red and black.
Two outriggers lie folded on the deck, one pair in front and one at the back.

When it deploys it plants the outriggers on the ground on both sides, raises the
emitter on its mast and lights it up; then it cloaks everything around it (the game
does that). Undeploying is the same backwards.

Nodes: "Emitter" (the dome on its mast), "EmitterRing" (turns while deployed),
"EmitterGlow" (the halo, hidden but while deployed), "Outrigger…" (the legs).
Clips (see nodvehicle.py for Idle and Walk):
    Deploy      once, 1.8 s: the outriggers swing out onto the ground, the emitter
                rises and lights up
    Deployed    loop, 2 s: the halo pulses, the ring turns
    Undeploy    once, 1.8 s: Deploy backwards

Run headless:

    blender -b --factory-startup --python blender/SGEN.py [-- --preview <dir>]

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

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'SGEN.glb')
BLEND = os.path.join(HERE, 'SGEN.blend')

WHEEL_RADIUS = 0.06
TRACK_X = 0.25
TRACK_WIDTH = 0.11
TRACK = (-0.42, 0.42)
WHEELS_Y = (-0.32, -0.16, 0.0, 0.16, 0.32)
WALK_FRAMES = 26
WALK_SPEED = 2 * math.pi * WHEEL_RADIUS / (WALK_FRAMES / kit.FPS)
DECK = 0.22                          # the deck's height
EMITTER = Vector((0, 0.08, DECK))     # the emitter's collar stands here at rest
RISE = 0.13                          # how far the mast lifts it
HINGE_X = 0.2                        # the outriggers' hinges on the deck's edges
# the outriggers' places along the deck (y): (front, back), left and right staggered so
# the folded legs lie side by side
OUTRIGGERS_Y = {-1: (-0.2, 0.35), 1: (-0.27, 0.28)}
HINGE_Z = DECK + 0.03
ARM = 0.2                            # the arm, level when planted
HOUSING = 0.13                       # the foot's housing at its end
FOLDED = math.radians(-90)           # lying inward on the deck (for the right side)
PLANTED = math.radians(90)           # level, out over the track
FOOT = HINGE_Z - HOUSING - 0.019   # how far the foot slides out to the ground
DEPLOY_FRAMES = 54
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = nod.materials()
    m.update({
        'zebra': material('ZebraWhite', srgb('#d6d4cc'), 0.6),
        'emitter': material('EmitterBlue', srgb('#2a7cff'), 0.1, 0.2, emission=srgb('#2a86ff'), strength=6, alpha=0.9),
        'emitter_glow': material('GlowBlue', (0, 0, 0), 1.0, emission=srgb('#3a9cff'), strength=3, alpha=0.18),
    })
    return m


def hull(m):
    """The armoured hull over the tracks; returns the hull and its fittings."""
    shell = kit.merge('Hull', [
        kit.hexahedron('HullMain', m['armour'], (
            (-0.2, -0.44, 0.08), (0.2, -0.44, 0.08), (0.2, 0.46, 0.08), (-0.2, 0.46, 0.08),
            (-0.18, -0.31, DECK), (0.18, -0.31, DECK), (0.18, 0.38, DECK), (-0.18, 0.38, DECK)), bevel=0.012),
        # the guards over the tracks: dark, red along their top edge
        *[kit.hexahedron(f'Guard{s}', m['armour_dark'], (
            (s * 0.19, -0.46, 0.12), (s * 0.32, -0.46, 0.12), (s * 0.32, 0.46, 0.12), (s * 0.19, 0.46, 0.12),
            (s * 0.19, -0.36, 0.17), (s * 0.31, -0.36, 0.17), (s * 0.31, 0.44, 0.17), (s * 0.19, 0.44, 0.17)), bevel=0.008)
          for s in (-1, 1)],
        *[kit.hexahedron(f'GuardStripe{s}', m['remap'], (
            (s * 0.3, -0.36, 0.165), (s * 0.322, -0.36, 0.165), (s * 0.322, 0.44, 0.165), (s * 0.3, 0.44, 0.165),
            (s * 0.3, -0.36, 0.178), (s * 0.318, -0.36, 0.178), (s * 0.318, 0.44, 0.178), (s * 0.3, 0.44, 0.178)), bevel=0.003)
          for s in (-1, 1)],
    ])
    parts = [
        box('DriverSlit', m['glass'], (0.12, 0.01, 0.018), (0.06, -0.37, 0.16), bevel=0.003, rotation=(math.radians(-55), 0, 0)),
        box('Hatch', m['armour_dark'], (0.08, 0.07, 0.014), (-0.09, -0.11, DECK + 0.005), bevel=0.004),
        # the emitter's well and its base plate
        cylinder('Well', m['dark'], 0.135, 0.012, EMITTER + Vector((0, 0, 0.001)), segments=24, bevel=0),
        beam('Antenna', m['steel'], (-0.16, 0.25, DECK), (-0.17, 0.29, 0.56), 0.006),
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (0.14, 0.46, 0.13), (0, 1, 0), 0.01),
    ]
    for s in (-1, 1):
        parts += [
            *detail.lamp(f'Headlight{s}', m['dark'], m['lamp_white'], (s * 0.13, -0.43, 0.11), (0, -1, 0.3), 0.015),
            *[box(f'HingeBlock{s}{k}', m['steel'], (0.03, 0.07, 0.03), (s * (HINGE_X + 0.005), y, HINGE_Z - 0.012), bevel=0.004)
              for k, y in enumerate(OUTRIGGERS_Y[s])],
        ]
    return shell, kit.merge('HullDetails', parts)


def tail(m):
    """The sloped tail behind the deck, striped red and black (not camouflaged)."""
    parts = [kit.hexahedron('TailPlate', m['dark'], (
        (-0.185, 0.38, DECK - 0.004), (0.185, 0.38, DECK - 0.004), (0.185, 0.462, 0.13), (-0.185, 0.462, 0.13),
        (-0.185, 0.38, DECK + 0.002), (0.185, 0.38, DECK + 0.002), (0.185, 0.462, 0.136), (-0.185, 0.462, 0.136)), bevel=0)]
    count, width = 8, 0.37 / 8
    for k in range(0, count, 2):
        x0 = -0.185 + k * width
        a, b = Vector((x0, 0.382, DECK + 0.003)), Vector((x0, 0.46, 0.137))
        shift = Vector((0.03, 0, 0))
        lo, hi = max(x0, -0.185), min(x0 + width, 0.185)
        parts.append(kit.hexahedron(f'TailStripe{k}', m['remap'], (
            Vector((lo, a.y, a.z)), Vector((hi, a.y, a.z)), Vector((min(hi + shift.x, 0.185), b.y, b.z)), Vector((min(lo + shift.x, 0.185), b.y, b.z)),
            Vector((lo, a.y, a.z + 0.003)), Vector((hi, a.y, a.z + 0.003)), Vector((min(hi + shift.x, 0.185), b.y, b.z + 0.003)),
            Vector((min(lo + shift.x, 0.185), b.y, b.z + 0.003))), bevel=0))
    return kit.merge('Tail', parts)


def emitter(m, body):
    """The emitter on its mast: collar in zebra stripes, the red ring, the blue dome
    and its halo. Returns (emitter, ring, glow)."""
    node = kit.parent(kit.empty('Emitter', EMITTER), body)
    c = EMITTER
    parts = [
        # the mast, hidden in the hull at rest
        cylinder('Mast', m['steel'], 0.05, RISE + 0.02, c - Vector((0, 0, (RISE + 0.02) / 2 - 0.005)), segments=14, bevel=0),
        cylinder('CollarCore', m['dark'], 0.112, 0.07, c + Vector((0, 0, 0.035)), segments=24, bevel=0.003),
    ]
    stripes = 18
    for k in range(stripes):
        a = 2 * math.pi * k / stripes
        parts.append(box(f'Zebra{k}', m['zebra'] if k % 2 == 0 else m['dark'], (0.04, 0.008, 0.066),
                         c + Vector((0.115 * math.sin(a), 0.115 * math.cos(a), 0.035)), bevel=0, rotation=(0, 0, -a)))
    parts += [
        cylinder('DomeSeat', m['armour_dark'], 0.1, 0.02, c + Vector((0, 0, 0.08)), segments=24, bevel=0.004),
    ]
    collar = kit.merge('EmitterCollar', parts, c)
    kit.parent(collar, node)
    # the red ring with its fins round the dome; turns while deployed
    ring = kit.merge('EmitterRingMesh', [
        cylinder('RingBand', m['remap'], 0.125, 0.03, c + Vector((0, 0, 0.1)), segments=28, bevel=0.004, radius2=0.11),
        *[box(f'RingFin{k}', m['armour_dark'], (0.012, 0.03, 0.03), c + Vector((0.13 * math.sin(k * math.pi / 3), 0.13 * math.cos(k * math.pi / 3), 0.1)),
              bevel=0.002, rotation=(0, 0, -k * math.pi / 3)) for k in range(6)],
    ], c)
    ring_node = kit.parent(kit.empty('EmitterRing', c), node)
    kit.parent(ring, ring_node)

    dome_centre = c + Vector((0, 0, 0.11))

    def half_sphere(bm):
        rings, around, r = 7, 24, 0.095
        verts = []
        for i in range(rings + 1):
            t = (math.pi / 2) * i / rings
            if i == rings:
                verts.append([bm.verts.new(dome_centre + Vector((0, 0, r)))])
                break
            verts.append([bm.verts.new(dome_centre + Vector((r * math.cos(t) * math.sin(2 * math.pi * j / around),
                                                             r * math.cos(t) * math.cos(2 * math.pi * j / around), r * math.sin(t))))
                          for j in range(around)])
        for i in range(rings - 1):
            for j in range(around):
                k = (j + 1) % around
                bm.faces.new((verts[i][j], verts[i][k], verts[i + 1][k], verts[i + 1][j]))
        for j in range(around):
            bm.faces.new((verts[rings - 1][j], verts[rings - 1][(j + 1) % around], verts[rings][0]))
        bm.faces.new(verts[0][::-1])

    dome = kit.finish(kit.mesh_object('Dome', half_sphere), m['emitter'], 0)
    dome.location = (0, 0, 0)
    kit.parent(kit.merge('EmitterDome', [dome,
                                          *[beam(f'DomeRib{k}', m['steel'], dome_centre + Vector((0.096 * math.sin(k * math.pi / 2), 0.096 * math.cos(k * math.pi / 2), 0)),
                                                 dome_centre + Vector((0.05 * math.sin(k * math.pi / 2), 0.05 * math.cos(k * math.pi / 2), 0.085)), 0.008)
                                            for k in range(4)],
                                          sphere('DomeCore', m['signal'], 0.03, dome_centre + Vector((0, 0, 0.03)), 12)], c), node)
    glow = kit.merge('EmitterGlow', [sphere('Halo', m['emitter_glow'], 0.135, dome_centre + Vector((0, 0, 0.03)), 16)], dome_centre + Vector((0, 0, 0.03)))
    kit.parent(glow, node)
    glow.scale = (kit.HIDDEN,) * 3
    return node, ring_node, glow


def outrigger(m, body, s, k):
    """A leg on its hinge at the deck's edge: an arm that swings out level, at its end
    the housing of a telescopic foot that pushes down onto the ground. Built pointing
    up (rotation 0); the foot (node OutriggerFoot…) slides along the arm's local x
    (s · x: down when planted). Returns (leg, foot), folded."""
    hinge = Vector((s * HINGE_X, OUTRIGGERS_Y[s][k], HINGE_Z))
    node = kit.parent(kit.empty(f'Outrigger{s}{k}', hinge), body)
    up, out = Vector((0, 0, 1)), Vector((s, 0, 0))
    tip = hinge + up * ARM
    leg = kit.merge(f'OutriggerLeg{s}{k}', [
        cylinder(f'Knuckle{s}{k}', m['steel'], 0.02, 0.05, hinge, rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
        box(f'Arm{s}{k}', m['armour_dark'], (0.03, 0.04, ARM), hinge + up * (ARM / 2), bevel=0.005),
        box(f'ArmStripe{s}{k}', m['remap'], (0.032, 0.042, 0.05), hinge + up * (ARM * 0.5), bevel=0.003),
        box(f'Housing{s}{k}', m['armour_dark'], (HOUSING, 0.044, 0.036), tip - up * 0.018 + out * (HOUSING / 2 - 0.015), bevel=0.005),
    ], hinge)
    kit.parent(leg, node)
    foot_at = tip - up * 0.018
    foot = kit.parent(kit.empty(f'OutriggerFoot{s}{k}', foot_at), node)
    kit.parent(kit.merge(f'FootMesh{s}{k}', [
        cylinder(f'Ram{s}{k}', m['steel_light'], 0.011, HOUSING + 0.018, foot_at + out * (HOUSING / 2 - 0.003), rotation=(0, math.pi / 2, 0), segments=10, bevel=0),
        box(f'Pad{s}{k}', m['steel'], (0.014, 0.07, 0.07), foot_at + out * (HOUSING + 0.012), bevel=0.003),
    ], foot_at), foot)
    node.rotation_euler = (0, s * FOLDED, 0)
    return node, foot


def deploy(emitter_node, ring, glow, legs, feet):
    """The clips Deploy, Deployed and Undeploy."""
    keys = kit.keys
    feet = [(foot, foot.location.copy()) for foot in feet]

    def foot_out(foot, s):   # along the arm's local s · x, in the parent's space (the arm's node)
        return Vector((s * FOOT, 0, 0))

    rest = emitter_node.location.copy()
    up = rest + Vector((0, 0, RISE))
    hidden, shown = Vector((kit.HIDDEN,) * 3), Vector((1, 1, 1))
    for clip, order in (('Deploy', lambda f: f), ('Undeploy', lambda f: DEPLOY_FRAMES - f)):
        for k, (node, s) in enumerate(legs):
            start = k % 2 * 3
            keys(node, 'rotation_euler', {order(0): Vector((0, s * FOLDED, 0)), order(start): Vector((0, s * FOLDED, 0)),
                                          order(start + 24): Vector((0, s * PLANTED, 0)), order(DEPLOY_FRAMES): Vector((0, s * PLANTED, 0))})
            kit.to_track(node, clip)
            foot, rest_foot = feet[k]
            keys(foot, 'location', {order(0): rest_foot, order(start + 22): rest_foot, order(start + 34): rest_foot + foot_out(foot, s),
                                    order(DEPLOY_FRAMES): rest_foot + foot_out(foot, s)})
            kit.to_track(foot, clip)
        keys(emitter_node, 'location', {order(0): rest, order(16): rest, order(40): up, order(DEPLOY_FRAMES): up})
        kit.to_track(emitter_node, clip)
        keys(glow, 'scale', {order(0): hidden, order(38): hidden, order(DEPLOY_FRAMES): shown})
        kit.to_track(glow, clip)
        keys(ring, 'rotation_euler', {order(0): Vector((0, 0, 0)), order(DEPLOY_FRAMES): Vector((0, 0, 0))}, 'LINEAR')
        kit.to_track(ring, clip)
    frames = kit.IDLE_END
    for node, s in legs:
        walker.hold(node, 'rotation_euler', Vector((0, s * PLANTED, 0)), frames, 'Deployed')
    for (foot, rest_foot), (_, s) in zip(feet, legs):
        walker.hold(foot, 'location', rest_foot + foot_out(foot, s), frames, 'Deployed')
        foot.location = rest_foot
    walker.hold(emitter_node, 'location', up, frames, 'Deployed')
    keys(glow, 'scale', {f: Vector((1, 1, 1)) * (1 + 0.12 * math.sin(2 * math.pi * f / frames)) for f in range(0, frames + 1, 5)}, 'LINEAR')
    kit.to_track(glow, 'Deployed')
    keys(ring, 'rotation_euler', {0: Vector((0, 0, 0)), frames: Vector((0, 0, math.pi / 3))}, 'LINEAR')  # one fin's step: seamless
    kit.to_track(ring, 'Deployed')
    for node, s in legs:
        node.rotation_euler = (0, s * FOLDED, 0)
    emitter_node.location = rest
    glow.scale = hidden
    ring.rotation_euler = (0, 0, 0)


def build():
    root, body = nod.start('NodStealthGenerator', 'StealthGenerator', WALK_SPEED)
    m = materials()
    for obj in hull(m):
        kit.parent(obj, body)
    emitter_node, ring, glow = emitter(m, body)
    rigs = [(outrigger(m, body, s, k), s) for s in (-1, 1) for k in range(2)]
    legs = [(leg, s) for (leg, _), s in rigs]
    feet = [foot for (_, foot), _ in rigs]
    for s in (-1, 1):
        kit.parent(nod.track(m, f'Track{s}', s * TRACK_X, TRACK_WIDTH, TRACK[0], TRACK[1], 0.11, 20), body)
    wheels = [kit.parent(nod.road_wheel(m, f'Wheel{s}{k}', (s * (TRACK_X + TRACK_WIDTH / 2 + 0.006), y, WHEEL_RADIUS + 0.004), WHEEL_RADIUS,
                                        0.024), body)
              for s in (-1, 1) for k, y in enumerate(WHEELS_Y)]
    nod.camouflage(kit.collection().objects)
    kit.parent(tail(m), body)   # stripes clean, without camouflage
    nod.drive(body, wheels, WALK_FRAMES, rock=0.003)
    deploy(emitter_node, ring, glow, legs, feet)
    body.location, body.rotation_euler = (0, 0, 0), (0, 0, 0)
    for w in wheels:
        w.rotation_euler = (0, 0, 0)
    nod.finish(root, SCALE)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Deploy': [14, 26, 40], 'Deployed': [10]}, scale=1.4, target=(0, 0, 0.2))
