'use client';

import { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { AuthChangeEvent, Session } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';
import { clearDjangoAuthToken, confirmPasswordReset } from '@/lib/api';
import { useI18n } from '@/lib/i18n';

type RecoveryStatus = 'checking' | 'ready' | 'invalid';
type ResetProvider = 'supabase' | 'django';

function hasRecoveryMarker() {
  const search = new URLSearchParams(window.location.search);
  const hash = new URLSearchParams(window.location.hash.slice(1));
  return search.get('type') === 'recovery'
    || search.has('code')
    || hash.get('type') === 'recovery';
}

export default function ResetPasswordPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [recoveryStatus, setRecoveryStatus] = useState<RecoveryStatus>('checking');
  const [resetProvider, setResetProvider] = useState<ResetProvider>('supabase');

  useEffect(() => {
    let active = true;
    let recoverySessionReceived = false;
    const search = new URLSearchParams(window.location.search);
    if (search.get('provider') === 'django') {
      setResetProvider('django');
      setRecoveryStatus('ready');
      return () => {
        active = false;
      };
    }

    const recoveryLink = hasRecoveryMarker();
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event: AuthChangeEvent, session: Session | null) => {
      if (event === 'PASSWORD_RECOVERY' && session) {
        recoverySessionReceived = true;
        if (active) {
          setRecoveryStatus('ready');
          window.history.replaceState(null, '', window.location.pathname);
        }
      }
    });

    supabase.auth.getSession().then((result: { data: { session: Session | null }; error: Error | null }) => {
      if (!active) return;
      const { data, error: sessionError } = result;
      if (sessionError) {
        setRecoveryStatus('invalid');
        return;
      }
      if ((recoveryLink && data.session) || recoverySessionReceived) {
        setRecoveryStatus('ready');
        window.history.replaceState(null, '', window.location.pathname);
        return;
      }
      setRecoveryStatus('invalid');
    }).catch(() => {
      if (!active) return;
      setRecoveryStatus('invalid');
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (recoveryStatus !== 'ready') {
      setError(t('passwordResetLinkInvalid'));
      return;
    }
    if (!password || password.length < 8) {
      setError(t('passwordMinLength'));
      return;
    }
    if (password !== confirmPassword) {
      setError(t('passwordsDoNotMatch'));
      return;
    }

    setLoading(true);
    try {
      if (resetProvider === 'django') {
        const search = new URLSearchParams(window.location.search);
        const uid = search.get('uid');
        const token = search.get('token');
        if (!uid || !token) throw new Error(t('passwordResetLinkInvalid'));
        await confirmPasswordReset(uid, token, password);
      } else {
        const { error: updateError } = await supabase.auth.updateUser({ password });
        if (updateError) throw updateError;
      }

      clearDjangoAuthToken();
      const { error: signOutError } = await supabase.auth.signOut();
      if (signOutError) console.error('Password updated, but the recovery session could not be signed out:', signOutError);

      setSuccess(t('passwordUpdated'));
      setPassword('');
      setConfirmPassword('');
      setTimeout(() => router.push('/'), 1800);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : t('passwordUpdateFailed'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container section" style={{ maxWidth: 480 }}>
      <div className="card" style={{ padding: 28 }}>
        <h1 style={{ marginBottom: 12 }}>{t('resetPassword')}</h1>
        {recoveryStatus === 'checking' ? (
          <p role="status" style={{ color: 'var(--text-muted)', marginBottom: 20 }}>{t('loadingDashboard')}...</p>
        ) : recoveryStatus === 'invalid' ? (
          <>
            <p role="alert" style={{ color: 'var(--danger)', marginBottom: 20 }}>
              {error || t('passwordResetLinkInvalid')}
            </p>
            <button className="btn btn-primary" type="button" onClick={() => router.push('/')}>
              {t('signIn')}
            </button>
          </>
        ) : (
          <>
            <p style={{ color: 'var(--text-muted)', marginBottom: 20 }}>{t('enterNewPassword')}</p>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <input
                className="input"
                type="password"
                autoComplete="new-password"
                minLength={8}
                placeholder={t('newPassword')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <input
                className="input"
                type="password"
                autoComplete="new-password"
                minLength={8}
                placeholder={t('confirmPassword')}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
              {error && <p role="alert" style={{ color: 'var(--danger)', margin: 0 }}>{error}</p>}
              {success && <p role="status" style={{ color: 'var(--brand)', margin: 0 }}>{success}</p>}
              <button className="btn btn-primary" type="submit" disabled={loading}>
                {loading ? t('updating') : t('updatePassword')}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
