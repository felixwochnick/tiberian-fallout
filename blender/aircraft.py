"""
Tiberian Fallout – shared parts of the aircraft (ORCA, APACHE).

The game sets the flight height and moves the aircraft over the map; the clips play
on the spot. Every clip keys every animated channel of the model at every frame
(clip()), so no clip leaks the pose of another: Fire, played alone while flying,
shows the aircraft in flight with its gear in. The clips every aircraft has:
    Idle     loop, 2 s: landed, engines off
    TakeOff  once, 1 s: from Idle to Fly (gear in, engines/rotor up)
    Fly      loop, 1 s: flying, a gentle sway
    Land     once, 1 s: from Fly to Idle (gear out, engines/rotor down)
    Fire     once, short: the Fly pose with the muzzle flash on the node "Flash"

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the aircraft; landed, its gear touches Z = 0.
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402
import walker  # noqa: E402

PROJECT = os.path.dirname(HERE)
FPS = kit.FPS
IDLE_FRAMES = 60
TAKEOFF_FRAMES = 30
FLY_FRAMES = 30
LAND_FRAMES = 30


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def span(f, start, end):
    return ease((f - start) / (end - start))


def mix(a, b, t):
    return a + (b - a) * t


def clip(name, frames, channels, pose):
    """Keys every channel ((object, property)) at every frame from pose(f) →
    {(object name, property): value} and makes it the clip `name`."""
    objects = []
    for obj, _ in channels:
        if obj not in objects:
            objects.append(obj)
    for obj in objects:
        obj.animation_data_create().action = bpy.data.actions.new(f'{name}_{obj.name}')
    prefs = bpy.context.preferences.edit
    old = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = 'LINEAR'
    for f in range(frames + 1):
        values = pose(f)
        for obj, prop in channels:
            setattr(obj, prop, values[(obj.name, prop)])
            obj.keyframe_insert(prop, frame=f)
    prefs.keyframe_new_interpolation_type = old
    for obj in objects:
        kit.to_track(obj, name)


def start(collection, name):
    """A fresh collection with the root and the Body empty (it sways in flight) on it."""
    kit.COLLECTION = collection
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 0
    scene.frame_end = IDLE_FRAMES
    root = kit.empty(name)
    body = kit.parent(kit.empty('Body'), root)
    return root, body


def main(build, out, blend, preview_clips, bake=False, scale=1.6, target=(0, 0, 0.2)):
    """Builds, bakes the camouflage (bake: texture size), renders previews
    (-- --preview <dir>), saves the .blend and exports the GLB in the rest pose (Idle,
    frame 0)."""
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    rest_pose = build()
    print('objects', len(kit.collection().objects), flush=True)
    if bake:
        kit.bake_camo(bake)
    if '--preview' in args:
        walker.previews(args[args.index('--preview') + 1], preview_clips, scale=scale, target=target)
    rest_pose()
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    print('export', walker.export(out), flush=True)
