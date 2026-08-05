#!/usr/bin/env node
// analyze_clip.mjs — 采样骨骼动画关键姿态，识别动作阶段（walk/eat/idle）
// 用法: node tools/analyze_clip.mjs FILE.glb CLIP_NAME
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { readFileSync, writeFileSync } from 'node:fs';

globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}

const [file, clipName, out] = process.argv.slice(2);
const data = readFileSync(file);
new GLTFLoader().parse(data.buffer, '', (gltf) => {
  const lines = [];
  const clip = gltf.animations.find(c => c.name === clipName) || gltf.animations[0];
  lines.push(`[analyze] clip=${clip.name} duration=${clip.duration.toFixed(2)}s tracks=${clip.tracks.length}`);

  // 骨骼名
  const bones = [];
  gltf.scene.traverse(o => { if (o.isBone) bones.push(o.name); });
  lines.push('bones: ' + JSON.stringify(bones));

  // 采样关键骨骼（含 leg/neck/head/beak/root/body/hip/root 的）
  const sampler = new THREE.AnimationMixer(gltf.scene);
  const action = sampler.clipAction(clip);
  action.play();
  const trackNames = clip.tracks.map(t => t.name);
  lines.push('tracks: ' + JSON.stringify(trackNames));

  // 对每个 0.5s 采样，记录关键骨骼世界旋转/位置
  const keyBones = bones.filter(n => /Thigh|Calf|Foot|leg|neck|head|beak|root|body|hip|Spine/i.test(n));
  lines.push('key bones: ' + JSON.stringify(keyBones));
  const N = Math.ceil(clip.duration / 0.5);
  for (let i = 0; i <= N; i++) {
    const t = i * 0.5;
    sampler.setTime(Math.min(t, clip.duration));
    const row = [`t=${t.toFixed(1)}s`];
    for (const bn of keyBones) {
      const b = gltf.scene.getObjectByName(bn);
      if (b) {
        const w = new THREE.Vector3();
        b.getWorldPosition(w);
        // 旋转简化为欧拉近似
        const q = new THREE.Quaternion();
        b.getWorldQuaternion(q);
        const e = new THREE.Euler().setFromQuaternion(q);
        row.push(`${bn}:(${w.x.toFixed(2)},${w.y.toFixed(2)},${w.z.toFixed(2)})r(${e.x.toFixed(2)},${e.y.toFixed(2)},${e.z.toFixed(2)})`);
      }
    }
    lines.push(row.join(' | '));
  }
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
