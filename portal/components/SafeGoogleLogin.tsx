"use client";

import React, { useEffect, useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { useAuth } from '@/lib/auth-context';

export default function SafeGoogleLogin({ onCredential }: { onCredential: (cred?: string) => void }) {
  const { signInWithGoogle } = useAuth();
  const [canUseGsi, setCanUseGsi] = useState(false);

  useEffect(() => {
    // If another instance already initialized GSI, set flag to false to avoid duplicate initialize warnings.
    // We use a global guard `__GSI_INITIALIZED_BY_APP` to detect prior initialization.
    if ((window as any).__GSI_INITIALIZED_BY_APP) {
      setCanUseGsi(false);
      return;
    }

    // Mark that we will initialize GSI when the provider/component mounts.
    // This prevents later mounts from attempting to initialize again.
    (window as any).__GSI_INITIALIZED_BY_APP = true;
    setCanUseGsi(true);
  }, []);

  if (!canUseGsi) {
    // Fallback: simple button that triggers the redirect-based OAuth sign in.
    return (
      <button type="button" className="btn btn-primary" onClick={() => signInWithGoogle()} style={{ width: '100%' }}>
        Continue with Google
      </button>
    );
  }

  return (
    <GoogleLogin
      onSuccess={(resp) => onCredential((resp as any)?.credential)}
      onError={() => onCredential(undefined)}
    />
  );
}
