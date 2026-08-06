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
  await page.goto('http://localhost:8898/demo_duck.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 10000));
  const info = await page.evaluate(() => {
    const status = document.getElementById('status').textContent;
    // 尝试从全局拿 scene
    let result = { status };
    // 检查 canvas 实际渲染
    const cv = document.querySelector('canvas');
    if (cv) {
      const gl = cv.getContext('webgl2') || cv.getContext('webgl');
      const pixels = new Uint8Array(4);
      gl.readPixels(cv.width/2, cv.height/2, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      result.centerPixel = Array.from(pixels);
    }
    return result;
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})();
