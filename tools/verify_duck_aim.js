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
  await page.goto('http://localhost:8898/demo_duck.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 8000));
  const info = await page.evaluate(() => {
    const duck = window.__duck, camera = window.__camera, controls = window.__controls;
    if (!duck || !camera) return 'no handles';
    const THREE = window.__THREE;
    // 相机对准鸭子中心
    const box = new THREE.Box3().setFromObject(duck);
    const center = new THREE.Vector3(); box.getCenter(center);
    controls.target.copy(center);
    camera.position.set(center.x + 2.2, center.y + 1.2, center.z + 2.2);
    controls.update();
    // 读取鸭子第一个 mesh 的材质信息
    let matInfo = [];
    duck.traverse(o => {
      if (o.isMesh) {
        matInfo.push({
          name: o.name,
          hasVC: o.material && o.material.vertexColors,
          color: o.material && o.material.color ? '#' + o.material.color.getHexString() : null,
          visible: o.visible
        });
      }
    });
    return { center: center.toArray(), materials: matInfo };
  });
  console.log(JSON.stringify(info, null, 2));
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_idle.png' });
  await browser.close();
})();
