.PHONY: help install dev prod test clean migrate seed

help:
	@echo "LSuite - Available Commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Run development server"
	@echo "  make prod       - Run production server with Gunicorn"
	@echo "  make docker     - Build and run with Docker Compose"
	@echo "  make test       - Run tests"
	@echo "  make migrate    - Run database migrations"
	@echo "  make seed       - Seed database with default data"
	@echo "  make clean      - Clean up temporary files"

install:
	pip install -r requirements.txt

dev:
	flask run --debug

prod:
	gunicorn -w 4 -b 0.0.0.0:5000 app:app

docker:
	docker-compose up -d --build

docker-logs:
	docker-compose logs -f

docker-down:
	docker-compose down

test:
	pytest tests/ -v --cov=lsuite

migrate:
	flask db upgrade

seed:
	flask seed-categories

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete

