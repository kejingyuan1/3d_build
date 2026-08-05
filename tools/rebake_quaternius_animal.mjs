#!/usr/bin/env node
// rebake_quaternius_animal.mjs — 修复 Quaternius animated GLB 的 scale/权重问题，缩放到米制
//
// 背景：仓库 animated GLB（FBX→GLB trs:false）带「Armature node scale=100 + mesh node scale=100/65 + IBM 非正确逆」
// → three 渲染级 bbox 爆炸（~1e4 倍）。本脚本：
//   1. 归一化 skin weight（Σw→1）
//   2. 塌缩所有非单位 node scale → 1
//   3. 按目标头高 k=target/geometryHeight，把 k 烘进 geometry + 所有 node position + 动画 position track
//   4. 脚底锚 y=0（geometry + node position + position track 统一偏移）
//   5. skeleton.calculateInverses() 重算 IBM（吸收 k），bindMatrix 置 identity
//   6. 重命名 clip：idle/walk/eat + 额外保留
//   7. 导出 + 自带 verify（applyBoneTransform × matrixWorld 渲染级 bbox 报告）
//
// 用法: node tools/rebake_quaternius_animal.mjs <in.glb> <out.glb> <head_h_m> [clipMapJson]
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { readFileSync, writeFileSync } from 'node:fs';

globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}
if (typeof globalThis.FileReader === 'undefined') {
  globalThis.FileReader = class {
    readAsArrayBuffer(blob) {
      blob.arrayBuffer().then((buf) => {
        this.result = buf;
        if (this.onloadend) this.onloadend();
        if (this.onload) this.onload();
      });
    }
    readAsDataURL(blob) {
      blob.arrayBuffer().then((buf) => {
        this.result = 'data:application/octet-stream;base64,' + Buffer.from(buf).toString('base64');
        if (this.onloadend) this.onloadend();
        if (this.onload) this.onload();
      });
    }
  };
}

const [inFile, outFile, headHStr] = process.argv.slice(2);
if (!inFile || !outFile || !headHStr) {
  console.error('usage: node tools/rebake_quaternius_animal.mjs <in.glb> <out.glb> <head_h_m>');
  process.exit(1);
}
const HEAD_H = parseFloat(headHStr);

const log = [];
const L = (m) => { log.push(String(m)); };

function loadGLB(path) {
  return new Promise((resolve, reject) => {
    const data = readFileSync(path);
    new GLTFLoader().parse(data.buffer, '', resolve, reject);
  });
}

// 渲染级 bbox：applyBoneTransform × matrixWorld（与 verify_render_vertex.mjs 同口径）
function renderBBox(sm) {
  sm.updateMatrixWorld(true);
  sm.skeleton.update();
  const pos = sm.geometry.attributes.position;
  const min = new THREE.Vector3(Infinity, Infinity, Infinity);
  const max = new THREE.Vector3(-Infinity, -Infinity, -Infinity);
  const v = new THREE.Vector3();
  let nan = 0, extreme = 0;
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    sm.applyBoneTransform(i, v);
    v.applyMatrix4(sm.matrixWorld);
    if (!Number.isFinite(v.x) || !Number.isFinite(v.y) || !Number.isFinite(v.z)) { nan++; continue; }
    if (Math.abs(v.x) > 100 || Math.abs(v.y) > 100 || Math.abs(v.z) > 100) { extreme++; continue; }
    min.min(v); max.max(v);
  }
  return { min, max, nan, extreme, h: max.y - min.y };
}

function main() {
  loadGLB(inFile).then((gltf) => {
    const scene = gltf.scene;
    scene.updateMatrixWorld(true);

    // ---- 1. 找 skinned mesh ----
    let sm = null;
    scene.traverse(o => { if (o.isSkinnedMesh && !sm) sm = o; });
    if (!sm) { L('ERROR: no SkinnedMesh'); console.log(log.join('\n')); process.exit(1); }
    L(`[0] skinned mesh: ${sm.name} verts=${sm.geometry.attributes.position.count}`);

    // ---- 2. 归一化权重 ----
    const sw = sm.geometry.attributes.skinWeight;
    let badW = 0, wBefore = 0;
    for (let i = 0; i < sw.count; i++) {
      let s = 0;
      for (let b = 0; b < 4; b++) s += sw.getX(i * 4 + b);
      wBefore = Math.max(wBefore, s);
      if (Math.abs(s - 1) > 0.001) { badW++; const inv = 1 / s; for (let b = 0; b < 4; b++) sw.setX(i * 4 + b, sw.getX(i * 4 + b) * inv); }
    }
    sw.needsUpdate = true;
    L(`[1] weights: max sum before=${wBefore.toFixed(4)} bad=${badW} (normalized)`);

    // ---- 3. 塌缩所有非单位 node scale ----
    let collapsed = 0;
    scene.traverse(o => {
      const sx = o.scale ? o.scale.x : 1;
      if (Math.abs(sx - 1) > 1e-4 || Math.abs(o.scale.y - 1) > 1e-4 || Math.abs(o.scale.z - 1) > 1e-4) {
        collapsed++;
        o.scale.set(1, 1, 1);
      }
    });
    scene.updateMatrixWorld(true);
    L(`[2] collapsed non-unit node scales: ${collapsed}`);

    // ---- 4. 目标 k：geometry bbox 高度（塌缩后 bind=geometry）→ 头高 target ----
    const gbb = new THREE.Box3().setFromObject(sm);   // 网格局部 bbox（不含缩放）
    const gH = gbb.max.y - gbb.min.y;
    const k = HEAD_H / gH;
    L(`[3] geometry bbox h=${gH.toFixed(4)} target_head=${HEAD_H} k=${k.toFixed(5)}`);

    // ---- 5. k 烘进 geometry ----
    const gpos = sm.geometry.attributes.position;
    for (let i = 0; i < gpos.count; i++) {
      gpos.setXYZ(i, gpos.getX(i) * k, gpos.getY(i) * k, gpos.getZ(i) * k);
    }
    gpos.needsUpdate = true;
    sm.geometry.computeBoundingBox();
    sm.geometry.computeBoundingSphere();

    // ---- 6. k 烘进所有 node position ----
    scene.traverse(o => { o.position.multiplyScalar(k); });
    scene.updateMatrixWorld(true);

    // ---- 7. 锚脚底 y=0（用几何 min y） ----
    const bb2 = new THREE.Box3().setFromObject(sm);
    const feetY = bb2.min.y;
    L(`[4] after k: feetY=${feetY.toFixed(4)} head=${(bb2.max.y).toFixed(4)} h=${(bb2.max.y - feetY).toFixed(4)}`);
    const offset = -feetY;
    const gpos2 = sm.geometry.attributes.position;
    for (let i = 0; i < gpos2.count; i++) {
      gpos2.setY(i, gpos2.getY(i) + offset);
    }
    gpos2.needsUpdate = true;
    scene.traverse(o => { o.position.y += offset; });
    scene.updateMatrixWorld(true);
    const bb3 = new THREE.Box3().setFromObject(sm);
    L(`[5] anchored: feetY=${bb3.min.y.toFixed(4)} head=${bb3.max.y.toFixed(4)} h=${(bb3.max.y - bb3.min.y).toFixed(4)}`);

    // ---- 8. 动画 position track 同步 k + offset ----
    for (const clip of gltf.animations) {
      for (const t of clip.tracks) {
        if (t.name.endsWith('.position') && t.values.length >= 3) {
          for (let i = 0; i < t.values.length; i += 3) {
            t.values[i] *= k;
            t.values[i + 1] = t.values[i + 1] * k + offset;
            t.values[i + 2] *= k;
          }
        }
      }
    }

    // ---- 9. 重算 IBM + bindMatrix 置 identity ----
    sm.skeleton.calculateInverses();
    sm.bindMatrix.identity();
    sm.bindMatrixInverse.identity();
    sm.skeleton.update();
    L('[6] recalculated inverseBindMatrices; bindMatrix=identity');

    // ---- 10. 重命名 clip ----
    const clipNames = gltf.animations.map(c => c.name);
    L(`[7] original clips: ${JSON.stringify(clipNames)}`);
    // 默认映射：最后一个(长 idle) → idle，倒数第2(短 walk) → walk，其余按序 eat/walk2/eat2/misc
    // 允许 CLI 传入 clipMapJson: {"旧名":"新名"}
    const argClipMap = process.argv[4];
    if (argClipMap) {
      const map = JSON.parse(argClipMap);
      gltf.animations.forEach(c => { if (map[c.name]) c.name = map[c.name]; });
    } else {
      const n = gltf.animations.length;
      if (n >= 3) {
        // 启发式：时长最长=idle；最短=walk；其余=eat+后缀
        const sorted = gltf.animations.slice().sort((a, b) => a.duration - b.duration);
        const walk = sorted[0], idle = sorted[n - 1];
        const rest = sorted.slice(1, n - 1);
        walk.name = 'walk';
        idle.name = 'idle';
        rest.forEach((c, i) => { c.name = i === 0 ? 'eat' : (i === 1 ? 'walk2' : 'eat2'); });
      }
    }
    L(`[8] renamed clips: ${JSON.stringify(gltf.animations.map(c => c.name + '(' + c.duration.toFixed(2) + 's)'))}`);

    // ---- 11. 导出 ----
    const exporter = new GLTFExporter();
    const options = { binary: true, animations: gltf.animations };
    exporter.parse(scene, (result) => {
      writeFileSync(outFile, Buffer.from(result));
      const bytes = Buffer.from(result).length;
      L(`[9] wrote ${outFile} (${(bytes / 1024).toFixed(1)} KB)`);

      // ---- 12. 自带 verify：重新加载导出文件 ----
      const data = readFileSync(outFile);
      new GLTFLoader().parse(data.buffer, '', (gltf2) => {
        gltf2.scene.updateMatrixWorld(true);
        let sm2 = null;
        gltf2.scene.traverse(o => { if (o.isSkinnedMesh && !sm2) sm2 = o; });
        const bb = sm2 ? renderBBox(sm2) : null;
        L('[verify] re-parsed output:');
        if (bb) {
          L(`  render bbox min=(${bb.min.x.toFixed(3)},${bb.min.y.toFixed(3)},${bb.min.z.toFixed(3)}) max=(${bb.max.x.toFixed(3)},${bb.max.y.toFixed(3)},${bb.max.z.toFixed(3)})`);
          L(`  height=${bb.h.toFixed(3)}m feetY=${bb.min.y.toFixed(4)} nan=${bb.nan} extreme>100=${bb.extreme}`);
        } else {
          L('  NO skinned mesh!');
        }
        // 权重复检
        const sw2 = sm2.geometry.attributes.skinWeight;
        let bad = 0;
        for (let i = 0; i < sw2.count; i++) { let s = 0; for (let b = 0; b < 4; b++) s += sw2.getX(i * 4 + b); if (Math.abs(s - 1) > 0.01) bad++; }
        L(`  weight sum!=1: ${bad}`);
        // 网格节点 scale 链复检
        const chain = [];
        let cur = sm2;
        while (cur) { chain.unshift(`${cur.name}(s=${cur.scale ? cur.scale.x : '?'})`); cur = cur.parent; }
        L(`  chain: ${chain.join(' -> ')}`);
        L('=====');
        L(log.join('\n'));
        console.log(log.join('\n'));
      }, (e) => {
        L('VERIFY PARSE ERROR: ' + (e && e.message ? e.message : e));
        console.log(log.join('\n'));
        process.exit(1);
      });
    }, (err) => {
      L('EXPORT ERROR: ' + (err && err.message ? err.message : err));
      console.log(log.join('\n'));
      process.exit(1);
    }, options);
  }).catch((e) => {
    L('LOAD ERROR: ' + (e && e.message ? e.message : String(e)));
    console.log(log.join('\n'));
    process.exit(1);
  });
}
main();
