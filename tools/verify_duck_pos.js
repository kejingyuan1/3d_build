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
    const duck = window.__duck;
    const scene = window.__scene;
    const camera = window.__camera;
    if (!duck || !scene || !camera) return 'no debug handles';
    const THREE = window.__THREE;
    // 鸭子世界位置
    duck.updateWorldMatrix(true, true);
    const box = new THREE.Box3().setFromObject(duck);
    const center = new THREE.Vector3(); box.getCenter(center);
    // 相机
    const camPos = camera.position.clone();
    // 相机是否看着鸭子
    const camDir = new THREE.Vector3(); camera.getWorldDirection(camDir);
    return {
      duckBox: { min: box.min.toArray(), max: box.max.toArray(), center: center.toArray() },
      cameraPos: camPos.toArray(),
      camDir: camDir.toArray(),
      meshCount: scene.children.filter(c => c.isMesh).length,
      duckVisible: duck.visible,
      duckChildren: duck.children.map(c => c.name + (c.isMesh ? ':' + (c.material && c.material.vertexColors ? 'vc' : 'mat') : '') ),
    };
  });
  console.log(JSON.stringify(info, null, 2));
  await page.screenshot({ path: 'C:\\Users\\WIN11\\WorkBuddy\\2026-08-05-11-48-42\\verify_duck_idle.png' });
  await browser.close();
})();
