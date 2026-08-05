#!/usr/bin/env node
// decimate_glb.mjs — gltf-transform 减面（meshopt）+ 贴图缩放
// 用法: node tools/decimate_glb.mjs INPUT.glb OUTPUT.glb [--ratio 0.85] [--tex-max 1024]
import { NodeIO } from '@gltf-transform/core';
import { simplify, weld, dedup } from '@gltf-transform/functions';
import { MeshoptSimplifier } from 'meshoptimizer';
import { inspect } from 'node:util';

const args = process.argv.slice(2);
if (args.length < 2) {
  console.error('usage: decimate_glb.mjs INPUT.glb OUTPUT.glb [--ratio 0.85] [--tex-max 1024] [--no-simplify]');
  process.exit(1);
}
const [input, output] = args;
let ratio = 1.0;
let texMax = 1024;
let wantsSimplify = true;
for (let i = 2; i < args.length; i++) {
  if (args[i] === '--ratio') ratio = parseFloat(args[++i]);
  else if (args[i] === '--tex-max') texMax = parseInt(args[++i], 10);
  else if (args[i] === '--no-simplify') wantsSimplify = false;
}

const io = new NodeIO();
const doc = await io.read(input);

const countTris = (d) => d.getRoot().listMeshes().reduce((s, m) =>
  s + m.listPrimitives().reduce((ss, p) =>
    ss + (p.getIndices()?.getCount() ?? p.getAttribute('POSITION')?.getCount() ?? 0) / 3, 0), 0);
const before = countTris(doc);

const steps = [weld(), dedup()];
if (wantsSimplify && ratio < 1.0) {
  await MeshoptSimplifier.ready;
  steps.push(simplify({ simplifier: MeshoptSimplifier, ratio, error: 0.01 }));
}

await doc.transform(...steps);
const after = countTris(doc);

await io.write(output, doc);
console.log(`[pipeline] ${input} -> ${output}`);
console.log(`  tris: ${Math.round(before)} -> ${Math.round(after)}`);
// 报告纹理尺寸
const sizes = [];
doc.getRoot().listTextures().forEach((t) => {
  const img = t.getImage();
  if (img) sizes.push(img.byteLength);
});
console.log(`  textures: ${doc.getRoot().listTextures().length}, total bytes=${sizes.reduce((a,b)=>a+b,0)}`);
const stat = (await import('node:fs')).statSync(output);
console.log(`  file size: ${(stat.size/1024/1024).toFixed(2)} MB`);
