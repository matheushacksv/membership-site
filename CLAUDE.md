# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

### Backend
- Python 3.13, Django 6.0, `django-ninja` 1.6 + `django-ninja-jwt` for the HTTP API.
- PostgreSQL via `psycopg` (settings load from env with `python-decouple`).
- `django-q2` for async task queue (welcome emails, password reset emails).
- `uv` manages the backend virtualenv (`backend/.venv`, `backend/pyproject.toml`, `backend/uv.lock`).
- `docker-compose.yml` at the repo root provisions Postgres for local dev.

### Frontend
- Nuxt 4 + Vue 3 (Composition API, `<script setup>`).
- TailwindCSS v4 via `@tailwindcss/vite`.
- `lucide-vue-next` for icons, `vuedraggable@next` + `sortablejs` for drag-and-drop in admin.
- Custom composables (no Pinia): `useApi`, `useAuth`, `useMe`, `useCatalog`, `useCourse`, `useAdmin`, `useProfile`, `useComments`, `useToast`.

## Commands

### Backend (from `backend/`)
```bash
uv sync                                              # install deps
docker compose up -d                                 # start Postgres (run from repo root)
uv run python manage.py makemigrations <app>         # always scope to one app
uv run python manage.py migrate
uv run python manage.py runserver
uv run python manage.py qcluster                     # run django-q worker (separate terminal)
uv run python manage.py shell
uv run python manage.py test <app>                   # pytest not configured
```

### Frontend (from `frontend/`)
```bash
npm install
npm run dev       # default port 3001
npm run build
```

### Env vars
Backend `.env` (no `.env.example` committed):
- DB: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- Django: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` (comma-separated)
- Frontend link: `FRONTEND_URL` (used in reset/welcome emails)
- Email (SMTP): `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`
- Integrations: `KIWIFY_WEBHOOK_TOKEN`

Frontend `.env`: `NUXT_PUBLIC_API_BASE` (e.g. `http://localhost:8000/api`).

## Architecture

Single Django project `core/` with feature apps as siblings: `accounts`, `courses`, `enrollments`, `integrations`. API surface is **django-ninja**, not DRF — keep that in mind when adding endpoints.

### API wiring

- `core/api.py` instantiates a single `NinjaAPI(auth=JWTAuth())` — **every route is JWT-authenticated by default**. Public endpoints (register/login/refresh, webhooks, password reset) must opt out with `auth=None` on the decorator.
- Per-app routers live in `<app>/api.py` and are mounted via `api.add_router("/<prefix>", router)` in `core/api.py`. Currently mounted: `/auth`, `/catalog`, `/admin`, `/enrollments`, `/integrations`.
- To add a new app to the API, create `<app>/api.py` with a `Router(tags=[...])` and register it.
- `core/urls.py` only exposes `/dj-admin/` (Django admin — moved off `/admin/` so the Nuxt SPA admin can own `/admin/*` behind Caddy) and `/api/` — no DRF urls, no app-level `urls.py`.
- Pydantic-style request/response shapes live in `<app>/schemas.py`. Shared error shape: `core.utils.errors.Error`.
- Staff-only endpoints call `core.utils.permissions.staff_required(request)` which raises `HttpError(403)`.

### Auth model

- Custom user `accounts.User` (set as `AUTH_USER_MODEL = 'accounts.User'`) extends `AbstractBaseUser` with `email` as `USERNAME_FIELD`. Custom `UserManager.create_user` hashes via `set_password`.
- Fields: `email`, `name`, `phone`, `avatar`, `is_staff`, `is_active`.
- JWT issuance uses `ninja_jwt.tokens.RefreshToken.for_user(user)`. Lifetimes: 30 min access / 7 day refresh (`NINJA_JWT` in `core/settings.py`).
- Inside a view, the authenticated principal is `request.auth` (a User instance), not `request.user`.
- Password reset: `urlsafe_base64_encode(force_bytes(user.pk))` + `default_token_generator.make_token(user)`. Frontend route `/reset-password?uid=<>&token=<>`. uid like `NQ` (no padding) is the standard base64url encoding of small ints — not a bug.

### Domain apps

- **accounts**: User model, auth endpoints (`/auth/login`, `/auth/register`, `/auth/refresh`, `/auth/me`, `/auth/me/avatar`, password reset flow), staff user management (`/auth/admin/users`, bulk-import, resend-welcome). Async email tasks in `accounts/tasks.py`: `send_welcome_email`, `send_welcome_email_with_reset`.
- **courses**: `Course` → `Module` → `Lesson` hierarchy + `Attachment` per lesson. `Course` has `kiwify_product_id` (mapping for webhook) and `access_days` (null = vitalício). Catalog endpoints (`/catalog`) and admin CRUD (`/admin/courses`, `/admin/modules`, `/admin/lessons`, attachments, reorder endpoints).
- **enrollments**: `CourseEnrollment(user, course, is_active, expires_at, source, external_order_id)`. Unique on `(user, course)`. `source` is `'kiwify' | 'admin' | 'manual'`. Endpoints under `/enrollments`.
- **integrations**: Kiwify webhook at `POST /api/integrations/kiwify/webhook?signature=<token>` (auth=None, query-param token comparison against `KIWIFY_WEBHOOK_TOKEN`). Events: `order_approved` → create user (if new) + enrollment + send welcome/reset email; `order_refunded` / `chargeback` → set enrollment inactive. Staff-only `GET /integrations/kiwify/config` exposes token to the admin UI.

### Frontend layout

- `app/pages/` — file-based routing. Top-level: `index.vue` (student catalog), `course.vue` (course view with sidebar), `profile.vue`, `auth.vue`, `login.vue`, `register.vue`, `forgot-password.vue`, `reset-password.vue`. Admin routes under `app/pages/admin/*`.
- `app/middleware/auth.global.ts` enforces auth on all routes except the public ones.
- `app/middleware/admin.ts` gates admin routes by `is_staff`.
- `app/composables/useApi.ts` wraps `$fetch` with the JWT, base URL, and refresh-on-401 logic.

### Type checking

`django-stubs` is a declared dep. Models use `TextChoices` with tuple-literal syntax (`SALES = "sales", "Vendas"`); without the stubs / a stubs-aware checker, pyright flags these as `tuple` → `str` mismatches.

## Conventions

- Endpoint handlers return `Status(<code>, <schema_instance>)` for non-200 responses; the response map in the decorator must list every status code used (e.g. `response={200: TokenOut, 404: Error, 401: Error}`).
- Migrations are committed per app under `<app>/migrations/`. Always run `makemigrations <app>` scoped to the app you changed.
- Multipart uploads on the frontend: build `FormData` and pass as `body` — do NOT set `Content-Type` manually (let the browser set the boundary).
- Secrets (`KIWIFY_WEBHOOK_TOKEN`, etc.) must never be exposed via public Nuxt `runtimeConfig.public`. Fetch via staff-authenticated endpoint when the admin UI needs them.
- When implementing a destructive or external-state-changing webhook handler, always guard with `get_or_create(user=..., course=...)` (both fields) — filtering by one side alone can return multiple rows and raise `MultipleObjectsReturned`.
