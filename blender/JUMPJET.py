"""
Tiberian Fallout – GDI jumpjet infantry (JUMPJET), after Tiberian Sun: the light
infantry's soldier (E1.py: same rig, camouflage and clips, via infantry.py) with a
jet pack on his back – two nozzles below, two broad swept wings in the house colour
with dark edges – and a heavy rifle with a long shrouded barrel and a drum magazine.

Nodes: Soldier (armature, extras walkSpeed), SoldierBody (skinned mesh), Flash (empty
at the muzzle, on hand.R). The jet flames are part of the mesh on the bones flame.L
and flame.R; their scale is keyed in every clip: hidden on the ground, burning in
TakeOff, Fly, FireFly and Land.

Animations (glTF clips, in place: the game moves the unit and gives it its height in
the air; in flight the lowest point hangs HOVER above the node's origin)
    Idle, Walk, GoProne, Prone, Crawl, Die1, Die2, DieProne   as E1.py
    Fire     once, 0.4 s: a shot standing, the rifle kicks
    TakeOff  once, 0.6 s: crouches, the jets ignite, he jumps and draws his legs up
             into the hover
    Fly      loop, 1 s: hovering, legs slightly bent, a gentle sway, the flames
             flicker
    FireFly  once, 0.4 s: a shot while hovering
    Land     once, 0.6 s: stretches his legs to the ground, the jets die, he takes
             the landing in his knees and straightens up

Run headless:

    blender -b --factory-startup --python blender/JUMPJET.py [-- --preview <clip:frame,…> <dir>]

Modelled in metres like E1 (1.8 m tall, scaled to cells by E1.SCALE); Blender Z is up,
he looks along -Y (glTF +Z).
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import infantry as inf  # noqa: E402
from infantry import box, cylinder, soldier, srgb, material, tween, body_pose  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), 'public', 'models', 'JUMPJET.glb')
BLEND = os.path.join(HERE, 'JUMPJET.blend')

SHOT_FRAMES = 12
JUMP_FRAMES = 18
FLY_FRAMES = 30
HOVER = 0.12            # metres between the feet and the node's origin in flight
NOZZLE_X, NOZZLE_Y, NOZZLE_Z = 0.1, 0.25, 1.0
FLAME_LENGTH = 0.42
MUZZLE = soldier.RIFLE_BUTT + soldier.RIFLE_DIR * 1.02 + Vector((0, 0, 0.01))


def flame_bones(bones):
    return {f'flame.{side}': ((s * NOZZLE_X, NOZZLE_Y, NOZZLE_Z), (s * NOZZLE_X, NOZZLE_Y, NOZZLE_Z - FLAME_LENGTH), 'chest')
            for side, s in (('L', 1), ('R', -1))}


def body(bones):
    m = inf.base_materials()
    m.update({
        'vest': inf.soldier.house_shade('Vest', 1.0, 1.0, 0.55),
        'armour': material('Armour', srgb('#ab9f7a'), 0.7, 0.1),
        'helmet': material('Helmet', srgb('#7a775b'), 0.6, 0.1),
        'jet': material('JetPack', srgb('#5d6166'), 0.45, 0.6),
        'jetdark': material('JetPackDark', srgb('#2a2c30'), 0.5, 0.6),
        'wingedge': material('WingEdge', srgb('#34363a'), 0.5, 0.4),
        'stock': material('RifleStock', srgb('#4a4535'), 0.8),
        'flame': material('JetFlame', srgb('#ff7a1a'), 0.5, emission=srgb('#ff8a2a'), strength=6.0),
        'core': material('JetFlameCore', srgb('#fff1b0'), 0.5, emission=srgb('#fff4c0'), strength=10.0),
    })
    for key, colour in (('armour', '#2b2c31'), ('helmet', '#1c1d21'), ('jet', '#2e3034'), ('stock', '#242426'),
                        ('fatigue', '#1f2023'), ('pack', '#252629')):
        m[key]['nodColour'] = colour
    parts = []

    def add(bone, *objs):
        parts.extend((obj, bone) for obj in objs)

    inf.torso(add, m, m['vest'])
    for x in (-0.11, 0.11):
        add('hips', box(f'BeltPouch{x}', m['pack'], (0.07, 0.04, 0.06), (x, -0.115, 0.99), bevel=0.01))
    add('chest',
        box('VestPlate', m['armour'], (0.26, 0.03, 0.16), (0, -0.14, 1.32), bevel=0.012),
        # harness straps over the shoulders down to the belt
        box('StrapL', m['jetdark'], (0.04, 0.3, 0.02), (0.1, 0.0, 1.44), bevel=0.006),
        box('StrapR', m['jetdark'], (0.04, 0.3, 0.02), (-0.1, 0.0, 1.44), bevel=0.006))
    for i, x in enumerate((-0.12, -0.04, 0.04, 0.12)):
        add('chest', box(f'Pouch{i}', m['pack'], (0.065, 0.04, 0.075), (x, -0.145, 1.21), bevel=0.01))

    # ---- the jet pack: body with a house-colour band, fuel tanks, two nozzles below
    add('chest',
        box('JetBody', m['jet'], (0.3, 0.17, 0.4), (0, 0.22, 1.27), bevel=0.03),
        box('JetBand', m['remap'], (0.31, 0.18, 0.05), (0, 0.22, 1.36), bevel=0.01),
        box('JetPlate', m['jetdark'], (0.2, 0.03, 0.22), (0, 0.31, 1.24), bevel=0.01),
        cylinder('JetIntake', m['jetdark'], 0.07, 0.06, (0, 0.24, 1.49), segments=12, bevel=0.006))
    for side, s in (('L', 1), ('R', -1)):
        x = s * NOZZLE_X
        add('chest',
            cylinder(f'FuelTank{side}', m['jet'], 0.055, 0.34, (s * 0.12, 0.33, 1.27), segments=12, bevel=0.01),
            cylinder(f'FuelCap{side}', m['remap'], 0.04, 0.03, (s * 0.12, 0.33, 1.455), segments=10, bevel=0.004),
            cylinder(f'NozzleNeck{side}', m['jetdark'], 0.045, 0.06, (x, NOZZLE_Y, NOZZLE_Z + 0.08), segments=12, bevel=0),
            cylinder(f'Nozzle{side}', m['jetdark'], 0.062, 0.09, (x, NOZZLE_Y, NOZZLE_Z + 0.02), segments=12, bevel=0,
                     radius2=0.045),
            cylinder(f'NozzleGlow{side}', m['flame'], 0.05, 0.01, (x, NOZZLE_Y, NOZZLE_Z - 0.025), segments=12, bevel=0))
        # wings: broad, spread nearly flat to the sides with a little dihedral, swept back
        # (from above they read like the original's), a dark leading edge
        root = Vector((s * 0.13, 0.2, 1.4))
        span, chord = Vector((s * 0.97, 0.0, 0.24)), Vector((0.0, 1.0, -0.05))

        def wing(points):
            return [root + span * u + chord * v for u, v in points]

        add('chest',
            inf.plate(f'Wing{side}', m['remap'], wing(((0, 0.03), (0.56, 0.1), (0.64, 0.2), (0.52, 0.26), (0.38, 0.22),
                                                      (0.22, 0.33), (0, 0.29))), 0.022),
            inf.plate(f'WingEdge{side}', m['wingedge'], wing(((0, -0.005), (0.58, 0.07), (0.57, 0.11), (0, 0.04))), 0.03),
            inf.limb(f'WingRoot{side}', m['jetdark'], root + Vector((0, 0.02, -0.06)), root + span * 0.12 + chord * 0.1,
                     0.035, 0.025, 8))
        # the flames: an orange cone round a bright core, pointing down from the nozzle
        top = Vector((x, NOZZLE_Y, NOZZLE_Z - 0.03))
        add(f'flame.{side}',
            inf.limb(f'Flame{side}', m['flame'], top, top - Vector((0, 0, FLAME_LENGTH)), 0.05, 0.004, 10),
            inf.limb(f'FlameCore{side}', m['core'], top - Vector((0, 0, 0.01)), top - Vector((0, 0, FLAME_LENGTH * 0.55)),
                     0.03, 0.004, 8))

    inf.helmet_head(add, bones, m, m['helmet'], m['visor'])
    inf.limbs(add, bones, m)

    # ---- the heavy rifle in both hands
    butt, d = soldier.RIFLE_BUTT, soldier.RIFLE_DIR
    add('hand.R',
        inf.along('Stock', m['stock'], (0.05, 0.24, 0.1), butt, d, 0.12, -0.015),
        inf.along('Receiver', m['gun'], (0.06, 0.3, 0.085), butt, d, 0.38),
        inf.along('Drum', m['gun'], (0.06, 0.07), butt, d, 0.33, -0.09, cyl=True, segments=12),
        inf.along('PistolGrip', m['gun'], (0.035, 0.04, 0.08), butt, d, 0.24, -0.06),
        inf.along('Handguard', m['stock'], (0.065, 0.22, 0.06), butt, d, 0.6),
        inf.along('Scope', m['gun'], (0.024, 0.15), butt, d, 0.36, 0.07, cyl=True),
        inf.along('ScopeBand', m['remap'], (0.027, 0.03), butt, d, 0.36, 0.07, cyl=True),
        inf.along('Shroud', m['gun'], (0.026, 0.24), butt, d, 0.82, 0.01, cyl=True, segments=8),
        inf.along('MuzzleBrake', m['gun'], (0.034, 0.06), butt, d, 0.98, 0.01, cyl=True, segments=8))
    return soldier.finish_parts(parts)


# ---- poses for the clips: tween() values of E1.body_pose
HOVER_POSE = {'hx': 4, 'cx': 2, 'dx': -4, 'tl': -28, 'tr': -12, 'kl': 52, 'kr': 34, 'fl': 30, 'fr': 26}
CROUCH = {'hx': 12, 'sx': 4, 'cx': 6, 'dx': -12, 'tl': -55, 'tr': -55, 'kl': 100, 'kr': 100, 'fl': -50, 'fr': -50}
STRETCH = {'hx': -2, 'cx': -4, 'tl': -6, 'tr': 4, 'kl': 10, 'kr': 14, 'fl': 35, 'fr': 32}
REACH = {'hx': 2, 'tl': -10, 'tr': -4, 'kl': 14, 'kr': 10, 'fl': 12, 'fr': 10}
KICK = {'cx': -6, 'dx': 3, 'ual': -5, 'uar': -5, 'fal': -3, 'far': -3}


def flames(size):
    return {'flame.L': size, 'flame.R': size * 0.96}


def hover(f, frames=FLY_FRAMES):
    """The Fly loop's pose at frame f (also the end of TakeOff and the start of Land)."""
    t = 2 * math.pi * f / frames
    sway = {'tl': 4 * math.sin(t), 'tr': 4 * math.sin(t + 0.8), 'kl': 5 * math.sin(t + 0.4), 'kr': 5 * math.sin(t + 1.2),
            'cx': 1.5 * math.sin(t), 'hy': 1.5 * math.sin(t), 'dz': 10 * math.sin(t + 0.5)}
    return {k: HOVER_POSE.get(k, 0.0) + sway.get(k, 0.0) for k in set(HOVER_POSE) | set(sway)}


def flicker(f):
    return 1.0 + 0.12 * math.sin(f * 2.1) + 0.06 * math.sin(f * 5.3)


def animate(rig, bones, mesh):
    inf.flash(rig, 'hand.R', MUZZLE)

    kick = [(0, {}), (2, KICK), (SHOT_FRAMES, {})]
    inf.clip(rig, 'Fire', SHOT_FRAMES, lambda f: (body_pose(tween(kick, f)), Vector(), {}, 0.0), mesh)

    # TakeOff: crouch, ignite, jump (stretched), legs drawn up into the hover
    jump = [(0, {}), (5, CROUCH), (9, STRETCH), (JUMP_FRAMES, hover(0))]
    lift = [(0, {'z': 0}), (6, {'z': 0}), (10, {'z': HOVER + 0.14}), (JUMP_FRAMES, {'z': HOVER})]
    burn = [(0, {'s': inf.HIDDEN}), (5, {'s': inf.HIDDEN}), (8, {'s': 1.35}), (JUMP_FRAMES, {'s': 1.0})]
    inf.clip(rig, 'TakeOff', JUMP_FRAMES,
             lambda f: (body_pose(tween(jump, f)), Vector(), flames(tween(burn, f)['s']), tween(lift, f)['z']), mesh)

    inf.clip(rig, 'Fly', FLY_FRAMES,
             lambda f: (body_pose(hover(f)), Vector(), flames(flicker(f)), HOVER + 0.012 * math.sin(2 * math.pi * f / FLY_FRAMES)),
             mesh)

    def shot_in_flight(f):
        k = tween(kick, f)
        v = {n: hover(0).get(n, 0.0) + k.get(n, 0.0) for n in set(hover(0)) | set(k)}
        return body_pose(v), Vector(), flames(flicker(f)), HOVER

    inf.clip(rig, 'FireFly', SHOT_FRAMES, shot_in_flight, mesh)

    # Land: legs reach for the ground, touch down, the knees take it, stand up
    land = [(0, hover(0)), (7, REACH), (10, {**CROUCH, 'tl': -40, 'tr': -40, 'kl': 75, 'kr': 75, 'fl': -38, 'fr': -38}),
            (JUMP_FRAMES, {})]
    drop = [(0, {'z': HOVER}), (7, {'z': 0}), (JUMP_FRAMES, {'z': 0})]
    burn = [(0, {'s': 1.0}), (6, {'s': 0.8}), (9, {'s': inf.HIDDEN}), (JUMP_FRAMES, {'s': inf.HIDDEN})]
    inf.clip(rig, 'Land', JUMP_FRAMES,
             lambda f: (body_pose(tween(land, f)), Vector(), flames(tween(burn, f)['s']), tween(drop, f)['z']), mesh)


if __name__ == '__main__':
    inf.setup('rifle', body, extra_bones=flame_bones, scaled=('flame.L', 'flame.R'))
    inf.run(OUT, BLEND, animate)
