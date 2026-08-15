import test from 'node:test';
import assert from 'node:assert/strict';
import { isUsableJwtToken } from './auth-token.ts';

test('rejects malformed bearer tokens', () => {
  assert.equal(isUsableJwtToken('not-a-jwt'), false);
});

test('rejects expired JWTs', () => {
  const expired = 'eyJhbGciOiJub25lIn0.eyJleHAiOjE3MDAwMDAwMDB9';
  assert.equal(isUsableJwtToken(expired), false);
});

test('accepts valid unexpired JWTs', () => {
  const now = Math.floor(Date.now() / 1000) + 3600;
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const payload = Buffer.from(JSON.stringify({ exp: now })).toString('base64url');
  const token = `${header}.${payload}.signature`;
  assert.equal(isUsableJwtToken(token), true);
});
