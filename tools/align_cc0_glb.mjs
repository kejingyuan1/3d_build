#!/usr/bin/env node
// align_cc0_glb.mjs — 导入对齐 CC0 带骨骼 GLB（B 方案 A 候选：MAXDESIGN Chicken）
// 流程：加载 GLB → 统计(skinned/bones/clips/tris/tex) → 对齐(包根 Group 缩放/旋转/平移, 不破坏 skin)
//       → 重命名 mesh/mat(spec §3.4) → 可选贴图微调 → GLTFExporter 导出(保留 animations)
// 用法: node tools/align_cc0_glb.mjs INPUT.glb OUTPUT.glb [--target-h 0.5] [--face-rot 0] [--report-only]
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
      blob.arrayBuffer().then((buf) => { this.result = buf; if (this.onloadend) this.onloadend(); if (this.onload) this.onload(); });
    }
    readAsDataURL(blob) {
      blob.arrayBuffer().then((buf) => {
        this.result = 'data:application/octet-stream;base64,' + Buffer.from(buf).toString('base64');
        if (this.onloadend) this.onloadend(); if (this.onload) this.onload();
      });
    }
  };
}

const args = process.argv.slice(2);
const input = args[0], output = args[1];
let targetH = 0.5, faceRot = 0, reportOnly = false;
for (let i = 2; i < args.length; i++) {
  if (args[i] === '--target-h') targetH = parseFloat(args[++i]);
  else if (args[i] === '--face-rot') faceRot = parseFloat(args[++i]);
  else if (args[i] === '--report-only') reportOnly = true;
}

const log = [];
const L = (m) => { log.push(String(m)); };

const data = readFileSync(input);
new GLTFLoader().parse(data.buffer, '', (gltf) => {
  const scene = gltf.scene;
  // ---- 0. 统计 ----
  let meshes = 0, tris = 0, skinned = 0, bones = 0;
  const boneNames = [], clipList = [];
  scene.traverse(o => {
    if (o.isMesh) {
      meshes++;
      const g = o.geometry;
      tris += g.index ? g.index.count / 3 : g.attributes.position.count / 3;
      if (o.isSkinnedMesh) skinned++;
    }
    if (o.isBone) { bones++; boneNames.push(o.name); }
  });
  for (const c of gltf.animations) clipList.push(`${c.name}(${c.duration.toFixed(2)}s,${c.tracks.length}t)`);
  const texCount = [];
  scene.traverse(o => { if (o.isMesh && o.material) {
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    mats.forEach(m => { const mm = m; if (mm.map) texCount.push('base'); if (mm.normalMap) texCount.push('normal'); if (mm.metalnessMap || mm.roughnessMap) texCount.push('orm'); if (mm.emissiveMap) texCount.push('emissive'); });
  }});
  const texSet = [...new Set(texCount)];
  L(`[0] meshes=${meshes} skinned=${skinned} bones=${bones} tris=${Math.round(tris)} textures=${texSet.join(',')||'none'} clips=${clipList.join(' | ')||'none'}`);

  if (reportOnly) { L('====='); console.log(log.join('\n')); return; }

  // ---- 1. 对齐：包根 Group（不破坏 skin 绑定） ----
  const box = new THREE.Box3().setFromObject(scene);
  const size = box.getSize(new THREE.Vector3());
  const scale = targetH / size.y;
  const rotY = THREE.MathUtils.degToRad(faceRot);
  const wrap = new THREE.Group();
  wrap.name = 'aligned';
  wrap.add(scene);
  // 先旋转(绕 Y)，再缩放，再平移锚点
  // 旋转后 bbox 需重算 —— 简化：旋转矩阵应用在 wrap 上，锚点按原 bbox 估算
  // 做法：wrap.scale = scale; wrap.rotation.y = rotY; 然后平移使脚底 y=0、x/z 居中
  wrap.rotation.y = rotY;
  wrap.scale.setScalar(scale);
  // 平移：需要旋转后 bbox —— 手动算：旋转后 y 不变(绕Y)，x/z 交换
  // 用临时: 更新 world matrix
  wrap.updateMatrixWorld(true);
  const box2 = new THREE.Box3().setFromObject(wrap);
  const tx = -(box2.min.x + box2.max.x) / 2;
  const ty = -box2.min.y;
  const tz = -(box2.min.z + box2.max.z) / 2;
  wrap.position.set(tx, ty, tz);
  wrap.updateMatrixWorld(true);
  const box3 = new THREE.Box3().setFromObject(wrap);
  L(`[1] align: scale=${scale.toFixed(4)} rotY=${faceRot} t=(${tx.toFixed(4)},${ty.toFixed(4)},${tz.toFixed(4)})`);
  L(`[1] after bbox min=(${box3.min.x.toFixed(3)},${box3.min.y.toFixed(3)},${box3.min.z.toFixed(3)}) max=(${box3.max.x.toFixed(3)},${box3.max.y.toFixed(3)},${box3.max.z.toFixed(3)}) h=${(box3.max.y-box3.min.y).toFixed(3)}`);

  // ---- 2. 重命名 mesh/mat（保留骨骼名） ----
  scene.traverse(o => {
    if (o.isMesh && o.name && !o.name.startsWith('mesh_')) o.name = 'mesh_' + o.name.replace(/[^A-Za-z0-9_]/g, '_');
    if (o.isMesh && o.material && !Array.isArray(o.material)) {
      if (o.material.name && !o.material.name.startsWith('mat_')) o.material.name = 'mat_' + o.material.name.replace(/[^A-Za-z0-9_]/g, '_');
    }
  });

  // ---- 3. 导出 ----
  const exporter = new GLTFExporter();
  exporter.parse(wrap, (result) => {
    writeFileSync(output, Buffer.from(result));
    L(`[3] wrote ${output}`);
    L('=====');
    console.log(log.join('\n'));
  }, (err) => { L('[3] EXPORT ERROR: ' + err); console.log(log.join('\n')); process.exit(1); },
    { binary: true, animations: gltf.animations });
}, (e) => {
  L('LOAD ERROR: ' + (e && e.message ? e.message : String(e)));
  console.log(log.join('\n'));
  process.exit(1);
});
