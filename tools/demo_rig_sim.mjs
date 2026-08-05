#!/usr/bin/env node
// demo_rig_sim.mjs — 复刻 demo 页新 rigParts（双通道分类）验证拆件 GLB
// 用法: node tools/demo_rig_sim.mjs <file.glb> <out.txt>
// 额外测试：--strip-names 把 mesh 名改成 mesh_0..N，模拟 GLTFLoader 改名，验证 bbox 兜底
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { readFileSync, appendFileSync } from 'node:fs';

globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}

const [file, out] = process.argv.slice(2);
const stripNames = process.argv.includes('--strip-names');
const logl = (m) => { try { appendFileSync(out, m + '\n'); } catch {} };

// ---- 复制 demo 页 classify / sideToken ----
function sideToken(n) {
  const m = n.match(/[_-](l|r|left|right)$/);
  if (m) return (m[1] === 'l' || m[1] === 'left') ? 'L' : 'R';
  return '';
}
function classify(name) {
  const n = name.toLowerCase();
  if (n.includes('body')) return 'body';
  if (n.includes('beak') || n.includes('bill')) return 'beak';
  if (n.includes('head') || n.includes('comb') || n.includes('wattle')) return 'head';
  if (n.includes('leg') || n.includes('foot')) {
    const s = sideToken(n);
    if (s === 'L') return 'legL';
    if (s === 'R') return 'legR';
    if (n.includes('left')) return 'legL';
    if (n.includes('right')) return 'legR';
    return 'leg';
  }
  if (n.includes('wing')) {
    const s = sideToken(n);
    if (s === 'L') return 'wingL';
    if (s === 'R') return 'wingR';
    return 'wing';
  }
  if (n.includes('tail')) return 'tail';
  return 'extra';
}
function box3World(obj) {
  const b = new THREE.Box3();
  obj.updateWorldMatrix(true, false);
  b.setFromObject(obj);
  return b;
}
function classifyByBBox(o, namePart) {
  const bb = box3World(o);
  const cy = (bb.min.y + bb.max.y) / 2;
  const cz = (bb.min.z + bb.max.z) / 2;
  const cx = (bb.min.x + bb.max.x) / 2;
  if (bb.max.y < 0.09) return cx < 0 ? 'legL' : 'legR';
  if (cy > 0.36 && cz > 0.0) {
    if (namePart !== 'head' && bb.min.z > 0.19 && bb.max.z > 0.20 && (bb.max.y - bb.min.y) < 0.2) return 'beak';
    return 'head';
  }
  if (cz < -0.12) return 'tail';
  if (cy > 0.36) return 'head';
  return 'body';
}
function classifyDual(name, o) {
  const byName = classify(name);
  if (byName === 'legL' || byName === 'legR' || byName === 'head' || byName === 'beak' ||
      byName === 'body' || byName === 'tail') return byName;
  return classifyByBBox(o, byName);
}

const data = readFileSync(file);
const loader = new GLTFLoader();
loader.parse(data.buffer, '', (gltf) => {
  const nodes = [];
  gltf.scene.traverse(o => { if (o.isMesh) nodes.push(o); });
  logl(`[sim] nodes=${nodes.length} stripNames=${stripNames}`);
  // 可选：破坏 name
  if (stripNames) nodes.forEach((n, i) => { n.name = 'mesh_' + i; });
  const parts = { body: null, head: null, beak: null, legL: null, legR: null };
  const found = { body: false, head: false, beak: false, legL: false, legR: false };
  for (const n of nodes) {
    const byName = classify(n.name);
    const c = classifyDual(n.name, n);
    const bb = box3World(n);
    logl(`  name=${JSON.stringify(n.name)} -> byName=${byName} -> final=${c} cy=${((bb.min.y+bb.max.y)/2).toFixed(2)} cz=${((bb.min.z+bb.max.z)/2).toFixed(2)}`);
    if (c === 'body' && !parts.body) { parts.body = n; found.body = true; }
    else if (c === 'head' && !parts.head) { parts.head = n; found.head = true; }
    else if (c === 'beak' && !parts.beak) { parts.beak = n; found.beak = true; }
    else if (c === 'legL' && !parts.legL) { parts.legL = n; found.legL = true; }
    else if (c === 'legR' && !parts.legR) { parts.legR = n; found.legR = true; }
  }
  // 腿 fallback
  if (!found.legL || !found.legR) {
    const legs = nodes.filter(n => { const c = classifyDual(n.name, n); return c === 'leg' || c === 'legL' || c === 'legR'; });
    for (const n of legs) {
      if (n === parts.legL || n === parts.legR) continue;
      const bb = box3World(n); const cx = (bb.min.x + bb.max.x) / 2;
      if (!found.legL && cx < 0) { parts.legL = n; found.legL = true; }
      else if (!found.legR && cx > 0) { parts.legR = n; found.legR = true; }
      else if (!found.legL) { parts.legL = n; found.legL = true; }
      else if (!found.legR) { parts.legR = n; found.legR = true; }
    }
  }
  const hasParts = found.body && (found.legL || found.legR);
  const modeTag = hasParts ? `多部件真关节（mesh×${nodes.length}）` : '⚠ 回退：旧单 mesh 整体动画';
  logl(`found=${JSON.stringify(found)} hasParts=${hasParts} modeTag=${modeTag}`);
}, (err) => {
  logl('PARSE ERROR: ' + (err && err.stack ? err.stack.split('\n').slice(0, 6).join(' | ') : String(err)));
});
