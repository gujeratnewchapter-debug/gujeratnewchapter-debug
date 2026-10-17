'use client';

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { useI18n } from '@/lib/i18n';

export default function ResetPasswordPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess('');

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
      const { error: updateError } = await supabase.auth.updateUser({ password });
      if (updateError) throw updateError;
      setSuccess(t('passwordUpdated'));
      setTimeout(() => router.push('/'), 1800);
    } catch (err: any) {
      setError(err?.message || t('passwordUpdateFailed'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container section" style={{ maxWidth: 480 }}>
      <div className="card" style={{ padding: 28 }}>
        <h1 style={{ marginBottom: 12 }}>{t('resetPassword')}</h1>
        <p style={{ color: 'var(--text-muted)', marginBottom: 20 }}>{t('enterNewPassword')}</p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <input className="input" type="password" placeholder={t('newPassword')} value={password} onChange={(e) => setPassword(e.target.value)} required />
          <input className="input" type="password" placeholder={t('confirmPassword')} value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required />
          {error && <p style={{ color: 'var(--danger)', margin: 0 }}>{error}</p>}
          {success && <p style={{ color: 'var(--brand)', margin: 0 }}>{success}</p>}
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? t('updating') : t('updatePassword')}
          </button>
        </form>
      </div>
    </div>
  );
}
