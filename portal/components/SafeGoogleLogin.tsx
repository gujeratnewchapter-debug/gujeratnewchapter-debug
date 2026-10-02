"use client";

import React from 'react';
import { GoogleLogin } from '@react-oauth/google';

export default function SafeGoogleLogin({ onCredential }: { onCredential: (cred?: string) => void }) {
  return (
    <GoogleLogin
      type="standard"
      theme="outline"
      size="large"
      text="signin_with"
      shape="rectangular"
      logo_alignment="left"
      onSuccess={(resp) => onCredential((resp as any)?.credential)}
      onError={() => onCredential(undefined)}
    />
  );
}
