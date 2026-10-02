'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { setDjangoAuthToken, syncSupabaseSessionWithRefresh } from '@/lib/api';
import { useAuth } from '@/lib/auth-context';

export default function AuthCallbackPage() {
  const router = useRouter();
  const { refreshProfile } = useAuth();
  const [message, setMessage] = useState('Completing sign-in...');

  useEffect(() => {
    const complete = async () => {
      try {
        const { data: sessionData, error } = await supabase.auth.getSession();
        if (error) throw error;
        const session = sessionData.session;
        if (!session?.access_token) throw new Error('No active sign-in session was returned. Please try again.');

        const { data: djangoSession } = await syncSupabaseSessionWithRefresh(session.access_token);
        setDjangoAuthToken(djangoSession.access);
        const profile = await refreshProfile();
        const requestedReturnTo = sessionStorage.getItem('auth_return_to');
        sessionStorage.removeItem('auth_return_to');
        const safeReturnTo = requestedReturnTo?.startsWith('/') && !requestedReturnTo.startsWith('//')
          ? requestedReturnTo
          : null;
        const target = profile.role === 'instructor'
          ? (safeReturnTo?.startsWith('/instructor/') ? safeReturnTo : '/instructor/courses/new')
          : (safeReturnTo && !safeReturnTo.startsWith('/instructor/') ? safeReturnTo : '/dashboard');
        setMessage('Sign-in complete. Redirecting...');
        router.push(target);
      } catch (err: any) {
        console.error('Auth callback error:', err);
        sessionStorage.removeItem('auth_return_to');
        const detail = err?.response?.data?.detail;
        const message = typeof detail === 'string' ? detail : err?.message;
        setMessage(message ? `Sign-in failed: ${message}` : 'The sign-in could not be completed. Please try again.');
        setTimeout(() => router.push('/'), 4000);
      }
    };

    complete();
  }, [refreshProfile, router]);

  return (
    <div className="container section" style={{ maxWidth: 520, textAlign: 'center' }}>
      <p>{message}</p>
    </div>
  );
}
