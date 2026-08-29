.PHONY: install test lint dev seed compose-up compose-down

install:
	python -m pip install -r backend/requirements-dev.txt
	cd frontend && npm install

test:
	pytest
	cd frontend && npm run test -- --run

lint:
	ruff check backend scanners cbom_engine knowledge_graph risk_engine tests
	cd frontend && npm run typecheck

dev:
	uvicorn backend.app.main:app --reload --port 8000

seed:
	python -m backend.app.seed

compose-up:
	docker-compose up

compose-down:
	docker-compose down
