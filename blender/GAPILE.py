"""
Tiberian Fallout – GDI barracks (GAPILE), modelled after Tiberian Sun.

Two long armoured halls on dark footings (foundation 2 × 2 cells), each with sloped,
X-braced buttresses at its ends, joined across a small yard by two ribbed tubes.
Stairs and a ramp lead down from the front hall; the back hall carries a radio mast,
a flag pole with the GDI flag stands at the back right.

Materials
    Camo_*   desert camouflage: a procedural shader (CamoProcedural) baked to a texture
    Remap    stripes tinted with the house colour in the game
    Lamp*    emissive bulbs, Glow* additive halos around them (the game blends them additively)

Animations (glTF clips, merged from the NLA tracks of the same name)
    Build    one-shot, 2.4 s: the pad grows, the halls rise out of the ground, tubes,
             roof fittings, ramps, masts and finally the flag appear
    Idle     loop, 2 s: the flag waves in the wind (morph targets), the beacons blink

Run headless (builds, bakes, saves the .blend, exports the GLB):

    Blender -b --factory-startup --python blender/GAPILE.py

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z).
"""
import math
import os
import re
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAPILE.glb')
LOGO = os.path.join(PROJECT, 'public', 'logos', 'gdi.svg')
BLEND = os.path.join(HERE, 'GAPILE.blend')
COLLECTION = 'GDIBarracks'

FPS = 30
BUILD_END = 72          # frames of the Build clip
IDLE_END = 60           # frames of the Idle loop

PAD_TOP = 0.06
WALL_TOP = 0.40
ROOF = 0.465            # top of the raised roof panels
HALL_DEPTH = 0.58
HIDDEN = 0.001          # scale of not yet built parts (0 would make singular matrices)


# --------------------------------------------------------------------------- helpers

def collection():
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(col)
    return col


def srgb(hex_colour):
    """'#rrggbb' to linear RGB (Blender colours are linear)."""
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hex_colour.lstrip('#')
    return tuple(lin(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def material(name, colour, roughness=0.8, metallic=0.0, emission=None, strength=4.0, alpha=1.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (*colour, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    if emission:
        bsdf.inputs['Emission Color'].default_value = (*emission, 1)
        bsdf.inputs['Emission Strength'].default_value = strength
    if alpha < 1:
        bsdf.inputs['Alpha'].default_value = alpha
        mat.surface_render_method = 'BLENDED'
    return mat


def finish(obj, mat, bevel=0.01, segments=2):
    mat.use_backface_culling = mat.name != 'Flag'  # glTF: single-sided except the cloth
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new('Bevel', 'BEVEL')
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = 'ANGLE'
        mod.angle_limit = math.radians(35)
        mod.harden_normals = True
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def mesh_object(name, build):
    """Creates an object from a bmesh filled by `build(bm)`."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    collection().objects.link(obj)
    return obj


def box(name, mat, size, location, bevel=0.008, rotation=(0, 0, 0)):
    sx, sy, sz = size

    def build(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)

    obj = mesh_object(name, build)
    obj.location = location
    obj.rotation_euler = rotation
    return finish(obj, mat, bevel)


def hexahedron(name, mat, verts, bevel=0.012):
    """Six-sided solid from 8 corners: bottom 0-3 and top 4-7, both in the same winding."""
    def build(bm):
        v = [bm.verts.new(p) for p in verts]
        for face in ((0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            bm.faces.new([v[i] for i in face])

    return finish(mesh_object(name, build), mat, bevel)


def frustum(name, mat, bottom, top, height, location, bevel=0.012):
    """A box whose top is smaller than its bottom: sloped walls. bottom/top = (x, y)."""
    (bx, by), (tx, ty) = bottom, top
    obj = hexahedron(name, mat, (
        (-bx / 2, -by / 2, 0), (bx / 2, -by / 2, 0), (bx / 2, by / 2, 0), (-bx / 2, by / 2, 0),
        (-tx / 2, -ty / 2, height), (tx / 2, -ty / 2, height), (tx / 2, ty / 2, height), (-tx / 2, ty / 2, height),
    ), bevel)
    obj.location = location
    return obj


def cylinder(name, mat, radius, depth, location, rotation=(0, 0, 0), segments=20, bevel=0.004, radius2=None):
    def build(bm):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius,
                              radius2=radius if radius2 is None else radius2, depth=depth)

    obj = mesh_object(name, build)
    obj.location = location
    obj.rotation_euler = rotation
    return finish(obj, mat, bevel, 1)


def sphere(name, mat, radius, location, segments=12):
    def build(bm):
        bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=segments // 2 + 2, radius=radius)

    obj = mesh_object(name, build)
    obj.location = location
    return finish(obj, mat, 0)


def beam(name, mat, p0, p1, width, depth=None):
    """A thin box from p0 to p1 (struts, rails, braces)."""
    p0, p1 = Vector(p0), Vector(p1)
    obj = box(name, mat, (width, depth or width, (p1 - p0).length), (p0 + p1) / 2, bevel=0)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = (p1 - p0).to_track_quat('Z', 'Y')
    return obj


def bake_modifiers(obj):
    """Applies the modifiers (and the transform) to the mesh data."""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    mesh.transform(obj.matrix_world)
    old = obj.data
    obj.modifiers.clear()
    obj.data = mesh
    obj.matrix_world = Matrix.Identity(4)
    bpy.data.meshes.remove(old)
    return obj


def merge(name, objects, pivot=(0, 0, 0)):
    """Joins objects (modifiers applied, materials kept) into one object whose origin is `pivot`."""
    pivot = Vector(pivot)
    bm = bmesh.new()
    materials = []
    for obj in objects:
        bake_modifiers(obj)
        slots = []
        for mat in obj.data.materials:
            if mat not in materials:
                materials.append(mat)
            slots.append(materials.index(mat))
        part = obj.data.copy()
        part.transform(Matrix.Translation(-pivot))
        indices = [slots[poly.material_index] for poly in part.polygons]
        first = len(bm.faces)
        bm.from_mesh(part)
        bm.faces.ensure_lookup_table()
        for face, index in zip(bm.faces[first:], indices):
            face.material_index = index
        bpy.data.meshes.remove(part)
        bpy.data.objects.remove(obj, do_unlink=True)
    mesh = bpy.data.meshes.new(name)
    for mat in materials:  # slots first: changing them later resets the face indices
        mesh.materials.append(mat)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = pivot
    collection().objects.link(obj)
    return obj


def empty(name, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = 0.2
    obj.location = location
    collection().objects.link(obj)
    return obj


def parent(child, parent_obj):
    """Parents without moving the child."""
    bpy.context.view_layer.update()
    world = child.matrix_world.copy()
    child.parent = parent_obj
    child.matrix_parent_inverse = Matrix.Identity(4)
    child.matrix_world = world
    return child


# --------------------------------------------------------------------------- materials

def materials():
    m = {
        'concrete': material('Concrete', srgb('#a39f94'), 0.92),
        'concrete_dark': material('ConcreteDark', srgb('#5e5a50'), 0.95),
        'sand': material('Sand', srgb('#bba57a'), 0.8),
        'sand_light': material('SandLight', srgb('#d2bf92'), 0.75),
        'remap': material('Remap', srgb('#d8b43a'), 0.55, 0.15),
        'steel': material('Steel', srgb('#4a4d50'), 0.45, 0.85),
        'steel_light': material('SteelLight', srgb('#9da2a6'), 0.4, 0.85),
        'grating': material('Grating', srgb('#34352f'), 0.7, 0.6),
        'dark': material('Dark', srgb('#17181a'), 0.9),
        'window': material('Window', srgb('#1d2a33'), 0.15, 0.3, emission=srgb('#3a5a70'), strength=0.6),
        'olive': material('Olive', srgb('#565a36'), 0.85),
        'gold': material('Gold', srgb('#d9b14a'), 0.3, 1.0),
        'lamp_white': material('LampWhite', srgb('#fff7dc'), 0.2, emission=srgb('#fff2c8'), strength=6),
        'lamp_red': material('LampRed', srgb('#ff3020'), 0.2, emission=srgb('#ff2a10'), strength=10),
        'lamp_amber': material('LampAmber', srgb('#ffaa20'), 0.2, emission=srgb('#ff9a10'), strength=8),
        'lamp_green': material('LampGreen', srgb('#40ff60'), 0.2, emission=srgb('#30ff50'), strength=8),
        'signal': material('SignalCyan', srgb('#40d8ff'), 0.2, emission=srgb('#30c8ff'), strength=5),
    }
    for colour, key in (('#ff2a10', 'red'), ('#ff9a10', 'amber'), ('#30ff50', 'green')):
        m[f'glow_{key}'] = material(f'Glow{key.capitalize()}', (0, 0, 0), 1.0, emission=srgb(colour), strength=3, alpha=0.25)
    return m


CAMO = {
    'sand': '#cbb88a',
    'khaki': '#a08d5e',
    'brown': '#7a5f45',
    'olive': '#5e5c3c',
}


def camo_nodes(nt, reference):
    """Procedural desert camouflage; returns the colour socket. The pattern is laid out in
    the space of `reference` (the building's root), so it runs on across all parts."""
    nodes, links = nt.nodes, nt.links
    coords = nodes.new('ShaderNodeTexCoord')
    coords.object = reference
    mapping = nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (1.0, 1.0, 1.6)
    links.new(coords.outputs['Object'], mapping.inputs['Vector'])

    def blotches(scale, seed, threshold):
        noise = nodes.new('ShaderNodeTexNoise')
        noise.noise_dimensions = '4D'
        noise.inputs['Scale'].default_value = scale
        noise.inputs['W'].default_value = seed
        noise.inputs['Detail'].default_value = 3.0
        noise.inputs['Roughness'].default_value = 0.55
        noise.inputs['Distortion'].default_value = 0.35
        links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
        edge = nodes.new('ShaderNodeMapRange')
        edge.interpolation_type = 'SMOOTHSTEP'
        edge.inputs['From Min'].default_value = threshold
        edge.inputs['From Max'].default_value = threshold + 0.012
        links.new(noise.outputs['Fac'], edge.inputs['Value'])
        return edge.outputs['Result']

    def mix(a, b, factor):
        node = nodes.new('ShaderNodeMix')
        node.data_type = 'RGBA'
        if isinstance(a, tuple):
            node.inputs['A'].default_value = (*a, 1)
        else:
            links.new(a, node.inputs['A'])
        node.inputs['B'].default_value = (*b, 1)
        links.new(factor, node.inputs['Factor'])
        return node.outputs['Result']

    colour = srgb(CAMO['sand'])
    colour = mix(colour, srgb(CAMO['khaki']), blotches(3.0, 1.3, 0.52))
    colour = mix(colour, srgb(CAMO['brown']), blotches(3.6, 7.1, 0.57))
    colour = mix(colour, srgb(CAMO['olive']), blotches(4.2, 13.7, 0.62))

    # grime: fine speckles and vertical streaks, darker in the corners
    def grime(scale, low):
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Detail'].default_value = 6.0
        mapped = nodes.new('ShaderNodeMapping')
        mapped.inputs['Scale'].default_value = scale
        links.new(coords.outputs['Object'], mapped.inputs['Vector'])
        links.new(mapped.outputs['Vector'], noise.inputs['Vector'])
        span = nodes.new('ShaderNodeMapRange')
        span.inputs['To Min'].default_value = low
        span.inputs['From Min'].default_value = 0.3
        span.inputs['From Max'].default_value = 0.7
        links.new(noise.outputs['Fac'], span.inputs['Value'])
        return span.outputs['Result']

    ao = nodes.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = 0.08
    ao.samples = 16
    shade = nodes.new('ShaderNodeMapRange')
    shade.inputs['To Min'].default_value = 0.68
    links.new(ao.outputs['AO'], shade.inputs['Value'])

    total = None
    for factor in (grime((40, 40, 40), 0.86), grime((30, 30, 2.5), 0.88), shade.outputs['Result']):
        node = nodes.new('ShaderNodeMath')
        node.operation = 'MULTIPLY'
        if total is None:
            node.inputs[0].default_value = 1.0
        else:
            links.new(total, node.inputs[0])
        links.new(factor, node.inputs[1])
        total = node.outputs['Value']

    darken = nodes.new('ShaderNodeMix')
    darken.data_type = 'RGBA'
    darken.blend_type = 'MULTIPLY'
    darken.inputs['Factor'].default_value = 1.0
    links.new(colour, darken.inputs['A'])
    combine = nodes.new('ShaderNodeCombineColor')
    for channel in ('Red', 'Green', 'Blue'):
        links.new(total, combine.inputs[channel])
    links.new(combine.outputs['Color'], darken.inputs['B'])
    return darken.outputs['Result']


def camo_material(name, reference):
    """Live procedural camouflage material (Blender preview, source for the bake)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.85
    nt.links.new(camo_nodes(nt, reference), bsdf.inputs['Base Color'])
    nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat


# --------------------------------------------------------------------------- flag texture

def logo_polygons():
    """The GDI emblem from public/logos/gdi.svg as polygons (even-odd), in [-1, 1]."""
    path = re.search(r' d="([^"]+)"', open(LOGO).read()).group(1)
    polygons = []
    for sub in re.findall(r'M[^M]+', path):
        if 'A' in sub:  # the two half circles of the disc
            polygons.append([(math.cos(a), math.sin(a)) for a in np.linspace(0, 2 * math.pi, 160, endpoint=False)])
            continue
        points = [tuple(float(n) / 500 for n in p) for p in re.findall(r'(-?[\d.]+),(-?[\d.]+)', sub)]
        polygons.append(points)
    return polygons


def flag_image(width=512, height=320):
    """Gold cloth with the black GDI emblem, a darker hem and a little weave."""
    ys, xs = np.mgrid[0:height, 0:width].astype(np.float32)
    # emblem space: centred, radius 0.36 of the flag height; image rows run bottom-up, svg y down
    radius = height * 0.36
    ex = (xs + 0.5 - width * 0.52) / radius
    ey = -(ys + 0.5 - height / 2) / radius
    inside = np.zeros((height, width), bool)
    for poly in logo_polygons():
        p = np.array(poly, np.float32)
        q = np.roll(p, -1, axis=0)
        for (x0, y0), (x1, y1) in zip(p, q):
            if y0 == y1:
                continue
            crosses = (ey >= min(y0, y1)) & (ey < max(y0, y1))
            x_at = x0 + (ey - y0) * (x1 - x0) / (y1 - y0)
            inside ^= crosses & (ex < x_at)

    # the image is sRGB: display colours, not linear ones
    gold = np.array((0xd6, 0xb0, 0x45), np.float32) / 255
    black = np.array((0x16, 0x15, 0x10), np.float32) / 255
    rgb = np.where(inside[..., None], black, gold)
    hem = (xs < 10) | (xs > width - 7) | (ys < 7) | (ys > height - 7)
    rgb = np.where(hem[..., None], gold * 0.55, rgb)
    rng = np.random.default_rng(7)
    weave = 0.93 + 0.07 * (np.sin(xs * 1.7) * np.sin(ys * 1.7) * 0.5 + 0.5)
    rgb *= (weave * (0.97 + 0.03 * rng.random((height, width))))[..., None]

    image = bpy.data.images.get('FlagGDI') or bpy.data.images.new('FlagGDI', width, height)
    image.scale(width, height)
    rgba = np.concatenate([rgb, np.ones((height, width, 1), np.float32)], axis=2)
    image.pixels.foreach_set(rgba.ravel())
    image.file_format = 'PNG'
    image.pack()
    return image


def flag_material():
    mat = bpy.data.materials.get('Flag') or bpy.data.materials.new('Flag')
    mat.use_nodes = True
    mat.use_backface_culling = False
    nt = mat.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.9
    tex = nt.nodes.get('FlagTexture') or nt.nodes.new('ShaderNodeTexImage')
    tex.name = 'FlagTexture'
    tex.image = flag_image()
    nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    return mat


# --------------------------------------------------------------------------- animation

def keys(obj, path, frames, interpolation='BEZIER'):
    """frames: {frame: value}; keys the property `path` of `obj`."""
    prefs = bpy.context.preferences.edit
    old = prefs.keyframe_new_interpolation_type
    prefs.keyframe_new_interpolation_type = interpolation
    for frame, value in sorted(frames.items()):
        setattr(obj, path, value)
        obj.keyframe_insert(path, frame=frame)
    prefs.keyframe_new_interpolation_type = old


def to_track(id_data, track_name):
    """Moves the active action of a datablock onto an NLA track (one glTF clip per track name)."""
    ad = id_data.animation_data
    action = ad.action
    action.name = f'{track_name}_{id_data.name}'
    slot = ad.action_slot
    track = ad.nla_tracks.new()
    track.name = track_name
    strip = track.strips.new(track_name, 0, action)
    if hasattr(strip, 'action_slot') and slot is not None:
        strip.action_slot = slot
    ad.action = None


def pop(obj, start, length=8):
    """Scales in from nothing with a small overshoot."""
    s = Vector(obj.scale)
    keys(obj, 'scale', {0: s * HIDDEN, start: s * HIDDEN, start + length * 0.65: s * 1.15, start + length: s})


def grow(obj, start, length, axis):
    """Grows along one local axis (its origin stays), like a telescopic mast."""
    s = Vector(obj.scale)
    first = s.copy()
    first[axis] = HIDDEN
    keys(obj, 'scale', {0: s * HIDDEN, start - 1: s * HIDDEN, start: first, start + length: s})


def blink(obj, pattern):
    """pattern: frames (within the Idle loop) where the light is on, as a set."""
    frames = {}
    state = None
    for f in range(IDLE_END + 1):
        on = (f % IDLE_END) in pattern
        if on != state or f in (0, IDLE_END):
            frames[f] = Vector((1, 1, 1)) if on else Vector((HIDDEN,) * 3)
            state = on
    keys(obj, 'scale', frames, 'CONSTANT')


def flashes(*spans):
    return {f % IDLE_END for start, length in spans for f in range(start, start + length)}


# --------------------------------------------------------------------------- model parts

def beacon(name, m, location, glow='red', lamp=None):
    """A small lamp housing with its bulb + halo as a separate child (that one blinks)."""
    x, y, z = location
    housing = cylinder(f'{name}Housing', m['steel'], 0.016, 0.022, (x, y, z + 0.011), segments=10, bevel=0)
    bulb = sphere(f'{name}Bulb', lamp or m[f'lamp_{glow}'], 0.016, (x, y, z + 0.03), 10)
    halo = sphere(f'{name}Halo', m[f'glow_{glow}'], 0.03, (x, y, z + 0.03), 10)
    light = merge(f'{name}Light', [bulb, halo], (x, y, z + 0.03))
    return housing, light


def ac_unit(name, m, x, y):
    parts = [
        box(f'{name}Base', m['steel'], (0.17, 0.17, 0.03), (x, y, ROOF + 0.015)),
        cylinder(f'{name}Drum', m['steel_light'], 0.065, 0.06, (x, y, ROOF + 0.06)),
        cylinder(f'{name}Grille', m['dark'], 0.052, 0.006, (x, y, ROOF + 0.091), segments=16, bevel=0),
    ]
    for i in range(3):
        a = i * math.pi / 3
        parts.append(beam(f'{name}Blade{i}', m['steel'], (x - 0.05 * math.cos(a), y - 0.05 * math.sin(a), ROOF + 0.095),
                          (x + 0.05 * math.cos(a), y + 0.05 * math.sin(a), ROOF + 0.095), 0.012, 0.004))
    return merge(name, parts, (x, y, ROOF))


def vent_block(name, m, x, y):
    parts = [box(f'{name}Block', m['concrete_dark'], (0.17, 0.09, 0.05), (x, y, ROOF + 0.025))]
    for dx in (-0.04, 0.04):
        parts.append(box(f'{name}Hole{dx}', m['dark'], (0.06, 0.06, 0.01), (x + dx, y, ROOF + 0.05), bevel=0.002))
    return merge(name, parts, (x, y, ROOF))


def floodlight(name, m, x, y, facing):
    """facing: unit vector (x, y) the lamp points to."""
    fx, fy = facing
    parts = [
        cylinder(f'{name}Pole', m['steel'], 0.009, 0.16, (x, y, ROOF + 0.08), segments=8, bevel=0),
        box(f'{name}Head', m['steel'], (0.07, 0.05, 0.045), (x, y, ROOF + 0.17), bevel=0.006,
            rotation=(0, 0, math.atan2(fy, fx) - math.pi / 2)),
        box(f'{name}Glass', m['lamp_white'], (0.055, 0.008, 0.032), (x + fx * 0.026, y + fy * 0.026, ROOF + 0.17),
            bevel=0.002, rotation=(0, 0, math.atan2(fy, fx) - math.pi / 2)),
    ]
    return merge(name, parts, (x, y, ROOF))


def dish(name, m, x, y):
    parts = [
        cylinder(f'{name}Stand', m['steel'], 0.012, 0.07, (x, y, ROOF + 0.035), segments=8, bevel=0),
        cylinder(f'{name}Bowl', m['steel_light'], 0.07, 0.03, (x + 0.01, y - 0.01, ROOF + 0.09),
                 rotation=(math.radians(35), 0, math.radians(-30)), radius2=0.02, segments=20),
        beam(f'{name}Feed', m['steel'], (x + 0.01, y - 0.01, ROOF + 0.09), (x + 0.03, y - 0.06, ROOF + 0.15), 0.006),
    ]
    return merge(name, parts, (x, y, ROOF))


def hall(name, m, y0, root, front):
    """One armoured hall along X, centred at y0. Returns (group, shell, details)."""
    group = parent(empty(name), root)
    d = HALL_DEPTH / 2
    static = {}

    def add(key, obj):
        static.setdefault(key, []).append(obj)

    # ---- shell: sloped walls and the buttresses at both ends (camouflage, baked)
    shell = [frustum(f'{name}Body', m['sand'], (1.2, HALL_DEPTH), (1.16, HALL_DEPTH - 0.04), WALL_TOP - PAD_TOP, (0, y0, PAD_TOP))]
    for s in (-1, 1):
        b = ((s * 0.58, y0 - 0.26, PAD_TOP), (s * 0.58, y0 + 0.26, PAD_TOP), (s * 0.86, y0 + 0.24, PAD_TOP), (s * 0.86, y0 - 0.24, PAD_TOP))
        t = ((s * 0.58, y0 - 0.2, 0.37), (s * 0.58, y0 + 0.2, 0.37), (s * 0.66, y0 + 0.18, 0.37), (s * 0.66, y0 - 0.18, 0.37))
        shell.append(hexahedron(f'{name}Buttress{s}', m['sand'], b + t))
        # X-bracing on the sloped end face
        n = Vector((s * 0.31, 0, 0.28)).normalized() * 0.012
        bm_, bp = Vector(b[3]) + n, Vector(b[2]) + n
        tm, tp = Vector(t[3]) + n, Vector(t[2]) + n
        for i, (p0, p1) in enumerate(((bm_, tp), (bp, tm), (bm_, tm), (bp, tp), (tm, tp))):
            add('steel', beam(f'{name}Brace{s}{i}', m['steel'], p0, p1, 0.022, 0.014))
        add('steel', beam(f'{name}Foot{s}', m['steel'], bm_ + Vector((0, 0, 0.012)), bp + Vector((0, 0, 0.012)), 0.03, 0.02))
    shell = merge(f'{name}Shell', shell)
    shell.data.materials.clear()
    shell.data.materials.append(camo_material(f'Camo_{name}', root))
    parent(shell, group)

    # ---- walls: ribs, a house-colour band, windows (front face y0 - d, back face y0 + d)
    for side in (-1, 1):
        face = y0 + side * (d - 0.01)
        for i in range(9):
            x = -0.52 + i * 0.13
            add('steel', box(f'{name}Rib{side}{i}', m['steel'], (0.02, 0.022, 0.27), (x, face + side * 0.004, 0.2)))
        add('remap', box(f'{name}Band{side}', m['remap'], (1.17, 0.012, 0.032), (0, face + side * 0.008, 0.35), bevel=0.003))
        add('steel', box(f'{name}Sill{side}', m['steel'], (1.17, 0.02, 0.012), (0, face + side * 0.01, 0.075), bevel=0.003))
        outside = (side == -1) == front  # the face that is not towards the yard
        for i, x in enumerate((-0.455, -0.325, -0.195, 0.065) if outside and front else (-0.455, -0.195, 0.065, 0.325)):
            add('window', box(f'{name}Window{side}{i}', m['window'], (0.09, 0.012, 0.04), (x, face + side * 0.008, 0.27), bevel=0.002))

    # ---- roof: base slab, raised panels with seams, hatches
    add('sand', box(f'{name}Roof', m['sand'], (1.18, HALL_DEPTH - 0.02, 0.03), (0, y0, WALL_TOP + 0.015), bevel=0.01))
    panels = ((-0.36, 0.42), (0.07, 0.38), (0.42, 0.26))
    for i, (x, w) in enumerate(panels):
        add('sand_light', box(f'{name}Panel{i}', m['sand_light'], (w, HALL_DEPTH - 0.1, 0.035), (x, y0, ROOF - 0.0175), bevel=0.008))
        add('dark', box(f'{name}Seam{i}', m['concrete_dark'], (0.012, HALL_DEPTH - 0.11, 0.004), (x - w / 4, y0, ROOF + 0.001), bevel=0))
    add('steel', box(f'{name}Hatch', m['steel'], (0.1, 0.1, 0.012), (-0.18, y0 + (0.12 if front else -0.12), ROOF + 0.006), bevel=0.003))
    add('remap', box(f'{name}RoofMark', m['remap'], (0.12, 0.02, 0.003), (0.07, y0 + 0.17, ROOF + 0.0015), bevel=0))

    for key, objs in static.items():
        parent(merge(f'{name}{key.title().replace("_", "")}', objs), group)
    return group, shell


def ramp(name, m, x, width, stairs):
    """Stairs or a smooth ramp from a door in the front face down to the pad. Returns the
    hinge object (origin on the top edge) to swing it down in the Build clip."""
    y_top, z_top = -0.72, 0.2
    y_end, z_end = -0.98, PAD_TOP
    parts = []
    if stairs:
        steps = 6
        for i in range(steps):
            t = (i + 0.5) / steps
            y = y_top + (y_end - y_top) * t
            z = z_top + (z_end - z_top) * t
            parts.append(box(f'{name}Step{i}', m['steel'], (width, (y_top - y_end) / steps + 0.004, 0.02), (x, y, z), bevel=0.003))
    else:
        def plate(bm):
            v = [bm.verts.new(p) for p in (
                (x - width / 2, y_end, z_end), (x + width / 2, y_end, z_end), (x + width / 2, y_top, z_top), (x - width / 2, y_top, z_top),
                (x - width / 2, y_end, z_end - 0.02), (x + width / 2, y_end, z_end - 0.02), (x + width / 2, y_top, z_top - 0.02), (x - width / 2, y_top, z_top - 0.02),
            )]
            for face in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
                bm.faces.new([v[i] for i in face])

        parts.append(finish(mesh_object(f'{name}Plate', plate), m['grating'], 0.004, 1))
        for i in range(7):  # anti-slip ribs
            t = (i + 0.5) / 7
            parts.append(box(f'{name}Grip{i}', m['steel_light'], (width - 0.02, 0.008, 0.006),
                             (x, y_top + (y_end - y_top) * t, z_top + (z_end - z_top) * t + 0.002), bevel=0))
    for s in (-1, 1):
        rx = x + s * width / 2
        parts.append(beam(f'{name}Stringer{s}', m['steel'], (rx, y_top, z_top - 0.01), (rx, y_end, z_end - 0.01), 0.014, 0.03))
        parts.append(beam(f'{name}Rail{s}', m['steel_light'], (rx, y_top, z_top + 0.08), (rx, y_end + 0.02, z_end + 0.08), 0.008))
        for t in (0.1, 0.9):
            p = Vector((rx, y_top + (y_end - y_top) * t, z_top + (z_end - z_top) * t))
            parts.append(beam(f'{name}Post{s}{t}', m['steel_light'], p, p + Vector((0, 0, 0.08)), 0.008))
    return merge(name, parts, (x, y_top, z_top))


def door(name, m, x, width, height):
    face = -0.72
    parts = [
        box(f'{name}Frame', m['steel'], (width + 0.05, 0.04, height + 0.03), (x, face + 0.005, 0.2 + height / 2), bevel=0.006),
        box(f'{name}Leaf', m['dark'], (width, 0.03, height), (x, face - 0.005, 0.2 + height / 2), bevel=0.003),
        box(f'{name}Hood', m['steel_light'], (width + 0.08, 0.06, 0.016), (x, face - 0.02, 0.2 + height + 0.025), bevel=0.004),
    ]
    for i in range(3):
        parts.append(box(f'{name}Slat{i}', m['steel'], (width - 0.02, 0.006, 0.006), (x, face - 0.022, 0.23 + i * height / 3), bevel=0))
    return merge(name, parts)


def tube(name, m, x):
    """Ribbed connector across the yard, origin in its middle (it grows from there)."""
    z = 0.25
    parts = [cylinder(f'{name}Pipe', m['steel_light'], 0.065, 0.3, (x, 0, z), rotation=(math.pi / 2, 0, 0), segments=24)]
    for i in range(6):
        parts.append(cylinder(f'{name}Rib{i}', m['steel'], 0.073, 0.016, (x, -0.11 + i * 0.044, z), rotation=(math.pi / 2, 0, 0), segments=24, bevel=0.003))
    return merge(name, parts, (x, 0, z))


# --------------------------------------------------------------------------- model

def build():
    for obj in list(collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 0
    scene.frame_end = BUILD_END + 18
    # parenting reads the evaluated pose: keep it at the finished building
    scene.frame_current = BUILD_END

    m = materials()
    root = empty('GDIBarracks')

    # ---- no concrete slab (like the power plant): dark footings under the halls, the
    # yard with its grating, an apron below the stairs and the ramp, the flag pole
    footing = m['concrete_dark']
    pad_parts = []
    for name, y0 in (('Front', -0.42), ('Back', 0.42)):
        pad_parts.append(box(f'Footing{name}', footing, (1.8, HALL_DEPTH + 0.1, PAD_TOP), (0, y0, PAD_TOP / 2), bevel=0.02))
        for x in (-0.45, 0.0, 0.45):  # joints between the footing's slabs
            pad_parts.append(box(f'FootingJoint{name}{x}', m['dark'], (0.01, HALL_DEPTH + 0.1, 0.003), (x, y0, PAD_TOP + 0.0015), bevel=0))
    pad_parts += [
        box('YardFooting', footing, (1.2, 0.3, PAD_TOP), (0, 0, PAD_TOP / 2), bevel=0.01),
        box('YardGrating', m['grating'], (1.12, 0.27, 0.008), (0, 0, PAD_TOP + 0.004), bevel=0),
        box('Apron', footing, (0.46, 0.32, PAD_TOP), (0.35, -0.87, PAD_TOP / 2), bevel=0.02),
        box('PoleFooting', footing, (0.16, 0.16, PAD_TOP), (0.86, 0.84, PAD_TOP / 2), bevel=0.015),
    ]
    pad_obj = parent(merge('Pad', pad_parts), root)
    keys(pad_obj, 'scale', {0: Vector((0.05, 0.05, 1)), 3: Vector((0.05, 0.05, 1)), 14: Vector((1.03, 1.03, 1)), 17: Vector((1, 1, 1))})

    # ---- the two halls rise out of the ground
    front, _ = hall('HallFront', m, -0.42, root, True)
    back, _ = hall('HallBack', m, 0.42, root, False)
    for group, start in ((front, 10), (back, 15)):
        keys(group, 'location', {0: Vector((0, 0, -0.5)), start: Vector((0, 0, -0.5)), start + 16: Vector((0, 0, 0.012)), start + 20: Vector((0, 0, 0))})

    # ---- entrances in the front face, with stairs and a ramp
    for name, x, width in (('DoorStairs', 0.24, 0.12), ('DoorRamp', 0.46, 0.15)):
        parent(door(name, m, x, width, 0.11), front)
    hinges = [parent(ramp('Stairs', m, 0.24, 0.12, True), root), parent(ramp('Ramp', m, 0.46, 0.15, False), root)]
    for hinge, start in zip(hinges, (40, 44)):
        keys(hinge, 'scale', {0: Vector((HIDDEN,) * 3), start - 1: Vector((HIDDEN,) * 3), start: Vector((1, 1, 1))}, 'CONSTANT')
        keys(hinge, 'rotation_euler', {0: Vector((-2.1, 0, 0)), start: Vector((-2.1, 0, 0)), start + 9: Vector((0.08, 0, 0)), start + 12: Vector((0, 0, 0))})

    # ---- connectors across the yard
    for i, (x, start) in enumerate(((-0.3, 34), (0.32, 37))):
        grow(parent(tube(f'Tube{i}', m, x), root), start, 7, 1)

    # ---- roof fittings pop up one after another
    fittings = [
        (ac_unit('AcFront', m, 0.42, -0.42), front, 36),
        (vent_block('VentFront', m, -0.4, -0.52), front, 40),
        (floodlight('FloodFront', m, -0.5, -0.64, (-0.5, -1)), front, 46),
        (ac_unit('AcBack', m, -0.05, 0.4), back, 39),
        (vent_block('VentBack', m, 0.4, 0.5), back, 43),
        (dish('Dish', m, 0.38, 0.32), back, 49),
        (floodlight('FloodBack', m, 0.18, 0.64, (0.3, 1)), back, 52),
    ]
    for obj, group, start in fittings:
        pop(parent(obj, group), start)

    # beacons on the roof corners (red, blinking in turn)
    lights = []
    corners = ((-0.52, -0.66, front, 0), (0.52, -0.66, front, 15), (0.52, 0.66, back, 30), (-0.52, 0.66, back, 45))
    for i, (x, y, group, phase) in enumerate(corners):
        housing, light = beacon(f'Beacon{i}', m, (x, y, WALL_TOP + 0.03))
        housing = merge(f'Beacon{i}', [housing], (x, y, WALL_TOP + 0.03))
        pop(parent(housing, group), 44 + i * 2, 6)
        parent(light, housing)
        lights.append((light, flashes((phase, 7))))

    # amber lights beside the doors blink alternately, a green one shows "ready"
    for i, x in enumerate((0.14, 0.34, 0.56)):
        housing, light = beacon(f'DoorLamp{i}', m, (x, -0.735, 0.33), 'amber')
        housing = merge(f'DoorLamp{i}', [housing], (x, -0.735, 0.33))
        pop(parent(housing, front), 50 + i, 6)
        parent(light, housing)
        lights.append((light, flashes((0, 15), (30, 15)) if i % 2 == 0 else flashes((15, 15), (45, 15))))
    housing, light = beacon('Ready', m, (0.46, -0.735, 0.39), 'green')
    housing = merge('Ready', [housing], (0.46, -0.735, 0.39))
    pop(parent(housing, front), 53, 6)
    parent(light, housing)
    lights.append((light, flashes((0, 42))))

    # ---- radio mast on the back hall: telescopes up, cyan signal light, red top beacon
    mx, my, mh = -0.42, 0.56, 0.78
    mast_parts = [
        box('MastFoot', m['steel'], (0.08, 0.08, 0.03), (mx, my, ROOF + 0.015), bevel=0.004),
        cylinder('MastPole', m['steel_light'], 0.011, mh, (mx, my, ROOF + mh / 2), segments=10, bevel=0),
        cylinder('MastSignal', m['signal'], 0.016, 0.14, (mx, my, ROOF + mh * 0.72), segments=10, bevel=0),
    ]
    for i, h in enumerate((0.3, 0.5)):
        mast_parts.append(beam(f'MastBar{i}', m['steel'], (mx - 0.06, my, ROOF + h), (mx + 0.06, my, ROOF + h), 0.008))
        mast_parts.append(beam(f'MastWhip{i}', m['steel'], (mx + 0.06, my, ROOF + h), (mx + 0.06, my, ROOF + h + 0.08), 0.005))
    for s in (-1, 1):  # guy wires
        mast_parts.append(beam(f'MastGuy{s}', m['steel'], (mx, my, ROOF + 0.45), (mx + s * 0.16, my - 0.1, ROOF), 0.004))
    mast = parent(merge('Mast', mast_parts, (mx, my, ROOF)), back)
    housing, light = beacon('MastTop', m, (mx, my, ROOF + mh))
    parent(housing, mast)
    parent(light, mast)
    grow(mast, 46, 12, 2)
    lights.append((light, flashes((0, 4), (8, 4), (30, 4), (38, 4))))

    # ---- flag pole at the back right
    px, py, ph = 0.86, 0.84, 1.32
    pole_parts = [
        box('PolePlinth', m['concrete_dark'], (0.1, 0.1, 0.05), (px, py, PAD_TOP + 0.025), bevel=0.008),
        cylinder('PoleShaft', m['steel_light'], 0.013, ph, (px, py, PAD_TOP + ph / 2), segments=12, bevel=0),
        sphere('PoleFinial', m['gold'], 0.022, (px, py, PAD_TOP + ph + 0.02)),
        cylinder('PoleCleat', m['steel'], 0.018, 0.04, (px, py, PAD_TOP + 0.5), segments=10, bevel=0),
    ]
    pole = parent(merge('FlagPole', pole_parts, (px, py, PAD_TOP)), root)
    grow(pole, 48, 12, 2)

    flag = parent(flag_object(m, (px + 0.014, py, PAD_TOP + ph - 0.01)), root)
    s = Vector(flag.scale)
    keys(flag, 'scale', {0: s * HIDDEN, 58: s * HIDDEN, 59: Vector((HIDDEN, 1, 0.3)), 61: Vector((0.15, 1, 1)), 68: Vector((1.04, 1, 1)), BUILD_END: s})

    # ---- clips: everything keyed so far is the Build clip
    for obj in collection().objects:
        if obj.animation_data and obj.animation_data.action:
            to_track(obj, 'Build')

    for light, pattern in lights:
        blink(light, pattern)
        to_track(light, 'Idle')
    wave_flag(flag)
    return len(collection().objects)


FLAG_W, FLAG_H = 0.5, 0.3
FLAG_COLS, FLAG_ROWS = 20, 12


def flag_object(m, top_left):
    """Cloth grid hanging from the pole (origin at the top of its pole edge), UV mapped."""
    def build(bm):
        uv = bm.loops.layers.uv.new('UVMap')
        grid, where = [], {}
        for r in range(FLAG_ROWS + 1):
            row = []
            for col in range(FLAG_COLS + 1):
                u, v = col / FLAG_COLS, r / FLAG_ROWS
                # the cloth sags a little towards its free end
                vert = bm.verts.new((u * FLAG_W * 0.97, 0, -v * FLAG_H - 0.035 * u ** 2))
                where[vert] = (u, 1 - v)
                row.append(vert)
            grid.append(row)
        for r in range(FLAG_ROWS):
            for col in range(FLAG_COLS):
                face = bm.faces.new((grid[r][col], grid[r + 1][col], grid[r + 1][col + 1], grid[r][col + 1]))
                for loop in face.loops:
                    loop[uv].uv = where[loop.vert]

    mesh = bpy.data.meshes.new('Flag')
    bm = bmesh.new()
    build(bm)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(flag_material())
    for poly in mesh.polygons:
        poly.use_smooth = True
    obj = bpy.data.objects.new('Flag', mesh)
    obj.location = top_left
    collection().objects.link(obj)
    return obj


def wave_flag(flag):
    """Wind as a travelling wave out of 4 morph targets: for each harmonic, sin and cos
    components weighted with cos(ωt) and -sin(ωt) give a(u)·sin(k·u - ωt) exactly."""
    harmonics = (  # amplitude, waves along the flag, cycles per Idle loop
        (0.08, 1.25, 2),
        (0.025, 2.6, 3),
    )
    flag.shape_key_add(name='Basis')
    base = [Vector(v.co) for v in flag.data.vertices]
    targets = []
    for n, (amplitude, waves, cycles) in enumerate(harmonics):
        for part in ('Sin', 'Cos'):
            key = flag.shape_key_add(name=f'Wave{n}{part}')
            key.slider_min = -1.0
            for i, co in enumerate(base):
                u = co.x / FLAG_W
                v = -co.z / FLAG_H
                phase = 2 * math.pi * waves * u + 1.1 * v * (n + 1)
                a = amplitude * u ** 1.15
                f = math.sin(phase) if part == 'Sin' else math.cos(phase)
                # sideways flutter plus a little pull towards the pole on the crests
                key.data[i].co = co + Vector((-0.12 * a * abs(f), a * f, 0.15 * a * f))
            targets.append((key, part, cycles))

    for key, part, cycles in targets:
        frames = {}
        for f in range(IDLE_END + 1):
            angle = 2 * math.pi * cycles * f / IDLE_END
            frames[f] = math.cos(angle) if part == 'Sin' else -math.sin(angle)
        keys(key, 'value', frames, 'LINEAR')
    to_track(flag.data.shape_keys, 'Idle')


# --------------------------------------------------------------------------- bake + export

def setup_cycles():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 16
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'METAL'
        prefs.get_devices()
        for device in prefs.devices:
            device.use = True
        scene.cycles.device = 'GPU'
    except Exception as error:  # noqa: BLE001 – CPU is fast enough for these few textures
        print('baking on CPU:', error)


def bake_camo(size=1024):
    """Bakes the procedural camouflage of every Camo_* material into an image texture."""
    setup_cycles()
    view_layer = bpy.context.view_layer
    for obj in [o for o in collection().objects if o.type == 'MESH' and o.data.materials and o.data.materials[0].name.startswith('Camo_')]:
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

        name = f'{mat.name}_Color'
        image = bpy.data.images.get(name) or bpy.data.images.new(name, size, size)
        nt = mat.node_tree
        # bake the camouflage colour as emission (no lighting)
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

        # final material: the baked texture; the procedural nodes stay for a rebake
        nt.nodes.remove(emit)
        nt.links.new(target.outputs['Color'], bsdf.inputs['Base Color'])
        nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        print('baked', obj.name, flush=True)


def export_glb(path=OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in collection().objects:
        obj.select_set(True)
    bpy.context.scene.frame_set(BUILD_END)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_apply=True,
        export_lights=False,
        export_cameras=False,
        export_extras=True,  # custom properties, e.g. a unit's walkSpeed
        export_animations=True,
        # one clip per NLA track name; mode NLA_TRACKS samples the shape keys of the flag
        # as constant, ACTIONS merged by track gets them right
        export_animation_mode='ACTIONS',
        export_merge_animation='NLA_TRACK',
        export_force_sampling=True,
        # the optimiser drops the flag's morph weights down to their first and last key
        export_optimize_animation_size=False,
        export_morph=True,
        export_morph_normal=True,  # the folds catch the light as they travel
        export_morph_animation=True,
        export_image_format='WEBP',
    )
    return {'path': path, 'bytes': os.path.getsize(path)}


# --------------------------------------------------------------------------- preview

def render_preview(frames, out_dir, size=480):
    """Renders frames through the game's camera (orthographic, 30° down, from the front right)."""
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = size
    scene.render.resolution_y = int(size * 0.75)
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new('World')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.35, 0.37, 0.42, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.8

    if 'PreviewGround' not in bpy.data.objects:
        bpy.ops.mesh.primitive_plane_add(size=12)
        ground = bpy.context.active_object
        ground.name = 'PreviewGround'
        ground.data.materials.append(material('PreviewGround', srgb('#6b5434'), 1.0))
        sun_data = bpy.data.lights.new('PreviewSun', 'SUN')
        sun_data.energy = 4.0
        sun_data.angle = math.radians(3)
        sun = bpy.data.objects.new('PreviewSun', sun_data)
        scene.collection.objects.link(sun)
        sun.rotation_euler = Vector((-6, 2, 9)).to_track_quat('Z', 'Y').to_euler()
        cam_data = bpy.data.cameras.new('PreviewCamera')
        cam_data.type = 'ORTHO'
        cam_data.ortho_scale = 2.9
        cam = bpy.data.objects.new('PreviewCamera', cam_data)
        scene.collection.objects.link(cam)
        direction = Vector((math.sin(math.radians(45)) * math.cos(math.radians(30)),
                            -math.cos(math.radians(45)) * math.cos(math.radians(30)),
                            math.sin(math.radians(30))))
        target = Vector((0.1, 0, 0.35))
        cam.location = target + direction * 10
        cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()
        scene.camera = cam
    os.makedirs(out_dir, exist_ok=True)
    for frame in frames:
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(out_dir, f'frame_{frame:03d}.png')
        bpy.ops.render.render(write_still=True)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    bake_camo()
    bpy.context.scene.frame_set(BUILD_END)
    print('export', export_glb(), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        render_preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2])


if __name__ == '__main__' and bpy.app.background:
    main()
