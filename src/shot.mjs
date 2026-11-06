// playwright may be a local dependency or a global install; try both, and let
// PLAYWRIGHT_PATH override. Dev utility only, not part of the analysis pipeline.
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const candidates = [
  process.env.PLAYWRIGHT_PATH,
  'playwright',
  '/opt/npm-tools/node_modules/playwright',
].filter(Boolean);
let pkg = null, tried = [];
for (const c of candidates) {
  try { pkg = require(c); break; } catch (e) { tried.push(c); }
}
if (!pkg) {
  console.error('could not resolve playwright. tried: ' + tried.join(', '));
  console.error('install it (npm i playwright) or set PLAYWRIGHT_PATH to its folder.');
  process.exit(1);
}
const { chromium } = pkg;

const url = 'file://' + new URL('../cruise_dashboard.html', import.meta.url).pathname;
const browser = await chromium.launch();
const shots = [
  { name: 'desk', w: 1280, h: 1100, scheme: 'light' },
  { name: 'dark', w: 1280, h: 1100, scheme: 'dark' },
  { name: 'phone', w: 390, h: 844, scheme: 'light' },
];
let bad = 0;
for (const s of shots) {
  const ctx = await browser.newContext({
    viewport: { width: s.w, height: s.h }, colorScheme: s.scheme,
    deviceScaleFactor: 2,
  });
  const page = await ctx.newPage();
  const errs = [];
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  await page.goto(url, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);

  const over = await page.evaluate(() =>
    document.documentElement.scrollWidth - document.documentElement.clientWidth);
  const empty = await page.evaluate(() =>
    [...document.querySelectorAll('svg.chart')].map(s => ({ id: s.id, kids: s.childElementCount })));
  console.log(`[${s.name} ${s.w}x${s.h} ${s.scheme}] h-overflow=${over}px  console-errors=${errs.length}`);
  empty.forEach(e => { if (e.kids < 3) { console.log('   EMPTY CHART:', e.id); bad++; } });
  if (over > 0) bad++;
  errs.slice(0, 5).forEach(e => console.log('   ', e.slice(0, 160)));
  if (errs.length) bad++;

  await page.screenshot({ path: `shot-${s.name}.png`, fullPage: s.name === 'phone' ? false : false });
  // also a tall capture of the charts area
  if (s.name === 'desk') {
    await page.screenshot({ path: 'shot-full.png', fullPage: true });
  }
  await ctx.close();
}
await browser.close();
console.log(bad === 0 ? 'OK: no overflow, no console errors, all charts drew' : `ISSUES: ${bad}`);
