// Phone-shaped page: a 3:4 portrait of the character on black, and a HUD under it
// (character, camera presets, chest / hip size, softness). Touch the chest or the hips = a jelly
// poke (dent + squash, bounces back on release); drag anywhere else = turn the camera.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { SoftChest } from './soft.js';

// characters: a file each (rigged with tools/rig.py); null = not ready yet
const CHARS = [
  { id: 'tim', name: 'Tím', file: 'assets/rigged.glb' },
];

const VERSION = '2026-10-10h3'; // bump when a model file is rebuilt (browsers cache the old one)
// ?vn=1 (set by the host page for Vietnamese visitors): the second character is not offered,
// and its file is also refused by the server, so a failed load just leaves the first one
const DEV = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);
const REGION_LIMITED = new URLSearchParams(location.search).get('vn') === '1';
const $ = (s) => document.querySelector(s);
// ?lang=en (set by the English host page): every visible word in English
const EN = new URLSearchParams(location.search).get('lang') === 'en';
const TX = EN
  ? {
      loading: 'Loading…',
      failed: 'Could not load the character',
      hint: '1 finger: turn · 2 fingers: pan & zoom · tap the chest or hips to squeeze',
      cams: { portrait: 'Portrait', half: 'Half body', full: 'Full body', side: 'Side', back: 'Back' },
      labels: { size: 'Chest', hip: 'Hips', soft: 'Softness' },
      names: { tim: 'Violet', hong: 'Rose' },
    }
  : { loading: 'Đang tải…', failed: 'Không tải được nhân vật' };
if (EN) {
  document.documentElement.lang = 'en';
  for (const c of CHARS) c.name = TX.names[c.id] || c.name;
  $('#hint').textContent = TX.hint;
  $('#loading').textContent = TX.loading;
  for (const b of document.querySelectorAll('#cams button')) b.textContent = TX.cams[b.dataset.cam] || b.textContent;
  for (const [id, t] of Object.entries(TX.labels)) {
    const label = document.getElementById(id)?.closest('label');
    if (label?.firstChild?.nodeType === Node.TEXT_NODE) label.firstChild.nodeValue = `${t} `;
  }
}
const canvas = $('#c');
const view = $('#view');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
// close to a neutral studio viewer: albedo colours untouched (no tone mapping), soft studio light all round
// (?tm= / ?exp= / ?env= override, for tuning)
const QS = new URLSearchParams(location.search);
renderer.toneMapping = { none: THREE.NoToneMapping, aces: THREE.ACESFilmicToneMapping, agx: THREE.AgXToneMapping, neutral: THREE.NeutralToneMapping }[QS.get('tm') || 'none'];
renderer.toneMappingExposure = Number(QS.get('exp') || 1);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);

// a small studio for image-based light: grey room, a big soft box above-front, side panels
function studioEnv() {
  const env = new THREE.Scene();
  env.add(new THREE.Mesh(new THREE.BoxGeometry(10, 10, 10), new THREE.MeshBasicMaterial({ color: 0x9c9ca4, side: THREE.BackSide })));
  const panel = (w, h, pos, c) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: c, side: THREE.DoubleSide }));
    m.position.set(...pos);
    m.lookAt(0, 0, 0);
    env.add(m);
  };
  panel(4, 4, [0, 4.5, 2], 0xffffff);
  panel(3, 5, [-4.5, 1, 1.5], 0xd8d8e0);
  panel(3, 5, [4.5, 1, 1.5], 0xe0dcd8);
  panel(4, 3, [0, 1, 4.8], 0xb8b8bc);
  const pm = new THREE.PMREMGenerator(renderer);
  const tex = pm.fromScene(env, 0.04).texture;
  pm.dispose();
  return tex;
}
scene.environment = studioEnv();
scene.environmentIntensity = Number(QS.get('env') || 0.65);
// soft fill from above and below so the albedo reads evenly (no dark sides)
scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8790, 0.9));
const key = new THREE.DirectionalLight(0xffffff, 0.7);
key.position.set(1, 2.5, 3);
scene.add(key);

// ---------- camera ----------
const camera = new THREE.PerspectiveCamera(30, 3 / 4, 0.02, 50);
const cam = { yaw: 0, pitch: 0.04, dist: 1.6, ty: 1.3 };
const camTo = { ...cam };
let chestY = 1.27;
let hipY = 0.95;
let camName = 'portrait';
const PRESETS = {
  portrait: () => ({ yaw: 0, pitch: 0.04, dist: 1.55, ty: chestY + 0.07 }),
  half: () => ({ yaw: 0, pitch: 0.05, dist: 2.25, ty: chestY - 0.12 }),
  full: () => ({ yaw: 0, pitch: 0.06, dist: 3.9, ty: 0.9 }),
  side: () => ({ yaw: 0.85, pitch: 0.05, dist: 1.75, ty: chestY + 0.02 }),
  // three-quarter from behind: long hair hides a straight back view
  back: () => ({ yaw: Math.PI * 0.72, pitch: 0.02, dist: 2.1, ty: hipY + 0.08 }),
};
function setCam(name) {
  camName = name;
  Object.assign(camTo, PRESETS[name]());
  // turn the short way round
  while (camTo.yaw - cam.yaw > Math.PI) camTo.yaw -= Math.PI * 2;
  while (camTo.yaw - cam.yaw < -Math.PI) camTo.yaw += Math.PI * 2;
}
function placeCamera(dt) {
  const k = Math.min(1, dt * 6);
  for (const n of ['yaw', 'pitch', 'dist', 'ty']) cam[n] += (camTo[n] - cam[n]) * k;
  camera.position.set(Math.sin(cam.yaw) * Math.cos(cam.pitch) * cam.dist, cam.ty + Math.sin(cam.pitch) * cam.dist, Math.cos(cam.yaw) * Math.cos(cam.pitch) * cam.dist);
  camera.lookAt(0, cam.ty, 0);
}
function resize() {
  const r = view.getBoundingClientRect();
  renderer.setSize(r.width, r.height, false);
  camera.aspect = r.width / r.height;
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);
new ResizeObserver(resize).observe(view);
resize();

// ---------- character ----------
let model = null;
let regions = []; // { soft, bone, restQ, p, v }
let loadId = 0;
const loader = new GLTFLoader();
const cache = new Map();
const val = (id) => +$(id).value;

function disposeCurrent() {
  if (!model) return;
  scene.remove(model);
  for (const r of regions) r.soft.geo.dispose();
  model.traverse((o) => o.geometry?.dispose());
  model = null;
  regions = [];
}

async function loadChar(c) {
  const my = ++loadId;
  $('#loading').classList.remove('hidden');
  $('#loading').textContent = TX.loading;
  let gltf = cache.get(c.file);
  if (!gltf) {
    try {
      gltf = await loader.loadAsync(`${c.file}?v=${VERSION}`);
    } catch {
      // not available (blocked for this region, or offline): stay on what is shown
      if (my !== loadId) return;
      $('#loading').textContent = model ? '' : TX.failed;
      if (model) $('#loading').classList.add('hidden');
      chars.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x.textContent === (CHARS.find((k) => k.file === cache.keys().next().value)?.name || CHARS[0].name)));
      return;
    }
    cache.set(c.file, gltf);
  }
  if (my !== loadId) return; // another character was picked meanwhile
  disposeCurrent();
  // a fresh copy every time: the soft regions cut the mesh they are given
  const { clone } = await import('three/addons/utils/SkeletonUtils.js');
  model = clone(gltf.scene);
  scene.add(model);
  model.updateMatrixWorld(true);
  let mesh = null;
  model.traverse((o) => o.isSkinnedMesh && !mesh && (mesh = o));
  mesh.frustumCulled = false;
  mesh.geometry = mesh.geometry.clone();
  for (const [name, a] of Object.entries(mesh.geometry.attributes)) {
    if (a.isInterleavedBufferAttribute) mesh.geometry.setAttribute(name, a.clone());
  }
  // keep the baked colours: no metal
  mesh.material.metalness = 0;
  const P = mesh.geometry.attributes.position.array;
  const hairA = mesh.geometry.attributes._hair?.array || null; // from tools/rig.py
  const box = new THREE.Box3().setFromBufferAttribute(mesh.geometry.attributes.position);
  const h = box.max.y - box.min.y;
  const u = h / 1.9; // the shapes below were measured on a 1.9-unit model
  // the most forward (chest) / backward (glutes) point of a height band on each side
  // centre of a soft region: the median of the ~40 most forward (chest) / backward (glutes)
  // non-hair points of a height band on each side, pushed back inside the body
  const extreme = (lo, hi, facing, xMin, xMax, push) =>
    [-1, 1].map((sd) => {
      const pts = [];
      for (let i = 0; i < P.length; i += 3) {
        if (hairA && hairA[i / 3] > 0.5) continue;
        const x = P[i], y = P[i + 1], z = P[i + 2];
        const ry = (y - box.min.y) / h;
        if (ry > lo && ry < hi && sd * x > xMin * u && sd * x < xMax * u) pts.push([facing * z, x, y, z]);
      }
      pts.sort((p, q) => q[0] - p[0]);
      const top = pts.slice(0, 40);
      const med = (j) => top.map((p) => p[j]).sort((p, q) => p - q)[top.length >> 1];
      const p = new THREE.Vector3(med(1), med(2), med(3));
      p.z -= facing * push * u;
      return p;
    });
  const chestC = extreme(0.62, 0.84, 1, 0.01, 0.2, 0.105);
  // glutes sit just above the crotch (proportions differ per model): find the crotch first =
  // lowest point of the centre column inside the body's depth, between the knees and the waist
  let crotch = 0.47;
  {
    let best = Infinity;
    for (let i = 0; i < P.length; i += 3) {
      const x = P[i], y = P[i + 1], z = P[i + 2];
      const ry = (y - box.min.y) / h;
      if (hairA && hairA[i / 3] > 0.5) continue; // hair hangs down the centre of the back
      if (ry > 0.3 && ry < 0.6 && Math.abs(x) < 0.012 * u && Math.abs(z) < 0.12 * u && ry < best) best = ry;
    }
    if (best < Infinity) crotch = best;
  }
  // one centre per cheek, away from the centre seam
  const hipC = extreme(crotch + 0.01, crotch + 0.14, -1, 0.05, 0.3, 0.1);
  // region size follows the bust: how far the apex stands out from the valley between the
  // breasts (sternum); a bigger bust needs a wider cut or the edge pinches when it scales
  let valley = -Infinity;
  for (let i = 0; i < P.length; i += 3) {
    const ry = (P[i + 1] - box.min.y) / h;
    if (ry > 0.62 && ry < 0.84 && Math.abs(P[i]) < 0.008 * u && P[i + 2] > valley) valley = P[i + 2];
  }
  const apexZ = (chestC[0].z + chestC[1].z) / 2 + 0.105 * u;
  const bust = valley > -Infinity ? apexZ - valley : 0.08 * u;
  const chestR = THREE.MathUtils.clamp(0.08 * u + bust * 1.3, 0.13 * u, 0.2 * u);
  const chest = new SoftChest(mesh, chestC, { radius: chestR, facing: 1, skip: hairA });
  const hips = new SoftChest(mesh, hipC, { radius: 0.16 * u, facing: -1, skip: hairA });
  for (const s of [chest, hips]) {
    mesh.parent.add(s.mesh);
    s.mesh.position.copy(mesh.position);
    s.mesh.quaternion.copy(mesh.quaternion);
    s.mesh.scale.copy(mesh.scale);
    s.soft = val('#soft');
  }
  chest.setSize(val('#size'));
  hips.setSize(val('#hip'));
  const B = (n) => model.getObjectByName(n);
  regions = [
    { soft: chest, bone: B('Spine2') },
    { soft: hips, bone: B('Hips') },
  ];
  for (const r of regions) {
    r.restQ = r.bone.getWorldQuaternion(new THREE.Quaternion());
    r.p = r.bone.getWorldPosition(new THREE.Vector3());
    r.v = new THREE.Vector3();
  }
  chestY = (chestC[0].y + chestC[1].y) / 2;
  hipY = (hipC[0].y + hipC[1].y) / 2;
  setCam(camName);
  $('#loading').classList.add('hidden');
  if (DEV) Object.assign(window, { __soft: chest, __hips: hips, __cam: camera, __dbg: { crotch, bust: +bust.toFixed(3), chestR: +chestR.toFixed(3), u: +u.toFixed(3) } }); // automated checks, dev only
}

// ---------- HUD ----------
const chars = $('#chars');
for (const c of CHARS.filter((x) => x.file && !(REGION_LIMITED && x.id === 'hong'))) {
  const b = document.createElement('button');
  b.textContent = c.name;
  b.addEventListener('click', () => {
    chars.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
    loadChar(c);
  });
  chars.appendChild(b);
}
chars.querySelector('button').classList.add('on');
const pick = (sel, attr, fn) => {
  for (const b of document.querySelectorAll(`${sel} button`)) {
    b.addEventListener('click', () => {
      document.querySelectorAll(`${sel} button`).forEach((x) => x.classList.toggle('on', x === b));
      fn(b.dataset[attr]);
    });
  }
};
pick('#cams', 'cam', setCam);
// slider readouts
for (const id of ['size', 'hip', 'soft']) $(`#${id}`).addEventListener('input', (e) => (e.target.nextElementSibling.textContent = (+e.target.value).toFixed(2)));
$('#size').addEventListener('input', (e) => regions[0]?.soft.setSize(+e.target.value));
$('#hip').addEventListener('input', (e) => regions[1]?.soft.setSize(+e.target.value));
$('#soft').addEventListener('input', (e) => regions.forEach((r) => (r.soft.soft = +e.target.value)));

// ---------- camera input ----------
const pointers = new Map();
let pinch = null;
// which soft region (if any) is under the finger, nothing of the body in front of it
const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
function softHit(e, only = null) {
  if (!model) return null;
  const r = canvas.getBoundingClientRect();
  ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const h = (only ? ray.intersectObject(only.mesh, false) : ray.intersectObjects([model], true))[0];
  const reg = h && regions.find((x) => x.soft.mesh === h.object);
  if (!reg || !h.face) return null;
  return { reg, p: reg.soft.mesh.worldToLocal(h.point.clone()), n: h.face.normal.clone() };
}
let grab = null; // { id, reg, poke }
canvas.addEventListener('pointerdown', (e) => {
  canvas.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pointers.size === 2) {
    if (grab) grab.reg.soft.pressEnd(grab.poke), (grab = null);
    const [a, b] = [...pointers.values()];
    pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), dist: camTo.dist };
    return;
  }
  const h = softHit(e);
  if (h) grab = { id: e.pointerId, reg: h.reg, poke: h.reg.soft.pressStart(h.p, h.n) };
});
canvas.addEventListener('pointermove', (e) => {
  const prev = pointers.get(e.pointerId);
  if (!prev) return;
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pinch && pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    camTo.dist = THREE.MathUtils.clamp((pinch.dist * pinch.d) / Math.max(20, Math.hypot(a.x - b.x, a.y - b.y)), 0.9, 5);
    // two fingers moving together: slide the view up / down the body
    const my = (a.y + b.y) / 2;
    if (pinch.my !== undefined) camTo.ty = THREE.MathUtils.clamp(camTo.ty + (my - pinch.my) * 0.0025 * camTo.dist, 0.1, 1.9);
    pinch.my = my;
    return;
  }
  if (grab === null && (e.buttons & 6 || e.shiftKey) && pointers.size === 1) {
    // right / middle button or shift + drag: pan (computer)
    camTo.ty = THREE.MathUtils.clamp(camTo.ty + (e.clientY - prev.y) * 0.0025 * camTo.dist, 0.1, 1.9);
    document.querySelectorAll('#cams button').forEach((x) => x.classList.remove('on'));
    return;
  }
  if (pointers.size !== 1) return;
  if (grab && grab.id === e.pointerId) {
    // finger slides over the surface: the dent follows (only this region is tested: fast)
    const h = softHit(e, grab.reg.soft);
    if (h) grab.reg.soft.pressMove(grab.poke, h.p, 1 / 60);
    return;
  }
  camTo.yaw -= (e.clientX - prev.x) * 0.008;
  camTo.pitch = THREE.MathUtils.clamp(camTo.pitch + (e.clientY - prev.y) * 0.005, -0.5, 0.9);
  document.querySelectorAll('#cams button').forEach((x) => x.classList.remove('on'));
});
const up = (e) => {
  pointers.delete(e.pointerId);
  if (pointers.size < 2) pinch = null;
  if (grab && grab.id === e.pointerId) {
    grab.reg.soft.pressEnd(grab.poke);
    grab = null;
  }
};
canvas.addEventListener('pointerup', up);
canvas.addEventListener('pointercancel', up);
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  // wheel = zoom; shift + wheel (or a trackpad's sideways scroll) = slide up / down
  if (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) camTo.ty = THREE.MathUtils.clamp(camTo.ty + (e.shiftKey ? e.deltaY : e.deltaX) * 0.0015 * camTo.dist, 0.1, 1.9);
  else camTo.dist = THREE.MathUtils.clamp(camTo.dist * Math.exp(e.deltaY * 0.001), 0.9, 5);
}, { passive: false });
canvas.addEventListener('contextmenu', (e) => e.preventDefault());

// ---------- loop ----------
let t0 = performance.now();
renderer.setAnimationLoop(() => {
  const t = performance.now();
  const dt = Math.min(0.05, (t - t0) / 1000);
  t0 = t;
  for (const r of regions) r.soft.update(dt);
  placeCamera(dt);
  renderer.render(scene, camera);
});

loadChar(CHARS[0]);
