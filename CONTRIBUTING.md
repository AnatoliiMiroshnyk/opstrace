# Contributing

## Development setup

- Use Python 3.12 or newer (Python 3.14 is the default runtime target).
- Create a virtual environment and install `requirements/dev.txt`.
- Copy `.env.example` to `.env`; remove `DATABASE_URL` to use SQLite locally.
- Apply migrations with `python manage.py migrate`.

## Before opening a pull request

```bash
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest --cov=apps
```

## Engineering expectations

- Keep tenant scoping explicit in every view and service.
- Put business transitions in `apps.operations.services`, not in templates or ad hoc view code.
- Add a regression test for every authorization or lifecycle rule.
- Use atomic transactions for state changes that must be consistent with audit events.
- Do not expose uploaded evidence through public media URLs.
- Add migrations for model changes and review them before committing.
- Never commit `.env`, customer data, database dumps, or uploaded evidence.
- Keep documentation honest: describe shipped behavior separately from future work.

## Pull request checklist

- [ ] Tests added or updated.
- [ ] Tenant boundary and role checks reviewed.
- [ ] Migrations generated and checked.
- [ ] Lint and format checks pass.
- [ ] User-visible behavior documented.
- [ ] No secrets or personal data added.
