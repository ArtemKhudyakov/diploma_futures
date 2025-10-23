.PHONY: build up down logs shell migrate collectstatic superuser clean setup

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f web

logs-all:
	docker-compose logs -f

shell:
	docker-compose exec web python manage.py shell

migrate:
	docker-compose exec web python manage.py migrate

collectstatic:
	docker-compose exec web python manage.py collectstatic --noinput

superuser:
	docker-compose exec web python manage.py create_superuser

celery-logs:
	docker-compose logs -f celery

celery-beat-logs:
	docker-compose logs -f celery-beat

db-shell:
	docker-compose exec db psql -U postgres -d futures_screener

restart:
	docker-compose restart

clean:
	docker-compose down -v
	docker system prune -f

setup: build up
	@echo "⏳ Waiting for services to start..."
	@sleep 10
	@echo "✅ Setup complete! Access at http://localhost:8000"
	@echo "📊 API Docs: http://localhost:8000/swagger/"
	@echo "🔧 Admin: http://localhost:8000/admin/"

dev:
	docker-compose up

stop:
	docker-compose stop