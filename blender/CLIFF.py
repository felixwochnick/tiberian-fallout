"""
Tiberian Fallout – cliff rock, after Tiberian Sun's temperate cliffs.

A cliff there is a sheer wall of dark grey rock, near black in its clefts: upright
columns and slabs of different widths and heights, some broken into blocks, leaning a
little, lit pale grey on their tops and on the edges towards the sun, olive in places.
Its top is a ragged rim of rock teeth and broken blocks with the plateau's soil between
them; at its foot rubble and boulders spill a little onto the ground below.

The terrain (app/lib/game/terrain.ts) keeps its heights on the cells' corners; a cell
whose corners differ is rock, a whole cell wide, one level (HEIGHT) high. The game puts
one of these pieces on every rock cell, by which of its corners are up
(Battlefield.placeCliffs: instanced, scaled up or down by the levels the cell climbs):

    Straight0 … Straight3   two corners side by side: the cliff runs straight across
    Cut0 … Cut2             three: the cliff runs diagonally across the cell (a
                            plateau's rounded corner, a slanting side)
    Foot0 … Foot2           one: below where a diagonal cliff meets the next

Frames (Blender, Z up; the game's x is X, its z is −Y): the cell from −0.5 to 0.5 round
the origin, Z = 0 the lower level, HEIGHT the upper one.
    Straight: the corners up on +Y; the cliff falls towards −Y.
    Cut:      the corner down at (+0.5, −0.5); the rim runs from (−0.5, −0.5) to (0.5, 0.5).
    Foot:     the corner up at (−0.5, +0.5).

The ground under a piece slopes between its corners (the game's mesh, which draws it
as rock too). Every piece is built the same way across that slope (Frame: along its
rim, out towards its foot): the face, a row of columns and slabs with ridges and
grooves down their fronts and broken-off top edges, standing where the slope has
fallen most of the way (FACE_AT), as high as the cliff or lower; behind it, over the
slope up to a little past the rim, broken blocks about as high as the plateau, so the
rim is a band of rock teeth and ledges rather than an edge; boulders at the foot and a
few on the rim. So the face meets its neighbours' faces on the cells' sides, and the
pieces reach a little past their cell (OVERLAP) so neighbours overlap without gaps.

One material, Rock; the shade of the stone is in the vertex colours, written as they
look (sRGB: the byte colour layer keeps sRGB, the export turns it linear): a shade per
column, darker towards the foot, the tops and the top edges pale, the clefts dark (the
rock and the ground round each corner are sounded out with rays).

Run headless:

    Blender -b --factory-startup --python blender/CLIFF.py
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

kit.COLLECTION = 'Cliff'
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'CLIFF.glb')
BLEND = os.path.join(HERE, 'CLIFF.blend')

HEIGHT = 1.25                   # one level (app/lib/game/terrain.ts LEVEL_HEIGHT)
OVERLAP = 0.12                  # how far a piece's rock reaches past its cell's sides
FACE_AT = 0.84                  # where the face stands: this share of the way from the rim to the foot
SMOOTH = 0.35                   # how far the game rounds off the ground's folds (terrain.ts SMOOTH_RADIUS)


def shade(hex_colour):
    """'#rrggbb' as it looks (sRGB, 0 … 1)"""
    h = hex_colour.lstrip('#')
    return Vector(tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))


# the stone of the columns: grey, warm grey, olive, cool grey, dark (a little cool, as the
# game's sun is warm)
STONE = [shade('#8e8f93'), shade('#969087'), shade('#888e70'), shade('#878d98'), shade('#75777b')]
LEDGE = shade('#dcdfe0')        # tops and ledges, lit pale grey
SOIL = shade('#8a6a48')         # the plateau's soil caught on the ledges of the rim
SCREE = shade('#8a8680')        # broken rock at the foot

# the clefts: how far the rays look for rock or ground round a corner, how dark it gets at most
SOUNDING = 0.4
DARKEST = 0.1


def hemisphere(count=16):
    """Directions over a hemisphere round +Z, denser towards the top (cosine-weighted)"""
    directions = []
    for i in range(count):
        u = (i + 0.5) / count
        r = math.sqrt(u)
        a = i * 2.399963
        directions.append(Vector((r * math.cos(a), r * math.sin(a), math.sqrt(1 - u))))
    return directions


RAYS = hemisphere()


def rock_material():
    mat = kit.material('Rock', (1, 1, 1), 0.95)
    nodes = mat.node_tree.nodes
    attribute = nodes.new('ShaderNodeVertexColor')
    attribute.layer_name = 'Col'
    mat.node_tree.links.new(attribute.outputs['Color'], nodes['Principled BSDF'].inputs['Base Color'])
    return mat


class Frame:
    """
    How a piece's cliff runs: its rim through `rim` along `along`, falling out (along
    turned clockwise) to its foot `reach` further; `width(d)` how far the cell reaches
    to either side along the rim at d out
    """

    def __init__(self, rim, along, reach, width):
        self.rim = rim
        self.along = along.normalized()
        self.out = Vector((self.along.y, -self.along.x, 0))
        self.reach = reach
        self.width = width

    def at(self, t, d, z=0.0):
        return self.rim + self.along * t + self.out * d + Vector((0, 0, z))

    def span(self, d):
        w = self.width(d) + OVERLAP
        return -w, w

    def plane(self, d):
        """Height of the plain slope at d out, as a share of HEIGHT"""
        return min(1.0, max(0.0, 1 - d / self.reach))

    def ground(self, d):
        """Height of the ground at d out, its folds rounded off like the game's (Terrain.heightAt)"""
        total = weights = 0.0
        for i in range(-2, 3):
            for j in range(-2, 3):
                w = (3 - abs(i)) * (3 - abs(j))
                total += w * self.plane(d + (i * self.out.x + j * self.out.y) * SMOOTH / 2)
                weights += w
        return HEIGHT * total / weights


class Rock:
    """A bmesh of blocks and boulders, shaded at the end (finish)"""

    def __init__(self, seed):
        self.bm = bmesh.new()
        self.colour = self.bm.loops.layers.color.new('Col')
        self.rng = random.Random(seed)
        self.seed = self.rng.uniform(0, 100)
        # per face: the shade of its sides and of its top; the corners on the blocks' top edges
        self.shades = {}
        self.edges = set()
        self.frame = None

    def stone(self, t):
        """A column's stone: patches of olive, warm and cool grey along the cliff, every column a little different"""
        rng = self.rng
        n = noise.noise(Vector((t * 1.7 + self.seed, self.seed * 0.3, 0.5)))
        if n > 0.15:
            base = STONE[2]
        elif n < -0.3:
            base = STONE[1]
        else:
            base = STONE[rng.choice((0, 0, 3, 4))]
        return base.lerp(rng.choice(STONE), rng.uniform(0.0, 0.35)) * rng.uniform(0.88, 1.08)

    def outline(self, e1, half1, half2, sides=5, flutes=0):
        """
        The corners of a block's cross-section round its middle, counter-clockwise (half
        widths `half1` along `e1`, `half2` across): `sides` corners all round, or with
        `flutes` a front (towards e1 turned clockwise: out of the cliff) of so many
        ridges and grooves between them, and a plain back of `sides` corners
        """
        rng = self.rng
        e1 = Vector((e1.x, e1.y, 0)).normalized()
        e2 = Vector((-e1.y, e1.x, 0))
        corners = []
        if flutes:
            for i in range(sides):
                corners.append((math.pi * (i + 0.5 + rng.uniform(-0.2, 0.2)) / sides, rng.uniform(0.9, 1.05)))
            for i in range(flutes):
                ridge = i % 2 == 0
                corners.append((math.pi * (1 + (i + 0.5 + rng.uniform(-0.15, 0.15)) / flutes),
                                rng.uniform(0.95, 1.1) if ridge else rng.uniform(0.62, 0.8)))
        else:
            turn = rng.uniform(0, math.tau)
            for i in range(sides):
                corners.append((turn + math.tau * (i + rng.uniform(-0.3, 0.3)) / sides, rng.uniform(0.84, 1.12)))
        return [e1 * (math.cos(a) * half1 * r) + e2 * (math.sin(a) * half2 * r) for a, r in corners]

    def block(self, centre, outline, bottom, top, side_shade, top_shade, lean=None, tilt=None, taper=1.0, waists=(),
              steps=0.0, bevel=0.0):
        """
        An upright block of rock: a rough prism of the cross-section `outline` round
        `centre` from `bottom` up to `top`, its upper end shifted by `lean` and narrower
        by `taper`, its top falling by `tilt` (a horizontal gradient) and broken in two.
        `waists`: the shares of the way up of rings where it bends a little or (by the
        chance `steps`) steps in, a ledge; `bevel`: how high the edge round its top is
        broken off, so it catches the light
        """
        rng = self.rng
        bm = self.bm
        sides = len(outline)
        lean = lean if lean is not None else Vector()
        tilt = tilt if tilt is not None else Vector()
        middle = Vector((centre.x, centre.y, 0))
        height = max(top - bottom, 1e-3)

        def ring(z, scale, wobble=0.0, drop=0.0):
            f = (z - bottom) / height
            verts = []
            for p in outline:
                q = p * scale * (1 + (taper - 1) * f)
                at = middle + lean * f + q + Vector((0, 0, z))
                if f >= 1 - 1e-6 or drop:
                    at.z += tilt.dot(q) - drop - rng.uniform(0.0, 0.02)
                verts.append(bm.verts.new(at + Vector((rng.uniform(-wobble, wobble), rng.uniform(-wobble, wobble), 0))))
            return verts

        rings = [ring(bottom, 1.0)]
        scale = 1.0
        for f in waists:
            z = bottom + height * f
            if rng.random() < steps:
                rings.append(ring(z, scale, 0.008))
                scale *= rng.uniform(0.72, 0.86)
                rings.append(ring(z + rng.uniform(0.03, 0.06), scale, 0.008))
            else:
                rings.append(ring(z + rng.uniform(-0.03, 0.03), scale * rng.uniform(0.97, 1.05), 0.015))
        if bevel:
            shoulder = ring(top, scale, 0.0, bevel)
            rings.append(shoulder)
            self.edges.update(shoulder)
            scale *= rng.uniform(0.72, 0.84)
        head = ring(top, scale)
        rings.append(head)
        faces = []
        for lower, upper in zip(rings, rings[1:]):
            for i in range(sides):
                j = (i + 1) % sides
                faces.append(bm.faces.new((lower[i], lower[j], upper[j], upper[i])))
        # the top in two pieces meeting in a point near the middle, a little out of line
        apex = bm.verts.new(middle + lean + sum(outline, Vector()) / sides * taper * scale * 0.5
                            + Vector((0, 0, top + rng.uniform(-0.025, 0.02))))
        a = rng.randrange(sides)
        b = (a + sides // 2 + rng.choice((0, 0, 1))) % sides
        for start, stop in ((a, b), (b, a)):
            faces.append(bm.faces.new([apex] + [head[(start + k) % sides] for k in range((stop - start) % sides + 1)]))
        for face in faces:
            self.shades[face] = (side_shade, top_shade)
        self.edges.update(head)
        return head

    def boulder(self, centre, size, squash, colour, points=8):
        """A broken lump of rock: the hull round a few points on a flattened ball"""
        rng = self.rng
        verts = []
        for i in range(points):
            # spread over the ball (a spiral), each pushed in or out a little
            u = (i + 0.5) / points
            z = 1 - 2 * u
            r = math.sqrt(1 - z * z)
            a = i * 2.399963 + rng.uniform(-0.4, 0.4)
            p = Vector((r * math.cos(a), r * math.sin(a), z)) * size * rng.uniform(0.75, 1.15)
            p.z *= squash
            verts.append(self.bm.verts.new(centre + p))
        hull = bmesh.ops.convex_hull(self.bm, input=verts)
        # points the hull swallowed
        bmesh.ops.delete(self.bm, geom=[v for v in hull['geom_interior'] if isinstance(v, bmesh.types.BMVert)], context='VERTS')
        faces = [f for f in hull['geom'] if isinstance(f, bmesh.types.BMFace)]
        bmesh.ops.recalc_face_normals(self.bm, faces=faces)
        for face in faces:
            self.shades[face] = (colour, colour.lerp(LEDGE, 0.45))

    def waists(self, height):
        """Rings up a block `height` high, more the higher it is"""
        rng = self.rng
        if height < HEIGHT * 0.6:
            return ()
        if height < HEIGHT * 0.9:
            return (rng.uniform(0.4, 0.6),)
        return (rng.uniform(0.3, 0.45), rng.uniform(0.6, 0.75))

    def face(self, frame):
        """
        The face: columns and slabs side by side where the slope has fallen most of the
        way, of all widths, gathered into masses that stand out with recesses between
        them; some as high as the cliff or higher (teeth), some lower with the blocks of
        the rim showing over them, some broken in two; clefts between them
        """
        rng = self.rng
        self.frame = frame
        at = frame.reach * FACE_AT
        t0, t1 = frame.span(at)
        t = t0 - rng.uniform(0.0, 0.08)
        columns = []
        while t < t1:
            kind = rng.random()
            if kind < 0.3:
                width = rng.uniform(0.28, 0.44)         # a wide slab
            elif kind < 0.38:
                width = rng.uniform(0.07, 0.1)          # a splinter
            else:
                width = rng.uniform(0.14, 0.27)
            mid = t + width / 2
            # masses standing out of the face, recesses between them, every column out or back a little
            mass = max(-1.0, min(1.0, 2 * noise.noise(Vector((mid * 1.9 + self.seed, 0.7, 0.2)))))
            front = at + 0.07 * mass + rng.uniform(-0.03, 0.03)
            recess = rng.random() < 0.2
            if recess:
                # set back between its neighbours: a deep cleft
                front -= rng.uniform(0.07, 0.14)
            depth = rng.uniform(0.16, 0.28)
            # the masses that stand out stand higher; a tooth over the rim now and then, a low one
            top = HEIGHT * (0.87 + 0.12 * mass + rng.uniform(-0.08, 0.05))
            kind = rng.random()
            if kind < 0.2:
                top += HEIGHT * rng.uniform(0.06, 0.14)
            elif kind > 0.85:
                top = HEIGHT * rng.uniform(0.45, 0.7)   # low: the rim's blocks show over it
            top = min(top, HEIGHT * 1.1)
            if mid < t0 + 0.1 or mid > t1 - 0.1:
                top = min(top, HEIGHT * rng.uniform(0.75, 0.95))
            centre = frame.at(mid, front - depth / 2)
            # leaning back into the cliff a little, and to the side
            lean = -frame.out * rng.uniform(0.0, 0.07) + frame.along * rng.uniform(-0.07, 0.07)
            tilt = frame.out * -rng.uniform(0.05, 0.5) + frame.along * rng.uniform(-0.2, 0.2)
            stone = self.stone(mid) * (0.8 if recess else 1.0)
            ledge = LEDGE.lerp(SOIL, rng.uniform(0.0, 0.2)) * rng.uniform(0.9, 1.03)
            bevel = rng.uniform(0.025, 0.05)
            # the wider, the more ridges and grooves down its front
            if width < 0.12:
                outline = self.outline(frame.along, width / 2, depth / 2, rng.choice((4, 5)))
            elif width < 0.27:
                outline = self.outline(frame.along, width / 2, depth / 2, 2, rng.choice((3, 4)))
            else:
                outline = self.outline(frame.along, width / 2, depth / 2, 3, rng.choice((5, 6)))
            bottom = -0.06
            if rng.random() < 0.35 and top > HEIGHT * 0.6:
                # broken: a lower block and a narrower one set back on it
                split = HEIGHT * rng.uniform(0.3, 0.55)
                self.block(centre, outline, bottom, split, stone, ledge, lean * (split / top), tilt * 0.5,
                           rng.uniform(0.92, 1.0), self.waists(split - bottom), 0.5, bevel * 0.7)
                upper = centre - frame.out * rng.uniform(0.01, 0.05) + frame.along * rng.uniform(-0.02, 0.02) + lean * (split / top)
                narrower = rng.uniform(0.8, 0.95)
                self.block(upper, [p * narrower for p in outline], split - 0.08, top, stone * rng.uniform(0.92, 1.06), ledge,
                           lean * (1 - split / top), tilt, rng.uniform(0.85, 1.0), self.waists(top - split + 0.08), 0.5, bevel)
            else:
                self.block(centre, outline, bottom, top, stone, ledge, lean, tilt, rng.uniform(0.8, 1.0),
                           self.waists(top - bottom), 0.5, bevel)
            columns.append((mid, front - depth / 2, min(width, depth) / 2))
            t += width * rng.uniform(0.8, 0.95)
        return columns

    def rim(self, frame, taken):
        """
        Behind the face up to a little past the rim: broken blocks about as high as the
        plateau, close together with clefts between them, some a little higher (teeth),
        some lower with soil on them; lower and more ragged towards the face
        """
        rng = self.rng
        at = frame.reach * FACE_AT
        near, far = -0.13, at - 0.12
        placed = list(taken)
        for count, small, large in ((200, 0.09, 0.17), (140, 0.05, 0.09)):
            for _ in range(count):
                d = rng.uniform(near, far)
                t0, t1 = frame.span(d)
                t = rng.uniform(t0 + 0.02, t1 - 0.02)
                r = rng.uniform(small, large)
                if any((t - pt) ** 2 + (d - pd) ** 2 < (0.8 * (r + pr)) ** 2 for pt, pd, pr in placed):
                    continue
                placed.append((t, d, r))
                front = (d - near) / (far - near)
                top = HEIGHT * (rng.uniform(0.95, 1.04) + (0.07 if rng.random() < 0.18 else 0.0))
                top -= HEIGHT * front * rng.uniform(0.0, 0.12)
                if d < 0:
                    # past the rim on the plateau: lower, half in the ground
                    top = frame.ground(d) + rng.uniform(0.0, 0.08)
                bottom = max(-0.06, frame.ground(d + r) - 0.3)
                angle = rng.uniform(-0.6, 0.6)
                e1 = frame.along * math.cos(angle) + frame.out * math.sin(angle)
                aspect = rng.uniform(0.75, 1.3)
                tilt = Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0)) - frame.out * rng.uniform(0.0, 0.25)
                lean = Vector((rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02), 0))
                stone = self.stone(t) * rng.uniform(0.95, 1.05)
                # soil on the ledges, more on the lower ones and past the rim
                soil = min(1.0, rng.uniform(0.0, 0.3) + max(0.0, (HEIGHT - top) * 2.0) + (0.3 if d < 0 else 0.0))
                ledge = LEDGE.lerp(SOIL, soil) * rng.uniform(0.88, 1.03)
                self.block(frame.at(t, d), self.outline(e1, r * aspect, r / aspect, rng.choice((4, 5, 5, 6))),
                           bottom, top, stone, ledge, lean, tilt, rng.uniform(0.85, 1.0))
        return placed

    def rubble(self, frame):
        """Boulders against the foot of the face, a few smaller stones spilling onto the ground, a few loose on the rim"""
        rng = self.rng
        at = frame.reach * FACE_AT
        t0, t1 = frame.span(at)
        count = max(2, round((t1 - t0) * 3))
        for i in range(count):
            t = t0 + (t1 - t0) * (i + rng.uniform(0.1, 0.9)) / count
            d = at + rng.uniform(0.0, 0.09)
            size = rng.uniform(0.06, 0.12)
            self.boulder(frame.at(t, d, frame.ground(d) + size * rng.uniform(0.0, 0.2)), size, rng.uniform(0.65, 0.9),
                         SCREE.lerp(rng.choice(STONE), rng.uniform(0.0, 0.6)) * rng.uniform(0.85, 1.05))
        t0, t1 = frame.span(frame.reach)
        for _ in range(max(1, round((t1 - t0) * 1.5))):
            t = rng.uniform(t0, t1)
            d = rng.uniform(at + 0.1, frame.reach + 0.1)
            size = rng.uniform(0.035, 0.06)
            self.boulder(frame.at(t, d, frame.ground(d) + size * 0.1), size, rng.uniform(0.6, 0.8),
                         SCREE * rng.uniform(0.8, 1.0))
        t0, t1 = frame.span(0.0)
        for _ in range(rng.choice((1, 2, 2))):
            t = rng.uniform(t0 + 0.1, t1 - 0.1) if t1 - t0 > 0.3 else 0.0
            d = rng.uniform(-0.18, 0.15)
            size = rng.uniform(0.045, 0.085)
            top = HEIGHT * 1.02 if d > -0.05 else frame.ground(d)
            self.boulder(frame.at(t, d, top + size * 0.15), size, rng.uniform(0.5, 0.7),
                         rng.choice(STONE) * rng.uniform(1.0, 1.15))

    def cliff(self, frame):
        columns = self.face(frame)
        self.rim(frame, columns)
        self.rubble(frame)

    def sounder(self):
        """The rock and the ground round it, to sound the clefts out with rays"""
        frame = self.frame
        coords = [v.co.copy() for v in self.bm.verts]
        index = {v: i for i, v in enumerate(self.bm.verts)}
        polygons = [[index[v] for v in f.verts] for f in self.bm.faces]
        steps = 40
        first = len(coords)
        for i in range(steps + 1):
            for j in range(steps + 1):
                t = -1.2 + 2.4 * i / steps
                d = -0.6 + (frame.reach + 1.0) * j / steps
                coords.append(frame.at(t, d, frame.ground(d)))
        for i in range(steps):
            for j in range(steps):
                a = first + i * (steps + 1) + j
                polygons.append([a, a + steps + 1, a + steps + 2, a + 1])
        return BVHTree.FromPolygons(coords, polygons)

    def finish(self, name, mat):
        """Shades every corner (its face's stone, darker towards the foot, the top edges pale, the clefts dark) and makes the object"""
        tree = self.sounder()
        for face in self.bm.faces:
            side, top = self.shades[face]
            normal = face.normal
            centre = face.calc_center_median()
            ahead = Vector((1, 0, 0)) if abs(normal.x) < 0.9 else Vector((0, 1, 0))
            u = normal.cross(ahead).normalized()
            v = normal.cross(u)
            upward = normal.z > 0.55
            rng = self.rng
            jitter = rng.uniform(0.86, 1.1)
            if not upward:
                # the fronts of the columns lighter, their sides in the clefts darker; streaks of soil
                facing = normal.dot(self.frame.out)
                jitter *= 1.0 + 0.2 * facing if facing > 0 else 1.0 + 0.3 * facing
                if rng.random() < 0.15:
                    side = side.lerp(SOIL, rng.uniform(0.3, 0.5))
            for loop in face.loops:
                co = loop.vert.co
                if upward:
                    colour = top * jitter
                else:
                    up = max(0.0, min(1.0, co.z / HEIGHT))
                    colour = side * (0.55 + 0.55 * up ** 0.85) * jitter
                    if loop.vert in self.edges:
                        colour = colour.lerp(top, 0.4)
                # the clefts: how much rock and ground there is round the corner
                origin = co + normal * 0.004 + (centre - co) * 0.06
                hidden = 0.0
                for ray in RAYS:
                    direction = u * ray.x + v * ray.y + normal * ray.z
                    hit, _, _, distance = tree.ray_cast(origin, direction, SOUNDING)
                    if hit is not None:
                        hidden += 1 - distance / SOUNDING
                open_ = 1 - hidden / len(RAYS)
                colour = colour * (DARKEST + (1 - DARKEST) * open_ ** 1.8)
                loop[self.colour] = (*(max(0.0, min(1.0, c)) for c in colour), 1)
        mesh = bpy.data.meshes.new(name)
        self.bm.to_mesh(mesh)
        self.bm.free()
        mesh.materials.append(mat)
        # only the stone's shades (the export would put any other colour layer first)
        for attribute in [a for a in mesh.color_attributes if a.name != 'Col']:
            mesh.color_attributes.remove(attribute)
        mesh.color_attributes.active_color = mesh.color_attributes['Col']
        mesh.color_attributes.render_color_index = mesh.color_attributes.active_color_index
        for poly in mesh.polygons:
            poly.use_smooth = False
        obj = bpy.data.objects.new(name, mesh)
        kit.collection().objects.link(obj)
        return obj


DIAGONAL = math.sqrt(0.5)


def straight(name, seed, mat):
    """The rim along +Y, the cliff falling to −Y across the whole cell"""
    rock = Rock(seed)
    rock.cliff(Frame(Vector((0, 0.5, 0)), Vector((1, 0, 0)), 1.0, lambda d: 0.5))
    return rock.finish(name, mat)


def cut(name, seed, mat):
    """The rim along the diagonal from (−0.5, −0.5) to (0.5, 0.5), the cliff falling to the corner (0.5, −0.5)"""
    rock = Rock(seed)
    rock.cliff(Frame(Vector((0, 0, 0)), Vector((1, 1, 0)), DIAGONAL, lambda d: max(0.0, DIAGONAL - abs(d))))
    return rock.finish(name, mat)


def foot(name, seed, mat):
    """The corner up at (−0.5, 0.5), the slope falling from it to the diagonal through the others"""
    rock = Rock(seed)
    rock.cliff(Frame(Vector((-0.5, 0.5, 0)), Vector((1, 1, 0)), DIAGONAL, lambda d: max(0.0, d)))
    return rock.finish(name, mat)


def build():
    for obj in list(kit.collection().objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    mat = rock_material()
    root = kit.empty('Cliff')
    pieces = [straight(f'Straight{i}', 11 + i * 17, mat) for i in range(4)]
    pieces += [cut(f'Cut{i}', 301 + i * 13, mat) for i in range(3)]
    pieces += [foot(f'Foot{i}', 701 + i * 19, mat) for i in range(3)]
    for piece in pieces:
        kit.parent(piece, root)
    return len(pieces)


def export():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in kit.collection().objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_apply=True,
                              export_lights=False, export_cameras=False, export_animations=False,
                              export_vertex_color='ACTIVE')
    return {'path': OUT, 'bytes': os.path.getsize(OUT)}


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    print('pieces', build(), flush=True)
    print('export', export(), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)


if __name__ == '__main__' and bpy.app.background:
    main()
