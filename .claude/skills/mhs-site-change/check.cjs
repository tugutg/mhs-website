// Browser checks for the built site (_site/ served locally): the three language pages at phone and desktop
// width, language leaks, errors, images, external requests, and the МН/EN/CN address switch.
//
//   node check.cjs --base http://127.0.0.1:8040 [--expect TEXT]... [--expect-en TEXT]... [--expect-zh TEXT]... [--absent TEXT]...
//                  [--shot CSS_SELECTOR --out DIR]
//
// --expect / --expect-en / --expect-zh  text that must be visible on /, /en/ and /zh/ (repeatable)
// --absent                text that must not be visible on any page (repeatable)
//                         (--expect/--absent ignore case, since headings are uppercase by CSS, and include closed FAQ answers)
// --shot                  screenshot that element on every page at 390 and 1440 px into --out (look at them!)
// Needs playwright-core: NODE_PATH=<dir>/node_modules (see SKILL.md, "Tools"). Exit code 1 on any failure.
const {chromium} = require('playwright-core');
const fs = require('fs');

const args = process.argv.slice(2);
const opt = (name) => args.flatMap((a, i) => (a === name ? [args[i + 1]] : []));
const BASE = (opt('--base')[0] || 'http://127.0.0.1:8040').replace(/\/$/, '');
const OUT = opt('--out')[0] || '.';
const chrome = (() => {
  // the pre-installed Chromium: the newest chromium-NNNN folder that holds the binary (its subfolder name
  // changed from chrome-linux to chrome-linux64 in 2026), else the /opt/pw-browsers/chromium link
  try {
    const dirs = fs.readdirSync('/opt/pw-browsers').filter((x) => /^chromium-\d+$/.test(x)).sort().reverse();
    for (const d of dirs) for (const sub of ['chrome-linux64', 'chrome-linux']) {
      const p = `/opt/pw-browsers/${d}/${sub}/chrome`;
      if (fs.existsSync(p)) return p;
    }
    return fs.existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined;
  } catch (e) { return undefined; }
})();

(async () => {
  const launch = {args: ['--no-sandbox']};
  if (chrome) launch.executablePath = chrome;
  // the session's egress proxy only for a remote --base; a local server is reached directly (through the
  // proxy it answers 405 to plain HTTP)
  if (process.env.HTTPS_PROXY && !/^https?:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(BASE)) launch.proxy = {server: process.env.HTTPS_PROXY, bypass: '127.0.0.1,localhost'};
  const b = await chromium.launch(launch);
  let bad = 0;
  const fail = (m) => { bad++; console.log('  FAIL ' + m); };

  const WANT = {'/': 'mn', '/en/': 'en', '/zh/': 'zh'};
  for (const path of Object.keys(WANT)) for (const w of [390, 1440]) {
    const ctx = await b.newContext({viewport: {width: w, height: 900}, deviceScaleFactor: w < 500 ? 3 : 1});
    const p = await ctx.newPage();
    const errs = [], ext = [];
    p.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') errs.push(m.text()); });
    p.on('pageerror', (e) => errs.push(String(e)));
    p.on('requestfailed', (r) => errs.push('failed ' + r.url()));
    p.on('response', (r) => { if (r.status() >= 400) errs.push(r.status() + ' ' + r.url()); });
    p.on('request', (r) => { if (!r.url().startsWith(BASE) && !r.url().startsWith('data:')) ext.push(r.url()); });
    await p.goto(BASE + path, {waitUntil: 'networkidle'});
    for (const h of await p.$$('img')) { await h.scrollIntoViewIfNeeded(); await p.waitForTimeout(80); }
    await p.waitForLoadState('networkidle');
    await p.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; })); // FAQ answers too
    const r = await p.evaluate(() => ({
      lang: document.documentElement.lang,
      title: document.title,
      hscroll: document.documentElement.scrollWidth > document.documentElement.clientWidth,
      broken: [...document.images].filter((i) => !(i.complete && i.naturalWidth > 0)).map((i) => i.getAttribute('src')),
      labels: [...document.querySelectorAll('[aria-label]')].map((e) => e.getAttribute('aria-label')),
      alts: [...document.images].map((i) => i.alt),
      switches: [...document.querySelectorAll('[data-set-lang]')].map((e) => e.getAttribute('data-href')),
      text: document.body.innerText,
    }));
    const want = WANT[path];
    console.log(`${path} @${w}px  lang=${r.lang}  "${r.title}"`);
    if (r.lang !== want) fail(`lang is ${r.lang}, expected ${want}`);
    if (r.hscroll) fail('horizontal scroll');
    if (r.broken.length) fail('images not loaded: ' + r.broken.join(', '));
    if (errs.length) fail('console/network errors: ' + errs.slice(0, 5).join(' | '));
    if (ext.length) fail('requests to other sites: ' + ext.slice(0, 5).join(', '));
    if (r.switches.length !== 3) fail('expected 3 language switches, found ' + r.switches.length);
    if (r.switches.some((h) => !h)) fail('language switch without data-href (is this the built _site, not docs/?)');
    if (want !== 'mn') {
      const cyr = (r.text.match(/[А-Яа-яЁёӨөҮү]+/g) || []).filter((x) => x !== 'МН');
      if (cyr.length) fail(`Mongolian visible on ${path}: ` + [...new Set(cyr)].slice(0, 8).join(' '));
      if ([...r.labels, ...r.alts].some((t) => /[А-Яа-яӨөҮү]/.test(t))) fail(`Mongolian alt/aria text on ${path}`);
    }
    if (want !== 'zh') {
      const cjk = (r.text.match(/[\u4e00-\u9fff]+/g) || []).filter((x) => x !== '中文');
      if (cjk.length) fail(`Chinese visible on ${path}: ` + [...new Set(cjk)].slice(0, 8).join(' '));
      if ([...r.labels, ...r.alts].some((t) => /[\u4e00-\u9fff]/.test(t))) fail(`Chinese alt/aria text on ${path}`);
    }
    if (want !== 'en') {
      const en = r.text.match(/\b(the|and|with|for|our|system|machine)\b/gi) || [];
      if (en.length) fail(`English visible on ${path}: ` + [...new Set(en)].slice(0, 8).join(' '));
    }
    const has = (t) => r.text.toLowerCase().includes(t.toLowerCase()); // innerText is UPPERCASE where CSS says so
    for (const t of opt({mn: '--expect', en: '--expect-en', zh: '--expect-zh'}[want])) if (!has(t)) fail(`missing text: ${t}`);
    for (const t of opt('--absent')) if (has(t)) fail(`text still visible: ${t}`);
    for (const sel of opt('--shot')) {
      await p.addStyleTag({content: '.mbar{display:none!important}.top{position:static!important}'});
      const el = p.locator(sel).first();
      if (await el.count()) {
        const file = `${OUT}/shot-${want}-${w}-${sel.replace(/[^a-z0-9]+/gi, '_')}.png`;
        await el.screenshot({path: file});
        console.log('  screenshot ' + file);
      } else fail(`--shot selector not found: ${sel}`);
    }
    await ctx.close();
  }

  // Language addresses: old links, a saved choice, and Back after switching
  const go = async (desc, setup, url, expect) => {
    const ctx = await b.newContext(); const p = await ctx.newPage();
    if (setup) { await p.goto(BASE + '/robots.txt'); await p.evaluate(setup); }
    await p.goto(BASE + url); await p.waitForLoadState('networkidle'); await p.waitForTimeout(300);
    const got = p.url().replace(BASE, '');
    if (got !== expect) fail(`${desc}: ${url} -> ${got}, expected ${expect}`);
    await ctx.close();
  };
  await go('?lang=en', null, '/?lang=en', '/en/');
  await go('#en', null, '/#en', '/en/');
  await go('?lang=mn on /en/', null, '/en/?lang=mn', '/');
  await go('?lang=zh', null, '/?lang=zh', '/zh/');
  await go('#zh', null, '/#zh', '/zh/');
  await go('?lang=mn on /zh/', null, '/zh/?lang=mn', '/');
  await go('?lang=zh on /en/', null, '/en/?lang=zh', '/zh/');
  await go('?lang=en on /zh/', null, '/zh/?lang=en', '/en/');
  await go('saved English', () => localStorage.setItem('mhs-lang', 'en'), '/', '/en/');
  await go('saved Chinese', () => localStorage.setItem('mhs-lang', 'zh'), '/', '/zh/');
  await go('no saved choice', null, '/', '/');
  {
    const ctx = await b.newContext(); const p = await ctx.newPage();
    await p.goto('about:blank'); await p.goto(BASE + '/'); await p.click('#lang-en'); await p.waitForURL(BASE + '/en/');
    await p.goBack(); await p.waitForLoadState('networkidle'); await p.waitForTimeout(300);
    if (p.url() !== BASE + '/') fail('Back after tapping EN landed on ' + p.url().replace(BASE, ''));
    await ctx.close();
  }
  await b.close();
  console.log(bad ? `\n${bad} problem(s)` : '\nall checks passed');
  process.exit(bad ? 1 : 0);
})();
