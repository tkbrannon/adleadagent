.PHONY: help install dev test clean docker-up docker-down deploy

help:
	@echo "Mesh Cowork Lead Agent - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Run all services locally"
	@echo "  make test         - Run test suite"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up    - Start all services with Docker Compose"
	@echo "  make docker-down  - Stop all services"
	@echo "  make docker-logs  - View logs"
	@echo ""
	@echo "Testing:"
	@echo "  make test-parser  - Test email parser"
	@echo "  make test-twilio  - Test Twilio connection"
	@echo "  make test-airtable - Test Airtable connection"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy       - Deploy to Digital Ocean"

install:
	python -m venv venv
	. venv/bin/activate && pip install -r requirements.txt
	@echo "✓ Dependencies installed"
	@echo "Run: source venv/bin/activate"

dev:
	@echo "Starting services..."
	@echo "Make sure Redis is running: redis-server"
	@echo ""
	@echo "Terminal 1: make run-api"
	@echo "Terminal 2: make run-celery"
	@echo "Terminal 3: make run-poller"

run-api:
	python app/main.py

run-celery:
	celery -A app.celery_app worker --loglevel=info

run-poller:
	python poller.py

docker-up:
	docker-compose up -d
	@echo "✓ Services started"
	@echo "View logs: make docker-logs"

docker-down:
	docker-compose down
	@echo "✓ Services stopped"

docker-logs:
	docker-compose logs -f

docker-restart:
	docker-compose restart

test-parser:
	python test_email_parser.py

test-twilio:
	python scripts/test_twilio.py

test-airtable:
	python scripts/test_airtable.py

test-call:
	python scripts/send_test_call.py

test: test-parser test-twilio test-airtable
	@echo "✓ All tests passed"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf logs/*.log
	@echo "✓ Cleaned up"

deploy:
	@echo "Deploying to Digital Ocean..."
	@echo "Make sure you've:"
	@echo "1. Pushed to GitHub"
	@echo "2. Updated .do/app.yaml with your repo"
	@echo "3. Set secrets in DO dashboard"
	@echo ""
	doctl apps create --spec .do/app.yaml

logs-api:
	tail -f logs/app.log

logs-poller:
	tail -f logs/poller.log

redis-cli:
	redis-cli

redis-monitor:
	redis-cli monitor
