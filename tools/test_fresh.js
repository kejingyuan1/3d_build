const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu','--disk-cache-size=0']
  });
  const page = await browser.newPage();
  await page.setCacheEnabled(false);
  await page.setBypassServiceWorker(true);
  await page.setUserAgent('Mozilla/5.0 Fresh');
  await page.goto('http://localhost:8898/demo_map.html?fresh=' + Date.now(), { waitUntil: 'networkidle0', timeout: 30000 });
  await new Promise(r => setTimeout(r, 30000));
  const cameraPos = await page.evaluate(() => {
    if (window.__camera) return { x: window.__camera.position.x, y: window.__camera.position.y, z: window.__camera.position.z };
    return 'no camera';
  });
  console.log('相机位置:', cameraPos);
  const islands = await page.evaluate(() => {
    const list = [];
    if (window.__loadedModels) for (const [k, m] of window.__loadedModels) {
      if (k.includes('island')) list.push({ id: k, pos: m.position.toArray() });
    }
    return list;
  });
  console.log('岛屿数:', islands.length);
  if (islands.length) console.log('前 3:', JSON.stringify(islands.slice(0,3)));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_map_fresh.png' });
  console.log('=== 截图已保存 verify_map_fresh.png ===');
  await browser.close();
})();
