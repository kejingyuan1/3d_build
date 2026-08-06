const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  const fails = [];
  page.on('requestfailed', r => fails.push(r.url()));
  page.on('response', r => { if (r.status() === 404) fails.push('404:' + r.url()); });
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_duck.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 10000));
  const info = await page.evaluate(() => {
    const duck = window.__duck;
    if (!duck) return 'no duck';
    const out = {};
    duck.traverse(o => {
      if (o.isMesh) {
        out[o.name] = {
          hasMap: !!o.material.map,
          mapUrl: o.material.map ? o.material.map.image.src.slice(-60) : null,
          mapLoaded: o.material.map ? o.material.map.image.width + 'x' + o.material.map.image.height : null,
        };
      }
    });
    return out;
  });
  console.log('材质:', JSON.stringify(info, null, 2));
  console.log('失败请求:', fails.slice(0, 5));
  await browser.close();
})();
