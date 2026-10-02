import { createClient } from '@supabase/supabase-js';
import { assertValidHttpHeaderValue, normalizePublicEnvironmentValue } from './http-headers';

const supabaseUrl = normalizePublicEnvironmentValue(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  'NEXT_PUBLIC_SUPABASE_URL',
);
const supabaseAnonKey = normalizePublicEnvironmentValue(
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  'NEXT_PUBLIC_SUPABASE_ANON_KEY',
);

if (supabaseAnonKey) {
  assertValidHttpHeaderValue('apikey', supabaseAnonKey);
}

const supabaseFetch: typeof fetch = (input, init) => {
  const headers = init?.headers;
  if (headers instanceof Headers) {
    headers.forEach((value, name) => assertValidHttpHeaderValue(name, value));
  } else if (Array.isArray(headers)) {
    headers.forEach(([name, value]) => assertValidHttpHeaderValue(name, value));
  } else if (headers) {
    Object.entries(headers).forEach(([name, value]) => assertValidHttpHeaderValue(name, value));
  }

  return globalThis.fetch(input, init);
};

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn('Supabase environment variables are not configured. Authentication will be disabled until NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set.');
}
let supabaseClient: any = null;

if (supabaseUrl && supabaseAnonKey) {
  supabaseClient = createClient(supabaseUrl, supabaseAnonKey, {
    global: { fetch: supabaseFetch },
    auth: {
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  });
} else {
  // Minimal no-op stub to avoid runtime network requests when Supabase isn't configured.
  supabaseClient = {
    auth: {
      getSession: async () => ({ data: { session: null }, error: null }),
      refreshSession: async () => ({ data: { session: null }, error: new Error('Supabase not configured') }),
      onAuthStateChange: (_cb: any) => ({ data: { subscription: { unsubscribe: () => {} } } }),
      signInWithPassword: async () => ({ error: new Error('Supabase not configured') }),
      signInWithOAuth: async () => ({ error: new Error('Supabase not configured') }),
      signUp: async () => ({ data: { session: null }, error: null }),
      signOut: async () => ({ error: null }),
      updateUser: async () => ({ error: new Error('Supabase not configured') }),
      resetPasswordForEmail: async () => ({ error: new Error('Supabase not configured') }),
    },
    from: () => ({ select: async () => ({ data: null, error: new Error('Supabase not configured') }) }),
  };
}

export const supabase = supabaseClient;
