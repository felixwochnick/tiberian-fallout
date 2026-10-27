"""
Tiberian Fallout – GDI concrete wall (GAWALL), after Tiberian Sun.

A low, broad wall of light grey concrete on one cell, built like the original's
overlay: each piece is two blocks with a trapezoid cross-section (broad sloped flanks,
a narrow flat ridge, a thin ochre band along their feet) with a groove between them in
the middle of the cell. Where two pieces meet, at the cell's edge, an ochre joint
stands up a little higher than the blocks – a pillar with upright faces under a grey
cap (the gap between the two halves' caps is the notch on top), with a dark triangular
gusset on either side at its foot. The concrete is speckled and stained (a baked
texture, like the camouflage of the other buildings, but grey).

Like the sandbags (see GASAND.py) the wall is made of parts the game shows or hides to
join up with its neighbours (Battlefield.connectWalls):

    Post     always shown: the two blocks of a lone piece – a square hump split in
             two by a groove, its ends sloped. Slightly smaller than the arms' blocks,
             so where arms are shown it lies inside them
    ArmXP    a block from the middle of the cell to the joint at its edge towards
             world +x (glTF), and that half of the joint
    ArmXN    … towards -x
    ArmZP    … towards +z (Blender -y)
    ArmZN    … towards -z (Blender +y)

Each arm is the joint's half (pillar, cap, gussets) with the baked block as a child
(<Arm>Block). So a straight run shows two blocks per cell (the groove in the middle of
the cell, a joint at its edge), like the original; a corner, T-piece or crossing joins
its blocks in the middle of the cell. The arm pieces (arm()) are also used by the
component tower (GACTWR) and the gates (GAGATE_A, GAGATE_B) to run into a wall.

Animations (glTF clips)
    Build    one-shot, 0.6 s: the blocks and joints grow up out of the ground

Run headless:

    blender -b --factory-startup --python blender/GAWALL.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up; origin in the middle of the cell on the ground.
"""
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'GAWALL.glb')
BLEND = os.path.join(HERE, 'GAWALL.blend')

HEIGHT = 0.44           # a block's ridge
FOOT = 0.47             # half a block's width at the ground
PLINTH = (0.46, 0.04)   # (half width, height) where the flank starts to slope in
RIDGE = 0.1             # half the width of the flat ridge
SHOULDER = (0.14, 0.42)  # (half width, height) of the ridge's rounded edge
GROOVE = 0.02           # half the groove between the two blocks of a cell
JOINT = 0.085           # length of half a joint (each cell brings one half)
PILLAR = (0.36, 0.31, 0.5)  # the joint: half width at its foot and its top, height
INSET = 0.03            # the post lies this much inside the arms' blocks
TEXTURE = 128           # size of a block's baked texture

box, srgb, material = kit.box, kit.srgb, kit.material


def materials():
    return {
        'concrete': material('WallConcrete', srgb('#b3b1aa'), 0.92),
        'concrete_dark': material('WallConcreteDark', srgb('#55554f'), 0.95),
        'cap': material('WallCap', srgb('#8f8e88'), 0.9),
        'coping': material('WallCoping', srgb('#a88a45'), 0.8),
        'coping_dark': material('WallCopingDark', srgb('#6f5a2c'), 0.85),
        'groove': material('WallGroove', srgb('#3e3d39'), 0.95),
    }


def concrete_material(name):
    """Speckled, stained light grey concrete; baked like the camouflage (kit.bake_camo
    bakes every Camo_* material) into a small texture of its own."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = True
    nt = mat.node_tree
    nt.nodes.clear()
    nodes, links = nt.nodes, nt.links
    out = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Roughness'].default_value = 0.92
    coords = nodes.new('ShaderNodeTexCoord')

    def noise(scale, detail, low, high, z_scale=1.0):
        mapping = nodes.new('ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (scale, scale, scale * z_scale)
        links.new(coords.outputs['Object'], mapping.inputs['Vector'])
        tex = nodes.new('ShaderNodeTexNoise')
        tex.inputs['Detail'].default_value = detail
        links.new(mapping.outputs['Vector'], tex.inputs['Vector'])
        span = nodes.new('ShaderNodeMapRange')
        span.inputs['From Min'].default_value = 0.3
        span.inputs['From Max'].default_value = 0.7
        span.inputs['To Min'].default_value = low
        span.inputs['To Max'].default_value = high
        links.new(tex.outputs['Fac'], span.inputs['Value'])
        return span.outputs['Result']

    ao = nodes.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = 0.06
    ao.samples = 16
    shade = nodes.new('ShaderNodeMapRange')
    shade.inputs['To Min'].default_value = 0.75
    links.new(ao.outputs['AO'], shade.inputs['Value'])

    total = None
    for factor in (noise(40, 8, 0.7, 1.12), noise(6, 3, 0.8, 1.06), noise(12, 4, 0.86, 1.04, 0.15), shade.outputs['Result']):
        node = nodes.new('ShaderNodeMath')
        node.operation = 'MULTIPLY'
        if total is None:
            node.inputs[0].default_value = 1.0
        else:
            links.new(total, node.inputs[0])
        links.new(factor, node.inputs[1])
        total = node.outputs['Value']
    tint = nodes.new('ShaderNodeMix')
    tint.data_type = 'RGBA'
    tint.blend_type = 'MULTIPLY'
    tint.inputs['Factor'].default_value = 1.0
    tint.inputs['A'].default_value = (*srgb('#aeaca4'), 1)
    combine = nodes.new('ShaderNodeCombineColor')
    for channel in ('Red', 'Green', 'Blue'):
        links.new(total, combine.inputs[channel])
    links.new(combine.outputs['Color'], tint.inputs['B'])
    links.new(tint.outputs['Result'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    # a small texture of its own (bake_camo takes an image of this name if it exists)
    image = f'{name}_Color'
    if image not in bpy.data.images:
        bpy.data.images.new(image, TEXTURE, TEXTURE)
    return mat


def profile(grow=0.0):
    """Cross-section of a block (across, up), counter-clockwise from the bottom left;
    `grow` moves it outwards (negative: inwards)."""
    (px, pz), (sx, sz), h = PLINTH, SHOULDER, HEIGHT + grow
    return [(-FOOT - grow, 0), (FOOT + grow, 0), (px + grow, pz), (sx + grow, sz + grow * 0.5), (RIDGE + grow, h),
            (-RIDGE - grow, h), (-sx - grow, sz + grow * 0.5), (-px - grow, pz)]


def half_width(z):
    """Half the block's width at height z."""
    pts = [(FOOT, 0), PLINTH, SHOULDER, (RIDGE, HEIGHT)]
    for (w0, z0), (w1, z1) in zip(pts, pts[1:]):
        if z0 <= z <= z1:
            return w0 + (w1 - w0) * (z - z0) / (z1 - z0)
    return RIDGE


def section(along_x, a0, a1, prof, name, mat, bevel):
    """A prism of a cross-section from a0 to a1 along x (or along y)."""
    def build(bm):
        rings = []
        for a in (a0, a1):
            rings.append([bm.verts.new((a, u, v) if along_x else (u, a, v)) for u, v in prof])
        bm.faces.new(rings[0])
        bm.faces.new(rings[1][::-1])
        n = len(prof)
        for k in range(n):
            j = (k + 1) % n
            bm.faces.new((rings[0][k], rings[0][j], rings[1][j], rings[1][k]))

    return kit.finish(kit.mesh_object(name, build), mat, bevel, 2)


def arm(name, m, direction, start=GROOVE, end=0.503):
    """A block from `start` (distance from the middle of the cell) to the joint and
    that half of the joint, reaching `end` (the cell's edge), along `direction` (unit
    vector along x or y). Returns the joint's half (pillar, cap, gussets, the ochre
    foot bands) named `name`, origin on the ground under the block's inner end; the
    baked block hangs from it as `name`Block."""
    d = Vector(direction)
    along_x = abs(d.x) > 0.5
    sign = d.x if along_x else d.y
    joint = end - JOINT

    def span(a0, a1):
        return (min(a0, a1) * sign, max(a0, a1) * sign) if sign > 0 else (-max(a0, a1), -min(a0, a1))

    def point(a, u, z):
        """(along, across, up) to Blender coordinates."""
        return (a * sign, u, z) if along_x else (u, a * sign, z)

    # the block, baked; it runs a little into the pillar
    block = section(along_x, *span(start, joint + 0.02), profile(), f'{name}Block', m['concrete'], 0.012)
    block.data.materials.clear()
    block.data.materials.append(concrete_material(f'Camo_{name}Block'))

    parts = []
    # ochre bands along the block's feet
    (px, pz) = PLINTH
    for s in (-1, 1):
        band = [(s * (FOOT + 0.006), 0), (s * (px + 0.006), pz + 0.004), (s * (px - 0.012), pz + 0.004), (s * (FOOT - 0.012), 0)]
        if s < 0:
            band = band[::-1]
        parts.append(section(along_x, *span(start + 0.01, joint), band, f'{name}Band{s}', m['coping'], 0))
    # the pillar: upright ochre faces, a grey cap (stopping short of the edge: the notch)
    w0, w1, h = PILLAR
    pillar = [(-w0, 0), (w0, 0), (w1, h), (-w1, h)]
    parts.append(section(along_x, *span(joint, end), pillar, f'{name}Pillar', m['coping'], 0.006))
    parts.append(section(along_x, *span(joint + 0.03, end), [(-w0 - 0.006, 0.06), (w0 + 0.006, 0.06), (w0 + 0.004, 0.075), (-w0 - 0.004, 0.075)],
                         f'{name}PillarBand', m['coping_dark'], 0))
    cap = [(-w1 - 0.012, h - 0.01), (w1 + 0.012, h - 0.01), (w1 - 0.01, h + 0.03), (-w1 + 0.01, h + 0.03)]
    parts.append(section(along_x, *span(joint - 0.012, end - 0.016), cap, f'{name}Cap', m['cap'], 0.005))
    # dark gussets at the pillar's foot, on either side (they hide the block's end)
    for s in (-1, 1):
        tri = [(w0 - 0.01, 0), (FOOT + 0.13, 0), (FOOT + 0.11, 0.02), (w0 + 0.005, 0.2), (w0 - 0.01, 0.2)]
        tri = [(s * u, z) for u, z in tri]
        if s < 0:
            tri = tri[::-1]
        parts.append(section(along_x, *span(joint + 0.012, end), tri, f'{name}Gusset{s}', m['concrete_dark'], 0.004))
    origin = Vector(direction) * start
    obj = kit.merge(name, parts, (origin.x, origin.y, 0))
    block = kit.merge(f'{name}Block', [block], (origin.x, origin.y, 0))
    kit.parent(block, obj)
    return obj


def post(m):
    """The two blocks of a lone piece: a square hump split by a groove across x, a dark
    core in the groove."""
    levels = []
    for w, z in ((FOOT, 0), PLINTH, SHOULDER, (RIDGE, HEIGHT)):
        levels.append((w - INSET, max(0.0, z - INSET * (0.3 if z < 0.1 else 1.0))))
    halves = []
    for s in (-1, 1):
        def build(bm, s=s):
            rings = []
            for w, z in levels:
                xs = (s * GROOVE, s * w)
                rings.append([bm.verts.new((x, y, z)) for x, y in ((xs[0], -w), (xs[1], -w), (xs[1], w), (xs[0], w))])
            bm.faces.new(rings[0])
            bm.faces.new(rings[-1])
            for lo, hi in zip(rings, rings[1:]):
                for k in range(4):
                    j = (k + 1) % 4
                    bm.faces.new((lo[k], lo[j], hi[j], hi[k]))

        halves.append(kit.finish(kit.mesh_object(f'PostHalf{s}', build), m['concrete'], 0.012, 2))
    obj = kit.merge('Post', halves)
    obj.data.materials.clear()
    obj.data.materials.append(concrete_material('Camo_Post'))
    core = section(True, -GROOVE - 0.005, GROOVE + 0.005, [(u, max(0.0, z - 0.05)) for u, z in profile(-INSET - 0.02)], 'PostGroove', m['groove'], 0)
    core = kit.parent(kit.merge('PostGroove', [core]), obj)
    return obj


def build():
    kit.COLLECTION = 'GDIWall'
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.render.fps = kit.FPS
    scene.frame_start = 0
    scene.frame_end = 20
    scene.frame_current = 0

    m = materials()
    root = kit.empty('GDIWall')
    # glTF +x = Blender +x, glTF +z = Blender -y
    parts = [post(m),
             arm('ArmXP', m, (1, 0, 0)), arm('ArmXN', m, (-1, 0, 0)),
             arm('ArmZN', m, (0, 1, 0)),     # Blender +y
             arm('ArmZP', m, (0, -1, 0))]    # Blender -y
    for obj in parts:
        kit.parent(obj, root)

    # Build: everything grows up out of the ground (scaled in z from the ground)
    for k, obj in enumerate(parts):
        kit.keys(obj, 'scale', {0: Vector((1, 1, kit.HIDDEN)), 2 + k: Vector((1, 1, kit.HIDDEN)),
                                12 + k: Vector((1, 1, 1.06)), 16 + k: Vector((1, 1, 1))})
        kit.to_track(obj, 'Build')
    return len(parts)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('objects', build(), flush=True)
    kit.bake_camo(TEXTURE)
    bpy.context.scene.frame_set(20)
    print('export', kit.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        import gdibuilding
        gdibuilding.preview([int(f) for f in args[args.index('--preview') + 1].split(',')], args[args.index('--preview') + 2],
                            1.6, (0, 0, 0.25))


if __name__ == '__main__' and bpy.app.background:
    main()
