// 抓取 preview 页面所有 404 / 资源加载失败的 URL
const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new'
  });
  const page = await browser.newPage();
  const notFound = [];
  page.on('response', r => { if (r.status() === 404) notFound.push(r.url()); });
  page.on('console', m => {
    if (m.type() === 'error') notFound.push('CONSOLE: ' + m.text());
  });
  await page.goto('http://localhost:8898/preview.html', { waitUntil: 'networkidle2', timeout: 60000 });
  await new Promise(r => setTimeout(r, 8000));
  console.log('=== 404 / console error 列表 ===');
  [...new Set(notFound)].forEach(u => console.log(u));
  await browser.close();
})();
