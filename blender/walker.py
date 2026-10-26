"""
Tiberian Fallout – shared parts of the GDI walkers (SMECH Wolverine, MMCH Titan).

A walker is a hierarchy of empties, no armature: Body (bobs while walking) carries
the torso and the arms; each leg is Hip → Knee → Ankle, the meshes of thigh, shin and
foot hang on them. Rotations are about X: positive swings the part below backwards
(+Y), the walkers look along -Y.

The walk cycle is two steps: a leg stands on the ground for one half (its foot moves
back at constant speed, so it does not slide), then swings forward with its knee bent.
walk() keys it and returns the ground speed (cells per second) that matches the feet,
stored as the root's walkSpeed (glTF extras) like the other units.
"""
import math

from mathutils import Vector

import GAPILE as kit


def joint(name, parent, location):
    """An empty at `location` (world), parented without moving."""
    obj = kit.empty(name, location)
    obj.empty_display_size = 0.05
    if parent is not None:
        kit.parent(obj, parent)
    return obj


class Leg:
    """Hip, knee and ankle joints of one leg; attach the meshes with kit.parent."""

    def __init__(self, name, parent, hip, thigh, shin):
        self.hip = joint(f'{name}Hip', parent, hip)
        self.knee = joint(f'{name}Knee', self.hip, hip - Vector((0, 0, thigh)))
        self.ankle = joint(f'{name}Ankle', self.knee, hip - Vector((0, 0, thigh + shin)))
        self.length = thigh + shin


def gait(p, swing, bend):
    """Hip and knee angle at phase p (0 … 1) of the cycle; the first half is the stance."""
    if p < 0.5:
        s = p / 0.5
        return -swing + 2 * swing * s, 0.04
    s = (p - 0.5) / 0.5
    return swing * math.cos(math.pi * s), bend * math.sin(math.pi * s)


def hide(objects, frames, track):
    """Keys `objects` hidden over a clip (e.g. the muzzle flashes outside Fire)."""
    for obj in objects:
        kit.keys(obj, 'scale', {0: Vector((kit.HIDDEN,) * 3), frames: Vector((kit.HIDDEN,) * 3)}, 'CONSTANT')
        kit.to_track(obj, track)


def walk(legs, body, arms, frames, swing, bend, arm_swing=0.12, hidden=()):
    """Keys the Walk clip (legs in turn, the body bobs, the arms swing a little against
    the legs) and puts it on the NLA track 'Walk'. Returns the ground speed."""
    for f in range(frames + 1):
        t = f / frames
        lowest = 0.0
        for k, leg in enumerate(legs):
            p = (t + 0.5 * k) % 1.0
            hip, knee = gait(p, swing, bend)
            leg.hip.rotation_euler = (hip, 0, 0)
            leg.knee.rotation_euler = (knee, 0, 0)
            leg.ankle.rotation_euler = (-(hip + knee), 0, 0)  # the foot stays flat
            for obj in (leg.hip, leg.knee, leg.ankle):
                obj.keyframe_insert('rotation_euler', frame=f)
            if p < 0.5:  # the standing leg carries the body: it sinks as the leg leans
                lowest = leg.length * (math.cos(hip) - 1)
        body.location = (0, 0, lowest)
        body.keyframe_insert('location', frame=f)
        for k, arm in enumerate(arms):
            arm.rotation_euler = (arm_swing * math.sin(2 * math.pi * (t + 0.5 * k)), 0, 0)
            arm.keyframe_insert('rotation_euler', frame=f)
    for obj in [body, *arms, *[j for leg in legs for j in (leg.hip, leg.knee, leg.ankle)]]:
        kit.to_track(obj, 'Walk')
    hide(hidden, frames, 'Walk')
    stride = 2 * legs[0].length * math.sin(swing)          # foot travel while standing
    return stride / (frames / 2 / kit.FPS)


def idle(body, arms, legs, sway=0.006, frames=None, hidden=()):
    """Keys the Idle clip: the body breathes up and down, the arms drift a little, the
    legs stand straight (keyed, so nothing of the walk is left over when it ends)."""
    frames = frames or kit.IDLE_END
    joints = [j for leg in legs for j in (leg.hip, leg.knee, leg.ankle)]
    for obj in joints:
        kit.keys(obj, 'rotation_euler', {0: Vector((0, 0, 0)), frames: Vector((0, 0, 0))}, 'LINEAR')
        kit.to_track(obj, 'Idle')
    hide(hidden, frames, 'Idle')
    for f in range(0, frames + 1, 2):
        t = 2 * math.pi * f / frames
        body.location = (0, 0, sway * math.sin(t))
        body.keyframe_insert('location', frame=f)
        for k, arm in enumerate(arms):
            arm.rotation_euler = (0.03 * math.sin(t + k), 0, 0)
            arm.keyframe_insert('rotation_euler', frame=f)
    for obj in (body, *arms):
        kit.to_track(obj, 'Idle')


def rest(body, joints):
    """Back to the rest pose after keying (the clips live on NLA tracks now): the body
    at its place, all joints straight."""
    body.location = (0, 0, 0)
    for obj in joints:
        obj.rotation_euler = (0, 0, 0)


def solo(clip):
    """Plays only the NLA tracks of one clip (for previews)."""
    import bpy
    for obj in bpy.data.objects:
        if obj.animation_data:
            for track in obj.animation_data.nla_tracks:
                track.mute = track.name != clip


def preview(frames, out_dir, scale=1.6, target=(0, 0, 0.4), clip=None):
    """kit.render_preview, closer: a single unit instead of a building; `clip` alone."""
    import bpy
    if clip:
        solo(clip)
    kit.render_preview([], out_dir)
    cam = bpy.data.objects['PreviewCamera']
    cam.data.ortho_scale = scale
    direction = Vector((math.sin(math.radians(45)) * math.cos(math.radians(30)),
                        -math.cos(math.radians(45)) * math.cos(math.radians(30)),
                        math.sin(math.radians(30))))
    cam.location = Vector(target) + direction * 10
    kit.render_preview(frames, out_dir)


def export(path):
    """kit.export_glb in the rest pose: the NLA tracks are muted while exporting (they
    would pose the nodes at the export frame); the clips are exported all the same."""
    import bpy
    tracks = [t for obj in bpy.data.objects if obj.animation_data for t in obj.animation_data.nla_tracks]
    for track in tracks:
        track.mute = True
    try:
        return kit.export_glb(path)
    finally:
        for track in tracks:
            track.mute = False


def previews(out_dir, clips, scale=1.3, target=(0, 0, 0.4)):
    """Renders `clips` ({clip: frames}) each alone into out_dir/<clip>, then takes the
    preview camera, sun and ground out again. Call it before exporting: the glTF
    exporter leaves the scene in a sampled pose."""
    import os
    import bpy
    for clip, frames in clips.items():
        preview(frames, os.path.join(out_dir, clip.lower()), scale, target, clip)
    solo(None)
    for obj in bpy.data.objects:
        if obj.animation_data:
            for track in obj.animation_data.nla_tracks:
                track.mute = False
    for name in ('PreviewGround', 'PreviewSun', 'PreviewCamera'):
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)


def hold(obj, path, value, frames, track):
    """Keys a property at one value over a clip (so a part another clip moves, e.g. a
    recoiling barrel, sits right in this one)."""
    kit.keys(obj, path, {0: value, frames: value}, 'CONSTANT')
    kit.to_track(obj, track)
