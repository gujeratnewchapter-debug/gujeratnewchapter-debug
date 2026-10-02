Deployment checklist — automated and manual steps

Summary
- Frontend (Next.js) is intended to be deployed to Vercel.
- Backend (Django) should be deployed to a dedicated host (Render, Heroku, DigitalOcean App Platform, or a VPS) — Vercel is not a suitable host for a full Django app.

Files added
- `portal/vercel.json` — Vercel build and route placeholder (forwards `/api/*` to backend).
- `.github/workflows/frontend-ci.yml` — GitHub Actions workflow to lint and build the `portal` folder.
- `backend/.env.production.example` and `portal/.env.production.example` — example env vars for production.

Quick steps (frontend)
1. Create a GitHub repo (or push this repo) and connect it to Vercel.
2. In Vercel Project Settings → Environment Variables, add:
   - `NEXT_PUBLIC_SUPABASE_URL` (value from Supabase project)
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_BASE_URL` (https://api.YOUR_DOMAIN or https://your-backend-host)
   - `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (optional)
3. Connect the GitHub repository in Vercel Project Settings → Git. Production deployments then run automatically from pushes to the production branch; GitHub Actions does not need a Vercel token.
4. Set the production Supabase and API values under Vercel Project Settings → Environment Variables. Paste plain values without quotes or invisible BOM characters. Re-deploy after changing any `NEXT_PUBLIC_*` value because Next.js embeds them at build time.
5. GitHub Actions runs lint and a production build on frontend changes.

Quick steps (backend)
1. Choose a host (Render / Heroku / DigitalOcean App Platform / Azure App Service). Example with Render:
   - Create a new Web Service on Render connected to your GitHub repo.
   - Set build command: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`
   - Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
   - Add environment variables from `backend/.env.production.example`.
2. Ensure you configure static/media storage (S3 or Render disks) and set `MEDIA_URL`/`STATIC_URL` appropriately.

DNS and SSL
- For production, point your domain A/ALIAS to the hosting provider (Vercel for frontend; backend host for API). Enable HTTPS using the host's automatic cert provisioning.

Notes
- `portal/vercel.json` uses the Next.js framework configuration. Set `NEXT_PUBLIC_API_BASE_URL` in Vercel to your backend host.
- I cannot set Vercel or GitHub secrets on your account — add them in the respective provider consoles.
