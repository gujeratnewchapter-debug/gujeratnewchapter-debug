import test from 'node:test';
import assert from 'node:assert/strict';
import { isExpiredDjangoAccessToken, isUsableJwtToken } from './auth-token.ts';

function createToken(payload) {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
  return `${header}.${encodedPayload}.signature`;
}

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
  const payload = Buffer.from(JSON.stringify({ exp: now, token_type: 'access', user_id: 1 })).toString('base64url');
  const token = `${header}.${payload}.signature`;
  assert.equal(isUsableJwtToken(token), true);
});

test('identifies expired Django access tokens for session renewal', () => {
  assert.equal(isExpiredDjangoAccessToken(createToken({
    exp: 1,
    token_type: 'access',
    user_id: 1,
  })), true);
});

test('does not classify malformed, Supabase, or non-access tokens as expired Django tokens', () => {
  const future = Math.floor(Date.now() / 1000) + 3600;
  assert.equal(isExpiredDjangoAccessToken('not-a-jwt'), false);
  assert.equal(isExpiredDjangoAccessToken(createToken({
    exp: 1,
    token_type: 'access',
    user_id: 1,
    iss: 'https://example.supabase.co/auth/v1',
  })), false);
  assert.equal(isExpiredDjangoAccessToken(createToken({
    exp: 1,
    token_type: 'refresh',
    user_id: 1,
  })), false);
  assert.equal(isExpiredDjangoAccessToken(createToken({
    exp: future,
    token_type: 'access',
    user_id: 1,
  })), false);
});
