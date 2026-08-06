// 拉近看一棵树，验证树干+树冠衔接
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_map.html?fresh=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 15000));
  // 相机拉近到主岛看树
  await page.evaluate(() => {
    if (window.__camera && window.__controls) {
      window.__controls.target.set(0, 5, 0);
      window.__camera.position.set(20, 15, 20);
      window.__controls.update();
    }
  });
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_tree_close.png' });
  console.log('=== 树近景截图 ===');
  await browser.close();
})();