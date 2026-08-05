#!/usr/bin/env node
// fix_eyes_root.mjs — 眼睛/毛簇改挂 bone_root（不再依赖 head bone）
// 世界坐标从「渲染头中心」计算：applyBoneTransform 渲染头区顶点 → bbox → center/halfW/maxY
// 作用：眼睛位置 100% 由 head mesh 决定，与骨骼布局无关；eat 低头时眼睛不随头（接受的代价）
// 用法: node tools/fix_eyes_root.mjs <in.glb> <out.glb>
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

const [inFile, outFile] = process.argv.slice(2);
const log = [];
const L = (m) => { log.push(String(m)); };

function renderHeadRegion(sm) {
  sm.updateMatrixWorld(true); sm.skeleton.update();
  const pos = sm.geometry.attributes.position;
  const v = new THREE.Vector3();
  const full = new THREE.Box3();
  for (let i = 0; i < pos.count; i++) { v.fromBufferAttribute(pos, i); sm.applyBoneTransform(i, v); full.expandByPoint(v); }
  const H = full.max.y - full.min.y, D = full.max.z - full.min.z;
  // 头区：前 12% 深 × 上 38% 高
  const head = new THREE.Box3();
  let n = 0;
  for (let i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    if (v.z > full.min.z + 0.88 * D && v.y > full.min.y + 0.62 * H) { sm.applyBoneTransform(i, v); head.expandByPoint(v); n++; }
  }
  const degenerate = n < 20 || (head.max.y - head.min.y) < 0.03 * H || (head.max.x - head.min.x) < 0.03 * H;
  if (degenerate) {
    // 宽头区兜底：前 50% 深 × 上 30% 高（鸡等头区几何退化）
    head.makeEmpty(); n = 0;
    for (let i = 0; i < pos.count; i++) {
      v.fromBufferAttribute(pos, i);
      if (v.z > full.min.z + 0.5 * D && v.y > full.min.y + 0.70 * H) { sm.applyBoneTransform(i, v); head.expandByPoint(v); n++; }
    }
    L(`[head] degenerate → broad region n=${n}`);
  }
  return { head, n, H, D, full };
}

function main() {
  const data = readFileSync(inFile);
  new GLTFLoader().parse(data.buffer, '', (gltf) => {
    const scene = gltf.scene;
    let sm = null; scene.traverse(o => { if (o.isSkinnedMesh && !sm) sm = o; });
    const rootBone = scene.getObjectByName('bone_root') || scene;
    if (!sm) { L('no skinned mesh'); console.log(log.join('\n')); return; }
    scene.updateMatrixWorld(true);

    const { head, n } = renderHeadRegion(sm);
    const hc = head.getCenter(new THREE.Vector3());
    const halfW = (head.max.x - head.min.x) / 2;
    const headMinY = head.min.y, headMaxY = head.max.y;
    L(`[head] n=${n} center=(${hc.x.toFixed(3)},${hc.y.toFixed(3)},${hc.z.toFixed(3)}) halfW=${halfW.toFixed(3)} y=${headMinY.toFixed(3)}..${headMaxY.toFixed(3)}`);

    // 收集眼睛/毛簇（hl 是 eye 的 child，会随 eye 一起重挂）
    const eyes = [];
    const tufts = [];
    scene.traverse(o => {
      if (!o.isMesh) return;
      if (/mesh_eye_(L|R)$/.test(o.name)) eyes.push(o);
      else if (/^mesh_tuft_/.test(o.name)) tufts.push(o);
    });
    L(`[fix] eyes=${eyes.length} tufts=${tufts.length}`);

    const eyeR = eyes.length ? (() => {
      const g = eyes[0].geometry;
      g.computeBoundingSphere();
      return g.boundingSphere.radius / Math.sqrt(3); // 还原球半径（bbox 半对角=√3r）
    })() : 0.01;
    L(`[fix] eyeR=${eyeR.toFixed(4)}`);

    // 眼睛目标世界位置：头侧表面（halfW + eyeR*0.1），上部
    const eyeY = headMinY + (headMaxY - headMinY) * 0.55;
    const eyeZ = hc.z;
    const eyeX = halfW + eyeR * 0.1;
    // 毛簇目标：头顶中心
    const tBase = new THREE.Vector3(0, headMaxY, hc.z);

    // 先全部 reparent 到 scene（保持当前 world），再设目标世界坐标，再 attach 到 bone_root（保持新 world）
    scene.updateMatrixWorld(true);
    eyes.forEach(e => scene.attach(e));
    tufts.forEach(t => scene.attach(t));
    scene.updateMatrixWorld(true);
    eyes.forEach(e => {
      const side = e.name.endsWith('_L') ? -1 : 1;
      e.position.set(side * eyeX, eyeY, eyeZ);
      rootBone.attach(e);
    });
    tufts.forEach(t => {
      t.position.copy(tBase);
      rootBone.attach(t);
    });
    L(`[fix] repositioned & re-parented to bone_root`);

    // 导出
    const exporter = new GLTFExporter();
    exporter.parse(scene, (result) => {
      writeFileSync(outFile, Buffer.from(result));
      L(`[out] ${outFile} (${(Buffer.from(result).length / 1024).toFixed(1)} KB)`);
      // verify：重解析
      const data2 = readFileSync(outFile);
      new GLTFLoader().parse(data2.buffer, '', (gltf2) => {
        let sm2 = null; gltf2.scene.traverse(o => { if (o.isSkinnedMesh && !sm2) sm2 = o; });
        const { head: head2 } = renderHeadRegion(sm2);
        const dist = (box, pt) => {
          const cx = Math.max(box.min.x, Math.min(pt.x, box.max.x));
          const cy = Math.max(box.min.y, Math.min(pt.y, box.max.y));
          const cz = Math.max(box.min.z, Math.min(pt.z, box.max.z));
          return Math.hypot(pt.x - cx, pt.y - cy, pt.z - cz);
        };
        const w = new THREE.Vector3();
        gltf2.scene.traverse(o => {
          if (o.isMesh && /(mesh_eye_(L|R)$|^mesh_tuft_)/.test(o.name)) {
            o.getWorldPosition(w);
            L(`[verify] ${o.name} world=(${w.x.toFixed(3)},${w.y.toFixed(3)},${w.z.toFixed(3)}) distToHead=${dist(head2, w).toFixed(4)}m parent=${o.parent.name}`);
          }
        });
        console.log(log.join('\n'));
      }, (e) => { L('verify ERR ' + e); console.log(log.join('\n')); });
    }, (err) => { L('EXPORT ERR ' + err); console.log(log.join('\n')); process.exit(1); }, { binary: true, animations: gltf.animations });
  }, (e) => { L('LOAD ERR ' + e); console.log(log.join('\n')); });
}
main();
