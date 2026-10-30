# Linux Upskill

Интерактивная веб-платформа для изучения Linux и DevOps: **Learn → Practice → Incident**. Пользователь работает в настоящем
shell внутри изолированной Linux-песочницы (xterm.js ⇄ WebSocket ⇄ PTY в контейнере), а независимый валидатор проверяет
**итоговое состояние системы**, начисляет XP и сохраняет прогресс.

> ⚠️ **Статус безопасности.** Контейнерная изоляция MVP подходит для локального использования и ограниченного доверенного
> тестирования. Не публикуйте в интернете без отдельного аудита и VM/microVM-изоляции. Подробности и список известных
> ограничений: [docs/security/README.md](docs/security/README.md).

## Что внутри

| Часть | Технологии |
|---|---|
| `apps/api` | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, PostgreSQL, Redis, Argon2id |
| `apps/sandbox-worker` | Python, Docker SDK, Redis Streams, внутренний WS-сервер PTY (отдельная граница доверия) |
| `apps/web` | React 18, TypeScript (strict), Vite, Tailwind 4, TanStack Query, xterm.js |
| `packages/upskill_content` | общая схема манифеста и загрузчик контента (API и worker) |
| `content/` | курс из 205 заданий: 162 запускаемых (75 в Docker-песочнице + 87 на учебной машине LXD) и 43 описанных |
| `sandbox-images/ubuntu-basic` | образ песочницы (Ubuntu 24.04, закреплён по digest) |
| `infra/` | docker compose, nginx, Prometheus, скрипты (e2e-smoke, нагрузочный тест, генератор контента) |

Архитектура: [docs/architecture/overview.md](docs/architecture/overview.md) · ADR: [docs/adr](docs/adr) ·
OpenAPI: [docs/api/openapi.json](docs/api/openapi.json) (живой Swagger — `http://localhost:8000/docs`).

## Требования

Docker (Docker Desktop с WSL2 на Windows), Python 3.12+ (проверено на 3.13), Node.js 22+ (проверено на 24), `make` (Linux/macOS/WSL2).

## Локальный запуск

### Linux / macOS / WSL2

```bash
cp .env.example .env
make setup      # venv, зависимости Python/npm, сборка образа песочницы + content/images.lock.json
make up         # PostgreSQL + Redis в Docker (127.0.0.1:15432 и 127.0.0.1:6379)
make migrate    # миграции Alembic
make seed       # импорт курса: 205 заданий (162 запускаются, 43 описаны)
# в трёх терминалах:
make api        # http://localhost:8000  (OpenAPI: /docs)
make worker     # sandbox worker (единственный компонент с доступом к Docker)
make web        # http://localhost:5173
```

Остановка: `make down` (инфраструктура), `make clean-sandboxes` (принудительно удалить контейнеры песочниц).

### Windows (PowerShell, Docker Desktop)

```powershell
./infra/scripts/dev.ps1 setup      # .env, venv, зависимости, образ песочницы
./infra/scripts/dev.ps1 up         # PostgreSQL + Redis
./infra/scripts/dev.ps1 migrate
./infra/scripts/dev.ps1 seed
./infra/scripts/dev.ps1 start      # api + worker + web в фоне (логи в .run\), затем http://localhost:5173
./infra/scripts/dev.ps1 stop
```

### Полный стек в контейнерах (nginx + api + worker + web)

```bash
make images                                                   # content/images.lock.json нужен для seed и worker
docker compose -f infra/compose/docker-compose.yml --profile full up -d --build
# интерфейс: http://localhost:8080 ; worker получает docker.sock хоста (см. раздел безопасности!)
```

### Порты

| Сервис | Адрес |
|---|---|
| Frontend (Vite) | http://localhost:5173 |
| API / OpenAPI | http://localhost:8000 · `/docs` |
| Worker (внутренний) | http://127.0.0.1:8100 |
| PostgreSQL | 127.0.0.1:**15432** (5432 на Windows часто зарезервирован ОС) |
| Redis | 127.0.0.1:6379 |

## Конфигурация

Все параметры — через ENV (см. `.env.example`): `DATABASE_URL`, `REDIS_URL`, `APP_SECRET`, `PUBLIC_ORIGIN`, `SANDBOX_RUNTIME`
(`docker` | `disabled`), `SANDBOX_MAX_CONCURRENT`, `SANDBOX_TTL_SECONDS`, `SANDBOX_IDLE_SECONDS`, `SANDBOX_CPU_LIMIT`,
`SANDBOX_MEMORY_LIMIT`, `INTERNAL_TOKEN` и др. `ENV=prod` включает строгие проверки секретов и `COOKIE_SECURE`.
`SANDBOX_RUNTIME=disabled` оставляет каталог и учётные записи работать, а запуск лабораторий отвечает `503 SANDBOX_DISABLED`.

## Тестирование

```bash
make up && make test      # ruff, mypy, eslint, tsc, pytest (API + worker), vitest, сборка web
make e2e                  # Playwright через UI (нужны запущенные api и worker)
make load-test            # 10 одновременных песочниц через настоящий API
# E2E и нагрузка регистрируют много пользователей: лимит регистрации 10/час с IP — запускайте API с RATE_LIMIT_ENABLED=false (или сбросьте ключи rl:* в Redis)
python infra/scripts/e2e_smoke.py     # сквозной сценарий без браузера
```

Что покрывают тесты:

- **API (`apps/api/tests`, PostgreSQL + Redis):** оценивание, автомат состояний, схема манифеста, регистрация/вход/refresh-ротация/CSRF,
  каталог, сессии, идемпотентность, лимиты, изоляция пользователей, XP (в т.ч. конкурентные запросы), sweeper, **WebSocket-шлюз** (ticket, Origin, владелец).
- **Worker (`apps/sandbox-worker/tests`, Docker + Redis):** свойства изоляции на живых контейнерах, очередь/retry/DLQ, PTY-hub
  (переподключение, Ctrl+C, лимит вывода), reconciler/TTL, и **для каждой из 75 запускаемых лабораторий — «пустое состояние / неверное решение не проходят, правильное (и альтернативные) проходят»**.
- **Frontend:** vitest + Playwright (регистрация → каталог → запуск → терминал → проверка → XP → повторный вход, переподключение к тому же shell, изоляция пользователей, остановка, мобильная раскладка).

## Контент

Курс — **205 заданий** учебной программы в четырёх этапах (новичок 17, джун 44, мидл 87, синьор 57); подробности и покрытие по темам — [docs/architecture/learning-program.md](docs/architecture/learning-program.md).
**Запускаются 162**: 75 в Docker-песочнице и **87 на учебной машине** (системный контейнер LXD с настоящим systemd на отдельной VM-хосте; сеть и «несколько узлов» — на network namespace, см. [docs/architecture/vm-labs.md](docs/architecture/vm-labs.md)). **Описаны, но не запускаются 43**: 25 с письменным результатом (проект, план, разбор — автопроверка была бы недостоверной), 9 требуют контейнерный runtime внутри машины (Docker/podman, отключено ради изоляции) и 9 не удалось воспроизвести детерминированно. **27 уроков исключены из курса**: они требуют настоящей VM со своим ядром (загрузка, ядро, LVM/RAID, блочные устройства), см. [docs/architecture/excluded-lessons.md](docs/architecture/excluded-lessons.md). Нумерация уроков сквозная, идентификаторы заданий (`ld-NNN`) стабильны.
Формат лаборатории — `content/labs/<id>/{manifest.yaml, setup/, checks/, hints/, README.md, tests/}`. Добавление лаборатории:

1. создайте каталог по образцу (или добавьте спецификацию в `infra/scripts/labgen` и выполните `python infra/scripts/labgen/generate.py`);
2. добавьте `tests/solution.sh` (проходит) и `tests/wrong.sh` (не проходит);
3. включите id в `content/courses/linux-upskill/course.yaml`, затем `make seed`.

Опубликованная версия лаборатории неизменяема: `make seed` откажется перезаписать изменённый контент с тем же `version`
(в `ENV=dev` перезапись разрешена для удобства разработки).

### Адаптации заданий к безопасной песочнице

- **linux-010 (chown):** без root нельзя менять пользователя-владельца, поэтому задание учит `chown :группа`, `chgrp -R` и setgid-каталоги.
- **linux-011 (пользователи и группы):** создание пользователей невозможно без привилегий — лаборатория исследовательская (`id`, `getent`, `/etc/passwd`, `/etc/group`).
- **incident-002 (квота логов):** «квота» — отдельный tmpfs 8 МБ на `/var/log/app`.
- **incident-003:** порт и healthcheck — на loopback внутри песочницы (сети нет).

## Ограничения и что не реализовано

Полный список — в итоговом отчёте разработки и в [docs/security/README.md](docs/security/README.md). Главное:

- нет VM-runtime (только DockerAdapter), нет публичного развёртывания «из коробки»;
- FR-10 реализован как CLI-импорт контента (`make seed`), без админ-интерфейса/админ-API;
- FR-11: метрики Prometheus есть (`/metrics`, защищено токеном), `infra/monitoring/prometheus.yml` приложен, но Grafana и дашборды не поставляются;
- worker держит только **текущую** версию контента: сессия на устаревшей версии не может быть выдана заново (`LAB_VERSION_UNAVAILABLE`);
- нет подтверждения email, сброса пароля, i18n (структура допускает), AI-наставника, рейтингов и multi-host сценариев (P2/вне MVP).
