"""Данные лабораторий Module C — Incident Simulation."""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append(kw)


lab(
    id="incident-001", module="incidents", mode="incident", difficulty="junior", minutes=15, xp=150,
    title="Permission denied при старте приложения",
    description="После деплоя приложение не стартует: «Permission denied». Найдите причину и исправьте права, не раздавая лишнего.",
    skills=["ls -l", "chmod", "диагностика прав", "принцип наименьших привилегий"],
    objectives=["Воспроизвести ошибку запуска", "Найти все причины отказа в доступе", "Исправить права без chmod 777"],
    task="""\
**Инцидент.** После релиза сервис `~/app/start.sh` не запускается: `bash: ./start.sh: Permission denied`.
Даже когда скрипт запустится, приложению нужно писать лог в `~/app/logs/app.log`.

Восстановите работу: после вашего исправления `./start.sh` должен запускаться, а приложение — записывать в лог `started OK`.

Ограничения: **не используйте** `chmod 777` и не давайте запись «всем» — только минимально необходимые права; содержимое скрипта менять не нужно.
""",
    hints=["Начните с `ls -l ~/app ~/app/logs` и попробуйте запустить `./start.sh`.", "Причин две: у скрипта нет права исполнения, а у каталога `logs` нет права записи для владельца.", "`chmod u+x` и `chmod u+w` — точечные исправления."],
    checks=[
        ("starts", "Приложение стартует и пишет в лог", "Приложение запущено и пишет лог", "Лог ~/app/logs/app.log не содержит «started OK» — приложение не работает"),
        ("start_executable", "start.sh исполняемый", "start.sh исполняемый", "start.sh не исполняемый"),
        ("script_unchanged", "Скрипт не изменён", "Скрипт не менялся", "Содержимое start.sh изменено — чините права, а не скрипт"),
        ("no_world_write", "Нет прав записи для всех", "Лишних прав не выдано", "Права слишком широкие: запись «всем» запрещена"),
    ],
    setup=r"""
mkdir -p ~/app/logs
cat > ~/app/app.py <<'EOT'
import datetime, os
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "app.log")
with open(path, "a") as f:
    f.write("%s started OK\n" % datetime.datetime.now().isoformat())
EOT
cat > ~/app/start.sh <<'EOT'
#!/bin/bash
cd "$(dirname "$0")" || exit 1
exec python3 app.py
EOT
chmod 644 ~/app/start.sh
chmod 555 ~/app/logs
""",
    exercise=r"""
cd ~/app && timeout 10 ./start.sh > /dev/null 2>&1 < /dev/null
true
""",
    validate=r"""
A=/home/student/app
chk starts 'grep -q "started OK" $A/logs/app.log'
chk start_executable '[ $(( 0$(stat -c %a $A/start.sh) & 0100 )) -ne 0 ]'
chk script_unchanged 'grep -qx "exec python3 app.py" $A/start.sh && [ "$(wc -l < $A/start.sh)" = 3 ]'
chk no_world_write '[ $(( 0$(stat -c %a $A/logs) & 0002 )) -eq 0 ] && [ $(( 0$(stat -c %a $A/start.sh) & 0002 )) -eq 0 ] && [ $(( 0$(stat -c %a $A) & 0002 )) -eq 0 ]'
""",
    solution=r"""
chmod u+x ~/app/start.sh && chmod u+w ~/app/logs
""",
    wrong=r"""
chmod -R 777 ~/app
""",
)

lab(
    id="incident-002", module="incidents", mode="incident", difficulty="junior", minutes=15, xp=150,
    title="Заполненная квота логов в sandbox",
    description="Каталог логов приложения заполнен до отказа, сервис не может писать «No space left on device». Освободите место, сохранив текущий лог.",
    skills=["df", "du", "ls -lS", "ротация логов"],
    objectives=["Диагностировать нехватку места", "Определить, что можно удалить безопасно", "Сохранить текущий лог"],
    writable_dirs=["/var/log/app"],
    task="""\
**Инцидент.** Сервис `~/bin/app.sh` перестал писать в `/var/log/app/app.log`: `No space left on device`.

Найдите причину (`df -h /var/log/app`, `ls -lS /var/log/app`) и освободите место так, чтобы сервис снова мог писать.

Ограничения: **текущий** файл `app.log` удалять и затирать нельзя — в нём важные записи. Нужно оставить не менее 2 МБ свободного места.
""",
    hints=["`df -h /var/log/app` покажет заполнение, `ls -lS /var/log/app` — самые большие файлы.", "Старые ротированные файлы `app.log.N` — кандидаты на удаление; текущий `app.log` не трогайте."],
    checks=[
        ("log_writable", "Сервис снова пишет в лог", "Сервис пишет в лог", "Сервис по-прежнему не может записать строку в app.log"),
        ("current_log_kept", "Текущий лог сохранён", "Текущий лог сохранён", "Текущий app.log удалён или затёрт"),
        ("space_freed", "Свободно более 2 МБ", "Места достаточно", "Свободного места меньше 2 МБ"),
    ],
    setup=r"""
echo "MARKER current-log-keep-me" > /var/log/app/app.log
dd if=/dev/zero of=/var/log/app/app.log.1 bs=1M count=3 2>/dev/null
dd if=/dev/zero of=/var/log/app/app.log.2 bs=1M count=3 2>/dev/null
dd if=/dev/zero of=/var/log/app/app.log.3 bs=1M 2>/dev/null
mkdir -p ~/bin
cat > ~/bin/app.sh <<'EOT'
#!/bin/bash
echo "$(date +%T) service ok" >> /var/log/app/app.log || { echo "ERROR: cannot write log" >&2; exit 1; }
EOT
chmod +x ~/bin/app.sh
true
""",
    exercise=r"""
~/bin/app.sh > /dev/null 2>&1 < /dev/null
true
""",
    validate=r"""
chk log_writable 'tail -n 1 /var/log/app/app.log | grep -q "service ok"'
chk current_log_kept 'grep -q "MARKER current-log-keep-me" /var/log/app/app.log'
chk space_freed '[ "$(df -k --output=avail /var/log/app | tail -n 1 | tr -d " ")" -gt 2048 ]'
""",
    solution=r"""
rm /var/log/app/app.log.1 /var/log/app/app.log.2 /var/log/app/app.log.3
""",
    wrong=r"""
: > /var/log/app/app.log
""",
    alt={"alt_glob": r"""
rm -f /var/log/app/app.log.*
"""},
)

lab(
    id="incident-003", module="incidents", mode="incident", difficulty="middle", minutes=20, xp=150,
    title="Приложение слушает неправильный порт (loopback внутри sandbox)",
    description="Healthcheck ждёт ответ на 127.0.0.1:8080, а приложение поднялось на другом порту. Найдите процесс, исправьте конфигурацию и перезапустите.",
    skills=["ss", "pgrep", "pkill", "конфигурация сервисов", "перезапуск"],
    objectives=["Найти, какой порт слушает приложение", "Исправить конфигурацию", "Корректно перезапустить сервис"],
    task="""\
**Инцидент.** Мониторинг сообщает: `127.0.0.1:8080` не отвечает. Приложение `~/app/server.py` запущено, но живёт не там, где ожидается.

1. Выясните, какой порт слушает приложение (`ss -ltnp`).
2. Исправьте конфигурацию `~/app/config.ini` так, чтобы приложение слушало порт `8080`.
3. **Перезапустите** приложение — старый процесс должен быть остановлен (прежний порт больше не слушается).

Запускать приложение можно так: `python3 ~/app/server.py &`.
""",
    hints=["`ss -ltnp` показывает слушающие порты и процессы.", "Порт задаётся в `~/app/config.ini`. Одной правки файла недостаточно — приложение читает конфиг при старте.", "Остановить старый процесс: `pkill -f app/server.py`, затем запустить заново."],
    checks=[
        ("port_8080", "Приложение отвечает на 8080", "Приложение отвечает на порту 8080", "На 127.0.0.1:8080 нет ответа «healthy»"),
        ("config_port", "В конфиге port=8080", "Конфигурация исправлена", "В config.ini не указан port=8080"),
        ("old_port_closed", "Старый порт 9090 закрыт", "Старый процесс остановлен", "Порт 9090 всё ещё слушается — старый процесс не остановлен"),
    ],
    setup=r"""
mkdir -p ~/app
printf 'port=9090\nname=demo-api\n' > ~/app/config.ini
cat > ~/app/server.py <<'EOT'
import http.server, os, socketserver

cfg = {}
base = os.path.dirname(os.path.abspath(__file__))
for line in open(os.path.join(base, "config.ini")):
    if "=" in line:
        key, value = line.strip().split("=", 1)
        cfg[key] = value


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"healthy\n"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", int(cfg.get("port", "8000"))), Handler).serve_forever()
EOT
setsid nohup python3 ~/app/server.py >/dev/null 2>&1 </dev/null &
sleep 1
""",
    validate=r"""
probe() {
python3 - "$1" <<'EOT'
import socket, sys
try:
    s = socket.create_connection(("127.0.0.1", int(sys.argv[1])), 2)
    s.sendall(b"GET / HTTP/1.0\r\n\r\n")
    data = b""
    while True:
        chunk = s.recv(1024)
        if not chunk:
            break
        data += chunk
    print("OK" if b"healthy" in data else "BAD")
except OSError:
    print("DOWN")
EOT
}
chk port_8080 '[ "$(probe 8080)" = OK ]'
chk config_port 'grep -qx "port=8080" /home/student/app/config.ini'
chk old_port_closed '[ "$(probe 9090)" = DOWN ]'
""",
    solution=r"""
sed -i 's/port=9090/port=8080/' ~/app/config.ini
pkill -f app/server.py
sleep 0.5
setsid nohup python3 ~/app/server.py >/dev/null 2>&1 </dev/null &
sleep 1
""",
    wrong=r"""
sed -i 's/port=9090/port=8080/' ~/app/config.ini
""",
)

lab(
    id="incident-004", module="incidents", mode="incident", difficulty="middle", minutes=20, xp=150,
    title="Неверный путь конфигурации",
    description="Приложение падает: «config not found». Найдите, откуда оно читает конфигурацию, и исправьте путь — не дублируя конфиг.",
    skills=["чтение скриптов", "ln -s", "sed", "переменные окружения"],
    objectives=["Прочитать сообщение об ошибке и скрипт запуска", "Найти фактическое расположение конфига", "Исправить путь постоянно"],
    writable_dirs=["/etc/myapp"],
    task="""\
**Инцидент.** `~/app/run.sh` завершается с ошибкой `FATAL: config not found`.

Рабочий конфиг приложения лежит в `/etc/myapp/`. Выясните, какой путь ищет скрипт, и исправьте проблему **постоянно** (проверка запустит приложение в новой login-сессии).

Требования: оригинальный `/etc/myapp/app.conf` не удалять и не менять; приложение должно читать именно его, а не копию.
""",
    hints=["Прочитайте `~/app/run.sh` и сравните путь из ошибки с содержимым `ls /etc/myapp`.", "Исправить можно путь в скрипте (`sed -i`) или создать символическую ссылку `ln -s`. Копия файла подойдёт хуже — она разойдётся с оригиналом."],
    checks=[
        ("starts_ok", "Приложение стартует с рабочим конфигом", "Приложение стартовало в режиме production", "Приложение не стартует: в логе нет «app started mode=production»"),
        ("reads_real_config", "Приложение читает оригинальный конфиг", "Приложение читает оригинальный /etc/myapp/app.conf", "Приложение читает не оригинальный конфиг (копия или жёстко заданное значение)"),
        ("config_intact", "Оригинальный конфиг цел", "Конфиг не повреждён", "/etc/myapp/app.conf изменён или удалён"),
    ],
    setup=r"""
printf 'MODE=production\nLEVEL=info\n' > /etc/myapp/app.conf
mkdir -p ~/app
cat > ~/app/run.sh <<'EOT'
#!/bin/bash
CONF="${APP_CONFIG:-/etc/myapp/application.conf}"
if [ ! -r "$CONF" ]; then
  echo "FATAL: config not found: $CONF" >&2
  exit 2
fi
. "$CONF"
echo "app started mode=$MODE" >> "$HOME/app/app.log"
EOT
chmod +x ~/app/run.sh
""",
    exercise=r"""
rm -f ~/app/app.log
cp /etc/myapp/app.conf /tmp/.app.conf.bak
timeout 8 bash -lc '~/app/run.sh' > /dev/null 2>&1 < /dev/null
sed -i 's/^MODE=.*/MODE=canary/' /etc/myapp/app.conf
timeout 8 bash -lc '~/app/run.sh' > /dev/null 2>&1 < /dev/null
cp /tmp/.app.conf.bak /etc/myapp/app.conf
true
""",
    validate=r"""
L=/home/student/app/app.log
chk starts_ok 'grep -qx "app started mode=production" $L'
chk reads_real_config 'grep -qx "app started mode=canary" $L'
chk config_intact 'grep -qx "MODE=production" /etc/myapp/app.conf && grep -qx "LEVEL=info" /etc/myapp/app.conf'
""",
    solution=r"""
sed -i 's#/etc/myapp/application.conf#/etc/myapp/app.conf#' ~/app/run.sh
""",
    wrong=r"""
cp /etc/myapp/app.conf /etc/myapp/application.conf
""",
    alt={"alt_symlink": r"""
ln -s /etc/myapp/app.conf /etc/myapp/application.conf
"""},
)

lab(
    id="incident-005", module="incidents", mode="incident", difficulty="middle", minutes=20, xp=150,
    title="Потеря доступа к рабочим файлам после релиза",
    description="Релиз-скрипт «закрутил гайки»: владелец больше не может редактировать файлы проекта. Восстановите доступ, не открывая его всему миру.",
    skills=["chmod -R", "символьные права (X)", "ls -l", "группы"],
    objectives=["Определить, какие права сломаны", "Восстановить права владельца и группы", "Не выдать доступ остальным"],
    task="""\
**Инцидент.** После релиза вы не можете редактировать файлы в `~/workspace`: `Permission denied` (попробуйте `echo x >> ~/workspace/src/main.py`).

Восстановите нормальные права по политике:

- **владелец** — читает и пишет всё, заходит во все каталоги;
- скрипты в `scripts/` (`deploy.sh`, `test.sh`) — **исполняемые** для владельца;
- **группа `devs`** — только чтение (каталоги — чтение и вход);
- **остальные** — никакого доступа;
- содержимое файлов (в т.ч. `data/db.json`) менять не нужно.
""",
    hints=["`ls -lR ~/workspace` покажет, что права урезаны для всех (400/500).", "`chmod -R u+rwX,g+rX,o-rwx ~/workspace` задаёт сразу владельца, группу и остальных; `X` ставит исполнение только каталогам.", "Скриптам `scripts/*.sh` отдельно нужен `u+x`."],
    checks=[
        ("owner_can_edit", "Владелец может писать и заходить", "Владелец может редактировать файлы", "Владелец всё ещё не может писать во все файлы / заходить во все каталоги"),
        ("scripts_executable", "Скрипты исполняемые", "Скрипты исполняемые", "deploy.sh и test.sh должны быть исполняемыми для владельца"),
        ("group_access", "Группа devs читает", "Группа devs имеет чтение", "Группа devs должна читать файлы и входить в каталоги"),
        ("no_world_access", "Остальным доступа нет", "Остальные не имеют доступа", "У «остальных» не должно быть никаких прав (никакого chmod 777)"),
        ("data_intact", "Данные не изменены", "Данные не изменены", "Содержимое data/db.json изменено"),
    ],
    setup=r"""
mkdir -p ~/workspace/src ~/workspace/scripts ~/workspace/data
echo 'print("main")' > ~/workspace/src/main.py
echo 'print("util")' > ~/workspace/src/util.py
printf '#!/bin/bash\necho deploy\n' > ~/workspace/scripts/deploy.sh
printf '#!/bin/bash\necho test\n' > ~/workspace/scripts/test.sh
printf '{"users": 3}\n' > ~/workspace/data/db.json
chgrp -R devs ~/workspace
chmod 400 ~/workspace/src/* ~/workspace/scripts/* ~/workspace/data/*
chmod 500 ~/workspace/src ~/workspace/scripts ~/workspace/data ~/workspace
""",
    validate=r"""
W=/home/student/workspace
chk owner_can_edit '[ -z "$(find $W ! -perm -u+w)" ] && [ -z "$(find $W -type d ! -perm -u+x)" ] && [ -f $W/src/main.py ]'
chk scripts_executable '[ $(( 0$(stat -c %a $W/scripts/deploy.sh) & 0100 )) -ne 0 ] && [ $(( 0$(stat -c %a $W/scripts/test.sh) & 0100 )) -ne 0 ]'
chk group_access '[ -z "$(find $W -type d ! -perm -g+rx)" ] && [ -z "$(find $W -type f ! -perm -g+r)" ] && [ -f $W/data/db.json ]'
chk no_world_access '[ -z "$(find $W -perm /o+rwx)" ] && [ $(( 0$(stat -c %a $W) & 0007 )) -eq 0 ]'
chk data_intact '[ "$(cat $W/data/db.json)" = "{\"users\": 3}" ]'
""",
    solution=r"""
cd ~/workspace && chmod -R u+rwX,g+rX,o-rwx . && chmod u+x scripts/*.sh
""",
    wrong=r"""
chmod -R 777 ~/workspace
""",
    alt={"alt_numeric": r"""
cd ~/workspace && find . -type d -exec chmod 750 {} + && find . -type f -exec chmod 640 {} + && chmod 750 scripts/*.sh
"""},
)
