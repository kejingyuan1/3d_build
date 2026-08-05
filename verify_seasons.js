// 验证季节/生长阶段资产：加载 preview.html，检查 22 个新资产可加载（不加入 LAYOUT，直接检查 manifest 加载）
const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-gpu', '--disable-application-cache']
  });
  const page = await browser.newPage();
  await page.setCacheEnabled(false);
  await page.setViewport({ width: 1600, height: 900 });
  const consoleErrors = [], pageErrors = [], failedRequests = [];
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', err => pageErrors.push(err.message));
  page.on('requestfailed', req => failedRequests.push(req.url() + ' :: ' + (req.failure() && req.failure().errorText)));
  page.on('response', resp => { if (resp.status() === 404) consoleErrors.push('404: ' + resp.url()); });

  console.log('打开页面...');
  await page.goto('http://localhost:8898/preview.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 15000));

  const info = await page.evaluate(() => document.getElementById('info').textContent);
  console.log('=== 状态栏:', info);

  // 内嵌 manifest 是否含 22 个新资产（存在即通过；LAYOUT 未放它们，所以不要求渲染）
  const manifestCheck = await page.evaluate(() => {
    const MANIFEST = JSON.parse(document.getElementById('manifest-data').textContent);
    const ids = new Set(MANIFEST.assets.map(a => a.assetId));
    const newIds = [
      'plant_tomato_seed','plant_tomato_seedling','plant_tomato_mature',
      'plant_pumpkin_seed','plant_pumpkin_seedling','plant_pumpkin_mature',
      'plant_tree_oak_spring','plant_tree_oak_summer','plant_tree_oak_autumn','plant_tree_oak_winter',
      'plant_tree_apple_spring','plant_tree_apple_summer','plant_tree_apple_autumn','plant_tree_apple_winter',
      'terrain_grass_spring','terrain_grass_summer','terrain_grass_autumn','terrain_grass_winter',
      'plant_tilled_soil_spring','plant_tilled_soil_summer','plant_tilled_soil_autumn','plant_tilled_soil_winter'
    ];
    const present = newIds.filter(id => ids.has(id));
    const missing = newIds.filter(id => !ids.has(id));
    return { total: MANIFEST.assets.length, present, missing };
  });
  console.log('=== manifest 新资产:', JSON.stringify(manifestCheck));

  // 手动加载一个季节资产验证 GLB 可被 GLTFLoader 解析（临时 fetch 检查路径）
  const fetchCheck = await page.evaluate(async () => {
    const MANIFEST = JSON.parse(document.getElementById('manifest-data').textContent);
    const sample = ['plant_tree_oak_spring', 'terrain_grass_winter', 'plant_tilled_soil_autumn', 'plant_tomato_mature'];
    const out = {};
    for (const id of sample) {
      const entry = MANIFEST.assets.find(a => a.assetId === id);
      if (!entry) { out[id] = 'no-entry'; continue; }
      try {
        const resp = await fetch('./' + entry.path);
        out[id] = resp.ok ? `OK ${resp.status}` : `HTTP ${resp.status}`;
      } catch (e) { out[id] = 'FETCH-ERR ' + e.message; }
    }
    return out;
  });
  console.log('=== 样本 GLB 可访问性:', JSON.stringify(fetchCheck));

  console.log('--- 控制台错误:', consoleErrors.length, '条 ---');
  consoleErrors.slice(0, 10).forEach(e => console.log('  ERR:', e));
  console.log('--- 页面错误:', pageErrors.length, '条 ---');
  pageErrors.slice(0, 10).forEach(e => console.log('  PAGEERR:', e));
  console.log('--- 失败请求:', failedRequests.length, '条 ---');
  failedRequests.slice(0, 10).forEach(e => console.log('  REQFAIL:', e));

  await browser.close();
  console.log('=== 验证完成 ===');
})();
