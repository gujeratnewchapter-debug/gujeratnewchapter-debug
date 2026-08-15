export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  if (!token || typeof token !== 'string') return null;

  const parts = token.split('.');
  if (parts.length !== 3) return null;

  try {
    const payloadSegment = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = payloadSegment + '='.repeat((4 - (payloadSegment.length % 4)) % 4);
    const binary = typeof atob === 'function' ? atob(padded) : Buffer.from(padded, 'base64').toString('binary');
    const text = typeof Uint8Array !== 'undefined'
      ? new TextDecoder().decode(Uint8Array.from(binary, (char) => char.charCodeAt(0)))
      : binary;
    return JSON.parse(text) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function isUsableJwtToken(token?: string | null): boolean {
  if (!token || typeof token !== 'string') return false;

  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload !== 'object') return false;

  const exp = Number(payload.exp);
  if (Number.isFinite(exp) && exp > 0 && Date.now() >= exp * 1000) {
    return false;
  }

  const tokenType = payload.token_type;
  const userId = payload.user_id;

  if (tokenType !== 'access') return false;
  if (userId === undefined || userId === null || Number.isNaN(Number(userId))) return false;

  const issuer = typeof payload.iss === 'string' ? payload.iss : '';
  if (issuer.includes('supabase')) return false;

  return true;
}

export function getStoredDjangoAccessToken(): string | null {
  try {
    return localStorage.getItem('django_access') || null;
  } catch {
    return null;
  }
}
