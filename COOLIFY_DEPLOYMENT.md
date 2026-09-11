# Coolify Deployment Preparation

This repository is prepared for three Coolify services from the same GitHub repository:

```text
Next.js frontend -> app.yourdomain.com:3000
Django backend   -> api.yourdomain.com:8000
PostgreSQL       -> private Coolify network
```

## Media storage decision

The application stores avatars, course thumbnails, lesson files, resources,
certificates, hero images, and knowledge-base files with Django's filesystem
storage. A Coolify persistent volume mounted at `/app/media` is the smallest
change for the current architecture and keeps the requested deployment to
three services. The backend serves `/media/` explicitly in both development and
production; it does not depend on `DEBUG=True` media serving.

For a multi-backend or multi-region deployment, migrate the default storage to
S3-compatible object storage later. Object storage is more durable and scales
better, but it adds credentials, a fourth external dependency, and a storage
migration that is not required for the initial Coolify topology.

## Coolify services

### Frontend

- Build context: `portal`
- Dockerfile: `portal/Dockerfile`
- Port: `3000`
- Domain: `https://app.yourdomain.com`
- Health check: `/`
- Set `NEXT_PUBLIC_*` variables as build-time variables.

### Backend

- Build context: `backend`
- Dockerfile: `backend/Dockerfile`
- Port: `8000`
- Domain: `https://api.yourdomain.com`
- Health check: `/health/`
- Persistent volume: `/app/media`
- The container runs migrations and `collectstatic` before Gunicorn starts.

### PostgreSQL

- Create a Coolify-managed PostgreSQL resource.
- Keep it on the private network.
- Set `DATABASE_URL` on the backend using the internal database hostname.
- Configure automated backups before importing production data.

## Local Compose test

```powershell
Copy-Item .env.compose.example .env.compose
# Edit .env.compose and replace every placeholder secret.
docker compose --env-file .env.compose up --build
```

Check `http://localhost:8000/health/`, `http://localhost:8000/admin/`, and
`http://localhost:3000`. Stop the stack with:

```powershell
docker compose --env-file .env.compose down
```

## Required environment variables

Backend variables are documented in `backend/.env.production.example`.
Frontend variables are documented in `portal/.env.production.example`.
Never commit `.env`, `.env.production`, `.env.compose`, database passwords,
OAuth secrets, Supabase private keys, or AI provider keys.

## Database and media migration

1. Back up the current PostgreSQL database.
2. Back up the current `backend/media/` contents separately.
3. Create the Coolify PostgreSQL resource and restore the database backup.
4. Attach the backend persistent volume and restore media into `/app/media`.
5. Run the backend health, admin, upload, authentication, course, quiz, and certificate smoke tests.
6. Switch DNS only after both services pass their health checks.

Do not use the local SQLite database as the production migration source unless
that data is intentionally the production dataset.