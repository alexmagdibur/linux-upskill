# Безопасность и ограничения контейнерного MVP

> **Linux Upskill в текущем виде пригоден для локального использования и ограниченного доверенного тестирования.
> Не публикуйте его в интернете без отдельного аудита безопасности и (желательно) VM/microVM-изоляции.**
> Docker в стандартной конфигурации — не достаточная граница доверия против целенаправленного побега из контейнера.

## Что реально сделано (и проверяется тестами)

| Требование ТЗ §4 | Реализация | Проверка |
|---|---|---|
| Нет `--privileged`, `--pid=host`, `--network=host`, docker.sock в песочнице | `DockerAdapter.create` не принимает таких параметров; `privileged=False`, `network_mode="none"`, `ipc_mode="private"`, нет bind-монтирований | `test_container_is_created_unprivileged_with_hard_limits` (docker inspect) |
| Непривилегированный пользователь, `no-new-privileges`, drop ALL caps | `user=student (uid 1000)`, `cap_drop=["ALL"]`, `no-new-privileges`, setuid/setgid-бинарники вычищены из образа | `test_inside_view_no_caps_no_network_no_root_no_socket` (CapEff=0, NoNewPrivs=1), `test_cannot_escalate_or_mount` |
| Read-only rootfs, отдельные writable tmpfs | `read_only=True`; tmpfs: `/home/student` (48 МБ), `/tmp` (16 МБ, noexec), по 8 МБ на `writable_dirs` лаборатории | `test_disk_is_bounded_by_tmpfs` |
| Лимиты CPU/RAM/PIDs/процессов/времени/вывода/сессий | 0.5 vCPU, 256 МиБ (swap = RAM), 128 PIDs, TTL 30 мин, idle 10 мин, лимит вывода 64 МиБ на сессию, 2 сессии на пользователя, 10 глобально | `test_fork_bomb…`, `test_memory_limit…`, `test_output_limit…`, API-тесты лимитов и sweeper'а, `load_test.py` |
| Сеть запрещена | `network_mode="none"` (внутри только loopback) | тест изнутри: только `lo`, соединение наружу невозможно |
| Образы только из allowlist | логическое имя в манифесте → `content/images.lock.json` → контейнер создаётся по content-addressed ID; несовпадение/отсутствие — отказ | `test_unknown_image_id_is_rejected`, юнит-тесты манифеста (placeholder и registry-ссылки отклоняются) |
| Скрипты проверки не в изменяемой FS | `validate.sh` передаётся через переменную окружения `docker exec` и исполняется `eval` под пользователем `validator`; не лежит ни в файле, ни в argv | `test_validator_script_is_not_readable_by_student`, `test_student_cannot_tamper_with_validator_output` |
| Пользовательский код не исполняется в контексте проверки | если нужно запустить артефакт ученика (скрипт бэкапа, приложение), это делает отдельный `exercise` **от имени student** | лаборатории linux-012/015, incident-001/002/004 |
| Доступ только владельцу (HTTP и WS) | чужая сессия неотличима от несуществующей (404); WS: Origin + cookie + одноразовый ticket, привязанный к `user_id+session_id` | `test_isolation_between_users`, `tests/test_ws.py` (9 тестов) |
| Rate limit, CSRF, Argon2id | Redis fixed-window; double-submit CSRF + проверка Origin; Argon2id; refresh-токены хранятся хэшем с ротацией и обнаружением повторного использования | `tests/test_auth.py` |
| Нет секретов/ввода в логах | JSON-логи, редактирование ключей `password/token/ticket/…`, access-log uvicorn отключён (в нём был бы ticket), терминальный ввод/вывод не логируется | ревью кода |
| Reconciliation и GC | label `upskill.session_id`, TTL-метка, сверка с БД | `test_reconciler_*`, sweeper-тесты |

## Известные ограничения и риски (не замалчиваем)

1. **Docker ≠ VM.** Ядро хоста общее. Побег через уязвимость ядра/runc не исключён. Для публичного доступа нужен gVisor/Kata/Firecracker
   или VM на каждую сессию (интерфейс `RuntimeAdapter` это допускает) и внешний аудит.
2. **Worker имеет доступ к Docker Engine** (в compose — через docker.sock) — это эквивалент root на хосте. Worker должен работать
   на отдельном хосте/VM, недоступном из публичной сети; API ↔ worker — только по внутренней сети и `INTERNAL_TOKEN`.
   В локальной разработке worker запускается на хосте разработчика с вашими правами Docker.
3. **Нет кастомного seccomp/AppArmor-профиля** — используется профиль Docker по умолчанию. User namespaces не включены.
4. **Дисковая квота — tmpfs**, а не настоящая quota файловой системы; она ограничивает запись, а страницы tmpfs учитываются
   в cgroup-лимите памяти контейнера (256 МиБ) — заполненный диск уменьшает доступную процессам RAM.
5. **`/home/student` смонтирован с `exec`** (нужно для запуска собственных скриптов). `/tmp` и `writable_dirs` — `noexec`.
   Компиляторов и доступа в сеть в образе нет.
6. **Лимит вывода** считается на сессию целиком (64 МиБ); backpressure защищает память worker'а при медленном клиенте.
7. **Idle-таймаут** учитывает ввод пользователя в терминал, а не вывод процессов.
8. **Один активный клиент терминала на сессию**: новая вкладка вытесняет предыдущую.
9. `/internal/*` и `/metrics` защищены токеном, но **должны быть закрыты на proxy** (в `infra/proxy/nginx.conf` закрыты).
10. Нет подтверждения email, сброса пароля, 2FA, блокировки аккаунтов (только rate limit).
11. Хэширование паролей Argon2id с параметрами по умолчанию `argon2-cffi`; JWT access-токен подписан HS256 `APP_SECRET`.
12. Контент лабораторий считается **доверенным** (импортируется при деплое); sandbox-проверки уязвимы к «обману» ровно в той мере,
    в какой пользователь может подделать *состояние*, которое проверяется (это допустимо по ТЗ — проверяется состояние).

## Учебные машины на LXD (runtime `lxd`)

Подробности — `docs/architecture/vm-labs.md`. Что проверено тестами (`apps/sandbox-worker/tests/test_lxd.py`, реальная VM):

- машина непривилегированная (`security.privileged` не включён, нет `security.nesting`/`raw.lxc`), root внутри — подчинённый uid на хосте;
- сеть: из учебной машины **недоступны** другая сессия, шлюз и SSH хоста, LAN, шлюз VMware, интернет и DNS; доступна только своя сессия;
- лимиты процессов и памяти удерживают форк-бомбу и OOM внутри машины (VM-хост не страдает);
- скрипт проверки не лежит ни в файлах, ни в argv процессов машины; имена и fingerprint образа проверяются регулярками (нет инъекции в SSH-команды);
- `destroy` идемпотентно удаляет машину и её сеть; неудачный `setup` ничего не оставляет; осиротевшие сети собираются gc.

Известные риски: общее ядро с VM-хостом (как у любого контейнера); учебный `sudo` внутри машины; доступ worker → VM по SSH-ключу
(ключ worker'а = управление всеми учебными машинами: храните его только на хосте worker'а).

## Конфигурация production (минимум)

`ENV=prod` включает проверки: `APP_SECRET` ≥ 32 символов и не dev-значение, `INTERNAL_TOKEN` задан, `COOKIE_SECURE=true`.
Дополнительно: HTTPS/WSS на proxy, `TRUST_PROXY=true` только за вашим proxy, `PUBLIC_ORIGIN` = реальный origin,
worker на отдельном хосте, регулярные обновления образа песочницы.
