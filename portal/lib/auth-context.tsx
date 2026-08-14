'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import * as api from './api';
import { supabase } from './supabase';

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
}

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signUp: (payload: {
    full_name: string; email: string; password: string; confirm_password: string; role?: 'student' | 'instructor';
  }) => Promise<{ requiresConfirmation: boolean } | void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
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

  useEffect(() => {
    let mounted = true;

    const loadSession = async () => {
      const { data: { session }, error } = await supabase.auth.getSession();
      if (!mounted) return;

      if (error || !session) {
        setUser(null);
        setIsLoading(false);
        return;
      }

      const nextUser = normalizeSupabaseUser(session.user);
      setUser(nextUser);

      try {
        const { data } = await api.getMe();
        if (mounted) setUser({ ...normalizeSupabaseUser(session.user), ...data });
      } catch {
        if (mounted) setUser(nextUser);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    loadSession();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event: string, session: any) => {
      const nextUser = normalizeSupabaseUser(session?.user ?? null);
      setUser(nextUser);
      setIsLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  async function signIn(email: string, password: string) {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    const { data: { session } } = await supabase.auth.getSession();
    setUser(normalizeSupabaseUser(session?.user ?? null));
  }

  async function signInWithGoogle() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    if (error) throw error;
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

    const { data, error } = await supabase.auth.signUp({
      email: payload.email,
      password: payload.password,
      options: {
        data: {
          full_name: fullName,
          role: payload.role || 'student',
          email_verified: false,
        },
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) throw error;

    return { requiresConfirmation: !data.session };
  }

  async function signOut() {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setUser(null);
  }

  async function refreshProfile() {
    const { data } = await api.getMe();
    setUser((current) => ({ ...(current || {} as User), ...data } as User));
  }

  return (
    <AuthContext.Provider
      value={{ user, isLoading, isAuthenticated: !!user, signIn, signInWithGoogle, signUp, signOut, refreshProfile }}
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
