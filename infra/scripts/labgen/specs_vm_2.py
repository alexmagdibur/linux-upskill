"""Задания на учебной машине (LXD), партия 2: права/ACL/sudo, процессы и память, секреты, расследование, tmpfs и inode, пакеты."""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append({"runtime_type": "lxd", **kw})


AS = r"""as() { runuser -u "$1" -- sh -c "$2"; }
"""

lab(
    id="ld-121", title="Какой пакет владеет бинарником: версия и зависимости",
    description="Определите пакет, которому принадлежит файл, его версию и прямые зависимости средствами dpkg.",
    skills=["dpkg -S", "dpkg -s", "dpkg-query", "зависимости пакетов"],
    objectives=["Найти пакет по файлу", "Узнать установленную версию", "Выписать прямые зависимости"],
    minutes=15,
    task="""\
Бинарник `/usr/bin/jq` установлен из пакета. Запишите в `~/pkg.txt` три строки:

```
package=<имя пакета, которому принадлежит /usr/bin/jq>
version=<установленная версия пакета>
depends=<прямые зависимости (Depends) через запятую, только имена пакетов без версий и альтернатив>
```
""",
    hints=["`dpkg -S /usr/bin/jq` показывает владельца файла.", "`dpkg-query -W -f='${Version}\\n' jq` и `dpkg-query -W -f='${Depends}\\n' jq` — версия и зависимости."],
    checks=[
        ("package_ok", "package: владелец /usr/bin/jq", "Пакет определён верно", "package должен быть пакетом, которому принадлежит /usr/bin/jq"),
        ("version_ok", "version: установленная версия", "Версия верна", "version не совпадает с установленной версией пакета"),
        ("depends_ok", "depends: прямые зависимости", "Зависимости верны", "depends должен содержать имена пакетов из Depends (без версий)"),
    ],
    setup="true\n",
    validate=r"""
F=/home/student/pkg.txt
pkg=$(dpkg -S /usr/bin/jq | cut -d: -f1)
ver=$(dpkg-query -W -f='${Version}' "$pkg")
norm() { tr ',' '\n' | sed 's/([^)]*)//g; s/|.*//; s/:[a-z0-9]*$//; s/ //g' | grep -v '^$' | sort -u; }
want=$(dpkg-query -W -f='${Depends}' "$pkg" | norm)
got=$(grep ^depends= $F | cut -d= -f2- | norm)
chk package_ok '[ "$(grep ^package= $F | cut -d= -f2- | tr -d " ")" = "$pkg" ]'
chk version_ok '[ "$(grep ^version= $F | cut -d= -f2- | tr -d " ")" = "$ver" ]'
chk depends_ok '[ -n "$want" ] && [ "$got" = "$want" ]'
""",
    solution=r"""
pkg=$(dpkg -S /usr/bin/jq | cut -d: -f1)
ver=$(dpkg-query -W -f='${Version}' "$pkg")
deps=$(dpkg-query -W -f='${Depends}' "$pkg" | sed 's/ ([^)]*)//g; s/, /,/g')
printf 'package=%s\nversion=%s\ndepends=%s\n' "$pkg" "$ver" "$deps" > ~/pkg.txt
""",
    wrong="printf 'package=jq-wrong\\nversion=0.0\\ndepends=libc6\\n' > ~/pkg.txt\n",
)

lab(
    id="ld-028", title="Сервисный пользователь: ровно нужные права на файлы",
    description="Создайте пользователя без интерактивного входа и дайте ему только необходимый доступ.",
    skills=["useradd --system", "nologin", "chown", "chmod", "runuser"],
    objectives=["Создать сервисную учётную запись", "Выдать чтение конфига и запись только в data/", "Не открыть соседние секреты"],
    minutes=20,
    task="""\
Служба будет работать от пользователя `labsvc`. Файлы лежат в `/srv/labsvc` (сейчас каталог доступен только root), рядом лежит секрет `/srv/secret/key`.

1. Создайте **системного** пользователя `labsvc`: без домашнего каталога и с оболочкой `/usr/sbin/nologin`.
2. `labsvc` должен **читать** `/srv/labsvc/app.conf`, но **не изменять** его.
3. `labsvc` должен **писать** в каталог `/srv/labsvc/data/`.
4. `/srv/secret/key` должен остаться **недоступным** для `labsvc` (и остальных).

Права проверяются запуском команд от имени `labsvc`. Права администратора — через `sudo`.
""",
    hints=["`sudo useradd --system --no-create-home --shell /usr/sbin/nologin labsvc`.", "Каталог и конфиг: владелец root, группа labsvc, режимы 750/640; каталог data — владелец labsvc.", "Не используйте `chmod -R 777`: секрет станет доступен всем."],
    checks=[
        ("user_ok", "labsvc: системный, nologin, без home", "Пользователь создан правильно", "labsvc должен быть системным пользователем с оболочкой nologin и без домашнего каталога"),
        ("reads_config", "labsvc читает app.conf", "Конфиг читается", "labsvc не может прочитать /srv/labsvc/app.conf"),
        ("config_readonly", "labsvc не может менять app.conf", "Конфиг защищён от записи", "labsvc может изменить app.conf — а не должен"),
        ("writes_data", "labsvc пишет в data/", "Запись в data/ разрешена", "labsvc не может писать в /srv/labsvc/data"),
        ("secret_closed", "Секрет закрыт", "Секрет закрыт", "/srv/secret/key доступен labsvc или всем: закройте доступ"),
    ],
    setup=r"""
install -d -m 700 /srv/labsvc /srv/labsvc/data /srv/secret
echo "port=8080" > /srv/labsvc/app.conf; chmod 600 /srv/labsvc/app.conf
echo "TOP-SECRET" > /srv/secret/key; chmod 600 /srv/secret/key
""",
    validate=AS + r"""
chk user_ok 'u=$(getent passwd labsvc); [ -n "$u" ] && echo "$u" | grep -q ":/usr/sbin/nologin$" && [ "$(id -u labsvc)" -lt 1000 ] && [ ! -d "$(echo "$u" | cut -d: -f6)" ]'
chk reads_config 'as labsvc "cat /srv/labsvc/app.conf" | grep -q port=8080'
chk config_readonly '! as labsvc "echo x >> /srv/labsvc/app.conf" && ! as labsvc "rm -f /srv/labsvc/app.conf"'
chk writes_data 'as labsvc "touch /srv/labsvc/data/probe && rm /srv/labsvc/data/probe"'
chk secret_closed '! as labsvc "cat /srv/secret/key" && [ "$(stat -c %a /srv/secret)" != 777 ] && [ $(( 0$(stat -c %a /srv/secret/key) & 0007 )) -eq 0 ]'
""",
    solution=r"""
sudo useradd --system --no-create-home --shell /usr/sbin/nologin labsvc
sudo chown root:labsvc /srv/labsvc /srv/labsvc/app.conf
sudo chmod 750 /srv/labsvc
sudo chmod 640 /srv/labsvc/app.conf
sudo chown labsvc:labsvc /srv/labsvc/data
sudo chmod 750 /srv/labsvc/data
""",
    wrong="sudo useradd -m labsvc\nsudo chmod -R 777 /srv\n",
)

lab(
    id="ld-029", title="Общий каталог: setgid и default ACL для двух групп",
    description="Настройте каталог, где новые файлы наследуют группу и доступны второй группе без chmod 777.",
    skills=["setgid", "setfacl -d", "getfacl", "umask и ACL"],
    objectives=["Наследование группы через setgid", "Доступ второй группы через default ACL", "Закрыть остальных"],
    minutes=25,
    task="""\
Команды `labdev` (пользователь `alice`) и `labops` (пользователь `bob`) работают в каталоге `/srv/shared`. Нужно, чтобы:

- каталог принадлежал группе `labdev`, а новые файлы **наследовали** эту группу (**setgid**);
- участники обеих групп могли **читать и писать** любые новые файлы и каталоги в нём (**default ACL** для `labops` и `labdev`);
- у остальных (пользователь `carol`) доступа **не было** вообще.

Проверка создаёт файл от `alice` с обычной `umask 022` и пишет в него от `bob`.
""",
    hints=["`chgrp labdev /srv/shared && chmod 2770 /srv/shared` — группа и setgid.", "`setfacl -m g:labops:rwx /srv/shared` (доступ сейчас) и `setfacl -d -m g:labops:rwx,g:labdev:rwx /srv/shared` (наследуемый, default)."],
    checks=[
        ("group_inherit", "Новые файлы наследуют группу labdev", "Группа наследуется", "Файл, созданный alice, должен принадлежать группе labdev (setgid)"),
        ("ops_can_write", "bob (labops) пишет в файл alice", "Вторая группа имеет доступ", "bob не может писать в файл, созданный alice (нужен default ACL)"),
        ("others_blocked", "carol не имеет доступа", "Остальным доступ закрыт", "carol может войти в каталог или читать файлы"),
    ],
    setup=r"""
groupadd labdev; groupadd labops
useradd -m -G labdev alice; useradd -m -G labops bob; useradd -m carol
install -d -m 755 /srv/shared
""",
    validate=AS + r"""
rm -f /srv/shared/probe_a
as alice "umask 022; echo from-alice > /srv/shared/probe_a"
chk group_inherit '[ "$(stat -c %G /srv/shared/probe_a)" = labdev ] && [ -g /srv/shared ]'
chk ops_can_write 'as bob "echo from-bob >> /srv/shared/probe_a" && as bob "cat /srv/shared/probe_a" | grep -q from-alice'
chk others_blocked '! as carol "ls /srv/shared" && ! as carol "cat /srv/shared/probe_a"'
rm -f /srv/shared/probe_a
""",
    solution=r"""
sudo chgrp labdev /srv/shared
sudo chmod 2770 /srv/shared
sudo setfacl -m g:labops:rwx /srv/shared
sudo setfacl -d -m g:labops:rwx,g:labdev:rwx,o::--- /srv/shared
""",
    wrong="sudo chmod 777 /srv/shared\n",
)

lab(
    id="ld-030", title="Инцидент: после chmod -R пропал доступ у части команды",
    description="После неудачного chmod -R команда потеряла доступ. Восстановите права по политике, не открывая запись миру.",
    skills=["chmod -R", "символьные права (X)", "группы", "принцип наименьших привилегий"],
    objectives=["Восстановить доступ группе", "Сохранить исполнение скриптов", "Не открыть запись всем"],
    minutes=20,
    task="""\
**Инцидент.** Кто-то выполнил `chmod -R 700 /srv/team`, и участники группы `labdev` (`alice`, `bob`) потеряли доступ к проектным файлам.

Восстановите права на `/srv/team` по политике:

- владелец `root`, группа `labdev` (уже так);
- участники `labdev` **читают и пишут** файлы и **заходят** во все каталоги, могут создавать файлы в `docs/`;
- скрипты `scripts/*.sh` **исполняемые** для группы;
- «остальные» (пользователь `carol`) — **никакого доступа**; **ничего** не должно быть доступно на запись всем (`o+w`).
""",
    hints=["`ls -lR /srv/team` покажет текущие 700.", "`chmod -R g+rwX,o-rwx /srv/team` задаёт группу и остальных; `X` ставит исполнение каталогам и уже исполняемым файлам."],
    checks=[
        ("group_rw", "alice читает/пишет файлы и создаёт файлы в docs/", "Группа работает с файлами", "alice не может читать/писать файлы или создавать файлы в docs/"),
        ("scripts_exec", "Скрипты исполняемы для группы", "Скрипты исполняемы", "scripts/run.sh не запускается от имени alice"),
        ("others_closed", "carol не имеет доступа", "Остальным доступ закрыт", "carol видит содержимое /srv/team"),
        ("no_world_write", "Нет прав записи для всех", "Лишних прав нет", "В /srv/team есть файлы с правом записи для всех (o+w)"),
    ],
    setup=r"""
groupadd labdev
useradd -m -G labdev alice; useradd -m -G labdev bob; useradd -m carol
mkdir -p /srv/team/docs /srv/team/scripts
echo "plan v1" > /srv/team/docs/plan.txt
printf '#!/bin/bash\necho run-ok\n' > /srv/team/scripts/run.sh
chmod +x /srv/team/scripts/run.sh
chown -R root:labdev /srv/team
chmod -R 700 /srv/team
""",
    validate=AS + r"""
chk group_rw 'as alice "cat /srv/team/docs/plan.txt" | grep -q "plan v1" && as alice "echo more >> /srv/team/docs/plan.txt" && as bob "touch /srv/team/docs/bob.txt && rm /srv/team/docs/bob.txt"'
chk scripts_exec '[ "$(as alice "/srv/team/scripts/run.sh")" = run-ok ]'
chk others_closed '! as carol "ls /srv/team" && ! as carol "cat /srv/team/docs/plan.txt"'
chk no_world_write '[ -z "$(find /srv/team -perm /o+w)" ] && [ "$(stat -c %a /srv/team)" != 777 ]'
""",
    solution="sudo chmod -R g+rwX,o-rwx /srv/team\nsudo chmod g+x /srv/team/scripts/run.sh\n",
    wrong="sudo chmod -R 777 /srv/team\n",
)

lab(
    id="ld-031", title="sudo: оператору можно только перезапускать одну службу",
    description="Дайте пользователю право перезапускать одну учебную службу и ничего больше.",
    skills=["sudoers.d", "visudo", "NOPASSWD", "ограничение команд"],
    objectives=["Описать точную команду в sudoers", "Не выдать общий root", "Проверить синтаксис и права файла"],
    minutes=20,
    task="""\
Пользователь `oper` должен уметь выполнять **без пароля** ровно одну команду: `sudo systemctl restart labsvc.service`. Остальное (`restart other.service`, `stop labsvc.service`, `id` и т. д.) должно быть **запрещено**.

Создайте файл в `/etc/sudoers.d/` (например, `oper`) с правами `0440`, синтаксис должен проходить `visudo -c`. Используйте полный путь к `systemctl` и точные аргументы.
""",
    hints=["Правило вида `oper ALL=(root) NOPASSWD: /usr/bin/systemctl restart labsvc.service`.", "Файл создавайте через `sudo tee`, затем `sudo chmod 440 файл` и `sudo visudo -c`."],
    checks=[
        ("can_restart", "oper перезапускает labsvc без пароля", "Нужная команда разрешена", "oper не может выполнить sudo systemctl restart labsvc.service"),
        ("others_denied", "Остальные команды запрещены", "Остальное запрещено", "oper может выполнить лишние команды (other.service, stop, id)"),
        ("syntax_perms", "visudo -c проходит, права 0440", "Синтаксис и права верны", "sudoers содержит ошибки или файл не 0440"),
        ("no_blanket_all", "Нет общего «ALL»", "Нет общего доступа", "В sudo -l для oper не должно быть NOPASSWD: ALL"),
    ],
    setup=r"""
useradd -m oper
for u in labsvc other; do
cat > /etc/systemd/system/$u.service <<EOT
[Service]
ExecStart=/usr/bin/sleep infinity
EOT
done
systemctl daemon-reload
systemctl start labsvc other
""",
    validate=AS + r"""
chk can_restart 'as oper "sudo -n /usr/bin/systemctl restart labsvc.service"'
chk others_denied '! as oper "sudo -n /usr/bin/systemctl restart other.service" && ! as oper "sudo -n /usr/bin/id" && ! as oper "sudo -n /usr/bin/systemctl stop labsvc.service"'
chk syntax_perms 'visudo -c >/dev/null 2>&1 && f=$(grep -l "^oper" /etc/sudoers.d/* | head -n 1) && [ -n "$f" ] && [ "$(stat -c %a $f)" = 440 ]'
chk no_blanket_all '! sudo -l -U oper 2>/dev/null | grep -Eq "NOPASSWD: ALL|\(ALL\) ALL"'
""",
    solution=r"""
echo 'oper ALL=(root) NOPASSWD: /usr/bin/systemctl restart labsvc.service' | sudo tee /etc/sudoers.d/oper > /dev/null
sudo chmod 440 /etc/sudoers.d/oper
sudo visudo -c
""",
    wrong="echo 'oper ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/oper > /dev/null\nsudo chmod 440 /etc/sudoers.d/oper\n",
)

lab(
    id="ld-039", title="Инцидент: приложение исчерпало файловые дескрипторы",
    description="Служба падает с «Too many open files». Подтвердите утечку измерениями и устраните её в коде, а не поднятием лимита.",
    skills=["/proc/PID/fd", "LimitNOFILE", "lsof/ls -l /proc", "утечка дескрипторов"],
    objectives=["Измерить рост числа FD", "Найти утечку", "Исправить код и проверить стабильность"],
    minutes=25,
    task="""\
**Инцидент.** Служба `leaky.service` регулярно падает и перезапускается; в журнале — `Too many open files`. Лимит `LimitNOFILE=128`.

1. Подтвердите **утечку измерениями**: число открытых дескрипторов процесса (`ls /proc/PID/fd | wc -l`) растёт со временем.
2. Найдите в `/opt/lab/leaky.py` место утечки и **исправьте код** (закрывайте файл). Поднимать `LimitNOFILE` нельзя (он должен остаться небольшим).
3. Перезапустите службу: число дескрипторов должно перестать расти.
""",
    hints=["Сравните `ls /proc/$(systemctl show -p MainPID --value leaky)/fd | wc -l` дважды с паузой.", "В коде файлы складываются в список и не закрываются. Достаточно открывать и сразу закрывать (`with open(...)`)."],
    checks=[
        ("service_running", "Служба работает без падений", "Служба работает", "leaky.service не запущена или падает"),
        ("fd_stable", "Число FD не растёт", "Дескрипторы не текут", "Число открытых дескрипторов продолжает расти"),
        ("limit_kept", "LimitNOFILE не завышен", "Лимит не завышен", "LimitNOFILE увеличен — нужно исправить утечку, а не лимит"),
        ("clean_journal", "В журнале нет свежих ошибок", "Журнал чистый", "В журнале есть свежие ошибки «Too many open files»"),
    ],
    setup=r"""
install -d /opt/lab
cat > /opt/lab/leaky.py <<'EOT'
import time
fds = []
while True:
    fds.append(open("/dev/null"))   # дескриптор никогда не закрывается
    time.sleep(0.05)
EOT
cat > /etc/systemd/system/leaky.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/leaky.py
LimitNOFILE=128
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now leaky.service >/dev/null 2>&1
sleep 2
""",
    validate=r"""
sleep 2
pid=$(systemctl show -p MainPID --value leaky); a=$(ls /proc/$pid/fd 2>/dev/null | wc -l); sleep 3
pid2=$(systemctl show -p MainPID --value leaky); b=$(ls /proc/$pid2/fd 2>/dev/null | wc -l)
chk service_running 'systemctl is-active --quiet leaky && [ "$pid" = "$pid2" ]'
chk fd_stable '[ "$pid" = "$pid2" ] && [ "$b" -le $((a + 5)) ]'
chk limit_kept '[ "$(systemctl show -p LimitNOFILE --value leaky)" -le 4096 ]'
chk clean_journal '[ "$(journalctl -u leaky --since "-6 seconds" --no-pager -o cat | grep -ci "too many open files")" = 0 ]'
""",
    solution=r"""
sudo sed -i 's#^    fds.append(open("/dev/null"))#    open("/dev/null").close()#' /opt/lab/leaky.py
sudo systemctl restart leaky
sleep 4
""",
    wrong="sudo mkdir -p /etc/systemd/system/leaky.service.d\nprintf '[Service]\\nLimitNOFILE=1000000\\n' | sudo tee /etc/systemd/system/leaky.service.d/limit.conf > /dev/null\nsudo systemctl daemon-reload\nsudo systemctl restart leaky\nsleep 4\n",
)

lab(
    id="ld-040", title="RSS, VSZ и page cache на живом процессе",
    description="Измерьте на работающем процессе виртуальную и резидентную память и покажите роль page cache.",
    skills=["ps -o rss,vsz", "/proc/PID/status", "/proc/meminfo", "page cache"],
    objectives=["Снять RSS и VSZ процесса", "Увидеть, что VSZ ≫ RSS", "Понять, где живёт page cache"],
    minutes=20,
    task="""\
Служба `labmem.service` держит в памяти ~60 МБ данных, резервирует ещё 300 МБ **не трогая** их и один раз прочитала 40 МБ файла (он остался в page cache).

Запишите в `~/mem_report.txt` (значения — из системы, в КБ):

```
rss_kb=<VmRSS процесса labmem>
vsz_kb=<VmSize процесса labmem>
cached_kb=<Cached из /proc/meminfo>
note=<1–2 фразы: почему VSZ много больше RSS и как с этим связан page cache (используйте слово cache)>
```
""",
    hints=["PID: `systemctl show -p MainPID --value labmem`; затем `grep -E 'VmRSS|VmSize' /proc/PID/status`.", "VSZ — всё адресное пространство, RSS — реально присутствующие страницы. Page cache не входит в RSS процесса."],
    checks=[
        ("rss_ok", "rss_kb ≈ VmRSS процесса", "RSS измерен верно", "rss_kb должен совпасть с VmRSS процесса labmem (±20%)"),
        ("vsz_ok", "vsz_kb ≈ VmSize процесса", "VSZ измерен верно", "vsz_kb должен совпасть с VmSize процесса labmem (±10%) и быть заметно больше RSS"),
        ("cached_ok", "cached_kb: Cached из meminfo", "Cached указан", "cached_kb должен быть значением Cached из /proc/meminfo (не менее 20000 КБ)"),
        ("note_ok", "note про cache", "Объяснение есть", "В note нужно объяснение, упоминающее cache"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/lab
dd if=/dev/urandom of=/var/lib/lab/cache.bin bs=1M count=40 2>/dev/null
cat > /opt/lab/mem.py <<'EOT'
import mmap, time

data = bytearray(b"x") * (60 * 1024 * 1024)      # 60 МБ реально занятой памяти (RSS)
reserve = mmap.mmap(-1, 300 * 1024 * 1024)        # 300 МБ адресного пространства без обращения (только VSZ)
with open("/var/lib/lab/cache.bin", "rb") as f:    # читаем файл целиком: страницы остаются в page cache
    while f.read(1 << 20):
        pass
while True:
    time.sleep(1)
EOT
cat > /etc/systemd/system/labmem.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/mem.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labmem.service >/dev/null 2>&1
sleep 3
""",
    validate=r"""
R=/home/student/mem_report.txt
pid=$(systemctl show -p MainPID --value labmem)
rss=$(awk '/VmRSS/{print $2}' /proc/$pid/status); vsz=$(awk '/VmSize/{print $2}' /proc/$pid/status)
val() { grep "^$1=" $R | cut -d= -f2- | tr -d ' '; }
near() { python3 -c "import sys; a,b,t=float(sys.argv[1]),float(sys.argv[2]),float(sys.argv[3]); sys.exit(0 if abs(a-b)<=t*b else 1)" "$1" "$2" "$3"; }
chk rss_ok 'near "$(val rss_kb)" "$rss" 0.20'
chk vsz_ok 'near "$(val vsz_kb)" "$vsz" 0.10 && [ "$(val vsz_kb)" -gt $(( $(val rss_kb) * 3 )) ]'
chk cached_ok '[ "$(val cached_kb)" -ge 20000 ]'
chk note_ok 'grep ^note= $R | grep -qiE "cache|кэш|кеш"'
""",
    solution=r"""
pid=$(systemctl show -p MainPID --value labmem)
{
  echo "rss_kb=$(awk '/VmRSS/{print $2}' /proc/$pid/status)"
  echo "vsz_kb=$(awk '/VmSize/{print $2}' /proc/$pid/status)"
  echo "cached_kb=$(awk '/^Cached:/{print $2}' /proc/meminfo)"
  echo "note=VSZ включает зарезервированное, но не тронутое адресное пространство, RSS — реально занятые страницы; page cache общий и в RSS не входит"
} > ~/mem_report.txt
""",
    wrong="printf 'rss_kb=1000\\nvsz_kb=2000\\ncached_kb=5\\nnote=не знаю\\n' > ~/mem_report.txt\n",
)

lab(
    id="ld-161", title="Неожиданные слушающие порты и их владельцы",
    description="Найдите TCP-порты, слушающие на всех адресах и не входящие в список разрешённых, и определите процессы-владельцы.",
    skills=["ss -ltnp", "allowlist портов", "PID владельца"],
    objectives=["Составить реальную картину слушающих портов", "Сравнить с белым списком", "Назвать процессы-владельцы"],
    minutes=20,
    task="""\
Разрешённые порты перечислены в `/etc/lab/allowed-ports` (по одному на строку).

Найдите все TCP-порты в состоянии LISTEN на **не-loopback** адресах (`0.0.0.0`, `*`, `[::]`), которых **нет** в этом списке, и запишите в `~/unexpected.txt` по строке на порт в формате:

```
<порт> <PID процесса-владельца> <имя процесса>
```

Процессы завершать не нужно. Информацию о процессах-владельцах `ss` показывает только с `sudo`.
""",
    hints=["`sudo ss -ltnp` — все слушающие TCP-порты и процессы.", "Игнорируйте адреса 127.0.0.1/127.0.0.53/::1; сравните порты со списком `cat /etc/lab/allowed-ports`."],
    checks=[
        ("ports_exact", "Список портов совпадает", "Список неожиданных портов верный", "В unexpected.txt должны быть ровно неожиданные порты (не-loopback, не из allowlist)"),
        ("pids_exact", "PID владельцев верны", "Владельцы определены верно", "PID процессов-владельцев указаны неверно"),
        ("services_alive", "Процессы не завершены", "Процессы не затронуты", "Процессы-владельцы завершены: в этом задании их только находят"),
    ],
    setup=r"""
install -d /opt/lab /etc/lab
printf '22\n8080\n5432\n' > /etc/lab/allowed-ports
cat > /opt/lab/listener.py <<'EOT'
import socket, sys, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((sys.argv[1], int(sys.argv[2])))
s.listen(5)
while True:
    time.sleep(60)
EOT
mk() { cat > /etc/systemd/system/$1.service <<EOT
[Service]
ExecStart=/usr/bin/python3 /opt/lab/listener.py $2 $3
[Install]
WantedBy=multi-user.target
EOT
}
mk labweb 0.0.0.0 8080; mk labdb 127.0.0.1 5432; mk miner 0.0.0.0 31337; mk debugd 0.0.0.0 9229
systemctl daemon-reload
systemctl enable --now labweb labdb miner debugd >/dev/null 2>&1
sleep 2
""",
    validate=r"""
F=/home/student/unexpected.txt
expected() { python3 - <<'EOT'
import re, subprocess
allowed = {l.strip() for l in open("/etc/lab/allowed-ports") if l.strip()}
out = subprocess.run(["ss", "-ltnpH"], capture_output=True, text=True).stdout
res = {}
for line in out.splitlines():
    cols = line.split()
    addr = cols[3]
    host, _, port = addr.rpartition(":")
    if host.strip("[]") in ("127.0.0.1", "::1") or host.startswith("127."):
        continue
    if port in allowed:
        continue
    m = re.search(r"pid=(\d+)", line)
    res[port] = m.group(1) if m else "?"
for p in sorted(res):
    print(p, res[p])
EOT
}
got() { awk 'NF>=2{print $1, $2}' $F | sort; }
want=$(expected | sort)
chk ports_exact '[ -n "$want" ] && [ "$(echo "$want" | cut -d" " -f1)" = "$(got | cut -d" " -f1)" ]'
chk pids_exact '[ -n "$want" ] && [ "$want" = "$(got)" ]'
chk services_alive 'systemctl is-active --quiet miner && systemctl is-active --quiet debugd'
""",
    solution=r"""
python3 - <<'EOT'
import re, subprocess
allowed = {l.strip() for l in open("/etc/lab/allowed-ports") if l.strip()}
out = subprocess.run(["sudo", "ss", "-ltnpH"], capture_output=True, text=True).stdout
lines = []
for line in out.splitlines():
    cols = line.split()
    host, _, port = cols[3].rpartition(":")
    if host.startswith("127.") or host.strip("[]") == "::1" or port in allowed:
        continue
    m = re.search(r'\("([^"]+)",pid=(\d+)', line)
    lines.append("%s %s %s" % (port, m.group(2), m.group(1)))
open("/home/student/unexpected.txt", "w").write("\n".join(lines) + "\n")
EOT
""",
    wrong="echo '8080 1 labweb' > ~/unexpected.txt\n",
)

lab(
    id="ld-165", title="Секреты в аргументах процесса, окружении и правах файлов",
    description="Уберите пароль из командной строки процесса, из unit-файла и защитите хранилище секретов.",
    skills=["EnvironmentFile=", "ps -eo args", "systemctl show", "права 0600"],
    objectives=["Найти утечки секрета", "Перенести секрет в файл с правами 0600", "Сохранить работоспособность службы"],
    minutes=25,
    task="""\
`labsecret.service` запускается с паролем в командной строке (`--password=...`) и в `Environment=` прямо в unit-файле. Эти места читаются любым пользователем (`ps`, `systemctl show`).

Исправьте так, чтобы:

- пароль **не** встречался в аргументах процесса и в unit-файлах (`/etc/systemd/system`);
- пароль лежал в `/etc/lab/secrets.env` (`DB_PASSWORD=...`), владелец `root`, права **0600** (не шире 0640), и подключался через `EnvironmentFile=`;
- служба **работает** и приложение подтверждает вход (в `/var/lib/lab/auth.log` появляется `auth ok`).

Проверка перезапустит службу.
""",
    hints=["`ps -eo args | grep labsecret` и `systemctl show -p Environment labsecret` покажут утечки.", "Создайте `/etc/lab/secrets.env`, `chmod 600`, уберите `Environment=` и `--password=`, добавьте `EnvironmentFile=/etc/lab/secrets.env`."],
    exercise_timeout=20,
    checks=[
        ("not_in_args", "Пароля нет в аргументах процессов", "Пароль не виден в ps", "Пароль виден в аргументах процессов (ps)"),
        ("not_in_units", "Пароля нет в unit-файлах и в show", "Пароль не в unit-файлах", "Пароль остался в unit-файле или в Environment службы"),
        ("secrets_file_safe", "secrets.env: root, 0600/0640", "Файл секретов защищён", "Нужен /etc/lab/secrets.env с владельцем root и правами не шире 0640"),
        ("service_auth_ok", "Служба работает, вход подтверждён", "Служба работает с новым способом передачи", "Служба не работает или не подтверждает вход (auth ok)"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/lab /etc/lab
cat > /opt/lab/secapp.py <<'EOT'
import os, time
ok = os.environ.get("DB_PASSWORD") == "S3cr3tPass"
with open("/var/lib/lab/auth.log", "a") as f:
    f.write("auth ok\n" if ok else "auth failed\n")
while True:
    time.sleep(5)
EOT
cat > /etc/systemd/system/labsecret.service <<'EOT'
[Service]
Environment=DB_PASSWORD=S3cr3tPass
ExecStart=/usr/bin/python3 /opt/lab/secapp.py --user=db --password=S3cr3tPass
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labsecret.service >/dev/null 2>&1
""",
    exercise=r"""
sudo rm -f /var/lib/lab/auth.log
sudo systemctl restart labsecret
sleep 2
true
""",
    validate=r"""
chk not_in_args '! ps -eo args | grep -v grep | grep -q S3cr3tPass'
chk not_in_units '! grep -rq S3cr3tPass /etc/systemd/system && ! systemctl show -p Environment --value labsecret | grep -q S3cr3tPass'
chk secrets_file_safe '[ "$(stat -c %U /etc/lab/secrets.env)" = root ] && [ $(( 0$(stat -c %a /etc/lab/secrets.env) & 0037 )) -eq 0 ] && grep -q "^DB_PASSWORD=" /etc/lab/secrets.env'
chk service_auth_ok 'systemctl is-active --quiet labsecret && grep -qx "auth ok" /var/lib/lab/auth.log'
""",
    solution=r"""
echo 'DB_PASSWORD=S3cr3tPass' | sudo tee /etc/lab/secrets.env > /dev/null
sudo chmod 600 /etc/lab/secrets.env
sudo tee /etc/systemd/system/labsecret.service > /dev/null <<'EOT'
[Service]
EnvironmentFile=/etc/lab/secrets.env
ExecStart=/usr/bin/python3 /opt/lab/secapp.py --user=db
[Install]
WantedBy=multi-user.target
EOT
sudo systemctl daemon-reload
""",
    wrong="sudo chmod 600 /etc/systemd/system/labsecret.service\n",
)

lab(
    id="ld-166", title="Инцидент: подозрительный процесс переживает перезапуск",
    description="Найдите механизм закрепления процесса, соберите артефакты и устраните его так, чтобы он не вернулся после перезагрузки.",
    skills=["ps -ef --forest", "cron @reboot", "ls -la скрытых каталогов", "сбор артефактов"],
    objectives=["Найти процесс и способ его возврата", "Сохранить доказательства до удаления", "Убрать закрепление"],
    reboot=True, minutes=30,
    task="""\
**Инцидент.** В системе работает подозрительный процесс из скрытого каталога `/usr/local/lib/.upd/`. После его остановки он «оживает» после перезагрузки.

1. Найдите процесс и выясните, **как он возвращается** (подсказка: планировщики).
2. **Сохраните артефакты до удаления:** скопируйте скрипт процесса и файл, который его запускает, в `~/evidence/` (с теми же именами файлов).
3. **Остановите** процесс и **уберите механизм закрепления** (скрипт можно удалить).

Проверка перезагрузит машину: процесса не должно быть, а в `~/evidence/` — неизменённые копии.
""",
    hints=["`ps -ef --forest` и `sudo ls -laR /usr/local/lib/.upd`; затем `ls /etc/cron.d /etc/cron.daily` и `systemctl list-timers`.", "Сначала `cp` артефактов в `~/evidence/`, потом `pkill -f` и удаление файла в `/etc/cron.d/`."],
    checks=[
        ("process_gone", "Процесса нет после reboot", "Процесс не вернулся", "Подозрительный процесс снова запущен после перезагрузки"),
        ("persistence_removed", "Механизм закрепления убран", "Закрепление удалено", "В /etc/cron.d остался файл, запускающий процесс"),
        ("evidence_saved", "Артефакты сохранены без изменений", "Артефакты сохранены", "В ~/evidence нет неизменённых копий agent.sh и sysupdate"),
    ],
    setup=r"""
install -d /usr/local/lib/.upd /var/lib/lab
cat > /usr/local/lib/.upd/agent.sh <<'EOT'
#!/bin/bash
# system update helper
while true; do sleep 30; done
EOT
chmod 755 /usr/local/lib/.upd/agent.sh
printf '@reboot root /usr/local/lib/.upd/agent.sh >/dev/null 2>&1 &\n' > /etc/cron.d/sysupdate
sha256sum /usr/local/lib/.upd/agent.sh /etc/cron.d/sysupdate > /var/lib/lab/ref.sha256
( setsid nohup /usr/local/lib/.upd/agent.sh >/dev/null 2>&1 </dev/null & )
sleep 1
""",
    validate=r"""
E=/home/student/evidence
h_agent=$(grep "agent.sh" /var/lib/lab/ref.sha256 | cut -d" " -f1); h_cron=$(grep "sysupdate" /var/lib/lab/ref.sha256 | cut -d" " -f1)
chk process_gone '! pgrep -f "\.upd/agent.sh"'
chk persistence_removed '[ ! -e /etc/cron.d/sysupdate ]'
chk evidence_saved '[ "$(sha256sum $E/agent.sh 2>/dev/null | cut -d" " -f1)" = "$h_agent" ] && [ "$(sha256sum $E/sysupdate 2>/dev/null | cut -d" " -f1)" = "$h_cron" ]'
""",
    solution=r"""
mkdir -p ~/evidence
sudo cp /usr/local/lib/.upd/agent.sh ~/evidence/agent.sh
sudo cp /etc/cron.d/sysupdate ~/evidence/sysupdate
sudo chown -R student:student ~/evidence
sudo pkill -f '.upd/agent.sh'
sudo rm -f /etc/cron.d/sysupdate
sudo rm -rf /usr/local/lib/.upd
""",
    wrong="sudo pkill -f '.upd/agent.sh'\n",
)

lab(
    id="ld-190", title="Инцидент: cron и timer запускают одно и то же задание",
    description="Два планировщика запускают одно задание в одну минуту и портят данные. Устраните двойной запуск и восстановите данные.",
    skills=["cron.d", "systemd timer", "flock", "идемпотентность задания"],
    objectives=["Найти оба триггера", "Оставить один (или сделать задание безопасным)", "Дедуплицировать журнал"],
    exercise_timeout=25, minutes=25,
    task="""\
**Инцидент.** Задание `/opt/lab/job.sh` запускается **и** из cron (`/etc/cron.d/labjob`), **и** по таймеру `labjob.timer`. В журнале `/var/lib/lab/ledger.txt` из-за этого дубли.

1. Устраните двойной запуск: оставьте **один** триггер (или сделайте задание безопасным: блокировка `flock` + пропуск уже записанного слота).
2. **Восстановите данные**: уберите дубликаты из `/var/lib/lab/ledger.txt` (уникальные записи должны сохраниться).

Проверка одновременно «сработает» оба оставшихся триггера: на один слот должна быть **ровно одна** запись.
""",
    hints=["`cat /etc/cron.d/labjob` и `systemctl list-timers labjob.timer` покажут оба триггера.", "Простейшее решение — удалить cron-файл или отключить timer. Журнал: `sort -u -o /var/lib/lab/ledger.txt /var/lib/lab/ledger.txt`."],
    checks=[
        ("no_double_run", "Одновременный запуск даёт одну запись", "Двойного запуска нет", "При одновременном срабатывании триггеров на слот записано не ровно одно выполнение"),
        ("data_repaired", "Журнал без дублей, записи сохранены", "Данные восстановлены", "В ledger.txt остались дубликаты или потеряны уникальные записи"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/lab
cat > /opt/lab/job.sh <<'EOT'
#!/bin/bash
L="${LEDGER:-/var/lib/lab/ledger.txt}"
slot=$(date +%F-%H%M)
sleep 1
echo "run $slot" >> "$L"
EOT
chmod 755 /opt/lab/job.sh
printf '* * * * * root /opt/lab/job.sh\n' > /etc/cron.d/labjob
cat > /etc/systemd/system/labjob.service <<'EOT'
[Service]
Type=oneshot
ExecStart=/opt/lab/job.sh
EOT
cat > /etc/systemd/system/labjob.timer <<'EOT'
[Timer]
OnCalendar=minutely
[Install]
WantedBy=timers.target
EOT
systemctl daemon-reload
systemctl enable --now labjob.timer >/dev/null 2>&1
printf 'run 2026-10-29-0101\nrun 2026-10-29-0101\nrun 2026-10-29-0102\nrun 2026-10-29-0102\nrun 2026-10-29-0103\nrun 2026-10-29-0104\nrun 2026-10-29-0104\n' > /var/lib/lab/ledger.txt
""",
    exercise=r"""
T=/tmp/ledger.test
sudo rm -f $T
sudo systemctl set-environment LEDGER=$T
cronline=$(grep -hv '^#' /etc/cron.d/labjob 2>/dev/null | awk 'NF>6{ $1=$2=$3=$4=$5=$6=""; print }')
if [ -n "$cronline" ]; then sudo env LEDGER=$T bash -c "$cronline" & fi
if systemctl is-active --quiet labjob.timer || systemctl is-enabled --quiet labjob.timer 2>/dev/null; then sudo systemctl start labjob.service & fi
wait
sudo systemctl unset-environment LEDGER
true
""",
    validate=r"""
L=/var/lib/lab/ledger.txt
chk no_double_run '[ "$(wc -l < /tmp/ledger.test)" = 1 ]'
chk data_repaired '[ "$(sort $L | uniq -d | wc -l)" = 0 ] && [ "$(wc -l < $L)" = 4 ]'
""",
    solution=r"""
sudo rm -f /etc/cron.d/labjob
sudo sort -u -o /var/lib/lab/ledger.txt /var/lib/lab/ledger.txt
""",
    wrong="sudo sort -u -o /var/lib/lab/ledger.txt /var/lib/lab/ledger.txt\n",
    alt={"alt_flock": r"""
sudo tee /opt/lab/job.sh > /dev/null <<'EOT'
#!/bin/bash
L="${LEDGER:-/var/lib/lab/ledger.txt}"
slot=$(date +%F-%H%M)
exec 9>/var/lock/labjob.lock
flock 9
grep -qx "run $slot" "$L" 2>/dev/null && exit 0
sleep 1
echo "run $slot" >> "$L"
EOT
sudo sort -u -o /var/lib/lab/ledger.txt /var/lib/lab/ledger.txt
"""},
)

lab(
    id="ld-185", title="Инцидент: сервис отдаёт старый конфиг из symlink — безопасный reload",
    description="Релиз выкатили, но сервис читает старую версию через symlink. Переключите ссылку и перезагрузите конфигурацию без рестарта.",
    skills=["symlink релизов", "ln -sfn", "systemctl reload", "SIGHUP"],
    objectives=["Найти, куда указывает current", "Переключить на новый релиз", "Применить reload, не перезапуская процесс"],
    minutes=20,
    task="""\
**Инцидент.** После выкладки релиза 2 сервис `labsite.service` по-прежнему отвечает старым значением (`curl http://127.0.0.1:8090` → `v1`). Конфиг читается через ссылку `/opt/labsite/current`.

Переключите `current` на `releases/2` и **перезагрузите конфигурацию без рестарта** (`systemctl reload labsite`): процесс (PID) должен остаться тем же, счётчик рестартов — нулевым, а ответ — `v2`.
""",
    hints=["`ls -l /opt/labsite` и `curl -s 127.0.0.1:8090` покажут текущее состояние.", "`sudo ln -sfn /opt/labsite/releases/2 /opt/labsite/current && sudo systemctl reload labsite`."],
    checks=[
        ("serves_v2", "Сервис отвечает v2", "Сервис отдаёт новую версию", "http://127.0.0.1:8090 всё ещё отвечает старым значением"),
        ("symlink_ok", "current → releases/2", "Ссылка указывает на релиз 2", "current должна указывать на /opt/labsite/releases/2"),
        ("no_restart", "PID не менялся, рестартов нет", "Reload выполнен без рестарта", "Сервис был перезапущен (PID изменился): нужен reload, а не restart"),
    ],
    setup=r"""
install -d /opt/lab /opt/labsite/releases/1 /opt/labsite/releases/2 /var/lib/lab
echo v1 > /opt/labsite/releases/1/value; echo v2 > /opt/labsite/releases/2/value
ln -s releases/1 /opt/labsite/current
cat > /opt/lab/site.py <<'EOT'
import http.server, signal, socketserver

def load():
    global value
    value = open("/opt/labsite/current/value").read().strip().encode() + b"\n"

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(value)))
        self.end_headers()
        self.wfile.write(value)
    def log_message(self, *a):
        pass

load()
signal.signal(signal.SIGHUP, lambda *_: load())
socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", 8090), H).serve_forever()
EOT
cat > /etc/systemd/system/labsite.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/site.py
ExecReload=/bin/kill -HUP $MAINPID
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labsite.service >/dev/null 2>&1
sleep 1
systemctl show -p MainPID --value labsite > /var/lib/lab/pid0
""",
    validate=r"""
chk serves_v2 '[ "$(curl -s -m 3 http://127.0.0.1:8090 | tr -d "\n")" = v2 ]'
chk symlink_ok '[ "$(readlink -f /opt/labsite/current)" = /opt/labsite/releases/2 ]'
chk no_restart '[ "$(systemctl show -p MainPID --value labsite)" = "$(cat /var/lib/lab/pid0)" ] && [ "$(systemctl show -p NRestarts --value labsite)" = 0 ]'
""",
    solution="sudo ln -sfn /opt/labsite/releases/2 /opt/labsite/current\nsudo systemctl reload labsite\nsleep 1\n",
    wrong="sudo ln -sfn /opt/labsite/releases/2 /opt/labsite/current\nsudo systemctl restart labsite\nsleep 1\n",
)

lab(
    id="ld-073", title="Исчерпание байтов и исчерпание inode на двух маленьких ФС",
    description="Покажите разницу между «кончилось место» и «кончились inode», найдя, какая из двух файловых систем страдает от чего.",
    skills=["df -h", "df -i", "tmpfs", "inode"],
    objectives=["Читать df по байтам и по inode", "Не путать два вида исчерпания"],
    minutes=20,
    task="""\
В системе две маленькие файловые системы: `/mnt/bytes` и `/mnt/inodes`. Запись в обе сейчас падает с `No space left on device`, но причины **разные**.

Запишите в `~/diag.txt` две строки:

```
bytes_full=<точка монтирования, где закончились БАЙТЫ>
inodes_full=<точка монтирования, где закончились INODE>
```

Подсказка: сравните вывод `df -h` и `df -i`.
""",
    hints=["`df -h /mnt/bytes /mnt/inodes` — байты, `df -i /mnt/bytes /mnt/inodes` — inode.", "Если по байтам почти пусто, а inode 100% — это исчерпание inode."],
    checks=[
        ("bytes_ok", "bytes_full определён верно", "Исчерпание байтов найдено", "bytes_full указан неверно"),
        ("inodes_ok", "inodes_full определён верно", "Исчерпание inode найдено", "inodes_full указан неверно"),
    ],
    setup=r"""
mkdir -p /mnt/bytes /mnt/inodes
mount -t tmpfs -o size=2m tmpfs /mnt/bytes
mount -t tmpfs -o size=64m,nr_inodes=40 tmpfs /mnt/inodes
dd if=/dev/zero of=/mnt/bytes/big bs=1M count=3 2>/dev/null || true
i=0; while touch /mnt/inodes/f$i 2>/dev/null; do i=$((i+1)); done
true
""",
    validate=r"""
F=/home/student/diag.txt
chk bytes_ok '[ "$(grep ^bytes_full= $F | cut -d= -f2- | tr -d " ")" = /mnt/bytes ]'
chk inodes_ok '[ "$(grep ^inodes_full= $F | cut -d= -f2- | tr -d " ")" = /mnt/inodes ]'
""",
    solution=r"""
b=$(df -k --output=target,avail /mnt/bytes /mnt/inodes | awk 'NR>1 && $2<=4 {print $1}')
i=$(df --output=target,iavail /mnt/bytes /mnt/inodes | awk 'NR>1 && $2==0 {print $1}')
printf 'bytes_full=%s\ninodes_full=%s\n' "$b" "$i" > ~/diag.txt
""",
    wrong="printf 'bytes_full=/mnt/inodes\\ninodes_full=/mnt/bytes\\n' > ~/diag.txt\n",
)

lab(
    id="ld-186", title="Инцидент: df показывает свободное место, а запись падает",
    description="Приложение не может создать файл при большом свободном объёме. Найдите причину и освободите ресурс, не тронув нужные данные.",
    skills=["df -i", "inode", "find -empty", "диагностика ENOSPC"],
    objectives=["Заподозрить inode, а не байты", "Найти мусор", "Освободить inode без потери нужных файлов"],
    minutes=25,
    task="""\
**Инцидент.** Скрипт `/opt/lab/writer.sh` пишет файл заданий в `/var/lib/labapp/spool/`, но падает с `No space left on device`, хотя `df -h` показывает много свободного места.

Найдите причину (`df -i`!), освободите ресурс, удалив **только мусор** (пустые файлы в `spool/stale/`). Нужные файлы в `spool/keep/` трогать нельзя. После исправления `writer.sh` должен работать, а занятость inode должна стать ниже 80 %.
""",
    hints=["`df -h /var/lib/labapp/spool` и `df -i /var/lib/labapp/spool` — сравните.", "Мусор — пустые файлы в `spool/stale/`: `find /var/lib/labapp/spool/stale -type f -empty -delete`."],
    exercise_timeout=20,
    checks=[
        ("writer_works", "writer.sh создаёт файл", "Запись снова работает", "writer.sh всё ещё не может создать файл"),
        ("inode_usage_low", "Занятость inode < 80%", "inode освобождены", "inode всё ещё заняты на 80% и больше"),
        ("keep_intact", "Нужные файлы в keep/ целы", "Нужные данные целы", "Файлы в spool/keep удалены или изменены"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/labapp/spool
mount -t tmpfs -o size=64m,nr_inodes=60 tmpfs /var/lib/labapp/spool
mkdir -p /var/lib/labapp/spool/stale /var/lib/labapp/spool/keep
for n in 1 2 3; do echo "important $n" > /var/lib/labapp/spool/keep/data$n; done
i=0; while : > /var/lib/labapp/spool/stale/junk$i 2>/dev/null; do i=$((i+1)); done
printf '#!/bin/bash\necho "job $(date +%%s)" > /var/lib/labapp/spool/job-$$\n' > /opt/lab/writer.sh
chmod 755 /opt/lab/writer.sh
true
""",
    exercise=r"""
mkdir -p /tmp/.ex
sudo /opt/lab/writer.sh > /tmp/.ex/writer.out 2>&1; echo $? > /tmp/.ex/writer.rc
true
""",
    validate=r"""
used=$(df --output=ipcent /var/lib/labapp/spool | tail -n 1 | tr -dc '0-9')
chk writer_works '[ "$(cat /tmp/.ex/writer.rc)" = 0 ] && ls /var/lib/labapp/spool/job-* >/dev/null 2>&1'
chk inode_usage_low '[ "$used" -lt 80 ]'
chk keep_intact '[ "$(cat /var/lib/labapp/spool/keep/data1 /var/lib/labapp/spool/keep/data2 /var/lib/labapp/spool/keep/data3 | wc -l)" = 3 ]'
""",
    solution="sudo find /var/lib/labapp/spool/stale -type f -empty -delete\n",
    wrong="sudo rm -rf /var/lib/labapp/spool/keep\n",
)

lab(
    id="ld-075", title="Инцидент: «Read-only file system» — причина по mount до исправления",
    description="Запись в каталог внезапно даёт Read-only file system. Установите причину по параметрам монтирования и верните запись.",
    skills=["findmnt", "/proc/mounts", "mount -o remount,rw", "диагностика RO"],
    objectives=["Определить причину по опциям mount", "Зафиксировать причину письменно", "Безопасно вернуть rw"],
    minutes=20,
    task="""\
**Инцидент.** Приложение не может писать в `/srv/data`: `Read-only file system`.

1. **Сначала диагностика:** по `findmnt /srv/data` (или `/proc/mounts`) выясните, почему запись невозможна. Запишите в `~/cause.txt` одну строку: путь монтирования и найденный признак (слово `ro`), например `/srv/data ro`.
2. Верните запись **без потери данных** (`remount`, а не размонтирование и не пересоздание).
""",
    hints=["`findmnt -o TARGET,FSTYPE,OPTIONS /srv/data` — смотрите опцию `ro`.", "`sudo mount -o remount,rw /srv/data`."],
    checks=[
        ("cause_recorded", "cause.txt: /srv/data и ro", "Причина зафиксирована", "В cause.txt должны быть путь /srv/data и признак ro"),
        ("writable_again", "Запись в /srv/data работает", "Запись снова работает", "/srv/data всё ещё доступен только для чтения"),
        ("data_intact", "Данные сохранены", "Данные на месте", "Файл marker.txt потерян: нельзя пересоздавать файловую систему"),
    ],
    setup=r"""
mkdir -p /srv/data
mount -t tmpfs -o size=8m tmpfs /srv/data
echo "keep-me" > /srv/data/marker.txt
mount -o remount,ro /srv/data
""",
    validate=r"""
chk cause_recorded 'grep -q "/srv/data" /home/student/cause.txt && grep -qw ro /home/student/cause.txt'
chk writable_again 'touch /srv/data/probe && rm /srv/data/probe'
chk data_intact '[ "$(cat /srv/data/marker.txt)" = keep-me ]'
""",
    solution="echo '/srv/data ro' > ~/cause.txt\nsudo mount -o remount,rw /srv/data\n",
    wrong="sudo umount /srv/data\nsudo mkdir -p /srv/data\n",
)

lab(
    id="ld-076", title="tmpfs для временных данных: лимит и очистка после перезагрузки",
    description="Подключите tmpfs с лимитом размера для временных данных так, чтобы он монтировался при загрузке.",
    skills=["tmpfs", "systemd .mount / fstab", "size=", "findmnt"],
    objectives=["Описать постоянный mount", "Ограничить размер", "Убедиться, что данные не переживают reboot"],
    reboot=True, minutes=20,
    task="""\
Для временных данных приложения нужен каталог `/srv/labtmp` на **tmpfs** размером **16 МБ**, который монтируется **автоматически при загрузке** (через mount-юнит `srv-labtmp.mount` или запись в `/etc/fstab`).

Данные в нём не должны переживать перезагрузку, а запись больше 16 МБ — упираться в лимит.

Проверка запишет файл-метку, **перезагрузит машину** и проверит, что каталог смонтирован как tmpfs 16M, метка исчезла, а запись 20 МБ невозможна.
""",
    hints=["Вариант fstab: строка `tmpfs /srv/labtmp tmpfs size=16M,mode=1777 0 0`, затем `sudo systemctl daemon-reload && sudo mount -a`.", "Вариант systemd: юнит `/etc/systemd/system/srv-labtmp.mount` (`What=tmpfs`, `Where=/srv/labtmp`, `Type=tmpfs`, `Options=size=16M`) и `systemctl enable --now`."],
    exercise_timeout=20,
    checks=[
        ("mounted_tmpfs", "/srv/labtmp — tmpfs после reboot", "tmpfs смонтирован при загрузке", "После перезагрузки /srv/labtmp не смонтирован как tmpfs"),
        ("size_limited", "Размер 16M, запись 20 МБ невозможна", "Лимит размера работает", "Лимит 16M не задан: запись 20 МБ проходит"),
        ("cleaned_on_reboot", "Метка пропала после reboot", "Данные не пережили reboot", "Файл-метка пережил перезагрузку (это не tmpfs)"),
    ],
    setup="mkdir -p /srv/labtmp\n",
    exercise=r"""
sudo sh -c 'echo marker > /srv/labtmp/marker.txt && sync'
true
""",
    validate=r"""
chk mounted_tmpfs '[ "$(findmnt -n -o FSTYPE /srv/labtmp 2>/dev/null)" = tmpfs ]'
chk size_limited '[ "$(findmnt -n -o SIZE /srv/labtmp 2>/dev/null | tr -d " ")" = 16M ] && ! dd if=/dev/zero of=/srv/labtmp/big bs=1M count=20 2>/dev/null'
chk cleaned_on_reboot '[ ! -e /srv/labtmp/marker.txt ]'
rm -f /srv/labtmp/big
""",
    solution=r"""
sudo tee /etc/systemd/system/srv-labtmp.mount > /dev/null <<'EOT'
[Unit]
Description=Lab tmpfs

[Mount]
What=tmpfs
Where=/srv/labtmp
Type=tmpfs
Options=size=16M,mode=1777

[Install]
WantedBy=multi-user.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now srv-labtmp.mount
""",
    wrong="sudo mkdir -p /srv/labtmp\n",
    alt={"alt_fstab": "echo 'tmpfs /srv/labtmp tmpfs size=16M,mode=1777 0 0' | sudo tee -a /etc/fstab > /dev/null\nsudo systemctl daemon-reload\nsudo mount -a\n"},
)
