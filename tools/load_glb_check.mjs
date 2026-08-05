#!/usr/bin/env node
// load_glb_check.mjs — 用 three GLTFLoader 实测加载 GLB，打印完整错误栈到文件
// 用法: node tools/load_glb_check.mjs <file.glb> <out.txt>
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { readFileSync, appendFileSync } from 'node:fs';

// Node 环境桩：GLTFLoader 纹理解码需要浏览器 self/createImageBitmap
globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}

const [file, out] = process.argv.slice(2);
if (!file) { console.error('usage: load_glb_check.mjs <file.glb> <out.txt>'); process.exit(1); }
const logl = (msg) => { try { appendFileSync(out, msg + '\n'); } catch {} };

logl(`[load_glb_check] file=${file} three=${THREE.REVISION}`);
const data = readFileSync(file);
logl(`  bytes=${data.length}`);

const loader = new GLTFLoader();
loader.parse(data.buffer, '', (gltf) => {
  logl('  PARSE OK');
  const names = [];
  let tris = 0;
  gltf.scene.traverse(o => {
    if (o.isMesh) {
      names.push(o.name);
      const g = o.geometry;
      tris += g.index ? g.index.count / 3 : (g.attributes.position ? g.attributes.position.count / 3 : 0);
      logl(`  mesh ${o.name}: index=${g.index ? 'YES(' + g.index.count + ')' : 'NO'} pos=${g.attributes.position ? g.attributes.position.count : 0} nrm=${g.attributes.normal ? 'YES' : 'NO'} uv=${g.attributes.uv ? 'YES' : 'NO'}`);
    }
  });
  logl(`  meshes=${names.length} names=${JSON.stringify(names)} tris=${Math.round(tris)}`);
}, (err) => {
  logl('  PARSE ERROR:');
  logl('  ' + (err && err.stack ? err.stack.split('\n').slice(0, 12).join('\n  ') : String(err)));
});
