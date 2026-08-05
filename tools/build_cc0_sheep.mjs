#!/usr/bin/env node
// build_cc0_sheep.mjs — 羊两态样本：静态 quaternius_Sheep（干净）→ 程序化骨骼 + idle/walk/eat
// MODE=fluffy → animal_sheep_b.glb（剪毛前：蓬松白毛 + 羊毛簇 + 棕脸/腿，目标高 0.78m）
// MODE=shorn  → animal_sheep_shorn_b.glb（剪毛后：贴身短毛无毛簇 + 米褐短毛色，目标高 0.65m）
// 用法: node tools/build_cc0_sheep.mjs [fluffy|shorn]
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

const MODE = (process.argv[2] || 'fluffy');
const SRC = 'assets/quaternius_farm_animals_glb/quaternius_Sheep.glb';
const OUT = MODE === 'shorn'
  ? 'assets/animals/staging/animal_sheep_shorn_b.glb'
  : 'assets/animals/staging/animal_sheep_b.glb';
const TARGET_H = MODE === 'shorn' ? 0.65 : 0.78; // 剪毛后更小
const IDLE_T = 4.0, WALK_T = 1.6, EAT_T = 1.6;

// spec §2.6 羊色板
const C = {
  wool:   0xEDE8DC, // 羊毛暖白
  fleece: 0xD8C9B0, // 剪毛后短毛米褐
  face:   0x6E4A32, // 脸/耳/腿棕褐
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

// 羊毛簇（fluffy 用）：小白色球体散布在身体背/顶
function makeWoolPuffs(matWool, scaleRef) {
  const puffs = [];
  const seed = [
    [-0.10, 0.62, -0.16, 0.055], [0.10, 0.62, -0.16, 0.055],
    [-0.12, 0.66, -0.06, 0.06], [0.12, 0.66, -0.06, 0.06],
    [-0.10, 0.68, 0.04, 0.06], [0.10, 0.68, 0.04, 0.06],
    [-0.07, 0.70, 0.12, 0.055], [0.07, 0.70, 0.12, 0.055],
    [0.00, 0.72, 0.00, 0.06], [0.00, 0.64, -0.20, 0.05],
    [-0.05, 0.66, -0.12, 0.05], [0.05, 0.66, -0.12, 0.05],
    [-0.08, 0.60, -0.05, 0.045], [0.08, 0.60, -0.05, 0.045],
    [0.00, 0.58, 0.10, 0.045], [0.00, 0.60, 0.14, 0.04],
  ];
  for (const [px, py, pz, pr] of seed) {
    const g = new THREE.SphereGeometry(1, 10, 8);
    g.scale(pr * scaleRef, pr * scaleRef, pr * scaleRef);
    g.computeVertexNormals();
    const m = new THREE.Mesh(g, matWool);
    m.name = 'mesh_wool_' + puffs.length;
    m.position.set(px, py, pz);
    m.castShadow = true;
    puffs.push(m);
  }
  return puffs;
}

function main() {
  loadGLB(SRC).then((gltf) => {
    let src = null;
    gltf.scene.traverse(o => { if (o.isMesh && !src) src = o; });
    L(`[0] MODE=${MODE} src verts=${src.geometry.attributes.position.count} tris=${src.geometry.index ? src.geometry.index.count / 3 : src.geometry.attributes.position.count / 3}`);

    // ---- 1. 对齐 ----
    const box0 = new THREE.Box3().setFromObject(src);
    const size0 = box0.getSize(new THREE.Vector3());
    const scale = TARGET_H / size0.y;
    const tx = -(box0.min.x + box0.max.x) / 2 * scale;
    const tz = -(box0.min.z + box0.max.z) / 2 * scale;
    const ty = -box0.min.y * scale;
    src.geometry.scale(scale, scale, scale);
    src.geometry.translate(tx, ty, tz);
    src.geometry.computeBoundingBox();
    const box = new THREE.Box3().setFromObject(src);
    L(`[1] scale=${scale.toFixed(4)} t=(${tx.toFixed(4)},${ty.toFixed(4)},${tz.toFixed(4)}) h=${(box.max.y - box.min.y).toFixed(3)} feetY=${box.min.y.toFixed(4)}`);

    // ---- 2. 拆腿（Y）+ 拆头（Z） ----
    const yLegCut = box.min.y + (0.051 / 0.218) * (box.max.y - box.min.y);
    const { top: bodyTmp, bottom: legRegion } = splitByY(src, yLegCut);
    const legL = legRegion ? splitByXSign(legRegion, -1) : null;
    const legR = legRegion ? splitByXSign(legRegion, 1) : null;
    const bodyBoxTmp = new THREE.Box3().setFromObject(bodyTmp);
    const zCut = bodyBoxTmp.min.z + 0.72 * (bodyBoxTmp.max.z - bodyBoxTmp.min.z);
    const headSplit = splitHeadByZ(bodyTmp, zCut);
    const headMesh = headSplit.head;
    const bodyMesh = headSplit.body;
    L(`[2] yLegCut=${yLegCut.toFixed(3)} legs L=${legL ? legL.geometry.attributes.position.count + 'v' : 'NONE'} R=${legR ? legR.geometry.attributes.position.count + 'v' : 'NONE'} head=${headMesh ? headMesh.geometry.attributes.position.count + 'v' : 'NONE'} body=${bodyMesh.geometry.attributes.position.count + 'v'}`);

    // ---- 3. 重涂 ----
    const bodyColor = MODE === 'shorn' ? C.fleece : C.wool;
    const matBody = makeMat(bodyColor, 0.9, 'fleece');
    const matFace = makeMat(C.face, 0.8, 'face');
    function repaint(m, mat, name) {
      if (!m) return;
      m.name = 'mesh_' + name;
      m.material = mat;
      m.castShadow = true;
    }
    repaint(bodyMesh, matBody, 'body');
    repaint(headMesh, matFace, 'head');
    repaint(legL, matFace, 'leg_L');
    repaint(legR, matFace, 'leg_R');
    L(`[3] repainted (${MODE === 'shorn' ? 'short fleece' : 'fluffy wool'})`);

    // ---- 4. 骨骼 ----
    const rig = new THREE.Group();
    rig.name = MODE === 'shorn' ? 'sheep_shorn_b' : 'sheep_b';
    const rootBone = new THREE.Bone();
    rootBone.name = 'bone_root';
    rig.add(rootBone);
    const bodyBox = new THREE.Box3();
    (headMesh ? [bodyMesh, headMesh] : [bodyMesh]).forEach(m => bodyBox.expandByObject(m));
    const bodyC = bodyBox.getCenter(new THREE.Vector3());
    rootBone.position.copy(bodyC);
    if (bodyMesh) rootBone.attach(bodyMesh);
    // 羊毛簇（fluffy 挂 root，shorn 不挂）
    if (MODE !== 'shorn') {
      const matWool = makeMat(C.wool, 0.9, 'wool_cluster');
      const puffs = makeWoolPuffs(matWool, 1.0);
      puffs.forEach(p => rootBone.attach(p));
      L(`[4] wool puffs: ${puffs.length}`);
    }
    const neckBone = new THREE.Bone();
    neckBone.name = 'bone_neck';
    rootBone.add(neckBone);
    if (headMesh) {
      const hb = new THREE.Box3().setFromObject(headMesh);
      neckBone.position.set((hb.min.x + hb.max.x) / 2, (hb.min.y + hb.max.y) / 2, hb.min.z);
      neckBone.attach(headMesh);
    } else {
      neckBone.position.set(0, bodyC.y + 0.2, box.max.z - 0.05);
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
    L(`[4] bones: root@(${rootBone.position.x.toFixed(2)},${rootBone.position.y.toFixed(2)},${rootBone.position.z.toFixed(2)}) neck@(${neckBone.position.x.toFixed(2)},${neckBone.position.y.toFixed(2)},${neckBone.position.z.toFixed(2)}) legL@(${legLBone.position.x.toFixed(2)},${legLBone.position.y.toFixed(2)},${legLBone.position.z.toFixed(2)}) legR@(${legRBone.position.x.toFixed(2)},${legRBone.position.y.toFixed(2)},${legRBone.position.z.toFixed(2)})`);

    // ---- 5. 动画 ----
    const idleTimes = sampleTimes(IDLE_T);
    const idleTracks = [];
    idleTracks.push(vecTrack(rootBone, 'position', idleTimes, t => {
      const y = Math.abs(Math.sin(t * 2 * Math.PI / IDLE_T)) * 0.012;
      return [bodyC.x, bodyC.y + y, bodyC.z];
    }));
    idleTracks.push(quatTrack(neckBone, 'rotation', idleTimes, t => {
      const s = Math.sin(t * 2 * Math.PI / IDLE_T) * 0.04;
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
      const s = Math.sin(t * 2 * Math.PI / WALK_T + 0.6) * 0.05;
      return [s, 0, 0];
    }));
    const walkClip = new THREE.AnimationClip('walk', WALK_T, walkTracks);
    const eatTimes = sampleTimes(EAT_T);
    const eatTracks = [];
    eatTracks.push(quatTrack(neckBone, 'rotation', eatTimes, t => {
      const env = Math.sin(t * Math.PI / EAT_T) ** 2;
      return [-0.5 * env, 0, 0];
    }));
    eatTracks.push(vecTrack(rootBone, 'position', eatTimes, t => {
      const env = Math.sin(t * Math.PI / EAT_T) ** 2;
      return [bodyC.x, bodyC.y + 0.01 * env, bodyC.z + 0.02 * env];
    }));
    const eatClip = new THREE.AnimationClip('eat', EAT_T, eatTracks);
    L(`[5] clips: idle(${idleClip.duration}s,${idleTracks.length}t) walk(${walkClip.duration}s,${walkTracks.length}t) eat(${eatClip.duration}s,${eatTracks.length}t)`);

    // ---- 6. 导出 ----
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
