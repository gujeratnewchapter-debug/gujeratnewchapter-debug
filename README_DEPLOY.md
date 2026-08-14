Deployment checklist — automated and manual steps

Summary
- Frontend (Next.js) is intended to be deployed to Vercel.
- Backend (Django) should be deployed to a dedicated host (Render, Heroku, DigitalOcean App Platform, or a VPS) — Vercel is not a suitable host for a full Django app.

Files added
- `portal/vercel.json` — Vercel build and route placeholder (forwards `/api/*` to backend).
- `.github/workflows/deploy-frontend.yml` — GitHub Actions workflow to build and deploy the `portal` folder to Vercel on push to `main`/`master`.
- `backend/.env.production.example` and `portal/.env.production.example` — example env vars for production.

Quick steps (frontend)
1. Create a GitHub repo (or push this repo) and connect it to Vercel.
2. In Vercel Project Settings → Environment Variables, add:
   - `NEXT_PUBLIC_SUPABASE_URL` (value from Supabase project)
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_BASE_URL` (https://api.YOUR_DOMAIN or https://your-backend-host)
   - `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (optional)
3. In GitHub repository settings → Secrets → Actions add:
   - `VERCEL_TOKEN` (create at https://vercel.com/account/tokens)
   - `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` (found in Vercel project settings)
4. Push to `main` — the workflow `.github/workflows/deploy-frontend.yml` will build `portal` and run the Vercel action.

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
- `portal/vercel.json` contains a rewrite that assumes `NEXT_PUBLIC_API_BASE_URL` is set in Vercel to your backend host. Edit as needed.
- I cannot set Vercel or GitHub secrets on your account — add them in the respective provider consoles.
