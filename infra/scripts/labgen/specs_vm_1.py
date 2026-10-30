"""Задания на учебной машине (LXD: настоящий systemd, root через sudo внутри изолированной машины): партия 1 — systemd и журналы.

Особенности: машина без сети наружу; ученик работает под student с sudo; проверка при необходимости перезагружает машину
(`reboot`), чтобы убедиться, что результат переживает холодную загрузку.
"""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append({"runtime_type": "lxd", **kw})


lab(
    id="ld-049", title="Unit для HTTP-сервиса: отдельный пользователь и автозапуск",
    description="Оформите учебный HTTP-сервер как systemd-сервис от непривилегированного пользователя, который стартует при загрузке.",
    skills=["systemd unit", "User=", "systemctl enable", "useradd --system"],
    objectives=["Создать системного пользователя", "Написать service unit", "Включить автозапуск и пережить reboot"],
    reboot=True, minutes=20,
    task="""\
Скрипт `/opt/lab/web.py` — простой HTTP-сервер на `127.0.0.1:8080` (отвечает `hello from labweb`). Сейчас он нигде не запущен.

1. Создайте **системного пользователя** `labweb` без домашнего каталога и без входа (`/usr/sbin/nologin`).
2. Напишите unit `/etc/systemd/system/labweb.service`: запуск `python3 /opt/lab/web.py` **от имени `labweb`**, политика перезапуска `on-failure`, установка в `multi-user.target`.
3. Включите сервис в автозапуск и запустите его.

Проверка **перезагрузит машину** и затем убедится, что сервис поднялся сам и отвечает. Права администратора — через `sudo`.
""",
    hints=["`sudo useradd --system --no-create-home --shell /usr/sbin/nologin labweb`.", "Нужные секции unit: `[Unit]`, `[Service]` (User=, ExecStart=, Restart=) и `[Install]` (WantedBy=multi-user.target).", "После создания файла: `sudo systemctl daemon-reload && sudo systemctl enable --now labweb`."],
    checks=[
        ("service_active", "Сервис labweb активен после reboot", "Сервис поднялся после перезагрузки", "labweb не запущен после перезагрузки"),
        ("enabled_for_boot", "Сервис включён в автозапуск", "Автозапуск включён", "labweb не включён в автозапуск (systemctl enable)"),
        ("runs_as_labweb", "Процесс работает от labweb", "Процесс работает от непривилегированного пользователя", "Процесс сервиса должен работать от пользователя labweb, а не от root"),
        ("answers", "Сервис отвечает на :8080", "Сервис отвечает", "http://127.0.0.1:8080 не отвечает hello from labweb"),
        ("restart_policy", "Задана политика Restart", "Политика перезапуска задана", "В unit должна быть политика Restart=on-failure (или always)"),
    ],
    setup=r"""
install -d /opt/lab
cat > /opt/lab/web.py <<'EOT'
import http.server, socketserver

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"hello from labweb\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", 8080), H).serve_forever()
EOT
chmod 755 /opt/lab/web.py
""",
    validate=r"""
chk service_active 'systemctl is-active --quiet labweb'
chk enabled_for_boot 'systemctl is-enabled --quiet labweb'
chk runs_as_labweb '[ "$(ps -o user= -p $(systemctl show -p MainPID --value labweb) | tr -d " ")" = labweb ]'
chk answers 'curl -s -m 3 http://127.0.0.1:8080 | grep -q "hello from labweb"'
chk restart_policy 'case "$(systemctl show -p Restart --value labweb)" in on-failure|always|on-abnormal) true;; *) false;; esac'
""",
    solution=r"""
sudo useradd --system --no-create-home --shell /usr/sbin/nologin labweb
sudo tee /etc/systemd/system/labweb.service > /dev/null <<'EOT'
[Unit]
Description=Lab web
After=network.target

[Service]
User=labweb
ExecStart=/usr/bin/python3 /opt/lab/web.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now labweb
""",
    wrong=r"""
sudo tee /etc/systemd/system/labweb.service > /dev/null <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/web.py
EOT
sudo systemctl daemon-reload
sudo systemctl start labweb
""",
)

lab(
    id="ld-050", title="Порядок запуска: зависимость сервиса от подготовленного ресурса",
    description="Сервис падает при холодной загрузке, потому что стартует раньше своей зависимости. Задайте зависимости в unit.",
    skills=["After=", "Requires=", "oneshot", "порядок загрузки"],
    objectives=["Увидеть гонку при загрузке", "Задать After= и Requires=", "Получить чистую загрузку без отказов"],
    reboot=True, minutes=20,
    task="""\
`labapp.service` нужен ресурс, который готовит `labdata.service` (oneshot: через ~4 с создаёт `/run/labdata/ready`). Оба сервиса включены в автозапуск, но порядка между ними нет, поэтому при загрузке `labapp` иногда стартует раньше и падает с сообщением `labdata not ready`.

Задайте в unit `labapp` **зависимость и порядок**: он должен запускаться **после** `labdata.service` и **требовать** его. Править сам `labdata` и приложение не нужно. Лучше использовать drop-in (`systemctl edit labapp`).

Проверка перезагрузит машину: `labapp` должен подняться **без единого отказа** в журнале этой загрузки (задержки и повторы `Restart=` — не решение).
""",
    hints=["`sudo systemctl cat labapp labdata` покажет оба unit. `After=` задаёт порядок, `Requires=` — зависимость.", "Drop-in: `sudo systemctl edit labapp` и добавить секцию `[Unit]` с `After=labdata.service` и `Requires=labdata.service`."],
    checks=[
        ("ordered_and_required", "labapp: After= и Requires= на labdata", "Порядок и зависимость заданы", "В unit labapp нет After=labdata.service и Requires=labdata.service"),
        ("app_running", "labapp активен после reboot", "labapp работает после перезагрузки", "labapp не запущен после перезагрузки"),
        ("clean_boot", "Загрузка без отказов labapp", "Холодная загрузка чистая", "В журнале этой загрузки есть отказы labapp (not ready)"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/lab
cat > /opt/lab/app.py <<'EOT'
import os, sys, time
if not os.path.exists("/run/labdata/ready"):
    print("labdata not ready", file=sys.stderr)
    sys.exit(1)
print("labapp started", flush=True)
while True:
    time.sleep(5)
EOT
cat > /etc/systemd/system/labdata.service <<'EOT'
[Unit]
Description=Lab data (готовится 4 секунды)

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'sleep 4; mkdir -p /run/labdata; touch /run/labdata/ready'

[Install]
WantedBy=multi-user.target
EOT
cat > /etc/systemd/system/labapp.service <<'EOT'
[Unit]
Description=Lab app

[Service]
ExecStart=/usr/bin/python3 /opt/lab/app.py

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable labdata.service labapp.service >/dev/null 2>&1
""",
    validate=r"""
chk ordered_and_required 'systemctl show -p After --value labapp | grep -qw labdata.service && systemctl show -p Requires --value labapp | grep -qw labdata.service'
chk app_running 'systemctl is-active --quiet labapp'
chk clean_boot '[ "$(journalctl -b -u labapp --no-pager -o cat | grep -c "labdata not ready")" = 0 ] && [ "$(systemctl show -p NRestarts --value labapp)" = 0 ]'
""",
    solution=r"""
sudo mkdir -p /etc/systemd/system/labapp.service.d
printf '[Unit]\nAfter=labdata.service\nRequires=labdata.service\n' | sudo tee /etc/systemd/system/labapp.service.d/order.conf > /dev/null
sudo systemctl daemon-reload
""",
    wrong=r"""
sudo mkdir -p /etc/systemd/system/labapp.service.d
printf '[Service]\nRestart=always\nRestartSec=5\n' | sudo tee /etc/systemd/system/labapp.service.d/retry.conf > /dev/null
sudo systemctl daemon-reload
""",
)

lab(
    id="ld-051", title="Инцидент: служба в цикле перезапуска из-за WorkingDirectory",
    description="Служба бесконечно перезапускается. Найдите причину по статусу и журналу и исправьте unit.",
    skills=["systemctl status", "journalctl -u", "WorkingDirectory=", "status=200/CHDIR"],
    objectives=["Прочитать причину из status и journal", "Исправить unit", "Добиться стабильной работы"],
    minutes=20,
    task="""\
**Инцидент.** Служба `labapp.service` постоянно перезапускается (`systemctl status labapp` показывает счётчик рестартов, `journalctl -u labapp` — причину). Приложение пишет heartbeat в `/var/lib/labapp/hb`, а сейчас этот файл не обновляется.

Найдите причину, **исправьте unit** (не приложение) и перезапустите службу. После исправления служба должна работать стабильно: без новых рестартов и ошибок в журнале.
""",
    hints=["`systemctl status labapp` и `journalctl -u labapp -n 20`: ищите код вида `status=200/CHDIR`.", "`WorkingDirectory=` указывает на несуществующий каталог. Приложения лежат в `/opt/labapp/releases/1`.", "После правки unit: `sudo systemctl daemon-reload && sudo systemctl restart labapp`."],
    checks=[
        ("service_stable", "labapp активен, рестарты не растут", "Служба работает стабильно", "labapp не активен или продолжает перезапускаться"),
        ("workdir_valid", "WorkingDirectory существует", "Рабочий каталог корректен", "WorkingDirectory в unit должен указывать на существующий каталог"),
        ("heartbeat_alive", "heartbeat обновляется", "Приложение пишет heartbeat", "Файл /var/lib/labapp/hb не обновляется"),
        ("clean_journal", "В журнале нет CHDIR за последние секунды", "Журнал чистый", "В журнале всё ещё свежие ошибки CHDIR"),
    ],
    setup=r"""
install -d /opt/labapp/releases/1 /var/lib/labapp
cat > /opt/labapp/releases/1/run.py <<'EOT'
import time
while True:
    with open("/var/lib/labapp/hb", "w") as f:
        f.write(str(time.time()))
    time.sleep(1)
EOT
cat > /etc/systemd/system/labapp.service <<'EOT'
[Unit]
Description=Lab app

[Service]
WorkingDirectory=/opt/labapp/current
ExecStart=/usr/bin/python3 run.py
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labapp.service >/dev/null 2>&1 || true
sleep 3
""",
    validate=r"""
n1=$(systemctl show -p NRestarts --value labapp); sleep 3; n2=$(systemctl show -p NRestarts --value labapp)
t1=$(stat -c %Y /var/lib/labapp/hb 2>/dev/null || echo 0); sleep 2; t2=$(stat -c %Y /var/lib/labapp/hb 2>/dev/null || echo 0)
chk service_stable 'systemctl is-active --quiet labapp && [ "$n1" = "$n2" ]'
chk workdir_valid '[ -d "$(systemctl show -p WorkingDirectory --value labapp)" ]'
chk heartbeat_alive '[ "$t2" -gt "$t1" ]'
chk clean_journal '[ "$(journalctl -u labapp --since "-6 seconds" --no-pager -o cat | grep -c CHDIR)" = 0 ]'
""",
    solution=r"""
sudo sed -i 's#^WorkingDirectory=.*#WorkingDirectory=/opt/labapp/releases/1#' /etc/systemd/system/labapp.service
sudo systemctl daemon-reload
sudo systemctl restart labapp
sleep 7
""",
    wrong="sudo systemctl stop labapp\n",
    alt={"alt_symlink": "sudo ln -sfn /opt/labapp/releases/1 /opt/labapp/current\nsudo systemctl restart labapp\nsleep 7\n"},
)

lab(
    id="ld-052", title="Restart и лимит повторов: лечим временный сбой, показываем постоянный",
    description="Настройте политику перезапуска так, чтобы кратковременный сбой восстанавливался, а постоянный был виден оператору.",
    skills=["Restart=", "StartLimitBurst", "StartLimitIntervalSec", "systemctl is-failed"],
    objectives=["Включить автоперезапуск", "Ограничить число повторов", "Не скрыть постоянную ошибку"],
    exercise_timeout=25, minutes=25,
    task="""\
Два сервиса:

- `flaky.service` падает при первых двух запусках, потом работает (временный сбой);
- `broken.service` падает **всегда** (постоянная ошибка).

Настройте **оба** (в unit или drop-in) так, чтобы:

- `Restart=on-failure` с небольшой паузой (`RestartSec=`);
- **явно** заданы `StartLimitIntervalSec=` и `StartLimitBurst=` (не больше 10 повторов);
- `flaky` в итоге **работает**, а `broken` после исчерпания лимита остаётся в состоянии **failed** (виден оператору), а не перезапускается бесконечно.

Проверка сама сбросит состояния и запустит оба сервиса заново.
""",
    hints=["`Restart=on-failure`, `RestartSec=1`, `StartLimitIntervalSec=30`, `StartLimitBurst=4` — в секциях `[Service]` и `[Unit]` соответственно.", "Бесконечный рестарт даёт `StartLimitIntervalSec=0` или `Restart=always` без лимита — так делать нельзя."],
    checks=[
        ("flaky_recovers", "flaky восстановился после временных сбоев", "Временный сбой вылечен", "flaky не работает: не заданы Restart=on-failure и лимиты"),
        ("broken_visible", "broken остановлен лимитом и в состоянии failed", "Постоянный сбой виден оператору", "broken должен оказаться в состоянии failed после исчерпания лимита повторов"),
        ("limits_explicit", "StartLimit* заданы явно и ≤ 10", "Лимиты заданы явно", "В конфигурации должны быть явные StartLimitIntervalSec и StartLimitBurst (≤ 10)"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/lab
cat > /opt/lab/flaky.py <<'EOT'
import os, sys, time
p = "/var/lib/lab/flaky.count"
n = int(open(p).read()) if os.path.exists(p) else 0
open(p, "w").write(str(n + 1))
if n < 2:
    print("flaky: crash #%d" % (n + 1), file=sys.stderr)
    sys.exit(1)
while True:
    time.sleep(5)
EOT
printf 'import sys\nprint("broken: permanent failure", file=sys.stderr)\nsys.exit(1)\n' > /opt/lab/broken.py
for n in flaky broken; do
cat > /etc/systemd/system/$n.service <<EOT
[Unit]
Description=Lab $n

[Service]
ExecStart=/usr/bin/python3 /opt/lab/$n.py
EOT
done
systemctl daemon-reload
""",
    exercise=r"""
sudo systemctl stop flaky broken 2>/dev/null
sudo systemctl reset-failed flaky broken 2>/dev/null
sudo rm -f /var/lib/lab/flaky.count
sudo systemctl daemon-reload
sudo systemctl start flaky broken 2>/dev/null
sleep 9
true
""",
    validate=r"""
chk flaky_recovers 'systemctl is-active --quiet flaky'
chk broken_visible 'systemctl is-failed --quiet broken && [ "$(systemctl show -p NRestarts --value broken)" -le 10 ]'
chk limits_explicit 'for u in flaky broken; do systemctl cat $u | grep -q "^StartLimitBurst=" && systemctl cat $u | grep -q "^StartLimitIntervalSec=" && [ "$(systemctl show -p StartLimitBurst --value $u)" -le 10 ] || exit 1; done'
""",
    solution=r"""
for u in flaky broken; do
  sudo mkdir -p /etc/systemd/system/$u.service.d
  printf '[Unit]\nStartLimitIntervalSec=30\nStartLimitBurst=4\n\n[Service]\nRestart=on-failure\nRestartSec=1\n' | sudo tee /etc/systemd/system/$u.service.d/restart.conf > /dev/null
done
sudo systemctl daemon-reload
""",
    wrong=r"""
for u in flaky broken; do
  sudo mkdir -p /etc/systemd/system/$u.service.d
  printf '[Unit]\nStartLimitIntervalSec=0\n\n[Service]\nRestart=always\nRestartSec=1\n' | sudo tee /etc/systemd/system/$u.service.d/restart.conf > /dev/null
done
sudo systemctl daemon-reload
""",
)

lab(
    id="ld-053", title="Timer с догоном пропущенного запуска и разбросом времени",
    description="Запускайте задачу по расписанию через systemd timer с Persistent= и RandomizedDelaySec=.",
    skills=["systemd timer", "OnCalendar=", "Persistent=", "RandomizedDelaySec="],
    objectives=["Написать timer к существующему service", "Не терять запуск при выключенной машине", "Разнести запуски по времени"],
    reboot=True, minutes=20,
    task="""\
`labbackup.service` (oneshot) выполняет резервное копирование. Создайте для него **timer** `/etc/systemd/system/labbackup.timer`:

- запуск **ежедневно в 03:00** (`OnCalendar=`);
- `Persistent=true` — пропущенный запуск догоняется после включения машины;
- `RandomizedDelaySec=` больше нуля (разброс);
- установка в `timers.target`, включите и запустите timer.

Проверка перезагрузит машину и убедится, что timer активен и расписание видно (`systemctl list-timers`).
""",
    hints=["Секции timer: `[Unit]`, `[Timer]` (OnCalendar, Persistent, RandomizedDelaySec), `[Install]` (WantedBy=timers.target).", "`sudo systemctl enable --now labbackup.timer`, затем `systemctl list-timers labbackup.timer`."],
    checks=[
        ("timer_active", "Timer активен и включён", "Timer активен после reboot", "labbackup.timer не включён или не активен после перезагрузки"),
        ("persistent_random", "Persistent=yes и RandomizedDelaySec > 0", "Догон и разброс настроены", "Нужны Persistent=true и RandomizedDelaySec больше нуля"),
        ("schedule_visible", "Расписание 03:00 видно, unit валиден", "Расписание задано", "У timer нет ближайшего запуска или unit не проходит systemd-analyze verify"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/lab
printf '#!/bin/bash\ndate +%%F-%%T >> /var/lib/lab/backup.log\n' > /opt/lab/backup.sh
chmod 755 /opt/lab/backup.sh
cat > /etc/systemd/system/labbackup.service <<'EOT'
[Unit]
Description=Lab backup

[Service]
Type=oneshot
ExecStart=/opt/lab/backup.sh
EOT
systemctl daemon-reload
""",
    validate=r"""
T=labbackup.timer
chk timer_active 'systemctl is-active --quiet $T && systemctl is-enabled --quiet $T'
chk persistent_random '[ "$(systemctl show -p Persistent --value $T)" = yes ] && [ "$(systemctl show -p RandomizedDelayUSec --value $T)" != 0 ]'
chk schedule_visible 'systemctl show -p TimersCalendar --value $T | grep -q "03:00" && [ -n "$(systemctl show -p NextElapseUSecRealtime --value $T)" ] && [ "$(systemd-analyze verify /etc/systemd/system/$T 2>&1 | grep -ci error)" = 0 ]'
""",
    solution=r"""
sudo tee /etc/systemd/system/labbackup.timer > /dev/null <<'EOT'
[Unit]
Description=Daily lab backup

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now labbackup.timer
""",
    wrong=r"""
sudo tee /etc/systemd/system/labbackup.timer > /dev/null <<'EOT'
[Timer]
OnCalendar=*-*-* 03:00:00

[Install]
WantedBy=timers.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now labbackup.timer
""",
)

lab(
    id="ld-054", title="Инцидент: два unit конфликтуют за порт (socket activation)",
    description="Сервис не стартует: «Address already in use». Найдите связь через socket-активацию и устраните конфликт навсегда.",
    skills=["ss -ltnp", "systemctl list-sockets", ".socket units", "disable/mask"],
    objectives=["Найти владельца порта", "Понять роль socket-юнита", "Устранить конфликт так, чтобы он не вернулся после reboot"],
    reboot=True, minutes=25,
    task="""\
**Инцидент.** `labweb.service` (нужный сервис) не запускается: порт `127.0.0.1:8081` уже занят. Кто держит порт, выясните сами (`ss -ltnp`, `systemctl list-sockets`).

Устраните конфликт так, чтобы **после перезагрузки порт принадлежал `labweb`** (отвечает `labweb v2`). Старый `legacy` больше не нужен, но удалять его файлы не обязательно — достаточно, чтобы он не включался.

Проверка перезагрузит машину.
""",
    hints=["`systemctl list-sockets` показывает `.socket`-юниты: они занимают порт до старта сервиса.", "Остановить мало — после reboot он вернётся. Нужно ещё `disable` (или `mask`) для `legacy.socket` и `legacy.service`."],
    checks=[
        ("labweb_owns_port", "Порт 8081 отвечает labweb v2", "Порт принадлежит labweb", "На 127.0.0.1:8081 должен отвечать labweb v2"),
        ("legacy_not_enabled", "legacy.socket не включён", "legacy не включается при загрузке", "legacy.socket всё ещё включён в автозапуск (disable/mask)"),
        ("labweb_active", "labweb активен после reboot", "labweb активен", "labweb не запущен после перезагрузки"),
    ],
    setup=r"""
install -d /opt/lab
cat > /opt/lab/server.py <<'EOT'
import os, socket, sys
name, ver = sys.argv[1], sys.argv[2]
if os.environ.get("LISTEN_FDS") == "1":
    s = socket.socket(fileno=3)            # сокет передал systemd (socket activation)
else:
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 8081))
    s.listen(5)
while True:
    c, _ = s.accept()
    c.recv(1024)
    c.sendall(b"HTTP/1.0 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (len(name + " " + ver) + 1, (name + " " + ver + "\n").encode()))
    c.close()
EOT
cat > /etc/systemd/system/legacy.socket <<'EOT'
[Socket]
ListenStream=127.0.0.1:8081

[Install]
WantedBy=sockets.target
EOT
cat > /etc/systemd/system/legacy.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/server.py legacy v1
EOT
cat > /etc/systemd/system/labweb.service <<'EOT'
[Unit]
Description=Lab web v2

[Service]
ExecStart=/usr/bin/python3 /opt/lab/server.py labweb v2
Restart=no

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now legacy.socket >/dev/null 2>&1
systemctl enable labweb.service >/dev/null 2>&1
systemctl start labweb.service >/dev/null 2>&1 || true
""",
    validate=r"""
chk labweb_owns_port '[ "$(curl -s -m 3 http://127.0.0.1:8081 | tr -d "\n")" = "labweb v2" ]'
chk legacy_not_enabled 'st=$(systemctl is-enabled legacy.socket 2>&1); [ "$st" != enabled ]'
chk labweb_active 'systemctl is-active --quiet labweb'
""",
    solution=r"""
sudo systemctl disable --now legacy.socket
sudo systemctl disable legacy.service 2>/dev/null || true
sudo systemctl restart labweb
""",
    wrong=r"""
sudo systemctl stop legacy.socket
sudo systemctl restart labweb
""",
)

lab(
    id="ld-057", title="Журнал: первый сбой после заданного времени и boot ID",
    description="Найдите в journald первое сообщение об отказе после контрольной метки времени и сопоставьте его с идентификатором загрузки.",
    skills=["journalctl --since", "journalctl -u", "-o json", "_BOOT_ID"],
    objectives=["Отфильтровать журнал по времени и юниту", "Выбрать первую запись после метки", "Определить boot ID"],
    minutes=20,
    task="""\
Служба `labcrash.service` несколько раз падала и писала в журнал строки вида `CRASH: code=N`. Время контрольной метки лежит в `~/cutoff.txt`.

Найдите **первое** сообщение `CRASH:` **после** этой метки и запишите в `~/first_failure.txt` три строки:

```
unit=labcrash.service
message=<текст сообщения, например CRASH: code=7>
boot=<идентификатор загрузки (_BOOT_ID), в которую это произошло>
```

Падения **до** метки — ложный след, их учитывать не нужно. Читать системный журнал нужно через `sudo`.
""",
    hints=["`sudo journalctl -u labcrash.service --since \"$(cat ~/cutoff.txt)\" -o cat` — сообщения после метки.", "Boot ID: `sudo journalctl -u labcrash.service --since ... -o json | head -1` и поле `_BOOT_ID` (или `journalctl --list-boots`)."],
    checks=[
        ("unit_ok", "unit=labcrash.service", "Юнит указан верно", "В first_failure.txt должна быть строка unit=labcrash.service"),
        ("message_ok", "message: первое падение после метки", "Сообщение найдено верно", "message не совпадает с первым CRASH после контрольной метки"),
        ("boot_ok", "boot: текущий _BOOT_ID", "boot ID указан верно", "boot должен совпадать с идентификатором загрузки этой записи"),
    ],
    setup=r"""
install -d /var/lib/lab
cat > /etc/systemd/system/labcrash.service <<'EOT'
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo "CRASH: code=$(cat /var/lib/lab/code)" >&2; exit 1'
EOT
systemctl daemon-reload
echo 11 > /var/lib/lab/code; systemctl start labcrash.service 2>/dev/null || true
sleep 2
date +%Y-%m-%dT%H:%M:%S > /home/student/cutoff.txt
chown student:student /home/student/cutoff.txt
sleep 1.2
echo 42 > /var/lib/lab/code; systemctl start labcrash.service 2>/dev/null || true
sleep 1
echo 77 > /var/lib/lab/code; systemctl start labcrash.service 2>/dev/null || true
""",
    validate=r"""
F=/home/student/first_failure.txt
boot=$(tr -d "-" < /proc/sys/kernel/random/boot_id)
chk unit_ok 'grep -qx "unit=labcrash.service" $F'
chk message_ok '[ "$(grep ^message= $F | cut -d= -f2-)" = "CRASH: code=42" ]'
chk boot_ok '[ "$(grep ^boot= $F | cut -d= -f2- | tr -d "-")" = "$boot" ]'
""",
    solution=r"""
cut=$(cat ~/cutoff.txt)
msg=$(sudo journalctl -u labcrash.service --since "$cut" -o cat | grep -m1 '^CRASH:')
boot=$(sudo journalctl -u labcrash.service --since "$cut" -o json | head -n 1 | python3 -c 'import sys, json; print(json.loads(sys.stdin.readline())["_BOOT_ID"])')
printf 'unit=labcrash.service\nmessage=%s\nboot=%s\n' "$msg" "$boot" > ~/first_failure.txt
""",
    wrong=r"""
msg=$(sudo journalctl -u labcrash.service -o cat | grep -m1 '^CRASH:')
printf 'unit=labcrash.service\nmessage=%s\nboot=unknown\n' "$msg" > ~/first_failure.txt
""",
)

lab(
    id="ld-059", title="Persistent journal с разумным лимитом места",
    description="Включите постоянное хранение журнала и ограничьте его размер, чтобы записи переживали перезагрузку.",
    skills=["journald.conf", "Storage=persistent", "SystemMaxUse", "journalctl --list-boots"],
    objectives=["Включить persistent storage", "Задать дисковый бюджет", "Подтвердить сохранение после reboot"],
    reboot=True, minutes=20,
    task="""\
Сейчас журнал хранится только в памяти и пропадает при перезагрузке (задано `Storage=volatile`).

Настройте journald так, чтобы:

- журнал **сохранялся на диск** (`Storage=persistent`);
- занимал **не больше 100 МБ** (`SystemMaxUse=`, укажите разумное значение, например `50M`);
- конфигурация лежала в drop-in `/etc/systemd/journald.conf.d/` (с номером больше, чем у существующего `00-lab.conf`);
- изменения вступили в силу (перезапустите `systemd-journald`).

Проверка запишет метку в журнал, **перезагрузит машину** и проверит, что метка видна в предыдущей загрузке.
""",
    hints=["Создайте `/etc/systemd/journald.conf.d/50-persistent.conf` с секцией `[Journal]`: `Storage=persistent` и `SystemMaxUse=50M`.", "Конфигурация с большим номером переопределяет меньший. После правки: `sudo systemctl restart systemd-journald`."],
    exercise_timeout=20,
    checks=[
        ("storage_persistent", "Storage=persistent и каталог журнала есть", "Журнал хранится на диске", "Нужны Storage=persistent и каталог /var/log/journal"),
        ("size_limited", "SystemMaxUse ≤ 100M", "Размер журнала ограничен", "Задайте SystemMaxUse не больше 100M"),
        ("survives_reboot", "Метка из прошлой загрузки видна", "Записи пережили перезагрузку", "Записи прошлой загрузки не сохранились (проверьте, что journald перезапущен)"),
    ],
    setup=r"""
install -d /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=volatile\n' > /etc/systemd/journald.conf.d/00-lab.conf
rm -rf /var/log/journal
systemctl restart systemd-journald
""",
    exercise=r"""
sudo logger -t labmark "LABMARK-BEFORE-REBOOT"
sleep 1
true
""",
    validate=r"""
chk storage_persistent '[ -d /var/log/journal ] && systemd-analyze cat-config systemd/journald.conf 2>/dev/null | grep -E "^Storage=" | tail -n 1 | grep -qx "Storage=persistent"'
chk size_limited 'v=$(systemd-analyze cat-config systemd/journald.conf 2>/dev/null | grep -E "^SystemMaxUse=" | tail -n 1 | cut -d= -f2); [ -n "$v" ] && [ "$(numfmt --from=iec "${v%B}")" -le 104857600 ]'
chk survives_reboot 'journalctl -b -1 --no-pager 2>/dev/null | grep -q LABMARK-BEFORE-REBOOT'
""",
    solution=r"""
printf '[Journal]\nStorage=persistent\nSystemMaxUse=50M\n' | sudo tee /etc/systemd/journald.conf.d/50-persistent.conf > /dev/null
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald
""",
    wrong=r"""
printf '[Journal]\nSystemMaxUse=50M\n' | sudo tee /etc/systemd/journald.conf.d/50-limit.conf > /dev/null
sudo systemctl restart systemd-journald
""",
)

lab(
    id="ld-061", title="logrotate для приложения с открытым файловым дескриптором",
    description="Настройте ротацию лога так, чтобы приложение, держащее файл открытым, не терялось и продолжало писать в новый файл.",
    skills=["logrotate", "postrotate", "SIGHUP", "открытый FD"],
    objectives=["Понять, что rename не меняет открытый дескриптор", "Сообщить приложению о ротации", "Не потерять записи"],
    exercise_timeout=25, minutes=25,
    task="""\
Служба `lablogger.service` непрерывно пишет в `/var/log/lab/app.log` строки `line N` и держит файл **открытым**. При получении `SIGHUP` она **переоткрывает** лог.

Напишите `/etc/logrotate.d/lablogger`: ротировать `/var/log/lab/app.log` (`rotate 3`, без сжатия), а после ротации **сообщать службе о смене файла** (`postrotate` с отправкой `SIGHUP`, например `systemctl kill -s HUP lablogger`). Вариант `copytruncate` **не годится**: он может терять записи.

Проверка выполнит `logrotate -f` под нагрузкой и убедится, что: ротированный файл появился, **новый `app.log` растёт**, а нумерация `line N` по всем файлам **непрерывна** (ничего не потеряно).
""",
    hints=["В конфиге: `/var/log/lab/app.log { rotate 3; missingok; nocompress; postrotate ... endscript }`.", "Отправить сигнал службе: `/usr/bin/systemctl kill -s HUP lablogger.service`."],
    checks=[
        ("rotated", "Появился ротированный файл", "Ротация выполнена", "После logrotate нет ротированного файла app.log.1"),
        ("new_log_grows", "Новый app.log продолжает расти", "Приложение пишет в новый файл", "Новый app.log не растёт: приложение пишет в ротированный файл (нужен postrotate с SIGHUP)"),
        ("no_lost_lines", "Нумерация записей непрерывна", "Записи не потеряны", "В логах пропущены записи (copytruncate теряет данные)"),
    ],
    setup=r"""
install -d /opt/lab /var/log/lab
cat > /opt/lab/logger.py <<'EOT'
import signal, time

PATH = "/var/log/lab/app.log"
f = open(PATH, "a", buffering=1)
n = 0

def reopen(*_):
    global f
    f.close()
    f = open(PATH, "a", buffering=1)

signal.signal(signal.SIGHUP, reopen)
while True:
    n += 1
    f.write("line %d\n" % n)
    time.sleep(0.05)
EOT
cat > /etc/systemd/system/lablogger.service <<'EOT'
[Unit]
Description=Lab logger

[Service]
ExecStart=/usr/bin/python3 /opt/lab/logger.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now lablogger.service >/dev/null 2>&1
sleep 2
""",
    exercise=r"""
sudo rm -f /var/lib/logrotate/status /var/log/lab/app.log.*
sleep 1
sudo logrotate -f /etc/logrotate.d/lablogger 2>/dev/null
sleep 2
sudo logrotate -f /etc/logrotate.d/lablogger 2>/dev/null
sleep 2
echo done > /tmp/.rotated
true
""",
    validate=r"""
D=/var/log/lab
s1=$(stat -c %s $D/app.log 2>/dev/null || echo 0); sleep 1; s2=$(stat -c %s $D/app.log 2>/dev/null || echo 0)
cont() { python3 - <<'EOT'
import glob, re
nums = set()
for p in glob.glob("/var/log/lab/app.log*"):
    for line in open(p, errors="replace"):
        m = re.fullmatch(r"line (\d+)\n", line)
        if m:
            nums.add(int(m.group(1)))
print("OK" if nums and max(nums) - min(nums) + 1 == len(nums) else "BAD")
EOT
}
chk rotated '[ -f $D/app.log.1 ]'
chk new_log_grows '[ "$s2" -gt "$s1" ]'
chk no_lost_lines '[ "$(cont)" = OK ]'
""",
    solution=r"""
sudo tee /etc/logrotate.d/lablogger > /dev/null <<'EOT'
/var/log/lab/app.log {
    rotate 3
    missingok
    nocompress
    postrotate
        /usr/bin/systemctl kill -s HUP lablogger.service
    endscript
}
EOT
""",
    wrong=r"""
sudo tee /etc/logrotate.d/lablogger > /dev/null <<'EOT'
/var/log/lab/app.log {
    rotate 3
    missingok
    nocompress
}
EOT
""",
)
