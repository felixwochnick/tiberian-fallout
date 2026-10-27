"""
Tiberian Fallout – shared parts of the Nod buildings: NAPOWR, NAHAND, NAWEAP, NARADR,
NATECH, the defences NALASR, NASAM, NAPULS, the helipad NAHPAD, NAWALL and NAGATE_A.

Nod builds in dark concrete and dark armour plate with sharp edges; the house colour
(red for Nod) only on accents: trims, spikes, frames, stripes.
    Nod_*        concrete: a procedural shader (mottling, streaks, speckles, darker in
                 the corners) baked to a texture per object; extra nodColour white (the
                 texture carries the colour)
    NodPlate*,   dark armour plate and steel, plain colours; extra nodColour = its own
    NodSteel,    colour (applyHouseColour in app/lib/game/models.ts)
    NodArmour*
    Remap        the house colour
    Lamp*, Glow* emissive bulbs and additive halos as in the other models

Gun towers have the nodes the game aims (see Combat in app/lib/game/combat.ts):
    Turret   turns about the vertical towards the target (never keyed by a clip)
    Cannon   inside the turret, tipped up and down (never keyed); its barrel looks
             along -Y (glTF +Z)
    Flash…   the muzzle: the game reads its position when a shot leaves, before the
             Fire clip moves anything – so it sits where the shot starts at rest
The building animations hang on nodes above or below them.

The clips of a building play at the same time in the game (Build holds its last frame,
Idle loops over it, Fire/Open run once in between), and three.js averages a channel
that two of them drive. So every node + property belongs to one clip only (checked by
test/models.test.ts): a lamp that pops in during Build and blinks in Idle is two nodes,
a housing (Build) and its light (Idle). Fire/Open must end in the rest pose.
Nothing animated in Idle/Fire/Open may hang under a parent that Build scales to ~0
(kit.pop, show_at, grow_z): the glTF exporter then writes wrong translation keys into
those clips and the part hops. Let such parents rise/slide in, or hang the part beside
them. Check: node <scratchpad>/na/idlecheck.mjs public/models/<ID>.glb [Idle|Fire|Open].

Also here: polygon prisms with sloped walls, lofted shells, lathes, spikes, hazard
stripes, pulsing glows, the previews and the build/bake/export main().

Units: 1 = one map cell. Blender Z is up; -Y is the front (glTF +Z). The origin is in
the middle of the foundation on the ground. In the game -Y (the front) faces the lower
left of the screen, +X the lower right – the two sides the original's sprite shows.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script
import nodvehicle as vehicle  # noqa: E402 – the Nod armour materials

PROJECT = os.path.dirname(HERE)
HIDDEN = kit.HIDDEN
NOD_RED = '#c42a1c'   # the house colour of the previews (the game paints Remap itself)

box, cylinder, sphere, beam, srgb, material = kit.box, kit.cylinder, kit.sphere, kit.beam, kit.srgb, kit.material

# key: (material name, colour); every one gets the extra nodColour
DARK = {
    'nplate': ('NodPlate', '#3c3d42'),
    'nplate_dark': ('NodPlateDark', '#232428'),
    'nsteel': ('NodSteel', '#64676d'),
    'nsteel_light': ('NodSteelLight', '#a3a6aa'),
    'dirt': ('NodDirt', '#7a6744'),
}
# concrete tones (concrete() takes one of these or any hex colour)
GREY = '#7b7c7e'
LIGHT = '#9a9893'
DARK_GREY = '#4b4c4f'
CONCRETE = {
    'dark': DARK_GREY,    # the towers' footings and bodies
    'olive': '#5f6158',   # the EMP cannon's greenish grey base
    'grey': GREY,         # walls and gate
    'light': LIGHT,
}


def dark_material(name, hex_colour, roughness=0.6, metallic=0.4):
    mat = kit.material(name, kit.srgb(hex_colour), roughness, metallic)
    mat['nodColour'] = hex_colour
    return mat


def materials():
    m = vehicle.materials()
    m['remap'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (*srgb(NOD_RED), 1)
    for key, colour in (('armour', '#45474c'), ('armour_dark', '#26272b')):
        m[key]['nodColour'] = colour
    for key, (name, colour) in DARK.items():
        m[key] = dark_material(name, colour, 0.95 if key == 'dirt' else 0.6, 0.0 if key == 'dirt' else 0.45)
    m['dark']['nodColour'] = '#17181a'
    m['steel']['nodColour'] = '#4a4d50'   # the lamp housings
    m['glow_red'] = material('GlowRed', (0, 0, 0), 1.0, emission=srgb('#ff2a10'), strength=3, alpha=0.25)
    m['ember'] = material('LampEmber', srgb('#ff4a20'), 0.3, emission=srgb('#ff3a10'), strength=6)
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


def concrete(name, parts, root, colour=GREY, pivot=(0, 0, 0)):
    """Merges `parts` into one object in baked Nod concrete of `colour` (a hex colour
    or a key of CONCRETE)."""
    obj = kit.merge(name, parts, pivot)
    obj.data.materials.clear()
    obj.data.materials.append(concrete_material(f'Nod_{name}', CONCRETE.get(colour, colour), root))
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


# --------------------------------------------------------------------------- shapes

def prism(name, mat, bottom, top, z0, z1, bevel=0.01):
    """A solid between two outlines (lists of (x, y), same count, counter-clockwise):
    the bottom one at height z0, the top one at z1 – sloped walls, sharp Nod shapes."""
    def build(bm):
        low = [bm.verts.new((x, y, z0)) for x, y in bottom]
        high = [bm.verts.new((x, y, z1)) for x, y in top]
        bm.faces.new(low[::-1])
        bm.faces.new(high)
        n = len(bottom)
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((low[k], low[j], high[j], high[k]))

    return kit.finish(kit.mesh_object(name, build), mat, bevel)


def chamfered(cx, cy, sx, sy, c):
    """Outline of a rectangle (centre, size) with its corners cut by c, counter-clockwise."""
    x0, x1, y0, y1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
    return [(x0 + c, y0), (x1 - c, y0), (x1, y0 + c), (x1, y1 - c), (x1 - c, y1), (x0 + c, y1), (x0, y1 - c), (x0, y0 + c)]


def loft(name, sections, material_of, cap=None):
    """A shell through cross-sections (lists of points of equal count, in order);
    material_of(i, k) → material of the face between sections i, i+1 and points k,
    k+1. `cap`: material to close the first and the last section with (None: open)."""
    import bmesh
    mats = []

    def index(mat):
        if mat not in mats:
            mats.append(mat)
        return mats.index(mat)

    def build(bm):
        rings = [[bm.verts.new(p) for p in section] for section in sections]
        for i, (a, b) in enumerate(zip(rings, rings[1:])):
            for k in range(len(a) - 1):
                face = bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
                face.material_index = index(material_of(i, k))
        if cap is not None:
            for ring in (rings[0], rings[-1]):
                face = bm.faces.new(ring)
                face.material_index = index(cap)

    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    build(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for mat in mats:
        mesh.materials.append(mat)
        mat.use_backface_culling = True
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    kit.collection().objects.link(obj)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj


def lathe(name, mat, profile, location, segments=32, bevel=0.0):
    """Surface of revolution from (radius, height) points, bottom to top, capped."""
    def build(bm):
        rings = []
        for r, z in profile:
            rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), z))
                          for a in (2 * math.pi * i / segments for i in range(segments))])
        for lower, upper in zip(rings, rings[1:]):
            for i in range(segments):
                j = (i + 1) % segments
                bm.faces.new((lower[i], lower[j], upper[j], upper[i]))
        bm.faces.new(rings[0])
        bm.faces.new(rings[-1])

    obj = kit.mesh_object(name, build)
    obj.location = location
    return kit.finish(obj, mat, bevel)


def spike(name, mat, root, direction, length, width, thickness, droop=0.0):
    """A flat, sharp blade from `root` along `direction`, its tip lowered by `droop`."""
    d = Vector(direction).normalized()
    side = Vector((-d.y, d.x, 0)) * width / 2
    up = Vector((0, 0, thickness / 2))
    root = Vector(root)
    tip = root + d * length - Vector((0, 0, droop))
    return kit.hexahedron(name, mat, (
        root - side - up, root + side - up, tip + side * 0.08 - up * 0.3, tip - side * 0.08 - up * 0.3,
        root - side + up, root + side + up, tip + side * 0.08 + up * 0.3, tip - side * 0.08 + up * 0.3), bevel=0.003)


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


def beacon(name, m, location, colour='red'):
    """A small lamp housing (returned first) and its bulb + halo, which blinks. Key them
    in different clips; if the housing pops in (scale from ~0) in Build, do not parent
    the light to it (see lamp())."""
    housing, light = kit.beacon(name, m, location, colour)
    return kit.merge(f'{name}Housing', [housing], location), light


def lamp(m, holder, name, at, colour, start):
    """A beacon on `holder` whose housing pops in at `start` (Build); returns its light
    (blinks in Idle). The light hangs on `holder`, not on the housing: under a parent
    that Build scales to ~0 the glTF exporter writes bad translation keys into Idle (the
    lamp hops) – so `holder` and its parents must not be scaled to ~0 in Build either
    (let them rise or slide in instead)."""
    housing, light = kit.beacon(name, m, at, colour)
    housing = kit.parent(kit.merge(name, [housing], at), holder)
    kit.parent(light, holder)
    kit.pop(housing, start, 5)
    return light


# --------------------------------------------------------------------------- animation

def pulse(obj, frames, low=0.6, high=1.15, phase=0.0, cycles=1):
    """Keys a glow swelling and fading (scale), `cycles` times a loop of `frames`."""
    base = Vector(obj.scale)
    keys = {}
    for f in range(0, frames + 1, 3):
        t = (math.sin(2 * math.pi * (cycles * f / frames + phase)) + 1) / 2
        keys[f] = base * (low + (high - low) * t)
    keys[frames] = keys[0]
    kit.keys(obj, 'scale', keys, 'LINEAR')


def spin(obj, frames, axis=2, turns=1):
    """Keys whole turns about one local axis over the loop."""
    rest = Vector(obj.rotation_euler)
    keys = {}
    for f in range(0, frames + 1, 5):
        r = rest.copy()
        r[axis] += 2 * math.pi * turns * f / frames
        keys[f] = r
    end = rest.copy()
    end[axis] += 2 * math.pi * turns
    keys[frames] = end
    kit.keys(obj, 'rotation_euler', keys, 'LINEAR')
    obj.rotation_euler = rest


def rise(obj, start, length, depth):
    """Keys the object rising out of the ground (from `depth` below) with a small overshoot."""
    p = Vector(obj.location)
    kit.keys(obj, 'location', {0: p - Vector((0, 0, depth)), start: p - Vector((0, 0, depth)),
                               start + length * 0.85: p + Vector((0, 0, 0.01)), start + length: p})


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


def clips(lights=(), idle=()):
    """Everything keyed so far goes on the track Build; then the lights blink
    ((object, frames on)) and the idle animations ((object, keyer)) go on Idle."""
    for obj in kit.collection().objects:
        if obj.animation_data and obj.animation_data.action:
            kit.to_track(obj, 'Build')
    for obj, pattern in lights:
        kit.blink(obj, pattern)
        kit.to_track(obj, 'Idle')
    for obj, animate in idle:
        animate(obj)
        kit.to_track(obj, 'Idle')


# --------------------------------------------------------------------------- run

def start(collection, root_name, build_end, idle_end=60):
    """A fresh collection with the root empty; the scene stands at the end of Build
    (parenting reads the evaluated pose: the finished building)."""
    kit.COLLECTION = collection
    kit.BUILD_END = build_end
    kit.IDLE_END = idle_end
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = build_end + 12
    scene.frame_current = build_end
    return kit.empty(root_name)


def _tracks():
    return [t for obj in bpy.data.objects if obj.animation_data for t in obj.animation_data.nla_tracks]


def _camera(scale, target, azimuth=45, elevation=30):
    cam = bpy.data.objects['PreviewCamera']
    cam.data.ortho_scale = scale
    a, e = math.radians(azimuth), math.radians(elevation)
    direction = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = Vector(target) + direction * 10
    cam.rotation_euler = (-direction).to_track_quat('-Z', 'Y').to_euler()


def _rest_pose():
    return {obj.name: (obj.location.copy(), obj.rotation_euler.copy(), obj.scale.copy()) for obj in kit.collection().objects}


def _pose(rest, playing):
    """Objects without a track in `playing` back to their rest pose (a muted track
    leaves its object in whatever pose it was last evaluated in)."""
    for obj in kit.collection().objects:
        ad = obj.animation_data
        if obj.name in rest and not (ad and any(t.name in playing for t in ad.nla_tracks)):
            obj.location, obj.rotation_euler, obj.scale = rest[obj.name]


def previews(out_dir, clips, scale, target, rest=None):
    """Renders through the game's camera (orthographic, 30° down, azimuth 45°):
    out_dir/build/… the Build clip alone; out_dir/<clip>/… every other clip over the
    finished building; out_dir/views/… the finished building from four sides and
    closer (az45 = the game's view, az225 the back, az135/az315 the other corners)."""
    scene = bpy.context.scene
    kit.render_preview([], out_dir)
    tracks = _tracks()
    for clip, frames in clips.items():
        for t in tracks:  # the finished building first, then the clip alone over it
            t.mute = t.name != 'Build'
        scene.frame_set(kit.BUILD_END)
        if clip != 'Build':
            for t in tracks:
                t.mute = t.name != clip
        if rest:
            _pose(rest, ('Build', clip))
        _camera(scale, target)
        kit.render_preview(frames, os.path.join(out_dir, clip.lower()))
    for t in tracks:
        t.mute = t.name != 'Build'
    scene.frame_set(kit.BUILD_END)
    if rest:
        _pose(rest, ('Build',))
    views = os.path.join(out_dir, 'views')
    os.makedirs(views, exist_ok=True)
    for azimuth, elevation, zoom in ((45, 30, 1.0), (45, 30, 0.55), (225, 30, 1.0), (135, 30, 1.0), (315, 30, 1.0), (45, 8, 1.0)):
        _camera(scale * zoom, target, azimuth, elevation)
        scene.render.filepath = os.path.join(views, f'az{azimuth}_el{elevation}_x{zoom}.png')
        bpy.ops.render.render(write_still=True)
    for t in tracks:
        t.mute = False
    for name in ('PreviewGround', 'PreviewSun', 'PreviewCamera'):
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)


def main(build, name, clips, ortho=2.9, target=(0, 0, 0.35), texture=512):
    """Builds, bakes the concrete (finished building), exports public/models/<name>.glb,
    saves blender/<name>.blend; `-- --preview <dir>` renders `clips` ({clip: frames})
    and the views (see previews())."""
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    out = os.path.join(PROJECT, 'public', 'models', f'{name}.glb')
    blend = os.path.join(HERE, f'{name}.blend')
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    rest = _rest_pose()   # build() leaves every object at rest (gates shut, flashes hidden)
    bpy.context.scene.frame_set(kit.BUILD_END)
    bake(texture)
    bpy.context.scene.frame_set(kit.BUILD_END)
    print('export', kit.export_glb(out), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    if '--preview' in args:
        previews(args[args.index('--preview') + 1], clips, ortho, target, rest)
