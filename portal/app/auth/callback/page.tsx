'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

export default function AuthCallbackPage() {
  const router = useRouter();
  const [message, setMessage] = useState('Completing sign-in...');

  useEffect(() => {
    const complete = async () => {
      try {
        const { error } = await supabase.auth.getSession();
        if (error) throw error;
        setMessage('Sign-in complete. Redirecting...');
        router.push('/dashboard');
      } catch {
        setMessage('The sign-in could not be completed. Please try again.');
        setTimeout(() => router.push('/'), 2000);
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
