const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  page.on('console', m => { if (m.type() === 'log') console.log('LOG:', m.text()); });
  page.on('response', r => { if (r.status() === 404) console.log('404:', r.url().split('/').pop()); });
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_island.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 60000 });
  await new Promise(r => setTimeout(r, 20000));
  const status = await page.evaluate(() => document.getElementById('status').textContent);
  console.log('STATUS:', status);
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_island.png' });
  console.log('截图完成');
  await browser.close();
})();
