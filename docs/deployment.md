# Deployment runbook

## Local Docker Compose

1. Copy `.env.example` to `.env`.
2. Set `SECRET_KEY` and `POSTGRES_PASSWORD` to unique values.
3. Make the `DATABASE_URL` password match `POSTGRES_PASSWORD`.
4. Run `docker compose up --build -d`.
5. Create a Django superuser with `docker compose exec web python manage.py createsuperuser`.
6. Register an ordinary user through the web UI to create the first workspace and become its owner.
7. Verify `/health/` and create a routine. Run `docker compose exec web python manage.py generate_work_items` for immediate generation.

## Updating an existing deployment

```bash
git pull
docker compose build --pull
docker compose up -d
```

The web command applies migrations before starting Gunicorn. For significant schema changes, take a database backup first and review migration operations before deployment.

## Database backup example

For a local Compose database:

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

Restore into a prepared database:

```bash
cat backup.sql | docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

Set `POSTGRES_USER` and `POSTGRES_DB` in the shell before running these commands. Back up the evidence volume separately; a database dump does not contain uploaded files.

## Operational notes

- Do not rely on `DEBUG=True` in a public environment.
- Configure TLS termination and pass the correct `X-Forwarded-Proto` header only from a trusted proxy.
- Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to exact hostnames/origins.
- Keep PostgreSQL private; only the web process and scheduler should connect.
- Monitor scheduler logs and alert if generation repeatedly fails.
- Test database and evidence restore procedures before onboarding customers.
