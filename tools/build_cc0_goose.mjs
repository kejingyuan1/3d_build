#!/usr/bin/env node
// build_cc0_goose.mjs — 鹅样本：程序化卡通鹅（spec §2.8 长颈/橙喙/蹼足/站立高≈0.65m）
// + 程序化骨骼（root/neck/head/legL/legR）+ idle/walk/eat 动画
// 几何统一用世界坐标 → bone.attach 保持世界位姿
// 用法: node tools/build_cc0_goose.mjs
import * as THREE from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { writeFileSync } from 'node:fs';

globalThis.self = globalThis;
if (typeof globalThis.FileReader === 'undefined') {
  globalThis.FileReader = class {
    readAsArrayBuffer(blob) {
      blob.arrayBuffer().then((buf) => {
        this.result = buf;
        if (this.onloadend) this.onloadend();
        if (this.onload) this.onload();
      });
    }
    readAsDataURL(blob) {
      blob.arrayBuffer().then((buf) => {
        this.result = 'data:application/octet-stream;base64,' + Buffer.from(buf).toString('base64');
        if (this.onloadend) this.onloadend();
        if (this.onload) this.onload();
      });
    }
  };
}

const OUT = 'assets/animals/staging/lifecycle_goose_adult_b.glb';
const IDLE_T = 4.0, WALK_T = 1.6, EAT_T = 1.6;

// spec §2.8 白鹅色板
const C = {
  body:  0xF2F0E8, // 羽暖白
  beak:  0xE8933A, // 喙橙
  beakT: 0x8A4A1E, // 喙尖端深
  foot:  0xD98A3A, // 蹼足橙
  eye:   0x1A1A1A, // 眼黑
};

const log = [];
const L = (m) => { log.push(String(m)); };

function makeMat(color, roughness, name) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0, name: 'mat_' + name });
}

function ellipsoid(rx, ry, rz, mat, name, x, y, z) {
  const g = new THREE.SphereGeometry(1, 18, 12);
  g.scale(rx, ry, rz);
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, mat);
  m.name = 'mesh_' + name;
  m.position.set(x, y, z);
  m.castShadow = true;
  return m;
}

function cone(rt, rb, h, mat, name, x, y, z, rx = 0) {
  const g = new THREE.CylinderGeometry(rt, rb, h, 10, 1, false);
  g.translate(0, h / 2, 0); // 底部在局部 y=0
  g.computeVertexNormals();
  const m = new THREE.Mesh(g, mat);
  m.name = 'mesh_' + name;
  m.position.set(x, y, z);
  m.rotation.x = rx;
  m.castShadow = true;
  return m;
}

function quatTrack(bone, prop, times, eulerFn) {
  const vals = [];
  const e = new THREE.Euler();
  const q = new THREE.Quaternion();
  for (const t of times) {
    const [x, y, z] = eulerFn(t);
    e.set(x, y, z);
    q.setFromEuler(e);
    vals.push(q.x, q.y, q.z, q.w);
  }
  return new THREE.QuaternionKeyframeTrack(`${bone.name}.quaternion`, times, vals);
}
function vecTrack(bone, prop, times, vecFn) {
  const vals = [];
  for (const t of times) {
    const v = vecFn(t);
    vals.push(v[0], v[1], v[2]);
  }
  return new THREE.VectorKeyframeTrack(`${bone.name}.position`, times, vals);
}
function sampleTimes(T) {
  const n = 24;
  const ts = [];
  for (let i = 0; i <= n; i++) ts.push((i / n) * T);
  return ts;
}

function main() {
  const rig = new THREE.Group();
  rig.name = 'goose_adult_b';

  const matBody = makeMat(C.body, 0.85, 'plumage_body');
  const matBeak = makeMat(C.beak, 0.5, 'beak');
  const matBeakT = makeMat(C.beakT, 0.5, 'beak_tip');
  const matFoot = makeMat(C.foot, 0.55, 'foot');
  const matEye = makeMat(C.eye, 0.2, 'eye');

  // ---- 世界坐标布局（面对 +Z，脚底 y=0）----
  // 身体
  const body = ellipsoid(0.26, 0.20, 0.34, matBody, 'body', 0, 0.26, 0);
  const wingL = ellipsoid(0.05, 0.14, 0.28, matBody, 'wing_L', -0.24, 0.28, 0);
  const wingR = ellipsoid(0.05, 0.14, 0.28, matBody, 'wing_R', 0.24, 0.28, 0);
  const tail = cone(0.03, 0.08, 0.16, matBody, 'tail', 0, 0.34, -0.40, 0.6);
  // 颈（两段 S 形）
  const neck1 = cone(0.045, 0.065, 0.18, matBody, 'neck_1', 0, 0.46, 0.20, 0.55);
  const neck2 = cone(0.035, 0.048, 0.16, matBody, 'neck_2', 0, 0.57, 0.11, -0.5);
  // 头 + 喙 + 眼
  const head = ellipsoid(0.055, 0.055, 0.07, matBody, 'head', 0, 0.60, 0.06);
  const beak = cone(0.015, 0.035, 0.10, matBeak, 'beak', 0, 0.585, 0.125, 1.35);
  const beakTip = cone(0.010, 0.018, 0.045, matBeakT, 'beak_tip', 0, 0.575, 0.19, 1.35);
  const eyeL = ellipsoid(0.012, 0.012, 0.012, matEye, 'eye_L', -0.048, 0.605, 0.10);
  const eyeR = ellipsoid(0.012, 0.012, 0.012, matEye, 'eye_R', 0.048, 0.605, 0.10);
  // 蹼足
  const footL = ellipsoid(0.10, 0.02, 0.14, matFoot, 'foot_L', -0.09, 0.02, 0.06);
  const footR = ellipsoid(0.10, 0.02, 0.14, matFoot, 'foot_R', 0.09, 0.02, 0.06);

  // ---- 骨骼（世界坐标 pivot） ----
  const rootBone = new THREE.Bone();
  rootBone.name = 'bone_root';
  rig.add(rootBone);
  rootBone.position.set(0, 0.26, 0);

  const neckBone = new THREE.Bone();
  neckBone.name = 'bone_neck';
  rootBone.add(neckBone);
  neckBone.position.set(0, 0.44, 0.20); // 颈根（身体前上端）

  const headBone = new THREE.Bone();
  headBone.name = 'bone_head';
  neckBone.add(headBone);
  headBone.position.set(0, 0.16, -0.06); // 相对 neckBone：头顶部

  const legLBone = new THREE.Bone();
  legLBone.name = 'bone_leg_L';
  rootBone.add(legLBone);
  legLBone.position.set(-0.09, 0.05, 0.06);
  const legRBone = new THREE.Bone();
  legRBone.name = 'bone_leg_R';
  rootBone.add(legRBone);
  legRBone.position.set(0.09, 0.05, 0.06);

  // ---- attach（保持世界位姿） ----
  rootBone.attach(body);
  rootBone.attach(wingL);
  rootBone.attach(wingR);
  rootBone.attach(tail);
  neckBone.attach(neck1);
  neckBone.attach(neck2);
  headBone.attach(head);
  headBone.attach(beak);
  headBone.attach(beakTip);
  headBone.attach(eyeL);
  headBone.attach(eyeR);
  legLBone.attach(footL);
  legRBone.attach(footR);

  L(`[0] bones: root@(${rootBone.position.x.toFixed(2)},${rootBone.position.y.toFixed(2)},${rootBone.position.z.toFixed(2)}) neck@(${neckBone.position.x.toFixed(2)},${neckBone.position.y.toFixed(2)},${neckBone.position.z.toFixed(2)}) head@(${headBone.position.x.toFixed(2)},${headBone.position.y.toFixed(2)},${headBone.position.z.toFixed(2)}) legL@(${legLBone.position.x.toFixed(2)},${legLBone.position.y.toFixed(2)},${legLBone.position.z.toFixed(2)}) legR@(${legRBone.position.x.toFixed(2)},${legRBone.position.y.toFixed(2)},${legRBone.position.z.toFixed(2)})`);

  // ---- 统一缩放到目标站立高 0.65m（脚底 y=0） ----
  const bb0 = new THREE.Box3().setFromObject(rig);
  const S = 0.65 / bb0.max.y;
  L(`[0] pre-scale height=${bb0.max.y.toFixed(3)} S=${S.toFixed(4)}`);
  rig.traverse(o => {
    if (o.isMesh) { o.geometry.scale(S, S, S); o.geometry.computeBoundingBox(); o.geometry.computeBoundingSphere(); }
    if (o.position) o.position.multiplyScalar(S);
  });
  rig.updateMatrixWorld(true);
  const bodyC = new THREE.Vector3(0, 0.26 * S, 0);
  const bb1 = new THREE.Box3().setFromObject(rig);
  L(`[0] post-scale height=${(bb1.max.y - bb1.min.y).toFixed(3)} feetY=${bb1.min.y.toFixed(4)}`);

  // ---- 动画 ----
  const idleTimes = sampleTimes(IDLE_T);
  const idleTracks = [];
  idleTracks.push(vecTrack(rootBone, 'position', idleTimes, t => {
    const y = Math.abs(Math.sin(t * 2 * Math.PI / IDLE_T)) * 0.012;
    return [bodyC.x, bodyC.y + y, bodyC.z];
  }));
  idleTracks.push(quatTrack(neckBone, 'rotation', idleTimes, t => {
    const s = Math.sin(t * 2 * Math.PI / IDLE_T) * 0.05;
    return [0, 0, s];
  }));
  const idleClip = new THREE.AnimationClip('idle', IDLE_T, idleTracks);

  const walkTimes = sampleTimes(WALK_T);
  const walkTracks = [];
  walkTracks.push(quatTrack(legLBone, 'rotation', walkTimes, t => {
    const s = Math.sin(t * 2 * Math.PI / WALK_T) * 0.35;
    return [s, 0, 0];
  }));
  walkTracks.push(quatTrack(legRBone, 'rotation', walkTimes, t => {
    const s = -Math.sin(t * 2 * Math.PI / WALK_T) * 0.35;
    return [s, 0, 0];
  }));
  walkTracks.push(vecTrack(rootBone, 'position', walkTimes, t => {
    const y = Math.abs(Math.sin(t * 2 * Math.PI / WALK_T)) * 0.03;
    return [bodyC.x, bodyC.y + y, bodyC.z];
  }));
  walkTracks.push(quatTrack(neckBone, 'rotation', walkTimes, t => {
    const s = Math.sin(t * 2 * Math.PI / WALK_T + 0.6) * 0.06;
    return [s, 0, 0];
  }));
  const walkClip = new THREE.AnimationClip('walk', WALK_T, walkTracks);

  const eatTimes = sampleTimes(EAT_T);
  const eatTracks = [];
  eatTracks.push(quatTrack(neckBone, 'rotation', eatTimes, t => {
    const env = Math.sin(t * Math.PI / EAT_T) ** 2;
    return [-0.55 * env, 0, 0]; // 颈下俯到地面啄食
  }));
  eatTracks.push(vecTrack(rootBone, 'position', eatTimes, t => {
    const env = Math.sin(t * Math.PI / EAT_T) ** 2;
    return [bodyC.x, bodyC.y + 0.01 * env, bodyC.z + 0.02 * env];
  }));
  const eatClip = new THREE.AnimationClip('eat', EAT_T, eatTracks);
  L(`[1] clips: idle(${idleClip.duration}s,${idleTracks.length}t) walk(${walkClip.duration}s,${walkTracks.length}t) eat(${eatClip.duration}s,${eatTracks.length}t)`);

  // ---- 导出 ----
  const exporter = new GLTFExporter();
  const options = { binary: true, animations: [idleClip, walkClip, eatClip] };
  exporter.parse(rig, (result) => {
    writeFileSync(OUT, Buffer.from(result));
    L(`[2] wrote ${OUT} (${(Buffer.from(result).length / 1024).toFixed(1)} KB)`);
    let tris = 0, vcount = 0, meshCount = 0, boneCount = 0;
    rig.traverse(o => {
      if (o.isMesh) { meshCount++; const gg = o.geometry; tris += gg.index ? gg.index.count / 3 : gg.attributes.position.count / 3; vcount += gg.attributes.position.count; }
      if (o.isBone) boneCount++;
    });
    const bb = new THREE.Box3().setFromObject(rig);
    L(`[2] meshes=${meshCount} bones=${boneCount} tris=${Math.round(tris)} verts=${vcount} height=${(bb.max.y - bb.min.y).toFixed(3)}m feetY=${bb.min.y.toFixed(4)} z=${bb.min.z.toFixed(2)}..${bb.max.z.toFixed(2)} x=${bb.min.x.toFixed(2)}..${bb.max.x.toFixed(2)}`);
    L('=====');
    L(log.join('\n'));
    console.log(log.join('\n'));
  }, (err) => {
    L('[2] EXPORT ERROR: ' + err);
    console.log(log.join('\n'));
    process.exit(1);
  }, options);
}
main();
