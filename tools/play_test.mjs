#!/usr/bin/env node
// play_test.mjs — 播放 3 clips，捕获 PropertyBinding 错误
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { readFileSync, writeFileSync } from 'node:fs';
globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}
const [file, out] = process.argv.slice(2);
const data = readFileSync(file);
const warns = [];
const origWarn = console.warn;
console.warn = (...a) => warns.push(a.join(' '));
new GLTFLoader().parse(data.buffer, '', (gltf) => {
  const lines = [];
  lines.push('animations: ' + gltf.animations.length);
  const mixer = new THREE.AnimationMixer(gltf.scene);
  for (const c of gltf.animations) {
    const a = mixer.clipAction(c);
    a.play();
    for (let t = 0; t <= c.duration; t += c.duration / 10) { mixer.setTime(t); mixer.update(0.001); }
    a.stop();
    lines.push(`  ${c.name}: played ${c.duration.toFixed(2)}s OK`);
  }
  console.warn = origWarn;
  const pb = warns.filter(w => w.includes('PropertyBinding') || w.includes('not found'));
  lines.push(pb.length ? 'WARN:\n' + pb.join('\n') : 'NO PropertyBinding errors');
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'PARSE ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
