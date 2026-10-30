# Linux Dojo — техническое задание для Claude Code

**Версия:** 1.0  
**Дата:** 2026-10-30  
**Статус:** спецификация MVP, предназначенная для реализации  
**Язык приложения:** русский (структура допускает i18n в будущем)

> **Инструкция исполнителю (Claude Code).** Реализуй работоспособный MVP по этой спецификации, а не только UI-макет. Придерживайся последовательности этапов из раздела 17. В спорных случаях выбирай простую, тестируемую и безопасную реализацию. Не заменяй реальную Linux-оболочку JavaScript-эмуляцией. Не включай небезопасные режимы контейнеров ради упрощения разработки. Если окружение не позволяет выполнить требование безопасно, опиши ограничение в README и не открывай соответствующую функциональность публично.

## 1. Описание продукта

**Linux Dojo** — интерактивная веб-платформа для изучения Linux и DevOps через практику в терминале браузера.

Обучающий путь: **Learn → Practice → Incident**.

- **Learn:** короткая теория, направляющие подсказки, выполнение конкретных действий.
- **Practice:** самостоятельное достижение заданного состояния системы.
- **Incident:** диагностика и устранение искусственно созданных неисправностей.

**Основная ценность:** пользователь выполняет настоящие команды в изолированном Linux-окружении, а система проверяет результат, а не буквальное совпадение введённых команд с шаблоном.

### 1.1. Целевая аудитория

- Студенты и начинающие DevOps/Linux-инженеры.
- Junior/Middle инженеры, совершенствующие диагностику Linux.
- На следующих этапах — SRE и Senior-инженеры, учебные группы и компании.

### 1.2. Цель MVP

Разработать законченный учебный сценарий: регистрация → каталог → запуск Linux-лаборатории → работа через браузерный терминал → независимая проверка → начисление XP → сохранение прогресса → уничтожение окружения.

**Целевой объём контента:** 20 лабораторий в 3 модулях (см. раздел 14).

### 1.3. Вне MVP

Не реализовывать в первом релизе: платежи, AI-наставника, корпоративные кабинеты, рейтинг, Kubernetes-песочницы, Terraform, полноценные multi-host лаборатории, публичный marketplace сценариев, сложный онлайн-редактор кода. Оставить архитектурную возможность для их добавления.

## 2. Технологический стек (обязателен)

| Уровень | Технологии |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Эмулятор терминала в браузере | xterm.js + FitAddon |
| Backend | **Python 3.12+**, FastAPI, Pydantic v2 |
| ORM / миграции | SQLAlchemy 2.x async, Alembic |
| База данных | PostgreSQL |
| Кэш / очередь / временные билеты | Redis (предпочтительно Redis Streams для фоновых задач) |
| Worker / sandbox orchestration | **Python**, Docker SDK или строго изолированный runtime adapter |
| Linux sandbox | Docker для локального ограниченного MVP; VM-backed runtime в будущем |
| Обратный прокси | Nginx или Traefik |
| Tests | pytest, pytest-asyncio, httpx, Playwright |
| Lint / types | Ruff, mypy, ESLint, TypeScript strict |
| CI/CD | GitHub Actions |
| Observability | структурированные JSON-логи, Prometheus, Grafana (после критического пути MVP) |

Backend — **модульный монолит**, Worker — отдельный процесс/служба с отдельной границей доверия. Не строить микросервисы ради микросервисов.

## 3. Архитектура и зоны доверия

```text
Browser (React + xterm.js)
         |
      HTTPS/WSS
         |
Reverse Proxy / TLS / rate limit
         |
  FastAPI application
  ├── Auth / Users
  ├── Catalog / Lab Content
  ├── Sessions / Progress / XP
  ├── Validation orchestration
  └── WebSocket terminal gateway
         |                 |
     PostgreSQL          Redis
                            |
                         Job queue
                            |
               Sandbox Worker (separate service)
                 ├── RuntimeAdapter
                 ├── Provision / PTY
                 ├── Independent Validator
                 └── Cleanup / Reconciler
                            |
                 Isolated Linux sandboxes
```

### 3.1. Ответственность компонентов

**Frontend:** аутентифицированные страницы, каталог, Workspace, терминал и его resize, подсказки, прогресс, статусы. Не вычисляет правильность задания и не получает приватные check scripts.

**API:** управление пользователями, доступом, учебным контентом, сессиями, идемпотентностью, состояниями и прогрессом. API не запускает пользовательский shell в собственном процессе.

**Worker:** создаёт и уничтожает окружения, привязывает PTY, исполняет проверку посредством отдельного доверенного канала, обеспечивает TTL и очистку. Только Worker имеет доступ к runtime control socket/API. Worker и runtime должны работать отдельно от публичного web/API-хоста при публичном развёртывании.

**PostgreSQL:** постоянное хранилище и источник истины для прогресса, состояния сессий и XP.

**Redis:** задания на provision/cleanup, временные одноразовые terminal tickets, краткоживущие блокировки/лимиты. Потеря Redis не должна приводить к потере завершённых результатов.

### 3.2. Runtime abstraction

Предусмотреть интерфейс `RuntimeAdapter` с методами:

- `create(session_id, lab_version, resource_limits) -> runtime_ref`
- `attach_terminal(runtime_ref) -> PTYStream`
- `resize_terminal(runtime_ref, cols, rows)`
- `snapshot_or_inspect(runtime_ref) -> validation_context`
- `destroy(runtime_ref)`
- `is_alive(runtime_ref) -> bool`

В MVP реализовать DockerAdapter. Архитектура должна позволить заменить его на VMAdapter для root/systemd/networking сценариев без изменения публичного REST API.

## 4. Безопасность (необсуждаемые ограничения)

Пользователь запускает **произвольные команды**. Считать каждую лабораторию потенциально враждебной. Docker в стандартной конфигурации не является достаточной security boundary против целенаправленного побега. Для публичного доступа нужен аудит безопасности и предпочтительно VM/microVM или усиленная sandbox-изоляция; первый Docker MVP допустим локально либо в ограниченном доверенном тестировании.

**Обязательно:**

1. Ни в коем случае не использовать для ученических контейнеров `--privileged`, `--pid=host`, `--network=host`, привилегированный root на хосте или монтирование `/var/run/docker.sock`.
2. Образ без лишних пакетов; непривилегированный пользователь внутри окружения; `no-new-privileges`; drop all Linux capabilities; read-only rootfs, где сценарий это позволяет; отдельные writeable tmpfs/volumes.
3. Ограничить CPU, RAM, количество процессов, объём writable storage, время жизни, максимальный вывод и количество одновременных сессий.
4. Сеть по умолчанию запрещена. Не разрешать доступ к приватным сетям, metadata endpoints, Postgres/Redis/API/management plane. Интернет — только как отдельная контролируемая возможность будущих сценариев.
5. Образы только из allowlist, фиксировать по digest; нельзя передавать Docker image или произвольные setup/check scripts через публичный API.
6. Проверяющие скрипты и ожидаемые результаты не должны находиться в изменяемой пользовательской файловой системе. Validation Runner должен работать через отдельную границу доверия. Не считать проверку защищённой от мошенничества, если пользователь может модифицировать её источник или контрольные данные.
7. Управление сессиями доступно только владельцу. Проверять права для HTTP **и** WebSocket, включая `Origin` и одноразовый краткоживущий ticket.
8. Ограничивать rate API/создания сессий и WebSocket, использовать HTTPS/WSS, безопасные cookies, CSRF protection, password hashing Argon2id.
9. Никогда не писать в общие логи пароли, cookies, токены, содержимое приватных env или полную терминальную историю по умолчанию.
10. При сбоях Worker, истечении TTL или рестарте осуществлять reconciliation и гарантировать сборку мусора; все ресурсы тегировать `session_id`.

Если ограничение технически не выполнено, **не выдавать функцию за безопасную** и не публиковать систему в интернет.

## 5. UX и страницы

1. **Landing** — описание продукта и вход.
2. **Login / Register** — аккаунт, обработка ошибок.
3. **Dashboard** — общий XP, завершённые лаборатории, последние попытки.
4. **Catalog** — модули/лаборатории, фильтры `mode`, `difficulty`, `completed`.
5. **Lab details** — цели, ожидаемая продолжительность, навыки, запуск.
6. **Workspace** — левая панель с задачей/подсказками, правая с реальным интерактивным терминалом, статус provision, `Start`, `Check`, `Reset`, `Stop`.
7. **Result** — успешные/неуспешные проверки, итог, XP, рекомендации.
8. **Profile / Progress** — история, лучшие результаты, выполненные задания.

Desktop — 2 колонки в Workspace; mobile — вкладки «Задание / Терминал». В терминале нужны UTF-8, scrollback, paste, Ctrl+C, интерактивный PTY, изменение размера, прокрутка, повторное подключение после краткого обрыва.

**Важно:** xterm.js только отображает терминал; shell выполняется исключительно в sandbox.

## 6. Функциональные требования

| ID | Требование | Приоритет |
|---|---|---|
| FR-01 | Регистрация / вход / выход / refresh | P0 |
| FR-02 | Каталог курсов, модулей и лабораторий | P0 |
| FR-03 | Просмотр задания, условий, подсказок | P0 |
| FR-04 | Создание изолированной лаборатории | P0 |
| FR-05 | Двусторонний терминал через WSS | P0 |
| FR-06 | Проверка конечного состояния (не строки команды) | P0 |
| FR-07 | Retry, reset, stop, TTL, cleanup | P0 |
| FR-08 | Прогресс и однократное начисление XP | P0 |
| FR-09 | История сессий и результатов | P0 |
| FR-10 | Админ-публикация сценариев из репозитория | P1 |
| FR-11 | Метрики и расширенный мониторинг | P1 |
| FR-12 | AI-наставник, рейтинги, многосерверные сценарии | P2 |

## 7. Состояния сессии

```text
CREATED -> PROVISIONING -> READY -> RUNNING
                          \-> FAILED
RUNNING -> VALIDATING -> RUNNING       (неуспешная проверка)
                      \-> COMPLETED   (успешная проверка)
Any active state -> STOPPING -> STOPPED
Any active state -> EXPIRED
```

- Переходы выполняются сервером атомарно с проверкой текущего статуса.
- `VALIDATING` не допускает параллельные проверки одной сессии.
- При успешной проверке прогресс и XP записываются в одной транзакции, XP защищён уникальным ключом идемпотентности.
- `Reset` создаёт чистую новую runtime-инстанцию (или новую логическую попытку) и не отменяет уже подтверждённый прогресс. Конкретно: завершить старую сессию, создать новую с новым UUID, вернуть новый `session_id`.
- `Stop` идемпотентен, можно безопасно повторить запрос.
- TTL задаётся при создании; все просроченные ресурсы удаляются Worker/reconciler.

## 8. Модели данных PostgreSQL

Все первичные ключи — UUID; время — `TIMESTAMPTZ` UTC. Рекомендуются индексы по FK, статусу/TTL, user/date. Использовать Alembic, не создавать схему неуправляемо через `create_all` на production.

### 8.1. `users`

- `id UUID PK`
- `email VARCHAR(320) UNIQUE NOT NULL`
- `password_hash TEXT NOT NULL`
- `display_name VARCHAR(100) NULL`
- `role VARCHAR(16) NOT NULL DEFAULT 'student'`
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`

### 8.2. `courses`

`id UUID PK`, `slug TEXT UNIQUE`, `title TEXT`, `description TEXT`, `position INT`, `published BOOLEAN`.

### 8.3. `modules`

`id UUID PK`, `course_id UUID FK`, `slug TEXT`, `title TEXT`, `description TEXT`, `position INT`; unique `(course_id, slug)`.

### 8.4. `labs`

`id UUID PK`, `module_id UUID FK`, `slug TEXT UNIQUE`, `title TEXT`, `description TEXT`, `mode TEXT` (`learn|practice|incident`), `difficulty TEXT`, `position INT`, `estimated_minutes INT`, `published BOOLEAN`.

### 8.5. `lab_versions`

`id UUID PK`, `lab_id UUID FK`, `version INT`, `manifest_ref TEXT`, `image_digest TEXT`, `published_at TIMESTAMPTZ NULL`, unique `(lab_id, version)`; сессия всегда привязана к конкретной неизменяемой опубликованной версии.

### 8.6. `lab_sessions`

`id UUID PK`, `user_id UUID FK`, `lab_version_id UUID FK`, `status TEXT`, `runtime_ref TEXT NULL` (не раскрывать клиенту), `created_at`, `started_at NULL`, `expires_at`, `finished_at NULL`, `last_activity_at NULL`, `error_code TEXT NULL`; индекс `(status, expires_at)`.

### 8.7. `validation_attempts`

`id UUID PK`, `session_id UUID FK`, `status TEXT`, `score NUMERIC(5,2)`, `passed BOOLEAN`, `checks_json JSONB` (публичные/санитизированные результаты), `created_at`, `finished_at NULL`.

### 8.8. `user_progress`

`user_id UUID FK`, `lab_id UUID FK`, `best_score NUMERIC(5,2)`, `completed_at TIMESTAMPTZ NULL`, `attempts_count INT DEFAULT 0`, primary key `(user_id, lab_id)`.

### 8.9. `xp_transactions`

`id UUID PK`, `user_id UUID FK`, `session_id UUID FK`, `amount INT`, `reason TEXT`, `created_at`, unique `(user_id, session_id, reason)`.

Суммарный XP — сумма подтверждённых транзакций либо кешируемое вычисляемое поле, обновляемое транзакционно.

### 8.10. Авторизационные сессии

Добавить `auth_sessions`/refresh-token sessions с hashed token, owner, expiry/revocation. Хранить только хэш refresh token, управлять ротацией.

## 9. REST API

Префикс: `/api/v1`; JSON; ошибки единообразно: `{ "error": { "code": "...", "message": "...", "details": {} } }`.

### 9.1. Auth

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/auth/register` | регистрация |
| POST | `/auth/login` | вход; cookie |
| POST | `/auth/refresh` | ротация refresh session |
| POST | `/auth/logout` | отзыв сессии |
| GET | `/users/me` | профиль |

### 9.2. Catalog / Progress

| Метод | Endpoint | Назначение |
|---|---|---|
| GET | `/courses` | опубликованные курсы |
| GET | `/courses/{course_id}/modules` | модули |
| GET | `/labs?mode=&difficulty=&completed=` | поиск/фильтрация/пагинация |
| GET | `/labs/{lab_id}` | публичная карточка задания |
| GET | `/users/me/progress` | прогресс |
| GET | `/users/me/sessions` | история с пагинацией |

### 9.3. Labs / Sessions

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/labs/{lab_id}/sessions` | создать sandbox-сессию (202) |
| GET | `/sessions/{session_id}` | статус, TTL, сведения о задаче |
| POST | `/sessions/{session_id}/validate` | запустить проверку (202) |
| GET | `/sessions/{session_id}/validations/{attempt_id}` | статус/результат проверки |
| POST | `/sessions/{session_id}/reset` | завершить старую, создать новую сессию |
| DELETE | `/sessions/{session_id}` | завершить/очистить (идемпотентно) |
| POST | `/sessions/{session_id}/terminal-ticket` | одноразовый короткий билет WS |

Все endpoints `/sessions/*` проверяют владельца и состояние. POST создания сессии принимает `Idempotency-Key`; повтор с тем же ключом и телом возвращает ту же операцию в период действия ключа, конфликтующее тело — `409`.

**Пример POST `/labs/{lab_id}/sessions`:**

```http
POST /api/v1/labs/linux-001/sessions
Idempotency-Key: e8ca58ec-1001-4bba-9939-182b35750001
```

```json
{
  "session_id": "8c43b960-5b93-41f7-a6af-1ff618d94d17",
  "status": "PROVISIONING",
  "expires_at": "2026-10-30T11:30:00Z",
  "status_url": "/api/v1/sessions/8c43b960-5b93-41f7-a6af-1ff618d94d17"
}
```

Ответ 202 означает принятую операцию, **не** готовность окружения. `GET /sessions/{id}` возвращает `READY` после создания.

**Пример результата проверки:**

```json
{
  "attempt_id": "045641a7-5840-4fd3-9ed4-a79502252719",
  "status": "FINISHED",
  "passed": true,
  "score": 100,
  "checks": [
    {"id": "directory_exists", "passed": true, "message": "Каталог создан"},
    {"id": "owner_valid", "passed": true, "message": "Владелец корректен"}
  ],
  "xp_awarded": 100
}
```

Не возвращать внутренние scripts, скрытые флаги/токены, runtime IDs, server filesystem paths.

## 10. WebSocket terminal protocol

**Endpoint:** `wss://<host>/api/v1/sessions/{session_id}/terminal?ticket=<one_time_ticket>`.

- Ticket выдаёт `/terminal-ticket` только владельцу сессии `READY/RUNNING`.
- Ticket живёт не более 30 секунд, одноразовый, хранится в Redis как хэш и привязан к `user_id + session_id`.
- Проверять `Origin`, сессионную авторизацию и принадлежность ticket.
- Input/output shell — **binary WS frames** (поток байтов PTY); управляющие сообщения — JSON text frames, например `{"type":"resize","cols":120,"rows":32}`; `ping`, `pong`, `error`, `session_expired`.
- Безопасно поддерживать повторное подключение к **той же** активной сессии.
- PTY имеет bounded output queues, backpressure, лимит вывода и корректное закрытие.
- Терминал нельзя использовать, когда сессия `STOPPED/FAILED/EXPIRED`.
- Предусмотреть обработку `Ctrl+C` как управляющего символа в PTY, а не отключение WebSocket.

## 11. Формат учебного контента

Каждая лаборатория — версия набора конфигураций и скриптов в репозитории:

```text
content/labs/linux-001/
├── manifest.yaml
├── setup/prepare.sh
├── checks/validate.sh
├── hints/hints.yaml
└── README.md
```

```yaml
schema_version: 1
id: linux-001
version: 1
title: "Поиск ошибки в логах"
mode: practice
difficulty: junior
estimated_minutes: 10
runtime:
  type: container
  image: "linuxdojo/ubuntu-basic@sha256:REPLACE_WITH_REAL_DIGEST"
  timeout_seconds: 1800
setup:
  script: setup/prepare.sh
validation:
  type: script
  script: checks/validate.sh
  timeout_seconds: 15
hints:
  - "Изучи содержимое /var/log/app"
  - "Попробуй grep"
reward:
  base_xp: 100
```

**Важно:** этот digest — placeholder в документе. Перед реализацией нужно собрать образ и зафиксировать реальный SHA256 digest. Ни в коем случае не использовать буквальный `REPLACE_WITH_REAL_DIGEST` при запуске.

- Схемы манифестов валидации — Pydantic/JSON Schema.
- Импорт/публикация контента — доверенная административная операция на этапе сборки или deploy, не API для обычного пользователя.
- Публичный GET лаборатории отдаёт только безопасные описательные поля и доступные hints.
- Setup выполняется из доверенного источника до передачи sandbox пользователю; checks исполняются независимо от пользовательской оболочки и не должны быть доступны ей для записи.
- Версионировать образы и манифесты, чтобы уже начатые сессии продолжали работать на своей версии.

### 11.1. Оценивание

Для check `i` задаются `weight_i` и `passed_i ∈ {0,1}`:

`Score = 100 * sum(weight_i * passed_i) / sum(weight_i)`.

- Для прохождения обязательны все required checks.
- Альтернативные способы решения допустимы.
- Для incident проверять восстановление функциональности, а не конкретную команду.
- XP начислять только за первое успешное прохождение конкретной лаборатории (MVP-политика); дальнейшие попытки могут улучшать `best_score`, но не приносить XP повторно.
- Сценарии с частичным баллом не считаются завершёнными при провале required check.

### 11.2. Пример безопасно проверяемой задачи

Задание: создать каталог `/home/student/workspace/report` и файл `result.txt` с заданным содержимым. Проверить наличие каталога и файл посредством независимого runner. Не сравнивать историю ввода `mkdir`/`touch` с эталоном. Для более сложных root-сценариев использовать VM runtime.

## 12. Организация репозитория

```text
linux-dojo/
├── apps/
│   ├── web/
│   │   ├── src/
│   │   │   ├── app/
│   │   │   ├── pages/
│   │   │   ├── components/
│   │   │   ├── features/{auth,catalog,terminal,laboratory,progress}/
│   │   │   ├── api/
│   │   │   ├── hooks/
│   │   │   └── types/
│   │   └── package.json
│   ├── api/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   ├── modules/{auth,users,courses,labs,sessions,validation,progress}/
│   │   │   ├── db/
│   │   │   └── websocket/
│   │   ├── alembic/
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── sandbox-worker/
│       ├── worker/
│       │   ├── runtime/{base.py,docker.py}
│       │   ├── provisioning/
│       │   ├── terminal/
│       │   ├── validation/
│       │   └── cleanup/
│       ├── tests/
│       └── pyproject.toml
├── content/
│   ├── courses/
│   ├── labs/
│   └── schemas/
├── sandbox-images/
│   ├── ubuntu-basic/
│   └── ubuntu-network/
├── infra/
│   ├── compose/
│   ├── proxy/
│   ├── monitoring/
│   └── scripts/
├── docs/{architecture,api,security,adr}/
├── .github/workflows/
├── .env.example
├── Makefile
└── README.md
```

Для backend-модулей использовать `router.py`, `schemas.py`, `service.py`, `repository.py`, `models.py`, если это имеет смысл для данного модуля; не создавать пустые абстракции.

## 13. Нефункциональные требования MVP

Показатели — **целевые для тестирования**, не обещанная производительность.

| Показатель | Целевое значение |
|---|---|
| Одновременно работающие лаборатории | 10 в ограниченном тестовом стенде |
| P95 подготовка sandbox из локального образа | ≤ 10 секунд |
| P95 интерактивная задержка в целевом регионе | ≤ 200 мс |
| Доступность API тестового стенда | 99% за месяц |
| TTL сессии | 30 минут |
| Idle timeout | 10 минут |
| Базовый лимит CPU | 0.5 vCPU |
| Базовый лимит RAM | 256 MiB, проверять на практике |
| Время обычной validation | ≤ 15 секунд |
| Поддерживаемые браузеры | актуальные Chrome/Firefox/Edge |

Не превышать лимиты через бесконтрольное создание окружений. При недоступности ресурсов возвращать понятный `429`/`503` и не создавать полусессии без cleanup.

## 14. Перечень 20 лабораторий

### Module A — Linux Basics (8)

| ID | Название | Mode |
|---|---|---|
| linux-001 | Навигация по файловой системе | Learn |
| linux-002 | Создание и удаление файлов | Learn |
| linux-003 | Просмотр файлов и потоков | Learn |
| linux-004 | Поиск файлов через find | Practice |
| linux-005 | Поиск в логах через grep | Practice |
| linux-006 | Pipes и перенаправление вывода | Practice |
| linux-007 | Архивирование и tar | Practice |
| linux-008 | Текстовые фильтры awk и sed | Practice |

### Module B — Administration (7)

| ID | Название | Mode |
|---|---|---|
| linux-009 | Права доступа chmod | Learn |
| linux-010 | Владельцы файлов chown (без выдачи опасных прав) | Practice |
| linux-011 | Пользователи и группы (без host privileges) | Practice |
| linux-012 | Переменные окружения | Learn |
| linux-013 | Процессы и сигналы | Practice |
| linux-014 | Диагностика дискового пространства (quota/workspace) | Practice |
| linux-015 | Bash-скрипт резервного копирования | Practice |

### Module C — Incident Simulation (5)

| ID | Название | Mode |
|---|---|---|
| incident-001 | Permission denied при старте приложения | Incident |
| incident-002 | Заполненная квота логов в sandbox | Incident |
| incident-003 | Приложение слушает неправильный порт (loopback внутри sandbox) | Incident |
| incident-004 | Неверный путь конфигурации | Incident |
| incident-005 | Потеря доступа к рабочим файлам после релиза | Incident |

**Ограничение:** `linux-010`, `linux-011` и отдельные инциденты могут требовать привилегий, которых нельзя безопасно предоставлять внутри обычного контейнера. Для MVP адаптировать их к непривилегированному workspace с контролируемой моделью файлов/пользователей либо перенести полноценный вариант на VM runtime; никогда не добавлять `--privileged` для прохождения теста.

Каждая лаборатория должна иметь: понятное описание, стартовые данные, 1–3 hints, проверяемые условия, критерий успеха, ожидаемый допустимый runtime и тесты «правильное решение / неправильное решение».

## 15. Observability и эксплуатация

- JSON-логи с `request_id`, `session_id`, `component`, `error_code`; секреты и терминальный ввод не логировать.
- Метрики: active/provisioning/failed sessions; launch latency; validation latency; WebSocket disconnects; sandbox CPU/RAM/PIDs; cleanup failures; API errors.
- Health endpoints: `/health/live` и `/health/ready` с различением liveness/readiness.
- Применять ограничение времени на все фоновые операции, retry with exponential backoff, bounded retries и dead-letter/error state.
- Reconciler периодически сравнивает БД и реально существующие контейнеры, помечает missing runtime и удаляет orphan resources.

## 16. Тестирование и критерии приёмки

### 16.1. Набор тестов

- **Unit:** правила XP, состояний, доступов, подсказок, манифестов, расчёт баллов.
- **Integration:** PostgreSQL, Redis, auth cookies, backend REST, migrations.
- **Worker integration:** создание, terminal attach, проверка, reset, stop, очистка.
- **E2E:** регистрация → каталог → запуск → команда → check → XP → перезаход → сохранённый прогресс.
- **Security:** запрет доступа к чужому terminal/session, подмена ticket, отсутствие host mounts/privileges, тест лимитов, TTL, сетевой изоляции и отказа от опасных запросов.
- **Load:** 10 одновременных sandbox при заданных ресурсах.

### 16.2. Acceptance criteria

- [ ] Проект запускается локально по документированным командам.
- [ ] Все 20 заданий доступны в каталоге и имеют корректные манифесты.
- [ ] Реальный shell работает внутри sandbox через браузерный PTY.
- [ ] У каждого задания воспроизводимое стартовое состояние.
- [ ] Проверка результата не требует строго определённой последовательности команд.
- [ ] Неверное решение не проходит, правильное проходит.
- [ ] Пользователь A не может читать/управлять сессией пользователя B.
- [ ] XP не начисляется повторно при конкурентных/повторных запросах.
- [ ] При отключении вкладки терминал может переподключиться, если сессия ещё активна.
- [ ] Истёкшие и осиротевшие sandbox автоматически удаляются.
- [ ] API отдаёт OpenAPI-схему, миграции выполняются успешно.
- [ ] CI запускает lint, types, tests и сборку.
- [ ] Документированы ограничения безопасности контейнерного MVP.

## 17. План реализации для Claude Code

**Работать итеративно, но обязательно довести до запущенного вертикального сценария.**

### Phase 1 — Foundation

1. Создать monorepo, базовые конфигурации и `.env.example` без реальных секретов.
2. Настроить FastAPI, React/Vite, PostgreSQL, Redis, миграции Alembic.
3. Реализовать auth, каталог/модели и seed первой лаборатории.
4. Настроить Docker Compose для инфраструктурных сервисов; документировать разделение API/Worker.

**DoD:** frontend, API, БД доступны, `GET /courses` работает, миграции воспроизводимы.

### Phase 2 — Safe sandbox & real terminal

1. Определить RuntimeAdapter и DockerAdapter с жёсткими лимитами.
2. Реализовать Worker, очередь задач, статусы provision/cleanup.
3. Сделать серверный PTY + WebSocket gateway + одноразовый ticket.
4. Ограничить attach чужих сессий, реализовать resize, cancellation, reconnect.
5. Реализовать TTL и reconciliation.

**DoD:** один пользователь запускает настоящий shell из браузера и завершает его без утечки контейнеров.

### Phase 3 — Lab engine

1. Определить строгую схему `manifest.yaml`.
2. Импортировать задания из trusted content directory.
3. Реализовать reproducible setup, validation, public checks summaries.
4. Реализовать reset, result, transactionally awarded XP.

**DoD:** одна настоящая лаборатория полностью проходима через UI; правильное и неправильное решения различаются тестами.

### Phase 4 — Learning UX

1. Каталог, описание задачи, подсказки, Workspace и экран результата.
2. Dashboard, история, XP, loading/error states.
3. Responsive design, keyboard accessibility, frontend E2E.

**DoD:** полный пользовательский путь работает без использования Swagger или ручного SQL.

### Phase 5 — Content pack

1. Добавить 20 заданий из раздела 14, не ослабляя sandbox.
2. На каждое задание добавить автоматический positive/negative test.
3. Заполнить понятные тексты и подсказки на русском.

**DoD:** каталог из 20 воспроизводимых и проверяемых лабораторий.

### Phase 6 — Hardening and delivery

1. Security review, лимиты, rate limits, запрет чувствительных логов, cleanup tests.
2. Ruff/mypy/pytest/ESLint/TypeScript/Playwright в CI.
3. Compose deployment, healthcheck, observability и README.
4. Нагрузочные испытания на 10 sandbox, фиксация фактических результатов.

**DoD:** продукт пригоден к локальному использованию и ограниченному доверенному тестированию; **не утверждать публичную безопасность без отдельного security audit**.

## 18. Требования к локальному запуску

Сформировать инструкции в `README.md` для Linux/macOS; для Windows — через WSL2. По возможности сделать единые команды Makefile:

```bash
cp .env.example .env
make setup
make up
make migrate
make seed
make test
make down
```

Реализовать реальные цели Makefile (не оставлять фиктивными), указать локальные URL frontend/API/OpenAPI. Если sandbox требует особой конфигурации и не может безопасно стартовать автоматически, **явно** описать настройку и предусмотреть disabled-by-default режим до её выполнения.

### Конфигурация через ENV

Обязательные переменные: `DATABASE_URL`, `REDIS_URL`, `APP_SECRET`, `PUBLIC_ORIGIN`, `SANDBOX_RUNTIME`, `SANDBOX_MAX_CONCURRENT`, `SANDBOX_TTL_SECONDS`, `SANDBOX_IDLE_SECONDS`, `SANDBOX_CPU_LIMIT`, `SANDBOX_MEMORY_LIMIT`; остальные — по необходимости. Предоставить безопасные dev defaults и отдельные настройки для production.

## 19. Нормы качества реализации

- Python: типизация, Pydantic, Ruff, mypy, pytest; асинхронный I/O не блокирует event loop.
- JavaScript/TypeScript: строгий TypeScript, ESLint, небольшие компоненты, TanStack Query.
- Логика разделена по доменам, без чрезмерных абстракций.
- SQL миграции версионируются, любые операции изменения схемы — через Alembic.
- Вся конфигурация через ENV; `.env` не коммитить.
- У ошибок есть стабильный `error.code`; в UI отображаются дружелюбные сообщения.
- Учебный контент добавляется данными, а не копированием бизнес-логики.
- Не использовать mocks как замену реальному worker/sandbox в демонстрационном сценарии.

## 20. Что Claude Code должен предоставить в результате

1. Исходный monorepo по разделу 12.
2. Рабочий локальный запуск и миграции.
3. Реальный терминал Linux в браузере.
4. Работающую безопасно ограниченную песочницу и автопроверку, без `--privileged` и доступа к Docker socket из пользовательского контейнера.
5. Каталог из 20 упражнений или, если объективно невозможно обеспечить часть сценариев безопасно, явную пометку блокирующих сценариев **без имитации их работоспособности**.
6. Все ключевые тесты и CI.
7. `README.md`, `.env.example`, OpenAPI, краткую диаграмму архитектуры, ограничения безопасности, инструкции тестирования и дальнейшие шаги.
8. В итоговом отчёте — перечень реально реализованного, результаты выполненных тестов и **отдельный перечень всего, что не реализовано**. Не заявлять о готовности функциональности, которую не запускал и не проверял.

---

## 21. Краткий стартовый prompt для Claude Code

> Прочитай `Linux_Dojo_TZ.md` полностью. Реализуй Linux Dojo MVP строго по документу, используя **Python/FastAPI для API и worker**, **React/TypeScript для frontend**, PostgreSQL и Redis. Начни с архитектуры репозитория и работающего end-to-end сценария «от запуска лаборатории до проверки», затем добавляй каталог и контент. Не подменяй терминал моками и не запускай пользовательские контейнеры в привилегированном режиме. Разбей работу на фазы, после каждой запускай релевантные тесты и исправляй ошибки. Если какая-либо функция не реализована безопасно, оставь её отключённой, документируй ограничение и продолжи с доступными задачами. В конце дай конкретные команды локального запуска и отчёт о реально выполненных проверках.
