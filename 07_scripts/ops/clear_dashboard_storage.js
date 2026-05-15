const { chromium } = require('playwright');

const URL = process.env.TARGET_URL || 'http://host.docker.internal:18789/';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(URL, { waitUntil: 'networkidle' });
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await context.clearCookies();
  await page.reload({ waitUntil: 'networkidle' });
  console.log('Storage cleared and page reloaded:', page.url());
  await browser.close();
})();
