// Simplify the character for the web: meshoptimizer keeps UV seams intact (no texture smears),
// the chest is locked at full density (it gets deformed), textures are re-encoded smaller.
// node simplify.mjs in.glb out.glb targetTris
import { NodeIO } from '@gltf-transform/core';
import { MeshoptSimplifier } from 'meshoptimizer';
import { execFileSync } from 'child_process';
import fs from 'fs';
const [src, dst, tgt] = process.argv.slice(2);
await MeshoptSimplifier.ready;
const io = new NodeIO();
const doc = await io.read(src);
const prim = doc.getRoot().listMeshes()[0].listPrimitives()[0];
const P = prim.getAttribute('POSITION').getArray();
const N = prim.getAttribute('NORMAL').getArray();
const UV = prim.getAttribute('TEXCOORD_0').getArray();
const idx = Uint32Array.from(prim.getIndices().getArray());
const nv = P.length / 3;
// chest: lock every vertex near the two front-most points of the chest band
let minY = Infinity, maxY = -Infinity;
for (let i = 1; i < P.length; i += 3) (minY = Math.min(minY, P[i])), (maxY = Math.max(maxY, P[i]));
const h = maxY - minY;
const centers = [-1, 1].map((sd) => {
  let best = -Infinity, c = null;
  for (let i = 0; i < nv; i++) {
    const x = P[i * 3], y = P[i * 3 + 1], z = P[i * 3 + 2], ry = (y - minY) / h;
    if (ry > 0.62 && ry < 0.84 && sd * x > 0.01 && sd * x < 0.2 && z > best) (best = z), (c = [x, y, z - 0.105]);
  }
  return c;
});
const lock = new Uint8Array(nv);
let locked = 0;
for (let i = 0; i < nv; i++) {
  for (const c of centers) {
    if (Math.hypot(P[i * 3] - c[0], P[i * 3 + 1] - c[1], P[i * 3 + 2] - c[2]) < 0.2) { lock[i] = 1; locked++; break; }
  }
}
const attrs = new Float32Array(nv * 5);
for (let i = 0; i < nv; i++) attrs.set([N[i * 3], N[i * 3 + 1], N[i * 3 + 2], UV[i * 2], UV[i * 2 + 1]], i * 5);
const [out, err] = MeshoptSimplifier.simplifyWithAttributes(idx, P, 3, attrs, 5, [0.5, 0.5, 0.5, 1, 1], lock, +tgt * 3, 0.02, []);
// drop unused vertices
const remap = new Int32Array(nv).fill(-1);
let n = 0;
for (const v of out) if (remap[v] < 0) remap[v] = n++;
const take = (arr, sz) => { const o = new arr.constructor(n * sz); for (let i = 0; i < nv; i++) if (remap[i] >= 0) for (let s = 0; s < sz; s++) o[remap[i] * sz + s] = arr[i * sz + s]; return o; };
for (const sem of prim.listSemantics()) {
  const a = prim.getAttribute(sem);
  a.setArray(take(a.getArray(), a.getElementSize()));
}
prim.getIndices().setArray(Uint32Array.from(out, (v) => remap[v]));
// textures: re-encode (base colour stays 2048, the other maps 1024)
const base = prim.getMaterial()?.getBaseColorTexture();
for (const t of doc.getRoot().listTextures()) {
  const tmp = `/tmp/sb_tex_${Math.random().toString(36).slice(2)}.jpg`;
  fs.writeFileSync(tmp, t.getImage());
  execFileSync('sips', ['-s', 'format', 'jpeg', '-s', 'formatOptions', '82', '-Z', t === base ? '2048' : '1024', tmp, '--out', tmp], { stdio: 'ignore' });
  t.setImage(fs.readFileSync(tmp)).setMimeType('image/jpeg');
  fs.unlinkSync(tmp);
}
await io.write(dst, doc);
console.log(JSON.stringify({ verts: [nv, n], tris: [idx.length / 3, out.length / 3], locked, err: +err.toFixed(4), centers, size: fs.statSync(dst).size }));
