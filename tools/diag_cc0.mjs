#!/usr/bin/env node
// diag_cc0.mjs — 诊断对齐后 GLB：节点 scale、动画驱动、bbox（含动画前后）
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
  lines.push(`[diag] ${file}`);
  lines.push('scene children: ' + gltf.scene.children.map(c => `${c.name}(s=${c.scale.x.toFixed(4)},p=(${c.position.x.toFixed(3)},${c.position.y.toFixed(3)},${c.position.z.toFixed(3)}))`).join(' | '));
  // 找 CHICKEN_ 节点
  const chicken = gltf.scene.getObjectByName('CHICKEN_') || gltf.scene.getObjectByName('CHICKEN_') || null;
  if (chicken) {
    lines.push(`CHICKEN_ scale=(${chicken.scale.x.toFixed(4)},${chicken.scale.y.toFixed(4)},${chicken.scale.z.toFixed(4)}) pos=(${chicken.position.x.toFixed(3)},${chicken.position.y.toFixed(3)},${chicken.position.z.toFixed(3)})`);
  }
  // rootJoint
  const rj = gltf.scene.getObjectByName('_rootJoint');
  if (rj) {
    const wp = new THREE.Vector3(); rj.getWorldPosition(wp);
    lines.push(`_rootJoint world pos=(${wp.x.toFixed(3)},${wp.y.toFixed(3)},${wp.z.toFixed(3)}) localScale=(${rj.scale.x.toFixed(4)},${rj.scale.y.toFixed(4)},${rj.scale.z.toFixed(4)})`);
  }
  // 动画前 bbox
  let bb = new THREE.Box3().setFromObject(gltf.scene);
  lines.push(`bbox BEFORE anim: min=(${bb.min.x.toFixed(3)},${bb.min.y.toFixed(3)},${bb.min.z.toFixed(3)}) max=(${bb.max.x.toFixed(3)},${bb.max.y.toFixed(3)},${bb.max.z.toFixed(3)}) h=${(bb.max.y-bb.min.y).toFixed(3)}`);
  // 动画后 bbox（采样 Take 001 t=0 和 t=2.5）
  const mixer = new THREE.AnimationMixer(gltf.scene);
  const clip = gltf.animations[0];
  const action = mixer.clipAction(clip);
  action.play();
  for (const t of [0, 1.0, 2.5, 3.5]) {
    mixer.setTime(t);
    mixer.update(0.001);
    gltf.scene.updateMatrixWorld(true);
    bb = new THREE.Box3().setFromObject(gltf.scene);
    lines.push(`bbox anim t=${t}: min=(${bb.min.x.toFixed(3)},${bb.min.y.toFixed(3)},${bb.min.z.toFixed(3)}) max=(${bb.max.x.toFixed(3)},${bb.max.y.toFixed(3)},${bb.max.z.toFixed(3)}) h=${(bb.max.y-bb.min.y).toFixed(3)}`);
  }
  // 贴图
  let texInfo = [];
  gltf.scene.traverse(o => { if (o.isMesh && o.material) { const mm = o.material; texInfo.push(`map=${!!mm.map} nrm=${!!mm.normalMap}`); } });
  lines.push('textures: ' + JSON.stringify(texInfo));
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
