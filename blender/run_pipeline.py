"""Headless pipeline: build → bake → save → export.

Full rebuild:
    Blender -b --factory-startup --python blender/run_pipeline.py
Re-bake single objects of the saved scene (much faster):
    Blender -b blender/startup_menu.blend --python blender/run_pipeline.py -- --rebake Plate,PlateOuter
"""
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, 'startup_menu.py')
ns = {'__file__': PATH, '__name__': 'startup_menu'}
exec(compile(open(PATH).read(), PATH, 'exec'), ns)

args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
rebake = args[args.index('--rebake') + 1].split(',') if '--rebake' in args else None

if not rebake:
    # Remove the default cube, camera and light of a fresh file
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

prefs = bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = True
    bpy.context.scene.cycles.device = 'GPU'
except Exception as error:  # noqa: BLE001 – fall back to CPU
    print('GPU not available, baking on CPU:', error)

start = time.time()
if rebake:
    for name in rebake:
        t = time.time()
        ns['rebake']([name])
        print(f'baked {name} in {time.time() - t:.0f}s', flush=True)
else:
    print('build', ns['build'](), flush=True)
    for name in ns['BAKE_SIZES']:
        t = time.time()
        ns['bake_all']([name])
        print(f'baked {name} in {time.time() - t:.0f}s', flush=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'startup_menu.blend'), compress=True)
print('export', ns['export_glb'](), flush=True)
print(f'done in {time.time() - start:.0f}s', flush=True)
sys.exit(0)
