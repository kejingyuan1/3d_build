const puppeteer = require('puppeteer-core');
(async () => {
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: 'new', args: ['--no-sandbox','--disable-gpu']
  });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('PAGEERR:', e.message));
  await page.setCacheEnabled(false);
  await page.goto('http://localhost:8898/demo_duck.html?t=' + Date.now(), { waitUntil: 'domcontentloaded', timeout: 30000 });
  await new Promise(r => setTimeout(r, 8000));
  const info = await page.evaluate(() => {
    const duck = window.__duck;
    if (!duck) return 'no duck';
    const out = {};
    duck.traverse(o => {
      if (o.isMesh && o.name === 'body') {
        const mat = o.material;
        out.bodyMat = {
          type: mat.type,
          vertexColors: mat.vertexColors,
          color: mat.color ? mat.color.getHexString() : null,
          hasGradient: !!mat.gradientMap,
          gradSize: mat.gradientMap ? mat.gradientMap.image.width + 'x' + mat.gradientMap.image.height : null,
          gradData: mat.gradientMap ? Array.from(mat.gradientMap.image.data.slice(0, 16)) : null,
        };
        out.bodyGeo = {
          posCount: o.geometry.attributes.position.count,
          hasColor: !!o.geometry.attributes.color,
          colorCount: o.geometry.attributes.color ? o.geometry.attributes.color.count : 0,
        };
      }
    });
    return out;
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})();
