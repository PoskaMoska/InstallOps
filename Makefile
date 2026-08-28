.PHONY: up down build logs test migrate make-migrations lint format shell

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

test:
	pytest tests/ -v

migrate:
	docker compose exec api alembic upgrade head

make-migrations:
	docker compose exec api alembic revision --autogenerate -m "auto"

lint:
	flake8 app/ tests/

format:
	black app/ tests/

shell:
	docker compose exec api bash
