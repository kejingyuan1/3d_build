#!/usr/bin/env node
// verify_cc0_glb.mjs — 验证导出的 CC0 鸡 GLB：animations / bones / bbox / 动画可播放
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { readFileSync, writeFileSync } from 'node:fs';

globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}

const file = process.argv[2];
const out = process.argv[3];
const data = readFileSync(file);
new GLTFLoader().parse(data.buffer, '', (gltf) => {
  const lines = [];
  lines.push(`[verify] ${file}`);
  lines.push('animations: ' + gltf.animations.length);
  for (const c of gltf.animations) {
    lines.push(`  clip '${c.name}' duration=${c.duration.toFixed(2)}s tracks=${c.tracks.length} loop=${c.loop === THREE.LoopRepeat}`);
    for (const t of c.tracks) lines.push(`    ${t.name} frames=${t.times.length}`);
  }
  let bones = 0;
  const boneNames = [];
  let meshes = 0;
  gltf.scene.traverse(o => { if (o.isBone) { bones++; boneNames.push(o.name); } if (o.isMesh) meshes++; });
  lines.push(`bones: ${bones} ${JSON.stringify(boneNames)}`);
  lines.push(`meshes: ${meshes}`);
  const bb = new THREE.Box3().setFromObject(gltf.scene);
  lines.push(`bbox min=(${bb.min.x.toFixed(3)},${bb.min.y.toFixed(3)},${bb.min.z.toFixed(3)}) max=(${bb.max.x.toFixed(3)},${bb.max.y.toFixed(3)},${bb.max.z.toFixed(3)}) height=${(bb.max.y - bb.min.y).toFixed(3)}`);

  // 动画可播放性：混入 mixer，逐 clip 推进时间采样
  const mixer = new THREE.AnimationMixer(gltf.scene);
  const plays = [];
  for (const c of gltf.animations) {
    const action = mixer.clipAction(c);
    action.play();
    let ok = true, cnt = 0;
    for (let t = 0; t <= c.duration; t += c.duration / 20) {
      mixer.setTime(t);
      mixer.update(0.001);
      cnt++;
      if (!action.isRunning()) { ok = false; break; }
    }
    plays.push(`${c.name}: playable=${ok} samples=${cnt}`);
    action.stop();
  }
  lines.push('playback: ' + plays.join(' | '));
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
