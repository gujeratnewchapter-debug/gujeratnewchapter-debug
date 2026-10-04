'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import * as api from './api';
import { supabase } from './supabase';
import {
  DJANGO_AUTH_TOKEN_UPDATED_EVENT,
  setDjangoAuthToken,
  clearDjangoAuthToken,
  syncSupabaseSessionWithRefresh,
} from './api';
import { getStoredDjangoAccessToken, isUsableJwtToken } from './auth-token';
import { getAuthRedirectUrl } from './auth-redirect';

export type Role = 'student' | 'instructor' | 'super_admin';

export interface User {
  id: string | number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  is_email_verified: boolean;
  avatar?: string | null;
  phone_number?: string;
  bio?: string;
  created_at?: string;
  course_progress?: Array<{ course_id?: number; course_title?: string; progress_percent?: number; completed_lessons?: number; total_lessons?: number; }>
  certificates?: Array<{ id?: number | string; course_title?: string; certificate_number?: string; pdf_file?: string; }>
  enrollment_count?: number;
}

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isBackendAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: (idToken?: string) => Promise<void>;
  signUp: (payload: {
    full_name: string; email: string; password: string; confirm_password: string; role?: 'student' | 'instructor';
  }) => Promise<{ requiresConfirmation: boolean } | void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<User>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function toDisplayName(fullName?: string | null, email?: string | null) {
  if (fullName && fullName.trim()) return fullName.trim();
  if (email) return email.split('@')[0];
  return 'Student';
}

function normalizeSupabaseUser(rawUser: any): User | null {
  if (!rawUser) return null;
  const fullName = rawUser.user_metadata?.full_name || rawUser.user_metadata?.name || '';
  const role = (rawUser.user_metadata?.role as Role) || 'student';

  return {
    id: rawUser.id,
    username: toDisplayName(fullName, rawUser.email),
    email: rawUser.email || '',
    first_name: fullName.split(' ')[0] || '',
    last_name: fullName.split(' ').slice(1).join(' ') || '',
    role,
    is_email_verified: !!rawUser.email_confirmed_at,
    avatar: rawUser.user_metadata?.avatar_url || null,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [tokenRefresh, setTokenRefresh] = useState(0); // Force re-render when token changes
  const [supabaseSessionAvailable, setSupabaseSessionAvailable] = useState(false);
  const [hasHydrated, setHasHydrated] = useState(false);

  useEffect(() => {
    setHasHydrated(true);
  }, []);

  useEffect(() => {
    const handleAuthTokenUpdate = () => setTokenRefresh((previous) => previous + 1);
    window.addEventListener(DJANGO_AUTH_TOKEN_UPDATED_EVENT, handleAuthTokenUpdate);
    return () => window.removeEventListener(DJANGO_AUTH_TOKEN_UPDATED_EVENT, handleAuthTokenUpdate);
  }, []);

  // Recalculate hasValidDjangoSession whenever tokenRefresh changes (triggered by setDjangoAuthToken)
  const djangoAccessToken = getStoredDjangoAccessToken();
  const hasValidDjangoSession = !!djangoAccessToken && isUsableJwtToken(djangoAccessToken);
  const isAuthenticated = hasHydrated ? (hasValidDjangoSession || Boolean(user?.email) || supabaseSessionAvailable) : false;

  useEffect(() => {
    let mounted = true;

    const loadSession = async () => {
      const { data: { session }, error } = await supabase.auth.getSession();
      if (!mounted) return;

      const djangoToken = getStoredDjangoAccessToken();
      const hasValidDjangoToken = !!djangoToken && isUsableJwtToken(djangoToken);

      if (hasValidDjangoToken) {
        if (error || !session) {
          setSupabaseSessionAvailable(false);
        } else {
          setSupabaseSessionAvailable(Boolean(session));
        }

        try {
          const { data } = await api.getMe();
          if (mounted) setUser({ ...normalizeSupabaseUser(session?.user ?? null), ...data });
        } catch (err) {
          console.error('Failed to fetch current user profile (/me):', err);
          if (mounted) setUser(normalizeSupabaseUser(session?.user ?? null));
        } finally {
          if (mounted) setIsLoading(false);
        }
        return;
      }

      if (session) {
        setSupabaseSessionAvailable(true);
        setUser(normalizeSupabaseUser(session.user));
        try {
          const { data: sessionData } = await syncSupabaseSessionWithRefresh(session.access_token);
          if (!mounted) return;
          setDjangoAuthToken(sessionData.access);
          setUser(sessionData.user as User);
          setTokenRefresh(prev => prev + 1);
        } catch (err) {
          console.error('Failed to sync the Supabase session with the learning platform:', err);
          if (mounted) {
            clearDjangoAuthToken();
            setSupabaseSessionAvailable(true);
            setUser(normalizeSupabaseUser(session.user));
          }
        } finally {
          if (mounted) setIsLoading(false);
        }
        return;
      }

      clearDjangoAuthToken();
      setSupabaseSessionAvailable(false);
      setUser(null);
      setIsLoading(false);
    };

    loadSession();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event: string, session: any) => {
      const djangoToken = getStoredDjangoAccessToken();
      const hasValidDjangoToken = !!djangoToken && isUsableJwtToken(djangoToken);

      setSupabaseSessionAvailable(Boolean(session));

      if (hasValidDjangoToken) {
        if (!session) {
          setUser(null);
          setIsLoading(false);
          return;
        }

        const nextUser = normalizeSupabaseUser(session.user);
        setUser(nextUser);
        setIsLoading(false);
        return;
      }

      if (!session) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      const nextUser = normalizeSupabaseUser(session.user);
      setUser(nextUser);
      setIsLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  async function signIn(email: string, password: string) {
    const normalizedEmail = email.trim();

    try {
      // Remove stale Django credentials before starting a fresh Supabase login.
      clearDjangoAuthToken();
      const res = await supabase.auth.signInWithPassword({ email: normalizedEmail, password });
      const error = (res as any)?.error;

      if (error) {
        const msg = (error?.message || '').toLowerCase();
        if (msg.includes('email not confirmed')) {
          throw new Error('Email not confirmed. Resend the verification email to activate your account.');
        }
        const isSupabaseUnavailable = msg.includes('supabase not configured') || msg.includes('not configured');
        const isCredentialFailure = isSupabaseUnavailable || msg.includes('invalid login') || msg.includes('invalid login credentials') || msg.includes('user not found') || msg.includes('email not confirmed');

        if (isCredentialFailure) {
          try {
            const { data: { session } } = await supabase.auth.getSession();
            const accessToken = session?.access_token;
            if (accessToken) {
              const { data: sessionData } = await syncSupabaseSessionWithRefresh(accessToken);
              setDjangoAuthToken(sessionData.access);
              setUser(sessionData.user as User);
              setTokenRefresh(prev => prev + 1);
              return;
            }

            // Keep legacy Django accounts usable when Supabase has no session.
            const backendRes = await api.login(normalizedEmail, password);
            const backendToken = backendRes?.data?.access;
            if (!backendToken) throw new Error('No access token returned from backend login');
            setDjangoAuthToken(backendToken);
            const { data: profile } = await api.getMe();
            setUser(profile as User);
            setTokenRefresh(prev => prev + 1);
            return;
          } catch (backendErr: any) {
            const backendMsg = backendErr?.response?.data?.detail || backendErr?.message || 'Backend login failed';
            throw new Error(`Authentication failed: ${backendMsg}`);
          }
        }

        console.error('Supabase signInWithPassword returned error:', error);
        throw error;
      }

      try {
        const accessToken = res.data?.session?.access_token;
        if (!accessToken) throw new Error('No Supabase session token returned');

        const { data: sessionData } = await syncSupabaseSessionWithRefresh(accessToken);
        setDjangoAuthToken(sessionData.access);
        setUser(sessionData.user as User);
        setTokenRefresh(prev => prev + 1);
        return;
      } catch (backendErr: any) {
        clearDjangoAuthToken();
        const detail = backendErr?.response?.data?.detail;
        if (typeof detail === 'string' && detail.trim()) {
          throw new Error(`Sign-in could not be completed: ${detail}`);
        }
        throw new Error('Sign-in is temporarily unavailable. Please try again.');
      }

      const { data: { session } } = await supabase.auth.getSession();
      setSupabaseSessionAvailable(Boolean(session));
      setUser(normalizeSupabaseUser(session?.user ?? null));
    } catch (err: any) {
      if (err?.message?.toLowerCase().includes('email not confirmed')) {
        throw new Error('Email not confirmed. Resend the verification email to activate your account.');
      }
      if (err?.response?.status === 400 || err?.status === 400) {
        throw new Error('Sign-in failed: invalid credentials or request. Check email/password and verify your email.');
      }
      throw err;
    }
  }

  async function signInWithGoogle() {
    const isProviderDisabledError = (err: any) => {
      const msg = (err?.message || err?.error_description || String(err || '')).toLowerCase();
      return msg.includes('unsupported provider') || msg.includes('provider is not enabled') || msg.includes('google provider') && msg.includes('not enabled');
    };

    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: getAuthRedirectUrl('/auth/callback'),
      },
    });
    if (error) {
      if (isProviderDisabledError(error)) {
        throw new Error('Google sign-in is not enabled in your Supabase project. Enable Google in Supabase Auth Providers or use email/password sign-in instead.');
      }
      throw error;
    }
  }

  async function signUp(payload: {
    full_name: string; email: string; password: string; confirm_password: string; role?: 'student' | 'instructor';
  }) {
    const fullName = payload.full_name.trim();
    if (!fullName || !payload.email || !payload.password || !payload.confirm_password) {
      throw new Error('Please complete all required fields.');
    }
    if (payload.password !== payload.confirm_password) {
      throw new Error('Password confirmation does not match.');
    }
    if (payload.password.length < 8) {
      throw new Error('Password must be at least 8 characters long.');
    }

    try {
      const { data, error } = await supabase.auth.signUp({
        email: payload.email,
        password: payload.password,
        options: {
          data: {
            full_name: fullName,
            role: payload.role || 'student',
            email_verified: false,
          },
          emailRedirectTo: getAuthRedirectUrl('/auth/callback'),
        },
      });

      if (error) {
        const m = (error?.message || '').toLowerCase();
        // If Supabase rejects due to project settings or rate limits, attempt backend fallback
        if ((error as any)?.status === 429 || m.includes('rate limit') || m.includes('too many') || (m.includes('invalid') && m.includes('email'))) {
          try {
            // Fallback to backend registration endpoint
            const firstName = fullName.split(' ')[0] || '';
            const lastName = fullName.split(' ').slice(1).join(' ') || '';

            await api.register({
              username: toDisplayName(fullName, payload.email),
              email: payload.email,
              password: payload.password,
              full_name: fullName,
              first_name: firstName,
              last_name: lastName,
              role: payload.role || 'student',
            });
            return { requiresConfirmation: true };
          } catch (be) {
            console.error('Backend register fallback failed:', be);
            // If backend also fails, surface original Supabase error
            if (m.includes('rate limit') || m.includes('too many')) {
              throw new Error('Too many signup attempts. Supabase is rate-limiting requests. Please wait a few minutes and try again.');
            }
            throw error;
          }
        }
        // Handle other Supabase errors
        if (m.includes('email address') && m.includes('invalid')) {
          throw new Error('Registration failed: Supabase rejected the email address. Ensure "Allow signups" is enabled and allowed email domains include your address in the Supabase project settings.');
        }
        throw error;
      }

      return { requiresConfirmation: !data.session };
    } catch (err: any) {
      // Re-throw errors so callers (UI) can handle special cases such as rate-limits
      throw err;
    }
  }

  async function signOut() {
    // Sign out from Supabase (if used) and clear any persisted Django tokens we set.
    try {
      const { error } = await supabase.auth.signOut();
      if (error) console.warn('Supabase signOut returned error:', error);
    } catch (e) {
      console.warn('Error signing out from Supabase:', e);
    }

    try {
      clearDjangoAuthToken();
      const keysToRemove = Object.keys(localStorage).filter((key) =>
        key.startsWith('sb-') && (key.includes('-auth-token') || key.includes('-auth-token-code-verifier'))
      );
      keysToRemove.forEach((key) => localStorage.removeItem(key));
    } catch (e) {
      console.warn('Error clearing persisted auth data:', e);
    }

    setSupabaseSessionAvailable(false);
    setUser(null);
    setTokenRefresh(prev => prev + 1); // Trigger re-render to update hasValidDjangoSession
  }

  const refreshProfile = React.useCallback(async (): Promise<User> => {
    const { data } = await api.getMe();
    setUser(data as User);
    setTokenRefresh(prev => prev + 1);
    return data as User;
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: hasHydrated ? isAuthenticated : false,
        isBackendAuthenticated: hasHydrated ? hasValidDjangoSession : false,
        signIn,
        signInWithGoogle,
        signUp,
        signOut,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
