const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  page.on('console', m => console.log('PAGE:', m.text()));
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_skel.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 60000 });
  await new Promise(r => setTimeout(r, 18000));
  // 截图0
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_skel_t0.png' });
  // 点走路
  await page.click('#btnWalk');
  await new Promise(r => setTimeout(r, 500));
  const dbg1 = await page.evaluate(() => {
    const m = window.__mixer, d = window.__duck;
    const sm = []; d.traverse(o => { if (o.isSkinnedMesh) sm.push({n:o.name, bones: o.skeleton?.bones?.length, boneNames: o.skeleton?.bones?.map(b=>b.name)}); });
    return { mixerTime: m.time, skinnedMeshes: sm, kids: d.children.map(c => ({n:c.name,t:c.type,sk:c.isSkinnedMesh})) };
  });
  console.log('walk后:', JSON.stringify(dbg1));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_skel_t1.png' });
  await new Promise(r => setTimeout(r, 800));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_skel_t2.png' });
  await browser.close();
})();
