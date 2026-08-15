Supabase setup and diagnostics

1) Local env
- Copy `.env.example` to `.env.local` and set:
  - `NEXT_PUBLIC_SUPABASE_URL` — your Supabase project URL (e.g. https://xyz.supabase.co)
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` — the "anon public" key from Supabase Project → Settings → API
  - `NEXT_PUBLIC_GOOGLE_CLIENT_ID` — (optional) Google OAuth client id

2) Enable email signups
- In Supabase dashboard: Authentication → Settings
  - Toggle `Allow signups` ON
  - If `Allowed email domains` is set, add the domain you will test (or remove the restriction)

3) Google OAuth (optional)
- In Supabase dashboard: Authentication → Providers → Google
  - Enter your Google Client ID and Secret
  - Add redirect URL(s) under Authentication → Settings → Redirect URLs (e.g. `http://localhost:3000/auth/callback`)

4) Diagnostic script
- Run this script to detect common misconfigurations:

```powershell
cd portal
node scripts/check_supabase.js
```

5) Security note
- Do NOT commit your anon or service_role keys to the repo. Use Vercel/GitHub Secrets or a local `.env.local`.
- If a key was exposed, rotate it immediately in Supabase (Project → Settings → API).

6) If signups fail
- The diagnostic will report likely causes. Fix settings in the dashboard and retry the signup test.
