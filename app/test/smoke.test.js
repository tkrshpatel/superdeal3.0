import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('PWA shell files exist', () => {
  assert.equal(fs.existsSync('index.html'), true);
  assert.equal(fs.existsSync('public/manifest.webmanifest'), true);
  assert.equal(fs.existsSync('public/sw.js'), true);
  assert.equal(fs.readFileSync('src/main.js', 'utf8').includes('SuperDeal'), true);
});


test('affiliate CTA uses the Capacitor Browser path', () => {
  const main = fs.readFileSync('src/main.js', 'utf8');
  assert.equal(main.includes("import { Browser } from '@capacitor/browser';"), true);
  assert.equal(main.includes("Browser.open({url})"), true);
  assert.equal(main.includes("d.affiliate_url||d.source_url"), true);
});
