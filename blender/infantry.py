"""
Tiberian Fallout – shared parts for infantry built on the light infantry's rig (E1.py)
that need more than E1's own variants: the medic (MEDIC.py), the jumpjet infantry
(JUMPJET.py) and the cyborg (CYBORG.py).

E1.py stays as it is; this module plugs into it: `setup()` swaps E1's skeleton, hands
and body for the unit's own (all of E1's clips are then built on them), bones listed
as `scaled` get their scale keyed in every clip (the jumpjet's flames: hidden on the
ground, shown in flight), `clip()` keys the unit's extra clips and `run()` is the
common main (build, extra clips, export, .blend, previews).
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import E1 as soldier  # noqa: E402

kit = soldier.kit
box, cylinder, sphere, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.srgb, kit.material
limb, dome, rotation, tween, body_pose = soldier.limb, soldier.dome, soldier.rotation, soldier.tween, soldier.body_pose

HIDDEN = 1e-3           # scale of a hidden part (zero would make degenerate matrices)
SCALED = []             # bones whose scale is keyed in every clip
EXTRA_BONES = None      # bones → {name: (head, tail, parent)} added to the skeleton
SHOULDER_X, HIP_X = 0.19, 0.1


# --------------------------------------------------------------------------- rig

def skeleton():
    """E1's skeleton with the shoulder and hip width of the unit and its extra bones."""
    bones = {
        'hips': ((0, 0, 0.93), (0, 0, 1.03), None),
        'spine': ((0, 0, 1.03), (0, 0, 1.2), 'hips'),
        'chest': ((0, 0, 1.2), (0, 0, 1.45), 'spine'),
        'neck': ((0, 0, 1.45), (0, 0, 1.56), 'chest'),
        'head': ((0, 0, 1.56), (0, 0, 1.8), 'neck'),
    }
    for side, s in (('L', 1), ('R', -1)):
        shoulder = Vector((s * SHOULDER_X, -0.03, 1.42))
        hand, wrist, pole = soldier.hands()[side]
        reach = (wrist - shoulder).length / (soldier.UPPER_ARM + soldier.FOREARM)
        if reach > 0.999:
            print(f'warning: arm {side} cannot reach its hold ({reach:.2f})')
        joint = soldier.elbow(shoulder, wrist, soldier.UPPER_ARM, soldier.FOREARM, pole)
        bones[f'upper_arm.{side}'] = (shoulder, joint, 'chest')
        bones[f'forearm.{side}'] = (joint, wrist, f'upper_arm.{side}')
        bones[f'hand.{side}'] = (wrist, hand + (hand - wrist).normalized() * 0.03, f'forearm.{side}')
        x = s * HIP_X
        bones[f'thigh.{side}'] = ((x, 0, 0.93), (x + s * 0.01, -0.01, 0.5), 'hips')
        bones[f'shin.{side}'] = ((x + s * 0.01, -0.01, 0.5), (x + s * 0.01, 0, 0.09), f'thigh.{side}')
        bones[f'foot.{side}'] = ((x + s * 0.01, 0, 0.09), (x + s * 0.01, -0.14, 0.03), f'shin.{side}')
    bones = {name: (Vector(h), Vector(t), p) for name, (h, t, p) in bones.items()}
    if EXTRA_BONES:
        bones.update({name: (Vector(h), Vector(t), p) for name, (h, t, p) in EXTRA_BONES(bones).items()})
    return bones


_key_pose, _armature = soldier.key_pose, soldier.armature


def key_pose(rig, frame):
    _key_pose(rig, frame)
    for name in SCALED:
        rig.pose.bones[name].keyframe_insert('scale', frame=frame)


def armature(bones):
    rig = _armature(bones)
    for name in SCALED:
        rig.pose.bones[name].scale = (HIDDEN,) * 3
    return rig


def setup(weapon, body, hands=None, shoulder=0.19, hip=0.1, extra_bones=None, scaled=(), scale=None):
    """Plugs the unit into E1.py: `weapon` picks E1's behaviour in its clips ('rifle':
    arms on the weapon, 'tools': hanging arms that swing), `body(bones)` returns the
    rigid parts as (object, bone), `hands()` the holds of the hands (E1.hands)."""
    global SHOULDER_X, HIP_X, EXTRA_BONES
    soldier.WEAPON = weapon
    soldier.body = body
    if hands:
        soldier.hands = hands
    if scale:
        soldier.SCALE = scale
    SHOULDER_X, HIP_X, EXTRA_BONES = shoulder, hip, extra_bones
    SCALED[:] = scaled
    soldier.skeleton = skeleton
    soldier.key_pose = key_pose
    soldier.armature = armature


# --------------------------------------------------------------------------- clips

def clip(rig, name, frames, pose, body=None):
    """Keys a clip from pose(f) → (deltas, offset, scales, lift): `scales` maps bones of
    SCALED to their scale (missing: hidden); with `body` given and `lift` not None, each
    frame is raised or lowered so the lowest point of the body (hidden parts left out)
    is `lift` above the ground (E1.grounded_clip). Needs the rig unscaled."""
    ad = rig.animation_data
    poses = [pose(f) for f in range(frames + 1)]
    if body is not None:
        muted = [(track, track.mute) for track in ad.nla_tracks]
        for track, _ in muted:
            track.mute = True
        ad.action = None
        for i, (deltas, offset, scales, lift) in enumerate(poses):
            if lift is None:
                continue
            soldier.set_pose(rig, deltas, offset)
            low = soldier.lowest_point(body)
            poses[i] = (deltas, offset - Vector((0, 0, low - lift)), scales, lift)
        for track, mute in muted:
            track.mute = mute
    ad.action = bpy.data.actions.new(name)
    for f, (deltas, offset, scales, _) in enumerate(poses):
        soldier.set_pose(rig, deltas, offset)
        for bone in SCALED:
            rig.pose.bones[bone].scale = (scales.get(bone, HIDDEN),) * 3
        key_pose(rig, f)
    kit.to_track(rig, name)
    soldier.set_pose(rig, {})
    for bone in SCALED:
        rig.pose.bones[bone].scale = (HIDDEN,) * 3


def flash(rig, bone, at):
    """The empty "Flash" on `bone` at `at` (rest pose): where the game starts the shots."""
    obj = soldier.muzzle(rig, bone, at)
    obj.name = 'Flash'
    return obj


# --------------------------------------------------------------------------- mesh

def plate(name, mat, outline, thickness, bevel=0.006):
    """A flat plate: the (planar) outline extruded by `thickness` along its normal."""
    pts = [Vector(p) for p in outline]
    normal = (pts[1] - pts[0]).cross(pts[2] - pts[0]).normalized()

    def build(bm):
        bottom = [bm.verts.new(p) for p in pts]
        top = [bm.verts.new(p + normal * thickness) for p in pts]
        bm.faces.new(bottom)
        bm.faces.new(list(reversed(top)))
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((bottom[i], bottom[j], top[j], top[i]))

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def along(name, mat, size, start, direction, at, up=0.0, cyl=False, segments=10, radius2=None):
    """A part of a gun along `direction` from `start`: a box (size x, y = along, z) or a
    cylinder (size = radius, length) centred `at` along it, `up` above its axis."""
    rot = direction.to_track_quat('Y', 'Z').to_matrix().to_4x4()
    if cyl:
        obj = cylinder(name, mat, size[0], size[1], (0, 0, 0), rotation=(math.pi / 2, 0, 0),
                       segments=segments, bevel=0, radius2=radius2)
    else:
        obj = box(name, mat, size, (0, 0, 0), bevel=0.006)
    kit.bake_modifiers(obj)
    obj.data.transform(Matrix.Translation(start) @ rot @ Matrix.Translation(Vector((0, at, up))))
    return obj


def cross(name, mat, centre, size, normal_axis, thickness=0.012):
    """A red cross: two bars of width size/3 on the plane across `normal_axis` (0 x, 1 y, 2 z)."""
    w = size / 3
    if normal_axis == 0:
        a, b = (thickness, size, w), (thickness, w, size)
    elif normal_axis == 1:
        a, b = (size, thickness, w), (w, thickness, size)
    else:
        a, b = (size, w, thickness), (w, size, thickness)
    return [box(f'{name}H', mat, a, centre, bevel=0.002), box(f'{name}V', mat, b, centre, bevel=0.002)]


def torso(add, m, vest):
    """E1's pelvis, belt, belly, vest and collar (camouflage on pelvis and belly)."""
    add('hips',
        kit.frustum('Pelvis', m['fatigue'], (0.32, 0.2), (0.3, 0.19), 0.13, (0, 0, 0.87), bevel=0.02),
        box('Belt', m['boot'], (0.33, 0.21, 0.045), (0, 0, 1.0), bevel=0.01))
    add('spine', kit.frustum('Belly', m['fatigue'], (0.29, 0.19), (0.33, 0.21), 0.2, (0, 0, 1.01), bevel=0.02))
    add('chest',
        kit.frustum('Vest', vest, (0.36, 0.25), (0.42, 0.27), 0.27, (0, 0, 1.17), bevel=0.03),
        kit.frustum('Collar', vest, (0.24, 0.18), (0.19, 0.15), 0.05, (0, 0, 1.44), bevel=0.01))


def helmet_head(add, bones, m, helmet, visor, stripe=True):
    """Neck, face and E1's helmet with visor (and the house-colour stripe); returns the
    centre of the head."""
    neck_top = bones['head'][0]
    add('neck', limb('Neck', m['skin'], bones['neck'][0], neck_top + Vector((0, 0, 0.03)), 0.055, 0.05))
    centre = neck_top + Vector((0, -0.01, 0.1))
    add('head',
        dome('Face', m['skin'], 0.095, centre, -1.0, (0.85, 0.95, 1.1)),
        dome('Helmet', helmet, 0.125, centre + Vector((0, 0.01, 0.0)), 0.0, (1.0, 1.08, 1.0)),
        box('HelmetRim', helmet, (0.25, 0.26, 0.025), centre + Vector((0, 0.01, 0.0)), bevel=0.01),
        box('Visor', visor, (0.17, 0.035, 0.05), centre + Vector((0, -0.105, -0.01)), bevel=0.012))
    if stripe:
        add('head', box('HelmetStripe', m['remap'], (0.03, 0.27, 0.02), centre + Vector((0, 0.005, 0.122)), bevel=0.006))
    return centre


def limbs(add, bones, m, hands=True):
    """E1's arms (sleeves, house-colour shoulder pads, gloves) and legs (trousers, knee
    pads, boots); the camouflage comes with E1.finish_parts."""
    for side in ('L', 'R'):
        s = 1 if side == 'L' else -1
        shoulder, joint, wrist = bones[f'upper_arm.{side}'][0], bones[f'forearm.{side}'][0], bones[f'hand.{side}'][0]
        add(f'upper_arm.{side}',
            limb(f'UpperArm{side}', m['fatigue'], shoulder, joint, 0.058, 0.048),
            dome(f'ShoulderPad{side}', m['remap'], 0.075, shoulder + Vector((s * 0.02, 0, 0.0)), -0.2, (1.0, 1.05, 0.9)),
            sphere(f'Elbow{side}', m['fatigue'], 0.048, joint, 10))
        add(f'forearm.{side}',
            limb(f'Forearm{side}', m['fatigue'], joint, wrist, 0.046, 0.038),
            limb(f'Cuff{side}', m['glove'], wrist + (joint - wrist).normalized() * 0.06, wrist, 0.045, 0.042))
        if hands:
            add(f'hand.{side}', box(f'Hand{side}', m['glove'], (0.06, 0.08, 0.09),
                                    (wrist + bones[f'hand.{side}'][1]) / 2, bevel=0.015))
    for side in ('L', 'R'):
        hip, knee, ankle = bones[f'thigh.{side}'][0], bones[f'shin.{side}'][0], bones[f'foot.{side}'][0]
        add(f'thigh.{side}',
            limb(f'Thigh{side}', m['fatigue'], hip, knee, 0.095, 0.065),
            box(f'LegPouch{side}', m['pack'], (0.04, 0.08, 0.1), hip.lerp(knee, 0.45) + Vector((hip.x * 0.75, 0, 0)), bevel=0.01))
        add(f'shin.{side}',
            limb(f'Shin{side}', m['fatigue'], knee, ankle + Vector((0, 0, 0.12)), 0.058, 0.05),
            sphere(f'KneePad{side}', m['boot'], 0.055, knee + Vector((0, -0.03, 0)), 10),
            limb(f'BootShaft{side}', m['boot'], ankle + Vector((0, 0, 0.17)), ankle - Vector((0, 0, 0.04)), 0.055, 0.058))
        add(f'foot.{side}',
            box(f'Boot{side}', m['boot'], (0.11, 0.25, 0.07), ankle + Vector((0, -0.055, -0.055)), bevel=0.02))


def base_materials():
    """E1's materials for fatigues, boots, gloves, skin, packs and the house colour."""
    return {
        'fatigue': material('Fatigue', srgb('#6c6849'), 0.9),
        'remap': material('Remap', srgb(soldier.HOUSE_COLOUR), 0.55, 0.15),
        'boot': material('Boot', srgb('#2a241c'), 0.75),
        'glove': material('Glove', srgb('#3a3226'), 0.8),
        'skin': material('Skin', srgb('#c69a78'), 0.7),
        'pack': material('Pack', srgb('#55553a'), 0.9),
        'gun': material('Gunmetal', srgb('#2d2f31'), 0.4, 0.8),
        'steel': material('Steel', srgb('#9a9c98'), 0.35, 0.9),
        'visor': material('Visor', srgb('#16222c'), 0.1, 0.4, emission=srgb('#2c4a5c'), strength=0.4),
    }


# --------------------------------------------------------------------------- main

def run(out, blend, animate=None):
    """Builds the unit (E1.build with the patched parts), adds its own clips with
    animate(rig, bones, body) on the unscaled rig, exports the GLB and the .blend and
    renders previews: -- --preview <clip:frame,…> <dir>."""
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    rig = soldier.build()
    if animate:
        scale = rig.scale.copy()
        rig.scale = (1, 1, 1)
        animate(rig, skeleton(), bpy.data.objects['SoldierBody'])
        rig.scale = scale
    print('export', soldier.export_glb(out), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    if '--preview' in args:
        frames = [(c, int(f)) for c, f in (x.split(':') for x in args[args.index('--preview') + 1].split(','))]
        soldier.render_preview(frames, args[args.index('--preview') + 2])
