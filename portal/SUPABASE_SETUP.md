Supabase setup for Ethiopian Startup School portal

This document lists the steps required to get authentication flows working end-to-end in development and production.

1) Enable Email Signups
- In Supabase dashboard → Authentication → Settings
  - Ensure "Allow signups" is ON.
  - If you restrict signups by domain, add any test email domains (e.g., example.com) or remove the restriction for testing.

2) Configure Google OAuth provider
- In Supabase dashboard → Authentication → Providers → Google
  - Enter the Google OAuth Client ID and Client Secret (from Google Cloud Console).
  - Add the redirect URI Supabase shows (usually: https://<project>.supabase.co/auth/v1/callback).
  - Save the provider settings.

3) Environment variables (frontend)
- Create or update `portal/.env.local` with:
  - `NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-public-key>`
  - `NEXT_PUBLIC_GOOGLE_CLIENT_ID=<google-client-id>`
  - `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api` (dev)

4) Environment variables (backend)
- Set the following in your Django env (e.g., `.env`, system env or hosting provider):
  - `DJANGO_ALLOWED_HOSTS` include your frontend host(s)
  - `DJANGO_CORS_ALLOWED_ORIGINS` include frontend dev URL(s) (http://localhost:3000,3001,3002...)
  - Keep secret keys and service_role keys out of the frontend.

5) Testing the flows locally
- Start the backend: `python manage.py runserver 127.0.0.1:8000`
- Start the frontend: `cd portal && npm run dev` (ensure `NEXT_PUBLIC_*` vars present in `.env.local`)
- Run quick diagnostic:
```
node portal/scripts/check_supabase.js
```
- Attempt email signup in the UI; if you see `email is invalid` or `too many requests`, check Supabase dashboard settings and rate limits.

6) Google direct sign-in
- Frontend uses Google Identity Services to obtain an ID token and exchanges it with Supabase via `signInWithIdToken`.
- Ensure `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set in `portal/.env.local` and the Google provider is configured in Supabase.
- If direct ID-token sign-in fails, the app falls back to redirect-based OAuth.

7) Troubleshooting
- If `/auth/v1/token?grant_type=password` returns 400:
  - Confirm `NEXT_PUBLIC_SUPABASE_ANON_KEY` matches the project's anon key.
  - Confirm email/password signups are enabled in Supabase.
  - Inspect browser network response body for the exact error message — the app now logs detailed Supabase errors to the console.

8) Production notes
- Do NOT commit `NEXT_PUBLIC_SUPABASE_ANON_KEY` or any private keys to source control.
- For production, set CORS to specific origins rather than allowing all origins.
- Consider using Supabase Realtime or webhooks for account events if needed.

If you want, I can walk you through the Supabase dashboard steps and validate each required redirect and key.