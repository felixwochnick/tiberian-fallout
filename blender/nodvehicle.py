"""
Tiberian Fallout – shared parts of the Nod vehicles (BGGY, BIKE, SAPC, TTNK).

Nod's vehicles wear camouflage (camouflage()): the armour near black blotched with
dark grey and a little dark red, the fairings, panels and guards red (the house
colour) blotched with darker red and black. The black shades are shades of the house
colour that the game turns near black for Nod; the red ones carry the extra nodAccent
and stay shades of the house colour (applyHouseColour in app/lib/game/models.ts). The parts here: materials, wheels and tracks, guns on a "Cannon" node that
the game tips towards the target (Combat.elevate) with a muzzle flash on a "Flash…"
node (Combat.muzzle), and the clips every vehicle has:
    Idle    loop, 2 s: the engine runs, the body shivers a little
    Walk    loop: driving, wheels and tracks turn (one turn per loop), the body rocks;
            the root's walkSpeed (glTF extras) is the ground speed in cells per second
            at which the wheels do not slip
    Fire    once: the shot, the barrel recoils, the muzzle flashes

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is on
the ground under the middle of the vehicle.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import housecamo  # noqa: E402 – shade()
import walker  # noqa: E402 – hide(), hold(), export(), previews()

PROJECT = os.path.dirname(HERE)

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material


def materials():
    m = kit.materials()
    m.update({
        'armour': material('NodArmour', srgb('#45474c'), 0.45, 0.6),
        'armour_dark': material('NodArmourDark', srgb('#26272b'), 0.55, 0.5),
        'tyre': material('Tyre', srgb('#1c1b1a'), 0.9, 0.1),
        'track': material('Track', srgb('#252422'), 0.8, 0.3),
        'glass': material('Canopy', srgb('#14191f'), 0.08, 0.7, emission=srgb('#1d2c3a'), strength=0.35),
        'seam': material('Seam', srgb('#141416'), 0.8),
        'hazard': material('HazardYellow', srgb('#e0b21c'), 0.6),
        'flash': material('GlowFlash', (0, 0, 0), 1.0, emission=srgb('#ffd27a'), strength=6, alpha=0.7),
    })
    return m


def camo_shades():
    """The camouflage's materials: name → material."""
    shades = {}
    for name, lightness, saturation, accent in (
        ('NodCamoBlack', 0.2, 0.5, False),
        ('NodCamoGrey', 0.8, 0.4, False),
        ('NodCamoMid', 0.5, 0.45, False),
        ('NodCamoRed', 1.0, 1.0, True),
        ('NodCamoRedDark', 0.55, 0.9, True),
    ):
        mat = housecamo.shade(name, lightness, saturation, 0.55)
        if accent:
            mat['nodAccent'] = True
        shades[name] = mat
    return shades


# which camouflage a material gets: its layers from the bottom up (shade, noise
# threshold; None: the ground)
CAMO = {
    'NodArmour': (('NodCamoBlack', None), ('NodCamoGrey', 0.05), ('NodCamoRedDark', 0.33)),
    'NodArmourDark': (('NodCamoBlack', None), ('NodCamoMid', 0.15), ('NodCamoRedDark', 0.4)),
    'Remap': (('NodCamoRed', None), ('NodCamoRedDark', 0.05), ('NodCamoBlack', 0.3)),
}


def camouflage(objects, frequency=7.0, max_edge=0.04):
    """Lays the camouflage on the faces of `objects` whose material is in CAMO (call it
    before keying the clips: it updates the scene, which poses the objects): their
    long edges are cut so the blotches have a fine grid, each face gets the shade of
    the blotch its middle lies in (noise in world space, so the pattern runs on across
    the parts)."""
    shades = camo_shades()
    bpy.context.view_layer.update()
    for obj in objects:
        if obj.type != 'MESH':
            continue
        # (a material made twice is called Remap.001 …)
        names = [mat.name.split('.')[0] if mat else '' for mat in obj.data.materials]
        if not any(name in CAMO for name in names):
            continue
        slots = {}
        for layers in CAMO.values():
            for shade, _ in layers:
                if shade not in slots:
                    slots[shade] = len(obj.data.materials)
                    obj.data.materials.append(shades[shade])
        world = obj.matrix_world
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for _ in range(6):
            long = [e for e in bm.edges if e.calc_length() * max(world.to_scale()) > max_edge
                    and any(names[f.material_index] in CAMO for f in e.link_faces if f.material_index < len(names))]
            if not long:
                break
            bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
        for face in bm.faces:
            name = names[face.material_index] if face.material_index < len(names) else ''
            layers = CAMO.get(name)
            if not layers:
                continue
            centre = world @ face.calc_center_median()
            index = slots[layers[0][0]]
            for k, (shade, threshold) in enumerate(layers):
                p = Vector((centre.x * frequency + k * 17.3, centre.y * frequency + k * 5.1, centre.z * frequency * 0.7 + k * 11.7))
                if threshold is None or noise.noise(p) > threshold:
                    index = slots[shade]
            face.material_index = index
        bm.to_mesh(obj.data)
        bm.free()


def finish(root, scale):
    """Scales the whole vehicle (parenting keeps world sizes); its walkSpeed with it."""
    root.scale = (scale,) * 3
    root['walkSpeed'] = round(root['walkSpeed'] * scale, 4)


def wheel(m, name, centre, radius, width, lugs=12, hub=0.55, rim=None):
    """A tyre with tread lugs and a bolted rim (material `rim`, default steel), turning
    about x; origin on its axle."""
    centre = Vector(centre)
    s = 1 if centre.x >= 0 else -1
    face = Vector((s * width / 2, 0, 0))
    turn = (0, math.pi / 2, 0)
    parts = [cylinder(f'{name}Tyre', m['tyre'], radius - 0.006, width, centre, rotation=turn, segments=18, bevel=min(0.008, width / 5)),
             cylinder(f'{name}Rim', rim or m['steel'], radius * hub, width + 0.004, centre, rotation=turn, segments=12, bevel=0.003),
             cylinder(f'{name}Cap', m['remap'], radius * 0.2, width + 0.012, centre, rotation=turn, segments=10, bevel=0.002)]
    for k in range(lugs):
        a = 2 * math.pi * k / lugs
        d = Vector((0, math.cos(a), math.sin(a)))
        parts.append(box(f'{name}Lug{k}', m['tyre'], (width - 0.008, radius * 0.22, radius * 0.16), centre + d * (radius - 0.006),
                         bevel=0.002, rotation=(a, 0, 0)))
    for k in range(4):  # spokes on the rim's face, so the turning shows
        a = 2 * math.pi * k / 4
        d = Vector((0, math.cos(a), math.sin(a)))
        parts.append(beam(f'{name}Spoke{k}', m['steel_light'], centre + face + d * radius * 0.2, centre + face + d * radius * hub * 0.95,
                          radius * 0.12, 0.006))
    return kit.merge(name, parts, centre)


def road_wheel(m, name, centre, radius, width):
    """A small road wheel of a track, turning about x."""
    centre = Vector(centre)
    s = 1 if centre.x >= 0 else -1
    turn = (0, math.pi / 2, 0)
    parts = [cylinder(f'{name}Rim', m['steel'], radius, width, centre, rotation=turn, segments=14, bevel=0.003),
             cylinder(f'{name}Hub', m['armour_dark'], radius * 0.45, width + 0.008, centre, rotation=turn, segments=10, bevel=0.002)]
    for k in range(3):
        a = 2 * math.pi * k / 3
        d = Vector((0, math.cos(a), math.sin(a)))
        parts.append(sphere(f'{name}Bolt{k}', m['steel_light'], radius * 0.12, centre + Vector((s * (width / 2 + 0.002), 0, 0)) + d * radius * 0.65, 6))
    return kit.merge(name, parts, centre)


def track(m, name, x, width, y0, y1, height, links=14):
    """A track's belt round its wheels from y0 to y1 (front to back), `height` high,
    with tread bars on top and bottom; returns the belt."""
    length = y1 - y0
    parts = [box(f'{name}Belt', m['track'], (width, length, height), (x, (y0 + y1) / 2, height / 2), bevel=height * 0.45)]
    for k in range(links):
        y = y0 + height * 0.4 + (k + 0.5) * (length - height * 0.8) / links
        for z in (0.004, height - 0.004):
            parts.append(box(f'{name}Link{k}{z:.3f}', m['steel'], (width + 0.006, 0.014, 0.01), (x, y, z), bevel=0.002))
    return kit.merge(name, parts, (x, (y0 + y1) / 2, 0))


def flash(m, name, muzzle, size=0.05, facing=(0, -1, 0)):
    """The muzzle flash: a few glowing balls ahead of the muzzle, hidden at rest."""
    muzzle, facing = Vector(muzzle), Vector(facing).normalized()
    obj = kit.merge(name, [sphere(f'{name}{k}', m['flash'], size * (1 - 0.25 * k), muzzle + facing * size * 0.9 * k, 10) for k in range(3)], muzzle)
    obj.scale = (kit.HIDDEN,) * 3
    return obj


def spin(objects, frames, turns=1, track_name='Walk'):
    """Keys the objects turning about x (the top moving forward, -y), `turns` a loop."""
    for obj in objects:
        kit.keys(obj, 'rotation_euler', {f: Vector((2 * math.pi * turns * f / frames, 0, 0)) for f in range(0, frames + 1, 2)} |
                 {frames: Vector((2 * math.pi * turns, 0, 0))}, 'LINEAR')
        kit.to_track(obj, track_name)


def drive(body, wheels, frames, rock=0.004, extra=()):
    """The Idle and Walk clips: idling, the body shivers; driving, the wheels turn (and
    `extra`: (objects, turns) more parts, e.g. sprockets of another size) and the body
    rocks."""
    keys = kit.keys
    keys(body, 'location', {f: Vector((0, 0, 0.0015 * math.sin(f * 2.7) + 0.001 * math.sin(f * 5.3))) for f in range(0, kit.IDLE_END)} |
         {kit.IDLE_END: Vector((0, 0, 0))}, 'LINEAR')
    kit.to_track(body, 'Idle')
    spin(wheels, frames)
    for objects, turns in extra:
        spin(objects, frames, turns)
    keys(body, 'location', {f: Vector((0, 0, rock * math.sin(4 * math.pi * f / frames))) for f in range(frames + 1)}, 'LINEAR')
    keys(body, 'rotation_euler', {f: Vector((rock * 1.5 * math.sin(2 * math.pi * f / frames + 1), 0, 0)) for f in range(frames + 1)}, 'LINEAR')
    kit.to_track(body, 'Walk')


def fire(flashes, frames, recoil=None, walk_frames=None):
    """The Fire clip: the flashes light up for a few frames, the barrel (recoil:
    (object, rest location, kick)) jumps back and runs out again. The flashes are hidden
    in Idle and Walk, the barrel keyed at rest there."""
    for obj in flashes:
        kit.keys(obj, 'scale', {0: Vector((1, 1, 1)), 2: Vector((1.3, 1.5, 1.3)), 4: Vector((kit.HIDDEN,) * 3),
                                frames: Vector((kit.HIDDEN,) * 3)}, 'CONSTANT')
        kit.to_track(obj, 'Fire')
    walker.hide(flashes, kit.IDLE_END, 'Idle')
    walker.hide(flashes, walk_frames or kit.IDLE_END, 'Walk')
    if recoil:
        obj, rest, kick = recoil
        kit.keys(obj, 'location', {0: rest, 2: rest + kick, 5: rest + kick, min(16, frames): rest, frames: rest})
        kit.to_track(obj, 'Fire')
        walker.hold(obj, 'location', rest, kit.IDLE_END, 'Idle')
        walker.hold(obj, 'location', rest, walk_frames or kit.IDLE_END, 'Walk')
        obj.location = rest
    for obj in flashes:
        obj.scale = (kit.HIDDEN,) * 3


def start(collection, name, walk_speed):
    """A fresh collection with the root (walkSpeed set) and the Body empty on it."""
    kit.COLLECTION = collection
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = kit.IDLE_END
    root = kit.empty(name)
    root['walkSpeed'] = round(walk_speed, 4)
    body = kit.parent(kit.empty('Body'), root)
    return root, body


def hold_rest(rest):
    """Keys every animated object at its rest pose (`rest`: name → location, rotation,
    quaternion, scale) in the clips that do not move it: the exporter puts all animated
    objects into every clip, those a clip leaves alone in whatever pose the scene was
    last in (the turret would stay on the tail after Undeploy, the hull dug in while
    firing on the move)."""
    animated = [obj for obj in kit.collection().objects if obj.animation_data and obj.animation_data.nla_tracks]
    lengths = {}
    for obj in animated:
        for track in obj.animation_data.nla_tracks:
            for strip in track.strips:
                lengths[track.name] = max(lengths.get(track.name, 0), int(round(strip.frame_end)))
    for obj in animated:
        have = {track.name for track in obj.animation_data.nla_tracks}
        location, rotation, _, scale = rest[obj.name]
        for clip, frames in lengths.items():
            if clip in have:
                continue
            for path, value in (('location', location), ('rotation_euler', rotation), ('scale', scale)):
                walker.hold(obj, path, value, frames, clip)
        obj.location, obj.rotation_euler, obj.scale = location, rotation, scale


def main(build, out, blend, preview_clips, scale=1.4, target=(0, 0, 0.15)):
    """Builds, renders previews (-- --preview <dir>), saves the .blend, exports the GLB."""
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    # the rest pose: evaluating the clips (the previews) writes their poses into the objects
    rest = {obj.name: (obj.location.copy(), obj.rotation_euler.copy(), obj.rotation_quaternion.copy(), obj.scale.copy())
            for obj in kit.collection().objects}
    if '--preview' in args:
        walker.previews(args[args.index('--preview') + 1], preview_clips, scale=scale, target=target)
    for obj in kit.collection().objects:
        obj.location, obj.rotation_euler, obj.rotation_quaternion, obj.scale = rest[obj.name]
    hold_rest(rest)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    print('export', walker.export(out), flush=True)
