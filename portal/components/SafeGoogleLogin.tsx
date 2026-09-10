"use client";

import React from 'react';
import { GoogleLogin } from '@react-oauth/google';

export default function SafeGoogleLogin({ onCredential }: { onCredential: (cred?: string) => void }) {
  return (
    <GoogleLogin
      onSuccess={(resp) => onCredential((resp as any)?.credential)}
      onError={() => onCredential(undefined)}
    />
  );
}
