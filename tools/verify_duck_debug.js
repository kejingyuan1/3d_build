const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  page.on('console', m => { if (m.type() === 'log') console.log('LOG:', m.text()); });
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_duck.html?fresh=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 10000));
  const info = await page.evaluate(() => {
    const status = document.getElementById('status').textContent;
    let sceneInfo = 'no scene';
    if (window.__duckDebug) {
      sceneInfo = window.__duckDebug;
    }
    return { status, sceneInfo };
  });
  console.log('Info:', JSON.stringify(info));
  // 检查 window 是否有 duck mesh
  const has = await page.evaluate(() => {
    // Three.js scene 默认在 window.__scene 没暴露，看 renderer 渲染结果
    const cv = document.querySelector('canvas');
    return { canvas: cv ? cv.width + 'x' + cv.height : 'none' };
  });
  console.log('Canvas:', has);
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_idle.png' });
  await browser.close();
})();