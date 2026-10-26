"""
Tiberian Fallout – GDI grenadier (E2), after Tiberian Sun: the light infantry's
soldier (E1.py: same rig, camouflage and clips) without a rifle, a grenade in his right
hand ready to throw, a bandolier of grenades across his vest and a satchel of them on
his hip. His own clip Fire: wind up, throw over the top, follow through.

Run headless:

    Blender -b --factory-startup --python blender/E2.py [-- --preview <clip:frame,…> <dir>]
"""
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import E1 as soldier  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), 'public', 'models', 'E2.glb')
BLEND = os.path.join(HERE, 'E2.blend')


def main():
    args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    soldier.WEAPON = 'grenades'
    soldier.build()
    print('export', soldier.export_glb(OUT), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    if '--preview' in args:
        frames = [(c, int(f)) for c, f in (x.split(':') for x in args[args.index('--preview') + 1].split(','))]
        soldier.render_preview(frames, args[args.index('--preview') + 2])


if __name__ == '__main__' and bpy.app.background:
    main()
