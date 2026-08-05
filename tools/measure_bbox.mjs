#!/usr/bin/env node
// measure_bbox.mjs — 测 GLB 渲染级 bbox（含 skinned mesh CPU 变形）
// 用法: node tools/measure_bbox.mjs FILE.glb OUT.txt
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { readFileSync, writeFileSync } from 'node:fs';
globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}
const [file, out] = process.argv.slice(2);
const data = readFileSync(file);
new GLTFLoader().parse(data.buffer, '', (gltf) => {
  const lines = [];
  gltf.scene.updateMatrixWorld(true);
  // skinned mesh CPU 变形顶点
  const worldVerts = [];
  const min = new THREE.Vector3(Infinity, Infinity, Infinity);
  const max = new THREE.Vector3(-Infinity, -Infinity, -Infinity);
  gltf.scene.traverse(o => {
    if (o.isSkinnedMesh) {
      o.updateMatrixWorld(true);
      o.skeleton.update();
      const pos = o.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const v = o.applyBoneTransform(i, new THREE.Vector3());
        min.min(v);
        max.max(v);
      }
    }
  });
  if (min.x === Infinity) {
    // 非 skinned：用 setFromObject
    const bb = new THREE.Box3().setFromObject(gltf.scene);
    lines.push(`setFromObject: min=(${bb.min.x.toFixed(3)},${bb.min.y.toFixed(3)},${bb.min.z.toFixed(3)}) max=(${bb.max.x.toFixed(3)},${bb.max.y.toFixed(3)},${bb.max.z.toFixed(3)}) h=${(bb.max.y-bb.min.y).toFixed(3)}`);
  } else {
    lines.push(`skinned CPU: min=(${min.x.toFixed(3)},${min.y.toFixed(3)},${min.z.toFixed(3)}) max=(${max.x.toFixed(3)},${max.y.toFixed(3)},${max.z.toFixed(3)}) h=${(max.y-min.y).toFixed(3)}`);
  }
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
