const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_duck.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 60000 });
  await new Promise(r => setTimeout(r, 18000));
  // 点击低头按钮
  await page.click('#btnEat');
  // 连续截 4 帧（0.2s / 1s / 2.5s / 4s 后）验证 pivot 平滑前倾
  const shots = [300, 1200, 2800, 5000];
  for (const [i, ms] of shots.entries()) {
    await new Promise(r => setTimeout(r, ms));
    const pivotX = await page.evaluate(() => window.__pivotRotX ? window.__pivotRotX : 'na');
    await page.screenshot({ path: `C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_eat${i}.png` });
    console.log(`帧${i} (${ms}ms): pivot.rotation.x=${pivotX}`);
  }
  await browser.close();
})();
