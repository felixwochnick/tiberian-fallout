"""
Tiberian Fallout – GDI Juggernaut (JUGG), after Tiberian Sun Firestorm.

A walking artillery piece: a boxy cabin in desert camouflage (raked front with a lit
window band, a roof rack, an antenna, house-colour bands) on a short pelvis and two
legs like the Titan's. Low in front of the cabin hangs the gun block with three long
barrels side by side. Two folded spades lie under the cabin pointing back like a tail.

Like the original it has to set up to fire: the legs crouch, the spades swing down
behind it into the ground, and the gun block raises its three barrels; set up, the
cabin with the guns turns towards the target.

Rig: empties, no armature (see walker.py): Body → pelvis, spades, Turret (the cabin)
→ Cradle (raised when deployed) → Cannon (the three barrels); two legs Hip → Knee →
Ankle.

Nodes the game uses: "Turret" (turns about the vertical when deployed), "Cannon" (the
barrels, tipped towards the target), "Flash0"/"Flash1"/"Flash2" (the barrels' muzzle
flashes, in turn).

Animations (glTF clips, merged from the NLA tracks of the same name)
    Idle          loop, 2 s: the body breathes, the legs stand
    Walk          loop, 1.4 s (two steps); the root's walkSpeed (glTF extras) is the
                  ground speed in cells per second at which the feet do not slide
    Fire          once, 1 s: the three barrels fire one after another and recoil
    Deploy        once, 2 s: crouch, spades down into the ground, barrels up
    Deployed      loop, 2 s: set up
    FireDeployed  once, 1 s: a salvo set up, heavy recoil, the body jolts
    Undeploy      once, 2 s: Deploy backwards

Run headless:

    blender -b --factory-startup --python blender/JUGG.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; the walker looks along -Y (glTF +Z). The
origin is on the ground between its feet.
"""
import math
import os
import sys

from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import detail  # noqa: E402
import nodvehicle as nod  # noqa: E402 – start(), finish(), main() (rest poses held in every clip)
import walker  # noqa: E402

OUT = os.path.join(nod.PROJECT, 'public', 'models', 'JUGG.glb')
BLEND = os.path.join(HERE, 'JUGG.blend')

ANKLE_Z = 0.03
THIGH = 0.22
SHIN = 0.22
HIP_Z = ANKLE_Z + THIGH + SHIN
HIP_X = 0.14
WALK_FRAMES = 42
SWING = 0.3
BEND = 0.7
FIRE_FRAMES = 30
DEPLOY_FRAMES = 60
CROUCH = 0.75                                   # hip angle when set up (knee twice that)
DROP = (THIGH + SHIN) * (1 - math.cos(CROUCH))  # how far the body sinks
TURRET = Vector((0, 0.02, HIP_Z + 0.07))        # the cabin's pivot over the pelvis
LOW, TOP = TURRET.z + 0.01, TURRET.z + 0.33     # the cabin's bottom and roof
FRONT, BACK = -0.17, 0.24
GUN = Vector((0, -0.2, LOW + 0.07))             # the gun block's trunnion, in front of the cabin
BARRELS_X = (-0.07, 0.0, 0.07)
BARREL = 0.5
RAISE = math.radians(-30)
SPADE_HINGE = Vector((0, 0.2, HIP_Z + 0.02))
SPADES_X = (-0.07, 0.07)
SCALE = 1.0

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'pod_dark': material('PodDark', srgb('#2b3036'), 0.6, 0.6),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'seam': material('Seam', srgb('#3a3a34'), 0.8),
        'flash': material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7),
    })
    return m


def camo(obj, root):
    obj.data.materials.clear()
    obj.data.materials.append(kit.camo_material(f'Camo_{obj.name}', root))
    return obj


def front(z):
    """The cabin's raked front (y) at height z."""
    return FRONT + (z - LOW) / (TOP - LOW) * 0.08


# --------------------------------------------------------------------------- body

def pelvis(m):
    """The pelvis between the hips (it does not turn) and the turret ring on it."""
    return kit.merge('Pelvis', [
        box('PelvisBlock', m['pod_dark'], (0.2, 0.22, 0.1), (0, 0.0, HIP_Z + 0.01), bevel=0.012),
        *[box(f'HipHousing{s}', m['pod_dark'], (0.05, 0.14, 0.09), (s * 0.115, 0.0, HIP_Z + 0.01), bevel=0.01) for s in (-1, 1)],
        cylinder('Ring', m['steel'], 0.13, 0.03, (TURRET.x, TURRET.y, TURRET.z - 0.0), segments=24),
        box('PelvisBand', m['hazard'], (0.204, 0.02, 0.025), (0, -0.105, HIP_Z + 0.03), bevel=0.003),
        *[box(f'PelvisStripe{k}', m['dark'], (0.02, 0.022, 0.026), (-0.08 + 0.04 * k, -0.106, HIP_Z + 0.03), bevel=0) for k in range(5)],
        box('SpadeMount', m['steel'], (0.2, 0.04, 0.04), (0, SPADE_HINGE.y - 0.02, SPADE_HINGE.z), bevel=0.005),
    ])


def cabin(m, root):
    """The cabin with its fittings; returns (shell, details), origin on the turret's pivot."""
    shell = camo(kit.merge('Cabin', [kit.hexahedron('Cabin', m['sand'], (
        (-0.19, FRONT, LOW), (0.19, FRONT, LOW), (0.19, BACK, LOW), (-0.19, BACK, LOW),
        (-0.17, front(TOP), TOP), (0.17, front(TOP), TOP), (0.17, BACK - 0.02, TOP), (-0.17, BACK - 0.02, TOP)), bevel=0.016)], TURRET), root)
    zw = LOW + 0.24
    parts = [
        box('Window', m['window'], (0.28, 0.012, 0.045), (0, front(zw) - 0.003, zw), bevel=0.004, rotation=(math.radians(-14), 0, 0)),
        box('WindowBrow', m['pod_dark'], (0.32, 0.03, 0.018), (0, front(zw + 0.04) - 0.01, zw + 0.04), bevel=0.004),
        *[box(f'WindowBar{k}', m['steel'], (0.01, 0.016, 0.05), (x, front(zw) - 0.006, zw), bevel=0.002, rotation=(math.radians(-14), 0, 0))
          for k, x in enumerate((-0.05, 0.05))],
        box('FrontBand', m['remap'], (0.34, 0.012, 0.03), (0, front(LOW + 0.16) - 0.004, LOW + 0.16), bevel=0.003, rotation=(math.radians(-14), 0, 0)),
        # the roof: a plate, a dark rack with slats as in the cameo, a hatch, the antenna
        box('Roof', m['sand_light'], (0.3, 0.3, 0.014), (0, 0.06, TOP + 0.006), bevel=0.004),
        box('Rack', m['pod_dark'], (0.2, 0.18, 0.03), (0.02, 0.1, TOP + 0.026), bevel=0.005),
        *[box(f'RackSlat{k}', m['steel'], (0.2, 0.01, 0.008), (0.02, 0.03 + 0.035 * k, TOP + 0.044), bevel=0) for k in range(5)],
        cylinder('Hatch', m['steel'], 0.04, 0.02, (-0.11, -0.03, TOP + 0.016), segments=16),
        cylinder('HatchLid', m['steel_light'], 0.032, 0.01, (-0.11, -0.03, TOP + 0.03), segments=16),
        beam('Antenna', m['steel'], (0.14, BACK - 0.05, TOP), (0.16, BACK - 0.02, TOP + 0.4), 0.006),
        box('AntennaBase', m['steel'], (0.03, 0.03, 0.03), (0.14, BACK - 0.05, TOP + 0.012), bevel=0.004),
        *detail.lamp('Searchlight', m['steel'], m['lamp_white'], (-0.15, front(TOP) + 0.02, TOP + 0.03), (0, -1, 0), 0.017),
        box('SearchlightMount', m['steel'], (0.03, 0.04, 0.02), (-0.15, front(TOP) + 0.05, TOP + 0.012), bevel=0.003),
        *detail.grille('BackVent', m['steel'], m['dark'], (0, BACK + 0.004, LOW + 0.16), 0.2, 0.1, 'Y', 5, 0.008),
        *detail.lamp('TailLight', m['dark'], m['lamp_red'], (0.13, BACK + 0.006, LOW + 0.26), (0, 1, 0), 0.011),
        # the trunnion cheeks carrying the gun block's pin
        *[kit.hexahedron(f'Cheek{s}', m['pod_dark'], (
            (s * 0.13, GUN.y - 0.03, GUN.z - 0.05), (s * 0.16, GUN.y - 0.03, GUN.z - 0.05), (s * 0.16, FRONT + 0.06, GUN.z - 0.05),
            (s * 0.13, FRONT + 0.06, GUN.z - 0.05),
            (s * 0.13, GUN.y - 0.03, GUN.z + 0.04), (s * 0.16, GUN.y - 0.03, GUN.z + 0.04), (s * 0.16, FRONT + 0.06, GUN.z + 0.08),
            (s * 0.13, FRONT + 0.06, GUN.z + 0.08)), bevel=0.006) for s in (-1, 1)],
    ]
    for s in (-1, 1):
        sx = s * 0.19
        parts += [
            box(f'SideBand{s}', m['remap'], (0.01, 0.38, 0.03), (s * 0.188, 0.03, LOW + 0.05), bevel=0.003),
            *detail.grille(f'SideVent{s}', m['steel'], m['dark'], (s * 0.184, 0.1, LOW + 0.17), 0.12, 0.06, 'X', 4, 0.008),
            *detail.rivets(f'SideRivets{s}', m['steel_light'], (s * 0.181, -0.08, LOW + 0.28), (s * 0.181, 0.2, LOW + 0.28), 6, axis='X'),
            *detail.seam(f'SideSeam{s}', m['seam'], (s * 0.185, -0.02, LOW + 0.08), (s * 0.18, -0.02, TOP - 0.02)),
            box(f'Step{s}', m['steel'], (0.03, 0.06, 0.01), (sx + s * 0.012, 0.16, LOW + 0.08), bevel=0.002),
        ]
    return shell, kit.merge('CabinDetails', parts, TURRET)


def gun(m, turret):
    """Cradle → Cannon with the gun block, the three barrels (each its own object, they
    recoil in turn) and their flashes; returns (cradle, barrels, flashes)."""
    cradle = kit.parent(kit.empty('Cradle', GUN), turret)
    pivot = kit.parent(walker.joint('Cannon', None, GUN), cradle)
    y0, y1 = GUN.y - 0.005, GUN.y - 0.17
    block = [
        kit.hexahedron('GunBlock', m['sand_light'], (
            (-0.12, y1, GUN.z - 0.06), (0.12, y1, GUN.z - 0.06), (0.12, y0, GUN.z - 0.06), (-0.12, y0, GUN.z - 0.06),
            (-0.11, y1 + 0.02, GUN.z + 0.06), (0.11, y1 + 0.02, GUN.z + 0.06), (0.11, y0, GUN.z + 0.05), (-0.11, y0, GUN.z + 0.05)), bevel=0.012),
        box('GunBand', m['remap'], (0.244, 0.03, 0.08), (0, y0 - 0.05, GUN.z - 0.005), bevel=0.004),
        cylinder('GunPin', m['steel_light'], 0.025, 0.3, GUN, rotation=(0, math.pi / 2, 0), segments=12),
        box('GunFace', m['pod_dark'], (0.23, 0.012, 0.1), (0, y1 - 0.004, GUN.z), bevel=0.003),
        *detail.rivets('GunRivets', m['steel_light'], (-0.09, y1 + 0.03, GUN.z + 0.062), (0.09, y1 + 0.03, GUN.z + 0.062), 5, axis='Z'),
    ]
    kit.parent(kit.merge('GunBlock', block, GUN), pivot)
    barrels, flashes = [], []
    for k, x in enumerate(BARRELS_X):
        at = Vector((x, y1, GUN.z))
        tip = at - Vector((0, BARREL, 0))
        parts = [
            cylinder(f'Sleeve{k}', m['steel'], 0.03, 0.12, at - Vector((0, 0.04, 0)), rotation=(math.pi / 2, 0, 0), segments=14),
            cylinder(f'Tube{k}', m['steel_light'], 0.02, BARREL - 0.08, at - Vector((0, (BARREL - 0.08) / 2 + 0.06, 0)), rotation=(math.pi / 2, 0, 0),
                     segments=12),
            cylinder(f'Collar{k}', m['steel'], 0.025, 0.025, at - Vector((0, 0.28, 0)), rotation=(math.pi / 2, 0, 0), segments=12),
            cylinder(f'Brake{k}', m['pod_dark'], 0.028, 0.05, tip + Vector((0, 0.025, 0)), rotation=(math.pi / 2, 0, 0), segments=12),
            cylinder(f'Bore{k}', m['dark'], 0.012, 0.004, tip - Vector((0, 0.001, 0)), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0),
        ]
        barrels.append(kit.parent(kit.merge(f'Barrel{k}', parts, at), pivot))
        muzzle = tip - Vector((0, 0.05, 0))
        flash = kit.merge(f'Flash{k}', [sphere(f'Flash{k}_{j}', m['flash'], 0.045 - 0.012 * j, muzzle - Vector((0, 0.045 * j, 0)), 10)
                                        for j in range(3)], muzzle)
        flash.scale = (kit.HIDDEN,) * 3
        flashes.append(kit.parent(flash, pivot))
    return cradle, barrels, flashes


def spade(m, x):
    """A spade, built set up (down and back into the ground behind the crouching
    walker); origin on its hinge. Returns it and its stowed rotation (pointing back,
    a little up, under the cabin)."""
    hinge = Vector((x, SPADE_HINGE.y, SPADE_HINGE.z))
    foot = Vector((x, SPADE_HINGE.y + 0.24, 0.02 + DROP))   # on the ground once the body has sunk
    d = foot - hinge
    parts = [
        cylinder(f'SpadeKnuckle{x}', m['steel'], 0.022, 0.06, hinge, rotation=(0, math.pi / 2, 0), segments=10),
        beam(f'SpadeArm{x}', m['pod_dark'], hinge, foot, 0.04, 0.03),
        beam(f'SpadeRam{x}', m['steel_light'], hinge.lerp(foot, 0.15), hinge.lerp(foot, 0.75), 0.016),
        kit.hexahedron(f'SpadeBlade{x}', m['steel_light'], (
            (x - 0.045, foot.y - 0.02, foot.z - 0.02), (x + 0.045, foot.y - 0.02, foot.z - 0.02),
            (x + 0.045, foot.y + 0.03, foot.z - 0.02), (x - 0.045, foot.y + 0.03, foot.z - 0.02),
            (x - 0.05, foot.y - 0.04, foot.z + 0.05), (x + 0.05, foot.y - 0.04, foot.z + 0.05),
            (x + 0.05, foot.y + 0.01, foot.z + 0.06), (x - 0.05, foot.y + 0.01, foot.z + 0.06)), bevel=0.004),
        box(f'SpadeStripe{x}', m['hazard'], (0.044, 0.03, 0.03), hinge.lerp(foot, 0.45), bevel=0.002),
    ]
    obj = kit.merge(f'Spade{"R" if x > 0 else "L"}', parts, hinge)
    return obj, Vector((math.radians(8) - math.atan2(d.z, d.y), 0, 0))


# --------------------------------------------------------------------------- legs

def leg(m, root, name, hip, body):
    """One heavy leg on its joints, centred under the hip; returns the walker.Leg."""
    joints = walker.Leg(name, body, hip, THIGH, SHIN)
    knee, ankle = hip - Vector((0, 0, THIGH)), hip - Vector((0, 0, THIGH + SHIN))
    x, y = hip.x, hip.y
    s = 1 if x > 0 else -1
    thigh = camo(kit.merge(f'{name}Thigh', [kit.hexahedron(f'{name}Thigh', m['sand'], (
        (x - 0.055, y - 0.065, knee.z + 0.02), (x + 0.055, y - 0.065, knee.z + 0.02), (x + 0.055, y + 0.055, knee.z + 0.02), (x - 0.055, y + 0.055, knee.z + 0.02),
        (x - 0.065, y - 0.085, hip.z - 0.02), (x + 0.065, y - 0.085, hip.z - 0.02), (x + 0.065, y + 0.075, hip.z - 0.02), (x - 0.065, y + 0.075, hip.z - 0.02)),
        bevel=0.014)], hip), root)
    kit.parent(thigh, joints.hip)
    top, low = hip.z - 0.04, knee.z + 0.05
    ox = x + s * 0.062
    kit.parent(kit.merge(f'{name}ThighDetails', [
        box(f'{name}ThighPlate', m['sand_light'], (0.09, 0.012, 0.08), (x, y - 0.083, hip.z - 0.09), bevel=0.003),
        *detail.rivets(f'{name}ThighRivetsF', m['steel_light'], (ox, y - 0.045, top), (ox, y - 0.045, low), 4, axis='X'),
        *detail.rivets(f'{name}ThighRivetsB', m['steel_light'], (ox, y + 0.045, top), (ox, y + 0.045, low), 4, axis='X'),
        cylinder(f'{name}HipJoint', m['steel'], 0.055, 0.09, hip, rotation=(0, math.pi / 2, 0), segments=16),
    ], hip), joints.hip)
    shin = camo(kit.merge(f'{name}Shin', [kit.hexahedron(f'{name}Shin', m['sand'], (
        (x - 0.06, y - 0.075, ankle.z + 0.05), (x + 0.06, y - 0.075, ankle.z + 0.05), (x + 0.06, y + 0.055, ankle.z + 0.05), (x - 0.06, y + 0.055, ankle.z + 0.05),
        (x - 0.05, y - 0.065, knee.z - 0.01), (x + 0.05, y - 0.065, knee.z - 0.01), (x + 0.05, y + 0.045, knee.z - 0.01), (x - 0.05, y + 0.045, knee.z - 0.01)),
        bevel=0.014)], knee), root)
    kit.parent(shin, joints.knee)
    kit.parent(kit.merge(f'{name}Knee', [
        cylinder(f'{name}KneeJoint', m['steel'], 0.045, 0.14, knee, rotation=(0, math.pi / 2, 0), segments=14),
        box(f'{name}KneeCap', m['pod_dark'], (0.1, 0.05, 0.08), knee + Vector((0, -0.07, 0.0)), bevel=0.012),
        box(f'{name}ShinPlate', m['remap'], (0.09, 0.02, 0.1), knee + Vector((0, -0.077, -0.11)), bevel=0.006, rotation=(math.radians(-3), 0, 0)),
        beam(f'{name}Piston', m['steel_light'], knee + Vector((0, 0.06, -0.02)), ankle + Vector((0, 0.055, 0.07)), 0.02),
        beam(f'{name}PistonSleeve', m['steel'], knee + Vector((0, 0.057, -0.02)), knee + Vector((0, 0.057, -0.1)), 0.03),
        *detail.grille(f'{name}ShinVent', m['steel'], m['dark'], (x + s * 0.058, y - 0.01, knee.z - 0.11), 0.06, 0.06, 'X', 3, 0.008),
        box(f'{name}AnkleGuard', m['pod_dark'], (0.11, 0.03, 0.05), ankle + Vector((0, -0.082, 0.06)), bevel=0.006),
    ], knee), joints.knee)
    foot = [
        box(f'{name}Foot', m['pod_dark'], (0.14, 0.18, 0.045), ankle + Vector((0, -0.02, -0.008)), bevel=0.01),
        box(f'{name}Heel', m['steel'], (0.07, 0.07, 0.035), ankle + Vector((0, 0.1, -0.013)), bevel=0.008),
        cylinder(f'{name}AnkleJoint', m['steel'], 0.032, 0.11, ankle + Vector((0, 0, 0.02)), rotation=(0, math.pi / 2, 0), segments=12),
    ]
    for t in (-1, 0, 1):
        foot.append(box(f'{name}Toe{t}', m['steel'], (0.04, 0.09, 0.035), ankle + Vector((t * 0.045, -0.135, -0.013)), bevel=0.008, rotation=(0, 0, t * 0.2)))
        foot.append(box(f'{name}Claw{t}', m['dark'], (0.03, 0.035, 0.022), ankle + Vector((t * 0.055, -0.19, -0.02)), bevel=0.005,
                        rotation=(math.radians(-15), 0, t * 0.2)))
    kit.parent(kit.merge(f'{name}Foot', foot, ankle), joints.ankle)
    return joints


# --------------------------------------------------------------------------- clips

def recoil(barrels, flashes, clip, frames, kick, step):
    """The barrels fire one after another (`step` frames apart) and recoil."""
    hidden = Vector((kit.HIDDEN,) * 3)
    for k, (barrel, flash) in enumerate(zip(barrels, flashes)):
        rest = barrel.location.copy()
        f = k * step
        kit.keys(barrel, 'location', {0: rest, **({f: rest} if f else {}), f + 2: rest + kick, f + 5: rest + kick, f + 16: rest, frames: rest})
        kit.to_track(barrel, clip)
        on = {0: hidden} if f else {}
        kit.keys(flash, 'scale', {**on, f: Vector((1, 1, 1)), f + 2: Vector((1.3, 1.6, 1.3)), f + 4: hidden, frames: hidden}, 'CONSTANT')
        kit.to_track(flash, clip)
        barrel.location = rest
        flash.scale = hidden


def deploy(body, legs, cradle, spades, barrels, flashes):
    """Deploy, Deployed, FireDeployed and Undeploy (Deploy backwards)."""
    level = Vector((0, 0, 0))
    # the crouch keyed frame by frame: the body sinks exactly as far as the bent legs
    # shorten, so the feet stay on the ground
    def bend(f):
        t = min(max((f - 4) / 30, 0.0), 1.0)
        return CROUCH * t * t * (3 - 2 * t)
    frames = list(range(0, DEPLOY_FRAMES + 1, 2))
    poses = []
    for leg in legs:
        for obj, factor in zip((leg.hip, leg.knee, leg.ankle), (-1, 2, -1)):
            poses.append((obj, 'rotation_euler', {f: Vector((factor * bend(f), 0, 0)) for f in frames}))
    poses.append((body, 'location', {f: Vector((0, 0, -(THIGH + SHIN) * (1 - math.cos(bend(f))))) for f in frames}))
    for k, (obj, stowed) in enumerate(spades):
        poses.append((obj, 'rotation_euler', {0: stowed, 10 + 2 * k: stowed, 34 + 2 * k: level, DEPLOY_FRAMES: level}))
    raised = Vector((RAISE, 0, 0))
    poses.append((cradle, 'rotation_euler', {0: level, 32: level, 56: raised, DEPLOY_FRAMES: raised}))
    for clip, order in (('Deploy', lambda f: f), ('Undeploy', lambda f: DEPLOY_FRAMES - f)):
        for obj, path, frames in poses:
            kit.keys(obj, path, {order(f): v for f, v in frames.items()})
            kit.to_track(obj, clip)
    for clip, frames in (('Deploy', DEPLOY_FRAMES), ('Undeploy', DEPLOY_FRAMES), ('Deployed', kit.IDLE_END)):
        walker.hide(flashes, frames, clip)
    for clip, frames in (('Deployed', kit.IDLE_END), ('FireDeployed', FIRE_FRAMES)):
        for obj, path, keyed in poses:
            if obj is body and clip == 'FireDeployed':
                continue
            walker.hold(obj, path, keyed[DEPLOY_FRAMES], frames, clip)
    # the salvo set up: a heavy recoil, the body jolts back and settles on its spades
    recoil(barrels, flashes, 'FireDeployed', FIRE_FRAMES, Vector((0, 0.08, 0)), 3)
    sunk = Vector((0, 0, -DROP))
    kit.keys(body, 'location', {0: sunk, 3: sunk + Vector((0, 0.012, -0.006)), 12: sunk, FIRE_FRAMES: sunk})
    kit.keys(body, 'rotation_euler', {0: level, 3: Vector((math.radians(-2), 0, 0)), 12: Vector((math.radians(0.4), 0, 0)), 18: level,
                                      FIRE_FRAMES: level})
    kit.to_track(body, 'FireDeployed')


def build():
    root, body = nod.start('GDIJuggernaut', 'Juggernaut', 0.0)
    m = materials()
    kit.parent(pelvis(m), body)
    turret = kit.parent(kit.empty('Turret', TURRET), body)
    for obj in cabin(m, root):
        kit.parent(obj, turret)
    cradle, barrels, flashes = gun(m, turret)
    spades = []
    for x in SPADES_X:
        obj, stowed = spade(m, x)
        spades.append((kit.parent(obj, body), stowed))
    legs = [leg(m, root, f'Leg{"R" if s > 0 else "L"}', Vector((s * HIP_X, 0, HIP_Z)), body) for s in (-1, 1)]
    kit.bake_camo(256)
    for obj, stowed in spades:
        obj.rotation_euler = stowed
    speed = walker.walk(legs, body, [], WALK_FRAMES, SWING, BEND, hidden=flashes)
    walker.idle(body, [], legs, sway=0.006, hidden=flashes)
    recoil(barrels, flashes, 'Fire', FIRE_FRAMES, Vector((0, 0.05, 0)), 4)
    deploy(body, legs, cradle, spades, barrels, flashes)
    walker.rest(body, [body, cradle, *[j for g in legs for j in (g.hip, g.knee, g.ankle)]])
    for obj, stowed in spades:
        obj.rotation_euler = stowed
    for flash in flashes:
        flash.scale = (kit.HIDDEN,) * 3
    root['walkSpeed'] = round(speed, 4)
    nod.finish(root, SCALE)
    print('walk speed', root['walkSpeed'], 'cells/s', flush=True)
    return len(kit.collection().objects)


if __name__ == '__main__':
    nod.main(build, OUT, BLEND, {'Idle': [0], 'Walk': [10], 'Fire': [1], 'Deploy': [20, 40, 59], 'FireDeployed': [4]},
             scale=1.7, target=(0, -0.15, 0.45))
