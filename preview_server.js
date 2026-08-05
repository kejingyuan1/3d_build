const http = require('http');
const fs = require('fs');
const path = require('path');
const root = process.cwd();
const MIME = {'.html':'text/html','.js':'text/javascript','.json':'application/json','.glb':'model/gltf-binary','.png':'image/png','.css':'text/css'};
http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p === '/') p = '/preview.html';
  const fp = path.join(root, p);
  fs.readFile(fp, (err, data) => {
    if (err) { res.writeHead(404); res.end('404'); return; }
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(fp)]||'application/octet-stream',
      // 关闭所有缓存，确保每次都拿最新版本
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    });
    res.end(data);
  });
}).listen(8898, () => console.log('preview server (no-cache): http://localhost:8898'));