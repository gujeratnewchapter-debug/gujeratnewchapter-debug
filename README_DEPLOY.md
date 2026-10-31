Deployment checklist — automated and manual steps

Summary
- Frontend (Next.js) is intended to be deployed to Vercel.
- Backend (Django) should be deployed to a dedicated host (Render, Heroku, DigitalOcean App Platform, or a VPS) — Vercel is not a suitable host for a full Django app.
- The standalone Business Plan Development course site is configured as a Render Static Site in `render.yaml`.
- The Render Django backend seeds the Business Plan Development course curriculum during startup.

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
3. After database migrations, the backend creates or updates the Business Plan Development course with exactly three modules and all nine detailed lesson notes. New courses default to draft; an existing course's publication status is preserved. Seeding is enabled by default in the Docker entrypoint and explicitly enabled in the Render Blueprint; set `SEED_BUSINESS_PLAN_DEVELOPMENT=false` to disable it. The command is idempotent and removes outdated modules and lessons from this course so the database matches the requested curriculum. Removing those records also removes related quizzes, attempts, bookmarks, and lesson progress through database cascades. The seed uses the first instructor account, or falls back to the first Django superuser; if neither exists, startup logs a clear error and the service will not start.

Quick steps (standalone course site on Render)
1. Sync the repository's `render.yaml` Blueprint in Render. It defines a separate `business-plan-development-course` Static Site and leaves the Django API configuration unchanged.
2. The Static Site builds with `node scripts/build-course-site.mjs` and publishes `course-site/dist`. The build copies the course notes into the published directory; the page renders the notes and provides a Markdown download.
3. After the first deploy succeeds, open the Static Site's `onrender.com` URL and check the course page and Markdown download.

Advertisement campaigns
- Run the normal Django migration step (`python manage.py migrate`) when deploying the backend; migration `0015` creates the campaign and anonymous event tables.
- In Django admin, use **Site settings → Advertisements** to create, preview, schedule, prioritize, activate, or remove campaigns. The global switch is under **Site settings → Site settings**.
- Images accept JPEG, PNG, or WebP up to 10 MB. Videos accept MP4 or WebM up to 100 MB; external videos must use YouTube or Vimeo. HTTPS is required for external media and destination links.
- Leave **Target routes** empty to show a campaign across the site. Otherwise enter a JSON list of paths, for example `["/", "/courses/*"]`.
- Select a frequency per campaign: once per browser session, once per local calendar day, or once per new browser page load. SPA route changes do not count as new visits. The close countdown defaults to four seconds; delay and countdown are capped at 60 and 30 seconds.
- Video ads attempt autoplay with sound. Browsers may block audible autoplay until the visitor interacts; uploaded videos then offer a "Play with sound" button, while embedded providers retain their own playback controls. A destination URL is optional; when supplied, the ad shows the configured CTA label or defaults to "Visit advertiser."
- Uploads use the configured Django default storage, which is the existing Supabase Storage integration when its `SUPABASE_S3_*` settings are present. Verify those credentials and the public media URL are configured in Render before relying on uploaded assets; otherwise Django falls back to local disk, which is not persistent across Render instances/redeployments.
- The admin campaign list reports impressions, clicks, and click-through rate. These are approximate browser-reported counts; blockers, lost requests, and repeated visits can affect totals. No visitor IP address or account identifier is stored.
- Locally, run the targeted backend checks with `python manage.py test site_settings.test_advertisements site_settings.tests.PageContentAdminTests`. The frontend popup is part of the root Next.js layout and deploys with the existing Vercel frontend.

DNS and SSL
- For production, point your domain A/ALIAS to the hosting provider (Vercel for frontend; backend host for API). Enable HTTPS using the host's automatic cert provisioning.

Notes
- `portal/vercel.json` uses the Next.js framework configuration. Set `NEXT_PUBLIC_API_BASE_URL` in Vercel to your backend host.
- I cannot set Vercel or GitHub secrets on your account — add them in the respective provider consoles.
