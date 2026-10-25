"""
Tiberian Fallout – GDI light infantry (E1), after Tiberian Sun: a soldier in olive
fatigues with a tan armour vest, a helmet with a dark visor and a backpack, holding
his rifle at the ready. Shoulder pads and the helmet stripe are in the house colour.

Rig: a small armature (hips, spine, chest, neck, head, arms, legs); the mesh is made
of rigid parts, each bound to one bone. The rest pose already holds the rifle, so the
arms just follow the chest and the hands stay on the weapon.

Animations (glTF clips, from the NLA tracks of the same name; in place, the game
moves the unit)
    Idle    loop, 2 s: breathing, a slow look around
    Walk    loop, 0.8 s (two steps), rifle at the ready
    GoProne once, 0.6 s: throws himself down when under fire (played backwards to
            stand up again)
    Prone   loop, 2 s: lying on his belly, rifle forward, looking around
    Crawl   loop, 1.2 s: crawling on his belly, legs drawn up in turn

The armature carries the custom property walkSpeed (glTF extras): the ground speed
in cells per second at which the feet do not slide.

Run headless:

    Blender -b --factory-startup --python blender/E1.py

Modelled in metres (1.8 m tall), scaled down to map cells by SCALE. Blender Z is up,
the soldier looks along -Y (glTF +Z).
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the mesh helpers of the barracks script

kit.COLLECTION = 'GDIInfantry'
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'E1.glb')
BLEND = os.path.join(HERE, 'E1.blend')

SCALE = 0.65 / 1.8      # 1.8 m soldier → 0.65 cells: taller than the barracks' halls, readable on the battlefield
FPS = 30
IDLE_FRAMES = 60
WALK_FRAMES = 24        # two steps
STRIDE_ANGLE = math.radians(24)
DIVE_FRAMES = 18
PRONE_FRAMES = 60
CRAWL_FRAMES = 36

box, cylinder, sphere, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.srgb, kit.material


# --------------------------------------------------------------------------- skeleton

def elbow(a, c, l1, l2, pole):
    """Middle joint of a two-bone chain from a to c, bent towards `pole`."""
    d = c - a
    dist = min(d.length, l1 + l2 - 1e-4)
    axis = d.normalized()
    x = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - x * x, 0))
    side = (pole - axis * pole.dot(axis)).normalized()
    return a + axis * x + side * h


# the rifle at the ready: butt against the right shoulder, muzzle forward and low
RIFLE_BUTT = Vector((-0.1, -0.12, 1.32))
RIFLE_DIR = Vector((0.1, -1.0, -0.3)).normalized()
RIFLE_LENGTH = 0.92
GRIP = RIFLE_BUTT + RIFLE_DIR * 0.22 + Vector((0, 0, -0.07))
SUPPORT = RIFLE_BUTT + RIFLE_DIR * 0.38 + Vector((0, 0, -0.035))

UPPER_ARM, FOREARM = 0.31, 0.29


def skeleton():
    """Bone name → (head, tail, parent)."""
    bones = {
        'hips': ((0, 0, 0.93), (0, 0, 1.03), None),
        'spine': ((0, 0, 1.03), (0, 0, 1.2), 'hips'),
        'chest': ((0, 0, 1.2), (0, 0, 1.45), 'spine'),
        'neck': ((0, 0, 1.45), (0, 0, 1.56), 'chest'),
        'head': ((0, 0, 1.56), (0, 0, 1.8), 'neck'),
    }
    for side, s in (('L', 1), ('R', -1)):
        shoulder = Vector((s * 0.19, -0.03, 1.42))
        hand = GRIP if s < 0 else SUPPORT
        wrist = hand + (Vector((0, 0.05, 0.03)) if s < 0 else Vector((0.03, 0.03, -0.01)))
        reach = (wrist - shoulder).length / (UPPER_ARM + FOREARM)
        if reach > 0.999:
            print(f'warning: arm {side} cannot reach the rifle ({reach:.2f})')
        joint = elbow(shoulder, wrist, UPPER_ARM, FOREARM, Vector((s * 1.0, 0.4, -1.0)))
        bones[f'upper_arm.{side}'] = (shoulder, joint, 'chest')
        bones[f'forearm.{side}'] = (joint, wrist, f'upper_arm.{side}')
        bones[f'hand.{side}'] = (wrist, hand + (hand - wrist).normalized() * 0.03, f'forearm.{side}')
        bones[f'thigh.{side}'] = ((s * 0.1, 0, 0.93), (s * 0.11, -0.01, 0.5), 'hips')
        bones[f'shin.{side}'] = ((s * 0.11, -0.01, 0.5), (s * 0.11, 0, 0.09), f'thigh.{side}')
        bones[f'foot.{side}'] = ((s * 0.11, 0, 0.09), (s * 0.11, -0.14, 0.03), f'shin.{side}')
    return {name: (Vector(h), Vector(t), p) for name, (h, t, p) in bones.items()}


def armature(bones):
    data = bpy.data.armatures.new('SoldierRig')
    rig = bpy.data.objects.new('Soldier', data)
    kit.collection().objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    for name, (head, tail, _) in bones.items():
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
    for name, (_, _, parent) in bones.items():
        if parent:
            data.edit_bones[name].parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return rig


# --------------------------------------------------------------------------- mesh

def limb(name, mat, p0, p1, r0, r1, segments=10):
    """A tapered cylinder from p0 (radius r0) to p1 (radius r1)."""
    p0, p1 = Vector(p0), Vector(p1)
    obj = cylinder(name, mat, r0, (p1 - p0).length, (p0 + p1) / 2, segments=segments, bevel=0, radius2=r1)
    obj.rotation_mode = 'QUATERNION'
    # create_cone puts radius1 at -Z: point -Z at p0
    obj.rotation_quaternion = (p1 - p0).to_track_quat('Z', 'Y')
    return obj


def dome(name, mat, radius, location, cut=0.0, scale=(1, 1, 1)):
    """Upper part of a sphere (above `cut` · radius), e.g. the helmet."""
    def build(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=radius)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < cut * radius - 1e-6], context='VERTS')
        edges = [e for e in bm.edges if e.is_boundary]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges)
        bmesh.ops.scale(bm, vec=scale, verts=bm.verts)

    obj = kit.mesh_object(name, build)
    obj.location = location
    return kit.finish(obj, mat, 0)


def body(bones):
    """Rigid parts as (object, bone)."""
    m = {
        'fatigue': material('Fatigue', srgb('#6c6849'), 0.9),
        'armour': material('Armour', srgb('#ab9f7a'), 0.7, 0.1),
        'remap': material('Remap', srgb('#d8b43a'), 0.55, 0.15),
        'boot': material('Boot', srgb('#2a241c'), 0.75),
        'glove': material('Glove', srgb('#3a3226'), 0.8),
        'skin': material('Skin', srgb('#c69a78'), 0.7),
        'helmet': material('Helmet', srgb('#7a775b'), 0.6, 0.1),
        'visor': material('Visor', srgb('#16222c'), 0.1, 0.4, emission=srgb('#2c4a5c'), strength=0.4),
        'pack': material('Pack', srgb('#55553a'), 0.9),
        'gun': material('Gunmetal', srgb('#2d2f31'), 0.4, 0.8),
        'stock': material('RifleStock', srgb('#4a4535'), 0.8),
    }
    parts = []

    def add(bone, *objs):
        parts.extend((obj, bone) for obj in objs)

    head = lambda name: bones[name][0]  # noqa: E731
    tail = lambda name: bones[name][1]  # noqa: E731

    # ---- torso
    add('hips',
        kit.frustum('Pelvis', m['fatigue'], (0.32, 0.2), (0.3, 0.19), 0.13, (0, 0, 0.87), bevel=0.02),
        box('Belt', m['boot'], (0.33, 0.21, 0.045), (0, 0, 1.0), bevel=0.01))
    for x in (-0.11, 0.11):
        add('hips', box(f'BeltPouch{x}', m['pack'], (0.07, 0.04, 0.06), (x, -0.115, 0.99), bevel=0.01))
    add('spine', kit.frustum('Belly', m['fatigue'], (0.29, 0.19), (0.33, 0.21), 0.2, (0, 0, 1.01), bevel=0.02))
    add('chest',
        kit.frustum('Vest', m['armour'], (0.36, 0.25), (0.42, 0.27), 0.27, (0, 0, 1.17), bevel=0.03),
        kit.frustum('Collar', m['armour'], (0.24, 0.18), (0.19, 0.15), 0.05, (0, 0, 1.44), bevel=0.01),
        box('VestPlate', m['armour'], (0.26, 0.03, 0.16), (0, -0.14, 1.32), bevel=0.012),
        box('Backpack', m['pack'], (0.3, 0.14, 0.3), (0, 0.2, 1.3), bevel=0.03),
        cylinder('Bedroll', m['fatigue'], 0.05, 0.32, (0, 0.2, 1.48), rotation=(0, math.pi / 2, 0), segments=12),
        limb('Antenna', m['gun'], (0.1, 0.24, 1.42), (0.12, 0.27, 1.75), 0.006, 0.003, 6))
    for i, x in enumerate((-0.12, -0.04, 0.04, 0.12)):
        add('chest', box(f'Pouch{i}', m['pack'], (0.065, 0.04, 0.075), (x, -0.145, 1.21), bevel=0.01))

    # ---- head: face, helmet with visor and a house-colour stripe
    neck_top = head('head')
    add('neck', limb('Neck', m['skin'], head('neck'), neck_top + Vector((0, 0, 0.03)), 0.055, 0.05))
    centre = neck_top + Vector((0, -0.01, 0.1))
    add('head',
        dome('Face', m['skin'], 0.095, centre, -1.0, (0.85, 0.95, 1.1)),
        dome('Helmet', m['helmet'], 0.125, centre + Vector((0, 0.01, 0.0)), 0.0, (1.0, 1.08, 1.0)),
        box('HelmetRim', m['helmet'], (0.25, 0.26, 0.025), centre + Vector((0, 0.01, 0.0)), bevel=0.01),
        box('Visor', m['visor'], (0.17, 0.035, 0.05), centre + Vector((0, -0.105, -0.01)), bevel=0.012),
        box('HelmetStripe', m['remap'], (0.03, 0.27, 0.02), centre + Vector((0, 0.005, 0.122)), bevel=0.006))

    # ---- arms: sleeves, shoulder pads in the house colour, gloves
    for side in ('L', 'R'):
        s = 1 if side == 'L' else -1
        shoulder, joint, wrist = head(f'upper_arm.{side}'), head(f'forearm.{side}'), head(f'hand.{side}')
        add(f'upper_arm.{side}',
            limb(f'UpperArm{side}', m['fatigue'], shoulder, joint, 0.058, 0.048),
            dome(f'ShoulderPad{side}', m['remap'], 0.075, shoulder + Vector((s * 0.02, 0, 0.0)), -0.2, (1.0, 1.05, 0.9)),
            sphere(f'Elbow{side}', m['fatigue'], 0.048, joint, 10))
        add(f'forearm.{side}',
            limb(f'Forearm{side}', m['fatigue'], joint, wrist, 0.046, 0.038),
            limb(f'Cuff{side}', m['glove'], wrist + (joint - wrist).normalized() * 0.06, wrist, 0.045, 0.042))
        add(f'hand.{side}', box(f'Hand{side}', m['glove'], (0.06, 0.08, 0.09), (wrist + tail(f'hand.{side}')) / 2, bevel=0.015))

    # ---- legs: trousers, knee pads, boots
    for side in ('L', 'R'):
        hip, knee, ankle = head(f'thigh.{side}'), head(f'shin.{side}'), head(f'foot.{side}')
        add(f'thigh.{side}',
            limb(f'Thigh{side}', m['fatigue'], hip, knee, 0.095, 0.065),
            box(f'LegPouch{side}', m['pack'], (0.04, 0.08, 0.1), hip.lerp(knee, 0.45) + Vector((hip.x * 0.75, 0, 0)), bevel=0.01))
        add(f'shin.{side}',
            limb(f'Shin{side}', m['fatigue'], knee, ankle + Vector((0, 0, 0.12)), 0.058, 0.05),
            sphere(f'KneePad{side}', m['boot'], 0.055, knee + Vector((0, -0.03, 0)), 10),
            limb(f'BootShaft{side}', m['boot'], ankle + Vector((0, 0, 0.17)), ankle - Vector((0, 0, 0.04)), 0.055, 0.058))
        add(f'foot.{side}',
            box(f'Boot{side}', m['boot'], (0.11, 0.25, 0.07), ankle + Vector((0, -0.055, -0.055)), bevel=0.02))

    # ---- rifle along RIFLE_DIR, in the right hand
    rot = RIFLE_DIR.to_track_quat('Y', 'Z').to_matrix().to_4x4()

    def rifle_part(name, mat, size, along, up=0.0, cyl=False):
        offset = Vector((0, along, up))
        if cyl:
            obj = cylinder(name, mat, size[0], size[1], (0, 0, 0), rotation=(math.pi / 2, 0, 0), segments=10, bevel=0)
        else:
            obj = box(name, mat, size, (0, 0, 0), bevel=0.006)
        kit.bake_modifiers(obj)
        obj.data.transform(Matrix.Translation(RIFLE_BUTT) @ rot @ Matrix.Translation(offset))
        return obj

    add('hand.R',
        rifle_part('Stock', m['stock'], (0.045, 0.24, 0.09), 0.12, -0.015),
        rifle_part('Receiver', m['gun'], (0.05, 0.26, 0.07), 0.36),
        rifle_part('Magazine', m['gun'], (0.035, 0.05, 0.13), 0.38, -0.08),
        rifle_part('PistolGrip', m['gun'], (0.035, 0.04, 0.08), 0.24, -0.06),
        rifle_part('Handguard', m['stock'], (0.055, 0.2, 0.05), 0.58),
        rifle_part('Scope', m['gun'], (0.022, 0.14), 0.36, 0.06, cyl=True),
        rifle_part('Barrel', m['gun'], (0.012, 0.26), RIFLE_LENGTH - 0.13, 0.01, cyl=True))
    return parts


def skinned_mesh(name, parts, rig):
    """Joins the parts into one mesh bound rigidly to their bones."""
    names = [b.name for b in rig.data.bones]
    bm = bmesh.new()
    deform = bm.verts.layers.deform.verify()
    materials = []
    for obj, bone in parts:
        kit.bake_modifiers(obj)
        slots = []
        for mat in obj.data.materials:
            if mat not in materials:
                materials.append(mat)
            slots.append(materials.index(mat))
        indices = [slots[p.material_index] for p in obj.data.polygons]
        first_vert, first_face = len(bm.verts), len(bm.faces)
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        for vert in bm.verts[first_vert:]:
            vert[deform][names.index(bone)] = 1.0
        for face, index in zip(bm.faces[first_face:], indices):
            face.material_index = index
        mesh = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)
    mesh = bpy.data.meshes.new(name)
    for mat in materials:
        mesh.materials.append(mat)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = False  # faceted low-poly look like the original voxels
    obj = bpy.data.objects.new(name, mesh)
    kit.collection().objects.link(obj)
    for bone in names:
        obj.vertex_groups.new(name=bone)
    obj.modifiers.new('Armature', 'ARMATURE').object = rig
    obj.parent = rig
    return obj


# --------------------------------------------------------------------------- animation

def rotation(x=0.0, y=0.0, z=0.0):
    """Rotation about the armature's axes (degrees): x pitches (+ tips forward for a bone
    pointing up, swings a leg backwards), y rolls sideways, z turns."""
    return (Quaternion((0, 0, 1), math.radians(z)) @ Quaternion((0, 1, 0), math.radians(y))
            @ Quaternion((1, 0, 0), math.radians(x)))


def set_pose(rig, deltas, offset=Vector()):
    """deltas: bone → rotation about its head in armature axes, relative to its parent's
    motion; offset moves the hips. Pose basis = rest⁻¹ · delta · rest."""
    for pb in rig.pose.bones:
        rest = pb.bone.matrix_local
        pivot = pb.bone.head_local
        q = deltas.get(pb.name, Quaternion())
        delta = Matrix.Translation(pivot) @ q.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
        if pb.name == 'hips':
            delta = Matrix.Translation(offset) @ delta
        basis = rest.inverted() @ delta @ rest
        loc, quat, _ = basis.decompose()
        previous = pb.rotation_quaternion.copy()
        if previous.dot(quat) < 0:
            quat.negate()  # keep the keys on one side so interpolation takes the short way
        pb.rotation_quaternion = quat
        pb.location = loc


def key_pose(rig, frame):
    for pb in rig.pose.bones:
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        if pb.name == 'hips':
            pb.keyframe_insert('location', frame=frame)


def leg_extent(bones, side, thigh, knee):
    """Height of the ankle below the hip joint and its forward offset, for leg angles (deg)."""
    hip, knee_p, ankle = bones[f'thigh.{side}'][0], bones[f'shin.{side}'][0], bones[f'foot.{side}'][0]
    r_thigh = rotation(thigh).to_matrix()
    r_shin = r_thigh @ rotation(knee).to_matrix()
    p = r_thigh @ (knee_p - hip) + r_shin @ (ankle - knee_p)
    return -p.z, p.y


def walk_pose(bones, phase):
    """Leg angles and hip height for a phase (radians) of the walk cycle."""
    amplitude = math.degrees(STRIDE_ANGLE)
    legs = {}
    for side, shift in (('L', 0.0), ('R', math.pi)):
        p = phase + shift
        thigh = -amplitude * math.sin(p)                              # negative: forward
        knee = 6 + 34 * max(0.0, math.cos(p)) ** 1.6                  # bends while swinging forward
        foot = -(thigh + knee) * 0.85 + 14 * max(0.0, -math.cos(p) * math.sin(p))  # flat, toe-off
        legs[side] = (thigh, knee, foot)
    # the lower foot stays on the ground: drop the hips by what the legs are shorter
    rest = leg_extent(bones, 'L', 0, 0)[0]
    height = max(leg_extent(bones, s, legs[s][0], legs[s][1])[0] for s in ('L', 'R'))
    return legs, height - rest


def lowest_point(body):
    """Lowest z of the posed mesh (rig not scaled yet: metres)."""
    bpy.context.view_layer.update()
    evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    z = min(v.co.z for v in mesh.vertices)
    evaluated.to_mesh_clear()
    return z


def grounded_clip(rig, body, name, frames, pose):
    """Keys a clip from pose(frame) → (deltas, offset), each frame lowered or raised so
    the lowest point of the body just touches the ground."""
    ad = rig.animation_data
    # measure without any animation overriding the pose
    muted = [(track, track.mute) for track in ad.nla_tracks]
    for track, _ in muted:
        track.mute = True
    ad.action = None
    poses = []
    for f in range(frames + 1):
        deltas, offset = pose(f)
        set_pose(rig, deltas, offset)
        poses.append((deltas, offset - Vector((0, 0, lowest_point(body)))))
    for track, mute in muted:
        track.mute = mute
    ad.action = bpy.data.actions.new(name)
    for f, (deltas, offset) in enumerate(poses):
        set_pose(rig, deltas, offset)
        key_pose(rig, f)
    kit.to_track(rig, name)


def leg_tuck(side, amount):
    """A leg drawn up sideways along the ground when crawling (0 = straight back):
    turned outward about its own axis, so the knee bends flat over the ground, and
    spread."""
    s = 1 if side == 'L' else -1
    thigh = Quaternion((0, 1, 0), math.radians(-s * (7 + 50 * amount))) @ Quaternion((0, 0, 1), math.radians(s * 90 * amount))
    return thigh, rotation(x=5 + 85 * amount)


def prone_pose(t=1.0, breath=0.0, look=0.0):
    """From standing (t = 0) to lying on the belly (t = 1); halfway he crouches and dives."""
    e = t * t * (3 - 2 * t)
    dive = math.sin(math.pi * t)
    deltas = {
        'hips': rotation(x=86 * e),
        'spine': rotation(x=-4 * e + 10 * dive - 0.6 * breath),
        'chest': rotation(x=-4 * e - 0.8 * breath),
        'neck': rotation(x=-38 * e),
        'head': rotation(x=-28 * e, z=look),
        # both arms turn about the line through the shoulders: the rifle comes up level
        # in front of the face and both hands stay on it
        'upper_arm.L': rotation(x=-92 * e),
        'upper_arm.R': rotation(x=-92 * e),
    }
    for side, s in (('L', 1), ('R', -1)):
        deltas[f'thigh.{side}'] = rotation(x=-50 * dive, y=-s * 7 * e)
        deltas[f'shin.{side}'] = rotation(x=80 * dive + 5 * e)
        deltas[f'foot.{side}'] = rotation(x=75 * e)  # stretched back, flat
    return deltas


def animate_prone(rig, body):
    # ---- GoProne: crouch, throw himself forward, land on the belly
    grounded_clip(rig, body, 'GoProne', DIVE_FRAMES,
                  lambda f: (prone_pose(f / DIVE_FRAMES), Vector()))

    # ---- Prone: lying, breathing, looking around over the rifle
    def lying(f):
        t = 2 * math.pi * f / PRONE_FRAMES
        return prone_pose(1.0, math.sin(2 * t), 12 * math.sin(t)), Vector()

    grounded_clip(rig, body, 'Prone', PRONE_FRAMES, lying)

    # ---- Crawl: legs drawn up in turn, the body sways, the arms pull twice per cycle
    def crawl(f):
        p = 2 * math.pi * f / CRAWL_FRAMES
        s = math.sin(p)
        deltas = prone_pose(1.0)
        deltas['hips'] = rotation(x=86, z=6 * s)
        deltas['chest'] = rotation(x=-4, z=-4 * s)
        deltas['head'] = rotation(x=-28, z=-3 * s)
        pull = -92 + 7 * math.cos(2 * p)
        deltas['upper_arm.L'] = deltas['upper_arm.R'] = rotation(x=pull)
        for side, amount in (('L', max(0.0, s)), ('R', max(0.0, -s))):
            deltas[f'thigh.{side}'], deltas[f'shin.{side}'] = leg_tuck(side, amount)
        return deltas, Vector((0, 0.04 * math.cos(2 * p), 0))

    grounded_clip(rig, body, 'Crawl', CRAWL_FRAMES, crawl)
    set_pose(rig, {})


def animate(rig, bones):
    ad = rig.animation_data_create()
    prefs = bpy.context.preferences.edit
    prefs.keyframe_new_interpolation_type = 'LINEAR'

    # ---- Idle: breathing, weight on one leg, a slow look around
    ad.action = bpy.data.actions.new('Idle')
    for f in range(IDLE_FRAMES + 1):
        t = 2 * math.pi * f / IDLE_FRAMES
        breath = math.sin(2 * t)
        set_pose(rig, {
            'spine': rotation(x=-1.0 - 0.8 * breath),
            'chest': rotation(x=-0.8 * breath, z=3 * math.sin(t)),
            'neck': rotation(z=8 * math.sin(t + 0.6)),
            'head': rotation(x=2 * math.sin(2 * t), z=14 * math.sin(t + 0.9)),
            'upper_arm.L': rotation(x=-0.6 * breath),
            'upper_arm.R': rotation(x=-0.6 * breath),
        }, Vector((0, 0, -0.004 - 0.003 * breath)))
        key_pose(rig, f)
    kit.to_track(rig, 'Idle')

    # ---- Walk: legs from walk_pose, hips bob and turn, the upper body counter-turns
    ad.action = bpy.data.actions.new('Walk')
    contacts = []
    for f in range(WALK_FRAMES + 1):
        phase = 2 * math.pi * f / WALK_FRAMES
        legs, drop = walk_pose(bones, phase)
        deltas = {
            'hips': rotation(z=-6 * math.sin(phase), y=2.5 * math.cos(2 * phase)),
            'spine': rotation(x=6, z=4 * math.sin(phase)),
            'chest': rotation(x=-2 + 1.5 * math.cos(2 * phase), z=3 * math.sin(phase)),
            'neck': rotation(z=-2 * math.sin(phase)),
            'head': rotation(x=-4, z=-1 * math.sin(phase)),
        }
        for side, (thigh, knee, foot) in legs.items():
            deltas[f'thigh.{side}'] = rotation(x=thigh)
            deltas[f'shin.{side}'] = rotation(x=knee)
            deltas[f'foot.{side}'] = rotation(x=foot)
        set_pose(rig, deltas, Vector((0, 0, drop - 0.01)))
        key_pose(rig, f)
    kit.to_track(rig, 'Walk')
    set_pose(rig, {})

    # ground speed: the stance foot moves back from its forward-most to its back-most point
    # in half a cycle; sampled numerically
    ys = [leg_extent(bones, 'L', walk_pose(bones, 2 * math.pi * i / 240)[0]['L'][0], 0)[1] for i in range(240)]
    stride = max(ys) - min(ys)                       # metres per step
    speed = stride / (WALK_FRAMES / 2 / FPS)         # metres per second
    rig['walkSpeed'] = round(speed * SCALE, 4)       # cells per second
    return rig['walkSpeed']


# --------------------------------------------------------------------------- build + export

def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 0
    scene.frame_end = IDLE_FRAMES

    bones = skeleton()
    rig = armature(bones)
    soldier = skinned_mesh('SoldierBody', body(bones), rig)
    speed = animate(rig, bones)
    animate_prone(rig, soldier)
    rig.scale = (SCALE,) * 3
    print('walk speed', speed, 'cells/s', flush=True)
    return rig


def export_glb(path=OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in kit.collection().objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=False,
        export_lights=False,
        export_cameras=False,
        export_extras=True,
        export_animations=True,
        export_animation_mode='ACTIONS',
        export_merge_animation='NLA_TRACK',
        export_force_sampling=True,
        export_optimize_animation_size=False,
        export_def_bones=True,
    )
    return {'path': path, 'bytes': os.path.getsize(path)}


def render_preview(frames, out_dir, size=360):
    """Close-up through the game's camera angle (orthographic, 30° down, from the front right)."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    world = scene.world or bpy.data.worlds.new('World')
    scene.world = world
    world.color = (0.35, 0.37, 0.42)
    if 'PreviewCamera' not in bpy.data.objects:
        bpy.ops.mesh.primitive_plane_add(size=4)
        bpy.context.active_object.data.materials.append(material('PreviewGround', srgb('#6b5434'), 1.0))
        sun = bpy.data.objects.new('PreviewSun', bpy.data.lights.new('PreviewSun', 'SUN'))
        sun.data.energy = 4.0
        scene.collection.objects.link(sun)
        sun.rotation_euler = Vector((-6, 2, 9)).to_track_quat('Z', 'Y').to_euler()
        cam = bpy.data.objects.new('PreviewCamera', bpy.data.cameras.new('PreviewCamera'))
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = 0.9
        scene.collection.objects.link(cam)
        direction = Vector((math.sin(math.radians(45)) * math.cos(math.radians(30)),
                            -math.cos(math.radians(45)) * math.cos(math.radians(30)),
                            math.sin(math.radians(30))))
        target = Vector((0, 0, 0.33))
        cam.location = target + direction * 5
        cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
        scene.camera = cam
    os.makedirs(out_dir, exist_ok=True)
    rig = bpy.data.objects['Soldier']
    for clip, frame in frames:
        for track in rig.animation_data.nla_tracks:
            track.mute = track.name != clip
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(out_dir, f'{clip}_{frame:03d}.png')
        bpy.ops.render.render(write_still=True)
    for track in rig.animation_data.nla_tracks:
        track.mute = False


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    build()
    print('export', export_glb(), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        frames = [(c, int(f)) for c, f in (x.split(':') for x in args[args.index('--preview') + 1].split(','))]
        render_preview(frames, args[args.index('--preview') + 2])


if __name__ == '__main__' and bpy.app.background:
    main()
