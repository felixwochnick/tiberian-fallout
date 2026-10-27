"""
Tiberian Fallout – shared parts of the Nod defences, walls and pads (NALASR, NASAM,
NAPULS, NAHPAD, NAWALL, NAGATE_A).

Nod builds in dark concrete and dark armour with red (house colour) accents:
    Nod_*        concrete: a procedural shader (mottling, streaks, speckles, darker in
                 the corners) baked to a texture per object; extra nodColour white (the
                 texture carries the colour)
    NodArmour*   dark armour plates (nodvehicle.materials), extra nodColour = its colour
    Remap        the house colour (accents: rims, bands, stripes)
    Lamp*, Glow* emissive bulbs and additive halos as in the other models

Gun towers have the nodes the game aims (see Combat in app/lib/game/combat.ts):
    Turret   turns about the vertical towards the target (never keyed by a clip)
    Cannon   inside the turret, tipped up and down (never keyed); its barrel looks
             along -Y (glTF +Z)
    Flash…   the muzzle: a glow hidden at rest, shown by the Fire clip
The building animations hang on nodes above or below them ("Mount" carries the turret
out of the ground in Build).

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is in
the middle of the foundation on the ground.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import nodvehicle as nod  # noqa: E402 – Nod materials, hold_rest()
import walker  # noqa: E402 – hide(), hold(), export(), previews()

PROJECT = os.path.dirname(HERE)
HIDDEN = kit.HIDDEN

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material

NOD_RED = '#c42a1c'      # the house colour in the previews (the game sets the player's)
CONCRETE = {
    'dark': '#4b4c4f',    # the towers' footings and bodies
    'olive': '#5f6158',   # the EMP cannon's greenish grey base
    'grey': '#7b7c7e',    # walls and gate
}


def model_path(name):
    return os.path.join(PROJECT, 'public', 'models', f'{name}.glb'), os.path.join(HERE, f'{name}.blend')


def start(collection, root_name, frames=90):
    """A fresh collection with the root empty."""
    kit.COLLECTION = collection
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = frames
    scene.frame_current = 0
    return kit.empty(root_name)


def materials():
    m = nod.materials()
    m['remap'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*srgb(NOD_RED), 1)
    for key, colour in (('armour', '#45474c'), ('armour_dark', '#26272b')):
        m[key]['nodColour'] = colour
    m['hazard_dark'] = material('HazardDark', srgb('#1c1b1a'), 0.8)
    m['glow_laser'] = material('GlowLaser', (0, 0, 0), 1.0, emission=srgb('#ff3a1c'), strength=8, alpha=0.6)
    m['glow_pulse'] = material('GlowPulse', (0, 0, 0), 1.0, emission=srgb('#5ad8ff'), strength=8, alpha=0.6)
    m['lamp_pulse'] = material('LampPulse', srgb('#b8f4ff'), 0.2, emission=srgb('#7ae4ff'), strength=10)
    return m


# --------------------------------------------------------------------------- concrete

def concrete_material(name, colour, reference):
    """Live procedural concrete (Blender preview, source of the bake)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()
    nodes, links = nt.nodes, nt.links
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.9
    coords = nodes.new('ShaderNodeTexCoord')
    coords.object = reference

    def factor(scale, low, high, detail=4.0, frm=(0.3, 0.7)):
        mapping = nodes.new('ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = scale
        links.new(coords.outputs['Object'], mapping.inputs['Vector'])
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Detail'].default_value = detail
        links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
        span = nodes.new('ShaderNodeMapRange')
        span.inputs['From Min'].default_value, span.inputs['From Max'].default_value = frm
        span.inputs['To Min'].default_value = low
        span.inputs['To Max'].default_value = high
        links.new(noise.outputs['Fac'], span.inputs['Value'])
        return span.outputs['Result']

    ao = nodes.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = 0.06
    ao.samples = 16
    shade = nodes.new('ShaderNodeMapRange')
    shade.inputs['To Min'].default_value = 0.62
    links.new(ao.outputs['AO'], shade.inputs['Value'])
    total = None
    for f in (factor((5, 5, 5), 0.86, 1.12),            # big mottling
              factor((70, 70, 70), 0.88, 1.06, 2.0),    # speckles
              factor((28, 28, 2.2), 0.84, 1.02),        # rain streaks down the walls
              shade.outputs['Result']):
        node = nodes.new('ShaderNodeMath')
        node.operation = 'MULTIPLY'
        if total is None:
            node.inputs[0].default_value = 1.0
        else:
            links.new(total, node.inputs[0])
        links.new(f, node.inputs[1])
        total = node.outputs['Value']
    tint = nodes.new('ShaderNodeMix')
    tint.data_type = 'RGBA'
    tint.blend_type = 'MULTIPLY'
    tint.inputs['Factor'].default_value = 1.0
    tint.inputs['B'].default_value = (*srgb(colour), 1)
    grey = nodes.new('ShaderNodeCombineColor')
    for channel in ('Red', 'Green', 'Blue'):
        links.new(total, grey.inputs[channel])
    links.new(grey.outputs['Color'], tint.inputs['A'])
    links.new(tint.outputs['Result'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    mat['nodColour'] = '#ffffff'   # the baked texture carries the colour
    return mat


def concrete(name, parts, root, tone='dark', pivot=(0, 0, 0)):
    """Merges `parts` into one object in baked concrete of a tone (CONCRETE)."""
    obj = kit.merge(name, parts, pivot)
    obj.data.materials.clear()
    obj.data.materials.append(concrete_material(f'Nod_{name}', CONCRETE[tone], root))
    return obj


def bake(size=512):
    """Bakes every Nod_* concrete into an image texture (in the rest pose)."""
    kit.setup_cycles()
    view_layer = bpy.context.view_layer
    for obj in [o for o in kit.collection().objects if o.type == 'MESH' and o.data.materials and o.data.materials[0].name.startswith('Nod_')]:
        mat = obj.data.materials[0]
        bpy.ops.object.select_all(action='DESELECT')
        view_layer.objects.active = obj
        obj.select_set(True)
        if not obj.data.uv_layers:
            obj.data.uv_layers.new(name='UVMap')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.01)
            bpy.ops.object.mode_set(mode='OBJECT')
        image = bpy.data.images.get(f'{mat.name}_Color') or bpy.data.images.new(f'{mat.name}_Color', size, size)
        nt = mat.node_tree
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        colour = bsdf.inputs['Base Color'].links[0].from_socket
        emit = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(colour, emit.inputs['Color'])
        nt.links.new(emit.outputs['Emission'], out.inputs['Surface'])
        target = nt.nodes.new('ShaderNodeTexImage')
        target.image = image
        nt.nodes.active = target
        bpy.ops.object.bake(type='EMIT', margin=8)
        image.file_format = 'PNG'
        image.pack()
        nt.nodes.remove(emit)
        nt.links.new(target.outputs['Color'], bsdf.inputs['Base Color'])
        nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        print('baked', obj.name, flush=True)


# --------------------------------------------------------------------------- parts

def stripes(name, m, centre, size, axis='X', count=8, normal='Z'):
    """A yellow and black hazard band: a dark strip with slanted yellow bars across it,
    `size` (length along `axis`, width, thickness); lies flat (normal Z) or stands on a
    wall facing -Y/+Y (normal 'Y')."""
    centre = Vector(centre)
    length, width, thick = size
    parts = []
    if normal == 'Z':
        dims = (length, width, thick) if axis == 'X' else (width, length, thick)
    else:
        dims = (length, thick, width)
    parts.append(box(f'{name}Base', m['hazard_dark'], dims, centre, bevel=0))
    step = length / count
    for k in range(count):
        t = -length / 2 + (k + 0.5) * step
        if normal == 'Z':
            off = Vector((t, 0, thick * 0.3)) if axis == 'X' else Vector((0, t, thick * 0.3))
            rot = (0, 0, math.radians(35)) if axis == 'X' else (0, 0, math.radians(55))
            bar = (step * 0.5, width * 2.2, thick * 0.6) if axis == 'X' else (width * 2.2, step * 0.5, thick * 0.6)
            p = box(f'{name}Bar{k}', m['hazard'], bar, centre + off, bevel=0, rotation=rot)
            parts.append(p)
        else:
            parts.append(box(f'{name}Bar{k}', m['hazard'], (step * 0.45, thick * 1.4, width * 1.1), centre + Vector((t, 0, 0)), bevel=0,
                             rotation=(0, math.radians(35), 0)))
    obj = kit.merge(name, parts, centre)
    clip_to(obj, centre, dims, (0, 1) if normal == 'Z' else (0, 2))
    return obj


def clip_to(obj, centre, dims, axes=(0, 1, 2)):
    """Cuts a merged object to a box (the slanted bars stick out at the ends)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    half = Vector(dims) / 2
    offset = Vector(centre) - obj.location
    for axis in axes:
        for sign in (-1, 1):
            co = Vector((0, 0, 0))
            no = Vector((0, 0, 0))
            co[axis] = offset[axis] + sign * half[axis]
            no[axis] = sign
            geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_outer=True)
    bm.to_mesh(obj.data)
    bm.free()


def glow(m, name, centre, size, mat, balls=3, facing=(0, -1, 0)):
    """Glowing balls along `facing` from `centre` (a muzzle flash, a charge)."""
    centre, facing = Vector(centre), Vector(facing).normalized()
    parts = [sphere(f'{name}{k}', m[mat], size * (1 - 0.22 * k), centre + facing * size * 0.9 * k, 12) for k in range(balls)]
    return kit.merge(name, parts, centre)


def lamp(name, m, location, colour='red'):
    """A small lamp housing (returned first) and its bulb + halo, which blinks."""
    housing, light = kit.beacon(name, m, location, colour)
    return kit.merge(f'{name}Housing', [housing], location), light


def rise(obj, start, length, depth):
    """Rises out of the ground by `depth` (keys location), with a small overshoot."""
    rest = obj.location.copy()
    below = rest - Vector((0, 0, depth))
    kit.keys(obj, 'location', {0: below, start: below, start + length: rest + Vector((0, 0, 0.01)), start + length + 3: rest})


def grow_z(obj, start, length):
    """Scales up from the ground (keys scale z from its origin)."""
    s = obj.scale.copy()
    flat = Vector((s.x, s.y, HIDDEN))
    kit.keys(obj, 'scale', {0: flat, start: flat, start + length: Vector((s.x, s.y, s.z * 1.04)), start + length + 3: s})


def show_at(obj, frame):
    """Hidden until `frame`, then there (constant keys)."""
    s = obj.scale.copy()
    kit.keys(obj, 'scale', {0: s * HIDDEN, frame - 1: s * HIDDEN, frame: s}, 'CONSTANT')


def all_to_build():
    """Every object with an active action: that action is the Build clip."""
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')


def flash_keys(obj, frames, on, off, peak=1.4):
    """The flash hidden, shown from `on` (bigger in the middle), hidden from `off`."""
    hidden = Vector((HIDDEN,) * 3)
    mid = (on + off) // 2
    keyed = {0: hidden, on: Vector((1, 1, 1)), off: hidden, frames: hidden}
    if on < mid < off:
        keyed[mid] = Vector((peak,) * 3)
    if on == 0:
        keyed[0] = Vector((1, 1, 1))
    kit.keys(obj, 'scale', keyed, 'CONSTANT')


def blinking(lights, track='Idle'):
    """lights: (object, frames on); the Idle loop."""
    for light, pattern in lights:
        kit.blink(light, pattern)
        kit.to_track(light, track)


# --------------------------------------------------------------------------- run

def _mute(state):
    for obj in bpy.data.objects:
        if obj.animation_data:
            for track in obj.animation_data.nla_tracks:
                track.mute = state


def main(build, name, preview_clips, scale=2.0, target=(0, 0, 0.3), texture=512):
    """Builds, bakes the concrete, renders previews (-- --preview <dir>), saves the
    .blend, exports the GLB. `build()` leaves every object in its rest pose (the
    finished building, guns level, flashes hidden, gates shut)."""
    out, blend = model_path(name)
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    rest = {obj.name: (obj.location.copy(), obj.rotation_euler.copy(), obj.rotation_quaternion.copy(), obj.scale.copy())
            for obj in kit.collection().objects}
    _mute(True)
    bake(texture)
    _mute(False)
    nod.hold_rest(rest)
    if '--preview' in args:
        walker.previews(args[args.index('--preview') + 1], preview_clips, scale=scale, target=target)
    for obj in kit.collection().objects:
        obj.location, obj.rotation_euler, obj.rotation_quaternion, obj.scale = rest[obj.name]
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    print('export', walker.export(out), flush=True)
