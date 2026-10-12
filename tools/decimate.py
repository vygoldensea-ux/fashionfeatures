# Blender headless: decimate the source model, keeping the chest dense (vertex-group weighted collapse).
# blender -b -P tools/decimate.py -- in.glb out.glb target_tris
import bpy, sys, math
argv = sys.argv[sys.argv.index('--') + 1:]
src, dst, target = argv[0], argv[1], int(argv[2])
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
me = ob.data
tris0 = sum(len(p.vertices) - 2 for p in me.polygons)
# glTF y-up becomes Blender z-up: (x, y, z)gltf -> (x, -z, y)blender
centers = [(-0.075, -0.12, 0.46), (0.075, -0.12, 0.46)]
vg = ob.vertex_groups.new(name='keep')
mw = ob.matrix_world
for v in me.vertices:
    p = mw @ v.co
    d = min(math.dist(p, c) for c in centers)
    w = 1.0 if d < 0.16 else max(0.0, 1.0 - (d - 0.16) / 0.08)
    if w > 0: vg.add([v.index], w, 'REPLACE')
mod = ob.modifiers.new('dec', 'DECIMATE')
mod.decimate_type = 'COLLAPSE'
mod.ratio = target / tris0
mod.vertex_group = 'keep'
mod.invert_vertex_group = True
mod.vertex_group_factor = 8.0
mod.use_collapse_triangulate = True
bpy.context.view_layer.objects.active = ob
bpy.ops.object.modifier_apply(modifier='dec')
ob.vertex_groups.clear()
tris1 = sum(len(p.vertices) - 2 for p in me.polygons)
# textures: cap at 2048
for img in bpy.data.images:
    if img.size[0] > 2048:
        img.scale(2048, int(img.size[1] * 2048 / img.size[0]))
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_image_format='JPEG', export_jpeg_quality=88, export_apply=True)
print('TRIS', tris0, '->', tris1, [ (i.name, tuple(i.size)) for i in bpy.data.images])
