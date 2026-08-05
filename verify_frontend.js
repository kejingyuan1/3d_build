// 前端验证脚本：用 puppeteer-core 连接系统 Edge 验证 preview.html
const puppeteer = require('puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: 'new',
    args: [
      '--no-sandbox', '--disable-gpu',
      '--disable-application-cache',
    ]
  });

  const page = await browser.newPage();
  await page.setCacheEnabled(false);  // 关键：禁用 fetch 缓存
  await page.setViewport({ width: 1600, height: 900 });

  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];

  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => pageErrors.push(err.message));
  page.on('requestfailed', req => failedRequests.push(req.url() + ' :: ' + (req.failure() && req.failure().errorText)));

  console.log('打开页面...');
  await page.goto('http://localhost:8898/preview.html', { waitUntil: 'domcontentloaded', timeout: 30000 });

  // 等待资产加载
  await new Promise(r => setTimeout(r, 12000));

  const info = await page.evaluate(() => document.getElementById('info').textContent);
  const stats = await page.evaluate(() => document.getElementById('stats').textContent);
  const hint = await page.evaluate(() => document.getElementById('hint').textContent);

  console.log('=== 验证结果 ===');
  console.log('状态栏:', info);
  console.log('统计栏:', stats);
  console.log('提示:', hint);

  // 截图
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_preview.png' });

  console.log('--- 控制台错误:', consoleErrors.length, '条 ---');
  consoleErrors.slice(0, 10).forEach(e => console.log('  ERR:', e));
  console.log('--- 页面错误:', pageErrors.length, '条 ---');
  pageErrors.slice(0, 10).forEach(e => console.log('  PAGEERR:', e));
  console.log('--- 失败请求:', failedRequests.length, '条 ---');
  failedRequests.slice(0, 10).forEach(e => console.log('  REQFAIL:', e));

  await browser.close();
  console.log('=== 验证完成 ===');
})();
