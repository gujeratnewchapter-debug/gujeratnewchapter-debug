# Ethiopian Startup School — Full-Stack Portal

Django REST backend + Next.js web portal for an AI-powered startup/business
education platform. **Web-based only** — no mobile app.

## Structure

```
backend/   Django + DRF API (auth, courses, quizzes, certificates, AI tutor, site settings)
portal/    Next.js 14 web portal (public site, student dashboard, instructor course-builder)
```

## What's in this build

**Backend** (`/backend` — Django + DRF, JWT auth, PostgreSQL/MySQL/SQLite)
- Custom User model with roles (student / instructor / super_admin)
- Email verification (branded "Ethiopian Startup School" sender/subject)
  + Google OAuth login
- Courses: Category → Course → Section → Lesson → Resource, with subtitle,
  rich-text description & notes (with a notes-as-cards toggle), category,
  instructor, thumbnail — everything the course-builder form needs
- Quizzes: multiple choice/checkbox/true-false/fill-blank/essay, auto-graded,
  per-lesson quizzes that **gate the next lesson until an 80% pass**
  (unlimited retry attempts), full Question/Choice CRUD API for the
  instructor course-builder
- Certificates: auto-issued PDF with embedded QR verification
- AI Tutor/Mentor/Coach: chat endpoint with a RAG scaffold
- Site settings: singleton model backing the footer (address, phone, bank
  details, Telebirr) and a public contact-form endpoint — all editable by
  admins via the API/Django admin, no code changes needed
- Ownership/permission checks throughout: an instructor can only edit their
  own courses/sections/lessons/quizzes; admins can edit everything
- A web-based admin panel already exists at `/admin/` (Django admin) with
  full CRUD over every model — users, courses, quizzes, certificates, site
  settings, contact messages

**Portal** (`/portal` — Next.js 14, TypeScript)
- Navbar: Home / AI Tutor / language switcher (English, Amharic, Afaan
  Oromo, Tigrinya) / a single "Sign in" button for guests, full dashboard
  access after auth
- Auth modal: email sign-in/up + "Continue with Google"
- Footer: address, phone, email, bank + Telebirr support info, working
  "Contact Us" form — all sourced from the backend site-settings API
- Functional course search in the navbar
- Course browsing, detail pages, lesson viewer, quiz-taking (unlimited
  retry attempts, pass/fail messaging)
- Instructor course-builder: thumbnail upload, topic/subtitle/description
  (rich text: bold/italic/lists/alignment/color)/notes with toggle,
  category dropdown, instructor name+photo, first lesson with
  video/text/pdf/slides/paste-URL/file-upload, a quiz builder (N questions
  each worth 100/N%, configurable pass threshold), and "add another lesson"
  / "add another module"
- Instructor course-edit page: edit every course field **plus** a full
  curriculum manager (add/edit/delete sections, lessons, quiz
  questions/choices on an already-created course)
- Profile page: avatar upload, certificates list, resend-verification
- Student dashboard: enrolled courses with progress bars

Both were verified working end-to-end:
- Backend: a comprehensive Django test-client smoke test covering
  register→verify-email→login, cross-instructor permission boundaries,
  the full quiz pass-to-unlock flow, avatar/thumbnail absolute-URL uploads,
  and the site-settings/contact endpoints.
- Portal: `npm run build` completes cleanly with zero errors.

## Running it

**Backend:**
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DB, OPENAI_API_KEY, GOOGLE_OAUTH_CLIENT_ID, EMAIL_* etc.
python3 manage.py migrate
python3 manage.py createsuperuser
python3 manage.py runserver
```

**Portal:**
```bash
cd portal
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_GOOGLE_CLIENT_ID
npm run dev
```

## Still open / next steps

- Real vector DB for AI Tutor RAG (currently a keyword-overlap stub)
- Payments (Telebirr, CBE, Stripe/PayPal) — footer already shows the manual
  bank/Telebirr details, but no automated checkout flow yet
- Full translation of all page copy into Amharic/Afaan Oromo/Tigrinya (the
  i18n system is wired up; only a subset of strings are translated so far)
- A custom-branded admin panel inside the portal itself, if you want
  something nicer than Django's default admin for day-to-day content
  editing (currently Django admin covers all CRUD needs)
- Startup incubator, mentor marketplace, investor connect, job board, and
  other Phase 3/4 modules from the PRD
