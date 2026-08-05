// 拉远镜头看完整 11 个生命周期模型（z=10 行 x=-8..8 排开）
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  await page.goto('http://localhost:8898/preview.html', {waitUntil:'domcontentloaded', timeout:30000});
  await new Promise(r => setTimeout(r, 12000));
  // 相机拉远，俯视 z=10 行全景
  await page.evaluate(() => {
    if (window.__camera && window.__controls) {
      window.__controls.target.set(0, 0.3, 10);
      window.__camera.position.set(0, 4, -2);
      window.__controls.update();
    }
  });
  await new Promise(r => setTimeout(r, 1500));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_lifecycle_row.png' });
  console.log('全景截图已保存');
  await browser.close();
})();
