'use client';

import React from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { AuthProvider } from '@/lib/auth-context';
import { I18nProvider } from '@/lib/i18n';
import { useEffect } from 'react';

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

if (!GOOGLE_CLIENT_ID) {
  console.info('NEXT_PUBLIC_GOOGLE_CLIENT_ID is not set. Google sign-in will be disabled.');
}

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Clean up extension-injected attributes that can cause hydration mismatches
    try {
      const attrs = ['suppresshydrationwarning', 'data-qb-installed'];
      attrs.forEach((a) => {
        if (document.documentElement.hasAttribute(a)) document.documentElement.removeAttribute(a);
        if (document.body && document.body.hasAttribute && document.body.hasAttribute(a)) document.body.removeAttribute(a);
      });
    } catch (e) {
      // Ignore errors during cleanup
    }
  }, []);
  if (!GOOGLE_CLIENT_ID) {
    return (
      <I18nProvider>
        <AuthProvider>{children}</AuthProvider>
      </I18nProvider>
    );
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <I18nProvider>
        <AuthProvider>{children}</AuthProvider>
      </I18nProvider>
    </GoogleOAuthProvider>
  );
}
