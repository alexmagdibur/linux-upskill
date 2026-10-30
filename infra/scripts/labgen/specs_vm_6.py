"""Задания на учебной машине (LXD), партия 6: наблюдаемость (correlation ID, алерты), SBOM, Ansible (узлы с local-подключением)."""

from __future__ import annotations

from specs_vm_3 import REPO

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append({"runtime_type": "lxd", **kw})


ANS = "cd /home/student/ansible 2>/dev/null\n"

lab(
    id="ld-063", validate_timeout=45, title="Correlation ID через прокси, приложение и worker",
    description="Сквозной идентификатор запроса: nginx генерирует его, передаёт приложению, а приложение — worker-у; один ID виден во всех трёх журналах.",
    skills=["$request_id", "proxy_set_header", "log_format", "трассировка запроса"],
    objectives=["Сгенерировать ID на входе", "Передать заголовком вниз по цепочке", "Найти запрос по ID во всех логах"],
    minutes=30,
    task="""\
Цепочка: **nginx** (`127.0.0.1:8090`) → **приложение** (`127.0.0.1:9100`, пишет `/var/log/lab/app.log`) → **worker** (читает очередь, пишет `/var/log/lab/worker.log`).

Приложение берёт идентификатор из заголовка `X-Request-ID` и передаёт его worker-у, но nginx его не формирует и в свой журнал не пишет.

Настройте nginx (`/etc/nginx/conf.d/trace.conf`):

- формат журнала доступа с `rid=$request_id`, запись в `/var/log/nginx/trace.log`;
- передача `X-Request-ID: $request_id` приложению (`proxy_set_header`).

Результат: после запроса `curl http://127.0.0.1:8090/order` **один и тот же** ID виден в журналах nginx, приложения и worker-а.
""",
    hints=["`log_format trace '$remote_addr rid=$request_id \"$request\"'; access_log /var/log/nginx/trace.log trace;` (log_format — на уровне http, т. е. в conf.d вне server).", "`proxy_set_header X-Request-ID $request_id;` в `location /` перед `proxy_pass`; затем `sudo nginx -t && sudo systemctl reload nginx`."],
    exercise_timeout=15,
    checks=[
        ("nginx_logs_rid", "nginx пишет rid=…", "ID есть в журнале nginx", "В /var/log/nginx/trace.log нет rid=<id> для запроса"),
        ("app_sees_rid", "приложение логирует тот же ID", "ID дошёл до приложения", "В app.log нет ID запроса (проверьте proxy_set_header X-Request-ID)"),
        ("worker_sees_rid", "worker логирует тот же ID", "ID дошёл до worker-а", "В worker.log нет ID запроса"),
    ],
    setup=r"""
install -d /opt/lab /var/log/lab /var/lib/lab/queue
cat > /opt/lab/traceapp.py <<'EOT'
import http.server, os, socketserver, time

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        rid = self.headers.get("X-Request-ID", "-")
        with open("/var/log/lab/app.log", "a") as f:
            f.write("rid=%s path=%s\n" % (rid, self.path))
        with open("/var/lib/lab/queue/%d.job" % (time.time() * 1000), "w") as f:
            f.write(rid)
        self.send_response(200); self.send_header("Content-Length", "3"); self.end_headers(); self.wfile.write(b"ok\n")
    def log_message(self, *a):
        pass

socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", 9100), H).serve_forever()
EOT
cat > /opt/lab/traceworker.py <<'EOT'
import glob, os, time
while True:
    for p in sorted(glob.glob("/var/lib/lab/queue/*.job")):
        rid = open(p).read().strip()
        with open("/var/log/lab/worker.log", "a") as f:
            f.write("rid=%s processed\n" % rid)
        os.remove(p)
    time.sleep(0.3)
EOT
for u in app worker; do
cat > /etc/systemd/system/lab-trace$u.service <<EOT
[Service]
ExecStart=/usr/bin/python3 /opt/lab/trace$u.py
[Install]
WantedBy=multi-user.target
EOT
done
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/trace.conf <<'EOT'
server {
    listen 127.0.0.1:8090;
    location / { proxy_pass http://127.0.0.1:9100; }
}
EOT
systemctl daemon-reload
systemctl enable --now lab-traceapp lab-traceworker nginx >/dev/null 2>&1
sleep 1
""",
    exercise="sudo nginx -t >/dev/null 2>&1 && sudo systemctl reload nginx\nsleep 1\ntrue\n",
    validate=r"""
: > /var/log/lab/app.log; : > /var/log/lab/worker.log
curl -s -m 4 http://127.0.0.1:8090/order >/dev/null
sleep 2
rid=$(tail -n 1 /var/log/nginx/trace.log 2>/dev/null | grep -o "rid=[0-9a-f]\{16,\}" | cut -d= -f2)
chk nginx_logs_rid '[ -n "$rid" ]'
chk app_sees_rid '[ -n "$rid" ] && grep -q "rid=$rid" /var/log/lab/app.log'
chk worker_sees_rid '[ -n "$rid" ] && grep -q "rid=$rid" /var/log/lab/worker.log'
""",
    solution=r"""
sudo tee /etc/nginx/conf.d/trace.conf > /dev/null <<'EOT'
log_format trace '$remote_addr rid=$request_id "$request"';
server {
    listen 127.0.0.1:8090;
    access_log /var/log/nginx/trace.log trace;
    location / {
        proxy_set_header X-Request-ID $request_id;
        proxy_pass http://127.0.0.1:9100;
    }
}
EOT
sudo nginx -t && sudo systemctl reload nginx
""",
    wrong="sudo tee /etc/nginx/conf.d/trace.conf > /dev/null <<'EOT'\nlog_format trace '$remote_addr rid=$request_id \"$request\"';\nserver {\n    listen 127.0.0.1:8090;\n    access_log /var/log/nginx/trace.log trace;\n    location / { proxy_pass http://127.0.0.1:9100; }\n}\nEOT\nsudo systemctl reload nginx\n",
)

lab(
    id="ld-154", validate_timeout=45, title="Алерт на ошибки и latency с окном и защитой от шума",
    description="Напишите проверку «ALERT/OK» по журналу запросов: доля ошибок и p95-задержка в скользящем окне, минимум запросов.",
    skills=["скользящее окно", "error rate", "p95", "минимальный объём выборки"],
    objectives=["Считать метрики за окно", "Не шуметь при малой выборке", "Игнорировать данные вне окна"],
    minutes=40,
    task="""\
Напишите исполняемый скрипт `/usr/local/bin/lab-alert`: `lab-alert ЖУРНАЛ ТЕКУЩЕЕ_ВРЕМЯ_EPOCH`. Формат строк журнала: `<epoch> <http_status> <latency_ms>`.

Правила:

- окно — последние **300 секунд**: строки с `epoch > NOW-300` и `epoch <= NOW`;
- если в окне **меньше 20** запросов — вывод `OK insufficient-data`;
- иначе `ALERT` (с причиной после слова), если доля ответов 5xx в окне **≥ 5 %** или **p95 задержки > 500 мс** (p95 = элемент с индексом `ceil(0.95·n)−1` в отсортированном списке задержек); иначе `OK`;
- вывод первым словом `ALERT` или `OK`, код возврата 0.

Скрипт можно писать на bash, awk или Python.
""",
    hints=["Удобно на Python: прочитать строки, отфильтровать окно, посчитать долю 5xx и p95.", "Проверьте на собственных мини-журналах: ошибки вне окна не должны вызывать алерт, как и 5 запросов подряд с 500."],
    exercise_timeout=15,
    checks=[
        ("errors_alert", "Доля ошибок ≥ 5% → ALERT", "Алерт по ошибкам", "Журнал с 10% ошибок в окне должен давать ALERT"),
        ("latency_alert", "p95 > 500 мс → ALERT", "Алерт по задержке", "Журнал с p95 > 500 мс должен давать ALERT"),
        ("quiet_ok", "Норма → OK", "В норме тихо", "Нормальный журнал (2% ошибок, быстрые ответы) должен давать OK"),
        ("window_respected", "Ошибки вне окна игнорируются", "Окно учитывается", "Ошибки старше 300 секунд не должны вызывать ALERT"),
        ("min_requests", "Мало запросов → OK insufficient-data", "Малая выборка не шумит", "При менее чем 20 запросах в окне нужен OK insufficient-data"),
    ],
    setup="true\n",
    validate=r"""
NOW=1700000000
gen() { python3 - "$@" <<'EOT'
import sys
kind = sys.argv[1]
now = 1700000000
rows = []
def add(n, status=200, lat=80, age=10):
    for i in range(n):
        rows.append((now - age - i % 100, status, lat))
if kind == "errors":
    add(90); add(10, 500)
elif kind == "latency":
    add(90); add(10, 200, 900)
elif kind == "quiet":
    add(98); add(2, 500)
elif kind == "window":
    add(100)
    add(50, 500, 80, 400)
elif kind == "few":
    add(5, 500)
for r in rows:
    print(*r)
EOT
}
run() { gen "$1" > /tmp/.log_$1; /usr/local/bin/lab-alert /tmp/.log_$1 $NOW | head -n 1; }
chk errors_alert 'run errors | grep -q "^ALERT"'
chk latency_alert 'run latency | grep -q "^ALERT"'
chk quiet_ok 'run quiet | grep -q "^OK"'
chk window_respected 'run window | grep -q "^OK"'
chk min_requests 'run few | grep -q "^OK insufficient-data"'
""",
    solution=r"""
sudo tee /usr/local/bin/lab-alert > /dev/null <<'EOT'
#!/usr/bin/env python3
import math, sys

log, now = sys.argv[1], int(sys.argv[2])
rows = []
for line in open(log):
    parts = line.split()
    if len(parts) != 3:
        continue
    ts, status, lat = int(parts[0]), int(parts[1]), float(parts[2])
    if now - 300 < ts <= now:
        rows.append((status, lat))
n = len(rows)
if n < 20:
    print("OK insufficient-data")
    sys.exit(0)
errors = sum(1 for s, _ in rows if s >= 500) / n
lats = sorted(l for _, l in rows)
p95 = lats[math.ceil(0.95 * n) - 1]
if errors >= 0.05:
    print("ALERT error-rate=%.3f" % errors)
elif p95 > 500:
    print("ALERT p95=%d" % p95)
else:
    print("OK")
EOT
sudo chmod 755 /usr/local/bin/lab-alert
""",
    wrong="sudo tee /usr/local/bin/lab-alert > /dev/null <<'EOT'\n#!/bin/bash\nif grep -q ' 500 ' \"$1\"; then echo ALERT; else echo OK; fi\nEOT\nsudo chmod 755 /usr/local/bin/lab-alert\n",
)

lab(
    id="ld-127", title="SBOM: список пакетов и удаление ненужных runtime-зависимостей",
    description="Сформируйте перечень установленных пакетов приложения и уберите из рабочей системы отладочные зависимости.",
    skills=["dpkg-query", "apt-get remove/autoremove", "SBOM", "минимальный runtime"],
    objectives=["Составить список пакетов с версиями", "Определить ненужные для работы пакеты", "Удалить их вместе с зависимостями"],
    minutes=25,
    task="""\
В системе установлены пакеты приложения: `labapp` (зависит от `labfmt`) и отладочные `labdebug` (зависит от `labgdb-tools`). Политика `/etc/lab/runtime-policy` разрешает в рабочей системе только `labapp` и `labfmt` из семейства `lab*`.

1. Удалите всё лишнее из семейства `lab*` (включая автоматически установленную зависимость `labgdb-tools`), не затронув `labapp` и `labfmt`.
2. После очистки составьте SBOM `~/sbom.txt`: по строке `имя версия` для каждого установленного пакета семейства `lab*`, отсортировано по имени.
""",
    hints=["`dpkg -l 'lab*'`; `sudo apt-get remove -y --purge labdebug` и `sudo apt-get autoremove -y --purge`.", "SBOM: `dpkg-query -W -f='${Package} ${Version}\\n' 'lab*' | sort > ~/sbom.txt`."],
    checks=[
        ("extras_removed", "labdebug и labgdb-tools удалены", "Лишнее удалено", "Пакеты labdebug и labgdb-tools должны быть удалены"),
        ("required_kept", "labapp и labfmt на месте", "Нужное сохранено", "labapp и labfmt должны остаться установленными"),
        ("sbom_ok", "sbom.txt соответствует системе", "SBOM корректен", "sbom.txt должен совпадать со списком установленных lab*-пакетов (имя версия, по алфавиту)"),
    ],
    setup=REPO + r"""
mkdeb labfmt 1.0 'def render(x):
    return str(x)'
mkdeb labapp 1.0 'VERSION = "1.0"' labfmt
mkdeb labgdb-tools 1.0 'TOOLS = True'
mkdeb labdebug 1.0 'DEBUG = True' labgdb-tools
reindex
echo 'deb [trusted=yes] file:/srv/repo ./' > /etc/apt/sources.list.d/labrepo.list
apt-get update -qq 2>/dev/null
apt-get install -y -qq labapp labdebug >/dev/null
mkdir -p /etc/lab; printf 'allow: labapp labfmt\n' > /etc/lab/runtime-policy
""",
    validate=r"""
inst=$(dpkg-query -W -f='${Package} ${Version}\n' 'lab*' 2>/dev/null | sort)
chk extras_removed '! dpkg -s labdebug 2>/dev/null | grep -q "^Status: install ok installed" && ! dpkg -s labgdb-tools 2>/dev/null | grep -q "^Status: install ok installed"'
chk required_kept 'dpkg -s labapp 2>/dev/null | grep -q "install ok installed" && dpkg -s labfmt 2>/dev/null | grep -q "install ok installed"'
chk sbom_ok '[ -n "$inst" ] && [ "$(sort /home/student/sbom.txt)" = "$inst" ] && [ "$(cat /home/student/sbom.txt)" = "$(sort /home/student/sbom.txt)" ]'
""",
    solution=r"""
sudo apt-get remove -y --purge labdebug
sudo apt-get autoremove -y --purge
dpkg-query -W -f='${Package} ${Version}\n' 'lab*' | sort > ~/sbom.txt
""",
    wrong="dpkg-query -W -f='${Package} ${Version}\\n' 'lab*' | sort > ~/sbom.txt\n",
)

lab(
    id="ld-177", title="Ansible inventory: группы и переменные",
    description="Соберите inventory учебных узлов с группами, вложенными группами и переменными.",
    skills=["ansible inventory", "group_vars", "children", "ansible-inventory --list"],
    objectives=["Описать группы и узлы", "Задать переменные групп", "Проверить командой ansible-inventory"],
    minutes=25,
    task="""\
Создайте `~/ansible/inventory.ini` (или `inventory.yml`) для узлов: `web1`, `web2` (группа `web`), `db1` (группа `db`); обе группы входят в группу `prod`.

Переменные (в самом файле или в `group_vars/`):

- группа `web`: `http_port=8080`;
- группа `db`: `db_port=5432`;
- группа `prod`: `env=prod`.

Для всех узлов задайте `ansible_connection=local` (учебные узлы работают локально). Проверка: `ansible-inventory -i ~/ansible/inventory.ini --list` (или `.yml`).
""",
    hints=["`[prod:children]` с перечислением `web` и `db`; переменные групп — `[web:vars]`.", "Проверка: `ansible-inventory -i inventory.ini --graph --vars`."],
    exercise_timeout=15,
    checks=[
        ("groups_ok", "Группы web, db и prod:children", "Группы описаны", "Должны быть группы web (web1, web2), db (db1), prod (web и db)"),
        ("web_vars", "web: http_port=8080, env=prod", "Переменные web верны", "У web1/web2 должны быть http_port=8080 и env=prod"),
        ("db_vars", "db: db_port=5432, env=prod", "Переменные db верны", "У db1 должны быть db_port=5432 и env=prod"),
        ("local_conn", "ansible_connection=local у всех", "Подключение local", "У всех узлов должно быть ansible_connection=local"),
    ],
    setup="install -d -o student -g student /home/student/ansible\n",
    validate=r"""
f=$(ls /home/student/ansible/inventory.ini /home/student/ansible/inventory.yml /home/student/ansible/inventory.yaml 2>/dev/null | head -n 1)
J=$(cd /home/student/ansible && ansible-inventory -i "$f" --list 2>/dev/null)
q() { echo "$J" | python3 -c "import json,sys; d=json.load(sys.stdin); h=d['_meta']['hostvars']; g=d; $1"; }
chk groups_ok 'q "assert sorted(g[\"web\"][\"hosts\"])==[\"web1\",\"web2\"]; assert g[\"db\"][\"hosts\"]==[\"db1\"]; assert set(g[\"prod\"][\"children\"])>={\"web\",\"db\"}"'
chk web_vars 'q "assert all(str(h[x][\"http_port\"])==\"8080\" and h[x][\"env\"]==\"prod\" for x in (\"web1\",\"web2\"))"'
chk db_vars 'q "assert str(h[\"db1\"][\"db_port\"])==\"5432\" and h[\"db1\"][\"env\"]==\"prod\""'
chk local_conn 'q "assert all(h[x].get(\"ansible_connection\")==\"local\" for x in (\"web1\",\"web2\",\"db1\"))"'
""",
    solution=r"""
mkdir -p ~/ansible
cat > ~/ansible/inventory.ini <<'EOT'
[web]
web1
web2

[db]
db1

[prod:children]
web
db

[web:vars]
http_port=8080

[db:vars]
db_port=5432

[prod:vars]
env=prod

[all:vars]
ansible_connection=local
EOT
""",
    wrong="mkdir -p ~/ansible\nprintf '[web]\\nweb1\\n' > ~/ansible/inventory.ini\n",
)

lab(
    id="ld-178", validate_timeout=45, title="Идемпотентный Ansible playbook: установка и запуск службы",
    description="Напишите playbook, который при повторном запуске ничего не меняет (changed=0).",
    skills=["ansible-playbook", "идемпотентность", "модули user/file/copy/systemd", "changed=0"],
    objectives=["Использовать модули вместо shell", "Получить changed=0 на втором запуске", "Запустить службу"],
    minutes=35,
    task="""\
Напишите `~/ansible/site.yml` (play для `localhost`, подключение local), который:

- создаёт системного пользователя `labsvc`;
- создаёт каталог `/opt/labsvc` (владелец `labsvc`) и файл `/opt/labsvc/index.html` с текстом `hello`;
- ставит unit `/etc/systemd/system/labsvc.service` (запуск `python3 -m http.server 8070 --bind 127.0.0.1` из `/opt/labsvc` от `labsvc`);
- включает и запускает службу `labsvc`.

Playbook должен быть **идемпотентным**: второй запуск даёт `changed=0`. Запускайте от root (`sudo ansible-playbook -i localhost, -c local ~/ansible/site.yml`).
""",
    hints=["Модули: `ansible.builtin.user`, `file`, `copy` (параметр `content:`), `systemd` (`daemon_reload`, `enabled`, `state`).", "Не используйте `shell`/`command` для того, что умеют модули — они всегда «changed»."],
    exercise_timeout=30,
    checks=[
        ("runs_ok", "playbook выполняется без ошибок", "Playbook выполняется", "ansible-playbook завершился с ошибкой или не найден"),
        ("idempotent", "второй запуск: changed=0", "Playbook идемпотентен", "Повторный запуск playbook изменил систему (changed > 0)"),
        ("service_ok", "labsvc отвечает hello", "Служба работает", "http://127.0.0.1:8070/ не отдаёт hello"),
    ],
    setup="install -d -o student -g student /home/student/ansible\n",
    validate=r"""
cd /home/student/ansible
run() { ansible-playbook -i localhost, -c local site.yml 2>&1; }
r1=$(run); r2=$(run)
sleep 1
chk runs_ok 'echo "$r1" | grep -Eq "failed=0" && echo "$r1" | grep -Eq "unreachable=0"'
chk idempotent 'echo "$r2" | grep -Eq "changed=0" && echo "$r2" | grep -Eq "failed=0"'
chk service_ok '[ "$(curl -s -m 3 http://127.0.0.1:8070/index.html | tr -d "\n")" = hello ]'
""",
    solution=r"""
mkdir -p ~/ansible
cat > ~/ansible/site.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: service user
      ansible.builtin.user:
        name: labsvc
        system: true
        shell: /usr/sbin/nologin
        create_home: false
    - name: app dir
      ansible.builtin.file:
        path: /opt/labsvc
        state: directory
        owner: labsvc
        mode: "0755"
    - name: index
      ansible.builtin.copy:
        content: "hello\n"
        dest: /opt/labsvc/index.html
        owner: labsvc
        mode: "0644"
    - name: unit
      ansible.builtin.copy:
        dest: /etc/systemd/system/labsvc.service
        content: |
          [Service]
          User=labsvc
          WorkingDirectory=/opt/labsvc
          ExecStart=/usr/bin/python3 -m http.server 8070 --bind 127.0.0.1
          [Install]
          WantedBy=multi-user.target
    - name: service
      ansible.builtin.systemd:
        name: labsvc
        daemon_reload: true
        enabled: true
        state: started
EOT
""",
    wrong="mkdir -p ~/ansible\ncat > ~/ansible/site.yml <<'EOT'\n- hosts: localhost\n  connection: local\n  gather_facts: false\n  tasks:\n    - name: everything\n      ansible.builtin.shell: |\n        id labsvc || useradd -r labsvc\n        echo hello > /opt/labsvc/index.html\n      args:\n        creates: /nonexistent\nEOT\n",
)

lab(
    id="ld-179", validate_timeout=45, title="Ansible: template конфига, handler restart и проверка синтаксиса",
    description="Шаблон конфига с переменной, handler перезапуска только при изменении и синтаксическая проверка перед применением.",
    skills=["template", "handlers", "notify", "--syntax-check", "--check --diff"],
    objectives=["Разместить конфиг из шаблона", "Перезапускать службу только при изменении", "Проверять playbook до запуска"],
    minutes=40,
    task="""\
Служба `labsvc2.service` читает порт из `/etc/labsvc2/app.conf` (`port=<N>`) при старте. Напишите `~/ansible/app.yml` (localhost, local), который:

- рендерит `/etc/labsvc2/app.conf` из шаблона `~/ansible/templates/app.conf.j2` с переменной `app_port` (по умолчанию `8071`);
- использует **handler** `restart labsvc2` (уведомляется только при изменении конфигурации);
- проходит `ansible-playbook --syntax-check`.

Проверка запустит playbook, затем с `-e app_port=8072` (служба должна перезапуститься и слушать новый порт), затем ещё раз с `8072` (**без** перезапуска).
""",
    hints=["`ansible.builtin.template` с `notify: restart labsvc2`; `handlers: - name: restart labsvc2` с модулем `systemd`.", "Шаблон: `port={{ app_port }}`; переменная по умолчанию — `vars:` в play."],
    exercise_timeout=40,
    checks=[
        ("syntax_ok", "--syntax-check проходит", "Синтаксис валиден", "ansible-playbook --syntax-check сообщает об ошибке"),
        ("renders_port", "Конфиг и порт из app_port", "Шаблон работает", "Служба должна слушать порт из app_port (8071 по умолчанию, 8072 при переопределении)"),
        ("restart_on_change", "Смена порта → перезапуск", "Handler срабатывает при изменении", "При смене app_port служба не перезапустилась"),
        ("no_restart_same", "Повтор без изменений → без перезапуска", "Лишних перезапусков нет", "Handler перезапустил службу без изменения конфигурации"),
    ],
    setup=r"""
install -d -o student -g student /home/student/ansible /home/student/ansible/templates
install -d /etc/labsvc2 /opt/lab
echo "port=8071" > /etc/labsvc2/app.conf
cat > /opt/lab/svc2.py <<'EOT'
import http.server, socketserver
port = int([l.split("=")[1] for l in open("/etc/labsvc2/app.conf") if l.startswith("port=")][0])
socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", port), http.server.SimpleHTTPRequestHandler).serve_forever()
EOT
cat > /etc/systemd/system/labsvc2.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/svc2.py
WorkingDirectory=/opt/lab
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labsvc2 >/dev/null 2>&1
""",
    validate=r"""
cd /home/student/ansible
run() { ansible-playbook -i localhost, -c local app.yml "$@" 2>&1; }
pid() { systemctl show -p MainPID --value labsvc2; }
listen() { ss -ltn | grep -q "127.0.0.1:$1 "; }
run >/dev/null; sleep 1; p1=$(pid); l1=0; listen 8071 && l1=1
run -e app_port=8072 >/dev/null; sleep 1; p2=$(pid); l2=0; listen 8072 && l2=1
run -e app_port=8072 >/dev/null; sleep 1; p3=$(pid)
chk syntax_ok 'ansible-playbook -i localhost, -c local app.yml --syntax-check'
chk renders_port '[ "$l1" = 1 ] && [ "$l2" = 1 ] && grep -qx "port=8072" /etc/labsvc2/app.conf'
chk restart_on_change '[ "$p1" != "$p2" ]'
chk no_restart_same '[ "$p2" = "$p3" ] && [ "$p2" != 0 ]'
""",
    solution=r"""
mkdir -p ~/ansible/templates
echo 'port={{ app_port }}' > ~/ansible/templates/app.conf.j2
cat > ~/ansible/app.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  vars:
    app_port: 8071
  tasks:
    - name: config
      ansible.builtin.template:
        src: templates/app.conf.j2
        dest: /etc/labsvc2/app.conf
        mode: "0644"
      notify: restart labsvc2
  handlers:
    - name: restart labsvc2
      ansible.builtin.systemd:
        name: labsvc2
        state: restarted
EOT
""",
    wrong="mkdir -p ~/ansible/templates\necho 'port={{ app_port }}' > ~/ansible/templates/app.conf.j2\ncat > ~/ansible/app.yml <<'EOT'\n- hosts: localhost\n  connection: local\n  gather_facts: false\n  vars:\n    app_port: 8071\n  tasks:\n    - ansible.builtin.template:\n        src: templates/app.conf.j2\n        dest: /etc/labsvc2/app.conf\n    - ansible.builtin.systemd:\n        name: labsvc2\n        state: restarted\nEOT\n",
)

lab(
    id="ld-180", validate_timeout=45, title="Дрейф конфигурации одного узла: найти и устранить",
    description="Один из трёх узлов отличается по конфигурации. Найдите его в режиме проверки и приведите к эталону без лишних изменений.",
    skills=["ansible --check --diff", "дрейф конфигурации", "template", "идемпотентность"],
    objectives=["Выявить расхождение без изменений", "Устранить дрейф playbook-ом", "Подтвердить changed=0"],
    minutes=30,
    task="""\
Три узла (`n1`, `n2`, `n3`) хранят конфигурацию в `/etc/lab/n1.conf`, `/etc/lab/n2.conf`, `/etc/lab/n3.conf`. Эталон описан playbook-ом `~/ansible/fleet.yml` (шаблон `templates/node.conf.j2`) — **менять playbook нельзя**.

1. В режиме проверки (`ansible-playbook ... --check --diff`) найдите узел, конфигурация которого разошлась, и запишите его имя в `~/drift.txt` (`n1`, `n2` или `n3`).
2. Устраните дрейф запуском playbook-а (от root, `-i localhost, -c local`). Повторный запуск должен дать `changed=0`.
""",
    hints=["`sudo ansible-playbook -i localhost, -c local ~/ansible/fleet.yml --check --diff` покажет diff для узла, который изменится.", "Затем тот же запуск без `--check`."],
    exercise_timeout=20,
    checks=[
        ("drifted_named", "drift.txt: узел с дрейфом", "Дрейф найден", "В drift.txt должно быть имя узла с расхождением"),
        ("fleet_converged", "Все конфиги совпадают с эталоном", "Дрейф устранён", "Конфигурация узлов всё ещё расходится с эталоном"),
        ("playbook_untouched", "Playbook не изменён", "Playbook не менялся", "Playbook fleet.yml или шаблон изменены"),
    ],
    setup=r"""
install -d -o student -g student /home/student/ansible /home/student/ansible/templates
install -d /etc/lab
cat > /home/student/ansible/templates/node.conf.j2 <<'EOT'
node={{ item }}
worker_threads=8
log_level=info
EOT
cat > /home/student/ansible/fleet.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: node config
      ansible.builtin.template:
        src: templates/node.conf.j2
        dest: "/etc/lab/{{ item }}.conf"
        mode: "0644"
      loop: [n1, n2, n3]
EOT
chown -R student:student /home/student/ansible
cd /home/student/ansible && ansible-playbook -i localhost, -c local fleet.yml >/dev/null 2>&1
sed -i 's/worker_threads=8/worker_threads=2/' /etc/lab/n2.conf
sha256sum /home/student/ansible/fleet.yml /home/student/ansible/templates/node.conf.j2 > /root/.fleet.ref
""",
    validate=r"""
cd /home/student/ansible
chk drifted_named '[ "$(tr -d " \r\n" < /home/student/drift.txt)" = n2 ]'
chk fleet_converged 'ansible-playbook -i localhost, -c local fleet.yml 2>&1 | grep -Eq "changed=0" && for n in n1 n2 n3; do grep -qx "worker_threads=8" /etc/lab/$n.conf || exit 1; done'
chk playbook_untouched 'sha256sum -c /root/.fleet.ref >/dev/null 2>&1'
""",
    solution=r"""
cd ~/ansible
sudo ansible-playbook -i localhost, -c local fleet.yml --check --diff | head -20
echo n2 > ~/drift.txt
sudo ansible-playbook -i localhost, -c local fleet.yml
""",
    wrong="echo n1 > ~/drift.txt\nsudo sed -i 's/worker_threads=2/worker_threads=8/' /etc/lab/n2.conf\nsed -i 's/worker_threads=8/worker_threads=2/' ~/ansible/templates/node.conf.j2\n",
)

lab(
    id="ld-181", validate_timeout=45, title="Ansible: секреты в vault отдельно от обычных переменных",
    description="Разделите обычные переменные и секреты, зашифруйте секреты ansible-vault и убедитесь, что в открытом виде их нет.",
    skills=["ansible-vault", "vars vs secrets", "vault password file", "права 0600"],
    objectives=["Вынести секрет в зашифрованный файл", "Оставить обычные переменные открытыми", "Запустить playbook с vault"],
    minutes=35,
    task="""\
Playbook `~/ansible/db.yml` создаёт `/etc/lab/db.conf` из переменных `db_host` (обычная) и `db_password` (секрет `S3cretPass`). Сейчас пароль лежит открытым текстом в `~/ansible/vars/all.yml`.

1. Вынесите секрет в `~/ansible/vars/secrets.yml` и **зашифруйте** его `ansible-vault` (пароль vault — в файле `~/.vault_pass`, права `0600`); в `all.yml` останется только `db_host`.
2. Playbook должен работать с `--vault-password-file ~/.vault_pass`, а `/etc/lab/db.conf` — иметь права `0600` и содержать пароль.
3. В открытом виде в `~/ansible` пароль встречаться не должен.
""",
    hints=["`ansible-vault encrypt vars/secrets.yml --vault-password-file ~/.vault_pass`.", "В playbook добавьте `vars_files: [vars/all.yml, vars/secrets.yml]`."],
    exercise_timeout=25,
    checks=[
        ("vault_encrypted", "secrets.yml зашифрован", "Секреты зашифрованы", "vars/secrets.yml должен быть зашифрован ansible-vault ($ANSIBLE_VAULT)"),
        ("no_plaintext", "Пароля нет в открытом виде", "Пароль не лежит открыто", "Пароль S3cretPass виден в открытом виде в ~/ansible"),
        ("playbook_works", "playbook работает, db.conf с паролем 0600", "Playbook работает с vault", "Playbook с --vault-password-file не создал /etc/lab/db.conf (0600) с паролем"),
        ("vault_pass_safe", ".vault_pass имеет права 0600", "Пароль vault защищён", "Права ~/.vault_pass должны быть 0600"),
    ],
    setup=r"""
install -d -o student -g student /home/student/ansible/vars
install -d /etc/lab
cat > /home/student/ansible/vars/all.yml <<'EOT'
db_host: db.lab.test
db_password: S3cretPass
EOT
cat > /home/student/ansible/db.yml <<'EOT'
- hosts: localhost
  connection: local
  gather_facts: false
  vars_files:
    - vars/all.yml
  tasks:
    - name: db config
      ansible.builtin.copy:
        dest: /etc/lab/db.conf
        content: |
          host={{ db_host }}
          password={{ db_password }}
        mode: "0600"
EOT
chown -R student:student /home/student/ansible
""",
    exercise="true\n",
    validate=r"""
cd /home/student/ansible
rm -f /etc/lab/db.conf
chk vault_encrypted 'head -n 1 vars/secrets.yml | grep -q "^\$ANSIBLE_VAULT"'
chk no_plaintext '! grep -rq S3cretPass /home/student/ansible --exclude-dir=.git'
chk playbook_works 'ansible-playbook -i localhost, -c local db.yml --vault-password-file /home/student/.vault_pass >/dev/null 2>&1 && grep -qx "password=S3cretPass" /etc/lab/db.conf && [ "$(stat -c %a /etc/lab/db.conf)" = 600 ]'
chk vault_pass_safe '[ "$(stat -c %a /home/student/.vault_pass)" = 600 ]'
""",
    solution=r"""
cd ~/ansible
echo 'lab-vault-pass' > ~/.vault_pass; chmod 600 ~/.vault_pass
printf 'db_password: S3cretPass\n' > vars/secrets.yml
ansible-vault encrypt vars/secrets.yml --vault-password-file ~/.vault_pass
printf 'db_host: db.lab.test\n' > vars/all.yml
sed -i 's#    - vars/all.yml#    - vars/all.yml\n    - vars/secrets.yml#' db.yml
""",
    wrong="cd ~/ansible\necho 'x' > ~/.vault_pass\n",
)
