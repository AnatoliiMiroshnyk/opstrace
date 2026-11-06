.PHONY: install install-dev run migrate makemigrations test lint format check scheduler collectstatic superuser compose-up compose-down

install:
	python -m pip install -r requirements/base.txt

install-dev:
	python -m pip install -r requirements/dev.txt

run:
	python manage.py runserver

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

test:
	pytest --cov=apps

lint:
	ruff check .

format:
	ruff format .

check:
	python manage.py check
	python manage.py makemigrations --check --dry-run
	ruff check .

scheduler:
	python manage.py generate_work_items

collectstatic:
	python manage.py collectstatic --noinput

superuser:
	python manage.py createsuperuser

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down
