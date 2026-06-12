#!/usr/bin/env node
/**
 * Playwright Form Filler — Karmostaji KYB auto-submit to gateway contact forms.
 * Uses headful Firefox so human can solve CAPTCHAs when they appear.
 * 
 * Usage: node playwright_form_filler.js <gateway_id>
 *        node playwright_form_filler.js all
 */
const { firefox } = require('playwright');
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const KYB = {
  legal_name: 'AL KARMOSTAJI TRADING ENTERPRISES',
  short_name: 'KARMOSTAJI TRADING LLC',
  license: '200100',
  register: '1387701',
  dcci: '7447',
  duns: '534472717',
  contact_name: 'Mohammed Ali Vellopadikal',
  contact_role: 'CEO / Partner',
  contact_email: 'compliance@sichermayor.online',
  contact_phone: '+971561049878',
  country: 'United Arab Emirates',
  city: 'Dubai',
  website: 'https://beastbrain.sichermayor.online',
  monthly_volume: '20000-100000',
  // Outreach message for textareas
  message: `We are applying for production merchant access for KARMOSTAJI TRADING LLC, with legal applicant AL KARMOSTAJI TRADING ENTERPRISES, a Dubai licensed general trading business (License 200100, Register 1387701, DCCI 7447, D-U-N-S 534472717, License expiry 2027-01-13).

Product URL: https://beastbrain.sichermayor.online/card-to-crypto

Use case: BeastPay/BeastBrain provides a hosted card-to-crypto checkout for users buying USDT, USDC, BTC, ETH, or SOL with AED, USD, EUR, GBP. Card entry, KYC, issuer challenge, risk review, and settlement stay inside the provider. BeastBrain does NOT collect raw card data, CVV, expiry, OTP, or 3DS.

Business: Ecommerce/online retail for industrial sewing machines (including Juki brand, 10,000-50,000 AED/item). Expected monthly volume: USD 20K-100K.

Request: Merchant onboarding, KYB checklist, production API credentials, domain approval for beastbrain.sichermayor.online, AED card-to-USDT/USDC support, webhook guidance, commercial terms.

Contact: Mohammed Ali Vellopadikal, CEO/Partner, +971561049878, compliance@sichermayor.online

Our document package (Dubai Commercial License, CEO Emirates ID, proof of address) is ready.`
};

const GATEWAYS = {
  guardarian: {
    url: 'https://guardarian.com/contact-us',
    fields: [
      { sel: 'input[placeholder="Name"]', value: KYB.contact_name },
      { sel: 'input[placeholder="Email"]', value: KYB.contact_email },
      { sel: 'textarea[placeholder="Message"]', value: KYB.message },
    ],
    submit: 'button:has-text("Talk to us")',
    hasCaptcha: true,
  },
  // Add more as we find form structures
};

async function fillGuardarian(page) {
  const gw = GATEWAYS.guardarian;
  console.log('  → Navigating to', gw.url);
  await page.goto(gw.url, { timeout: 20000, waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/guardarian_01_before.png' });

  // Fill fields
  for (const f of gw.fields) {
    try {
      const el = page.locator(f.sel).first();
      if (await el.isVisible({ timeout: 3000 })) {
        await el.fill(f.value);
        console.log('  ✓ Filled:', f.sel);
      }
    } catch(e) {
      console.log('  ✗ Failed:', f.sel, e.message.slice(0,40));
    }
  }
  await page.screenshot({ path: '/tmp/guardarian_02_filled.png' });

  if (gw.hasCaptcha) {
    console.log('\n  ⚠️  RECAPTCHA detected — YOU must solve it in the browser window.');
    console.log('  After solving CAPTCHA, the script will auto-submit.');
    console.log('  Waiting up to 5 minutes for you to solve...\n');
    // Wait for reCAPTCHA to be solved (textarea gets filled with token)
    try {
      await page.waitForFunction(() => {
        const el = document.querySelector('.g-recaptcha-response');
        return el && el.value && el.value.length > 10;
      }, { timeout: 300000 });
      console.log('  ✓ CAPTCHA solved!');
    } catch(e) {
      console.log('  ✗ CAPTCHA timeout — continuing anyway');
    }
  }

  // Submit
  try {
    const btn = page.locator(gw.submit).first();
    await btn.click();
    console.log('  ✓ Submitted!');
    await page.waitForTimeout(5000);
    await page.screenshot({ path: '/tmp/guardarian_03_submitted.png' });
    console.log('  URL after submit:', page.url());
  } catch(e) {
    console.log('  ✗ Submit failed:', e.message.slice(0,50));
  }

  console.log('\n  ✅ Guardarian form completed. Leave browser open to verify.');
  await page.waitForTimeout(10000);
}

async function main() {
  const args = process.argv.slice(2);
  const target = args[0] || 'guardarian';

  if (target === 'all') {
    for (const gwId of Object.keys(GATEWAYS)) {
      console.log(`\n${'='.repeat(70)}`);
      console.log(`  🚀 FILLING: ${gwId}`);
      console.log(`${'='.repeat(70)}`);
      const browser = await firefox.launch({ headless: false });
      const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
      const page = await context.newPage();
      try {
        if (gwId === 'guardarian') await fillGuardarian(page);
      } catch(e) { console.log('ERR:', e.message); }
      console.log('  Closing browser in 3s...');
      await page.waitForTimeout(3000);
      await browser.close();
    }
    return;
  }

  if (!GATEWAYS[target]) {
    console.log('Unknown gateway:', target);
    console.log('Available:', Object.keys(GATEWAYS).join(', '));
    return;
  }

  console.log(`\n${'='.repeat(70)}`);
  console.log(`  🚀 PLAYWRIGHT FORM FILLER — ${target}`);
  console.log(`${'='.repeat(70)}`);

  const browser = await firefox.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  try {
    if (target === 'guardarian') await fillGuardarian(page);
  } catch(e) {
    console.log('FATAL:', e.message);
  } finally {
    console.log('\n  Press Ctrl+C to close browser, or it will close in 30s...');
    try { await page.waitForTimeout(30000); } catch(e) {}
    await browser.close();
  }
}

main();
