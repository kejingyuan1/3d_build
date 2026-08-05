#!/usr/bin/env node
// build_skinned_animal.mjs — 程序化顶点蒙皮 v2：静态 GLB → 真 skin（bones + skinIndex/skinWeight + IBM）
// v2 变更：
//  - 按物种配色：单材质带贴图物种(cow/goose/sheep) → 顶点色刷色(身/腿/头)；多材质物种(duck/chicken) → 保留源材质色
//  - 脚底自校正：导出→重解析测渲染级 feetY，若≠0 平移几何+骨骼并重算 IBM 再导出（动画只驱动旋转，不受平移影响）
// 用法: node tools/build_skinned_animal.mjs <in.glb> <out.glb> <head_h_m> <species>
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

const [inFile, outFile, headHStr, species] = process.argv.slice(2);
if (!inFile || !outFile || !headHStr || !species) {
  console.error('usage: node tools/build_skinned_animal.mjs <in.glb> <out.glb> <head_h_m> <species>');
  process.exit(1);
}
const HEAD_H = parseFloat(headHStr);
const IDLE_T = 4.0, WALK_T = 1.6, EAT_T = 1.6;

// 物种配色（hex）· useVC=true → 顶点色刷色；false → 保留源材质色
// splitMatName：源材质中「一个材质覆盖多区域」时按 y 拆分（如鸭：lambert5SG 覆盖喙+脚 → 腿黄/其余橙）
const SPECIES = {
  cow:     { useVC: true,  body: 0x8C5A2E, leg: 0x261A14, head: 0x7A4E32 },
  goose:   { useVC: true,  body: 0xF2F0E8, leg: 0xD98A3A, head: 0xF2F0E8 },
  sheep:   { useVC: true,  body: 0xEDE8DC, leg: 0x6E4A32, head: 0x6E4A32 },
  duck:    { useVC: true,  body: 0xF5F5F0, leg: 0xD9A83E, head: 0xF5F5F0, beak: 0xE8A33C, splitMatName: 'lambert5SG', tuft: true },
  chicken: { useVC: false },
  pig:     { useVC: false },
};
const cfg = SPECIES[species] || SPECIES.cow;

const log = [];
const L = (m) => { log.push(String(m)); };

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
function sampleTimes(T) {
  const n = 24;
  const ts = [];
  for (let i = 0; i <= n; i++) ts.push((i / n) * T);
  return ts;
}

function renderBBox(sm) {
  sm.updateMatrixWorld(true);
  sm.skeleton.update();
  const pos = sm.geometry.attributes.position;
  const min = new THREE.Vector3(Infinity, Infinity, Infinity);
  const max = new THREE.Vector3(-Infinity, -Infinity, -Infinity);
  const v = new THREE.Vector3();
  let nan = 0, extreme = 0;
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    sm.applyBoneTransform(i, v);
    v.applyMatrix4(sm.matrixWorld);
    if (!Number.isFinite(v.x) || !Number.isFinite(v.y) || !Number.isFinite(v.z)) { nan++; continue; }
    if (Math.abs(v.x) > 100 || Math.abs(v.y) > 100 || Math.abs(v.z) > 100) { extreme++; continue; }
    min.min(v); max.max(v);
  }
  return { min, max, nan, extreme };
}

function main() {
  loadGLB(inFile).then(async (gltf) => {
    // ---- 1. 收集子网格 ----
    const meshes = [];
    gltf.scene.traverse(o => { if (o.isMesh) meshes.push(o); });
    L(`[0] sub-meshes=${meshes.length}`);
    const mats = [];
    const matKey = (mm) => mm.uuid || (mm.name || '?');
    const meshMatIdx = [];
    const srcMatNameOfMesh = []; // 每个子网格的源材质名（useVC 替换前）
    meshes.forEach(m => {
      const list = Array.isArray(m.material) ? m.material : [m.material];
      list.forEach(mm => {
        srcMatNameOfMesh.push(mm.name || '');
        let target = mm;
        if (cfg.useVC) {
          target = new THREE.MeshStandardMaterial({ color: 0xffffff, vertexColors: true, roughness: 0.9, metalness: 0, name: (species || 'animal') + '_vc' });
        } else if (mm.map) {
          const color = mm.color ? mm.color.clone() : new THREE.Color(0xcccccc);
          target = new THREE.MeshStandardMaterial({ color, roughness: 0.9, metalness: 0, name: (mm.name || 'mat') + '_flat' });
        }
        let idx = mats.findIndex(x => matKey(x) === matKey(target));
        if (idx < 0) { mats.push(target); idx = mats.length - 1; }
        meshMatIdx.push(idx);
      });
    });
    L(`[0] materials=${mats.length} (${mats.map(m => (m.name || '?') + (m.vertexColors ? '[VC]' : '')).join(', ')})`);

    // ---- 2. 合并几何 ----
    const positions = [];
    const indices = [];
    const groupList = [];
    let vertOffset = 0, groupStart = 0;
    let mi = 0;
    for (const m of meshes) {
      const g = m.geometry;
      const p = g.attributes.position;
      for (let i = 0; i < p.count; i++) positions.push(p.getX(i), p.getY(i), p.getZ(i));
      const idxCount = g.index ? g.index.count : p.count * 3;
      if (g.index) { for (let i = 0; i < g.index.count; i++) indices.push(g.index.getX(i) + vertOffset); }
      else { for (let i = 0; i < p.count; i++) indices.push(i + vertOffset); }
      const nPrims = Array.isArray(m.material) ? m.material.length : 1;
      for (let k = 0; k < nPrims; k++) {
        groupList.push({ start: (groupStart + idxCount * k / nPrims), count: idxCount / nPrims, materialIndex: meshMatIdx[mi] });
      }
      groupStart += idxCount;
      vertOffset += p.count;
      mi++;
    }
    const merged = new THREE.BufferGeometry();
    merged.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    merged.setIndex(indices);
    merged.clearGroups();
    groupList.forEach(gg => merged.addGroup(Math.round(gg.start), Math.round(gg.count), gg.materialIndex));
    // 记录每个顶点的源材质名 id（供 splitMat 物种按材质区域刷色）
    const srcIdMap = {};
    const srcIdsOfMesh = [];
    srcMatNameOfMesh.forEach(nm => { if (!(nm in srcIdMap)) srcIdMap[nm] = Object.keys(srcIdMap).length; });
    meshes.forEach((m, mi) => {
      const nPrims = Array.isArray(m.material) ? m.material.length : 1;
      for (let k = 0; k < nPrims; k++) srcIdsOfMesh.push(srcIdMap[srcMatNameOfMesh[mi]]);
    });
    const vertexMat = new Uint8Array(positions.length / 3);
    let vCursor = 0;
    for (let mi = 0; mi < meshes.length; mi++) {
      const pcnt = meshes[mi].geometry.attributes.position.count;
      for (let i = 0; i < pcnt; i++) vertexMat[vCursor++] = srcIdsOfMesh[mi];
    }
    L(`[0] merged verts=${merged.attributes.position.count} tris=${indices.length / 3} groups=${groupList.length}`);

    // ---- 3. 前向判定 + 对齐 ----
    merged.computeBoundingBox();
    let bb = merged.boundingBox;
    const height0 = bb.max.y - bb.min.y;
    const midZ0 = (bb.max.z + bb.min.z) / 2;
    const pos = merged.attributes.position;
    let nTopP = 0, nTopN = 0;
    for (let i = 0; i < pos.count; i++) {
      if (pos.getY(i) > bb.min.y + 0.8 * height0) {
        if (pos.getZ(i) > midZ0) nTopP++; else nTopN++;
      }
    }
    const front = nTopP >= nTopN ? 1 : -1;
    L(`[1] top-band verts: +Z=${nTopP} -Z=${nTopN} → front=${front > 0 ? '+Z' : '-Z'}`);
    if (front < 0) {
      merged.applyMatrix4(new THREE.Matrix4().makeRotationY(Math.PI));
      merged.computeBoundingBox();
      bb = merged.boundingBox;
    }
    const h0 = bb.max.y - bb.min.y;
    const k = HEAD_H / h0;
    const tx = -(bb.min.x + bb.max.x) / 2 * k;
    const tz = -(bb.min.z + bb.max.z) / 2 * k;
    const ty = -bb.min.y * k;
    merged.scale(k, k, k);
    merged.translate(tx, ty, tz);
    merged.computeBoundingBox();
    bb = merged.boundingBox;
    const height = bb.max.y - bb.min.y;
    const depth = bb.max.z - bb.min.z;
    L(`[1] scale=${k.toFixed(5)} h=${height.toFixed(3)} feetY=${bb.min.y.toFixed(4)} z=${bb.min.z.toFixed(2)}..${bb.max.z.toFixed(2)}`);

    // ---- 4. 骨骼定位 ----
    const yLegCut = bb.min.y + 0.28 * height;
    const zHeadCut = bb.min.z + 0.72 * depth;
    const clusters = { FL: [], FR: [], RL: [], RR: [], body: [], head: [] };
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
      if (y < yLegCut) {
        const key = (z > bb.min.z + depth / 2 ? 'F' : 'R') + (x < 0 ? 'L' : 'R');
        clusters[key].push([x, y, z]);
      } else {
        clusters.body.push([x, y, z]);
        if (z > zHeadCut) clusters.head.push([x, y, z]);
      }
    }
    function centroid(pts, fallback) {
      if (!pts.length) return fallback.clone();
      const c = new THREE.Vector3();
      for (const p of pts) c.add(new THREE.Vector3(p[0], p[1], p[2]));
      c.divideScalar(pts.length);
      return c;
    }
    const bodyC = centroid(clusters.body, new THREE.Vector3(0, 0.5 * height, 0));
    const headC = centroid(clusters.head, new THREE.Vector3(0, 0.85 * height, bb.min.z + 0.85 * depth));
    const hipFL = centroid(clusters.FL, new THREE.Vector3(-0.15, yLegCut, bb.min.z + 0.75 * depth));
    const hipFR = centroid(clusters.FR, new THREE.Vector3(0.15, yLegCut, bb.min.z + 0.75 * depth));
    const hipRL = centroid(clusters.RL, new THREE.Vector3(-0.15, yLegCut, bb.min.z + 0.25 * depth));
    const hipRR = centroid(clusters.RR, new THREE.Vector3(0.15, yLegCut, bb.min.z + 0.25 * depth));
    [hipFL, hipFR, hipRL, hipRR].forEach(h => { h.y = yLegCut + 0.02; });
    const neckC = new THREE.Vector3(0, bodyC.y + 0.25 * height, bb.min.z + 0.55 * depth);
    L(`[2] bodyC=(${bodyC.x.toFixed(2)},${bodyC.y.toFixed(2)},${bodyC.z.toFixed(2)}) headC=(${headC.x.toFixed(2)},${headC.y.toFixed(2)},${headC.z.toFixed(2)})`);
    L(`[2] hips FL=(${hipFL.x.toFixed(2)},${hipFL.y.toFixed(2)},${hipFL.z.toFixed(2)}) RL=(${hipRL.x.toFixed(2)},${hipRL.y.toFixed(2)},${hipRL.z.toFixed(2)}) clusters head=${clusters.head.length}`);

    // ---- 5. 顶点色刷色（useVC 物种） ----
    if (cfg.useVC) {
      const colors = new Float32Array(pos.count * 3);
      const colBody = new THREE.Color(cfg.body);
      const colLeg = new THREE.Color(cfg.leg);
      const colHead = new THREE.Color(cfg.head);
      const colBeak = cfg.beak ? new THREE.Color(cfg.beak) : null;
      // splitMat：源材质中一个材质覆盖多区域（鸭 lambert5SG = 喙+脚）→ 腿区黄、其余橙
      let splitIdx = -1;
      if (cfg.splitMatName) {
        splitIdx = (cfg.splitMatName in srcIdMap) ? srcIdMap[cfg.splitMatName] : -1;
        L(`[2] splitMat '${cfg.splitMatName}' srcId=${splitIdx}`);
      }
      for (let i = 0; i < pos.count; i++) {
        const y = pos.getY(i), z = pos.getZ(i);
        let c = colBody;
        if (splitIdx >= 0 && vertexMat[i] === splitIdx) {
          c = y < yLegCut ? colLeg : (colBeak || colBody);
        } else if (y < yLegCut) {
          c = colLeg;
        } else if (z > zHeadCut) {
          c = colHead;
        }
        colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
      }
      merged.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
      L(`[2] vertex colors painted: body=#${cfg.body.toString(16)} leg=#${cfg.leg.toString(16)} head=#${cfg.head.toString(16)}${cfg.beak ? ' beak=#' + cfg.beak.toString(16) : ''}`);
    }

    // ---- 6. 程序化 skin weights ----
    const bonePositions = [bodyC, hipFL, hipFR, hipRL, hipRR, neckC, headC];
    const eps = 0.06 * height;
    const eps2 = eps * eps;
    const skinIndex = new Uint16Array(pos.count * 4);
    const skinWeight = new Float32Array(pos.count * 4);
    const tmpV = new THREE.Vector3();
    for (let i = 0; i < pos.count; i++) {
      tmpV.set(pos.getX(i), pos.getY(i), pos.getZ(i));
      const ws = [];
      for (let b = 0; b < bonePositions.length; b++) {
        const d = tmpV.distanceTo(bonePositions[b]);
        ws.push([b, 1 / (d * d + eps2)]);
      }
      ws.sort((a, b) => b[1] - a[1]);
      const top = ws.slice(0, 4);
      let sum = 0;
      for (const [, w] of top) sum += w;
      if (sum < 1e-9) { top.length = 1; top[0] = [0, 1]; sum = 1; }
      for (let j = 0; j < 4; j++) {
        const [bi, w] = top[j] || [0, 0];
        skinIndex[i * 4 + j] = bi;
        skinWeight[i * 4 + j] = sum > 0 ? w / sum : 0;
      }
    }
    merged.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(skinIndex, 4));
    merged.setAttribute('skinWeight', new THREE.Float32BufferAttribute(skinWeight, 4));
    L(`[3] generated skin weights (top-4, inv-d² eps=${eps.toFixed(3)})`);

    // ---- 7. SkinnedMesh + Skeleton ----
    const root = new THREE.Group();
    root.name = 'skinned_' + species;
    const rootBone = new THREE.Bone(); rootBone.name = 'bone_root';
    root.add(rootBone); rootBone.position.copy(bodyC);
    const legBones = {};
    const mkLeg = (name, hip) => {
      const b = new THREE.Bone(); b.name = name;
      rootBone.add(b); b.position.copy(hip.clone().sub(bodyC));
      return b;
    };
    legBones.FL = mkLeg('bone_leg_FL', hipFL);
    legBones.FR = mkLeg('bone_leg_FR', hipFR);
    legBones.RL = mkLeg('bone_leg_RL', hipRL);
    legBones.RR = mkLeg('bone_leg_RR', hipRR);
    const neckBone = new THREE.Bone(); neckBone.name = 'bone_neck';
    rootBone.add(neckBone); neckBone.position.copy(neckC.clone().sub(bodyC));
    const headBone = new THREE.Bone(); headBone.name = 'bone_head';
    neckBone.add(headBone); headBone.position.copy(headC.clone().sub(neckC));
    root.updateMatrixWorld(true);
    const bones = [rootBone, legBones.FL, legBones.FR, legBones.RL, legBones.RR, neckBone, headBone];

    const matArray = mats.length === 1 ? mats[0] : mats;
    const sm = new THREE.SkinnedMesh(merged, matArray);
    sm.name = 'mesh_skinned';
    sm.castShadow = true;
    root.add(sm);
    const skeleton = new THREE.Skeleton(bones);
    sm.bind(skeleton);

    // ---- 7.5 卡通风眼睛（黑圆 + 白高光，挂 head bone） ----
    const matEye = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: 0.3, metalness: 0, name: 'mat_eye' });
    const matHL = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.15, metalness: 0, name: 'mat_eye_highlight' });
    // 头区 = 前 12% 深 + 上 38% 高（z > minZ+0.88*depth && y > minY+0.62*height）→ 真正的头部
    const facePts = [];
    for (let i = 0; i < pos.count; i++) {
      if (pos.getZ(i) > bb.min.z + 0.88 * depth && pos.getY(i) > bb.min.y + 0.62 * height) facePts.push([pos.getX(i), pos.getY(i), pos.getZ(i)]);
    }
    // 尺寸按模型高度比例（自适应物种）：eyeR ≈ height*0.022（牛≈3.3cm 半径/6.6cm 直径，鸡≈1.1cm/2.2cm）
    const eyeR = Math.max(0.008, height * 0.022);
    // 头区退化检测（薄片/单侧/太小 → 兜底围绕 head bone 放置）
    const headDegenerate = (() => {
      if (facePts.length < 8) return true;
      let minY = Infinity, maxY = -Infinity, minX = Infinity, maxX = -Infinity;
      for (const p of facePts) { minY = Math.min(minY, p[1]); maxY = Math.max(maxY, p[1]); minX = Math.min(minX, p[0]); maxX = Math.max(maxX, p[0]); }
      if (maxY - minY < 0.03 * height) return true;
      if (maxX - minX < 0.03 * height) return true;
      return false;
    })();
    if (!headDegenerate) {
      const fmin = new THREE.Vector3(Infinity, Infinity, Infinity);
      const fmax = new THREE.Vector3(-Infinity, -Infinity, -Infinity);
      for (const p of facePts) { fmin.min(new THREE.Vector3(p[0], p[1], p[2])); fmax.max(new THREE.Vector3(p[0], p[1], p[2])); }
      // 眼睛放在头区【中心深度】两侧（不是最前端！否则飘在口鼻/喙前方）
      const headCz = (fmin.z + fmax.z) / 2;
      const eyeZ = headCz;
      const eyeY = fmin.y + (fmax.y - fmin.y) * 0.55; // 头区上部
      const hw = (fmax.x - fmin.x) / 2;
      const ex = Math.max(eyeR * 1.3, hw * 0.85 + eyeR * 0.2); // 头侧表面略凸
      root.updateMatrixWorld(true);
      for (const side of [-1, 1]) {
        const eye = new THREE.Mesh(new THREE.SphereGeometry(eyeR, 12, 8), matEye);
        eye.name = side < 0 ? 'mesh_eye_L' : 'mesh_eye_R';
        eye.position.set(side * ex, eyeY, eyeZ);
        eye.castShadow = true;
        headBone.attach(eye);
        const hl = new THREE.Mesh(new THREE.SphereGeometry(eyeR * 0.32, 8, 6), matHL);
        hl.name = side < 0 ? 'mesh_eye_hl_L' : 'mesh_eye_hl_R';
        hl.position.set(side * eyeR * 0.35, eyeR * 0.4, eyeR * 0.55);
        eye.add(hl);
      }
      L(`[2] eyes: facePts=${facePts.length} eyeR=${eyeR.toFixed(4)}m(d=${(eyeR * 2 * 100).toFixed(1)}cm) at x=±${ex.toFixed(3)} y=${eyeY.toFixed(3)} z=${eyeZ.toFixed(3)} (headCz=${headCz.toFixed(3)})`);
    } else {
      // 兜底：头区退化（薄片/单侧/太小，如鸡）→ 用模型高度比例放在前上端
      const eyeZ = bb.min.z + 0.86 * depth;
      const eyeY = bb.min.y + 0.80 * height;
      const ex = Math.max(eyeR * 1.8, 0.05 * height);
      root.updateMatrixWorld(true);
      for (const side of [-1, 1]) {
        const eye = new THREE.Mesh(new THREE.SphereGeometry(eyeR, 12, 8), matEye);
        eye.name = side < 0 ? 'mesh_eye_L' : 'mesh_eye_R';
        eye.position.set(side * ex, eyeY, eyeZ);
        eye.castShadow = true;
        headBone.attach(eye);
        const hl = new THREE.Mesh(new THREE.SphereGeometry(eyeR * 0.32, 8, 6), matHL);
        hl.name = side < 0 ? 'mesh_eye_hl_L' : 'mesh_eye_hl_R';
        hl.position.set(side * eyeR * 0.35, eyeR * 0.4, eyeR * 0.55);
        eye.add(hl);
      }
      L(`[2] eyes: FALLBACK(headDegenerate) eyeR=${eyeR.toFixed(4)}m at y=${eyeY.toFixed(3)} z=${eyeZ.toFixed(3)} x=±${ex.toFixed(3)}`);
    }

    // ---- 7.6 头顶黑毛簇（cfg.tuft 物种，如鸭：黑顶一撮毛，挂 head bone） ----
    if (cfg.tuft && facePts.length >= 8) {
      const matTuft = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, roughness: 0.8, metalness: 0, name: 'mat_tuft' });
      const tmin = new THREE.Vector3(Infinity, Infinity, Infinity);
      const tmax = new THREE.Vector3(-Infinity, -Infinity, -Infinity);
      for (const p of facePts) { tmin.min(new THREE.Vector3(p[0], p[1], p[2])); tmax.max(new THREE.Vector3(p[0], p[1], p[2])); }
      const headD = Math.max(tmax.x - tmin.x, tmax.z - tmin.z, tmax.y - tmin.y);
      const tuftH = headD * 0.28;       // 毛簇高 ≈ 头径 28%
      const tuftR = headD * 0.10;       // 毛簇底半径
      const tBase = new THREE.Vector3(0, tmax.y, (tmin.z + tmax.z) / 2);
      const coneGeo = new THREE.CylinderGeometry(tuftR * 0.25, tuftR, tuftH, 7, 1, false);
      coneGeo.translate(0, tuftH / 2, 0);
      coneGeo.computeVertexNormals();
      root.updateMatrixWorld(true);
      const fan = [[0, 0, 0], [-0.18, 0.10, 0.05], [0.18, 0.10, 0.05]];
      fan.forEach(([tx, ty, tz], i) => {
        const c = new THREE.Mesh(coneGeo, matTuft);
        c.name = 'mesh_tuft_' + i;
        c.position.set(tBase.x + tx * tuftH, tBase.y + ty * tuftH, tBase.z + tz * tuftH);
        c.rotation.x = ty !== 0 ? ty * 2 : 0;
        c.rotation.z = tx !== 0 ? tx * 2 : 0;
        headBone.attach(c);
      });
      L(`[2] hair tuft: 3 cones tuftH=${(tuftH * 100).toFixed(1)}cm at top y=${tBase.y.toFixed(3)} z=${tBase.z.toFixed(3)}`);
    }

    // ---- 8. 动画（只驱动旋转，避免位置 track 与脚底校正冲突） ----
    const idleTimes = sampleTimes(IDLE_T);
    const idleTracks = [];
    idleTracks.push(quatTrack(neckBone, 'rotation', idleTimes, t => {
      const s = Math.sin(t * 2 * Math.PI / IDLE_T) * 0.05;
      return [0, 0, s];
    }));
    const idleClip = new THREE.AnimationClip('idle', IDLE_T, idleTracks);
    const walkTimes = sampleTimes(WALK_T);
    const walkTracks = [];
    const pairA = [legBones.FL, legBones.RR];
    const pairB = [legBones.FR, legBones.RL];
    pairA.forEach(b => walkTracks.push(quatTrack(b, 'rotation', walkTimes, t => {
      const s = Math.sin(t * 2 * Math.PI / WALK_T) * 0.3;
      return [s, 0, 0];
    })));
    pairB.forEach(b => walkTracks.push(quatTrack(b, 'rotation', walkTimes, t => {
      const s = -Math.sin(t * 2 * Math.PI / WALK_T) * 0.3;
      return [s, 0, 0];
    })));
    walkTracks.push(quatTrack(neckBone, 'rotation', walkTimes, t => {
      const s = Math.sin(t * 2 * Math.PI / WALK_T + 0.6) * 0.06;
      return [s, 0, 0];
    }));
    const walkClip = new THREE.AnimationClip('walk', WALK_T, walkTracks);
    const eatTimes = sampleTimes(EAT_T);
    const eatTracks = [];
    eatTracks.push(quatTrack(neckBone, 'rotation', eatTimes, t => {
      const env = Math.sin(t * Math.PI / EAT_T) ** 2;
      return [-0.5 * env, 0, 0];
    }));
    const eatClip = new THREE.AnimationClip('eat', EAT_T, eatTracks);
    L(`[4] clips: idle(${idleClip.duration}s,${idleTracks.length}t) walk(${walkClip.duration}s,${walkTracks.length}t) eat(${eatClip.duration}s,${eatTracks.length}t)`);

    // ---- 9. 导出 + 脚底自校正 ----
    const exporter = new GLTFExporter();
    const options = { binary: true, animations: [idleClip, walkClip, eatClip] };
    const exportOnce = () => new Promise((res, rej) => {
      exporter.parse(root, (result) => { res(Buffer.from(result)); }, (err) => rej(err), options);
    });
    const parseFile = (buf) => new Promise((res, rej) => {
      const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
      new GLTFLoader().parse(ab, '', (g) => {
        let sm2 = null; g.scene.traverse(o => { if (o.isSkinnedMesh && !sm2) sm2 = o; });
        res(sm2);
      }, rej);
    });
    const measureFeet = (sm2) => {
      sm2.updateMatrixWorld(true); sm2.skeleton.update();
      const p = sm2.geometry.attributes.position;
      const v = new THREE.Vector3();
      let minY = Infinity;
      for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i); sm2.applyBoneTransform(i, v); minY = Math.min(minY, v.y); }
      return minY;
    };

    let buf = await exportOnce();
    let feet = await parseFile(buf).then(measureFeet);
    L(`[5] first export feetY=${feet.toFixed(4)}`);
    if (Math.abs(feet) > 0.005) {
      // 平移几何 + 所有节点 y（含骨骼/网格），重算 IBM，再导出
      for (let i = 0; i < pos.count; i++) pos.setY(i, pos.getY(i) - feet);
      pos.needsUpdate = true;
      root.traverse(o => { if (o.position) o.position.y -= feet; });
      root.updateMatrixWorld(true);
      sm.skeleton.calculateInverses();
      buf = await exportOnce();
      feet = await parseFile(buf).then(measureFeet);
      L(`[5] corrected feetY=${feet.toFixed(4)} (translated by ${(-feet).toFixed(4)})`);
    }
    writeFileSync(outFile, buf);
    L(`[5] wrote ${outFile} (${(buf.length / 1024).toFixed(1)} KB)`);
    let tris = 0, vcount = 0, meshCount = 0, boneCount = 0;
    root.traverse(o => {
      if (o.isMesh) { meshCount++; const gg = o.geometry; tris += gg.index ? gg.index.count / 3 : gg.attributes.position.count / 3; vcount += gg.attributes.position.count; }
      if (o.isBone) boneCount++;
    });
    L(`[5] meshes=${meshCount} bones=${boneCount} tris=${Math.round(tris)} verts=${vcount}`);

    // ---- 10. 最终 verify ----
    const sm2 = await parseFile(buf);
    const bb2 = renderBBox(sm2);
    const sw = sm2.geometry.attributes.skinWeight;
    let bad = 0, nanW = 0;
    for (let i = 0; i < sw.count; i++) {
      let s = 0;
      for (let b = 0; b < 4; b++) { const w = sw.getComponent(i, b); if (!Number.isFinite(w)) nanW++; else s += w; }
      if (Math.abs(s - 1) > 0.01) bad++;
    }
    L('[verify] re-parsed:');
    L(`  skinnedMesh found: true bones=${sm2.skeleton.bones.length}`);
    L(`  render bbox h=${(bb2.max.y - bb2.min.y).toFixed(3)}m feetY=${bb2.min.y.toFixed(4)} nan=${bb2.nan} extreme=${bb2.extreme}`);
    L(`  weight NaN=${nanW} sum!=1=${bad} / ${sw.count}`);
    L('=====');
    L(log.join('\n'));
    console.log(log.join('\n'));
  }).catch((e) => {
    L('ERR: ' + (e && e.message ? e.message : String(e)));
    console.log(log.join('\n'));
    process.exit(1);
  });
}
main();
