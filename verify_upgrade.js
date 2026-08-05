// 验证升级链建筑：加载 preview.html，把相机移到 x=16 列查看 5 级建筑 + 门交互
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
  page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text() + ' [url:' + (msg.location() && msg.location().url) + ']'); });
  page.on('pageerror', err => pageErrors.push(err.message));
  page.on('requestfailed', req => failedRequests.push(req.url() + ' :: ' + (req.failure() && req.failure().errorText)));
  page.on('response', resp => { if (resp.status() === 404) consoleErrors.push('404: ' + resp.url()); });

  console.log('打开页面...');
  await page.goto('http://localhost:8898/preview.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 12000));

  const info = await page.evaluate(() => document.getElementById('info').textContent);
  console.log('=== 状态栏:', info);

  // 升级链建筑是否存在（通过 window.__loadedModels 调试句柄）
  const upLoaded = await page.evaluate(() => {
    const out = {};
    for (const [k, v] of window.__loadedModels) {
      if (k.startsWith('building_upgrade')) {
        // 统计门部件（plank/rail/handle）
        const doorParts = [];
        v.traverse(o => { if (o.isMesh && /plank|rail|handle/.test(o.name)) doorParts.push(o.name); });
        out[k] = { meshes: doorParts.length, sample: doorParts.slice(0, 4) };
      }
    }
    return out;
  });
  console.log('=== 升级链建筑已加载:', JSON.stringify(upLoaded, null, 1));

  // 把相机移到 x=16 列（直接 lookAt 绕过 damping）
  await page.evaluate(() => {
    window.__camera.position.set(16, 6, 4);
    window.__camera.lookAt(16, 1.5, -10);
    window.__controls.target.set(16, 1.5, -10);
    window.__controls.enableDamping = false;
    window.__controls.update();
    window.__camera.updateProjectionMatrix();
  });
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_upgrade_l1to5.png' });

  // 真实门交互测试结果已打印
  // 再截一张：把第一个升级建筑的门 toggle 开启
  await page.evaluate(() => {
    for (const [key, rec] of window.__doorRegistry) {
      if (key.includes('building_upgrade_l1:')) {
        rec.open = true;
        rec.pivot.rotation.y = (rec.cfg.angle || 110) * (rec.cfg.hinge === 'right' ? -1 : 1);
        break;
      }
    }
  });
  await new Promise(r => setTimeout(r, 600));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_upgrade_door_open.png' });

  console.log('--- 控制台错误:', consoleErrors.length, '条 ---');
  consoleErrors.slice(0, 10).forEach(e => console.log('  ERR:', e));
  console.log('--- 页面错误:', pageErrors.length, '条 ---');
  pageErrors.slice(0, 10).forEach(e => console.log('  PAGEERR:', e));
  console.log('--- 失败请求:', failedRequests.length, '条 ---');
  failedRequests.slice(0, 10).forEach(e => console.log('  REQFAIL:', e));

  await browser.close();
  console.log('=== 验证完成 ===');
})();
