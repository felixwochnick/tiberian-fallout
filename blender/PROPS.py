"""
Tiberian Fallout – the terrain objects of the landscape: trees, bushes and rocks, after
Tiberian Sun's TREE01 … TREE25 and boulders of the temperate and the snow theater.

The game puts a few hundred of them on a map and draws each variant as one
InstancedMesh, so a variant is one static mesh (no animation) and all of them share one
material, Prop, whose colour comes from the vertex colours: a shade per face, light on
top and on the outside, dark underneath and in the hollows, a little dappled, so they
read at the game's small scale in its gloomy light. Low poly, flat shading.

Variants – top-level nodes at the origin, the trunk (or the middle of the stones) on
the origin, standing on Z = 0; each node's extras give `radius` (how far it reaches
out from the origin), `height` (both in cells) and `theater` (temperate or snow):

  temperate
    Oak1 … Oak3       broad leafy trees (TREE01, TREE05, TREE15): a grey-brown gnarled
                      trunk forking into a few big branches, a crown of lumpy clumps of
                      dark olive foliage, khaki where the light falls on top; Oak1 big and
                      round, Oak2 smaller and taller, Oak3 low and spreading on two stems
    Pine1, Pine2      conifers (TREE10): tall and narrow, drooping tiers of dark green
                      needles; Pine2 a big one with a small one beside it
    Dead1, Dead2      autumn trees (TREE25, TREE20): a pale grey trunk and branching
                      twigs, bare; Dead2 with clumps of dry ochre leaves
    Bush1 … Bush3     low shrubs, dry olive and brownish green
    Rock1 … Rock3     angular boulders of brown-grey stone half sunk in the ground with
                      smaller stones round them: big, medium, small
  snow
    SnowPine1 … 3     conifers heavy with snow: tall and white (TREE01.SNO), broad, dark
                      and dense (TREE20.SNO), a small pair (TREE10.SNO)
    SnowDead1         a bare grey tree with snow lying on its branches
    SnowBush1         a low shrub under snow
    SnowRock1, 2      grey-blue boulders with snow caps on their tops

The pairs stand as in the sprites, seen through the game's camera (from the front
right): Pine2's small tree left of the big one, SnowPine3's small one in front on the
left.

Run headless (builds, exports the GLB, saves the .blend; --preview also renders every
variant through the game's camera and light into <dir>, alone and in a row per theater
with a soldier and the MCV for scale):

    blender -b --factory-startup --python blender/PROPS.py [-- --preview <dir>]

Units: 1 = one map cell. Blender Z is up, the front is −Y.
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

kit.COLLECTION = 'Props'
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'PROPS.glb')
BLEND = os.path.join(HERE, 'PROPS.blend')
UP = Vector((0, 0, 1))
# bmesh.ops.create_icosphere's subdivisions (Blender 5): a plain icosahedron of 20 faces, or 80
ROUGH, ROUND = 1, 2
# along the ground, the screen's right and its back (the game's camera looks from the front right)
SCREEN_RIGHT = Vector((1, 1, 0)).normalized()
SCREEN_BACK = Vector((-1, 1, 0)).normalized()


# --------------------------------------------------------------------------- colours
# The colour layer holds bytes, read as sRGB: the export turns them into linear values.

def rgb(hex_colour):
    h = hex_colour.lstrip('#')
    return Vector([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def gradient(*hexes):
    return [rgb(h) for h in hexes]


LEAVES = gradient('#10160a', '#222c0e', '#38481a', '#56642e', '#837a4c', '#b09e70')
LEAVES_BRIGHT = rgb('#4c7a28')
NEEDLES = gradient('#0a1206', '#172812', '#29421e', '#42642a', '#66803e')
NEEDLES_BRIGHT = rgb('#4e8c2c')
NEEDLES_TAN = rgb('#7a6a3c')
BARK = gradient('#2e2a24', '#554d42', '#7f7564', '#aa9e8a')
DEAD_WOOD = gradient('#3c3c3a', '#6a6864', '#9e9c96', '#d4d2ca')
OCHRE = gradient('#382810', '#664c1e', '#8e7036', '#b2924c', '#cfb06a')
SCRUB = gradient('#1c1c0a', '#3a3a18', '#5c5a28', '#7c763e', '#9a8a58')
SCRUB_BROWN = gradient('#201a0c', '#42361a', '#645428', '#84723e', '#9e8a58')
SCRUB_TAN = rgb('#a08a58')
STONE = gradient('#27231e', '#48423a', '#6e675b', '#979081', '#c0b8a6')
SNOW = gradient('#7890b0', '#a8bcd6', '#d4e2f4', '#eef5ff')
SNOW_NEEDLES = gradient('#0e1a20', '#1c2e36', '#2e4656', '#486676')
SNOW_STONE = gradient('#262c34', '#46505c', '#6a7684', '#909cab')
SNOW_WOOD = gradient('#303032', '#58585c', '#848488', '#acacb0')
SNOW_TWIGS = gradient('#1c1c16', '#34322a', '#504a3a', '#6c644e')


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def ramp(stops, t):
    """The colour at t (0 … 1, clamped) on a gradient of evenly spaced stops"""
    t = clamp(t) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    return stops[i].lerp(stops[i + 1], t - i)


def around(angle):
    return Vector((math.cos(angle), math.sin(angle), 0))


def tilt(direction, angle, turn):
    """`direction` tipped over by `angle` towards the side `turn` (radians round it)"""
    d = direction.normalized()
    u = d.cross(UP if abs(d.z) < 0.95 else Vector((1, 0, 0))).normalized()
    w = d.cross(u)
    side = u * math.cos(turn) + w * math.sin(turn)
    return (d * math.cos(angle) + side * math.sin(angle)).normalized()


def frames(points):
    """A frame (tangent, u, w) at every point of a polyline, carried along it without twisting"""
    tangents = [(points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
                for i in range(len(points))]
    previous = tangents[0]
    u = previous.cross(UP if abs(previous.z) < 0.9 else Vector((1, 0, 0))).normalized()
    result = []
    for t in tangents:
        u = previous.rotation_difference(t) @ u
        u = (u - t * u.dot(t)).normalized()
        result.append((t, u, t.cross(u)))
        previous = t
    return result


# --------------------------------------------------------------------------- geometry

class Prop:
    """A bmesh with a colour per face corner, filled with trunks, foliage, tiers and stones"""

    def __init__(self, seed):
        self.bm = bmesh.new()
        self.colour = self.bm.loops.layers.color.new('Col')
        self.rng = random.Random(seed)
        self.offset = Vector([self.rng.uniform(0, 100) for _ in range(3)])

    def paint(self, faces, shade):
        """Colours each face with shade(point, normal) at its middle"""
        for face in faces:
            face.normal_update()
            colour = shade(face.calc_center_median(), face.normal.copy())
            for loop in face.loops:
                loop[self.colour] = (*colour, 1)

    def dapple(self, point, scale=9.0):
        """Coherent noise, about −1 … 1: patches of light and shade"""
        return noise.noise(point * scale + self.offset)

    def tube(self, points, radii, sides, upright=True, wobble=0.12):
        """
        A rough prism along a polyline (open at its start, which sits inside the ground or
        its parent); a radius 0 ends it in a point. `upright` turns its sides so one faces
        up wherever it is not upright, the face snow lies on.
        """
        rng = self.rng
        step = math.tau / sides
        rings = []
        turn = 0.0
        for (t, u, w), p, r in zip(frames(points), points, radii):
            if r <= 0:
                rings.append(self.bm.verts.new(p))
                continue
            top = UP - t * t.z
            if upright and top.length > 0.3:
                want = math.atan2(top.dot(w), top.dot(u)) - step / 2
                turn += (want - turn + step / 2) % step - step / 2
            rings.append([self.bm.verts.new(p + (u * math.cos(turn + step * i) + w * math.sin(turn + step * i))
                                            * r * rng.uniform(1 - wobble, 1 + wobble)) for i in range(sides)])
        faces = []
        for a, b in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                if isinstance(b, bmesh.types.BMVert):
                    faces.append(self.bm.faces.new((a[i], a[j], b)))
                else:
                    faces.append(self.bm.faces.new((a[i], a[j], b[j], b[i])))
        return faces

    def lump(self, centre, radius, scale=(1.0, 1.0, 1.0), subdivisions=ROUND, rough=0.35):
        """A lumpy blob (an icosphere pushed in and out by noise), scaled by `scale`"""
        rng = self.rng
        result = bmesh.ops.create_icosphere(self.bm, subdivisions=subdivisions, radius=radius)
        offset = Vector([rng.uniform(0, 50) for _ in range(3)])
        for v in result['verts']:
            v.co *= (1 + rough * noise.noise(v.co / radius * 1.8 + offset)) * rng.uniform(0.9, 1.08)
            v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + centre
        return list(dict.fromkeys(f for v in result['verts'] for f in v.link_faces))

    def boulder(self, centre, size, top, count=16, turn=0.0, sink=0.04):
        """
        An angular stone: the hull of points on a squashed ellipsoid of half widths `size`
        (x, y) round `centre` on the ground, `top` high, its widest part about the
        ground, so it lies half sunk in; cut off flat `sink` under the ground (no faces
        there) and a little flattened on top
        """
        rng = self.rng
        rz = top * 1.4
        cz = top - rz
        c, s = math.cos(turn), math.sin(turn)
        points = []
        if count >= 10:
            # a broad, slanted facet on top
            spin = rng.uniform(0, math.tau)
            for k in range(3):
                at = around(spin + math.tau * k / 3) * rng.uniform(0.35, 0.5)
                points.append(Vector((at.x * size[0], at.y * size[1], top * rng.uniform(0.88, 1.0))))
        while len(points) < count:
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
            if d.z < -0.05:
                continue
            # pushed out towards the corners of its box (a superellipsoid): a blocky stone
            d /= (abs(d.x) ** 3 + abs(d.y) ** 3 + abs(d.z) ** 3) ** (1 / 3)
            r = rng.uniform(0.8, 1.0)
            points.append(Vector((d.x * size[0] * r, d.y * size[1] * r, min(cz + d.z * rz * r, top * rng.uniform(0.86, 1.0)))))
        base = max(4, count // 3)
        for i in range(base):
            a = math.tau * (i + rng.uniform(-0.3, 0.3)) / base
            points.append(Vector((math.cos(a) * size[0], math.sin(a) * size[1], 0)) * rng.uniform(0.85, 1.0) - Vector((0, 0, sink)))
        verts = [self.bm.verts.new(centre + Vector((p.x * c - p.y * s, p.x * s + p.y * c, p.z))) for p in points]
        result = bmesh.ops.convex_hull(self.bm, input=verts)
        unused = list(dict.fromkeys(v for v in result['geom_interior'] + result['geom_unused']
                                    if isinstance(v, bmesh.types.BMVert)))
        bmesh.ops.delete(self.bm, geom=unused, context='VERTS')
        faces = [f for f in result['geom'] if isinstance(f, bmesh.types.BMFace) and f.is_valid]
        for f in faces:
            f.normal_update()
        bottom = [f for f in faces if f.normal.z < -0.97]
        bmesh.ops.delete(self.bm, geom=bottom, context='FACES_ONLY')
        return [f for f in faces if f.is_valid]

    def tier(self, centre, top, bottom, radius, points, turn, droop):
        """
        One drooping layer of a conifer's branches round `centre` (on the ground): a low
        cone from `top` out to a star-shaped rim of `points` hanging tips at `bottom`
        (notches between them higher up), closed underneath. Its faces by part:
        (upper, fringe, under).
        """
        rng = self.rng
        h = top - bottom
        apex = self.bm.verts.new(centre + Vector((0, 0, top)))
        ring, rim = [], []
        for j in range(2 * points):
            out = around(turn + math.pi * j / points + rng.uniform(-0.12, 0.12))
            tip = j % 2 == 0
            ring.append(self.bm.verts.new(centre + out * radius * (0.62 if tip else 0.42)
                                          + Vector((0, 0, top - h * (0.32 if tip else 0.27)))))
            rim.append(self.bm.verts.new(centre + out * radius * (rng.uniform(0.94, 1.08) if tip else 0.5)
                                         + Vector((0, 0, bottom - rng.uniform(0.3, 1.0) * droop if tip else bottom + h * 0.42))))
        under = self.bm.verts.new(centre + Vector((0, 0, bottom + h * 0.36)))
        n = 2 * points
        upper = [self.bm.faces.new((apex, ring[j], ring[(j + 1) % n])) for j in range(n)]
        fringe = [self.bm.faces.new((ring[j], rim[j], rim[(j + 1) % n], ring[(j + 1) % n])) for j in range(n)]
        below = [self.bm.faces.new((under, rim[(j + 1) % n], rim[j])) for j in range(n)]
        return upper, fringe, below

    def finish(self, name, mat, theater):
        mesh = bpy.data.meshes.new(name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        mesh.materials.append(mat)
        mesh.color_attributes.active_color = mesh.color_attributes['Col']
        mesh.color_attributes.render_color_index = mesh.color_attributes.active_color_index
        for poly in mesh.polygons:
            poly.use_smooth = False
        obj = bpy.data.objects.new(name, mesh)
        kit.collection().objects.link(obj)
        obj['radius'] = round(max(math.hypot(v.co.x, v.co.y) for v in mesh.vertices if v.co.z > -0.01), 2)
        obj['height'] = round(max(v.co.z for v in mesh.vertices), 2)
        obj['theater'] = theater
        return obj


def prop_material():
    """The one material of all variants: the vertex colours, matt"""
    mat = kit.material('Prop', (1, 1, 1), 0.95)
    nodes = mat.node_tree.nodes
    attribute = nodes.new('ShaderNodeVertexColor')
    attribute.layer_name = 'Col'
    mat.node_tree.links.new(attribute.outputs['Color'], nodes['Principled BSDF'].inputs['Base Color'])
    mat.use_backface_culling = True  # closed meshes: single-sided in glTF
    return mat


# --------------------------------------------------------------------------- shades

def bark_shade(prop, gradient_, height, light=0.0):
    """Wood: darker at the foot and underneath, streaked"""
    def shade(p, n):
        v = 0.3 + light + 0.25 * clamp(p.z / height) + 0.25 * max(0.0, n.z) - 0.1 * max(0.0, -n.z)
        v += 0.12 * prop.dapple(Vector((p.x * 3, p.y * 3, p.z * 0.6)), 14) + prop.rng.uniform(-0.06, 0.06)
        return ramp(gradient_, v)
    return shade


def snowy_wood_shade(prop, height):
    """Grey wood with snow on whatever faces up"""
    wood = bark_shade(prop, SNOW_WOOD, height, 0.2)

    def shade(p, n):
        if n.z + 0.15 * prop.dapple(p, 12) > 0.32:
            return ramp(SNOW, 0.55 + 0.4 * n.z + prop.rng.uniform(-0.08, 0.05))
        return wood(p, n)
    return shade


def foliage_shade(prop, middle, a, b, gradient_=LEAVES, bright=LEAVES_BRIGHT, light=0.0):
    """
    A crown of leaves round `middle` (half widths a across, b up): light on top and on
    the outside, dark underneath and in the hollows between the clumps, dappled
    """
    low, high = middle.z - b, middle.z + b

    def shade(p, n):
        h = clamp((p.z - low) / (high - low))
        d = p - middle
        d.z *= a / b
        out = n.dot(d.normalized()) if d.length > 1e-6 else 0.0
        v = 0.06 + light + 0.42 * h + 0.2 * max(0.0, n.z) + 0.2 * max(0.0, out) - 0.12 * max(0.0, -n.z)
        v += 0.18 * prop.dapple(p) + prop.rng.uniform(-0.07, 0.07)
        if v > 0.45 and prop.rng.random() < 0.06:
            return bright
        return ramp(gradient_, v)
    return shade


def needle_shade(prop, height, snow=None):
    """
    A conifer's tiers by part: the upper faces lighter towards the top, the drooping
    fringe darker, the underside nearly black; with snow (upper share, fringe slope) the
    upper faces and the flatter parts of the fringe lie white under the snow
    """
    gradient_ = SNOW_NEEDLES if snow else NEEDLES

    def shade_for(part):
        def shade(p, n):
            h = clamp(p.z / height)
            rng = prop.rng
            if snow and part != 'under':
                upper, edge = snow
                if (part == 'upper' and rng.random() < upper) or \
                        (part == 'fringe' and n.z + 0.15 * prop.dapple(p, 12) > edge and rng.random() < 0.85):
                    return ramp(SNOW, 0.4 + 0.35 * h + 0.3 * n.z + rng.uniform(-0.1, 0.06))
            if part == 'under':
                v = 0.04 + 0.1 * h
            elif part == 'upper':
                v = 0.5 + 0.3 * h + 0.15 * n.z
            else:
                v = 0.24 + 0.28 * h + 0.3 * max(0.0, n.z)
            v += 0.14 * prop.dapple(p, 11) + rng.uniform(-0.08, 0.08)
            if not snow and part != 'under' and v > 0.35:
                roll = rng.random()
                if roll < 0.06:
                    return NEEDLES_BRIGHT
                if roll < 0.09:
                    return NEEDLES_TAN
            return ramp(gradient_, v)
        return shade
    return shade_for


def scrub_shade(prop, middle, height, gradient_, snow=False):
    """A shrub: light on top, dark at the foot; under snow white wherever it faces up"""
    def shade(p, n):
        rng = prop.rng
        if snow and n.z + 0.2 * prop.dapple(p, 10) > 0.25:
            return ramp(SNOW, 0.45 + 0.45 * n.z + 0.15 * clamp(p.z / height) + rng.uniform(-0.1, 0.05))
        d = p - middle
        out = n.dot(Vector((d.x, d.y, 0)).normalized()) if d.length > 1e-6 else 0.0
        v = 0.1 + 0.42 * clamp(p.z / height) + 0.25 * max(0.0, n.z) + 0.12 * max(0.0, out)
        v += 0.16 * prop.dapple(p, 14) + rng.uniform(-0.07, 0.07)
        if not snow and v > 0.5 and rng.random() < 0.06:
            return SCRUB_TAN
        return ramp(gradient_, v)
    return shade


def stone_shade(prop, top, gradient_, snow=False):
    """Stone: light on the faces turned up, dark below; snow caps on the flat tops"""
    def shade(p, n):
        rng = prop.rng
        if snow:
            cover = n.z + 0.12 * prop.dapple(p, 6)
            if cover > 0.6:
                return ramp(SNOW, 0.55 + 0.45 * n.z + rng.uniform(-0.08, 0.05))
            if cover > 0.48:
                return ramp(SNOW, 0.2 + rng.uniform(-0.05, 0.1))
        v = 0.2 + 0.55 * max(0.0, n.z) ** 1.5 + 0.2 * clamp(p.z / top) + 0.1 * prop.dapple(p, 7) + rng.uniform(-0.08, 0.08)
        return ramp(gradient_, v)
    return shade


# --------------------------------------------------------------------------- trees

def oak(name, mat, seed, width, height, crown_base, ring, lower, sprigs=4, lean=(0.0, 0.0), stems=1, light=0.0):
    """
    A broad leafy tree: a gnarled trunk (or two stems) forking into big branches, under a
    crown `width` across from `crown_base` up to `height` of lumpy clumps: one on top, a
    `ring` round the middle, `lower` ones underneath, small `sprigs` sticking out of it
    """
    prop = Prop(seed)
    rng = prop.rng
    a = width / 2
    b = (height - crown_base) / 2
    middle = Vector((lean[0], lean[1], crown_base + b))
    squash = 0.85
    r = min(a, b) * 0.7
    spots = [(middle + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), b - r * squash)), r)]
    turn = rng.uniform(0, math.tau)
    for i in range(ring):
        r = a * rng.uniform(0.33, 0.48)
        at = around(turn + math.tau * (i + rng.uniform(-0.2, 0.2)) / ring) * (a - r)
        spots.append((middle + at + Vector((0, 0, b * rng.uniform(-0.15, 0.3))), r))
    for i in range(lower):
        r = a * rng.uniform(0.3, 0.38)
        at = around(turn + math.tau * (i + 0.5 + rng.uniform(-0.2, 0.2)) / lower) * (a - r) * 0.8
        spots.append((middle + at + Vector((0, 0, -b + r * squash * 0.9)), r))

    # the trunk: a flared foot, bent on the way up, closed in a point above the fork
    wood = bark_shade(prop, BARK, crown_base)
    if stems == 1:
        forks = [Vector((lean[0] * 0.5, lean[1] * 0.5, crown_base * 0.8))]
        bends = [Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), crown_base * 0.4))]
        thickness = [1.0]
    else:
        side = around(rng.uniform(0, math.tau))
        shift = Vector((lean[0], lean[1], 0)) * 0.3
        forks = [shift + side * a * 0.3 + Vector((0, 0, crown_base * 0.85)),
                 shift - side * a * 0.28 + Vector((0, 0, crown_base * 0.7))]
        bends = [f * 0.45 + Vector((0, 0, -f.z * 0.2)) for f in forks]
        thickness = [0.85, 0.75]
    for fork, bend, k in zip(forks, bends, thickness):
        points = [Vector((0, 0, -0.05)), Vector((bend.x * 0.2, bend.y * 0.2, 0.05)), bend, fork, fork + Vector((0, 0, 0.08))]
        prop.paint(prop.tube(points, [r * k for r in (0.1, 0.075, 0.062, 0.055, 0.0)], 5), wood)

    # the big branches, from the fork up into the clumps above and round it
    targets = [spots[0]] + spots[1 + ring:] + spots[1:1 + ring:2]
    for centre, _ in targets:
        fork = min(forks, key=lambda f: (f - centre).length)
        bend = fork.lerp(centre, 0.5) + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), -0.04))
        prop.paint(prop.tube([fork - Vector((0, 0, 0.03)), bend, fork.lerp(centre, 0.92)], [0.045, 0.03, 0.018], 4), wood)

    leaves = foliage_shade(prop, middle, a, b, light=light)
    for k, (centre, r) in enumerate(spots):
        lower_clump = k > ring
        prop.paint(prop.lump(centre, r, (1, 1, squash), ROUGH if lower_clump else ROUND, 0.45 if lower_clump else 0.38), leaves)
    for i in range(sprigs):
        r = a * rng.uniform(0.15, 0.22)
        at = around(turn + math.tau * (i + rng.uniform(0.2, 0.8)) / sprigs) * (a - r * 0.6)
        centre = middle + at + Vector((0, 0, b * rng.uniform(-0.3, 0.45)))
        prop.paint(prop.lump(centre, r, (1, 1, squash), ROUGH, 0.5), leaves)
    return prop.finish(name, mat, 'temperate')


def conifer(prop, base, height, radius, tiers, points, snow=None):
    """A conifer on `base`: a thin trunk under `tiers` drooping layers, narrowing to a spike on top"""
    rng = prop.rng
    trunk = [base + Vector((0, 0, -0.05)), base + Vector((0, 0, height * 0.45)), base + Vector((0, 0, height * 0.85))]
    prop.paint(prop.tube(trunk, [radius * 0.17, radius * 0.12, 0.0], 4),
               bark_shade(prop, SNOW_WOOD if snow else BARK, height * 0.3, -0.1))
    shade_for = needle_shade(prop, height, snow)
    z0 = height * 0.12
    span = height - z0
    spacing = span * 0.78 / (tiers - 1)
    for i in range(tiers):
        f = i / (tiers - 1)            # 0 the top tier, 1 the lowest
        bottom = height - span * (0.22 + 0.78 * f)
        top = height if i == 0 else bottom + spacing * 1.9
        r = radius * (0.22 + 0.78 * f ** 0.8) * rng.uniform(0.92, 1.06)
        parts = prop.tier(base, top, bottom, r, points, rng.uniform(0, math.tau), span * 0.05)
        for part, faces in zip(('upper', 'fringe', 'under'), parts):
            prop.paint(faces, shade_for(part))


def pines(name, mat, seed, trees, theater='temperate', snow=None):
    """One or more conifers: (x, y, height, radius, tiers, points) each"""
    prop = Prop(seed)
    for x, y, height, radius, tiers, points in trees:
        conifer(prop, Vector((x, y, 0)), height, radius, tiers, points, snow)
    return prop.finish(name, mat, theater)


def bare_tree(name, mat, seed, height, mains, levels, theater='temperate', leaves=0, snow=False):
    """
    A bare tree: a pale trunk forking at less than half its height into `mains` branches,
    each forking `levels` times into finer twigs that end in points, reaching up and
    out; `leaves` clumps of dry ochre leaves on the twigs; or snow on the branches
    """
    prop = Prop(seed)
    rng = prop.rng
    wood = snowy_wood_shade(prop, height) if snow else bark_shade(prop, DEAD_WOOD, height, 0.22)
    fork_z = height * 0.4
    fork = Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), fork_z))
    trunk = [Vector((0, 0, -0.05)), Vector((0, 0, 0.04)), fork * 0.5 + Vector((rng.uniform(-0.02, 0.02), 0, 0)), fork]
    prop.paint(prop.tube(trunk, [0.075, 0.056, 0.048, 0.042], 5), wood)
    reach = (height - fork_z) * 0.5
    tips = []

    def branch(start, direction, length, radius, level):
        segments = 2 if level < 2 else 1
        points = [start]
        d = direction
        for _ in range(segments):
            d = (d + Vector([rng.uniform(-0.25, 0.25) for _ in range(3)]) + Vector((0, 0, 0.08))).normalized()
            points.append(points[-1] + d * length / segments)
        last = level == levels
        radii = [radius * (1 - 0.3 * k / segments) for k in range(segments + 1)]
        if last:
            radii[-1] = 0.0
        prop.paint(prop.tube(points, radii, 4 if level == 0 else 3), wood)
        if last:
            tips.append((points[-1], d))
            return
        out = Vector((points[-1].x, points[-1].y, 0))
        out = out.normalized() if out.length > 1e-4 else around(rng.uniform(0, math.tau))
        turn = rng.uniform(0, math.tau)
        # the leader carries on, a side twig forks off; on the big branches another one halfway
        branch(points[-1] - d * radii[-1], (tilt(d, rng.uniform(0.1, 0.3), turn) + out * 0.15).normalized(),
               length * rng.uniform(0.62, 0.75), radii[-1] * 0.95, level + 1)
        branch(points[-1] - d * radii[-1], (tilt(d, rng.uniform(0.5, 0.8), turn + math.pi) + out * 0.2 + UP * 0.1).normalized(),
               length * rng.uniform(0.5, 0.65), radii[-1] * 0.8, level + 1)
        if level == 0:
            branch(points[1], (tilt(d, rng.uniform(0.6, 0.9), turn + math.pi / 2) + out * 0.25).normalized(),
                   length * 0.6, radii[1] * 0.75, level + 1)

    turn = rng.uniform(0, math.tau)
    for k in range(mains):
        direction = tilt(UP, rng.uniform(0.45, 0.7), turn + math.tau * (k + rng.uniform(-0.15, 0.15)) / mains)
        branch(fork - Vector((0, 0, 0.03)), direction, reach * rng.uniform(0.85, 1.05), 0.038, 0)

    if leaves:
        ochre = foliage_shade(prop, Vector((0, 0, (fork_z + height) / 2)), height * 0.5, (height - fork_z) / 2,
                              OCHRE, rgb('#7e8a3a'), 0.12)
        chosen = sorted(tips, key=lambda t: rng.random())[:leaves]
        for k, (tip, d) in enumerate(chosen):
            big = k < 3
            r = rng.uniform(0.08, 0.1) if big else rng.uniform(0.055, 0.08)
            prop.paint(prop.lump(tip - d * r * 0.5, r, (1.2, 1.2, 0.6), ROUND if big else ROUGH, 0.4 if big else 0.5), ochre)
    return prop.finish(name, mat, theater)


# --------------------------------------------------------------------------- bushes and rocks

def bush(name, mat, seed, radius, height, count, gradients, theater='temperate', snow=False):
    """A low shrub `radius` round and `height` high: a lump in the middle, `count` − 1 round it"""
    prop = Prop(seed)
    rng = prop.rng
    spots = [(Vector((0, 0, 0)), radius * 0.6, height)]
    turn = rng.uniform(0, math.tau)
    for i in range(count - 1):
        r = radius * rng.uniform(0.42, 0.55)
        at = around(turn + math.tau * (i + rng.uniform(-0.25, 0.25)) / (count - 1)) * (radius - r)
        spots.append((at, r, height * rng.uniform(0.6, 0.85)))
    for k, (at, r, top) in enumerate(spots):
        squash = clamp((top + 0.02) / (2 * r), 0.6, 1.15)
        centre = at + Vector((0, 0, top - r * squash))
        shade = scrub_shade(prop, Vector((0, 0, 0)), height, gradients[k % len(gradients)], snow)
        prop.paint(prop.lump(centre, r, (1, 1, squash), ROUND if k < 2 else ROUGH, 0.42), shade)
    return prop.finish(name, mat, theater)


def rocks(name, mat, seed, stones, theater='temperate', snow=False):
    """Boulders and stones: (x, y, half width x, half width y, height, points of the hull) each"""
    prop = Prop(seed)
    rng = prop.rng
    gradient_ = SNOW_STONE if snow else STONE
    top = max(s[4] for s in stones)
    for x, y, sx, sy, h, count in stones:
        faces = prop.boulder(Vector((x, y, 0)), (sx, sy), h, count, rng.uniform(0, math.tau))
        prop.paint(faces, stone_shade(prop, top, gradient_, snow))
    return prop.finish(name, mat, theater)


# --------------------------------------------------------------------------- build

def screen(right, back):
    """A spot on the ground by how far right and back on the screen it lies"""
    at = SCREEN_RIGHT * right + SCREEN_BACK * back
    return round(at.x, 3), round(at.y, 3)


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    mat = prop_material()
    # temperate
    oak('Oak1', mat, 101, 1.3, 1.4, 0.5, 5, 4)
    oak('Oak2', mat, 202, 1.0, 1.3, 0.48, 4, 3, lean=(0.03, -0.02), light=0.04)
    oak('Oak3', mat, 303, 1.25, 1.05, 0.42, 5, 3, lean=(0.06, 0.04), stems=2, light=0.02)
    pines('Pine1', mat, 404, [(0, 0, 1.7, 0.3, 7, 6)])
    # like TREE10: the small one on the left, a little further back
    pines('Pine2', mat, 505, [(*screen(0.13, 0.0), 1.55, 0.29, 7, 6), (*screen(-0.3, 0.06), 0.9, 0.18, 5, 5)])
    bare_tree('Dead1', mat, 606, 1.2, 3, 3)
    bare_tree('Dead2', mat, 707, 1.15, 3, 3, leaves=8)
    bush('Bush1', mat, 808, 0.22, 0.28, 4, [SCRUB, SCRUB, SCRUB_BROWN])
    bush('Bush2', mat, 909, 0.26, 0.24, 4, [SCRUB_BROWN, SCRUB])
    bush('Bush3', mat, 1010, 0.16, 0.22, 3, [SCRUB_BROWN, SCRUB_BROWN, SCRUB])
    rocks('Rock1', mat, 1111, [(0.02, 0.0, 0.36, 0.28, 0.3, 15), (-0.24, 0.17, 0.16, 0.12, 0.17, 11),
                               (0.3, -0.2, 0.07, 0.06, 0.045, 8), (-0.12, -0.3, 0.06, 0.05, 0.035, 8),
                               (0.36, 0.14, 0.05, 0.04, 0.03, 7)])
    rocks('Rock2', mat, 1212, [(-0.05, 0.03, 0.22, 0.17, 0.22, 13), (0.17, -0.08, 0.13, 0.1, 0.12, 10),
                               (-0.2, -0.16, 0.05, 0.04, 0.03, 7)])
    rocks('Rock3', mat, 1313, [(0.0, 0.0, 0.12, 0.1, 0.12, 12), (0.12, 0.07, 0.07, 0.055, 0.07, 9),
                               (-0.1, 0.06, 0.04, 0.035, 0.025, 7)])
    # snow
    pines('SnowPine1', mat, 1414, [(0, 0, 1.8, 0.28, 8, 6)], 'snow', snow=(0.97, -0.15))
    pines('SnowPine2', mat, 1515, [(0, 0, 1.3, 0.38, 7, 7)], 'snow', snow=(0.6, 0.5))
    # like TREE10.SNO: the small one on the left in front, the bigger one behind it on the right
    pines('SnowPine3', mat, 1616, [(*screen(0.16, 0.1), 1.05, 0.22, 6, 5), (*screen(-0.2, -0.1), 0.75, 0.17, 5, 5)],
          'snow', snow=(0.92, 0.0))
    bare_tree('SnowDead1', mat, 1717, 1.15, 3, 3, 'snow', snow=True)
    bush('SnowBush1', mat, 1818, 0.24, 0.24, 4, [SNOW_TWIGS], 'snow', snow=True)
    rocks('SnowRock1', mat, 1919, [(0.0, 0.0, 0.3, 0.24, 0.32, 15), (0.26, 0.14, 0.12, 0.1, 0.14, 10),
                                   (-0.24, -0.2, 0.06, 0.05, 0.04, 8)], 'snow', snow=True)
    rocks('SnowRock2', mat, 2020, [(0.0, 0.0, 0.17, 0.14, 0.2, 12), (-0.15, 0.1, 0.08, 0.07, 0.09, 9)], 'snow', snow=True)
    return list(kit.collection().objects)


def report(objects):
    for obj in objects:
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print(f"variant {obj.name:10s} tris {tris:5d} radius {obj['radius']:.2f} height {obj['height']:.2f} "
              f"{obj['theater']}", flush=True)


def export():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in kit.collection().objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_apply=True,
                              export_lights=False, export_cameras=False, export_animations=False,
                              export_extras=True, export_vertex_color='ACTIVE')
    return {'path': OUT, 'bytes': os.path.getsize(OUT)}


# --------------------------------------------------------------------------- preview

GAME_PIXELS_PER_CELL = 48 / math.sqrt(2)
CAMERA = Vector((math.sin(math.radians(45)) * math.cos(math.radians(30)),
                 -math.cos(math.radians(45)) * math.cos(math.radians(30)),
                 math.sin(math.radians(30))))


def preview(out_dir):
    """
    Renders through the game's camera (orthographic, 30° down, from the front right) in
    its light (app/lib/game/battlefield.ts: a weak, pale sun from the front, 55° high, a
    dim sky; the ground as dark as the game draws it): every variant alone
    (tile_<name>.png, 160 px a cell, bushes and rocks 320) and each theater in a row with a soldier (E1) and
    the MCV (row_<theater>_<n>x.png, n times the game's scale)
    """
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.view_settings.view_transform = 'Standard'
    scene.render.film_transparent = False
    world = bpy.data.worlds.new('PreviewWorld')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.058, 0.067, 0.084, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
    sun = bpy.data.objects.new('PreviewSun', bpy.data.lights.new('PreviewSun', 'SUN'))
    sun.data.energy = 1.6
    sun.data.color = (1.0, 0.84, 0.6)
    sun.data.angle = math.radians(2)
    scene.collection.objects.link(sun)
    sun.rotation_euler = Vector((0, -math.cos(math.radians(55)), math.sin(math.radians(55)))).to_track_quat('Z', 'Y').to_euler()
    # the ground's albedo so it comes out lit about as the game's unlit ground shader draws it
    grounds = {}
    for theater, albedo in (('temperate', (0.141, 0.112, 0.086)), ('snow', (0.525, 0.74, 1.0))):
        bpy.ops.mesh.primitive_plane_add(size=60)
        ground = bpy.context.active_object
        ground.name = f'PreviewGround_{theater}'
        ground.data.materials.append(kit.material(f'PreviewGround_{theater}', albedo, 1.0))
        grounds[theater] = ground
    cam = bpy.data.objects.new('PreviewCamera', bpy.data.cameras.new('PreviewCamera'))
    cam.data.type = 'ORTHO'
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.rotation_euler = (-CAMERA).to_track_quat('-Z', 'Y').to_euler()
    os.makedirs(out_dir, exist_ok=True)

    variants = list(kit.collection().objects)
    before = set(bpy.data.objects)
    references = {}
    for ref in ('E1', 'MCV'):
        known = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(PROJECT, 'public', 'models', f'{ref}.glb'))
        references[ref] = [o for o in set(bpy.data.objects) - known]
        for o in references[ref]:
            if o.animation_data:
                o.animation_data.action = None
            if o.type == 'ARMATURE':
                o.data.pose_position = 'REST'
    scene.frame_set(1)
    extra = set(bpy.data.objects) - before

    def show(objects, theater):
        visible = set(objects) | {sun, cam, grounds[theater]}
        for o in bpy.data.objects:
            o.hide_render = o not in visible

    def shoot(path, target, width, height, pixels_per_cell):
        cam.location = target + CAMERA * 20
        cam.data.ortho_scale = max(width, height)
        scene.render.resolution_x = max(16, round(width * pixels_per_cell))
        scene.render.resolution_y = max(16, round(height * pixels_per_cell))
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)

    for obj in variants:
        show([obj], obj['theater'])
        if obj['height'] > 0.5:
            shoot(os.path.join(out_dir, f'tile_{obj.name}.png'), Vector((0, 0, 0.78)), 2.4, 2.4, 160)
        else:  # bushes and rocks twice as close
            shoot(os.path.join(out_dir, f'tile_{obj.name}.png'), Vector((0, 0, 0.12)), 1.2, 1.2, 320)

    up = CAMERA.cross(SCREEN_RIGHT).normalized()  # screen up
    for theater in ('temperate', 'snow'):
        row = [o for o in variants if o['theater'] == theater]
        x = 0.0
        placed = []
        for ref, radius in (('E1', 0.15), ('MCV', 0.8)):
            roots = [o for o in references[ref] if o.parent is None]
            x += radius
            for o in roots:
                o.location = SCREEN_RIGHT * x
            placed += references[ref]
            x += radius + 0.3
        for obj in row:
            x += obj['radius']
            obj.location = SCREEN_RIGHT * x
            placed.append(obj)
            x += obj['radius'] + 0.3
        show(placed, theater)
        top = max(o['height'] for o in row)
        bottom_v = -1.0
        top_v = top * math.cos(math.radians(30)) + 0.5
        target = SCREEN_RIGHT * (x / 2) + up * ((top_v + bottom_v) / 2) + Vector((0, 0, 0))
        for scale in (1, 2):
            shoot(os.path.join(out_dir, f'row_{theater}_{scale}x.png'), target, x + 0.4, top_v - bottom_v,
                  GAME_PIXELS_PER_CELL * scale)
        for obj in row:
            obj.location = (0, 0, 0)
    for o in extra:
        bpy.data.objects.remove(o, do_unlink=True)


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    report(build())
    print('export', export(), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        preview(args[args.index('--preview') + 1])


if __name__ == '__main__' and bpy.app.background:
    main()
