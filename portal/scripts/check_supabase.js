// Simple Supabase diagnostic script
// Usage: node scripts/check_supabase.js

require('dotenv').config({ path: '.env.local' });
const { createClient } = require('@supabase/supabase-js');

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

(async () => {
  console.log('Supabase URL:', url ? 'present' : 'MISSING');
  console.log('Supabase anon key:', key ? 'present' : 'MISSING');

  if (!url || !key) {
    console.log('\nAction: Ensure both NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set in .env.local or environment.');
    process.exit(2);
  }

  const supabase = createClient(url, key);

  try {
    const { data, error } = await supabase.auth.getSession();
    if (error) {
      console.log('getSession: ERROR', error.message);
    } else {
      console.log('getSession: OK (no session or anonymous)');
    }
  } catch (e) {
    console.log('getSession: EXCEPTION', e.message || e);
  }

  // Try a lightweight signUp to detect project-level signup restrictions.
  const testEmail = `diag-${Date.now()}@example.com`;
  const testPassword = 'DiagTest123!';
  console.log('\nAttempting lightweight signup (will not create persistent accounts if blocked)');

  try {
    const { data, error } = await supabase.auth.signUp({ email: testEmail, password: testPassword });
    if (error) {
      const msg = (error.message || '').toLowerCase();
      console.log('signUp: ERROR ->', error.message);
      if (msg.includes('email address') && msg.includes('invalid')) {
        console.log('\nLikely causes:');
        console.log('- Email signups are disabled in Supabase (Dashboard → Authentication → Settings → Allow signups).');
        console.log('- Allowed email domains are configured and block example.com.');
        console.log('\nAction: Enable signups or add allowed domains to include your test email domain.');
      }
    } else {
      console.log('signUp: OK', data.session ? 'session created' : 'signup created (email verify may be required)');
    }
  } catch (e) {
    console.log('signUp: EXCEPTION', e.message || e);
  }

  console.log('\nDiagnostics complete.');
})();
