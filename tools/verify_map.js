// 验证海洋地图 demo_map.html
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  await page.setCacheEnabled(false);
  const pageErrors = [];
  const failed = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  page.on('requestfailed', r => failed.push(r.url().split('/').pop()));
  page.on('console', m => { if (m.type() === 'error' && !m.text().includes('404')) console.log('ERR:', m.text().slice(0,100)); });
  await page.goto('http://localhost:8898/demo_map.html?nocache=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 25000)); // ×20 资源多，等久点

  const status = await page.evaluate(() => document.getElementById('status').textContent);
  console.log('状态栏:', status);
  console.log('页面错误:', pageErrors.length ? pageErrors.slice(0,3) : '0 条');
  console.log('失败请求:', failed.length ? failed.slice(0,5) : '0 个');

  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_map.png' });
  console.log('=== 截图已保存 verify_map.png ===');
  await browser.close();
})();
