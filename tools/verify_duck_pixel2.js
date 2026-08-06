const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  page.on('console', m => console.log('LOG:', m.text()));
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_duck.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 10000));
  // 注入全局引用 + 检查
  const info = await page.evaluate(() => {
    // 在模块作用域外拿不到 duck，但我们可以扫描 scene 的 mesh 数量
    // 直接检查 canvas 渲染的像素分布
    const cv = document.querySelector('canvas');
    const gl = cv.getContext('webgl2') || cv.getContext('webgl');
    // 采样 3x3 网格中心
    const out = [];
    for (const [fx, fy] of [[0.5, 0.5], [0.5, 0.3], [0.3, 0.5], [0.7, 0.5], [0.5, 0.7]]) {
      const px = new Uint8Array(4);
      gl.readPixels(Math.floor(cv.width*fx), Math.floor(cv.height*fy), 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
      out.push(`(${fx},${fy})=[${px.join(',')}]`);
    }
    return out;
  });
  console.log('像素采样:', info.join(' '));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_idle.png' });
  console.log('=== 截图保存 ===');
  await browser.close();
})();
