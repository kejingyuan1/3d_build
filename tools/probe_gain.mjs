#!/usr/bin/env node
// probe_gain.mjs — 测 rootJoint.position 对 GPU 顶点 bbox 的增益（两点法）
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
  let mesh = null;
  gltf.scene.traverse(o => { if (o.isSkinnedMesh) mesh = o; });
  const rj = gltf.scene.getObjectByName('_rootJoint');
  rj.scale.setScalar(1.037);
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
  const b0 = gpuBBox();
  lines.push(`t=(0,0,0): min_y=${b0.min.y.toFixed(4)} max_y=${b0.max.y.toFixed(4)} h=${(b0.max.y-b0.min.y).toFixed(4)} cx=${((b0.min.x+b0.max.x)/2).toFixed(4)} cz=${((b0.min.z+b0.max.z)/2).toFixed(4)}`);
  rj.position.y = 10;
  const by = gpuBBox();
  lines.push(`t=(0,10,0): min_y=${by.min.y.toFixed(4)} max_y=${by.max.y.toFixed(4)} -> gainY=${((by.min.y-b0.min.y)/10).toFixed(6)}`);
  rj.position.y = 0; rj.position.x = 10;
  const bx = gpuBBox();
  lines.push(`t=(10,0,0): cx=${((bx.min.x+bx.max.x)/2).toFixed(4)} -> gainX=${(((bx.min.x+bx.max.x)/2-((b0.min.x+b0.max.x)/2))/10).toFixed(6)}`);
  rj.position.x = 0; rj.position.z = 10;
  const bz = gpuBBox();
  lines.push(`t=(0,0,10): cz=${((bz.min.z+bz.max.z)/2).toFixed(4)} -> gainZ=${(((bz.min.z+bz.max.z)/2-((b0.min.z+b0.max.z)/2))/10).toFixed(6)}`);
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'PARSE ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
