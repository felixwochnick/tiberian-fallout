"""
Tiberian Fallout – GDI engineer (ENGINEER), after Tiberian Sun: the light
infantry's rig and clips (E1.py) in a grey-blue work vest with reflective bands and a
hard hat in the house colour, goggles on it, a tool pack with a coil of cable on his
back, hammer and wrench in his belt and a toolbox in his right hand; unarmed, his
arms hang down and swing as he walks.

Run headless:

    Blender -b --factory-startup --python blender/ENGINEER.py [-- --preview <clip:frame,…> <dir>]
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import E1 as soldier  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), 'public', 'models', 'ENGINEER.glb')
BLEND = os.path.join(HERE, 'ENGINEER.blend')


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    soldier.WEAPON = 'tools'
    soldier.build()
    print('export', soldier.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        frames = [(c, int(f)) for c, f in (x.split(':') for x in args[args.index('--preview') + 1].split(','))]
        soldier.render_preview(frames, args[args.index('--preview') + 2])


if __name__ == '__main__' and bpy.app.background:
    main()
