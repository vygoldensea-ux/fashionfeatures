import bpy, sys, numpy as np
argv = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=argv[0])
ob = [o for o in bpy.context.scene.objects if o.type == 'MESH'][0]
bpy.context.view_layer.objects.active = ob
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=0.0005); bpy.ops.object.mode_set(mode='OBJECT')
me = ob.data
nv = len(me.vertices)
par = np.arange(nv)
def find(a):
    while par[a] != a:
        par[a] = par[par[a]]; a = par[a]
    return a
ev = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get('vertices', ev); ev = ev.reshape(-1, 2)
for a, b in ev:
    ra, rb = find(a), find(b)
    if ra != rb: par[ra] = rb
roots = np.array([find(i) for i in range(nv)])
u, cnt = np.unique(roots, return_counts=True)
zs = np.array([v.co.z for v in me.vertices])
order = np.argsort(-cnt)
print('COMP total', len(u))
for k in order[:12]:
    m = roots == u[k]
    print('COMP', cnt[k], 'z', round(zs[m].min(), 2), round(zs[m].max(), 2))
