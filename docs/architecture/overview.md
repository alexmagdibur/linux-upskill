# Архитектура Linux Upskill

Модульный монолит (API) + отдельный процесс **sandbox worker** с собственной границей доверия.

```text
 Browser (React + xterm.js)
        │  HTTPS / WSS (один origin; в dev — Vite proxy)
        ▼
 Reverse proxy (nginx: статика, /api, лимиты; /internal и /metrics наружу закрыты)
        ▼
 ┌─────────────────────── FastAPI (apps/api) ────────────────────────┐
 │ auth · users · courses/labs (каталог) · sessions · validation ·   │
 │ progress/XP · internal (callbacks worker) · WS-шлюз терминала     │
 └────┬──────────────────────┬───────────────────────────────┬───────┘
      │ SQLAlchemy async     │ Redis                         │ внутренний WS (X-Internal-Token)
      ▼                      ▼                               ▼
 PostgreSQL            Redis Streams `upskill:jobs`   ┌── Sandbox Worker (apps/sandbox-worker) ──┐
 (источник истины:     + одноразовые ticket'ы         │ JobConsumer (retry, DLQ) · TerminalHub   │
  сессии, XP,          + rate limit                   │ RuntimeAdapter → DockerAdapter           │
  прогресс)                                           │ Validation runner · Reconciler/TTL       │
                                                      └──────────────┬───────────────────────────┘
                                                                     ▼ Docker Engine API
                                                      изолированные контейнеры-песочницы
```

## Потоки

**Запуск лаборатории.** `POST /labs/{id}/sessions` → транзакция в PostgreSQL (проверка лимитов под advisory-lock,
статус `PROVISIONING`, ключ идемпотентности) → задание `provision` в Redis Streams → worker создаёт контейнер,
выполняет доверенный setup и вызывает `POST /internal/v1/sessions/{id}/provisioned` → `READY`.
Если сессию успели остановить, callback возвращает `accepted=false`, и worker удаляет окружение.

**Терминал.** `POST /sessions/{id}/terminal-ticket` (одноразовый, 30 с, в Redis только SHA-256) →
`WS /api/v1/sessions/{id}/terminal?ticket=…`. Шлюз API проверяет Origin, cookie-сессию, принадлежность ticket
пользователю **и** сессии, статус `READY/RUNNING`, затем проксирует кадры во внутренний WS worker'а
(binary — байты PTY, text — JSON-управление: `resize`, `ping/pong`, `error`, `session_expired`).
PTY живёт в worker'е столько же, сколько сессия: переподключение (даже после перезагрузки вкладки) возвращает
в тот же shell и воспроизводит последние 128 КиБ вывода.

**Проверка.** `POST /sessions/{id}/validate` → атомарный переход в `VALIDATING` (+ частичный уникальный индекс
«одна незавершённая проверка на сессию») → задание `validate`. Worker: (1) необязательный `exercise` — доверенный
сценарий, который запускает пользовательский артефакт **от имени student**; (2) `validate.sh` под отдельным
пользователем `validator` через собственный `docker exec`. Результат (`PASS/FAIL <id>`) уходит в API, где
в одной транзакции записываются попытка, прогресс и XP.

**Очистка.** Три независимых контура: (1) sweeper в API по TTL/idle/зависшим состояниям (PostgreSQL),
(2) reconciler worker'а по меткам контейнеров (`upskill.expires_at`) — работает даже при недоступном API,
(3) сверка с API: удаление контейнеров без активной сессии и перевод в `FAILED` сессий без контейнера.

## Состояния сессии

```text
CREATED → PROVISIONING → READY → RUNNING ⇄ VALIDATING → COMPLETED
                      ↘ FAILED     (READY → VALIDATING допустим — «проверить» без подключения терминала)
любое активное → STOPPING → STOPPED;  любое активное → EXPIRED
```

Переходы — атомарные `UPDATE … WHERE status IN (…) RETURNING`; правила собраны в
`apps/api/app/modules/sessions/states.py` и покрыты тестами. После успешной проверки окружение сразу
уничтожается (`COMPLETED` — финальный статус, терминал больше недоступен).

## Решения, отличающиеся от буквального ТЗ

См. `docs/adr/`. Кратко: образы описываются логическим именем + `content/images.lock.json` (content-addressed ID
вместо registry digest), добавлены `packages/upskill_content` (общая схема манифеста) и необязательный `exercise`-шаг проверки.
