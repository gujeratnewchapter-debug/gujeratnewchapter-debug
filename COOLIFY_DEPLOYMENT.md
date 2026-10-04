# Coolify Deployment Preparation

## Production architecture

```text
GitHub
  ├── Vercel: Next.js frontend
  └── Coolify: Django backend
        └── Existing Supabase PostgreSQL, Storage, and Auth
```

Do not create a Coolify database or replace the existing Supabase project.
The backend uses the existing Supabase PostgreSQL connection through
`DATABASE_URL`, the existing Supabase Storage S3-compatible endpoint, and the
existing Supabase Auth JWKS or JWT configuration.

## Coolify backend service

Use the repository root as the GitHub source and configure the service as:

- Build context: `backend`
- Dockerfile: `backend/Dockerfile`
- Application port: `8000`
- Start command: `./docker-entrypoint.sh`
- Health check: `GET https://<backend-domain>/health/`
- Public domain: the HTTPS domain generated or assigned by Coolify

The container installs dependencies, collects static files, and starts Gunicorn
on `0.0.0.0:${PORT:-8000}`. It does not reset, drop, flush, or recreate
production data. Migrations are opt-in: set `RUN_MIGRATIONS=True` only after
inspecting migration state and confirming the change is required.

A persistent `/app/media` volume is not required when the existing Supabase
Storage variables are configured. Keep the volume only for a deliberately
local/filesystem storage setup.

## Backend environment variables

Set these as Coolify service environment variables. Values must remain secret
except for public Supabase anon/JWKS-related values that are intentionally
needed by the backend:

```text
DJANGO_SECRET_KEY
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS
DJANGO_CORS_ALLOWED_ORIGINS
DJANGO_CSRF_TRUSTED_ORIGINS
DJANGO_SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS
DJANGO_SECURE_PROXY_SSL_HEADER=True
DJANGO_DB_CONN_MAX_AGE
RUN_MIGRATIONS=False
DATABASE_URL
FRONTEND_BASE_URL

SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_JWT_SECRET or SUPABASE_JWKS_URL

SUPABASE_S3_ENDPOINT
SUPABASE_S3_ACCESS_KEY_ID
SUPABASE_S3_SECRET_ACCESS_KEY
SUPABASE_S3_REGION
SUPABASE_STORAGE_BUCKET
SUPABASE_STORAGE_PUBLIC_URL

EMAIL_BACKEND
EMAIL_HOST
EMAIL_PORT
EMAIL_USE_TLS
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL
EMAIL_TIMEOUT
```

`DJANGO_ALLOWED_HOSTS` must contain the backend host without a scheme.
`DJANGO_CORS_ALLOWED_ORIGINS` and `DJANGO_CSRF_TRUSTED_ORIGINS` must contain
the exact Vercel frontend origin, without a path. `FRONTEND_BASE_URL` must be
the exact public Vercel URL and is used for email and certificate links.

## Frontend environment variables

In the existing Vercel frontend project, set:

```text
NEXT_PUBLIC_API_BASE_URL=https://<backend-domain>/api
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY
NEXT_PUBLIC_GOOGLE_CLIENT_ID
```

`NEXT_PUBLIC_API_BASE_URL` is the only frontend variable that changes for the
Coolify migration. Do not put backend secrets in Vercel environment variables.

## Coolify UI sequence

1. Create or open the Coolify project.
2. Add an application from the GitHub repository.
3. Select the repository and `main` branch.
4. Use Docker deployment with build context `backend` and Dockerfile
   `backend/Dockerfile`.
5. Set port `8000` and health path `/health/`.
6. Add the backend environment variables above through the Coolify secret
   interface.
7. Add the public backend domain and enable HTTPS.
8. Deploy and wait for the container and health check to become healthy.
9. Keep `RUN_MIGRATIONS=False` for the initial deployment. After the service is
   healthy, inspect `python manage.py showmigrations` and
   `python manage.py makemigrations --check`, then run only required migrations
   through a one-off Coolify command or temporary `RUN_MIGRATIONS=True`
   deployment.
10. In Vercel, update `NEXT_PUBLIC_API_BASE_URL` to the Coolify backend URL and
    redeploy the existing frontend.
11. Test public endpoints, Supabase JWT authentication, storage URLs, CORS,
    CSRF, and the complete learning flow.

Do not create a Coolify PostgreSQL resource, do not import or migrate the
existing Supabase database, and do not run destructive database commands.
