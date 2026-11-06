# OpsTrace

**Evidence-based recurring operations management for small teams.**

[Русская документация](README.ru.md) · [Architecture](docs/architecture.md)

OpsTrace helps a team define recurring operational procedures, generate work items on a schedule, attach evidence of execution, review the result, and retain an append-only activity history.

> Product language: Ukrainian. Source code, domain names, and technical documentation: English.

## Why OpsTrace exists

A normal task list tells a team what should be done. It does not reliably establish what was done, who was responsible, what evidence supports completion, or who accepted the result. OpsTrace models that missing control loop.

A routine (for example, “inspect the backup appliance every Monday”) creates dated work items. The assignee performs the work and attaches one or more PDF/image files. A reviewer approves the result or returns it with a required explanation. Every material transition is recorded in an audit event.

The implementation in this repository is an original product concept and codebase. It is not a claim that no similar software exists anywhere.

## Core capabilities

- **Workspace isolation:** every operational record belongs to a workspace; the active workspace is resolved from a database-backed membership, not trusted from a session value alone.
- **Role-based access:** owner, administrator, reviewer, and member roles.
- **Recurring routines:** daily, weekly, monthly, quarterly, and yearly schedules.
- **Idempotent task generation:** `generate_work_items` can be run repeatedly; a database unique constraint prevents duplicate occurrences.
- **Evidence-based execution:** PDF, PNG, JPG/JPEG, and WEBP attachments, limited to 10 MB per file; the SHA-256 digest is stored with the evidence metadata.
- **Review lifecycle:** open → in progress → submitted → approved/rejected. Rejected work can be resumed and submitted again.
- **Append-only audit events:** routine creation/updates, generated items, work start, evidence upload, submission, and review decisions.
- **Private file delivery:** uploads are not exposed through a public `/media/` URL; downloads pass through a workspace-scoped view.
- **Operational dashboard:** overdue, in-progress, submitted, and upcoming work.
- **Quality baseline:** tests, linting, Docker, PostgreSQL, environment-based configuration, and GitHub Actions.

## Roles and access

| Capability | Owner | Admin | Reviewer | Member |
|---|:---:|:---:|:---:|:---:|
| View workspace routines | Yes | Yes | Assigned routines | Assigned routines |
| Create/edit routines | Yes | Yes | No | No |
| Manage team members | Yes | Yes | No | No |
| View all workspace work items | Yes | Yes | Yes | No, assigned only |
| Start/execute own assigned work | Yes | Yes | If assigned | If assigned |
| Review submitted work | Yes | Yes | Yes | No |
| Attach evidence | If assigned / manager | If assigned / manager | If assigned / manager | If assigned |

**Adding people:** in this version, an administrator adds an existing OpsTrace account by email. The invited person must register first. Email invitation tokens and automated notifications are intentionally left as a future extension rather than shipping an unverified invitation flow.

## Work-item lifecycle

```text
OPEN
  │ assignee starts
  ▼
IN_PROGRESS
  │ at least one evidence file is attached
  │ assignee submits
  ▼
SUBMITTED ── reviewer approves ──> APPROVED
  │
  └──────── reviewer rejects ───> REJECTED
                                     │
                                     └── assignee resumes → IN_PROGRESS
```

A submission is rejected by the service layer if no evidence exists. A rejection must include a comment, and the submitter cannot review their own result. State transitions are transaction-wrapped and write an audit event.

## Technology

- Python 3.14 (Python 3.12+ is declared in package metadata)
- Django 6.1.2
- PostgreSQL 17 in Docker Compose; SQLite fallback for local development
- Django Templates + responsive CSS (no Node build chain)
- Gunicorn + WhiteNoise
- `django-environ` for environment settings
- Pytest, pytest-django, pytest-cov, Ruff
- Docker Compose and GitHub Actions

## Quick start — Docker (recommended)

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set strong, unique values for `SECRET_KEY` and `POSTGRES_PASSWORD`. Ensure the password in `DATABASE_URL` matches `POSTGRES_PASSWORD`.

For a local Docker launch, the example values `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, and `SECURE_SSL_REDIRECT=False` are suitable for `http://localhost:8000`. Do not reuse these development settings in production.

### 2. Build and start

```bash
docker compose up --build -d
```

The web container applies migrations, collects static assets, and starts Gunicorn. The scheduler container runs the idempotent task-generation command once per hour.

### 3. Create an administrator

```bash
docker compose exec web python manage.py createsuperuser
```

Then open:

- Application: <http://localhost:8000>
- Django admin: <http://localhost:8000/admin/>
- Health endpoint: <http://localhost:8000/health/>

Register the first workspace through the application. The first registered user becomes its owner. The Django superuser is for platform administration and does not automatically get a workspace membership; register a normal owner account for day-to-day use.

### 4. Generate due work items immediately

The scheduler runs hourly. To generate tasks on demand:

```bash
docker compose exec web python manage.py generate_work_items
```

To backfill occurrences up to a specific date:

```bash
docker compose exec web python manage.py generate_work_items --through 2026-11-03
```

The command creates all missing occurrences from each active routine's `next_due_date` through the requested date, then advances the next occurrence. It does not create future occurrences beyond the requested date.

## Local development without Docker

### 1. Create a virtual environment

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate
```

### 2. Install dependencies and configure the environment

```bash
python -m pip install -r requirements/dev.txt
cp .env.example .env
```

For SQLite-based local development, remove or comment out `DATABASE_URL` in `.env`. Django will then use `db.sqlite3`. Keep `DEBUG=True` and `SECURE_SSL_REDIRECT=False` locally.

### 3. Apply migrations and start the server

```bash
python manage.py migrate
python manage.py runserver
```

In a second terminal, create routine occurrences when needed:

```bash
python manage.py generate_work_items
```

## Tests and code quality

```bash
# All tests with coverage
pytest --cov=apps

# Static linting
ruff check .

# Django checks and migration drift detection
python manage.py check
python manage.py makemigrations --check --dry-run
```

Or use the `Makefile` shortcuts: `make install-dev`, `make run`, `make test`, `make lint`, `make check`.

## Repository structure

```text
opstrace/
├── apps/
│   ├── accounts/          # Email-based custom user and registration
│   ├── core/               # Dashboard and health endpoint
│   ├── operations/         # Routines, work items, evidence, audit, scheduler
│   └── workspaces/         # Workspaces, memberships, middleware, RBAC, team UI
├── config/                 # Django settings, URL routing, WSGI/ASGI
├── docs/                   # Architecture, deployment and commit plan
├── requirements/           # Runtime and development dependencies
├── static/css/             # Responsive application styles
├── templates/               # Django templates
├── tests/                   # Cross-app workflow and isolation tests
├── .github/workflows/       # CI pipeline
├── Dockerfile
├── docker-compose.yml
├── manage.py
├── pyproject.toml
└── README.md
```

## Important environment variables

| Variable | Purpose | Example |
|---|---|---|
| `SECRET_KEY` | Django cryptographic secret | long random string |
| `DEBUG` | Development debug mode | `False` in production |
| `ALLOWED_HOSTS` | Allowed hostnames | `app.example.com` |
| `DATABASE_URL` | Database connection | `postgres://user:pass@host:5432/db` |
| `CSRF_TRUSTED_ORIGINS` | Trusted HTTPS origins | `https://app.example.com` |
| `SECURE_SSL_REDIRECT` | Force HTTPS | `True` in production |
| `SECURE_HSTS_SECONDS` | HSTS max age | set after TLS validation |
| `EMAIL_BACKEND` | Outbound mail backend | SMTP backend in production |
| `DEFAULT_FROM_EMAIL` | Sender address | `OpsTrace <noreply@example.com>` |
| `LOG_LEVEL` | Application log level | `INFO` |

## Production deployment checklist

This repository is a production-minded application baseline, not a substitute for an environment-specific security and operations review. Before exposing it to real customer data:

1. Set `DEBUG=False`, rotate `SECRET_KEY`, set strict `ALLOWED_HOSTS`, and configure HTTPS at a trusted reverse proxy.
2. Set `SECURE_SSL_REDIRECT=True`, secure cookies, an appropriate HSTS policy, and exact `CSRF_TRUSTED_ORIGINS`.
3. Use managed PostgreSQL with automated backups, restore drills, monitoring, and least-privilege credentials.
4. Move evidence files to private object storage (S3-compatible or equivalent), retain private download authorization, and configure lifecycle/backup policies.
5. Add malware scanning and content-type inspection for uploads. The current allowlist checks file extensions and size; it is not an antivirus scanner.
6. Configure SMTP, email verification, invitation links, password reset delivery, and notification policies.
7. Configure centralized logs, error reporting, metrics, alerting, and an external uptime monitor.
8. Run dependency/security scanning, a penetration test, and a review of data-retention/privacy requirements.
9. Back up and test restoration of both PostgreSQL and evidence storage.
10. Put the app behind a TLS-enabled reverse proxy and do not expose the database port publicly.

The Docker Compose configuration is intended for local evaluation and small controlled deployments. A managed production deployment should use separate web and scheduler processes, secret management, durable private object storage, and an explicit backup/restore runbook.

## Current scope and deliberate next steps

Included now: the end-to-end routine → work item → evidence → review → audit loop, workspace isolation, a simple team panel, private evidence retrieval, PostgreSQL and automated checks.

Natural next increments: signed invitation/acceptance flow, email notifications and reminders, timezone-aware per-workspace schedules, configurable due-date grace windows, object storage, malware scanning, CSV/SARIF-style audit exports, API endpoints, and organization-level retention policies. These are not represented as implemented features in this version.

## License

MIT. See [LICENSE](LICENSE).
