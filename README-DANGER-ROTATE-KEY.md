Security & local setup

1) Rotate the exposed OpenRouter key immediately
- Go to your OpenRouter dashboard and revoke the leaked key.
- Create a new key and store it securely (do NOT commit it).

2) How to run locally
- Backend (Django):
  - Create a `.env` or set env vars:
    - `DJANGO_SECRET_KEY` (optional)
    - `DJANGO_DEBUG=True`
    - `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`
    - `OPENROUTER_API_KEY` (server-side only)
  - Run:
    ```powershell
    cd backend
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver
    ```
- Frontend (Next.js):
  - Fill `portal/.env.local` with:
    - `NEXT_PUBLIC_SUPABASE_URL`
    - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
    - `NEXT_PUBLIC_GOOGLE_CLIENT_ID`
  - Run:
    ```powershell
    cd portal
    npm install
    npm run dev
    ```

3) Supabase auth settings (for local dev)
- In Supabase Console -> Auth -> Settings:
  - Add `http://localhost:3000` and `http://localhost:3001` to Allowed origins
  - Add `http://localhost:3000/auth/callback` and `http://localhost:3001/auth/callback` to Redirect URLs

4) Purging secrets from git history
- We ran a mirror rewrite using `git-filter-repo` to replace the exposed key with `REDACTED` and pushed cleaned refs to GitHub.
- After a history rewrite, all collaborators must re-clone the repo.

5) Testing signup/login (Playwright)
- There is a test scaffold at `portal/tests/auth.spec.ts`. To run it:
  - `cd portal`
  - `npm i -D playwright`
  - `npx playwright test portal/tests/auth.spec.ts`

If you want, I can try deleting the local mirror `repo-mirror.git` again or help you rotate the key step-by-step while you perform the action on the OpenRouter site.
