#!/usr/bin/env node
// gen_clips.mjs — 生成 eat(截取 Take 001 啄食段) + walk(程序化真实骨骼) clips JSON
// 输出 JSON 供 Python finalize 写入 GLB
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { AnimationUtils } from 'three';
import { readFileSync, writeFileSync } from 'node:fs';
globalThis.self = globalThis;
if (typeof globalThis.createImageBitmap !== 'function') {
  globalThis.createImageBitmap = async () => ({ width: 1, height: 1 });
}
const [file, out] = process.argv.slice(2);
const data = readFileSync(file);
new GLTFLoader().parse(data.buffer, '', (gltf) => {
  const take = gltf.animations.find(c => c.name === 'Take 001') || gltf.animations[0];
  const lines = [];

  // ---------- eat：手动截取 Take 001 啄食段 (t=0.75 ~ 1.5) ----------
  // 注意：AnimationUtils.subclip 的 start/end 是「帧号」(默认 fps=30)，传秒数会取到 0.025-0.05s 空段
  // 手动截取：保留 t∈[t0,t1] 的采样点，时间重映射到 0 起
  function sliceClip(clip, name, t0, t1) {
    const tracks = [];
    for (const t of clip.tracks) {
      const keepIdx = [];
      for (let i = 0; i < t.times.length; i++) {
        if (t.times[i] >= t0 && t.times[i] <= t1) keepIdx.push(i);
      }
      if (keepIdx.length < 2) continue;
      const times = keepIdx.map(i => +(t.times[i] - t0).toFixed(4));
      const stride = t.getValueSize();
      const values = [];
      for (const i of keepIdx) for (let c = 0; c < stride; c++) values.push(t.values[i * stride + c]);
      const nt = t.clone();
      nt.times = times;
      nt.values = values;
      tracks.push(nt);
    }
    return new THREE.AnimationClip(name, +(t1 - t0).toFixed(4), tracks);
  }
  const eatClip = sliceClip(take, 'eat', 0.75, 1.5);

  // ---------- walk：程序化真实骨骼 ----------
  const WALK_T = 1.6;
  const n = 24;
  const times = [];
  for (let i = 0; i <= n; i++) times.push((i / n) * WALK_T);
  const e = new THREE.Euler(), q = new THREE.Quaternion();
  function quatTrack(boneName, fn) {
    const vals = [];
    for (const t of times) {
      const [x, y, z] = fn(t);
      e.set(x, y, z); q.setFromEuler(e);
      vals.push(q.x, q.y, q.z, q.w);
    }
    return { node: boneName, path: 'rotation', times: [...times], values: vals };
  }
  function vecTrack(boneName, fn) {
    const vals = [];
    for (const t of times) vals.push(...fn(t));
    return { node: boneName, path: 'translation', times: [...times], values: vals };
  }
  const w = 2 * Math.PI / WALK_T;
  const walkTracks = [
    // 大腿前后摆（交替）
    quatTrack('CHICKEN_-R-Thigh_016', t => [Math.sin(w * t) * 0.45, 0, 0]),
    quatTrack('CHICKEN_-L-Thigh_028', t => [-Math.sin(w * t) * 0.45, 0, 0]),
    // 小腿膝弯
    quatTrack('CHICKEN_-R-Calf_017', t => [Math.max(0, Math.sin(w * t)) * 0.4, 0, 0]),
    quatTrack('CHICKEN_-L-Calf_029', t => [Math.max(0, -Math.sin(w * t)) * 0.4, 0, 0]),
    // 根骨起伏 + 轻微前移
    vecTrack('_rootJoint', t => {
      const y = Math.abs(Math.sin(w * t)) * 0.03;
      const z = Math.sin(w * t * 0.5) * 0.05;
      return [0, y, z];
    }),
    // 头微点
    quatTrack('CHICKEN_-Head_05', t => [Math.sin(w * t + 0.6) * 0.06, 0, 0]),
  ];
  const walkClip = {
    name: 'walk', duration: WALK_T, tracks: walkTracks,
  };
  lines.push(`eat: duration=${eatClip.duration.toFixed(2)} tracks=${eatClip.tracks.length}`);
  lines.push(`walk: duration=${walkClip.duration.toFixed(2)} tracks=${walkClip.tracks.length}`);

  // 输出 JSON
  // three track 名是 name.position/.quaternion/.scale → glTF path 是 translation/rotation/scale
  const PATH_MAP = { position: 'translation', quaternion: 'rotation', scale: 'scale' };
  function trackToJSON(t) {
    const dot = t.name.indexOf('.');
    const node = dot === -1 ? t.name : t.name.slice(0, dot);
    const p = dot === -1 ? 'rotation' : t.name.slice(dot + 1);
    const path = PATH_MAP[p] || 'rotation';
    return { node, path, times: Array.from(t.times), values: Array.from(t.values) };
  }
  const eatJSON = {
    name: 'eat', duration: eatClip.duration,
    tracks: eatClip.tracks.map(trackToJSON),
  };
  writeFileSync(out, JSON.stringify({ clips: [eatJSON, walkClip] }, null, 1));
  lines.push('wrote ' + out);
  console.log(lines.join('\n'));
}, (e) => {
  console.log('ERROR: ' + (e && e.stack ? e.stack.split('\n').slice(0, 6).join(' | ') : String(e)));
});
