'use client';

import React from 'react';
import { AuthProvider } from '@/lib/auth-context';
import { I18nProvider } from '@/lib/i18n';
import { useEffect } from 'react';

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
  return (
    <I18nProvider>
      <AuthProvider>{children}</AuthProvider>
    </I18nProvider>
  );
}
