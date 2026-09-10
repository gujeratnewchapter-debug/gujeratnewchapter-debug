'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { getMe, setDjangoAuthToken, syncSupabaseSession } from '@/lib/api';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [message, setMessage] = useState('Completing sign-in...');

  useEffect(() => {
    const complete = async () => {
      try {
        const { data: sessionData, error } = await supabase.auth.getSession();
        if (error) throw error;
        const session = sessionData.session;
        let target = '/dashboard';
        if (session?.access_token) {
          const { data: djangoSession } = await syncSupabaseSession(session.access_token);
          setDjangoAuthToken(djangoSession.access);
          const { data: profile } = await getMe();
          if (profile.role === 'instructor') target = '/instructor/courses/new';
        }
        setMessage('Sign-in complete. Redirecting...');
        router.push(target);
      } catch (err: any) {
        console.error('Auth callback error:', err);
        setMessage(err?.message ? `Sign-in failed: ${err.message}` : 'The sign-in could not be completed. Please try again.');
        setTimeout(() => router.push('/'), 4000);
      }
    };

    complete();
  }, [router]);

  return (
    <div className="container section" style={{ maxWidth: 520, textAlign: 'center' }}>
      <p>{message}</p>
    </div>
  );
}
