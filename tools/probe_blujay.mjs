#!/usr/bin/env node
// probe_blujay.mjs — 加载 blujay 静态鸡 GLB，输出每个 Mesh 的材质名/bbox/顶点数，用于部件语义判断
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { readFileSync, appendFileSync } from 'node:fs';

globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}

const [file, out] = process.argv.slice(2);
const logl = (m) => { try { appendFileSync(out, m + '\n'); } catch {} };

const data = readFileSync(file);
const loader = new GLTFLoader();
loader.parse(data.buffer, '', (gltf) => {
  const meshes = [];
  gltf.scene.traverse(o => { if (o.isMesh) meshes.push(o); });
  logl(`[probe] scene children=${gltf.scene.children.length} meshes=${meshes.length}`);
  for (const m of meshes) {
    const matName = m.material ? (m.material.name || '(unnamed)') : '(none)';
    const g = m.geometry;
    g.computeBoundingBox();
    const bb = g.boundingBox;
    const tris = g.index ? g.index.count / 3 : (g.attributes.position ? g.attributes.position.count / 3 : 0);
    logl(`mesh name=${m.name || '(unnamed)'} mat=${matName} verts=${g.attributes.position ? g.attributes.position.count : 0} tris=${Math.round(tris)}`);
    logl(`  bbox min=(${bb.min.x.toFixed(3)},${bb.min.y.toFixed(3)},${bb.min.z.toFixed(3)}) max=(${bb.max.x.toFixed(3)},${bb.max.y.toFixed(3)},${bb.max.z.toFixed(3)})`);
    if (m.material && m.material.color) {
      logl(`  color=#${m.material.color.getHexString()}`);
    }
  }
  // 全局 bbox
  const box = new THREE.Box3().setFromObject(gltf.scene);
  logl(`[global] min=(${box.min.x.toFixed(3)},${box.min.y.toFixed(3)},${box.min.z.toFixed(3)}) max=(${box.max.x.toFixed(3)},${box.max.y.toFixed(3)},${box.max.z.toFixed(3)})`);
}, (err) => {
  logl('PARSE ERROR: ' + (err && err.stack ? err.stack.split('\n').slice(0, 6).join(' | ') : String(err)));
});
