'use client';

import React, { useState } from 'react';
import { X, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { useI18n } from '@/lib/i18n';
import { supabase } from '@/lib/supabase';

export function AuthModal({ onClose }: { onClose: () => void }) {
  const { signIn, signUp, signInWithGoogle } = useAuth();
  const { t } = useI18n();
  const [tab, setTab] = useState<'signin' | 'signup'>('signin');
  const [role, setRole] = useState<'student' | 'instructor'>('student');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState('');

  const [signInForm, setSignInForm] = useState({ email: '', password: '' });
  const [signUpForm, setSignUpForm] = useState({
    full_name: '', email: '', password: '', confirm_password: '',
  });

  async function handleSignIn(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await signIn(signInForm.email.trim(), signInForm.password);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSignUp(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const payload = {
        ...signUpForm,
        full_name: signUpForm.full_name.trim(),
        email: signUpForm.email.trim(),
        role,
      };
      await signUp(payload);
      setSuccess('Account created. Please check your email to verify your account before signing in.');
      setTab('signin');
      setSignUpForm({ full_name: '', email: '', password: '', confirm_password: '' });
    } catch (err: any) {
      setError(err?.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleSignIn() {
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      await signInWithGoogle();
    } catch (err: any) {
      setError(err?.message || 'Google sign-in failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function handleForgotPassword() {
    const email = forgotPasswordEmail.trim();
    if (!email) {
      setError('Please enter your email address.');
      return;
    }
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });
      if (error) throw error;
      setSuccess('A password reset email has been sent. Please check your inbox.');
    } catch (err: any) {
      setError(err?.message || 'Unable to send password reset email.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
    >
      <div onClick={(e) => e.stopPropagation()} className="card" style={{ width: 440, maxWidth: '100%', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: 14, right: 14, background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
          <X size={18} />
        </button>

        <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
          <button
            className="btn"
            onClick={() => setTab('signin')}
            style={{ flex: 1, background: tab === 'signin' ? 'var(--brand)' : 'var(--surface-2)', borderColor: tab === 'signin' ? 'var(--brand)' : 'var(--border)', color: tab === 'signin' ? '#fff' : 'var(--text)' }}
          >
            {t('signIn')}
          </button>
          <button
            className="btn"
            onClick={() => setTab('signup')}
            style={{ flex: 1, background: tab === 'signup' ? 'var(--brand)' : 'var(--surface-2)', borderColor: tab === 'signup' ? 'var(--brand)' : 'var(--border)', color: tab === 'signup' ? '#fff' : 'var(--text)' }}
          >
            {t('signUp')}
          </button>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 14 }}>
          <button type="button" className="btn btn-primary" onClick={handleGoogleSignIn} disabled={loading} style={{ width: '100%' }}>
            Continue with Google
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '14px 0', color: 'var(--text-muted)', fontSize: 12 }}>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          or continue with email
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
        </div>

        {error && <p style={{ color: 'var(--danger)', fontSize: 13, marginBottom: 10 }}>{error}</p>}
        {success && <p style={{ color: 'var(--brand)', fontSize: 13, marginBottom: 10 }}>{success}</p>}

        {tab === 'signin' ? (
          <form onSubmit={handleSignIn} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input className="input" type="email" placeholder="Email" value={signInForm.email} onChange={(e) => setSignInForm((f) => ({ ...f, email: e.target.value }))} required />
            <div style={{ position: 'relative' }}>
              <input className="input" type={showPassword ? 'text' : 'password'} placeholder="Password" value={signInForm.password} onChange={(e) => setSignInForm((f) => ({ ...f, password: e.target.value }))} required />
              <button type="button" onClick={() => setShowPassword((v) => !v)} style={{ position: 'absolute', right: 8, top: 10, background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <button className="btn btn-primary" disabled={loading} type="submit">{t('signIn')}</button>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <button type="button" onClick={() => setTab('signup')} style={{ background: 'transparent', border: 'none', color: 'var(--brand)', cursor: 'pointer', padding: 0, fontWeight: 600 }}>
                Create account
              </button>
              <button type="button" onClick={handleForgotPassword} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}>
                Forgot password?
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <input className="input" type="email" placeholder="Enter your email to reset password" value={forgotPasswordEmail} onChange={(e) => setForgotPasswordEmail(e.target.value)} />
              <button type="button" className="btn btn-accent" onClick={handleForgotPassword} disabled={loading}>Send</button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSignUp} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              {(['student', 'instructor'] as const).map((r) => (
                <button
                  type="button"
                  key={r}
                  onClick={() => setRole(r)}
                  className="btn"
                  style={{ flex: 1, background: role === r ? 'var(--brand)' : 'var(--surface-2)', color: role === r ? '#fff' : 'var(--text)' }}
                >
                  {r === 'student' ? 'Student' : 'Instructor'}
                </button>
              ))}
            </div>
            <input className="input" placeholder="Full name" value={signUpForm.full_name} onChange={(e) => setSignUpForm((f) => ({ ...f, full_name: e.target.value }))} required />
            <input className="input" type="email" placeholder="Email" value={signUpForm.email} onChange={(e) => setSignUpForm((f) => ({ ...f, email: e.target.value }))} required />
            <div style={{ position: 'relative' }}>
              <input className="input" type={showPassword ? 'text' : 'password'} placeholder="Password" value={signUpForm.password} onChange={(e) => setSignUpForm((f) => ({ ...f, password: e.target.value }))} required />
              <button type="button" onClick={() => setShowPassword((v) => !v)} style={{ position: 'absolute', right: 8, top: 10, background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <div style={{ position: 'relative' }}>
              <input className="input" type={showConfirmPassword ? 'text' : 'password'} placeholder="Confirm password" value={signUpForm.confirm_password} onChange={(e) => setSignUpForm((f) => ({ ...f, confirm_password: e.target.value }))} required />
              <button type="button" onClick={() => setShowConfirmPassword((v) => !v)} style={{ position: 'absolute', right: 8, top: 10, background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            <button className="btn btn-primary" disabled={loading} type="submit">{t('signUp')}</button>
            <p style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>
              You will need to verify your email before signing in.
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
