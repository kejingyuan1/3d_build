#!/usr/bin/env node
// verify_render_vertex.mjs — 模拟 GPU 渲染：每个顶点最终世界位置（applyBoneTransform + matrixWorld）
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
  let skinnedMesh = null;
  gltf.scene.traverse(o => { if (o.isSkinnedMesh) skinnedMesh = o; });
  lines.push('skinnedMesh found: ' + !!skinnedMesh);
  if (!skinnedMesh) { writeFileSync(out, lines.join('\n')); return; }
  lines.push('vertex count: ' + skinnedMesh.geometry.attributes.position.count);

  // scene root 链
  const chain = [];
  let cur = skinnedMesh;
  while (cur) { chain.unshift(`${cur.name}(s=${cur.scale ? cur.scale.x : '?'})`); cur = cur.parent; }
  lines.push('chain: ' + chain.join(' -> '));

  skinnedMesh.updateMatrixWorld(true);
  skinnedMesh.skeleton.update();
  const pos = skinnedMesh.geometry.attributes.position;
  const skinIdx = skinnedMesh.geometry.attributes.skinIndex;
  const skinWeight = skinnedMesh.geometry.attributes.skinWeight;
  lines.push('has skinIndex: ' + !!skinIdx + ', skinWeight: ' + !!skinWeight);
  if (skinIdx) {
    // 权重检查
    let badW = 0, badIdx = 0;
    for (let i = 0; i < pos.count; i++) {
      let sum = 0;
      for (let b = 0; b < 4; b++) {
        const w = skinWeight ? skinWeight.getX(i * 4 + b) : (b === 0 ? 1 : 0);
        const idx = skinIdx ? skinIdx.getX(i * 4 + b) : 0;
        sum += w;
        if (idx >= skinnedMesh.skeleton.bones.length) badIdx++;
      }
      if (Math.abs(sum - 1) > 0.01) badW++;
    }
    lines.push(`weight sum != 1: ${badW} / bad bone index: ${badIdx}`);
  }

  // GPU 等价：每个顶点世界位置 = applyBoneTransform × mesh.matrixWorld
  let minX = Infinity, minY = Infinity, minZ = Infinity;
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
  let nanCount = 0, extremeCount = 0, zeroCount = 0;
  const samples = [];
  for (let i = 0; i < pos.count; i++) {
    const v = new THREE.Vector3().fromBufferAttribute(pos, i);
    skinnedMesh.applyBoneTransform(i, v);
    v.applyMatrix4(skinnedMesh.matrixWorld);
    if (isNaN(v.x) || isNaN(v.y) || isNaN(v.z)) { nanCount++; continue; }
    if (Math.abs(v.x) > 100 || Math.abs(v.y) > 100 || Math.abs(v.z) > 100) { extremeCount++; continue; }
    if (v.x === 0 && v.y === 0 && v.z === 0) zeroCount++;
    if (samples.length < 3) samples.push(`v[${i}]=(${v.x.toFixed(3)},${v.y.toFixed(3)},${v.z.toFixed(3)})`);
    minX = Math.min(minX, v.x); minY = Math.min(minY, v.y); minZ = Math.min(minZ, v.z);
    maxX = Math.max(maxX, v.x); maxY = Math.max(maxY, v.y); maxZ = Math.max(maxZ, v.z);
  }
  lines.push('samples: ' + samples.join(' | '));
  lines.push('world bbox: min=(' + [minX, minY, minZ].map(x => x.toFixed(3)).join(',') + ') max=(' + [maxX, maxY, maxZ].map(x => x.toFixed(3)).join(',') + ')');
  lines.push(`NaN: ${nanCount} / extreme(>100): ${extremeCount} / zero: ${zeroCount}`);
  // mesh.matrixWorld
  const e = skinnedMesh.matrixWorld.elements;
  lines.push('mesh.matrixWorld row0: ' + [e[0], e[1], e[2], e[3]].map(x => +x.toFixed(4)).join(', '));
  lines.push('mesh.matrixWorld row1: ' + [e[4], e[5], e[6], e[7]].map(x => +x.toFixed(4)).join(', '));
  lines.push('mesh.matrixWorld row2: ' + [e[8], e[9], e[10], e[11]].map(x => +x.toFixed(4)).join(', '));
  lines.push('mesh.matrixWorld row3: ' + [e[12], e[13], e[14], e[15]].map(x => +x.toFixed(4)).join(', '));
  // rootJoint matrixWorld
  const rj = gltf.scene.getObjectByName('_rootJoint');
  if (rj) {
    const re = rj.matrixWorld.elements;
    lines.push('rootJoint.matrixWorld row0: ' + [re[0], re[1], re[2], re[3]].map(x => +x.toFixed(4)).join(', '));
    lines.push('rootJoint.matrixWorld row3: ' + [re[12], re[13], re[14], re[15]].map(x => +x.toFixed(4)).join(', '));
  }
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'PARSE ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 8).join(' | ') : String(e)));
});
