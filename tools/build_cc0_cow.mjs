#!/usr/bin/env node
// build_cc0_cow.mjs — 棕牛样本：静态 quaternius_Cow（干净）→ 程序化骨骼 + idle/walk/eat 动画 GLB
// 背景：animated 牛 GLB skinWeight 75% NaN 损坏 → 弃用，走静态几何 + 程序骨骼（鸡样本同款管线）
// 用法: node tools/build_cc0_cow.mjs
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

const SRC = 'assets/quaternius_farm_animals_glb/quaternius_Cow.glb';
const OUT = 'assets/animals/staging/animal_cow_brown_b.glb';
const TARGET_H = 1.5;          // spec §2.3 头高 ≈ 1.5m（肩 ≈ 1.35m）
const IDLE_T = 4.0, WALK_T = 1.6, EAT_T = 1.6;

// spec §2.3 棕牛色板（单材质简化版）
const PALETTE = {
  body:  0x8B5A3A, // 身毛暖棕
  leg:   0x3A3A3A, // 蹄/腿深灰
  head:  0x7A4E32, // 头略深
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

// 通用三角形重建（带越界/NaN 防护：坏三角形直接丢弃）
function rebuildTris(mesh, tris) {
  if (!tris || tris.length === 0) return null;
  const g = mesh.geometry;
  const pos = g.attributes.position;
  const vmap = new Map();
  const newPos = [], newIdx = [];
  let skipped = 0;
  for (const t of tris) {
    const triIdx = [];
    let ok = true;
    for (const vi of t) {
      if (!Number.isInteger(vi) || vi < 0 || vi >= pos.count ||
          !Number.isFinite(pos.getX(vi)) || !Number.isFinite(pos.getY(vi)) || !Number.isFinite(pos.getZ(vi))) { ok = false; break; }
      let ni = vmap.get(vi);
      if (ni === undefined) {
        ni = newPos.length / 3;
        vmap.set(vi, ni);
        newPos.push(pos.getX(vi), pos.getY(vi), pos.getZ(vi));
      }
      triIdx.push(ni);
    }
    if (!ok) { skipped++; continue; }
    newIdx.push(triIdx[0], triIdx[1], triIdx[2]);
  }
  if (newIdx.length === 0) return null;
  const ng = new THREE.BufferGeometry();
  ng.setAttribute('position', new THREE.Float32BufferAttribute(newPos, 3));
  ng.setIndex(newIdx);
  ng.computeVertexNormals();
  ng.computeBoundingBox();
  const m = new THREE.Mesh(ng, mesh.material.clone());
  m.userData.skippedTris = skipped;
  return m;
}

// NaN 诊断
function checkNaN(label, mesh) {
  if (!mesh) { L(`  [nan] ${label}: null`); return; }
  const p = mesh.geometry.attributes.position;
  let n = 0;
  for (let i = 0; i < p.count; i++) {
    if (!Number.isFinite(p.getX(i)) || !Number.isFinite(p.getY(i)) || !Number.isFinite(p.getZ(i))) n++;
  }
  const bb = new THREE.Box3().setFromObject(mesh);
  L(`  [nan] ${label}: verts=${p.count} NaN=${n} h=${(bb.max.y - bb.min.y).toFixed(3)} minY=${bb.min.y.toFixed(3)}`);
}

// 按三角形质心 y 切：上半(y>=cut)=body，下半(y<cut)=legs
function splitByY(mesh, yCut) {
  const g = mesh.geometry;
  const pos = g.attributes.position;
  const idx = g.index;
  if (!idx) return { top: mesh, bottom: null };
  const topTris = [], bottomTris = [];
  for (let i = 0; i < idx.count; i += 3) {
    const a = idx.getX(i), b = idx.getX(i + 1), c = idx.getX(i + 2);
    const yc = (pos.getY(a) + pos.getY(b) + pos.getY(c)) / 3;
    if (yc >= yCut) topTris.push([a, b, c]);
    else bottomTris.push([a, b, c]);
  }
  return { top: rebuildTris(mesh, topTris) || mesh, bottom: rebuildTris(mesh, bottomTris) };
}

// 按三角形质心 x 符号拆左右
function splitByXSign(mesh, side) {
  const g = mesh.geometry;
  const pos = g.attributes.position;
  const idx = g.index;
  if (!idx) return null;
  const tris = [];
  for (let i = 0; i < idx.count; i += 3) {
    const a = idx.getX(i), b = idx.getX(i + 1), c = idx.getX(i + 2);
    const xc = (pos.getX(a) + pos.getX(b) + pos.getX(c)) / 3;
    if (side === -1 && xc < 0) tris.push([a, b, c]);
    else if (side === 1 && xc > 0) tris.push([a, b, c]);
  }
  return rebuildTris(mesh, tris);
}

// 按 z 范围拆头（前端上部）
function splitHeadByZ(mesh, zCut) {
  const g = mesh.geometry;
  const pos = g.attributes.position;
  const idx = g.index;
  if (!idx) return { head: null, body: mesh };
  const headTris = [], bodyTris = [];
  for (let i = 0; i < idx.count; i += 3) {
    const a = idx.getX(i), b = idx.getX(i + 1), c = idx.getX(i + 2);
    const zc = (pos.getZ(a) + pos.getZ(b) + pos.getZ(c)) / 3;
    if (zc > zCut) headTris.push([a, b, c]);
    else bodyTris.push([a, b, c]);
  }
  return { head: rebuildTris(mesh, headTris), body: rebuildTris(mesh, bodyTris) || mesh };
}

function main() {
  loadGLB(SRC).then((gltf) => {
    // ---------- 0. 收集 mesh ----------
    const meshes = [];
    gltf.scene.traverse(o => { if (o.isMesh) meshes.push(o); });
    L(`[0] loaded meshes: ${meshes.length} (${meshes[0].geometry.attributes.position.count} verts, ${(meshes[0].geometry.index ? meshes[0].geometry.index.count / 3 : meshes[0].geometry.attributes.position.count / 3)} tris)`);

    // ---------- 1. 对齐 bake：旋转到 +Z 前向 + 缩放/锚脚 ----------
    // 静态牛头朝哪？bbox z 范围 -0.189..0.27，假定 +Z 前向（头在 +Z）
    const mesh = meshes[0];
    const M = new THREE.Matrix4();
    const box0 = new THREE.Box3().setFromObject(mesh);
    const size0 = box0.getSize(new THREE.Vector3());
    // 若头在 -Z（maxZ 侧是屁股），旋转 180 让头朝 +Z —— 先假定头在 +Z，不转
    L(`[1] src bbox min=(${box0.min.x.toFixed(3)},${box0.min.y.toFixed(3)},${box0.min.z.toFixed(3)}) max=(${box0.max.x.toFixed(3)},${box0.max.y.toFixed(3)},${box0.max.z.toFixed(3)}) h=${size0.y.toFixed(3)}`);
    // 缩放 + 锚脚（几何局部空间）
    const scale = TARGET_H / size0.y;
    const tx = -(box0.min.x + box0.max.x) / 2 * scale;
    const tz = -(box0.min.z + box0.max.z) / 2 * scale;
    const ty = -box0.min.y * scale;
    mesh.geometry.scale(scale, scale, scale);
    mesh.geometry.translate(tx, ty, tz);
    mesh.geometry.computeBoundingBox();
    L(`[1] align: scale=${scale.toFixed(4)} t=(${tx.toFixed(4)},${ty.toFixed(4)},${tz.toFixed(4)})`);

    const box = new THREE.Box3().setFromObject(mesh);
    const size = box.getSize(new THREE.Vector3());
    L(`[1] after align h=${size.y.toFixed(3)} feetY=${box.min.y.toFixed(4)} z-range=(${box.min.z.toFixed(3)}..${box.max.z.toFixed(3)})`);

    // ---------- 2. 拆腿（先按 Y 切腿，再按 X 分左右）+ 拆头（前端上部） ----------
    // 静态牛结构（连通分量分析）：腿 y∈[0,0.075] 身体从 y≈0.08 起；前后腿分居 x 两侧
    checkNaN('src', mesh);
    const yLegCut = box.min.y + 0.077 / 0.257 * size.y; // 原始 0.077/0.257 比例 → 缩放后
    const { top: bodyTmp, bottom: legRegion } = splitByY(mesh, yLegCut);
    checkNaN('bodyTmp', bodyTmp);
    checkNaN('legRegion', legRegion);
    const legL = legRegion ? splitByXSign(legRegion, -1) : null;
    const legR = legRegion ? splitByXSign(legRegion, 1) : null;
    checkNaN('legL', legL);
    checkNaN('legR', legR);
    L(`[2] skipped tris: bodyTmp=${bodyTmp ? (bodyTmp.userData.skippedTris || 0) : '?'} legRegion=${legRegion ? (legRegion.userData.skippedTris || 0) : '?'} legL=${legL ? (legL.userData.skippedTris || 0) : '?'} legR=${legR ? (legR.userData.skippedTris || 0) : '?'}`);
    L(`[2] yLegCut=${yLegCut.toFixed(3)} legs: L=${legL ? legL.geometry.attributes.position.count + 'v' : 'NONE'} R=${legR ? legR.geometry.attributes.position.count + 'v' : 'NONE'}`);

    // 头：身体前上端（z > bodyMinZ + 0.68 * bodyDepth）
    const bodyBoxTmp = new THREE.Box3().setFromObject(bodyTmp);
    const bodyDepth = bodyBoxTmp.max.z - bodyBoxTmp.min.z;
    const zCut = bodyBoxTmp.min.z + 0.68 * bodyDepth;
    const headSplit = splitHeadByZ(bodyTmp, zCut);
    let headMesh = headSplit.head;
    const bodyMesh = headSplit.body;
    checkNaN('headMesh', headMesh);
    checkNaN('bodyMesh', bodyMesh);
    if (headMesh) {
      const hb = new THREE.Box3().setFromObject(headMesh);
      if ((hb.max.z - hb.min.z) < 0.05) headMesh = null; // 头太小视为失败
    }
    L(`[2] head split: ${headMesh ? 'OK ' + headMesh.geometry.attributes.position.count + 'v' : 'SKIPPED (fallback whole-body)'}`);

    // ---------- 3. 重命名 + 重涂 ----------
    function repaint(m, colorHex, matName, rough) {
      m.name = 'mesh_' + matName;
      m.material = makeMat(colorHex, rough, matName);
      m.castShadow = true;
    }
    if (headMesh) repaint(headMesh, PALETTE.head, 'head', 0.85);
    if (bodyMesh) repaint(bodyMesh, PALETTE.body, 'body', 0.85);
    if (legL) repaint(legL, PALETTE.leg, 'leg_L', 0.7);
    if (legR) repaint(legR, PALETTE.leg, 'leg_R', 0.7);
    L('[3] repainted PBR + renamed (brown)');

    // ---------- 4. 骨骼 ----------
    const rig = new THREE.Group();
    rig.name = 'cow_brown_b';
    const rootBone = new THREE.Bone();
    rootBone.name = 'bone_root';
    rig.add(rootBone);
    const bodyBox = new THREE.Box3();
    (headMesh ? [bodyMesh, headMesh] : [bodyMesh]).forEach(m => bodyBox.expandByObject(m));
    const bodyC = bodyBox.getCenter(new THREE.Vector3());
    rootBone.position.copy(bodyC);
    if (bodyMesh) rootBone.attach(bodyMesh);

    // 颈/头 bone
    const neckBone = new THREE.Bone();
    neckBone.name = 'bone_neck';
    rootBone.add(neckBone);
    if (headMesh) {
      const hb = new THREE.Box3().setFromObject(headMesh);
      neckBone.position.set((hb.min.x + hb.max.x) / 2, (hb.min.y + hb.max.y) / 2, hb.min.z);
      neckBone.attach(headMesh);
    } else {
      // 无头拆分：颈 bone 放在身体前上端（空 bone，供后续扩展）
      neckBone.position.set(0, bodyC.y + 0.25, box.max.z - 0.1);
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
    const legLBone = makeLegBone(legL, -1);
    const legRBone = makeLegBone(legR, 1);
    L(`[4] bones: root@(${rootBone.position.x.toFixed(3)},${rootBone.position.y.toFixed(3)},${rootBone.position.z.toFixed(3)}) neck@(${neckBone.position.x.toFixed(3)},${neckBone.position.y.toFixed(3)},${neckBone.position.z.toFixed(3)}) legL@(${legLBone.position.x.toFixed(3)},${legLBone.position.y.toFixed(3)},${legLBone.position.z.toFixed(3)}) legR@(${legRBone.position.x.toFixed(3)},${legRBone.position.y.toFixed(3)},${legRBone.position.z.toFixed(3)})`);

    // ---------- 5. 动画 ----------
    function sampleTimes(T) {
      const n = 24;
      const ts = [];
      for (let i = 0; i <= n; i++) ts.push((i / n) * T);
      return ts;
    }
    // idle：身体轻微起伏 + 头微摆
    const idleTimes = sampleTimes(IDLE_T);
    const idleTracks = [];
    idleTracks.push(vecTrack(rootBone, 'position', idleTimes, t => {
      const y = Math.abs(Math.sin(t * 2 * Math.PI / IDLE_T)) * 0.015;
      return [bodyC.x, bodyC.y + y, bodyC.z];
    }));
    idleTracks.push(quatTrack(neckBone, 'rotation', idleTimes, t => {
      const s = Math.sin(t * 2 * Math.PI / IDLE_T) * 0.04;
      return [0, 0, s];
    }));
    const idleClip = new THREE.AnimationClip('idle', IDLE_T, idleTracks);

    // walk：腿交替 + 身体起伏 + 头轻微点头
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
      const y = Math.abs(Math.sin(t * 2 * Math.PI / WALK_T)) * 0.04;
      return [bodyC.x, bodyC.y + y, bodyC.z];
    }));
    walkTracks.push(quatTrack(neckBone, 'rotation', walkTimes, t => {
      const s = Math.sin(t * 2 * Math.PI / WALK_T + 0.6) * 0.06;
      return [s, 0, 0];
    }));
    const walkClip = new THREE.AnimationClip('walk', WALK_T, walkTracks);

    // eat：头下俯（颈 bone pitch）或整体前倾 + 腿微动
    const eatTimes = sampleTimes(EAT_T);
    const eatTracks = [];
    eatTracks.push(quatTrack(neckBone, 'rotation', eatTimes, t => {
      const env = Math.sin(t * Math.PI / EAT_T) ** 2;
      return [-0.45 * env, 0, 0];
    }));
    if (!headMesh) {
      // 无独立头：整体低头（root 前倾）模拟进食
      eatTracks.push(quatTrack(rootBone, 'rotation', eatTimes, t => {
        const env = Math.sin(t * Math.PI / EAT_T) ** 2;
        return [-0.12 * env, 0, 0];
      }));
    }
    eatTracks.push(vecTrack(rootBone, 'position', eatTimes, t => {
      const env = Math.sin(t * Math.PI / EAT_T) ** 2;
      return [bodyC.x, bodyC.y + 0.01 * env, bodyC.z + 0.02 * env];
    }));
    const eatClip = new THREE.AnimationClip('eat', EAT_T, eatTracks);
    L(`[5] clips: idle(${idleClip.duration}s,${idleTracks.length}t) walk(${walkClip.duration}s,${walkTracks.length}t) eat(${eatClip.duration}s,${eatTracks.length}t)`);

    // ---------- 6. 导出 ----------
    const exporter = new GLTFExporter();
    const options = { binary: true, animations: [idleClip, walkClip, eatClip] };
    exporter.parse(rig, (result) => {
      writeFileSync(OUT, Buffer.from(result));
      L(`[6] wrote ${OUT} (${(Buffer.from(result).length / 1024).toFixed(1)} KB)`);
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
