// Procedural animations for the auto-rigged character (Mixamo-style bone names, no fingers).
// Each animation returns, per bone, a rotation about CHARACTER axes (x = her left, y = up,
// z = forward) plus a hips offset and a turn. The animator converts character-space rotations
// to each bone's local frame from the rest pose, and cross-fades between animations.
import * as THREE from 'three';

const q = (x = 0, y = 0, z = 0) => new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, 'YXZ'));
const TAU = Math.PI * 2;

// arms a little closer to the body than the A-pose they were modelled in
const ARMS_DOWN = 0.32;

const ANIMS = {
  idle(t) {
    const br = Math.sin(t * 1.6);
    const sway = Math.sin(t * 0.7);
    return {
      bones: {
        Hips: q(0, 0.03 * sway, 0.025 * sway),
        Spine: q(0.012 * br, 0, -0.015 * sway),
        Spine1: q(0.018 * br, 0, 0),
        Spine2: q(-0.012 * br, 0, 0),
        Neck: q(0, 0, 0.01 * sway),
        Head: q(0.03 * Math.sin(t * 0.5), 0.12 * Math.sin(t * 0.37), 0.04 * sway),
        LeftArm: q(0.04 * br, 0, -ARMS_DOWN + 0.02 * br),
        RightArm: q(0.04 * br, 0, ARMS_DOWN - 0.02 * br),
        LeftForeArm: q(0, 0, -0.12),
        RightForeArm: q(0, 0, 0.12),
        LeftShoulder: q(0, 0, 0.015 * br),
        RightShoulder: q(0, 0, -0.015 * br),
      },
      hips: new THREE.Vector3(0.012 * sway, -0.004 * (1 + br), 0),
    };
  },
  wave(t) {
    const base = ANIMS.idle(t);
    const w = Math.sin(t * 7);
    Object.assign(base.bones, {
      RightArm: q(0.25, 0, -2.05),
      RightForeArm: q(0, 0, -0.55 + 0.42 * w),
      RightHand: q(0, 0, 0.2 * w),
      Head: q(0.04, -0.15, -0.1),
      Spine1: q(0, 0, 0.05),
    });
    return base;
  },
  dance(t) {
    const beat = t * 2; // 120 bpm
    const bob = Math.abs(Math.sin(Math.PI * beat));
    const side = Math.sin(Math.PI * beat * 0.5);
    const arm = Math.sin(Math.PI * beat);
    return {
      bones: {
        Hips: q(0, 0.18 * side, 0.1 * side),
        Spine: q(0.04 * bob, -0.1 * side, -0.07 * side),
        Spine1: q(0.03 * bob, -0.06 * side, -0.05 * side),
        Head: q(0.1 * bob - 0.03, 0.1 * side, 0.08 * side),
        LeftUpLeg: q(-0.32 * bob, 0, 0.04),
        RightUpLeg: q(-0.32 * bob, 0, -0.04),
        LeftLeg: q(0.62 * bob, 0, 0),
        RightLeg: q(0.62 * bob, 0, 0),
        LeftFoot: q(-0.3 * bob, 0, 0),
        RightFoot: q(-0.3 * bob, 0, 0),
        LeftArm: q(0.3, 0, 0.35 + 0.45 * arm),
        RightArm: q(0.3, 0, -0.35 + 0.45 * arm),
        LeftForeArm: q(0, 0, 0.9),
        RightForeArm: q(0, 0, -0.9),
      },
      hips: new THREE.Vector3(0.04 * side, -0.05 * bob, 0),
    };
  },
  pose(t) {
    const s = Math.sin(t * 0.9);
    return {
      bones: {
        Hips: q(0, 0.1, 0.12 + 0.02 * s),
        Spine: q(0.02, -0.06, -0.1),
        Spine1: q(0.03, -0.05, -0.06 - 0.02 * s),
        Spine2: q(-0.02, 0, 0),
        Head: q(0.05, 0.22, 0.16 + 0.03 * s),
        LeftUpLeg: q(0, 0, -0.05),
        RightUpLeg: q(-0.12, 0.15, 0.1),
        RightLeg: q(0.25, 0, 0),
        LeftArm: q(-0.15, 0, -0.18),
        RightArm: q(0.1, 0, 0.45),
        LeftForeArm: q(0, 0.4, -0.75),
        RightForeArm: q(0, 0, 0.25),
      },
      hips: new THREE.Vector3(0.04, -0.01, 0),
    };
  },
  walk(t) {
    const ph = t * TAU * 0.95;
    const s = Math.sin(ph);
    const c = Math.cos(ph);
    return {
      bones: {
        Hips: q(0, 0.09 * s, 0.035 * c),
        Spine: q(0.03, -0.06 * s, -0.02 * c),
        Spine1: q(0.02, -0.05 * s, 0),
        Head: q(0, 0.06 * s, 0),
        LeftUpLeg: q(-0.42 * s, 0, 0),
        RightUpLeg: q(0.42 * s, 0, 0),
        LeftLeg: q(0.75 * Math.max(0, Math.sin(ph + 1.1)), 0, 0),
        RightLeg: q(0.75 * Math.max(0, Math.sin(ph + 1.1 + Math.PI)), 0, 0),
        LeftFoot: q(0.18 * c, 0, 0),
        RightFoot: q(-0.18 * c, 0, 0),
        LeftArm: q(0.38 * s, 0, -ARMS_DOWN - 0.08),
        RightArm: q(-0.38 * s, 0, ARMS_DOWN + 0.08),
        LeftForeArm: q(0, 0, -0.3),
        RightForeArm: q(0, 0, 0.3),
      },
      hips: new THREE.Vector3(0, -0.025 * Math.abs(c), 0),
    };
  },
  spin(t) {
    return ANIMS.idle(t);
  },
};
export const ANIM_NAMES = Object.keys(ANIMS);

export class Animator {
  constructor(root) {
    this.root = root;
    this.bones = {};
    this.restQ = {};
    this.restW = {};
    this.restWInv = {};
    root.updateMatrixWorld(true);
    const rootInv = root.getWorldQuaternion(new THREE.Quaternion()).invert();
    root.traverse((o) => {
      if (!o.isBone) return;
      this.bones[o.name] = o;
      this.restQ[o.name] = o.quaternion.clone();
      const w = rootInv.clone().multiply(o.getWorldQuaternion(new THREE.Quaternion()));
      this.restW[o.name] = w;
      this.restWInv[o.name] = w.clone().invert();
    });
    this.hips = this.bones.Hips;
    this.hipsRest = this.hips?.position.clone();
    this.cur = 'idle';
    this.prev = null;
    this.fade = 1;
    this.t = 0;
    this.turn = 0;
  }

  play(name) {
    if (!ANIMS[name] || name === this.cur) return;
    this.prev = this.cur;
    this.cur = name;
    this.fade = 0;
  }

  update(dt) {
    this.t += dt;
    this.fade = Math.min(1, this.fade + dt / 0.45);
    const k = this.fade * this.fade * (3 - 2 * this.fade);
    const a = ANIMS[this.cur](this.t);
    const b = this.prev && k < 1 ? ANIMS[this.prev](this.t) : null;
    const id = new THREE.Quaternion();
    const tmp = new THREE.Quaternion();
    for (const name of Object.keys(this.bones)) {
      const ra = a.bones[name] || id;
      const R = b ? (b.bones[name] || id).clone().slerp(ra, k) : ra;
      // character-space rotation → this bone's local frame
      tmp.copy(this.restWInv[name]).multiply(R).multiply(this.restW[name]);
      this.bones[name].quaternion.copy(this.restQ[name]).multiply(tmp);
    }
    if (this.hips) {
      const off = b ? b.hips.clone().lerp(a.hips, k) : a.hips;
      this.hips.position.copy(this.hipsRest).add(off);
    }
    // facing: spin keeps turning her; anything else eases back to the nearest front
    if (this.cur === 'spin') this.turn += dt * 0.7 * k;
    else this.turn += (Math.round(this.turn / TAU) * TAU - this.turn) * Math.min(1, dt * 2.5);
    this.root.rotation.y = this.turn;
  }
}
