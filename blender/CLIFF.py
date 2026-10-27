"""
Tiberian Fallout – cliff rock, after Tiberian Sun's cliffs (help/img_2.png).

A cliff there is a wall of grey rock in upright columns: pillars of different widths
and heights, standing a little apart with dark clefts between them, lit pale grey on
top and on the faces towards the sun, with broken rock at the foot.

The terrain (app/lib/game/terrain.ts) keeps its heights on the cells' corners; a cell
whose corners differ is rock, a whole cell wide, one level (HEIGHT) high. The game puts
one of these pieces on every rock cell, by which of its corners are up:

    Straight0 … Straight3   two corners side by side: the cliff runs straight across
    Cut0 … Cut2             three: the cliff runs diagonally across the cell (a
                            plateau's rounded corner, a slanting side)
    Foot0 … Foot2           one: below where a diagonal cliff meets the next

Frames (Blender, Z up; the game's x is X, its z is −Y): the cell from −0.5 to 0.5 round
the origin, Z = 0 the lower level, HEIGHT the upper one.
    Straight: the corners up on +Y; the cliff falls towards −Y.
    Cut:      the corner down at (+0.5, −0.5); the rim runs from (−0.5, −0.5) to (0.5, 0.5).
    Foot:     the corner up at (−0.5, +0.5).

The ground under a piece slopes between its corners (the game's mesh); the columns
stand on that slope, their tops level with the plateau at the rim, where low stones
lie half sunk in the ground so the rock runs out into it. The pieces reach a little
past their cell so neighbours overlap without gaps. One material, Rock; the shade of
the stone is in the vertex colours.

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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import GAPILE as kit  # noqa: E402 – the helpers of the barracks script

kit.COLLECTION = 'Cliff'
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(PROJECT, 'public', 'models', 'CLIFF.glb')
BLEND = os.path.join(HERE, 'CLIFF.blend')

HEIGHT = 1.25                    # one level (app/lib/game/terrain.ts LEVEL_HEIGHT)
OVERLAP = 0.1                   # how far a piece's columns reach past its cell
SIDES = 6                       # sides of a pillar
SEGMENTS = 4                    # rings up a pillar

# vertex colours are linear
ROCK_LIGHT = Vector(kit.srgb('#d2d2d0'))
ROCK_DARK = Vector(kit.srgb('#303236'))
SCREE = Vector(kit.srgb('#7a7064'))
GRAVEL = Vector(kit.srgb('#8a857c'))


def rock_material():
    mat = kit.material('Rock', (1, 1, 1), 0.95)
    nodes = mat.node_tree.nodes
    attribute = nodes.new('ShaderNodeVertexColor')
    attribute.layer_name = 'Col'
    mat.node_tree.links.new(attribute.outputs['Color'], nodes['Principled BSDF'].inputs['Base Color'])
    return mat


class Rock:
    """A bmesh with a colour per face corner, filled with pillars and boulders"""

    def __init__(self, seed):
        self.bm = bmesh.new()
        self.colour = self.bm.loops.layers.color.new('Col')
        self.rng = random.Random(seed)
        # the wall being built: a point on its rim and how far out its foot is
        self.rim = Vector()
        self.reach = 1.0

    def paint(self, face, shade):
        for loop in face.loops:
            loop[self.colour] = (*shade, 1)

    def shade_of(self, point, tint, out):
        """Lighter higher up and further out of the wall; the clefts deep in are dark"""
        up = max(0.0, min(1.0, point.z / HEIGHT))
        # how far the rock stands out of the wall at its height
        outward = max(0.0, min(1.0, ((point - self.rim).dot(out) - (1 - up) * self.reach + 0.12) * 3))
        light = 0.3 + 0.4 * up ** 0.7 + 0.35 * outward
        return ROCK_DARK.lerp(ROCK_LIGHT, max(0.0, min(1.0, light * tint)))

    def pillar(self, bottom, top, radius, out, tint=1.0):
        """
        An upright column of rock from `bottom` to `top`: a rough prism that breaks into
        offset blocks on the way up, with a slanted, chipped top
        """
        rng = self.rng
        axis = top - bottom
        side = Vector((-out.y, out.x, 0)).normalized()
        rings = []
        turn = rng.uniform(0, math.tau)
        shift = Vector()
        for k in range(SEGMENTS + 1):
            t = k / SEGMENTS
            if 0 < k < SEGMENTS and rng.random() < 0.5:
                # a break in the column: the block above stands off
                shift += side * rng.uniform(-0.05, 0.05) + out * rng.uniform(-0.05, 0.03)
            centre = bottom + axis * t + shift
            r = radius * (1.15 - 0.3 * t) * rng.uniform(0.9, 1.08)
            ring = []
            for i in range(SIDES):
                a = turn + math.tau * i / SIDES + rng.uniform(-0.25, 0.25)
                # flattened along the wall, so the columns stand close side by side
                d = side * math.cos(a) * 1.1 + out * math.sin(a) * 0.9
                ring.append(self.bm.verts.new(centre + d * r * rng.uniform(0.85, 1.1)))
            rings.append(ring)
        # the top: tilted, a little lower towards the outside
        tilt = rng.uniform(0.04, 0.12) * radius / 0.1
        for v in rings[-1]:
            v.co.z -= max(0.0, (v.co - top).dot(out)) * tilt * 4 + rng.uniform(0, 0.02)
        cap = self.bm.verts.new(top + shift + Vector((0, 0, rng.uniform(0.0, 0.03))) - out * radius * 0.2)
        for k in range(SEGMENTS):
            for i in range(SIDES):
                j = (i + 1) % SIDES
                face = self.bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
                mid = sum((v.co for v in face.verts), Vector()) / 4
                self.paint(face, self.shade_of(mid, tint, out))
        for i in range(SIDES):
            face = self.bm.faces.new((rings[-1][i], rings[-1][(i + 1) % SIDES], cap))
            self.paint(face, ROCK_LIGHT * min(1.0, 0.85 * tint))

    def boulder(self, centre, size, squash=0.7, colour=None, tint=1.0):
        """A broken lump of rock (a rough, flattened icosphere)"""
        result = bmesh.ops.create_icosphere(self.bm, subdivisions=1, radius=size)
        seed = self.rng.uniform(0, 100)
        for v in result['verts']:
            n = noise.noise(v.co * 4 + Vector((seed, 0, 0)))
            v.co *= 1 + 0.35 * n
            v.co.z *= squash
            v.co += centre
        for face in {f for v in result['verts'] for f in v.link_faces}:
            normal_up = max(0.0, face.normal.z)
            base = colour if colour is not None else ROCK_DARK.lerp(ROCK_LIGHT, 0.45 + 0.4 * normal_up)
            self.paint(face, base * tint)

    def wall(self, start, end, out, reach):
        """
        Columns along the rim from `start` to `end` (on the plateau's level), standing on
        the slope down to the foot `reach` further out along `out`: gathered into masses
        of rock that stand out, with recesses between them; broken rock at the foot,
        low stones sunk in the ground along the rim
        """
        rng = self.rng
        self.rim, self.reach = start.copy(), reach
        length = (end - start).length
        along = (end - start).normalized()
        masses = [(rng.uniform(0, length), rng.uniform(0.06, 0.2), rng.uniform(0.12, 0.3))
                  for _ in range(max(1, round(length * 2.5)))]

        def stands_out(d):
            return max(m[1] * math.exp(-((d - m[0]) / m[2]) ** 2) for m in masses)

        count = max(2, round(length / 0.15))
        for i in range(count):
            d = (i + rng.uniform(0.15, 0.85)) / count * length
            at = start + along * d
            forward = 0.06 + stands_out(d) + rng.uniform(-0.04, 0.04)
            # towards the ends the columns come down and in, so a wall that stops (at a
            # ramp, round a corner) breaks off in rubble, not a hard edge
            taper = min(1.0, min(d, length - d) / (2 * OVERLAP))
            radius = rng.uniform(0.08, 0.15) * (1 + forward) * (0.75 + 0.25 * taper)
            top = at + out * forward + Vector((0, 0, HEIGHT * (0.88 + 0.12 * taper) + rng.uniform(-0.12, 0.05) - forward * 0.4))
            foot = at + out * (reach + forward * 0.6 + rng.uniform(-0.05, 0.08)) + Vector((0, 0, -0.04))
            tint = rng.uniform(0.85, 1.1)
            self.pillar(foot, top, radius, out, tint)
            # a lower block in front of it now and then
            if rng.random() < 0.35:
                h = rng.uniform(0.25, 0.55) * HEIGHT
                base = foot + along * rng.uniform(-0.05, 0.05) + out * 0.04
                self.pillar(base, base - out * reach * h / HEIGHT + Vector((0, 0, h)), radius * rng.uniform(0.8, 1.1), out, tint * 0.95)
        # broken rock at the foot
        for _ in range(round(length * 3)):
            d = rng.uniform(0.0, length)
            size = rng.uniform(0.06, 0.12)
            at = start + along * d + out * (reach + stands_out(d) * 0.6 + rng.uniform(0.0, 0.25))
            self.boulder(at + Vector((0, 0, size * 0.1)), size, 0.55, SCREE * rng.uniform(0.6, 1.0))
        self.rim_stones(start, end, -out)

    def rim_stones(self, start, end, inward):
        """Low, flat stones half sunk in the plateau along the rim"""
        rng = self.rng
        length = (end - start).length
        for _ in range(round(length * 2)):
            at = start + (end - start) * rng.uniform(0.0, 1.0) + inward * rng.uniform(0.1, 0.4)
            size = rng.uniform(0.04, 0.08)
            # the ground is rounded off at the rim (Terrain.heightAt): sunk in deep
            self.boulder(at + Vector((0, 0, HEIGHT - size * 0.5)), size, 0.35, GRAVEL * rng.uniform(0.75, 1.1))

    def fan(self, corner, directions, reach, count=4):
        """Columns from a corner on the rim down into the cell, fanning out between two directions"""
        rng = self.rng
        a0 = math.atan2(directions[0].y, directions[0].x)
        a1 = math.atan2(directions[1].y, directions[1].x)
        if a1 < a0:
            a1 += math.tau
        self.rim, self.reach = corner.copy(), reach
        for i in range(count):
            a = a0 + (a1 - a0) * (i + rng.uniform(0.3, 0.7)) / count
            out = Vector((math.cos(a), math.sin(a), 0))
            top = corner + out * rng.uniform(0.04, 0.12) + Vector((0, 0, HEIGHT * rng.uniform(0.7, 0.95)))
            foot = corner + out * (reach + rng.uniform(-0.05, 0.1)) + Vector((0, 0, -0.04))
            self.pillar(foot, top, rng.uniform(0.09, 0.13), out, rng.uniform(0.85, 1.05))
            for _ in range(2):
                size = rng.uniform(0.05, 0.1)
                at = corner + out * (reach + rng.uniform(0.0, 0.25))
                self.boulder(at + Vector((0, 0, size * 0.1)), size, 0.55, SCREE * rng.uniform(0.6, 1.0))

    def finish(self, name, mat):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
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


def straight(name, seed, mat):
    """The rim along +Y, the cliff falling to −Y across the whole cell"""
    rock = Rock(seed)
    rock.wall(Vector((-0.5 - OVERLAP, 0.5, 0)), Vector((0.5 + OVERLAP, 0.5, 0)), Vector((0, -1, 0)), 0.95)
    return rock.finish(name, mat)


def cut(name, seed, mat):
    """The rim along the diagonal from (−0.5, −0.5) to (0.5, 0.5), the cliff falling to the corner (0.5, −0.5)"""
    rock = Rock(seed)
    along = Vector((1, 1, 0)).normalized()
    rock.wall(Vector((-0.5, -0.5, 0)) - along * OVERLAP, Vector((0.5, 0.5, 0)) + along * OVERLAP,
              Vector((1, -1, 0)).normalized(), 0.68)
    return rock.finish(name, mat)


def foot(name, seed, mat):
    """Columns from the corner up at (−0.5, 0.5) down into the cell"""
    rock = Rock(seed)
    rock.fan(Vector((-0.5, 0.5, 0)), (Vector((0.3, -1, 0)).normalized(), Vector((1, -0.3, 0)).normalized()), 0.6, 3)
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
