import test from 'node:test';
import assert from 'node:assert/strict';
import { formatNoticeDate } from './notices.ts';

test('formats notice dates with a readable month, day, and year', () => {
  const formatted = formatNoticeDate('2026-10-17T08:30:00.000Z');

  assert.match(formatted, /October/);
  assert.match(formatted, /2026/);
});

test('uses a safe fallback for invalid notice timestamps', () => {
  assert.equal(formatNoticeDate('not-a-date'), 'Date unavailable');
});
