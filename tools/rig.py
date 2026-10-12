# Auto-rig a static GLB in Blender (headless).
#   blender -b -P tools/autorig.py -- <in.glb> <out.glb> <human|quad> <target_tris>
import bpy, sys, math
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
src, dst, mode, target = argv[0], argv[1], argv[2], int(argv[3])
hair_hue = argv[4] if len(argv) > 4 else 'purple'  # which texels count as hair: purple | pink

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in bpy.context.scene.objects:
    o.select_set(False)
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
# apply transforms, drop parents (Sketchfab nodes)
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o != obj:
        bpy.data.objects.remove(o, do_unlink=True)

# weld + decimate
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.remove_doubles(threshold=0.0005)
bpy.ops.object.mode_set(mode='OBJECT')
tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
if tris > target:
    m = obj.modifiers.new('dec', 'DECIMATE')
    m.ratio = target / tris
    bpy.ops.object.modifier_apply(modifier='dec')

# normalise: feet on ground, centred, glTF +Y up already converted to Blender Z-up
vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
mn = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
mx = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))
c = (mn + mx) / 2
obj.location -= Vector((c.x, c.y, mn.z))
bpy.ops.object.transform_apply(location=True)
vs = [v.co.copy() for v in obj.data.vertices]
H = max(v.z for v in vs)
if mode == 'human':
    # real-world metres so the game's retargeting maths (hip height etc.) holds
    k = 1.75 / H
    obj.scale = (k, k, k)
    bpy.ops.object.transform_apply(scale=True)
    vs = [v.co.copy() for v in obj.data.vertices]
    H = 1.75

# Blender: Z up, glTF +Z (front) == Blender -Y.
def front_sign():
    low = [v for v in vs if v.z < H * 0.06]
    if not low:
        return -1
    avg_low = sum(v.y for v in low) / len(low)
    avg = sum(v.y for v in vs) / len(vs)
    return -1 if avg_low < avg else 1  # toes stick out to the front
fs = front_sign() if mode == 'human' else -1
if fs > 0:
    # face glTF +Z (Blender -Y) like every other character
    obj.rotation_euler[2] = math.pi
    bpy.ops.object.transform_apply(rotation=True)
    vs = [v.co.copy() for v in obj.data.vertices]
    fs = -1

bpy.ops.object.armature_add(location=(0, 0, 0))
arm = bpy.context.object
arm.name = 'Armature'
bpy.ops.object.mode_set(mode='EDIT')
eb = arm.data.edit_bones
for b in list(eb):
    eb.remove(b)

def bone(name, head, tail, parent=None):
    b = eb.new(name)
    b.head = Vector(head)
    b.tail = Vector(tail)
    if parent:
        b.parent = eb[parent]
    return b

if mode == 'human':
    # arm reach from the mesh (A-pose): extreme |x| near shoulder-to-hip height
    band = [v for v in vs if H * 0.45 < v.z < H * 0.85]
    hx = max(abs(v.x) for v in band)
    hand = [v for v in band if abs(v.x) > hx * 0.9]
    hz = sum(v.z for v in hand) / len(hand)
    f = fs * 0.02 * H
    bone('Hips', (0, 0, H * 0.53), (0, 0, H * 0.6))
    bone('Spine', (0, 0, H * 0.6), (0, 0, H * 0.68), 'Hips')
    bone('Spine1', (0, 0, H * 0.68), (0, 0, H * 0.75), 'Spine')
    bone('Spine2', (0, 0, H * 0.75), (0, 0, H * 0.83), 'Spine1')
    bone('Neck', (0, 0, H * 0.83), (0, 0, H * 0.88), 'Spine2')
    bone('Head', (0, 0, H * 0.88), (0, 0, H * 1.0), 'Neck')
    for side, s in (('Left', 1), ('Right', -1)):
        # glTF/three: character's left is +x when facing +z
        sx = s * (1 if fs < 0 else -1)
        sh = (sx * H * 0.09, 0, H * 0.81)
        st = (sx * H * 0.17, 0, H * 0.80)
        handp = (sx * hx * 0.95, 0, hz)
        elbow = ((st[0] + handp[0]) / 2, 0, (st[2] + handp[2]) / 2)
        bone(side + 'Shoulder', sh, st, 'Spine2')
        bone(side + 'Arm', st, elbow, side + 'Shoulder')
        bone(side + 'ForeArm', elbow, handp, side + 'Arm')
        bone(side + 'Hand', handp, (handp[0] + sx * H * 0.06, 0, handp[2] - H * 0.02), side + 'ForeArm')
        lx = sx * H * 0.09
        bone(side + 'UpLeg', (lx, 0, H * 0.52), (lx, 0, H * 0.28), 'Hips')
        bone(side + 'Leg', (lx, 0, H * 0.28), (lx, 0, H * 0.05), side + 'UpLeg')
        bone(side + 'Foot', (lx, 0, H * 0.05), (lx, f * 4, H * 0.01), side + 'Leg')
else:
    # quadruped: body along Y (front = -Y), legs found per quadrant
    L = max(abs(v.y) for v in vs)
    def leg(xs, ys):
        pts = [v for v in vs if v.z < H * 0.25 and (v.x > 0) == (xs > 0) and (v.y > 0) == (ys > 0)]
        if not pts:
            return Vector((xs * 0.2, ys * L * 0.5, 0))
        return Vector((sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts), 0))
    back = H * 0.62
    bone('root', (0, L * 0.45, back), (0, 0, back))
    bone('spine', (0, 0, back), (0, -L * 0.45, back), 'root')
    bone('neck', (0, -L * 0.45, back), (0, -L * 0.6, H * 0.75), 'spine')
    bone('head', (0, -L * 0.6, H * 0.75), (0, -L * 0.95, H * 0.7), 'neck')
    bone('tail', (0, L * 0.45, back), (0, L * 0.7, H * 0.7), 'root')
    for name, xs, ys in (('FL', 1, -1), ('FR', -1, -1), ('BL', 1, 1), ('BR', -1, 1)):
        p = leg(xs, ys)
        top = (p.x, p.y, back * 0.85)
        knee = (p.x, p.y, H * 0.25)
        par = 'spine' if ys < 0 else 'root'
        bone(name + '_upper', top, knee, par)
        bone(name + '_lower', knee, (p.x, p.y, 0.0), name + '_upper')

bpy.ops.object.mode_set(mode='OBJECT')
for o in bpy.context.scene.objects:
    o.select_set(False)
obj.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
try:
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
except Exception as e:
    print('heat weights failed, using envelopes', e)
    bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
# hair must not ride on the arms: find it by colour (purple-ish in the base texture) and give it
# to the head / neck / upper back by height instead
import numpy as np
me = obj.data
mat = obj.active_material
img = None
if mat and mat.use_nodes:
    for nd in mat.node_tree.nodes:
        if nd.type == 'BSDF_PRINCIPLED':
            l = nd.inputs['Base Color'].links
            if l and l[0].from_node.type == 'TEX_IMAGE':
                img = l[0].from_node.image
if img is not None and mode == 'human':
    W_, H_ = img.size
    px = np.empty(W_ * H_ * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(H_, W_, 4)
    uvl = me.uv_layers.active.data
    uv = np.empty(len(uvl) * 2, dtype=np.float32)
    uvl.foreach_get('uv', uv)
    uv = uv.reshape(-1, 2)
    li = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get('vertex_index', li)
    xs = np.clip((uv[:, 0] % 1.0) * (W_ - 1), 0, W_ - 1).astype(int)
    ys = np.clip((uv[:, 1] % 1.0) * (H_ - 1), 0, H_ - 1).astype(int)
    col = px[ys, xs, :3]
    # purple hair and its light-blue tips: blue clearly above green (skin, black, white, stockings are not)
    # hair by colour: purple = blue well above green; pink = red well above green (skin is much closer)
    sat = col.max(1) - col.min(1)
    if hair_hue == 'purple':
        purple = ((col[:, 2] - col[:, 1]) > 0.10) & (sat > 0.2)          # purple + light-blue tips, not bluish whites
    else:
        # pink hair ≈ (0.98, 0.81, 0.83), skin ≈ (0.95, 0.88, 0.86): red well above green, blue not below green
        purple = ((col[:, 0] - col[:, 1]) > 0.125) & ((col[:, 2] - col[:, 1]) > -0.01)
    votes = np.zeros(len(me.vertices)); tot = np.zeros(len(me.vertices))
    np.add.at(votes, li, purple.astype(float)); np.add.at(tot, li, 1.0)
    colorHair = (votes / np.maximum(tot, 1)) > 0.5
    co = np.array([v.co[:] for v in me.vertices])
    nrm = np.array([v.normal[:] for v in me.vertices])
    xs_, zs = co[:, 0], co[:, 2]
    xs0, ns0 = xs_, nrm
    # per-vertex colour stats (mean of its texels)
    vc = np.zeros((len(co), 3)); np.add.at(vc, li, col); vc /= np.maximum(tot, 1)[:, None]
    lumv = vc @ np.array([0.3, 0.59, 0.11]); satv = vc.max(1) - vc.min(1)
    # ---- geometry: what is a layer OVER the body (hair, mask, choker) vs the body surface ----
    # Cast from each vertex toward the body axis: an overlay hits the body a few cm in; the body
    # surface itself hits nothing until the far inner wall. Cast outward too: anything with a
    # layer above it (the ear under the hair, the face under the mask) is covered = invisible.
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    bvh = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    nv = len(co)
    inD = np.full(nv, np.inf); outD = np.full(nv, np.inf)
    for i in range(nv):
        x, y, z = co[i]
        tgt = Vector((0.0, 0.0, min(z, H * 0.92) if z > H * 0.8 else z))
        o = Vector((x, y, z))
        d = tgt - o
        if d.length < 0.01:
            continue
        d.normalize()
        # only a surface FACING us counts as "something beneath": a ray that starts on the body
        # itself (e.g. the thin neck) travels inside and meets the back of the far wall instead.
        # Back faces on the way (the strand's own inner side) are stepped through.
        start = o + d * 0.006
        travelled = 0.006
        for _step in range(4):
            hit = bvh.ray_cast(start, d, 0.3 - travelled)
            if hit[0] is None:
                break
            travelled += hit[3]
            if hit[1].dot(d) < 0:
                inD[i] = travelled
                break
            start = hit[0] + d * 0.002
            travelled += 0.002
        hit = bvh.ray_cast(o - d * 0.004, -d, 0.08)
        if hit[0] is not None:
            outD[i] = hit[3] + 0.004
    overlay = (inD < 0.08) & ~(outD < 0.08)
    # face front (eyes, brows, lids) and the white mask are never hair
    face = (zs > H * 0.84) & (zs < H * 0.96) & (np.abs(xs_) < H * 0.065) & (nrm[:, 1] < -0.3)
    # the mask is really white and faces forward; pale skin/lavender strands at the sides are not it
    maskWhite = (lumv > 0.9) & (satv < 0.06) & (zs > H * 0.83) & (zs < H * 0.93) & (np.abs(xs_) < H * 0.1) & (nrm[:, 1] < 0.1)
    # where hair can be: the head (not the arms / hands), and the back/torso width below it
    region = ((zs > H * 0.8) & (np.abs(xs_) < H * 0.16)) | ((zs > H * 0.35) & (zs <= H * 0.8) & (np.abs(xs_) < H * 0.12))
    # hair = hair-coloured, unless it is body painted in the hair's colour (nothing under it for
    # 15 cm: the butt / back under a wall of hair), plus any lit overlay that was painted skin
    # ...but a hanging strand is a thin shell (a back face with the opposite normal a few mm
    # away) even when its inward ray misses the body: that stays hair
    from mathutils import kdtree
    kd = kdtree.KDTree(nv)
    for v in me.vertices:
        kd.insert(v.co, v.index)
    kd.balance()
    thin = np.zeros(nv, dtype=bool)
    for i in np.nonzero(colorHair & (inD > 0.15) & (zs < H * 0.8))[0]:
        i = int(i)
        for _co, j, _d in kd.find_range(me.vertices[i].co, 0.012):
            if j != i and float(np.dot(nrm[i], nrm[j])) < -0.3:
                thin[i] = True
                break
    painted_body = (inD > 0.15) & (zs < H * 0.8) & ~thin
    hair = (colorHair & ~painted_body) | (overlay & region & (lumv > 0.35))
    # width limit only keeps the hands (dark nails) out; hair fans past the hips to ~0.2 H
    hair &= ~face & ~maskWhite & (zs > H * 0.35) & (np.abs(xs_) < H * 0.25)
    print('AUTORIG labels: colour', int(colorHair.sum()), 'overlay', int(overlay.sum()), 'painted body', int((colorHair & painted_body).sum()), 'hair', int(hair.sum()))
    names = {g.name: g for g in obj.vertex_groups}
    neckZ = H * 0.85
    n_h = 0
    for i in np.nonzero(hair)[0]:
        i = int(i)
        for g in obj.vertex_groups:
            g.remove([i])
        z = zs[i]
        if z > neckZ:
            names['Head'].add([i], 1.0, 'REPLACE')
        else:
            # long hair hangs from the head and follows the upper back as it goes down
            t = min(1.0, (neckZ - z) / (H * 0.25))
            names['Head'].add([i], 1.0 - t, 'REPLACE')
            names['Spine2'].add([i], t, 'REPLACE')
        n_h += 1
    print('AUTORIG hair verts', n_h, 'of', len(me.vertices))
    # tell the web side which vertices are hair (custom attribute _hair, 1 = hair): the soft
    # regions must not grab the long hair that hangs over the back
    attr = me.attributes.new(name='_hair', type='FLOAT', domain='POINT')
    attr.data.foreach_set('value', hair.astype(np.float32))

    # ---- texture clean-up: skin-coloured patches baked onto the hair → hair colour ----
    # (only the purple model has them; a wrong fill here damages eyes and skin)
if img is not None and mode == 'human' and hair_hue == 'purple':
    me.calc_loop_triangles()
    tris = np.empty(len(me.loop_triangles) * 3, dtype=np.int32)
    me.loop_triangles.foreach_get('loops', tris)
    tris = tris.reshape(-1, 3)
    tv = li[tris]
    # texture fill only where the colour says hair (the overlay test also marks skin patches on
    # arms/thighs under the hair, and painting those purple was a bad regression)
    hairc = colorHair & ~painted_body & ~face & ~maskWhite & (zs > H * 0.35) & (np.abs(xs_) < H * 0.16)
    # the sides of the head are hair all the way down to the jaw (the ears are under it), so
    # every lit texel there is hair, whatever colour was baked on it
    # (the skin-painted strands sit at |x| ≈ 0.03–0.045 H facing sideways/back: not the face)
    sideHead = (zs > H * 0.835) & (zs < H * 0.985) & (np.abs(xs_) < H * 0.16) & ~face & ~maskWhite & (lumv > 0.3) & (((np.abs(xs_) > H * 0.025) & (nrm[:, 1] > -0.3)) | (np.abs(xs_) > H * 0.045))
    # the strands beside the jaw, just under the mask line (the neck itself is narrower than this)
    sideHead |= (zs > H * 0.80) & (zs <= H * 0.835) & (np.abs(xs_) > H * 0.04) & (np.abs(xs_) < H * 0.16) & ~maskWhite & (lumv > 0.3) & (nrm[:, 1] > -0.5)
    hairc |= sideHead
    # anything at the head with a surface a few cm beneath it is a layer over the head: hair
    # (also strands hanging in front of the cheeks, and the hidden ears). Not: the mask (its own
    # small mesh component), white texels, and the eye zone (eyeballs sit right behind the lids)
    comp = np.zeros(nv, dtype=np.int64) - 1
    ev = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get('vertices', ev); ev = ev.reshape(-1, 2)
    par = np.arange(nv)
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for a, b in ev:
        ra, rb = find(a), find(b)
        if ra != rb: par[ra] = rb
    roots = np.array([find(i) for i in range(nv)])
    bigroot = np.bincount(roots).argmax()
    small = roots != bigroot
    # only the eyes themselves (the cheek beside them is protected by the ray test: nothing beneath)
    eyeZone = (zs > H * 0.875) & (zs < H * 0.94) & (np.abs(xs_) < H * 0.032) & (nrm[:, 1] < -0.2)
    white = (lumv > 0.88) & (satv < 0.08)
    # (no white test: the mask is out by component already, and pale skin on strands reads as white)
    # the mask is neutral white/grey (no tint); pale skin on strands is pinkish, so saturation tells them apart
    neutral = (satv < 0.05) & (lumv > 0.5)
    overHead = (zs > H * 0.80) & (zs < H * 0.985) & (inD < 0.08) & ~small & ~neutral & ~eyeZone & (lumv > 0.3) & (np.abs(xs_) < H * 0.2)
    hairc |= overHead
    # strands fused onto the cheeks have no surface beneath them: grow hair over the mesh into
    # any head vertex whose neighbours are mostly hair (two rings), eyes/mask/white still excluded
    deg = np.zeros(nv); np.add.at(deg, ev[:, 0], 1); np.add.at(deg, ev[:, 1], 1)
    headOk = (zs > H * 0.80) & (zs < H * 0.985) & ~small & ~neutral & ~eyeZone & (lumv > 0.3) & (np.abs(xs_) < H * 0.2)
    grown = 0
    for _ in range(2):
        hs = np.zeros(nv); np.add.at(hs, ev[:, 0], hairc[ev[:, 1]]); np.add.at(hs, ev[:, 1], hairc[ev[:, 0]])
        add = headOk & ~hairc & (hs / np.maximum(deg, 1) > 0.5)
        hairc |= add
        grown += int(add.sum())
    print('AUTORIG grown into fused strands', grown)
    print('AUTORIG over-head layer forced hair', int(overHead.sum()), 'mask comp verts', int(small.sum()))
    print('AUTORIG side-of-head forced hair', int(sideHead.sum()))
    lum = lumv
    grow = hairc.copy()
    for ring in range(3):
        m = grow[tv].any(1)
        nxt = grow.copy()
        nxt[tv[m].ravel()] = True
        # at head height grow just one ring: the face and forehead must keep their skin
        if ring >= 1:
            nxt &= ~((zs > H * 0.86) & ~grow)
        grow = nxt
    grow &= (zs > H * 0.35) & (np.abs(xs_) < H * 0.16)
    head = (zs[tv] > H * 0.8).any(1)
    # body: only triangles whose three corners are hair; a triangle bridging a strand and the
    # shorts/skin would smear purple onto them (seen as stains on the shorts and thigh)
    sel = np.where(head, hairc[tv].any(1), hairc[tv].all(1))
    mask = np.zeros((H_, W_), dtype=bool)
    hv = hairc.astype(np.float32)
    for t, hw in zip(tris[sel], hv[tv[sel]]):
        p = uv[t] * [W_ - 1, H_ - 1]
        x0, y0 = np.floor(p.min(0)).astype(int); x1, y1 = np.ceil(p.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W_ - 1), min(y1, H_ - 1)
        if x1 < x0 or y1 < y0 or (x1 - x0) * (y1 - y0) > 40000:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        (ax, ay), (bx, by), (cx, cy) = p
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-9:
            continue
        l1 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / d
        l2 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / d
        l3 = 1 - l1 - l2
        inside = (l1 >= -0.02) & (l2 >= -0.02) & (l3 >= -0.02)
        # hair-ness interpolated across the triangle: boundary triangles get their hair half only
        hairy = (l1 * hw[0] + l2 * hw[1] + l3 * hw[2]) >= (0.5 if hw.min() < 1 else 0.0)
        mask[y0:y1 + 1, x0:x1 + 1] |= inside & hairy
    rgb = px[:, :, :3]
    tlum = rgb @ np.array([0.3, 0.59, 0.11], dtype=np.float32)  # per texel
    # a real hair texel is purple AND dark-ish; the baked streaks are pale lavender/grey (a faint
    # blue tint passes the hue test alone), so brightness is part of the test
    good = mask & ((((rgb[:, :, 2] - rgb[:, :, 1]) > 0.08) & (tlum < 0.6)) if hair_hue == 'purple' else ((rgb[:, :, 0] - rgb[:, :, 1]) > 0.14))
    tsat = rgb.max(2) - rgb.min(2)
    mask &= ~((tsat < 0.05) & (tlum > 0.5))  # neutral white/grey texels = the mask, never repainted
    bad = mask & ~good
    print('AUTORIG hair texels', int(mask.sum()), 'skin-coloured fixed', int(bad.sum()))
    # recolour every non-hair texel on the hair to the hair's own colour, keeping the texel's
    # shading (a whole patch at once: a slow diffusion left the middle of big patches skin)
    base = rgb[good].mean(0)
    lref = max(float(np.median(tlum[good])), 1e-3)
    shade = np.clip(tlum / lref, 0.45, 1.2)[..., None]
    fillc = np.clip(base[None, None, :] * shade, 0, 1)
    import os
    if os.environ.get('DUMP_DIR'):
        d = os.environ['DUMP_DIR']; os.makedirs(d, exist_ok=True)
        np.save(os.path.join(d, 'orig.npy'), px[:, :, :3].copy())
        np.save(os.path.join(d, 'hairmask.npy'), mask)
        np.save(os.path.join(d, 'bad.npy'), bad)
    if os.environ.get('SKIP_REPAINT'):
        bad = np.zeros_like(bad)
    px[:, :, :3] = np.where(bad[..., None], fillc, rgb)
    img.pixels.foreach_set(px.ravel())
    img.update()
    img.pack()
groups = [g.name for g in obj.vertex_groups]
print('AUTORIG front', fs, 'H', H, 'groups', groups)

bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_skins=True, export_animations=False, export_apply=False, export_attributes=True, export_image_format='WEBP' if hasattr(bpy.types, 'Image') else 'AUTO')
print('AUTORIG done', dst)
