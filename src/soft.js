// Soft chest: a small dynamic mesh cut out of the character, deformed every frame.
//   size    radial scale around each breast centre (rest shape)
//   squeeze a "poke" dents the surface under the finger and bulges a ring around it; it springs
//           back (under-damped = jelly) when released, and drags shear the surface along
//   mold    a grab brush that changes the rest shape for good (reset clears it)
//   jiggle  each breast has a damped 3D spring; pokes, drags, size changes and shakes excite it
// Everything outside the cut stays a static mesh; the cut's border vertices never move, so the
// two meshes always meet without cracks.
import * as THREE from 'three';

const smooth = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const lerp = (a, b, t) => a + (b - a) * t;

export class SoftChest {
  // mesh: the character mesh (indexed); centers: breast centres in the mesh's local space
  // facing: +1 = the region bulges toward +z (chest), -1 = toward -z (glutes)
  // skip: optional per-vertex array, > 0.5 = never part of the region (hair over the back)
  constructor(mesh, centers, { radius = 0.14, facing = 1, skip = null } = {}) {
    const g = mesh.geometry;
    const P = g.attributes.position.array;
    const N = g.attributes.normal.array;
    const idx = g.index.array;
    const nv = P.length / 3;
    this.C = centers.map((c) => c.clone());
    this.R = radius;

    // weld: vertices split at UV seams share a position; join them so the surface is one piece
    const weld = new Int32Array(nv);
    const keys = new Map();
    let nw = 0;
    for (let i = 0; i < nv; i++) {
      const k = `${Math.round(P[i * 3] * 2e4)},${Math.round(P[i * 3 + 1] * 2e4)},${Math.round(P[i * 3 + 2] * 2e4)}`;
      let id = keys.get(k);
      if (id === undefined) keys.set(k, (id = nw++));
      weld[i] = id;
    }
    const wpos = new Float32Array(nw * 3);
    for (let i = 0; i < nv; i++) wpos.set([P[i * 3], P[i * 3 + 1], P[i * 3 + 2]], weld[i] * 3);
    const wskip = new Uint8Array(nw);
    if (skip) for (let i = 0; i < nv; i++) if (skip[i] > 0.5) wskip[weld[i]] = 1;
    // welded adjacency (CSR) for the flood fill
    const deg = new Uint32Array(nw);
    for (let i = 0; i < idx.length; i++) deg[weld[idx[i]]] += 2;
    const start = new Uint32Array(nw + 1);
    for (let i = 0; i < nw; i++) start[i + 1] = start[i] + deg[i];
    const fill = start.slice(0, nw);
    const adj = new Uint32Array(start[nw]);
    for (let t = 0; t < idx.length; t += 3) {
      const a = weld[idx[t]], b = weld[idx[t + 1]], c = weld[idx[t + 2]];
      adj[fill[a]++] = b; adj[fill[a]++] = c;
      adj[fill[b]++] = a; adj[fill[b]++] = c;
      adj[fill[c]++] = a; adj[fill[c]++] = b;
    }

    // per breast: start at the front-most point near the centre, then flood over the surface
    // inside the sphere. Hair or arms that only pass nearby are not connected, so they stay out.
    const wW = this.C.map(() => new Float32Array(nw));
    const dist = (i, c) => Math.hypot(wpos[i * 3] - c.x, wpos[i * 3 + 1] - c.y, wpos[i * 3 + 2] - c.z);
    this.C.forEach((c, k) => {
      // candidates: the most forward (facing) welded points near the centre, best first; a stray
      // strand that slipped the hair label gives a tiny fill, so try the next candidate then
      const cand = [];
      for (let i = 0; i < nw; i++) if (!wskip[i] && dist(i, c) < radius * 0.8) cand.push(i);
      cand.sort((a, b) => facing * wpos[b * 3 + 2] - facing * wpos[a * 3 + 2]);
      // the region is the union of every surface patch (that is not hair) within the sphere,
      // found by flooding from each candidate: strands crossing the skin split it into pieces
      const seen = new Uint8Array(nw);
      let total = 0;
      for (const apex of cand) {
        if (seen[apex]) continue;
        const q = [apex];
        seen[apex] = 1;
        while (q.length) {
          const i = q.pop();
          wW[k][i] = smooth(radius, radius * 0.45, dist(i, c));
          total++;
          for (let e = start[i]; e < start[i + 1]; e++) {
            const j = adj[e];
            if (!seen[j] && !wskip[j] && dist(j, c) < radius) (seen[j] = 1), q.push(j);
          }
        }
      }
      // hair lying over the region rides along with it (otherwise the grown surface pokes
      // through the strands); it just never seeds or carries the flood
      if (total) for (let i = 0; i < nw; i++) if (wskip[i]) {
        const d = dist(i, c);
        if (d < radius) wW[k][i] = Math.max(wW[k][i], smooth(radius, radius * 0.45, d));
      }
      // (hair only follows outward growth and a little of the bounce: see update())
    });
    const wK = wW.map((w) => Float32Array.from(weld, (id) => w[id]));

    // split: triangles touching the cut go to the dynamic mesh, the rest stay on the original
    const inCut = (i) => wK.some((w) => w[i] > 0);
    const dynTris = [];
    const statTris = [];
    for (let t = 0; t < idx.length; t += 3) {
      const a = idx[t], b = idx[t + 1], c = idx[t + 2];
      (inCut(a) || inCut(b) || inCut(c) ? dynTris : statTris).push(a, b, c);
    }
    g.setIndex(statTris);
    const map = new Map();
    const orig = [];
    const local = dynTris.map((i) => {
      if (!map.has(i)) map.set(i, orig.push(i) - 1);
      return map.get(i);
    });
    const n = orig.length;
    this.n = n;
    const dg = new THREE.BufferGeometry();
    for (const [name, attr] of Object.entries(g.attributes)) {
      const sz = attr.itemSize;
      const arr = new attr.array.constructor(n * sz);
      for (let i = 0; i < n; i++) for (let s = 0; s < sz; s++) arr[i * sz + s] = attr.array[orig[i] * sz + s];
      dg.setAttribute(name, new THREE.BufferAttribute(arr, sz, attr.normalized));
    }
    dg.setIndex(local);
    dg.attributes.position.setUsage(THREE.DynamicDrawUsage);
    dg.attributes.normal.setUsage(THREE.DynamicDrawUsage);
    this.rest = dg.attributes.position.array.slice();
    this.origN = dg.attributes.normal.array.slice();
    this.mold = new Float32Array(n * 3);
    this.w = this.C.map((_, k) => Float32Array.from(orig, (i) => wK[k][i]));
    this.wMax = Float32Array.from(orig, (_, i) => Math.max(...this.w.map((w) => w[i])));
    this.isHair = Uint8Array.from(orig, (i) => (skip && skip[i] > 0.5 ? 1 : 0));
    this.geo = dg;
    if (mesh.isSkinnedMesh) {
      // the cut keeps the skin weights it was copied with: same skeleton, same bind pose
      this.mesh = new THREE.SkinnedMesh(dg, mesh.material);
      this.mesh.bind(mesh.skeleton, mesh.bindMatrix);
      this.mesh.bindMode = mesh.bindMode;
      this.mesh.frustumCulled = false;
    } else this.mesh = new THREE.Mesh(dg, mesh.material);
    this.mesh.name = 'softChest';
    dg.computeBoundingSphere();
    dg.boundingSphere.radius += 0.12; // room to grow, so raycasts never miss a deformed part
    this.verts = n;

    // state
    this.size = 1;
    this.sizeT = 1;
    this.soft = 0.6;
    this.J = this.C.map(() => ({ x: new THREE.Vector3(), v: new THREE.Vector3() }));
    // jelly: a squash/stretch spring per breast (flattens along the poke, bulges sideways, wobbles back)
    this.S = this.C.map(() => ({ x: 0, v: 0, axis: new THREE.Vector3(0, 0, 1) }));
    this.pokes = [];
    this.dirty = true;
    this._p = new THREE.Vector3();
  }

  // which breast a point belongs to (nearest centre)
  side(p) {
    let k = 0;
    for (let i = 1; i < this.C.length; i++) if (p.distanceTo(this.C[i]) < p.distanceTo(this.C[k])) k = i;
    return k;
  }

  // ---------- squeeze ----------
  pressStart(p, nrm) {
    const poke = { p: p.clone(), n: nrm.clone().normalize(), depth: 0, vel: 0, held: true, shear: new THREE.Vector3(), shearT: new THREE.Vector3(), k: this.side(p) };
    this.pokes.push(poke);
    if (this.pokes.length > 4) this.pokes.shift();
    // a touch knocks it back and squashes it: the jelly wobble starts right away
    const kick = 0.35 + this.soft * 0.9;
    this.J[poke.k].v.addScaledVector(poke.n, -kick * this.size);
    const sq = this.S[poke.k];
    sq.axis.copy(poke.n);
    sq.v += (2.2 + 3 * this.soft);
    this.dirty = true;
    return poke;
  }
  pressMove(poke, p, dt) {
    if (!poke) return;
    const d = p.clone().sub(poke.p);
    poke.shearT.add(d.multiplyScalar(0.8)).clampLength(0, 0.035 * this.size);
    poke.p.lerp(p, 0.35);
    const j = this.J[poke.k];
    j.v.addScaledVector(d, (0.6 + this.soft) * 6 / Math.max(dt, 1 / 120) * 0.016);
    this.dirty = true;
  }
  pressEnd(poke) {
    if (!poke) return;
    poke.held = false;
    poke.shearT.set(0, 0, 0);
    // let go: the breast bounces back out along the press direction
    this.J[poke.k].v.addScaledVector(poke.n, poke.depth * (6 + 10 * this.soft));
    this.S[poke.k].v -= 2 + 3 * this.soft;
    this.dirty = true;
  }

  // ---------- mold (grab brush on the rest shape) ----------
  moldDrag(p, delta) {
    const s2 = 0.045 * 0.045 * this.size * this.size;
    const R = this.rest;
    const M = this.mold;
    const lim = 0.06;
    for (let i = 0; i < this.n; i++) {
      const w = this.wMax[i];
      if (w <= 0) continue;
      const dx = R[i * 3] + M[i * 3] - p.x, dy = R[i * 3 + 1] + M[i * 3 + 1] - p.y, dz = R[i * 3 + 2] + M[i * 3 + 2] - p.z;
      const g = Math.exp(-(dx * dx + dy * dy + dz * dz) / s2) * w;
      if (g < 1e-3) continue;
      for (let a = 0; a < 3; a++) {
        M[i * 3 + a] = Math.max(-lim, Math.min(lim, M[i * 3 + a] + delta.getComponent(a) * g));
      }
    }
    this.J[this.side(p)].v.addScaledVector(delta, 4 * this.soft);
    this.dirty = true;
  }

  // body motion → jiggle: acceleration (and tilt against gravity) of the chest, in bind space
  drive(force, dt) {
    const gain = lerp(0.2, 0.32, this.soft) * this.size;
    for (const j of this.J) j.v.addScaledVector(force, gain * dt);
    this.dirty = true;
  }

  shake() {
    for (const q of this.S) q.v += (Math.random() - 0.3) * (3 + 3 * this.soft);
    for (const j of this.J) j.v.add(new THREE.Vector3((Math.random() - 0.5) * 0.4, 0.5 + Math.random() * 0.3, (Math.random() - 0.5) * 0.2).multiplyScalar(0.6 + this.soft));
    this.dirty = true;
  }
  reset() {
    this.mold.fill(0);
    this.pokes.length = 0;
    for (const j of this.J) j.x.set(0, 0, 0), j.v.set(0, 0, 0);
    for (const q of this.S) (q.x = 0), (q.v = 0);
    this.dirty = true;
  }
  setSize(s) {
    const ds = s - this.sizeT;
    this.sizeT = s;
    for (const j of this.J) j.v.y += ds * 0.6 * (0.5 + this.soft);
    this.dirty = true;
  }

  // ---------- per frame ----------
  update(dt) {
    dt = Math.min(dt, 1 / 30);
    const soft = this.soft;
    // springs (sub-stepped so stiff settings stay stable)
    const steps = 4;
    const h = dt / steps;
    const kJ = lerp(260, 70, soft);
    const cJ = lerp(12, 1.7, soft);
    const kS = lerp(420, 120, soft);
    const cS = lerp(14, 2.2, soft);
    const kP = lerp(520, 120, soft);
    const zP = lerp(0.7, 0.16, soft);
    const cP = 2 * zP * Math.sqrt(kP);
    const depthMax = lerp(0.02, 0.05, soft) * this.size;
    let energy = Math.abs(this.sizeT - this.size);
    for (let s = 0; s < steps; s++) {
      this.size += (this.sizeT - this.size) * Math.min(1, h * 10);
      for (const j of this.J) {
        j.v.addScaledVector(j.x, -kJ * h).multiplyScalar(Math.max(0, 1 - cJ * h));
        j.x.addScaledVector(j.v, h);
        if (j.x.length() > 0.05 * this.size) j.x.setLength(0.05 * this.size);
      }
      for (const q of this.S) {
        q.v += (-kS * q.x - cS * q.v) * h;
        q.x = Math.max(-0.35, Math.min(0.35, q.x + q.v * h));
      }
      for (const p of this.pokes) {
        const target = p.held ? depthMax : 0;
        p.vel += (kP * (target - p.depth) - cP * p.vel) * h;
        p.depth += p.vel * h;
        p.shear.lerp(p.shearT, Math.min(1, h * (p.held ? 18 : lerp(10, 4, soft))));
      }
    }
    this.pokes = this.pokes.filter((p) => p.held || Math.abs(p.depth) > 1e-5 || Math.abs(p.vel) > 1e-4 || p.shear.lengthSq() > 1e-9);
    for (const j of this.J) energy += j.x.lengthSq() * 100 + j.v.lengthSq();
    for (const q of this.S) energy += q.x * q.x + q.v * q.v * 0.01;
    energy += this.pokes.length;
    if (!this.dirty && energy < 1e-7) return false;
    this.dirty = energy > 1e-7;

    // deform
    const pos = this.geo.attributes.position.array;
    const R = this.rest;
    const M = this.mold;
    const N0 = this.origN;
    const sig2 = (0.038 * this.size) ** 2;
    const scale = this.size - 1;
    for (let i = 0; i < this.n; i++) {
      const wm = this.wMax[i];
      let x = R[i * 3] + M[i * 3], y = R[i * 3 + 1] + M[i * 3 + 1], z = R[i * 3 + 2] + M[i * 3 + 2];
      if (wm > 0) {
        let ox = 0, oy = 0, oz = 0;
        for (let k = 0; k < this.C.length; k++) {
          const w = this.w[k][i];
          if (w <= 0) continue;
          const c = this.C[k];
          // size: grow from the centre, and sag a touch when big. Hair lying over the region
          // is pushed out with it but never pulled in (it hangs, it is not glued to the skin)
          const hairV = this.isHair[i];
          const sc = hairV ? Math.max(0, scale) * 0.9 : scale;
          ox += (x - c.x) * sc * w;
          oy += (y - c.y) * sc * w - Math.max(0, scale) * 0.025 * w * w;
          oz += (z - c.z) * sc * w;
          // jelly squash: flatten along the poke axis, bulge across it
          const q = this.S[k];
          if (q.x !== 0) {
            const a = q.axis;
            const rx = x - c.x, ry = y - c.y, rz = z - c.z;
            const along = rx * a.x + ry * a.y + rz * a.z;
            const f = q.x * w;
            ox += -a.x * along * f + (rx - a.x * along) * f * 0.5;
            oy += -a.y * along * f + (ry - a.y * along) * f * 0.5;
            oz += -a.z * along * f + (rz - a.z * along) * f * 0.5;
          }
          // jiggle: the tip moves most
          const wj = w * Math.sqrt(w) * (hairV ? 0.5 : 1);
          ox += this.J[k].x.x * wj;
          oy += this.J[k].x.y * wj;
          oz += this.J[k].x.z * wj;
        }
        x += ox;
        y += oy;
        z += oz;
        for (const p of this.pokes) {
          const dx = x - p.p.x, dy = y - p.p.y, dz = z - p.p.z;
          const d2 = dx * dx + dy * dy + dz * dz;
          const g = Math.exp(-d2 / sig2) * wm;
          // dent under the finger, a soft bulge in a ring around it (flesh goes somewhere)
          const r = Math.sqrt(d2 / sig2);
          const ring = Math.exp(-((r - 1.7) ** 2) / 0.5) * 0.45 * wm;
          const dn = -p.depth * g;
          const bn = p.depth * ring;
          x += p.n.x * dn + N0[i * 3] * bn + p.shear.x * g;
          y += p.n.y * dn + N0[i * 3 + 1] * bn + p.shear.y * g;
          z += p.n.z * dn + N0[i * 3 + 2] * bn + p.shear.z * g;
        }
      }
      pos[i * 3] = x;
      pos[i * 3 + 1] = y;
      pos[i * 3 + 2] = z;
    }
    this.geo.attributes.position.needsUpdate = true;
    // lighting: fresh normals inside, the original ones at the border (no seam with the body)
    this.geo.computeVertexNormals();
    const nn = this.geo.attributes.normal.array;
    for (let i = 0; i < this.n; i++) {
      const t = smooth(0, 0.25, this.wMax[i]);
      if (t >= 1) continue;
      let ax = lerp(N0[i * 3], nn[i * 3], t), ay = lerp(N0[i * 3 + 1], nn[i * 3 + 1], t), az = lerp(N0[i * 3 + 2], nn[i * 3 + 2], t);
      const l = Math.hypot(ax, ay, az) || 1;
      nn[i * 3] = ax / l;
      nn[i * 3 + 1] = ay / l;
      nn[i * 3 + 2] = az / l;
    }
    this.geo.attributes.normal.needsUpdate = true;
    return true;
  }
}
