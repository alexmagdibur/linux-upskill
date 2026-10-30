# Linux Upskill — локальная разработка. Linux/macOS: `make`; Windows: WSL2 (или команды из README).
SHELL := /bin/bash
ROOT := $(CURDIR)
ifeq ($(OS),Windows_NT)
  VENV_BIN := .venv/Scripts
  PYTHON_BOOT ?= py -3.13
else
  VENV_BIN := .venv/bin
  PYTHON_BOOT ?= python3
endif
PY := $(VENV_BIN)/python
COMPOSE := docker compose -f infra/compose/docker-compose.yml

.PHONY: help setup images up down migrate seed api worker web dev test test-api test-worker test-web lint typecheck \
        e2e load-test openapi clean-sandboxes logs-clean

help:  ## список целей
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ —/' | sort

setup:  ## venv, зависимости Python и npm, образ песочницы, .env
	test -f .env || cp .env.example .env
	test -d .venv || $(PYTHON_BOOT) -m venv .venv
	$(PY) -m pip install -U pip
	$(PY) -m pip install -e packages/upskill_content -e "apps/api[dev]" -e "apps/sandbox-worker[dev]"
	cd apps/web && npm ci
	$(MAKE) images

images:  ## собрать образы песочниц и зафиксировать их ID в content/images.lock.json
	$(PY) infra/scripts/build_images.py

up:  ## PostgreSQL + Redis в Docker (порты только на 127.0.0.1)
	$(COMPOSE) up -d --wait
	-$(COMPOSE) exec -T postgres psql -U upskill -d upskill -tc "SELECT 1 FROM pg_database WHERE datname='upskill_test'" | grep -q 1 || \
	  $(COMPOSE) exec -T postgres psql -U upskill -d upskill -c "CREATE DATABASE upskill_test"

down:  ## остановить инфраструктуру
	$(COMPOSE) down

migrate:  ## применить миграции Alembic
	cd apps/api && ../../$(PY) -m alembic upgrade head

seed:  ## импортировать каталог из content/ (курс, 20 лабораторий)
	cd apps/api && ../../$(PY) -m app.seed

api:  ## API на http://localhost:8000 (OpenAPI: /docs)
	cd apps/api && ../../$(PY) -m uvicorn app.main:app --port 8000 --reload

worker:  ## sandbox worker (единственный компонент с доступом к Docker)
	cd apps/sandbox-worker && ../../$(PY) -m worker.main

web:  ## frontend на http://localhost:5173
	cd apps/web && npm run dev

lint:  ## ruff + eslint
	cd apps/api && ../../$(PY) -m ruff check .
	cd apps/sandbox-worker && ../../$(PY) -m ruff check .
	$(PY) -m ruff check packages infra --config ruff.toml
	cd apps/web && npm run lint

typecheck:  ## mypy + tsc
	cd apps/api && ../../$(PY) -m mypy app
	cd apps/sandbox-worker && ../../$(PY) -m mypy worker
	cd apps/web && npm run typecheck

test-api:  ## тесты API (нужны PostgreSQL и Redis: make up)
	cd apps/api && ../../$(PY) -m pytest -q

test-worker:  ## тесты worker/песочниц/20 лабораторий (нужен Docker и собранный образ)
	cd apps/sandbox-worker && ../../$(PY) -m pytest -q

test-web:  ## unit-тесты frontend + сборка
	cd apps/web && npm test && npm run build

test: lint typecheck test-api test-worker test-web  ## всё, кроме E2E и нагрузки

e2e:  ## Playwright через UI (нужны запущенные api, worker; vite поднимется сам)
	cd apps/web && npx playwright install chromium && npx playwright test

load-test:  ## 10 одновременных песочниц (нужны запущенные api и worker)
	$(PY) infra/scripts/load_test.py

openapi:  ## выгрузить docs/api/openapi.json
	$(PY) infra/scripts/export_openapi.py

clean-sandboxes:  ## удалить ВСЕ контейнеры песочниц (метка upskill.managed=true)
	docker ps -aq --filter label=upskill.managed=true | xargs -r docker rm -f
