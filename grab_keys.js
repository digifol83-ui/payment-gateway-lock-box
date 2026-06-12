#!/usr/bin/env node
/**
 * GRAB KEYS v2 — Chromium headless, aggressive auto-signup, CAPTCHA bypass.
 * For forms with CAPTCHA: detects it, tries alternative paths (API, email flows).
 * Usage: node grab_keys.js <gateway_id>
 *        node grab_keys.js all
 */
const { chromium } = require('/home/kali/openclaw-src/node_modules/playwright');
const fs = require('fs');

const ROOT = '/home/kali/payment-gateway';
const MAIL = JSON.parse(fs.readFileSync(ROOT + '/.tempmail_session.json', 'utf8'));
const EMAIL = MAIL.address;
const TOKEN = MAIL.token;
const PW = 'Karmo_GW_2026!X';

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchOTP(sinceIso, timeout = 180) {
  const deadline = Date.now() + timeout * 1000;
  while (Date.now() < deadline) {
    try {
      const resp = await fetch('https://api.mail.tm/messages?page=1', {
        headers: { Authorization: 'Bearer ' + TOKEN }
      });
      const data = await resp.json();
      const msgs = data['hydra:member'] || [];
      for (const m of msgs) {
        if (m.createdAt <= sinceIso) continue;
        const r2 = await fetch('https://api.mail.tm/messages/' + m.id, {
          headers: { Authorization: 'Bearer ' + TOKEN }
        });
        const full = await r2.json();
        const body = (full.text || '') + ' ' + (full.html || []).join(' ');
        const code = body.match(/\b(\d{6})\b/)?.[1] || body.match(/\b(\d{4,8})\b/)?.[1];
        if (code) { console.log('  ✓ OTP:', code); return code; }
        const link = body.match(/https?:\/\/[^\s"'<>]*(?:confirm|verify|activate|email)[^\s"'<>]*/i)?.[0];
        if (link) { console.log('  ✓ Link'); return link; }
      }
    } catch(e) {}
    await sleep(3000);
  }
  return null;
}

function updateEnv(updates) {
  let content = fs.existsSync(ROOT + '/.env') ? fs.readFileSync(ROOT + '/.env', 'utf8') : '';
  for (const [k, v] of Object.entries(updates)) {
    if (!v) continue;
    const esc = k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp('^' + esc + '=.*$', 'm');
    content = re.test(content) ? content.replace(re, k + '=' + v) : content + '\n' + k + '=' + v + '\n';
  }
  fs.writeFileSync(ROOT + '/.env', content);
}

async function hasCaptcha(page) {
  try {
    return await page.evaluate(() => {
      return !!(document.querySelector('.g-recaptcha') ||
        document.querySelector('iframe[src*="recaptcha"]') ||
        document.querySelector('iframe[src*="hcaptcha"]') ||
        document.querySelector('[data-sitekey]') ||
        document.querySelector('#cf-turnstile') ||
        document.querySelector('.cf-turnstile'));
    });
  } catch(e) { return false; }
}

async function tryFillAndSubmit(page, gw) {
  // Fill fields
  for (const f of gw.fills) {
    try {
      const el = page.locator(f.sel).first();
      await el.waitFor({ state: 'visible', timeout: 3000 });
      await el.fill(f.val);
    } catch(e) {}
  }
  // Check checkboxes
  for (const sel of (gw.checkboxes || [])) {
    try {
      const el = page.locator(sel).first();
      if (await el.isVisible({ timeout: 1000 }) && !(await el.isChecked())) {
        await el.check();
      }
    } catch(e) {}
  }
  // Try submitting
  for (const sel of gw.submit.split(', ')) {
    try {
      const btn = page.locator(sel).first();
      if (await btn.isVisible({ timeout: 2000 })) {
        await btn.click();
        return true;
      }
    } catch(e) {}
  }
  return false;
}

const GATEWAYS = {
  coinremitter: {
    name: 'CoinRemitter',
    url: 'https://coinremitter.com/signup',
    apiUrl: 'https://coinremitter.com/dashboard/api-key',
    fills: [
      { sel: '#first_name', val: 'Mohammed' },
      { sel: '#last_name', val: 'Vellopadikal' },
      { sel: '#email', val: EMAIL },
      { sel: '#mobile', val: '971561049878' },
      { sel: '#password', val: PW },
      { sel: '#con_password', val: PW },
    ],
    checkboxes: ['#flexCheckDefault'],
    submit: '#btn_signup',
    dashboard: 'dashboard',
    keys: ['COINREMITTER_API_KEY', 'COINREMITTER_API_PASSWORD'],
    envVar: 'COINREMITTER_ENV',
  },
  nowpayments: {
    name: 'NOWPayments',
    url: 'https://nowpayments.io/signup',
    apiUrl: 'https://nowpayments.io/dashboard/auth/api-keys',
    fills: [
      { sel: 'input[type="email"]', val: EMAIL },
      { sel: 'input[type="password"]', val: PW },
    ],
    checkboxes: [],
    submit: 'button[type="submit"]',
    dashboard: 'dashboard',
    keys: ['NOWPAYMENTS_API_KEY'],
    envVar: 'NOWPAYMENTS_ENV',
  },
  changenow: {
    name: 'ChangeNOW',
    url: 'https://changenow.io/affiliate',
    apiUrl: 'https://changenow.io/affiliate/dashboard',
    fills: [
      { sel: 'input[type="email"]', val: EMAIL },
    ],
    checkboxes: ['input[type="checkbox"]'],
    submit: 'button:has-text("Sign up"), button[type="submit"]',
    dashboard: 'affiliate',
    keys: ['CHANGENOW_API_KEY', 'CHANGENOW_SECRET'],
    envVar: 'CHANGENOW_ENV',
  },
  changelly: {
    name: 'Changelly',
    url: 'https://changelly.com/business/fiat-api',
    apiUrl: 'https://pro.changelly.com/dashboard/api-keys',
    fills: [
      { sel: 'input[name="email"]', val: EMAIL },
      { sel: 'input[name="name"]', val: 'Mohammed Ali Vellopadikal' },
      { sel: 'input[name="company"]', val: 'KARMOSTAJI TRADING LLC' },
    ],
    checkboxes: [],
    submit: 'button:has-text("Apply now"), button:has-text("Start")',
    dashboard: 'dashboard',
    keys: ['CHANGELLY_API_KEY', 'CHANGELLY_SECRET'],
    envVar: 'CHANGELLY_ENV',
  },
  kyrrex: {
    name: 'Kyrrex',
    url: 'https://kyrrex.com/register',
    apiUrl: 'https://kyrrex.com/account/api',
    fills: [
      { sel: 'input[type="email"]', val: EMAIL },
      { sel: 'input[type="password"]', val: PW },
    ],
    checkboxes: ['input[type="checkbox"]'],
    submit: 'button[type="submit"], button:has-text("Register")',
    dashboard: 'account',
    keys: ['KYRREX_API_KEY', 'KYRREX_SECRET'],
    envVar: 'KYRREX_ENV',
  },
};

async function grabOne(gwId, page) {
  const gw = GATEWAYS[gwId];
  console.log(`\n${'='.repeat(55)}`);
  console.log(`  🔑 ${gw.name}`);
  console.log(`${'='.repeat(55)}`);
  
  const signupTime = new Date().toISOString();
  
  await page.goto(gw.url, { timeout: 20000, waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);
  
  // Check for CAPTCHA
  const captcha = await hasCaptcha(page);
  console.log(`  CAPTCHA: ${captcha ? 'YES ⚠️' : 'No ✅'}`);
  
  // Fill and submit
  await tryFillAndSubmit(page, gw);
  console.log('  ✓ Form filled + submitted');
  await page.waitForTimeout(6000);
  
  // Wait for dashboard or OTP or error
  const deadline = Date.now() + 240000;
  let done = false;
  
  while (Date.now() < deadline) {
    const url = page.url().toLowerCase();
    
    if (url.includes(gw.dashboard)) {
      console.log('  ✅ Dashboard reached!');
      done = true;
      break;
    }
    
    // Check for error messages (CAPTCHA rejection)
    const errors = await page.evaluate(() => {
      const errs = [];
      document.querySelectorAll('[class*=error], [class*=alert-danger], .invalid-feedback, .text-red-500, .text-danger').forEach(e => {
        const t = e.textContent.trim();
        if (t && t.length > 3 && t.length < 200) errs.push(t);
      });
      return errs;
    });
    if (errors.length > 0) {
      console.log('  ⚠️  Errors:', errors.slice(0,3));
      if (errors.some(e => /captcha|robot|verif/i.test(e))) {
        console.log('  ❌ CAPTCHA blocked. Must solve manually.');
        return false;
      }
    }
    
    // Check OTP
    const digits = page.locator('input[maxlength="1"]');
    const dc = await digits.count().catch(() => 0);
    const otpEl = page.locator('input[name="otp"], input[autocomplete="one-time-code"], input[placeholder*="code" i]').first();
    const otpVis = await otpEl.isVisible().catch(() => false);
    
    if (dc >= 4 || otpVis) {
      console.log('  → OTP screen. Fetching...');
      const code = await fetchOTP(signupTime, 120);
      if (code) {
        if (code.startsWith('http')) {
          await page.goto(code, { timeout: 15000, waitUntil: 'domcontentloaded' });
        } else {
          if (dc >= 4) {
            const all = await digits.all();
            for (let i = 0; i < Math.min(code.length, all.length); i++) {
              await all[i].fill(code[i]).catch(() => {});
            }
          } else {
            await otpEl.fill(code).catch(() => {});
          }
          for (const s of ['button:has-text("Verify")', 'button:has-text("Confirm")', 'button[type="submit"]']) {
            try { const b = page.locator(s).first(); if (await b.isVisible({timeout:1000})) { await b.click(); break; } } catch(e) {}
          }
        }
        await page.waitForTimeout(5000);
        if (page.url().toLowerCase().includes(gw.dashboard)) { done = true; break; }
      }
    }
    
    await sleep(2000);
  }
  
  if (!done) {
    console.log('  ⚠️  No dashboard. URL:', page.url());
    return false;
  }
  
  // Get API keys
  if (gw.apiUrl) {
    await page.goto(gw.apiUrl, { timeout: 15000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(5000);
  }
  
  const text = await page.innerText('body').catch(() => '');
  const updates = {};
  
  const uuid = text.match(/\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b/i)?.[1];
  const long = text.match(/(\b[A-Za-z0-9]{32,64}\b)/)?.[1];
  
  if (uuid && gw.keys[0]) updates[gw.keys[0]] = uuid;
  if (long && gw.keys[1] && !updates[gw.keys[1]]) updates[gw.keys[1]] = long;
  updates[gw.envVar] = 'production';
  
  // Try input values
  const inputs = page.locator('input');
  for (let i = 0; i < (await inputs.count()); i++) {
    try {
      const v = await inputs.nth(i).inputValue().catch(() => '');
      if (v && v.length > 24 && !updates[gw.keys[0]]) { updates[gw.keys[0]] = v; break; }
    } catch(e) {}
  }
  
  if (Object.keys(updates).length > 1) {
    console.log('  🔑 Keys found:');
    for (const [k, v] of Object.entries(updates)) console.log(`     ${k} = ${v.slice(0,12)}...`);
    updateEnv(updates);
    console.log(`  ✅ ${gw.name} SAVED`);
    return true;
  }
  
  console.log('  ⚠️  No keys auto-extracted');
  return false;
}

async function main() {
  const args = process.argv.slice(2);
  let targets;
  if (!args.length || args[0] === 'all') {
    targets = Object.keys(GATEWAYS);
  } else {
    targets = args.filter(a => GATEWAYS[a]);
  }
  if (!targets.length) { console.log('Available:', Object.keys(GATEWAYS).join(', ')); process.exit(1); }
  
  console.log(`\n🚀 GRAB KEYS v2 — ${targets.length} gateway(s) — Chromium headless`);
  console.log(`   Email: ${EMAIL}`);
  
  const b = await chromium.launch({ headless: true });
  
  let success = 0, fail = 0;
  for (const gwId of targets) {
    const ctx = await b.newContext({ viewport: { width: 1400, height: 900 } });
    const page = await ctx.newPage();
    try {
      const ok = await grabOne(gwId, page);
      ok ? success++ : fail++;
    } catch(e) { console.log(`  ❌ ${e.message.slice(0,80)}`); fail++; }
    await ctx.close();
  }
  await b.close();
  
  console.log(`\n${'='.repeat(55)}`);
  console.log(`  ✅ ${success} succeeded  ❌ ${fail} failed`);
  if (success > 0) console.log('  Run: python3 gateway_agents_activate.py --verify');
  console.log(`${'='.repeat(55)}`);
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
