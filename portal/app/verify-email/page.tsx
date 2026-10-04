'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { setDjangoAuthToken, verifyEmail } from '@/lib/api';

export default function VerifyEmailPage() {
  const router = useRouter();
  const [status, setStatus] = useState<'pending' | 'success' | 'error'>('pending');
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const run = async () => {
      try {
        const token = new URLSearchParams(window.location.search).get('token');
        if (token) {
          const { data } = await verifyEmail(token);
          if (!data?.access) throw new Error('Verification succeeded but no sign-in token was returned.');
          setDjangoAuthToken(data.access);
          setStatus('success');
          window.setTimeout(() => window.location.assign('/dashboard'), 1200);
          return;
        }

        const { data: { session }, error } = await supabase.auth.getSession();
        if (error) throw error;
        if (session?.user?.email_confirmed_at) {
          setStatus('success');
          setTimeout(() => router.push('/dashboard'), 1200);
          return;
        }
        setStatus('error');
      } catch (err: any) {
        console.error('Verify email check failed:', err);
        setStatus('error');
      }
    };

    run();
  }, [router]);

  return (
    <div className="container section" style={{ maxWidth: 520, textAlign: 'center' }}>
      {status === 'pending' && <p>Checking your verification status...</p>}
      {status === 'success' && <p style={{ color: 'var(--brand)' }}>✓ Email verified. Redirecting to your dashboard...</p>}
      {status === 'error' && <p style={{ color: 'var(--danger)' }}>Your email could not be verified yet. Please check the verification link in your inbox or sign in again.</p>}
    </div>
  );
}
