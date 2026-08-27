# Área de Membros

Plataforma de área de membros para cursos online. Suporta catálogo, matrículas (manual e via webhook Kiwify), reprodução de vídeo-aulas com módulos, comentários, anexos, painel admin e gerenciamento de usuários.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.13, Django 6.0, django-ninja 1.6, django-ninja-jwt |
| Tarefas async | django-q2 (broker Redis) |
| Banco | PostgreSQL 16 |
| Mídia | MinIO/S3 (via `django-storages` + `boto3`) |
| Frontend | Nuxt 4 + Vue 3 (Composition API) |
| Estilo | TailwindCSS 4 |
| Reverse proxy | Caddy 2 (TLS automático) |
| Orquestração | Docker Compose |

## Arquitetura

```
┌──────────┐
│  Caddy   │  :80/:443 (TLS auto via Let's Encrypt)
└────┬─────┘
     │
     ├── /api/*,/dj-admin/*  →  backend  (Django + gunicorn)
     ├── /static/*           →  volume (collectstatic)
     └── /*                  →  frontend (Nuxt SSR, inclui SPA admin em /admin/*)

backend  ─→ db (Postgres)
         ─→ redis (broker django-q)
         ─→ MinIO/S3 externo (upload de avatar, capa de curso, anexos)

worker (django-q qcluster) consome tarefas: envio de email (welcome, reset).
```

### Apps Django

- `accounts`: usuário custom (`AbstractBaseUser`, `email` como `USERNAME_FIELD`), auth JWT, gerenciamento de usuários staff
- `courses`: `Course` → `Module` → `Lesson` → `Attachment`. Catálogo público + CRUD admin.
- `enrollments`: `CourseEnrollment(user, course)` com `is_active`, `expires_at`, `source`, `external_order_id`
- `integrations`: webhook Kiwify (`/api/integrations/kiwify/webhook`) que mapeia `kiwify_product_id` → curso, cria usuário + matrícula em `order_approved`, revoga em `order_refunded`/`chargedback`

## Pré-requisitos

- Docker + Docker Compose
- Python 3.13 + [uv](https://docs.astral.sh/uv/) (dev local sem Docker)
- Node 22+ (dev local sem Docker)
- Instância MinIO/S3 acessível pela URL pública configurada

## Setup

### 1. Clone e env vars

```bash
git clone <repo>
cd new_area
cp backend/.env.example backend/.env       
cp frontend/.env.example frontend/.env
```

#### `backend/.env`

```
# Django
SECRET_KEY=<random>
DEBUG=False
ALLOWED_HOSTS=hosts
CSRF_TRUSTED_ORIGINS=hosts
CORS_ALLOWED_ORIGINS=hosts
FRONTEND_URL=hosts

# Postgres
POSTGRES_DB=db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<senha>
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis (broker django-q)
REDIS_HOST=redis
REDIS_PORT=6379

# MinIO/S3
MINIO_ENDPOINT_URL=https://minio.seu-servidor.com
MINIO_ACCESS_KEY=<key>
MINIO_SECRET_KEY=<secret>
MINIO_BUCKET_NAME=name

# SMTP (envio de email)
EMAIL_HOST=smtp.seu-provedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=<user>
EMAIL_HOST_PASSWORD=<password>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=no-reply@seu-dominio.com

# Integrações
KIWIFY_WEBHOOK_TOKEN=<token-aleatório>
```

#### `frontend/.env`

```
NUXT_PUBLIC_API_BASE=host
```

Em dev local: `http://localhost:8000/api`.

### 2. Subir via Docker Compose (produção)

```bash
docker compose up -d db redis
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py createsuperuser
docker compose up -d
```

### 3. Dev local (sem Docker)

**Backend:**
```bash
cd backend
uv sync
docker compose up -d db redis           # só infra
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver       # :8000
uv run python manage.py qcluster        # worker, terminal separado
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev                              # :3001
```

## Comandos úteis

### Backend (de `backend/`)

```bash
uv sync                                          # instala/atualiza deps
uv run python manage.py makemigrations <app>     # sempre escopado ao app
uv run python manage.py migrate
uv run python manage.py shell
uv run python manage.py test <app>               # pytest não configurado
uv run python manage.py collectstatic --noinput  # gera STATIC_ROOT
uv run python manage.py qcluster                 # worker django-q
```

### Frontend (de `frontend/`)

```bash
npm install
npm run dev
npm run build
npm run preview
```

### Docker

```bash
docker compose ps
docker compose logs -f <service>
docker compose exec backend uv run python manage.py shell
docker compose exec caddy caddy validate --config /etc/caddy/Caddyfile
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
docker compose down            # mantém volumes
docker compose down -v         # apaga volumes (Postgres, static, caddy_data)
```

## Estrutura do projeto

```
new_area/
├── backend/
│   ├── accounts/         # User custom, auth, gerenciamento de usuários
│   ├── courses/          # Course, Module, Lesson, Attachment
│   ├── enrollments/      # CourseEnrollment
│   ├── integrations/     # Kiwify webhook
│   ├── core/             # settings, urls, api, wsgi/asgi
│   ├── pyproject.toml
│   ├── uv.lock
│   └── Dockerfile
├── frontend/
│   ├── app/
│   │   ├── components/   # AppLogo, AppHeader, etc
│   │   ├── composables/  # useApi, useAuth, useMe, useCatalog, useAdmin...
│   │   ├── middleware/   # auth.global.ts, admin.ts
│   │   ├── pages/        # rotas baseadas em arquivo
│   │   └── layouts/
│   ├── public/           # favicon, ícones PWA
│   ├── nuxt.config.ts
│   └── Dockerfile
├── docker-compose.yml
├── Caddyfile
├── CLAUDE.md             # instruções pro Claude Code
└── README.md
```

## Integração Kiwify

1. No painel da Kiwify, configure webhook apontando para:
   ```
   https://<dominio>/api/integrations/kiwify/webhook?signature=<KIWIFY_WEBHOOK_TOKEN>
   ```
2. No admin do curso (`/admin/courses/<id>/edit`), preencha:
   - **Kiwify Product ID**, ID do produto na Kiwify
   - **Dias de acesso**, opcional, vazio = vitalício
3. Eventos tratados:
   - `order_approved` → cria usuário (se novo), matrícula com `expires_at`, envia email de boas-vindas com link de definir senha
   - `order_refunded` / `chargedback` → desativa matrícula (`is_active=False`)

## Deploy

1. DNS: aponta `A/AAAA` do domínio pro IP do servidor
2. Cria `backend/.env` + `frontend/.env` no servidor
3. `docker compose up -d`
4. Migrate + createsuperuser conforme acima
5. Caddy pega cert Let's Encrypt no primeiro request HTTPS

## Convenções

- Todo endpoint API herda `JWTAuth()` por padrão, public (`register`, `login`, `refresh`, webhook, reset) opta out com `auth=None`.
- Em uma view, principal autenticado é `request.auth` (não `request.user`).
- Migrations sempre escopadas: `makemigrations <app>`.
- Multipart upload no frontend: monte `FormData`, não setar `Content-Type` (browser cuida do boundary).
- Não exponha segredos via `runtimeConfig.public`; busque via endpoint staff-only.

## Licença

Privado.
