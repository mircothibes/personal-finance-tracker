.PHONY: run gui db-up db-down migrate revision seed-categories seed-accounts shell logs

# Run the local GUI (outside of Docker, with your venv active)
run gui:	
	python -m app.gui

# Start/stop docker-compose services
db-up:
	docker compose up -d

db-down:
	docker compose down

# Alembic
revision:
	alembic revision -m "update" --autogenerate

migrate:
	alembic upgrade head

# Seeds
seed-categories:
	python scripts/seed_categories.py

seed-accounts:
	python scripts/seed_accounts.py

# Utilidades
shell:
	docker compose exec app bash

logs:
	docker compose logs -f













