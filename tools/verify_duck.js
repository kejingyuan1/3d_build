// 验证分离式鸭子动画：加载 + 切换走路/低头模式截图
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  page.on('console', m => { if (m.type()==='error' && !m.text().includes('404')) errs.push(m.text().slice(0,100)); });
  await page.goto('http://localhost:8898/demo_duck.html', { waitUntil:'domcontentloaded', timeout:30000 });
  await new Promise(r => setTimeout(r, 8000));

  const status = await page.evaluate(() => document.getElementById('status').textContent);
  console.log('状态:', status);

  // 待机
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_idle.png' });
  console.log('=== 待机截图 ===');

  // 走路模式（等 0.5s 让脚摆起来）
  await page.evaluate(() => document.getElementById('btnWalk').click());
  await new Promise(r => setTimeout(r, 800));
  const walkRot = await page.evaluate(() => {
    const scene = window.__duckDebug || null;
    return 'walk clicked';
  });
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_walk.png' });
  console.log('=== 走路截图 ===');

  // 低头吃食
  await page.evaluate(() => document.getElementById('btnEat').click());
  await new Promise(r => setTimeout(r, 800));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_eat.png' });
  console.log('=== 低头吃食截图 ===');

  console.log('页面错误:', errs.length ? errs.slice(0,3) : '0 条');
  await browser.close();
})();
