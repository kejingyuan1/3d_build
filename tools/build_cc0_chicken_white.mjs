#!/usr/bin/env node
// build_cc0_chicken_white.mjs — 白鸡样本：blujay 静态鸡 → 程序化骨骼 + walk/eat 动画 GLB
// 与 build_cc0_chicken.mjs 同管线，仅换白鸡色板（spec §2.2）
// 用法: node tools/build_cc0_chicken_white.mjs
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { readFileSync, writeFileSync } from 'node:fs';

globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}
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

const SRC = 'assets/_cc0_src/chicken_blujay_raw.glb';
const OUT = 'assets/animals/staging/animal_chicken_white_b.glb';
const TARGET_H = 0.5;          // spec §2.2 白鸡身高
const WALK_T = 1.6, EAT_T = 1.4;

// spec §2.2 白鸡色板
const PALETTE = {
  body: 0xF0EDE4, // 羽暖白（禁纯白）
  wing: 0xE8E2D6, // 翼羽暖白微灰
  tail: 0xDED8CA, // 尾羽暖白略深
  comb: 0xD6452A, // 冠/肉垂鲜红
  beak: 0xE0A93C, // 喙金黄
  leg:  0xE0A93C, // 腿金黄
};

const log = [];
const L = (m) => { log.push(String(m)); };

function makeMat(color, roughness, name) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0, name: 'mat_' + name });
}

function loadGLB(path) {
  return new Promise((resolve, reject) => {
    const data = readFileSync(path);
    new GLTFLoader().parse(data.buffer, '', resolve, reject);
  });
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

function main() {
  loadGLB(SRC).then((gltf) => {
    // ---------- 0. 收集 7 个部件 mesh ----------
    const byMat = {};
    gltf.scene.traverse(o => {
      if (o.isMesh && o.material) {
        const nm = o.material.name;
        byMat[nm] = byMat[nm] || [];
        byMat[nm].push(o);
      }
    });
    L(`[0] loaded parts: ${Object.keys(byMat).join(', ')}`);

    // ---------- 1. 对齐 bake：旋转 +90°(Y) 使头朝 +Z，再按 bbox 缩放/平移 ----------
    const M = new THREE.Matrix4().makeRotationY(Math.PI / 2);
    for (const arr of Object.values(byMat)) {
      for (const m of arr) {
        m.geometry.applyMatrix4(M);
        m.geometry.computeBoundingBox();
      }
    }
    const box = new THREE.Box3();
    for (const arr of Object.values(byMat)) for (const m of arr) box.expandByObject(m);
    const size = box.getSize(new THREE.Vector3());
    const scale = TARGET_H / size.y;
    const tx = -(box.min.x + box.max.x) / 2 * scale;
    const tz = -(box.min.z + box.max.z) / 2 * scale;
    const ty = -box.min.y * scale;
    for (const arr of Object.values(byMat)) {
      for (const m of arr) {
        m.geometry.scale(scale, scale, scale);
        m.geometry.translate(tx, ty, tz);
        m.geometry.computeBoundingBox();
      }
    }
    L(`[1] align: scale=${scale.toFixed(4)} t=(${tx.toFixed(4)},${ty.toFixed(4)},${tz.toFixed(4)})`);

    // ---------- 2. 部件语义 + 拆腿 ----------
    const parts = {};
    for (const [matName, arr] of Object.entries(byMat)) {
      const b = new THREE.Box3();
      arr.forEach(m => b.expandByObject(m));
      parts[matName] = { arr, b };
      L(`[2] ${matName}: min=(${b.min.x.toFixed(3)},${b.min.y.toFixed(3)},${b.min.z.toFixed(3)}) max=(${b.max.x.toFixed(3)},${b.max.y.toFixed(3)},${b.max.z.toFixed(3)})`);
    }
    const rootParts = [];
    let combMesh = null, beakMesh = null;
    const legMeshes = [];
    for (const [matName, { arr, b }] of Object.entries(parts)) {
      if (matName === 'pale_red') combMesh = arr[0];
      else if (matName === 'gold') beakMesh = arr[0];
      else if (matName === 'buttermilk') legMeshes.push(...arr);
      else rootParts.push(...arr);
    }
    function splitLegByZ(mesh, side) {
      const g = mesh.geometry;
      const pos = g.attributes.position;
      const idx = g.index;
      if (!idx) return null;
      const tris = [];
      for (let i = 0; i < idx.count; i += 3) {
        const a = idx.getX(i), b = idx.getX(i + 1), c = idx.getX(i + 2);
        const za = pos.getZ(a), zb = pos.getZ(b), zc = pos.getZ(c);
        const zc_mid = (za + zb + zc) / 3;
        if (side === -1 && zc_mid < 0) tris.push([a, b, c]);
        else if (side === 1 && zc_mid > 0) tris.push([a, b, c]);
      }
      if (tris.length === 0) return null;
      const vmap = new Map();
      const newPos = [], newIdx = [];
      for (const t of tris) {
        for (const vi of t) {
          if (!vmap.has(vi)) {
            vmap.set(vi, newPos.length);
            newPos.push(pos.getX(vi), pos.getY(vi), pos.getZ(vi));
          }
          newIdx.push(vmap.get(vi));
        }
      }
      const ng = new THREE.BufferGeometry();
      ng.setAttribute('position', new THREE.Float32BufferAttribute(newPos, 3));
      ng.setIndex(newIdx);
      ng.computeVertexNormals();
      ng.computeBoundingBox();
      return new THREE.Mesh(ng, mesh.material.clone());
    }
    let legMeshL = null, legMeshR = null;
    for (const lm of legMeshes) {
      const l = splitLegByZ(lm, -1);
      const r = splitLegByZ(lm, 1);
      if (l) legMeshL = l;
      if (r) legMeshR = r;
    }
    L(`[2] split legs: L=${legMeshL ? 'OK(' + legMeshL.geometry.attributes.position.count + 'v)' : 'NONE'} R=${legMeshR ? 'OK(' + legMeshR.geometry.attributes.position.count + 'v)' : 'NONE'}`);

    // ---------- 3. 重命名 + 重涂白鸡 PBR ----------
    function repaint(mesh, colorHex, matName, rough) {
      mesh.name = 'mesh_' + matName;
      mesh.material = makeMat(colorHex, rough, matName);
      mesh.castShadow = true;
    }
    for (const m of rootParts) {
      const nm = m.material.name;
      if (nm === 'white') repaint(m, PALETTE.body, 'body', 0.85);
      else if (nm === 'pale_grey') repaint(m, PALETTE.wing, 'wing', 0.85);
      else if (nm === 'mid_grey') repaint(m, PALETTE.wing, 'wing_2', 0.85);
      else if (nm === 'black') repaint(m, PALETTE.tail, 'tail', 0.9);
      else repaint(m, PALETTE.body, 'body_other', 0.85);
    }
    if (combMesh) repaint(combMesh, PALETTE.comb, 'comb', 0.45);
    if (beakMesh) repaint(beakMesh, PALETTE.beak, 'beak', 0.5);
    if (legMeshL) repaint(legMeshL, PALETTE.leg, 'leg_L', 0.55);
    if (legMeshR) repaint(legMeshR, PALETTE.leg, 'leg_R', 0.55);
    L('[3] repainted PBR + renamed (white)');

    // ---------- 4. 构建骨骼 ----------
    const rig = new THREE.Group();
    rig.name = 'chicken_white_b';
    const rootBone = new THREE.Bone();
    rootBone.name = 'bone_root';
    rig.add(rootBone);
    const bodyBox = new THREE.Box3();
    rootParts.forEach(m => bodyBox.expandByObject(m));
    const bodyC = bodyBox.getCenter(new THREE.Vector3());
    rootBone.position.copy(bodyC);
    for (const m of rootParts) rootBone.attach(m);
    const neckBone = new THREE.Bone();
    neckBone.name = 'bone_neck';
    rootBone.add(neckBone);
    if (combMesh) {
      const cb = new THREE.Box3().setFromObject(combMesh);
      neckBone.position.set(cb.min.x, cb.min.y, (cb.min.z + cb.max.z) / 2);
      neckBone.attach(combMesh);
    } else {
      neckBone.position.set(0, 0.35, 0.15);
    }
    const beakBone = new THREE.Bone();
    beakBone.name = 'bone_beak';
    neckBone.add(beakBone);
    if (beakMesh) {
      const bb = new THREE.Box3().setFromObject(beakMesh);
      beakBone.position.set((bb.min.x + bb.max.x) / 2, (bb.min.y + bb.max.y) / 2, bb.min.z);
      beakBone.attach(beakMesh);
    } else {
      beakBone.position.set(0, 0, 0.1);
    }
    function makeLegBone(mesh, side) {
      const bone = new THREE.Bone();
      bone.name = side < 0 ? 'bone_leg_L' : 'bone_leg_R';
      rootBone.add(bone);
      if (mesh) {
        const lb = new THREE.Box3().setFromObject(mesh);
        bone.position.set((lb.min.x + lb.max.x) / 2, lb.max.y, (lb.min.z + lb.max.z) / 2);
        bone.attach(mesh);
      }
      return bone;
    }
    const legLBone = makeLegBone(legMeshL, -1);
    const legRBone = makeLegBone(legMeshR, 1);
    L(`[4] bones: root@(${rootBone.position.x.toFixed(3)},${rootBone.position.y.toFixed(3)},${rootBone.position.z.toFixed(3)}) neck@(${neckBone.position.x.toFixed(3)},${neckBone.position.y.toFixed(3)},${neckBone.position.z.toFixed(3)}) beak@(${beakBone.position.x.toFixed(3)},${beakBone.position.y.toFixed(3)},${beakBone.position.z.toFixed(3)}) legL@(${legLBone.position.x.toFixed(3)},${legLBone.position.y.toFixed(3)},${legLBone.position.z.toFixed(3)}) legR@(${legRBone.position.x.toFixed(3)},${legRBone.position.y.toFixed(3)},${legRBone.position.z.toFixed(3)})`);

    // ---------- 5. 骨骼动画 ----------
    function sampleTimes(T) {
      const n = 24;
      const ts = [];
      for (let i = 0; i <= n; i++) ts.push((i / n) * T);
      return ts;
    }
    const walkTimes = sampleTimes(WALK_T);
    const walkTracks = [];
    walkTracks.push(quatTrack(legLBone, 'rotation', walkTimes, t => {
      const s = Math.sin(t * 2 * Math.PI / WALK_T) * 0.5;
      return [s, 0, 0];
    }));
    walkTracks.push(quatTrack(legRBone, 'rotation', walkTimes, t => {
      const s = -Math.sin(t * 2 * Math.PI / WALK_T) * 0.5;
      return [s, 0, 0];
    }));
    walkTracks.push(vecTrack(rootBone, 'position', walkTimes, t => {
      const y = Math.abs(Math.sin(t * 2 * Math.PI / WALK_T)) * 0.03;
      return [bodyC.x, bodyC.y + y, bodyC.z];
    }));
    walkTracks.push(quatTrack(neckBone, 'rotation', walkTimes, t => {
      const s = Math.sin(t * 2 * Math.PI / WALK_T + 0.6) * 0.05;
      return [s, 0, 0];
    }));
    const walkClip = new THREE.AnimationClip('walk', WALK_T, walkTracks);
    const eatTimes = sampleTimes(EAT_T);
    const eatTracks = [];
    eatTracks.push(quatTrack(neckBone, 'rotation', eatTimes, t => {
      const env = Math.sin(t * Math.PI / EAT_T) ** 2;
      return [-0.55 * env, 0, 0];
    }));
    eatTracks.push(quatTrack(beakBone, 'rotation', eatTimes, t => {
      const env = Math.sin(t * Math.PI / EAT_T) ** 2;
      return [0.35 * Math.sin(t * 4 * Math.PI / EAT_T) * env, 0, 0];
    }));
    eatTracks.push(vecTrack(rootBone, 'position', eatTimes, t => {
      const env = Math.sin(t * Math.PI / EAT_T) ** 2;
      return [bodyC.x, bodyC.y + 0.01 * env, bodyC.z + 0.035 * env];
    }));
    const eatClip = new THREE.AnimationClip('eat', EAT_T, eatTracks);
    L(`[5] clips: walk(${walkClip.duration}s, ${walkTracks.length} tracks) eat(${eatClip.duration}s, ${eatTracks.length} tracks)`);

    // ---------- 6. 导出 ----------
    const exporter = new GLTFExporter();
    const options = { binary: true, animations: [walkClip, eatClip] };
    exporter.parse(rig, (result) => {
      writeFileSync(OUT, Buffer.from(result));
      L(`[6] wrote ${OUT}`);
      let tris = 0, vcount = 0, meshCount = 0, boneCount = 0;
      rig.traverse(o => {
        if (o.isMesh) { meshCount++; const gg = o.geometry; tris += gg.index ? gg.index.count / 3 : gg.attributes.position.count / 3; vcount += gg.attributes.position.count; }
        if (o.isBone) boneCount++;
      });
      const bb = new THREE.Box3().setFromObject(rig);
      L(`[6] meshes=${meshCount} bones=${boneCount} tris=${Math.round(tris)} verts=${vcount} height=${(bb.max.y - bb.min.y).toFixed(3)}m feetY=${bb.min.y.toFixed(4)}`);
      L('=====');
      L(log.join('\n'));
      console.log(log.join('\n'));
    }, (err) => {
      L('[6] EXPORT ERROR: ' + err);
      console.log(log.join('\n'));
      process.exit(1);
    }, options);
  }).catch((e) => {
    L('LOAD ERROR: ' + (e && e.message ? e.message : String(e)));
    console.log(log.join('\n'));
    process.exit(1);
  });
}
main();
