import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { getSignInProcessSteps } from './sign-in-guide.ts';

test('uses CMS named groups with seven account steps and six learning steps', () => {
  const accountSetupSteps = Array.from({ length: 7 }, (_, index) => ({
    title: `Account ${index + 1}`,
    desc: `Account description ${index + 1}`,
  }));
  const learningSteps = Array.from({ length: 6 }, (_, index) => ({
    title: `Learning ${index + 1}`,
    desc: `Learning description ${index + 1}`,
  }));

  const sections = getSignInProcessSteps({
    en: { account_setup_steps: accountSetupSteps, learning_steps: learningSteps },
  }, 'en');

  assert.deepEqual(sections.accountSetupSteps, accountSetupSteps);
  assert.deepEqual(sections.learningSteps, learningSteps);
  assert.equal(sections.accountSetupSteps.length, 7);
  assert.equal(sections.learningSteps.length, 6);
});

test('uses localized CMS panel headings', () => {
  const sections = getSignInProcessSteps({
    en: {
      account_setup_title: 'Your account',
      learning_title: 'Your learning',
      account_setup_steps: [],
      learning_steps: [],
    },
  }, 'en');

  assert.equal(sections.accountSetupTitle, 'Your account');
  assert.equal(sections.learningTitle, 'Your learning');
});

test('falls back to exactly seven account steps and six learning steps', () => {
  const sections = getSignInProcessSteps(undefined, 'en');

  assert.equal(sections.accountSetupTitle, 'Set up your account');
  assert.equal(sections.learningTitle, 'Start learning');
  assert.equal(sections.accountSetupSteps.length, 7);
  assert.equal(sections.learningSteps.length, 6);
  assert.ok(sections.accountSetupSteps.every(({ title, desc }) => title && desc));
  assert.ok(sections.learningSteps.every(({ title, desc }) => title && desc));
});

test('continues parsing all thirteen legacy items as seven account and six learning steps', () => {
  const items = Array.from({ length: 13 }, (_, index) => [`Legacy ${index + 1}`, `Description ${index + 1}`]);
  const sections = getSignInProcessSteps({ en: { items } }, 'en');

  assert.equal(sections.accountSetupSteps.length, 7);
  assert.equal(sections.learningSteps.length, 6);
  assert.deepEqual(sections.accountSetupSteps[0], { title: 'Legacy 1', desc: 'Description 1' });
  assert.deepEqual(sections.accountSetupSteps[6], { title: 'Legacy 7', desc: 'Description 7' });
  assert.deepEqual(sections.learningSteps[0], { title: 'Legacy 8', desc: 'Description 8' });
  assert.deepEqual(sections.learningSteps[5], { title: 'Legacy 13', desc: 'Description 13' });
  assert.equal(sections.accountSetupTitle, 'Set up your account');
  assert.equal(sections.learningTitle, 'Start learning');
});

test('renders a standalone accessible Next Link callout to notices', () => {
  const source = readFileSync(new URL('../app/page.tsx', import.meta.url), 'utf8');

  assert.match(source, /<Link href="\/notices"[^>]*className="home-notices-callout"/);
  assert.match(source, /aria-label="New notices"/);
  assert.match(source, />\s*New\s*</);
  assert.match(source, /className="home-notices-indicator" aria-hidden="true"/);
  assert.match(source, /className="input"[^>]*aria-label=\{t\('searchPlaceholder'\)\}/);
});

test('keeps the notices attention indicator visible without motion when reduced motion is preferred', () => {
  const css = readFileSync(new URL('../app/globals.css', import.meta.url), 'utf8');

  assert.match(css, /\.home-notices-indicator[\s\S]*?animation:/);
  assert.match(css, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.home-notices-indicator[\s\S]*?animation:\s*none/);
});

test('raises homepage instructional copy above the compact global text scale with stronger muted contrast', () => {
  const css = readFileSync(new URL('../app/globals.css', import.meta.url), 'utf8');

  assert.match(css, /\.homepage-shell\s*\{[^}]*--text-muted:\s*#[0-9a-f]{6}/i);
  assert.match(css, /\.homepage-shell \.signin-guide-step p\s*\{[^}]*font-size:\s*14px/i);
  assert.match(css, /\.homepage-shell \.home-ai-card p:last-of-type[\s\S]*?font-size:\s*14px/i);
  assert.match(css, /\.homepage-shell \.home-steps-section \.step-item p:last-child[\s\S]*?font-size:\s*14px/i);
});
