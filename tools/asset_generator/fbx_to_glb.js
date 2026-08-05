// FBX → 带动画 GLB 转换器（Node + three FBXLoader/GLTFExporter）
// 用法: node tools/asset_generator/fbx_to_glb.js <输入.fbx> <输出.glb>
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const THREE = require('three');
const { FBXLoader } = require('three/examples/jsm/loaders/FBXLoader.js');
const { GLTFExporter } = require('three/examples/jsm/exporters/GLTFExporter.js');

// Node 没有 FileReader，GLTFExporter 写二进制 GLB 需要它 → 最小 polyfill
class FileReaderPolyfill {
  constructor() {
    this.result = null;
    this._listeners = {};
  }
  addEventListener(type, cb) {
    (this._listeners[type] = this._listeners[type] || []).push(cb);
  }
  _emit(type) {
    const ev = { target: this, type };
    (this._listeners[type] || []).forEach(cb => cb(ev));
    if (this['on' + type]) this['on' + type](ev);
    // GLTFExporter 0.170 用 onloadend
    if (this.onloadend && type === 'load') this.onloadend(ev);
    if (this.onerror && type === 'error') this.onerror(ev);
  }
  _finish(buf) {
    this.result = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
    this._emit('load');
  }
  readAsArrayBuffer(blob) {
    if (blob && typeof blob.arrayBuffer === 'function') {
      blob.arrayBuffer().then(ab => {
        this.result = ab;
        this._emit('load');
      });
    } else {
      const buf = Buffer.isBuffer(blob) ? blob : Buffer.from(blob || []);
      this._finish(buf);
    }
  }
  readAsDataURL(blob) {
    if (blob && typeof blob.arrayBuffer === 'function') {
      blob.arrayBuffer().then(ab => {
        this.result = 'data:application/octet-stream;base64,' + Buffer.from(ab).toString('base64');
        this._emit('load');
      });
    } else {
      const buf = Buffer.isBuffer(blob) ? blob : Buffer.from(blob || []);
      this.result = 'data:application/octet-stream;base64,' + buf.toString('base64');
      this._emit('load');
    }
  }
}
if (typeof globalThis.FileReader === 'undefined') globalThis.FileReader = FileReaderPolyfill;
// FBXLoader 里 createCamera 用了 window.innerWidth/innerHeight
if (typeof globalThis.window === 'undefined') {
  globalThis.window = { innerWidth: 1280, innerHeight: 720 };
}

const inFile = path.resolve(process.argv[2]);
const outFile = process.argv[3];
if (!inFile || !outFile) { console.error('用法: fbx_to_glb.js <in.fbx> <out.glb>'); process.exit(1); }

(async () => {
  const loader = new FBXLoader();
  // Node 无 fetch/file:// 支持 → 直接读文件转 ArrayBuffer 用 parse
  const buf = fs.readFileSync(inFile);
  // Buffer → ArrayBuffer（避免 Buffer 被误判为文本）
  const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
  const object = loader.parse(ab, path.dirname(inFile) + '/');

  // 收集动画（去重：traverse 与 object.animations 可能重复收集同一批）
  const seenClips = new Set();
  const clips = [];
  const pushClips = (arr) => {
    if (!arr) return;
    for (const c of arr) {
      const key = c.name + ':' + (c.tracks ? c.tracks.length : 0);
      if (!seenClips.has(key)) { seenClips.add(key); clips.push(c); }
    }
  };
  object.traverse(o => { if (o.animations && o.animations.length) pushClips(o.animations); });
  pushClips(object.animations);

  // 重命名 clip（去掉 UUID 前缀，可读化）
  clips.forEach((c, i) => { c.name = `${path.basename(inFile, '.fbx')}_anim${i}`; });

  const exporter = new GLTFExporter();
  console.log('开始导出（binary GLB, clips=' + clips.length + '）...');
  const glb = await new Promise((resolve, reject) => {
    exporter.parse(object, glb => { console.log('parse 完成, 大小=' + glb.byteLength); resolve(glb); }, err => { console.error('导出失败:', err); reject(err); }, {
      binary: true,
      animations: clips.length ? clips : undefined,
      onlyVisible: false,
      trs: false,
    });
  });

  fs.writeFileSync(outFile, Buffer.from(glb));
  console.log(`✓ ${inFile}`);
  console.log(`  → ${outFile} (${(fs.statSync(outFile).size/1024).toFixed(1)} KB)`);
  console.log(`  动画 clip: ${clips.length} 个: ${clips.map(c => c.name).join(', ')}`);
})();
