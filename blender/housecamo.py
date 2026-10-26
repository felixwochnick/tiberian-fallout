"""
Tiberian Fallout – camouflage in shades of the house colour (E1's fatigues, the MCV's
and the harvester's bodies).

The faces of a mesh get one of a few materials, by the blotch of a noise field their
centre lies in. Each material is a shade of the house colour: its lightness and
saturation factors (HLS) go into the GLB as material extras (remapLightness,
remapSaturation), and the game derives the same shades from the player's colour
(applyHouseColour in app/lib/game/models.ts): gold gives a brown-yellow pattern, red
a red one, blue a blue one.
"""
import colorsys

import bmesh
from mathutils import Vector, noise

import GAPILE as kit

HOUSE_COLOUR = '#d8b43a'  # GDI gold, the colour of the previews
# from the bottom layer up: name, lightness and saturation factor, the noise threshold
# of the blotches (None: the ground)
CAMO = (
    ('CamoBase', 0.55, 0.6, None),
    ('CamoDark', 0.3, 0.55, 0.05),
    ('CamoLight', 0.85, 0.45, 0.15),
    ('CamoAccent', 1.0, 0.9, 0.2),
)


def shade(name, lightness, saturation, roughness=0.9):
    """A material in a shade of the house colour; the game recolours it (extras)."""
    rgb = [int(HOUSE_COLOUR[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    h, l, s = colorsys.rgb_to_hls(*rgb)
    rgb = colorsys.hls_to_rgb(h, l * lightness, s * saturation)
    mat = kit.material(name, kit.srgb('#' + ''.join(f'{round(c * 255):02x}' for c in rgb)), roughness)
    mat['remapLightness'] = lightness
    mat['remapSaturation'] = saturation
    return mat


def shades(roughness=0.9):
    """The camouflage's materials with their thresholds, from the bottom layer up."""
    return [(shade(name, lightness, saturation, roughness), threshold) for name, lightness, saturation, threshold in CAMO]


def camo(obj, colours=None, frequency=7.0, cuts=3, stretch=0.6, max_edge=None):
    """Lays the blotches on `obj`: its faces are subdivided (`cuts`), each gets the
    material of the blotch its centre lies in. `colours` are (material, threshold) from
    the bottom layer up (default: shades()); `frequency` is blotches per unit, `stretch`
    flattens them along z. With `max_edge` instead of a fixed number of cuts, only
    edges longer than it are split, again and again: big panels get a fine grid, the
    narrow bevels stay as they are. The noise runs in the object's space as placed
    (world), so the pattern carries on across neighbouring parts."""
    colours = colours or shades()
    kit.bake_modifiers(obj)
    obj.data.materials.clear()
    for mat, _ in colours:
        obj.data.materials.append(mat)
    world = obj.matrix_world
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    if max_edge:
        for _ in range(8):
            long = [e for e in bm.edges if e.calc_length() > max_edge]
            if not long:
                break
            bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
    elif cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    for face in bm.faces:
        centre = world @ face.calc_center_median()
        face.material_index = 0
        for layer, (_, threshold) in enumerate(colours):
            # each colour its own noise field
            p = Vector((centre.x * frequency, centre.y * frequency, centre.z * frequency * stretch))
            if threshold is None or noise.noise(p + Vector((layer * 17.3, layer * 5.1, layer * 11.7))) > threshold:
                face.material_index = layer
    bm.to_mesh(obj.data)
    bm.free()
    return obj
