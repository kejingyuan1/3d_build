#!/usr/bin/env node
// calc_alignment.mjs — 迭代对齐 rootJoint TRS：GPU 顶点 bbox 收敛到 0.5m / 脚底 y=0 / x,z 居中
// 用法: node tools/calc_alignment.mjs INPUT.glb OUT_TRS.json [--start-scale 1.07]
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { readFileSync, writeFileSync } from 'node:fs';
globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}
const [file, out] = process.argv.slice(2);
let startScale = 1.07;
const si = process.argv.indexOf('--start-scale');
if (si !== -1) startScale = parseFloat(process.argv[si + 1]);
const data = readFileSync(file);
new GLTFLoader().parse(data.buffer, '', (gltf) => {
  const lines = [];
  let mesh = null;
  gltf.scene.traverse(o => { if (o.isSkinnedMesh) mesh = o; });
  const rj = gltf.scene.getObjectByName('_rootJoint');
  if (!mesh || !rj) { lines.push('ERR no mesh/rootJoint'); writeFileSync(out, lines.join('\n')); return; }
  // 初始化 rootJoint TRS
  rj.scale.setScalar(startScale);
  rj.position.set(0, 0, 0);

  function gpuBBox() {
    gltf.scene.updateMatrixWorld(true);
    mesh.updateMatrixWorld(true);
    mesh.skeleton.update();
    const pos = mesh.geometry.attributes.position;
    const min = new THREE.Vector3(Infinity, Infinity, Infinity);
    const max = new THREE.Vector3(-Infinity, -Infinity, -Infinity);
    for (let i = 0; i < pos.count; i++) {
      const v = new THREE.Vector3().fromBufferAttribute(pos, i);
      mesh.applyBoneTransform(i, v);
      v.applyMatrix4(mesh.matrixWorld);
      min.min(v); max.max(v);
    }
    return { min, max };
  }

  let bb = gpuBBox();
  lines.push(`[init] h=${(bb.max.y - bb.min.y).toFixed(3)} min_y=${bb.min.y.toFixed(3)} cx=${((bb.min.x + bb.max.x) / 2).toFixed(3)} cz=${((bb.min.z + bb.max.z) / 2).toFixed(3)}`);
  // 缩放收敛
  for (let i = 0; i < 8; i++) {
    bb = gpuBBox();
    const h = bb.max.y - bb.min.y;
    const f = 0.5 / h;
    rj.scale.multiplyScalar(f);
  }
  // 平移：两点法测增益（rootJoint.position 对 world bbox 的偏导），精确求解
  function measure() {
    bb = gpuBBox();
    return { min_y: bb.min.y, cx: (bb.min.x + bb.max.x) / 2, cz: (bb.min.z + bb.max.z) / 2 };
  }
  const D = 10.0;
  const p0 = measure();
  rj.position.y += D; const py = measure();
  rj.position.y -= D;
  rj.position.x += D; const px = measure();
  rj.position.x -= D;
  rj.position.z += D; const pz = measure();
  rj.position.z -= D;
  const gy = (py.min_y - p0.min_y) / D;
  const gx = (px.cx - p0.cx) / D;
  const gz = (pz.cz - p0.cz) / D;
  rj.position.y += -p0.min_y / gy;
  rj.position.x += -p0.cx / gx;
  rj.position.z += -p0.cz / gz;
  bb = gpuBBox();
  const h = bb.max.y - bb.min.y;
  const cx = (bb.min.x + bb.max.x) / 2;
  const cz = (bb.min.z + bb.max.z) / 2;
  lines.push(`[final] h=${h.toFixed(4)} min_y=${bb.min.y.toFixed(4)} max_y=${bb.max.y.toFixed(4)} cx=${cx.toFixed(4)} cz=${cz.toFixed(4)}`);
  lines.push(`[TRS] scale=${rj.scale.x.toFixed(5)} tx=${rj.position.x.toFixed(4)} ty=${rj.position.y.toFixed(4)} tz=${rj.position.z.toFixed(4)}`);
  lines.push(`[bbox] min=(${bb.min.x.toFixed(4)},${bb.min.y.toFixed(4)},${bb.min.z.toFixed(4)}) max=(${bb.max.x.toFixed(4)},${bb.max.y.toFixed(4)},${bb.max.z.toFixed(4)})`);
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'PARSE ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
