"""
Tiberian Fallout – startup animation before the main menu.

Builds the mechanical shaft scene (models, procedural grime shaders and the
6 second animation), bakes the shaders to textures and exports a GLB for
Three.js.

Run inside Blender (Scripting tab or via the MCP server):

    ns = {}
    exec(compile(open(PATH).read(), PATH, 'exec'), ns)
    ns['build']()          # models, materials, animation
    ns['bake_all']()       # bake procedural shaders into images
    ns['export_glb']()     # writes public/models/startup-menu.glb

Units: 1 = shaft radius / 1.25. Z is up, the plate lies in the XY plane and
the camera looks down -Z, exactly like the Three.js scene.
"""
import math
import os

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if '__file__' in globals() else ''
FPS = 30
END_FRAME = 180  # 6 s
SHAFT_R = 1.25
COLLECTION = 'StartupMenu'

# Timeline in seconds (must match app/lib/menu/startup-scene.ts)
T_CAMERA = (0.0, 3.4)
T_OUTER = (0.0, 2.2)
T_SEG = (0.15, 2.45)
T_RIB = (0.3, 2.7)
T_PLATE = (0.8, 3.2)


# --------------------------------------------------------------------------- helpers

def clamp01(x):
    return max(0.0, min(1.0, x))


def progress(window, t):
    a, b = window
    return clamp01((t - a) / (b - a))


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def lerp(a, b, t):
    return a + (b - a) * t


def collection():
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(col)
    return col


def new_object(name, mesh):
    obj = bpy.data.objects.new(name, mesh)
    collection().objects.link(obj)
    return obj


def lathe(name, profile, segments=192, z_fn=None, r_fn=None, uv='cyl', planar_scale=1.0, smooth=True):
    """Revolves a (radius, z) profile around Z.

    z_fn(theta, i, r) / r_fn(theta, i, r) return offsets for profile point i,
    which is used for ribs, notches and recesses.
    """
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new('UVMap')
    rows = []
    poles = {}  # profile points on the axis share one vertex
    for s in range(segments):
        theta = 2 * math.pi * s / segments
        row = []
        for i, (r, z) in enumerate(profile):
            if r == 0:
                if i not in poles:
                    poles[i] = bm.verts.new((0, 0, z + (z_fn(0, i, 0) if z_fn else 0.0)))
                row.append(poles[i])
                continue
            rr = r + (r_fn(theta, i, r) if r_fn else 0.0)
            zz = z + (z_fn(theta, i, r) if z_fn else 0.0)
            row.append(bm.verts.new((rr * math.cos(theta), rr * math.sin(theta), zz)))
        rows.append(row)

    # cumulative profile length for cylindrical v
    lengths = [0.0]
    for i in range(1, len(profile)):
        (r0, z0), (r1, z1) = profile[i - 1], profile[i]
        lengths.append(lengths[-1] + math.hypot(r1 - r0, z1 - z0))
    total = lengths[-1] or 1.0

    for s in range(segments):
        s1 = (s + 1) % segments
        for i in range(len(profile) - 1):
            corners = [((s, i), rows[s][i]), ((s + 1, i), rows[s1][i]), ((s + 1, i + 1), rows[s1][i + 1]), ((s, i + 1), rows[s][i + 1])]
            unique = []
            for key, vert in corners:
                if all(vert is not other for _, other in unique):
                    unique.append((key, vert))
            if len(unique) < 3:
                continue
            try:
                face = bm.faces.new([v for _, v in unique])
            except ValueError:
                continue
            face.smooth = smooth
            for loop, ((ss, ii), _) in zip(face.loops, unique):
                if uv == 'cyl':
                    loop[uv_layer].uv = (ss / segments, lengths[ii] / total)
                else:
                    co = loop.vert.co
                    loop[uv_layer].uv = (co.x / planar_scale * 0.5 + 0.5, co.y / planar_scale * 0.5 + 0.5)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.normal_update()
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = new_object(name, mesh)
    return obj


def bar(name, start, end, radius=0.012):
    """Thin iron rod between two points."""
    start, end = Vector(start), Vector(end)
    direction = end - start
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=radius, radius2=radius, depth=direction.length)
    bm.to_mesh(mesh)
    bm.free()
    obj = new_object(name, mesh)
    obj.location = (start + end) / 2
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(direction.normalized())
    for p in mesh.polygons:
        p.use_smooth = True
    return obj


def flat_bar(name, start, end, height=0.045, thickness=0.011):
    """Flat iron strip standing on edge between two points (height along Z)."""
    start, end = Vector(start), Vector(end)
    direction = end - start
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(direction.length + thickness, thickness, height), verts=bm.verts)
    bm.to_mesh(mesh)
    bm.free()
    obj = new_object(name, mesh)
    obj.location = (start + end) / 2
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = (0, 0, math.atan2(direction.y, direction.x))
    return obj


def clamp_band(name, at, axis, radius=0.012):
    """Short sleeve around a cross rod that holds a strip hanging below it."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=radius + 0.006, radius2=radius + 0.006, depth=0.03)
    bm.to_mesh(mesh)
    bm.free()
    obj = new_object(name, mesh)
    obj.location = at
    obj.rotation_euler = (0, math.pi / 2, 0) if axis == 'x' else (math.pi / 2, 0, 0)
    return obj


def smart_uv(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')


def join(objects, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    return obj


# --------------------------------------------------------------------------- materials

def socket(node, name, kind=None, output=False):
    sockets = node.outputs if output else node.inputs
    for s in sockets:
        if s.name == name and (kind is None or s.type == kind) and s.enabled:
            return s
    for s in sockets:
        if s.name == name and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


class Graph:
    def __init__(self, material):
        material.use_nodes = True
        self.nt = material.node_tree
        self.nt.nodes.clear()
        self.out = self.node('ShaderNodeOutputMaterial', (800, 0))
        self.bsdf = self.node('ShaderNodeBsdfPrincipled', (500, 0))
        self.link(self.bsdf.outputs['BSDF'], self.out.inputs['Surface'])
        coords = self.node('ShaderNodeTexCoord', (-1200, 0))
        self.obj = coords.outputs['Object']

    def node(self, kind, location=(0, 0), **props):
        n = self.nt.nodes.new(kind)
        n.location = location
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def noise(self, scale, detail=6.0, roughness=0.6, distortion=0.0, vector=None, loc=(-900, 0)):
        n = self.node('ShaderNodeTexNoise', loc)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = roughness
        n.inputs['Distortion'].default_value = distortion
        self.link(vector or self.obj, n.inputs['Vector'])
        return n.outputs['Fac']

    def voronoi(self, scale, feature='F1', loc=(-900, -300)):
        n = self.node('ShaderNodeTexVoronoi', loc, feature=feature)
        n.inputs['Scale'].default_value = scale
        self.link(self.obj, n.inputs['Vector'])
        return n.outputs['Distance']

    def ramp(self, value, stops, loc=(-600, 0)):
        n = self.node('ShaderNodeValToRGB', loc)
        els = n.color_ramp.elements
        while len(els) > 1:
            els.remove(els[-1])
        els[0].position, els[0].color = stops[0][0], (*stops[0][1], 1)
        for pos, col in stops[1:]:
            e = els.new(pos)
            e.color = (*col, 1)
        self.link(value, n.inputs['Fac'])
        return n.outputs['Color']

    def mix(self, fac, a, b, blend='MIX', loc=(-300, 0)):
        n = self.node('ShaderNodeMix', loc, data_type='RGBA', blend_type=blend)
        for value, target in ((fac, socket(n, 'Factor', 'VALUE')), (a, socket(n, 'A', 'RGBA')), (b, socket(n, 'B', 'RGBA'))):
            if isinstance(value, (int, float)):
                target.default_value = value
            elif isinstance(value, tuple):
                target.default_value = (*value, 1) if len(value) == 3 else value
            else:
                self.link(value, target)
        return socket(n, 'Result', 'RGBA', output=True)

    def math(self, op, a, b=0.0, loc=(-300, -400), clamp=True):
        n = self.node('ShaderNodeMath', loc, operation=op, use_clamp=clamp)
        for value, target in ((a, n.inputs[0]), (b, n.inputs[1])):
            if isinstance(value, (int, float)):
                target.default_value = value
            else:
                self.link(value, target)
        return n.outputs[0]

    def stretched(self, scale, rotation=(0.0, 0.0, 0.0), loc=(-1100, -700)):
        """Anisotropically scaled object coordinates, for scratches and streaks."""
        n = self.node('ShaderNodeMapping', loc)
        n.inputs['Scale'].default_value = scale
        n.inputs['Rotation'].default_value = rotation
        self.link(self.obj, n.inputs['Vector'])
        return n.outputs['Vector']

    def edges(self, radius=0.006, loc=(-1100, 500)):
        """1 on sharp convex/concave edges, 0 on flat areas (Cycles bevel trick)."""
        bevel = self.node('ShaderNodeBevel', loc, samples=8)
        bevel.inputs['Radius'].default_value = radius
        geo = self.node('ShaderNodeNewGeometry', (loc[0], loc[1] - 200))
        dot = self.node('ShaderNodeVectorMath', (loc[0] + 200, loc[1]), operation='DOT_PRODUCT')
        self.link(bevel.outputs['Normal'], dot.inputs[0])
        self.link(geo.outputs['Normal'], dot.inputs[1])
        edge = self.math('SUBTRACT', 1.0, socket(dot, 'Value', output=True), loc=(loc[0] + 400, loc[1]))
        return self.math('MULTIPLY', edge, 25.0, loc=(loc[0] + 600, loc[1]))

    def lines(self, vector, scale, width=0.012, loc=(-900, -700)):
        """Thin random lines from stretched noise (scratches)."""
        n = self.node('ShaderNodeTexNoise', loc)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = 3.0
        n.inputs['Roughness'].default_value = 0.5
        self.link(vector, n.inputs['Vector'])
        dist = self.math('ABSOLUTE', self.math('SUBTRACT', n.outputs['Fac'], 0.5, loc=(loc[0] + 200, loc[1]), clamp=False), loc=(loc[0] + 350, loc[1]))
        return self.math('LESS_THAN', dist, width, loc=(loc[0] + 500, loc[1]))

    def value(self, color_socket, loc=(0, -900)):
        n = self.node('ShaderNodeRGBToBW', loc)
        self.link(color_socket, n.inputs['Color'])
        return n.outputs['Val']

    def ao(self, distance=0.15, loc=(-900, 300)):
        n = self.node('ShaderNodeAmbientOcclusion', loc, samples=16)
        n.inputs['Distance'].default_value = distance
        return n.outputs['AO']

    def bump(self, height, strength, distance=0.02):
        n = self.node('ShaderNodeBump', (250, -400))
        n.inputs['Strength'].default_value = strength
        n.inputs['Distance'].default_value = distance
        self.link(height, n.inputs['Height'])
        self.link(n.outputs['Normal'], self.bsdf.inputs['Normal'])


def material_brass(name, tint=(0.46, 0.31, 0.1), grime_amount=0.55, bump=0.25):
    """Old, tarnished brass.

    Layers: colour variation, tarnish, cavity grime with verdigris, polished
    edges, directional scratches, fine grain, hammer dents and pitting.
    """
    mat = bpy.data.materials.new(name)
    g = Graph(mat)
    dark = tuple(c * 0.55 for c in tint)
    bright = tuple(min(1.0, c * 1.7) for c in tint)

    variation = g.noise(18, detail=4, roughness=0.5, loc=(-900, 600))
    tarnish_n = g.noise(4, detail=12, roughness=0.62, loc=(-900, 400))
    verd_n = g.noise(28, detail=6, roughness=0.6, loc=(-900, 200))
    grain = g.noise(380, detail=2, roughness=0.5, loc=(-900, 0))
    dents = g.voronoi(9, feature='SMOOTH_F1', loc=(-900, -200))
    pits = g.voronoi(170, loc=(-900, -400))
    # Stretching the noise along one axis turns its contour lines into short straight scratches
    scratch_a = g.lines(g.stretched((1.0, 30.0, 1.0), (0, 0, 0.6), loc=(-1300, -700)), 22, 0.006, loc=(-900, -700))
    scratch_b = g.lines(g.stretched((1.0, 45.0, 1.0), (0, 0, 2.1), loc=(-1300, -900)), 35, 0.004, loc=(-900, -900))
    scratches = g.math('MAXIMUM', scratch_a, scratch_b, loc=(-300, -800))
    edge = g.edges()
    ao = g.ao(0.1)

    tarnish = g.value(g.ramp(tarnish_n, [(0.38, (0, 0, 0)), (0.72, (1, 1, 1))], loc=(-600, 400)), loc=(-400, 400))
    cavity = g.value(g.ramp(ao, [(0.45, (1, 1, 1)), (0.97, (0, 0, 0))], loc=(-600, 800)), loc=(-400, 800))
    verdigris = g.math('MULTIPLY', cavity, g.value(g.ramp(verd_n, [(0.5, (0, 0, 0)), (0.62, (1, 1, 1))], loc=(-600, 200)), loc=(-400, 200)), loc=(-200, 200))
    edge_wear = g.math('MULTIPLY', edge, g.value(g.ramp(grain, [(0.3, (0.3, 0.3, 0.3)), (0.6, (1, 1, 1))], loc=(-600, 0)), loc=(-400, 0)), loc=(-200, 0))

    color = g.mix(g.value(g.ramp(variation, [(0.35, (0, 0, 0)), (0.7, (1, 1, 1))], loc=(-600, 600)), loc=(-400, 600)), tint, dark, loc=(-100, 600))
    color = g.mix(g.math('MULTIPLY', tarnish, grime_amount, loc=(-200, 450)), color, (0.08, 0.055, 0.03), loc=(50, 550))
    color = g.mix(verdigris, color, (0.11, 0.2, 0.14), loc=(200, 500))
    color = g.mix(g.math('MULTIPLY', cavity, 0.85, loc=(-200, 700)), color, (0.015, 0.012, 0.008), loc=(350, 600))
    color = g.mix(g.math('MULTIPLY', edge_wear, 0.8, loc=(0, 0)), color, bright, loc=(500, 400))
    color = g.mix(g.math('MULTIPLY', scratches, 0.3, loc=(0, -800)), color, bright, loc=(650, 350))
    speck = g.ramp(grain, [(0.2, (0.82, 0.82, 0.82)), (0.8, (1.12, 1.12, 1.12))], loc=(-600, -100))
    color = g.mix(1.0, color, speck, blend='MULTIPLY', loc=(800, 300))
    g.bsdf.location = (1100, 0)
    g.out.location = (1400, 0)
    g.link(color, g.bsdf.inputs['Base Color'])

    rough = g.math('ADD', 0.38, g.math('MULTIPLY', tarnish, 0.35, loc=(200, -150)), loc=(350, -150))
    rough = g.math('ADD', rough, g.math('MULTIPLY', cavity, 0.3, loc=(200, -250)), loc=(500, -150))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', edge_wear, 0.2, loc=(200, -350)), loc=(650, -150))
    rough = g.math('ADD', rough, g.math('MULTIPLY', grain, 0.12, loc=(200, -450)), loc=(800, -150))
    g.link(rough, g.bsdf.inputs['Roughness'])
    metal = g.math('SUBTRACT', 1.0, g.math('ADD', g.math('MULTIPLY', cavity, 0.7, loc=(200, -550)), verdigris, loc=(350, -550)), loc=(500, -550))
    metal = g.math('SUBTRACT', metal, g.math('MULTIPLY', tarnish, 0.25, loc=(350, -650)), loc=(650, -550))
    g.link(metal, g.bsdf.inputs['Metallic'])

    height = g.math('MULTIPLY', dents, 0.5, loc=(200, -800), clamp=False)
    height = g.math('ADD', height, g.math('MULTIPLY', pits, 0.25, loc=(200, -900), clamp=False), loc=(350, -850), clamp=False)
    height = g.math('ADD', height, g.math('MULTIPLY', grain, 0.12, loc=(200, -1000), clamp=False), loc=(500, -850), clamp=False)
    height = g.math('SUBTRACT', height, g.math('MULTIPLY', scratches, 0.35, loc=(200, -1100), clamp=False), loc=(650, -850), clamp=False)
    bump_node = g.node('ShaderNodeBump', (900, -700))
    bump_node.inputs['Strength'].default_value = bump
    bump_node.inputs['Distance'].default_value = 0.003
    g.link(height, bump_node.inputs['Height'])
    g.link(bump_node.outputs['Normal'], g.bsdf.inputs['Normal'])
    return mat


def material_iron(name, base=(0.04, 0.035, 0.03), dust=(0.11, 0.1, 0.085), rust=(0.2, 0.085, 0.03)):
    """Dusty cast iron: rust patches with streaks, pitting, dents, fine grain and scratches."""
    mat = bpy.data.materials.new(name)
    g = Graph(mat)
    large = g.noise(1.4, detail=12, roughness=0.62, loc=(-900, 600))
    rust_n = g.noise(5.5, detail=12, roughness=0.6, distortion=1.2, loc=(-900, 400))
    rust_tone = g.noise(40, detail=4, roughness=0.6, loc=(-900, 200))
    streak = g.noise(6, detail=4, roughness=0.5, vector=g.stretched((1.0, 0.08, 1.0), loc=(-1300, 0)), loc=(-900, 0))
    grain = g.noise(450, detail=2, roughness=0.5, loc=(-900, -200))
    pits = g.voronoi(48, loc=(-900, -400))
    dents = g.voronoi(7, feature='SMOOTH_F1', loc=(-900, -550))
    scratches = g.lines(g.stretched((1.0, 35.0, 1.0), (0, 0, 0.9), loc=(-1300, -700)), 8, 0.004, loc=(-900, -700))
    ao = g.ao(0.3)

    dust_mask = g.value(g.ramp(large, [(0.45, (0, 0, 0)), (0.78, (0.5, 0.5, 0.5))], loc=(-600, 600)), loc=(-400, 600))
    cavity = g.value(g.ramp(ao, [(0.35, (1, 1, 1)), (0.95, (0, 0, 0))], loc=(-600, 800)), loc=(-400, 800))
    rust_mask = g.value(g.ramp(rust_n, [(0.6, (0, 0, 0)), (0.68, (0.85, 0.85, 0.85))], loc=(-600, 400)), loc=(-400, 400))
    streaks = g.value(g.ramp(streak, [(0.62, (0, 0, 0)), (0.72, (0.5, 0.5, 0.5))], loc=(-600, 0)), loc=(-400, 0))
    rust_all = g.math('MAXIMUM', rust_mask, g.math('MULTIPLY', streaks, 0.25, loc=(-200, 0)), loc=(-50, 300))
    pit_dots = g.value(g.ramp(pits, [(0.06, (1, 1, 1)), (0.12, (0, 0, 0))], loc=(-600, -400)), loc=(-400, -400))

    rust_color = g.mix(rust_tone, rust, (0.09, 0.04, 0.018), loc=(-200, 200))
    color = g.mix(dust_mask, base, dust, loc=(-100, 650))
    color = g.mix(g.math('MULTIPLY', cavity, 0.5, loc=(-200, 800)), color, (dust[0] * 0.8, dust[1] * 0.75, dust[2] * 0.7), loc=(50, 700))
    color = g.mix(rust_all, color, rust_color, loc=(200, 500))
    color = g.mix(g.math('MULTIPLY', pit_dots, 0.8, loc=(0, -400)), color, (0.01, 0.008, 0.006), loc=(350, 400))
    color = g.mix(g.math('MULTIPLY', scratches, 0.25, loc=(0, -700)), color, (0.24, 0.22, 0.2), loc=(500, 350))
    speck = g.ramp(grain, [(0.25, (0.75, 0.75, 0.75)), (0.8, (1.2, 1.2, 1.2))], loc=(-600, -200))
    color = g.mix(1.0, color, speck, blend='MULTIPLY', loc=(650, 300))
    g.bsdf.location = (1100, 0)
    g.out.location = (1400, 0)
    g.link(color, g.bsdf.inputs['Base Color'])

    rough = g.math('ADD', 0.72, g.math('MULTIPLY', rust_all, 0.25, loc=(300, -150)), loc=(450, -150))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', scratches, 0.3, loc=(300, -250)), loc=(600, -150))
    g.link(rough, g.bsdf.inputs['Roughness'])
    metal = g.math('MULTIPLY', g.math('SUBTRACT', 1.0, g.math('MAXIMUM', rust_all, dust_mask, loc=(300, -450)), loc=(450, -450)), 0.55, loc=(600, -450))
    g.link(metal, g.bsdf.inputs['Metallic'])

    height = g.math('MULTIPLY', rust_all, 0.35, loc=(300, -800), clamp=False)
    height = g.math('SUBTRACT', height, g.math('MULTIPLY', pit_dots, 0.5, loc=(300, -900), clamp=False), loc=(450, -850), clamp=False)
    height = g.math('ADD', height, g.math('MULTIPLY', dents, 0.4, loc=(300, -1000), clamp=False), loc=(600, -850), clamp=False)
    height = g.math('ADD', height, g.math('MULTIPLY', grain, 0.15, loc=(300, -1100), clamp=False), loc=(750, -850), clamp=False)
    bump_node = g.node('ShaderNodeBump', (900, -700))
    bump_node.inputs['Strength'].default_value = 0.4
    bump_node.inputs['Distance'].default_value = 0.006
    g.link(height, bump_node.inputs['Height'])
    g.link(bump_node.outputs['Normal'], g.bsdf.inputs['Normal'])
    return mat


def assign(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)


def procedural_materials(name):
    """Fresh procedural material(s) for an object (each object gets its own, for baking)."""
    brass = lambda: material_brass(f'TF_Brass_{name}')
    dark_brass = lambda: material_brass(f'TF_DarkBrass_{name}', tint=(0.27, 0.17, 0.06), grime_amount=0.75)
    pale_brass = lambda: material_brass(f'TF_PaleBrass_{name}', tint=(0.56, 0.42, 0.19), grime_amount=0.45)
    return {
        'Plate': lambda: [material_iron(f'TF_Iron_{name}')],
        'PlateOuter': lambda: [material_iron(f'TF_Iron_{name}')],
        'Shaft': lambda: [material_iron(f'TF_ShaftIron_{name}', base=(0.03, 0.025, 0.02), dust=(0.1, 0.085, 0.06))],
        'Bezel': lambda: [pale_brass()],
        'OuterRing': lambda: [brass()],
        'Knob': lambda: [brass()],
        'RibRing': lambda: [dark_brass()],
        # dark ring with one bright inset segment
        'SegRing': lambda: [dark_brass(), pale_brass()],
        'Rods': lambda: [material_brass(f'TF_Rod_{name}', tint=(0.52, 0.4, 0.2), grime_amount=0.3, bump=0.03)],
        # light brass face, dark recesses
        'CentrePlate': lambda: [pale_brass(), dark_brass()],
    }[name]()


def assign_procedural(obj):
    obj.data.materials.clear()
    for material in procedural_materials(obj.name):
        obj.data.materials.append(material)
    if obj.name == 'SegRing':
        for poly in obj.data.polygons:
            c = poly.center
            angle = math.degrees(math.atan2(c.y, c.x)) % 360
            poly.material_index = 1 if 33 < angle < 49 and c.z > -0.005 else 0
    if obj.name == 'CentrePlate':
        for poly in obj.data.polygons:
            c = poly.center
            poly.material_index = 1 if c.z < -0.015 and math.hypot(c.x, c.y) < 0.499 else 0


# --------------------------------------------------------------------------- models

def build_models():
    # Plate with the opening (annulus out to r = 12, planar UVs)
    # Inner part (what the camera sees) gets a high-res texture, the outer part a coarse one
    radii = [SHAFT_R + 0.11]
    while radii[-1] < 3.8:
        radii.append(min(3.8, radii[-1] * 1.08 + 0.02))
    plate_profile = [(SHAFT_R, -0.05)] + [(r, 0.0) for r in radii]
    plate = lathe('Plate', list(reversed(plate_profile)), segments=256, uv='planar', planar_scale=3.8)
    outer_radii = [3.8]
    while outer_radii[-1] < 12:
        outer_radii.append(outer_radii[-1] * 1.15)
    plate_outer = lathe('PlateOuter', [(r, 0.0) for r in reversed(outer_radii)], segments=128, uv='planar', planar_scale=12.0)

    # Ribbed shaft wall going down into darkness
    shaft_profile = [(SHAFT_R, -0.04 - 3.0 * i / 12) for i in range(13)]
    shaft = lathe('Shaft', shaft_profile, segments=384,
                  r_fn=lambda th, i, r: 0.025 if math.sin(th * 96) > 0.2 else 0.0)

    # Fixed bezel with notched outer edge
    bezel_profile = [(1.24, -0.14), (1.24, 0.02), (1.265, 0.06), (1.33, 0.075), (1.36, 0.05), (1.37, 0.0), (1.37, -0.01)]
    notch = lambda th, i, r: -0.025 if i in (4, 5) and math.sin(th * 160) > 0.55 else 0.0
    bezel = lathe('Bezel', bezel_profile, segments=640, z_fn=notch)

    # Outer moving ring with a groove, plus the domed button
    outer_profile = [(1.0, -0.2), (1.0, -0.02), (1.02, 0.0), (1.035, 0.0), (1.035, -0.015), (1.06, -0.015), (1.06, 0.0),
                     (1.16, 0.0), (1.19, -0.025), (1.19, -0.2)]
    outer = lathe('OuterRing', outer_profile, segments=256)
    knob_profile = [(0.0, 0.07), (0.05, 0.068), (0.1, 0.055), (0.13, 0.035), (0.15, 0.012), (0.155, 0.0), (0.18, 0.0),
                    (0.185, -0.015), (0.185, -0.03)]
    knob = lathe('Knob', knob_profile, segments=96)
    angle = math.radians(215)
    knob.location = (math.cos(angle) * 1.075, math.sin(angle) * 1.075, 0.0)
    knob.parent = outer

    # Second level: plain dark ring with a fine groove near its inner edge
    seg_profile = [(0.8, -0.18), (0.8, -0.015), (0.815, 0.0), (0.83, 0.0), (0.83, -0.01), (0.845, -0.01), (0.845, 0.0),
                   (0.985, 0.0), (1.0, -0.015), (1.0, -0.18)]
    seg_ring = lathe('SegRing', seg_profile, segments=384)

    # Third level: ring with radial ribs on its face
    rib_profile = [(0.5, -0.16), (0.5, -0.012), (0.515, 0.0), (0.785, 0.0), (0.8, -0.015), (0.8, -0.16)]
    ribs = lambda th, i, r: -0.014 if i in (2, 3) and math.sin(th * 96) > 0.35 else 0.0
    rib_ring = lathe('RibRing', rib_profile, segments=768, z_fn=ribs)

    # Centre plate: two crescent recesses and a raised boss
    bites = [(0.475, 0.475), (-0.475, -0.475)]

    def plate_z(th, i, r):
        if r > 0.5:
            return 0.0
        x, y = r * math.cos(th), r * math.sin(th)
        if 0.055 < r < 0.09:
            return 0.012
        for bx, by in bites:
            if math.hypot(x - bx, y - by) < 0.475:
                return -0.03
        return 0.0
    centre_profile = [(0.5 * k / 120, 0.0) for k in range(121)] + [(0.5, -0.012), (0.5, -0.1)]
    centre = lathe('CentrePlate', centre_profile, segments=512, z_fn=plate_z, uv='planar', planar_scale=0.5)

    # Iron rods: the cross exactly above the shaft centre. The thin flat strips
    # hang directly below it (their top edge touches the rods) and are held by sleeves.
    cross_z, cross_r = 0.2, 0.012
    strip_h = 0.045
    z = cross_z - cross_r - strip_h / 2  # strip top edge = underside of the cross
    z2 = z - 0.05                        # second, slightly lower frame
    rods = [
        bar('Rod_H', (-8, 0, cross_z), (8, 0, cross_z), cross_r),
        bar('Rod_V', (0, -6, cross_z), (0, 6, cross_z), cross_r),
        # frame in the lower right quadrant, its top edge under the horizontal rod
        flat_bar('Strip_Top', (0.18, 0, z), (0.77, 0, z)),
        flat_bar('Strip_Left', (0.18, 0, z), (0.18, -0.75, z)),
        flat_bar('Strip_Right', (0.77, 0, z), (0.77, -0.75, z)),
        flat_bar('Strip_Bottom', (0.18, -0.75, z), (0.77, -0.75, z)),
        # inner frame, one level lower, hung from the outer one
        flat_bar('Strip_InnerTop', (0.18, -0.09, z2), (0.69, -0.09, z2), 0.035, 0.009),
        flat_bar('Strip_InnerRight', (0.69, -0.09, z2), (0.69, -0.75, z2), 0.035, 0.009),
        flat_bar('Hanger_A', (0.18, -0.09, (z + z2) / 2), (0.18, -0.09, (z + z2) / 2), 0.05 + strip_h, 0.009),
        flat_bar('Hanger_B', (0.69, -0.75, (z + z2) / 2), (0.69, -0.75, (z + z2) / 2), 0.05 + strip_h, 0.009),
        # long strip up to the far rim, held by a cross strip under the vertical rod
        flat_bar('Strip_Long', (0.24, 0.97, z), (0.24, -0.75, z)),
        flat_bar('Strip_Upper', (-0.14, 0.97, z), (0.24, 0.97, z)),
        flat_bar('Strip_Short', (-0.14, 0.97, z), (-0.14, 1.2, z)),
        # sleeves where strips meet the cross
        clamp_band('Clamp_1', (0.18, 0, cross_z), 'x', cross_r),
        clamp_band('Clamp_2', (0.24, 0, cross_z), 'x', cross_r),
        clamp_band('Clamp_3', (0.77, 0, cross_z), 'x', cross_r),
        clamp_band('Clamp_4', (0, 0.97, cross_z), 'y', cross_r),
    ]
    rods = join(rods, 'Rods')
    smart_uv(rods)

    for obj in (plate, plate_outer, shaft, bezel, outer, knob, seg_ring, rib_ring, centre, rods):
        assign_procedural(obj)

    # Hard edges stay sharp, curved surfaces stay smooth
    for obj in (plate, plate_outer, shaft, bezel, outer, knob, seg_ring, rib_ring, centre, rods):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_auto_smooth(angle=math.radians(35))

    return {'outer': outer, 'seg': seg_ring, 'rib': rib_ring, 'centre': centre}


# --------------------------------------------------------------------------- camera, lights, animation

def look_at(obj, target, up=(0.0, 1.0, 0.0)):
    """Points -Z at the target with a fixed screen-up direction.

    The scene is viewed from above, so world +Y is "up" on screen. Using
    to_track_quat() here would leave the roll undefined when looking
    straight down and make the camera twist.
    """
    forward = (Vector(target) - obj.location).normalized()
    right = forward.cross(Vector(up)).normalized()
    cam_up = right.cross(forward)
    rot = Matrix((right, cam_up, -forward)).transposed()
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rot.to_quaternion()


def build_camera_and_lights():
    cam_data = bpy.data.cameras.new('MenuCamera')
    cam_data.sensor_fit = 'VERTICAL'
    cam_data.lens_unit = 'FOV'
    cam_data.angle = math.radians(38)
    cam_data.clip_start = 0.05
    cam_data.clip_end = 50
    cam = new_object('MenuCamera', cam_data)
    bpy.context.scene.camera = cam

    key = bpy.data.lights.new('Key', 'SPOT')
    key.energy = 900
    key.spot_size = math.radians(80)
    key.spot_blend = 0.9
    key.color = (1.0, 0.94, 0.82)
    key_obj = new_object('Key', key)
    key_obj.location = (-1.2, 1.6, 5.2)
    look_at(key_obj, (0, 0, 0))
    return cam


def animate(cam, parts):
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 0
    scene.frame_end = END_FRAME

    for frame in range(0, END_FRAME + 1):
        t = frame / FPS
        c = ease_in_out(progress(T_CAMERA, t))
        cam.location = (lerp(-0.15, 0, c), lerp(-2.5, 0, c), lerp(2.3, 3.95, c))
        look_at(cam, (lerp(0.08, 0, c), lerp(-0.1, 0, c), lerp(-0.3, 0, c)))
        cam.keyframe_insert('location', frame=frame)
        cam.keyframe_insert('rotation_quaternion', frame=frame)

        for key, window, depth, twist in (('outer', T_OUTER, 0.45, 0.5), ('seg', T_SEG, 0.9, -0.7), ('rib', T_RIB, 1.5, 0.9), ('centre', T_PLATE, 2.5, -1.4)):
            obj = parts[key]
            p = ease_out(progress(window, t))
            obj.location = (0, 0, -depth * (1 - p))
            obj.rotation_euler = (0, 0, twist * (1 - p))
            obj.keyframe_insert('location', frame=frame)
            obj.keyframe_insert('rotation_euler', frame=frame)

    for obj in [cam] + list(parts.values()):
        action = obj.animation_data.action
        for fcurve in getattr(action, 'fcurves', []):
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'LINEAR'


def setup_render():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 800
    world = scene.world or bpy.data.worlds.new('World')
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs['Color'].default_value = (0, 0, 0, 1)
        bg.inputs['Strength'].default_value = 0.0


def clear():
    col = bpy.data.collections.get(COLLECTION)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    for mat in list(bpy.data.materials):
        if mat.name.startswith('TF_') or mat.name.endswith('_Baked'):
            mat.use_fake_user = False
            bpy.data.materials.remove(mat)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.images, bpy.data.actions):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def build():
    clear()
    setup_render()
    parts = build_models()
    cam = build_camera_and_lights()
    animate(cam, parts)
    bpy.context.scene.frame_set(END_FRAME)
    return {'objects': [o.name for o in collection().objects]}


# --------------------------------------------------------------------------- baking

BAKE_SIZES = {
    'Plate': (4096, 4096),
    'PlateOuter': (1024, 1024),
    'Shaft': (4096, 1024),
    'Bezel': (4096, 512),
    'OuterRing': (4096, 1024),
    'Knob': (1024, 512),
    'SegRing': (4096, 512),
    'RibRing': (4096, 1024),
    'CentrePlate': (2048, 2048),
    'Rods': (2048, 2048),
}


def _bake(obj, kind, image, **kwargs):
    for mat in obj.data.materials:
        nt = mat.node_tree
        node = nt.nodes.get('BakeTarget') or nt.nodes.new('ShaderNodeTexImage')
        node.name = 'BakeTarget'
        node.image = image
        node.location = (800, 300)
        nt.nodes.active = node
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type=kind, margin=8, **kwargs)


def _with_emission_from(obj, input_name, fn):
    """Bakes a Principled input (e.g. Metallic) by routing it to the output as emission."""
    saved = []
    for mat in obj.data.materials:
        nt = mat.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        emit = nt.nodes.new('ShaderNodeEmission')
        src = bsdf.inputs[input_name]
        if src.links:
            nt.links.new(src.links[0].from_socket, emit.inputs['Color'])
        else:
            v = src.default_value
            emit.inputs['Color'].default_value = (v, v, v, 1)
        old = out.inputs['Surface'].links[0].from_socket
        nt.links.new(emit.outputs['Emission'], out.inputs['Surface'])
        saved.append((nt, out, old, emit))
    try:
        fn()
    finally:
        for nt, out, old, emit in saved:
            nt.links.new(old, out.inputs['Surface'])
            nt.nodes.remove(emit)


def bake_object(name):
    obj = bpy.data.objects[name]
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.render.bake.use_selected_to_active = False
    # Bake in the final (resting) pose so AO matches the assembled machine
    scene.frame_set(END_FRAME)
    w, h = BAKE_SIZES[name]
    images = {}
    for channel, non_color in (('color', False), ('roughness', True), ('metallic', True), ('normal', True)):
        img_name = f'{name}_{channel}'
        old = bpy.data.images.get(img_name)
        if old:
            bpy.data.images.remove(old)
        img = bpy.data.images.new(img_name, w, h, alpha=False, float_buffer=False)
        if non_color:
            img.colorspace_settings.name = 'Non-Color'
        images[channel] = img

    _bake(obj, 'DIFFUSE', images['color'], pass_filter={'COLOR'})
    _bake(obj, 'ROUGHNESS', images['roughness'])
    _with_emission_from(obj, 'Metallic', lambda: _bake(obj, 'EMIT', images['metallic']))
    _bake(obj, 'NORMAL', images['normal'], normal_space='TANGENT')
    for img in images.values():
        img.pack()
    return images


def apply_baked(name, images):
    """Replaces the procedural materials by simple image based ones for glTF."""
    obj = bpy.data.objects[name]
    procedural = list(obj.data.materials)
    mat = bpy.data.materials.new(f'{name}_Baked')
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')

    def tex(img, loc):
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = img
        n.location = loc
        return n

    nt.links.new(tex(images['color'], (-600, 300)).outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(tex(images['roughness'], (-600, 0)).outputs['Color'], bsdf.inputs['Roughness'])
    nt.links.new(tex(images['metallic'], (-600, -250)).outputs['Color'], bsdf.inputs['Metallic'])
    normal_map = nt.nodes.new('ShaderNodeNormalMap')
    normal_map.location = (-250, -500)
    nt.links.new(tex(images['normal'], (-600, -500)).outputs['Color'], normal_map.inputs['Color'])
    nt.links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])

    # procedural sources can be recreated with rebake()
    obj.data.materials.clear()
    for m in procedural:
        if m.users == 0:
            bpy.data.materials.remove(m)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.material_index = 0


def rebake(names):
    """Rebuilds the procedural materials of some objects and bakes only those."""
    for name in names:
        obj = bpy.data.objects[name]
        old = list(obj.data.materials)
        assign_procedural(obj)
        for material in old:
            if material and material.users == 0:
                bpy.data.materials.remove(material)
        images = bake_object(name)
        apply_baked(name, images)
    return names


def bake_all(names=None):
    done = []
    for name in names or BAKE_SIZES:
        images = bake_object(name)
        apply_baked(name, images)
        done.append(name)
    return done


# --------------------------------------------------------------------------- export

def export_glb(path=None):
    path = path or os.path.join(PROJECT, 'public', 'models', 'startup-menu.glb')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in collection().objects:
        if obj.type in {'MESH', 'CAMERA'}:
            obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        use_selection=True,
        export_cameras=True,
        export_lights=False,
        export_animations=True,
        export_force_sampling=True,
        export_frame_range=True,
        export_image_format='WEBP',
        export_apply=True,
    )
    return {'path': path, 'bytes': os.path.getsize(path)}
