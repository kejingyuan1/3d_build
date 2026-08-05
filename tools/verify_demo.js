// 验证 demo_lifecycle.html 交互演示
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') console.log('ERR:', m.text().slice(0,120)); });
  await page.goto('http://localhost:8898/demo_lifecycle.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 15000)); // 等资产加载

  const status = await page.evaluate(() => document.getElementById('status').textContent);
  console.log('状态栏:', status.slice(0, 80));

  // 点击生命周期按钮
  const clickBtn = async (id) => {
    await page.evaluate(id => document.getElementById(id).click(), id);
    await new Promise(r => setTimeout(r, 600));
    return page.evaluate(id => {
      const btn = document.getElementById(id);
      return { active: btn.classList.contains('active'), disabled: btn.disabled };
    }, id);
  };

  console.log('=== 生命周期切换 ===');
  for (const [label, id] of [['蛋','btnEgg'],['幼年','btnBaby'],['成年','btnAdult']]) {
    const r = await clickBtn(id);
    console.log(`  ${label}: active=${r.active} disabled=${r.disabled}`);
  }
  console.log('=== 建筑升级切换 ===');
  for (const [label, id] of [['L1','btnL1'],['L3','btnL3'],['L5','btnL5']]) {
    const r = await clickBtn(id);
    console.log(`  ${label}: active=${r.active} disabled=${r.disabled}`);
  }
  console.log('=== 季节切换（tree 缺失时 graceful skip）===');
  for (const [label, id] of [['春','btnSpring'],['秋','btnAutumn'],['冬','btnWinter']]) {
    const r = await clickBtn(id);
    console.log(`  ${label}: active=${r.active} disabled=${r.disabled}`);
  }
  console.log('页面错误:', pageErrors.length ? pageErrors.slice(0,3) : '0 条');

  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_demo.png' });
  console.log('=== 截图已保存 verify_demo.png ===');
  await browser.close();
})();
