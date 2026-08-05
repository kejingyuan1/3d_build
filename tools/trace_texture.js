// 抓取 Three.js 内部状态：纹理是否加载、材质是否引用纹理
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-gpu']
  });
  const page = await browser.newPage();
  await page.setCacheEnabled(false);
  page.on('console', m => console.log('CONSOLE:', m.type(), m.text()));
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  await page.goto('http://localhost:8898/preview.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 15000));

  // 抓取第一个 Quaternius 建筑
  const stats = await page.evaluate(() => {
    const lm = window.__loadedModels;
    const out = { loaded: lm ? Array.from(lm.keys()) : null };
    if (lm) {
      const qb = Array.from(lm.entries()).find(([k]) => k.includes('quaternius'));
      if (qb) {
        const [k, model] = qb;
        out.first_qb = k;
        const meshes = [];
        model.traverse(o => {
          if (o.isMesh) {
            const mat = o.material;
            let tex = null;
            if (mat) {
              if (mat.map) tex = mat.map;
              else if (mat.pbrMetallicRoughness && mat.pbrMetallicRoughness.baseColorTexture) {
                tex = mat.pbrMetallicRoughness.baseColorTexture;
              }
            }
            meshes.push({
              name: o.name,
              matName: mat ? mat.name : null,
              matType: mat ? mat.type : null,
              hasTex: !!tex,
              texImage: tex && tex.image ? `image ${tex.image.width}x${tex.image.height}` : null,
              texSource: tex ? (tex.source ? 'glTF.textures[0]' : tex.image ? 'inline' : 'unknown') : null,
            });
          }
        });
        out.meshes = meshes.slice(0, 3);
      }
    }
    return out;
  });
  console.log('=== loaded models ===');
  console.log(JSON.stringify(stats, null, 2));
  await browser.close();
})();
