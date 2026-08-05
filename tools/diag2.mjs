#!/usr/bin/env node
// diag2.mjs — 诊断骨骼 matrixWorld scale 与 applyBoneTransform 结果
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
  // 场景根
  lines.push('scene root children: ' + gltf.scene.children.map(c => `${c.name}(s=${c.scale.x.toFixed(4)})`).join(', '));
  // rootJoint matrixWorld 缩放
  const rj = gltf.scene.getObjectByName('_rootJoint');
  if (rj) {
    const e = rj.matrixWorld.elements;
    const sx = Math.sqrt(e[0] ** 2 + e[1] ** 2 + e[2] ** 2);
    lines.push(`_rootJoint matrixWorld scaleX=${sx.toFixed(4)}`);
    const wp = new THREE.Vector3(); rj.getWorldPosition(wp);
    lines.push(`_rootJoint world pos=(${wp.x.toFixed(3)},${wp.y.toFixed(3)},${wp.z.toFixed(3)})`);
  }
  // skinned mesh
  let mesh = null;
  gltf.scene.traverse(o => { if (o.isSkinnedMesh) mesh = o; });
  if (mesh) {
    lines.push(`mesh.name=${mesh.name} parent=${mesh.parent ? mesh.parent.name : 'none'}`);
    const parent = mesh.parent;
    if (parent) {
      const ps = parent.scale;
      lines.push(`mesh.parent scale=(${ps.x.toFixed(4)},${ps.y.toFixed(4)},${ps.z.toFixed(4)})`);
    }
    // 手动算一个顶点（用骨骼世界矩阵 + inverseBindMatrix）
    mesh.updateMatrixWorld(true);
    mesh.skeleton.update();
    const bone = mesh.skeleton.bones[0];
    if (bone) {
      lines.push(`skeleton.bones[0]=${bone.name} matrixWorld scaleX=${(Math.sqrt(bone.matrixWorld.elements[0]**2+bone.matrixWorld.elements[1]**2+bone.matrixWorld.elements[2]**2)).toFixed(4)}`);
    }
    const pos = mesh.geometry.attributes.position;
    const v0 = mesh.applyBoneTransform(0, new THREE.Vector3());
    lines.push(`applyBoneTransform v[0]=(${v0.x.toFixed(3)},${v0.y.toFixed(3)},${v0.z.toFixed(3)})`);
    const vmid = mesh.applyBoneTransform(Math.floor(pos.count/2), new THREE.Vector3());
    lines.push(`applyBoneTransform v[mid]=(${vmid.x.toFixed(3)},${vmid.y.toFixed(3)},${vmid.z.toFixed(3)})`);
  }
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
