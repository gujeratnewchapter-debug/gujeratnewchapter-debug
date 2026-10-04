# Supabase Auth Setup

This project uses Supabase Auth as the real authentication layer for the React/Next.js frontend. Django remains the application backend for educational data.

## 1) Create a Supabase project

1. Go to https://supabase.com and create a new project.
2. Select your organization and region.
3. Save the project URL and the project API keys.

## 2) Get project credentials

In the Supabase Dashboard:

- Open Project Settings > API
- Copy:
  - Project URL
  - anon/public key
- Keep the secret/service role key private and never put it in the frontend.

## 3) Configure auth providers

### Email authentication

- Go to Authentication > Providers
- Enable Email
- Enable email confirmation if you want a verification step
- Configure email templates

### Password reset

- Go to Authentication > Settings
- Enable email recovery.
- Set the Supabase **Site URL** to the canonical deployed portal URL (for this deployment, `https://ethiopian-startup-school-frontend.vercel.app`).
- Add these production redirect URLs to the Supabase redirect allow-list:
  - `https://ethiopian-startup-school-frontend.vercel.app/auth/callback`
  - `https://ethiopian-startup-school-frontend.vercel.app/reset-password`
- Add `http://localhost:3000/auth/callback` and `http://localhost:3000/reset-password` only for local development.
- Keep confirmation email templates based on Supabase's `{{ .ConfirmationURL }}`. Do not hard-code a localhost URL in an email template.

### Google OAuth

1. In Google Cloud Console create OAuth credentials.
2. Set the authorized redirect URI in Google Console to:
   - https://<project-ref>.supabase.co/auth/v1/callback
3. In Supabase:
   - Authentication > Providers > Google
   - Enable Google
   - Add the Google client ID and client secret
4. Add redirect URLs in Supabase Auth:
   - http://localhost:3000/auth/callback
   - https://your-production-domain.com/auth/callback

## 4) Configure project environment variables

Frontend:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_APP_URL=https://your-production-domain.com
```

Backend:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_JWT_SECRET=
SUPABASE_JWKS_URL=https://your-project-ref.supabase.co/auth/v1/.well-known/jwks.json
```

If you use a JWT secret instead of JWKS, set `SUPABASE_JWT_SECRET` and keep it server-only.

## 5) Django configuration

The Django backend validates bearer tokens from Supabase using the custom authentication class in `backend/accounts/authentication.py`.

Ensure your environment contains the Supabase URL/JWKS values before starting Django.

## 6) Local testing checklist

1. Register a new user.
2. Check email confirmation.
3. Verify link works.
4. Log in with email/password.
5. Test invalid credentials and weak password.
6. Test Google sign in.
7. Test password reset.
8. Test logout.
9. Hit a protected Django endpoint with a bearer token.
10. Refresh the browser and confirm session persists.

## 7) Production deployment

Set `NEXT_PUBLIC_APP_URL` in the frontend hosting environment to the canonical portal URL, set the same URL as the Supabase **Site URL**, and add these production redirects to Supabase's allow-list:

- https://your-domain.com/auth/callback
- https://your-domain.com/reset-password

Backend-issued legacy verification links use `/verify-email?token=...`; that page exchanges the token with the API. Supabase confirmation emails should instead use `/auth/callback`.

For public launch, configure a production SMTP provider and appropriate sending/rate limits in Supabase Auth. The built-in email service is not intended for high-volume production registration.

## 8) Important security notes

- Never put the service-role key in the frontend.
- Never store plain text passwords.
- Never disable backend JWT validation.
- Never trust frontend-only auth checks for protected API endpoints.
