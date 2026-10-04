import { normalizePublicEnvironmentValue } from './http-headers';

const configuredAppUrl =
  normalizePublicEnvironmentValue(process.env.NEXT_PUBLIC_APP_URL, 'NEXT_PUBLIC_APP_URL')
  || normalizePublicEnvironmentValue(process.env.NEXT_PUBLIC_FRONTEND_URL, 'NEXT_PUBLIC_FRONTEND_URL');

export function getAuthRedirectUrl(path: string) {
  if (!path.startsWith('/') || path.startsWith('//')) {
    throw new Error('Authentication redirect path must be a same-site absolute path.');
  }

  if (typeof window === 'undefined') {
    throw new Error('Authentication redirects can only be created in a browser.');
  }

  const baseUrl = process.env.NODE_ENV === 'development'
    ? window.location.origin
    : configuredAppUrl || window.location.origin;

  return new URL(path, baseUrl).toString();
}
