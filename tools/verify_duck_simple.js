const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  page.on('console', m => { if (m.type() === 'error') console.log('CONSOLE-ERR:', m.text().slice(0, 120)); });
  page.on('response', r => { if (r.status() === 404) console.log('404:', r.url().split('/').pop()); });
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_duck.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 15000));
  const matInfo = await page.evaluate(() => {
    const duck = window.__duck;
    if (!duck) return 'no duck';
    const out = [];
    duck.traverse(o => {
      if (o.isMesh) {
        out.push({ name: o.name, hasMap: !!o.material.map, imgLoaded: o.material.map ? o.material.map.image.width + 'x' + o.material.map.image.height : null });
      }
    });
    return out;
  });
  console.log('材质:', JSON.stringify(matInfo, null, 2));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_idle.png' });
  await browser.close();
})();
