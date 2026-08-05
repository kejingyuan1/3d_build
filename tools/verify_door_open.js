// 开门验证：把相机对准升级建筑并打开所有门
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-gpu']
  });
  const page = await browser.newPage();
  page.on('console', m => { if (m.type() === 'error') console.log('ERR:', m.text()); });
  await page.goto('http://localhost:8898/preview.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 12000));

  // 相机对准升级建筑（x=16 列）
  await page.evaluate(() => {
    if (window.__camera && window.__controls) {
      window.__controls.target.set(14, 2, -10);
      window.__camera.position.set(6, 5, 3);
      window.__controls.update();
    }
  });
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_doors_closed.png' });
  console.log('=== 关门截图已保存 ===');

  // 列出门 registry
  const doors = await page.evaluate(() => {
    return Array.from(window.__doorRegistry.entries()).map(([k, v]) => ({key: k, open: v.open, hasPivot: !!v.pivot}));
  });
  console.log('门列表:', doors.length, '扇');

  // 打开所有升级建筑的门
  const after = await page.evaluate(() => {
    const out = {};
    for (const [k, rec] of window.__doorRegistry) {
      if (!k.startsWith('building_upgrade')) continue;
      rec.open = true;
      const angle = rec.cfg.angle || 110;
      const sign = rec.cfg.hinge === 'right' ? -1 : 1;
      rec.pivot.rotation.y = (angle * Math.PI / 180) * sign;
      out[k] = { open: rec.open, ry: rec.pivot.rotation.y.toFixed(2) };
    }
    return out;
  });
  console.log('开门后:', JSON.stringify(after, null, 2));
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_doors_open.png' });
  console.log('=== 开门截图已保存 ===');

  await browser.close();
})();
