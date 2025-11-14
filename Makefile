.PHONY: help up down logs app-shell seed-categories seed-accounts gui alembic-revision alembic-upgrade

help:
	@echo "Available commands:"
	@echo "  make up               - Start Docker containers (db + app)"
	@echo "  make down             - Stop Docker containers"
	@echo "  make logs             - Show app container logs"
	@echo "  make app-shell        - Open shell inside app container"
	@echo "  make seed-categories  - Run categories seed script inside container"
	@echo "  make seed-accounts    - Run accounts seed script inside container"
	@echo "  make gui              - Run local GUI (python -m app.gui)"
	@echo "  make alembic-revision - Create new Alembic revision (auto)"
	@echo "  make alembic-upgrade  - Apply Alembic migrations (upgrade head)"

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f app

app-shell:
	docker compose exec app bash

seed-categories:
	docker compose exec app python scripts/seed_categories.py

seed-accounts:
	docker compose exec app python scripts/seed_accounts.py

gui:
	python -m app.gui

alembic-revision:
	docker compose exec app alembic revision --autogenerate -m "auto"

alembic-upgrade:
	docker compose exec app alembic upgrade head













