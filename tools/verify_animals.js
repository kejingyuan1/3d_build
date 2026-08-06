const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  page.on('console', m => console.log('LOG:', m.text()));
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_animals.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 60000 });
  await new Promise(r => setTimeout(r, 15000));
  const animals = ['hy3_cat.glb','hy3_dog.glb','hy3_sheep.glb','hy3_chicken.glb','hy3_pig.glb','hy3_cow.glb'];
  const results = [];
  for (const a of animals) {
    await page.select('#selAnimal', a);
    await new Promise(r => setTimeout(r, 8000));
    const st = await page.evaluate(() => document.getElementById('status').textContent);
    results.push(a + ' -> ' + st.slice(0, 40));
    console.log(results[results.length - 1]);
  }
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_idle.png' });
  console.log('截图完成');
  await browser.close();
})();
