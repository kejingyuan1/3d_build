#!/usr/bin/env node
// check_track_names.mjs — 加载 GLB，对比 animation track 名与场景骨骼名，找不匹配
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
  const boneNames = new Set();
  gltf.scene.traverse(o => { if (o.isBone) boneNames.add(o.name); });
  lines.push('bones: ' + JSON.stringify([...boneNames]));
  for (const c of gltf.animations) {
    lines.push(`clip '${c.name}' duration=${c.duration.toFixed(2)} tracks=${c.tracks.length}`);
    const missing = [];
    for (const t of c.tracks) {
      const bone = t.name.split('.')[0];
      if (!boneNames.has(bone)) missing.push(t.name);
    }
    lines.push(`  missing bone tracks (${missing.length}): ${missing.slice(0, 12).join(' | ')}`);
  }
  writeFileSync(out, lines.join('\n'));
}, (e) => {
  writeFileSync(out, 'ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
