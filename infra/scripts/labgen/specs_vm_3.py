"""Задания на учебной машине (LXD), партия 3: systemd-песочница, cgroup, пакеты и репозитории, namespaces, диагностика, SSH baseline."""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append({"runtime_type": "lxd", **kw})


# Локальный APT-репозиторий для заданий про пакеты (интернета в учебной машине нет; штатные источники отключаем).
REPO = r"""
mv /etc/apt/sources.list.d/ubuntu.sources /root/ubuntu.sources.off 2>/dev/null || true
mkdir -p /srv/repo
mkdeb() { # имя версия содержимое-модуля [зависимости]
  d=$(mktemp -d); mkdir -p $d/DEBIAN $d/usr/lib/python3/dist-packages
  printf 'Package: %s\nVersion: %s\nArchitecture: all\nMaintainer: Lab <lab@example.com>\nDescription: lab package %s\n' "$1" "$2" "$1" > $d/DEBIAN/control
  [ -n "${4:-}" ] && printf 'Depends: %s\n' "$4" >> $d/DEBIAN/control
  printf '%s\n' "$3" > $d/usr/lib/python3/dist-packages/$1.py
  dpkg-deb --build -Zgzip $d /srv/repo/${1}_${2}_all.deb >/dev/null; rm -rf $d
}
reindex() { (cd /srv/repo && dpkg-scanpackages --multiversion . /dev/null > Packages 2>/dev/null && gzip -kf Packages); }
"""

lab(
    id="ld-055", title="Sandboxing systemd: минимальные права службы",
    description="Ужесточите unit через директивы sandboxing так, чтобы служба работала, но не могла менять систему и читать домашние каталоги.",
    skills=["ProtectSystem", "ProtectHome", "PrivateTmp", "NoNewPrivileges", "ReadWritePaths"],
    objectives=["Включить изоляцию unit", "Оставить службе доступ только к её каталогу", "Подтвердить эффект самой службой"],
    minutes=20,
    task="""\
Служба `labscan.service` работает от root без ограничений. Раз в секунду она пытается (1) создать файл в `/etc`, (2) прочитать каталог `/home/student` и записывает результат в `/var/lib/labapp/probe.txt` (`etc=open|blocked home=open|blocked`). Ещё она обновляет `/var/lib/labapp/heartbeat`.

Ужесточите unit (лучше через drop-in) по принципу минимальных прав:

- `/etc` и система только для чтения (`ProtectSystem=strict` или `full`), но запись в `/var/lib/labapp` **остаётся** (`ReadWritePaths=` или `StateDirectory=`);
- домашние каталоги недоступны (`ProtectHome=`), собственный `/tmp` (`PrivateTmp=`), `NoNewPrivileges=yes`;
- служба продолжает работать: `probe.txt` должен показывать `etc=blocked home=blocked`, а heartbeat обновляться.
""",
    hints=["Через drop-in: `sudo systemctl edit labscan` и секция `[Service]`.", "`ProtectSystem=strict` делает всю ФС read-only — не забудьте `ReadWritePaths=/var/lib/labapp`.", "Проверка эффекта: `sudo systemctl restart labscan; sleep 2; cat /var/lib/labapp/probe.txt`."],
    exercise_timeout=20,
    checks=[
        ("sandbox_props", "ProtectSystem/ProtectHome/PrivateTmp/NoNewPrivileges", "Директивы изоляции включены", "Нужны ProtectSystem=strict|full, ProtectHome=yes|read-only|tmpfs, PrivateTmp=yes, NoNewPrivileges=yes"),
        ("effect_blocked", "Служба не может писать в /etc и читать /home", "Изоляция действует", "probe.txt должен показывать etc=blocked home=blocked"),
        ("still_works", "Служба работает и пишет в свой каталог", "Служба по-прежнему работает", "Служба не работает или не может писать heartbeat в /var/lib/labapp"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/labapp
cat > /opt/lab/scan.py <<'EOT'
import os, time

def try_write(path):
    try:
        with open(path, "w") as f:
            f.write("x")
        os.remove(path)
        return "open"
    except OSError:
        return "blocked"

def try_home():
    try:
        os.listdir("/home/student")
        return "open"
    except OSError:
        return "blocked"

while True:
    with open("/var/lib/labapp/probe.txt", "w") as f:
        f.write("etc=%s home=%s\n" % (try_write("/etc/lab-probe"), try_home()))
    with open("/var/lib/labapp/heartbeat", "w") as f:
        f.write(str(time.time()))
    time.sleep(1)
EOT
cat > /etc/systemd/system/labscan.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/scan.py
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labscan >/dev/null 2>&1
sleep 2
""",
    exercise="sudo systemctl daemon-reload\nsudo systemctl restart labscan\nsleep 3\ntrue\n",
    validate=r"""
prop() { systemctl show -p "$1" --value labscan; }
chk sandbox_props 'case "$(prop ProtectSystem)" in strict|full) true;; *) false;; esac && [ "$(prop ProtectHome)" != no ] && [ "$(prop PrivateTmp)" = yes ] && [ "$(prop NoNewPrivileges)" = yes ]'
chk effect_blocked 'grep -qx "etc=blocked home=blocked" /var/lib/labapp/probe.txt'
chk still_works 'systemctl is-active --quiet labscan && [ $(( $(date +%s) - $(cut -d. -f1 /var/lib/labapp/heartbeat) )) -le 5 ]'
""",
    solution=r"""
sudo mkdir -p /etc/systemd/system/labscan.service.d
sudo tee /etc/systemd/system/labscan.service.d/sandbox.conf > /dev/null <<'EOT'
[Service]
ProtectSystem=strict
ReadWritePaths=/var/lib/labapp
ProtectHome=yes
PrivateTmp=yes
NoNewPrivileges=yes
EOT
""",
    wrong="sudo mkdir -p /etc/systemd/system/labscan.service.d\nprintf '[Service]\\nNoNewPrivileges=yes\\n' | sudo tee /etc/systemd/system/labscan.service.d/x.conf > /dev/null\n",
)

lab(
    id="ld-083", title="Ограничение CPU и RAM службы через cgroup и измерение throttling",
    description="Ограничьте службу по CPU и памяти средствами systemd и докажите по cpu.stat, что ограничение работает.",
    skills=["CPUQuota", "MemoryMax", "cgroup v2", "cpu.stat"],
    objectives=["Выставить лимиты через systemd", "Найти cgroup службы", "Прочитать nr_throttled"],
    minutes=20,
    task="""\
Служба `labburn.service` крутит бесконечный цикл и занимает целое ядро. Ограничьте её:

- `CPUQuota=25%`;
- `MemoryMax=64M`.

Затем **измерьте throttling**: запишите в `~/throttle.txt` строку `nr_throttled=<число>` — значение из `cpu.stat` cgroup этой службы (оно должно быть больше нуля: служба упирается в квоту).
""",
    hints=["`sudo systemctl set-property labburn CPUQuota=25% MemoryMax=64M` применяет лимиты сразу.", "cgroup службы: `/sys/fs/cgroup/system.slice/labburn.service/cpu.stat` — поле `nr_throttled`."],
    exercise_timeout=15,
    checks=[
        ("limits_set", "CPUQuota=25%, MemoryMax=64M", "Лимиты заданы", "Нужны CPUQuota=25% и MemoryMax=64M у labburn"),
        ("really_throttled", "Служба реально упирается в квоту", "Квота действует", "В cpu.stat службы nr_throttled не растёт: ограничение не действует"),
        ("report_ok", "throttle.txt: измеренное значение", "Измерение записано", "В throttle.txt нужна строка nr_throttled=<число > 0, не больше текущего значения>"),
    ],
    setup=r"""
cat > /etc/systemd/system/labburn.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 -c "while True: pass"
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labburn >/dev/null 2>&1
""",
    validate=r"""
cg=/sys/fs/cgroup/system.slice/labburn.service
thr() { awk '/^nr_throttled/{print $2}' $cg/cpu.stat; }
a=$(thr); sleep 3; b=$(thr)
rep=$(grep ^nr_throttled= /home/student/throttle.txt | cut -d= -f2 | tr -d ' ')
chk limits_set '[ "$(systemctl show -p CPUQuotaPerSecUSec --value labburn)" = 250ms ] && [ "$(systemctl show -p MemoryMax --value labburn)" = 67108864 ]'
chk really_throttled '[ "$b" -gt "$a" ]'
chk report_ok '[ -n "$rep" ] && [ "$rep" -gt 0 ] && [ "$rep" -le "$b" ]'
""",
    solution=r"""
sudo systemctl set-property labburn CPUQuota=25% MemoryMax=64M
sleep 4
echo "nr_throttled=$(awk '/^nr_throttled/{print $2}' /sys/fs/cgroup/system.slice/labburn.service/cpu.stat)" > ~/throttle.txt
""",
    wrong="sudo systemctl set-property labburn MemoryMax=64M\necho nr_throttled=999999999 > ~/throttle.txt\n",
)

lab(
    id="ld-084", title="nice и CPU quota на двух конкурирующих службах",
    description="Покажите разницу между приоритетом (nice) и жёстким лимитом (CPU quota): приоритет не ограничивает службу, когда CPU свободен.",
    skills=["nice", "CPUQuota", "CPUWeight", "cgroup cpu.stat"],
    objectives=["Понять, что nice работает только при конкуренции", "Ограничить фоновую службу квотой", "Не навредить критичной службе"],
    minutes=20,
    task="""\
Две службы жгут CPU: критичная `labcrit.service` и фоновая `labbatch.service`. Фоновая не должна отнимать у машины больше **25 % одного ядра даже когда критичная простаивает** (одним `nice` этого не добиться — он действует только при конкуренции).

1. Ограничьте `labbatch` квотой CPU (`CPUQuota=`) и понизьте ей приоритет (`Nice=` > 0).
2. Критичную службу не трогайте: она должна остаться запущенной и без лимитов.

Проверка остановит критичную службу и измерит использование CPU фоновой.
""",
    hints=["`sudo systemctl set-property labbatch CPUQuota=20%` и `sudo systemctl set-property labbatch Nice=10` (Nice можно задать drop-in-ом).", "`systemctl show -p Nice -p CPUQuotaPerSecUSec labbatch` покажет итог."],
    exercise_timeout=15,
    checks=[
        ("batch_capped", "Фоновая служба ≤ 30% ядра в одиночку", "Квота действует", "labbatch в одиночку занимает больше 30% ядра: нужна CPUQuota"),
        ("batch_nice", "Nice > 0 у labbatch", "Приоритет понижен", "У labbatch должен быть Nice > 0"),
        ("crit_untouched", "labcrit работает без квоты", "Критичная служба не тронута", "labcrit остановлена или ограничена по CPU"),
    ],
    setup=r"""
for u in crit batch; do
cat > /etc/systemd/system/lab$u.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 -c "while True: pass"
[Install]
WantedBy=multi-user.target
EOT
done
systemctl daemon-reload
systemctl enable --now labcrit labbatch >/dev/null 2>&1
""",
    exercise="sleep 1\ntrue\n",
    validate=r"""
u1=0; u2=0
systemctl stop labcrit
cg=/sys/fs/cgroup/system.slice/labbatch.service
u1=$(awk '/^usage_usec/{print $2}' $cg/cpu.stat); sleep 4; u2=$(awk '/^usage_usec/{print $2}' $cg/cpu.stat)
share=$(( (u2 - u1) / 40000 ))   # проценты одного ядра за 4 секунды
systemctl start labcrit
chk batch_capped '[ "$share" -le 30 ]'
chk batch_nice '[ "$(systemctl show -p Nice --value labbatch)" -gt 0 ]'
chk crit_untouched 'systemctl is-active --quiet labcrit && [ "$(systemctl show -p CPUQuotaPerSecUSec --value labcrit)" = infinity ]'
""",
    solution="sudo systemctl set-property labbatch CPUQuota=20%\nsudo mkdir -p /etc/systemd/system/labbatch.service.d\nprintf '[Service]\\nNice=10\\n' | sudo tee /etc/systemd/system/labbatch.service.d/nice.conf > /dev/null\nsudo systemctl daemon-reload\nsudo systemctl restart labbatch\n",
    wrong="sudo mkdir -p /etc/systemd/system/labbatch.service.d\nprintf '[Service]\\nNice=15\\n' | sudo tee /etc/systemd/system/labbatch.service.d/nice.conf > /dev/null\nsudo systemctl daemon-reload\nsudo systemctl restart labbatch\n",
)

lab(
    id="ld-060", title="Инцидент: логи перестали записываться — раздел заполнен",
    description="Приложение не может писать журнал из-за заполненного раздела. Освободите место и настройте ротацию, чтобы это не повторилось.",
    skills=["df", "du", "logrotate", "освобождение места"],
    objectives=["Найти, что занимает раздел", "Освободить место, не удаляя текущий лог", "Настроить logrotate"],
    minutes=25,
    task="""\
**Инцидент.** Служба `labapp-log.service` пишет журнал в `/var/log/labapp/app.log`, но записи перестали появляться — раздел `/var/log/labapp` заполнен.

1. Найдите, что занимает место, и освободите его, **не удаляя** текущий `app.log` (в нём нужные записи).
2. Настройте ротацию `/etc/logrotate.d/labapp` (ротация по размеру или по дням, `rotate`, `compress`), которая проходит проверку `logrotate -d`.

Результат: записи снова появляются, свободно не менее 1 МБ.
""",
    hints=["`df -h /var/log/labapp` и `du -ah /var/log/labapp | sort -h | tail`.", "Большой старый архив можно удалить; конфигурацию проверьте `sudo logrotate -d /etc/logrotate.d/labapp`."],
    exercise_timeout=15,
    checks=[
        ("logging_again", "Новые записи появляются", "Журнал снова пишется", "В app.log нет свежих записей"),
        ("space_free", "Свободно ≥ 1 МБ, app.log сохранён", "Место освобождено", "Свободно менее 1 МБ или app.log удалён"),
        ("rotation_configured", "logrotate настроен и валиден", "Ротация настроена", "Нужен /etc/logrotate.d/labapp с rotate, compress и size/daily/weekly (проходит logrotate -d)"),
    ],
    setup=r"""
install -d /opt/lab /var/log/labapp
mount -t tmpfs -o size=4m,mode=755 tmpfs /var/log/labapp
echo "boot-record: important" > /var/log/labapp/app.log
dd if=/dev/zero of=/var/log/labapp/app.log.2023.old bs=1k count=3900 2>/dev/null
cat > /opt/lab/logger.py <<'EOT'
import time
while True:
    try:
        with open("/var/log/labapp/app.log", "a") as f:
            f.write("tick %d\n" % time.time())
    except OSError:
        pass
    time.sleep(0.5)
EOT
cat > /etc/systemd/system/labapp-log.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/logger.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labapp-log >/dev/null 2>&1
dd if=/dev/zero of=/var/log/labapp/filler bs=1k count=400 2>/dev/null || true
rm -f /var/log/labapp/filler
dd if=/dev/zero of=/var/log/labapp/.pad bs=1k count=100000 2>/dev/null || true
mv /var/log/labapp/.pad /var/log/labapp/app.log.2022.old
""",
    validate=r"""
sleep 2
chk logging_again 'now=$(date +%s); last=$(tail -n 1 /var/log/labapp/app.log | awk "{print \$2}"); [ -n "$last" ] && [ $((now - last)) -le 5 ]'
chk space_free '[ "$(df -k --output=avail /var/log/labapp | tail -n 1 | tr -d " ")" -ge 1024 ] && grep -q boot-record /var/log/labapp/app.log'
chk rotation_configured 'f=/etc/logrotate.d/labapp; [ -f $f ] && grep -q "rotate" $f && grep -q "compress" $f && grep -Eq "size|daily|weekly|monthly" $f && logrotate -d $f >/dev/null 2>&1'
""",
    solution=r"""
sudo rm -f /var/log/labapp/app.log.2022.old /var/log/labapp/app.log.2023.old
sudo tee /etc/logrotate.d/labapp > /dev/null <<'EOT'
/var/log/labapp/app.log {
    daily
    size 1M
    rotate 5
    compress
    missingok
    notifempty
    copytruncate
}
EOT
sleep 2
""",
    wrong="sudo rm -f /var/log/labapp/app.log\n",
)

lab(
    id="ld-122", title="Подписанный APT-репозиторий: подключить и установить пакет",
    description="Подключите учебный репозиторий с проверкой подписи (signed-by) и установите из него пакет, не отключая проверку.",
    skills=["apt sources", "signed-by", "gpg --dearmor", "apt-cache policy"],
    objectives=["Импортировать ключ в keyring", "Описать источник с signed-by", "Установить пакет из репозитория"],
    minutes=20,
    task="""\
В `/srv/repo` лежит учебный APT-репозиторий (плоский формат, с подписанным `InRelease`). Открытый ключ — `/srv/repo/key.asc`. Интернета нет, штатные источники отключены.

1. Преобразуйте ключ в формат keyring и положите его в `/etc/apt/keyrings/labrepo.gpg`.
2. Добавьте источник `/etc/apt/sources.list.d/labrepo.list` с `signed-by=` (**без** `trusted=yes` и `allow-insecure`).
3. Обновите списки и установите пакет `labtool`.
""",
    hints=["`gpg --dearmor` превращает ASCII-ключ в бинарный keyring: `sudo gpg --dearmor -o /etc/apt/keyrings/labrepo.gpg /srv/repo/key.asc`.", "Строка источника: `deb [signed-by=/etc/apt/keyrings/labrepo.gpg] file:/srv/repo ./`."],
    checks=[
        ("installed", "labtool установлен", "Пакет установлен", "Пакет labtool не установлен"),
        ("signed_source", "Источник с signed-by и ключом", "Источник подписан", "Источник должен использовать signed-by=/etc/apt/keyrings/labrepo.gpg без trusted=yes"),
        ("from_repo", "Кандидат из file:/srv/repo", "Пакет из учебного репозитория", "apt-cache policy labtool не показывает file:/srv/repo"),
    ],
    setup=REPO + r"""
mkdeb labtool 1.0 'VERSION = "1.0"'
reindex
export GNUPGHOME=$(mktemp -d)
cat > /tmp/gk <<'EOT'
%no-protection
Key-Type: RSA
Key-Length: 2048
Name-Real: Lab Repo
Name-Email: repo@lab.example
Expire-Date: 0
%commit
EOT
gpg --batch --gen-key /tmp/gk 2>/dev/null
(cd /srv/repo && apt-ftparchive release . > Release && gpg --batch --yes --clearsign -o InRelease Release && gpg --batch --yes -abs -o Release.gpg Release)
gpg --armor --export repo@lab.example > /srv/repo/key.asc
rm -rf "$GNUPGHOME" /tmp/gk
chmod -R a+rX /srv/repo
""",
    validate=r"""
chk installed 'dpkg -s labtool 2>/dev/null | grep -q "^Status: install ok installed"'
chk signed_source 'f=$(grep -l "/srv/repo" /etc/apt/sources.list.d/* 2>/dev/null | head -n 1); [ -n "$f" ] && grep -q "signed-by=" $f && ! grep -Eqi "trusted=yes|allow-insecure" $f && kr=$(grep -o "signed-by=[^] ]*" $f | head -n 1 | cut -d= -f2) && [ -s "$kr" ]'
chk from_repo 'apt-cache policy labtool | grep -q "file:/srv/repo"'
""",
    solution=r"""
sudo mkdir -p /etc/apt/keyrings
sudo gpg --dearmor -o /etc/apt/keyrings/labrepo.gpg /srv/repo/key.asc
echo 'deb [signed-by=/etc/apt/keyrings/labrepo.gpg] file:/srv/repo ./' | sudo tee /etc/apt/sources.list.d/labrepo.list > /dev/null
sudo apt-get update -qq
sudo apt-get install -y labtool
""",
    wrong="echo 'deb [trusted=yes] file:/srv/repo ./' | sudo tee /etc/apt/sources.list.d/labrepo.list > /dev/null\nsudo apt-get update -qq\nsudo apt-get install -y labtool\n",
)

lab(
    id="ld-123", title="Инцидент: обновление библиотеки сломало приложение",
    description="После обновления пакета приложение падает. Верните рабочую версию и закрепите её, чтобы обновление не повторилось.",
    skills=["apt-get install pkg=ver", "apt-mark hold", "dpkg -l", "journalctl -u"],
    objectives=["Связать сбой с обновлением", "Откатить версию", "Закрепить версию (hold)"],
    minutes=25,
    task="""\
**Инцидент.** Служба `labapp.service` перестала работать после обновления библиотеки `labfmt` до версии 2.0 (в ней убрана функция `render`).

1. Найдите причину в журнале (`journalctl -u labapp`).
2. Откатите `labfmt` до версии **1.0** из локального репозитория (`/srv/repo`, он уже подключён).
3. **Закрепите** версию (`apt-mark hold`), чтобы следующее обновление её не тронуло, и убедитесь, что служба снова работает.
""",
    hints=["`apt-cache policy labfmt` покажет доступные версии.", "`sudo apt-get install -y --allow-downgrades labfmt=1.0`, затем `sudo apt-mark hold labfmt` и `sudo systemctl restart labapp`."],
    exercise_timeout=15,
    checks=[
        ("version_rolled_back", "labfmt версии 1.0", "Версия откачена", "Установлена не версия 1.0 пакета labfmt"),
        ("held", "Версия закреплена", "Версия закреплена", "Пакет labfmt не закреплён (apt-mark hold)"),
        ("service_ok", "labapp работает", "Служба работает", "labapp не работает"),
    ],
    setup=REPO + r"""
mkdeb labfmt 1.0 'def render(x):
    return "[" + str(x) + "]"'
mkdeb labfmt 2.0 'def format_value(x):
    return "<" + str(x) + ">"'
reindex
echo 'deb [trusted=yes] file:/srv/repo ./' > /etc/apt/sources.list.d/labrepo.list
apt-get update -qq 2>/dev/null
apt-get install -y -qq labfmt=1.0 >/dev/null
install -d /opt/lab
cat > /opt/lab/fmtapp.py <<'EOT'
import time
import labfmt
while True:
    labfmt.render("ok")
    time.sleep(1)
EOT
cat > /etc/systemd/system/labapp.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/fmtapp.py
Restart=on-failure
RestartSec=1
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable labapp >/dev/null 2>&1
apt-get install -y -qq labfmt=2.0 >/dev/null
systemctl restart labapp
sleep 2
""",
    exercise="sudo systemctl restart labapp\nsleep 3\ntrue\n",
    validate=r"""
chk version_rolled_back '[ "$(dpkg-query -W -f="\${Version}" labfmt)" = 1.0 ]'
chk held 'apt-mark showhold | grep -qx labfmt'
chk service_ok 'sleep 2; systemctl is-active --quiet labapp'
""",
    solution="sudo apt-get install -y --allow-downgrades labfmt=1.0\nsudo apt-mark hold labfmt\nsudo systemctl restart labapp\nsleep 3\n",
    wrong="sudo systemctl restart labapp\n",
)

lab(
    id="ld-124", title="Закрепление версий зависимостей и воспроизводимая установка",
    description="Закрепите версии пакетов через APT pinning, чтобы установка давала одинаковый результат.",
    skills=["apt preferences", "Pin-Priority", "apt-cache policy", "воспроизводимость"],
    objectives=["Описать pin в /etc/apt/preferences.d", "Убедиться, что кандидат — нужная версия", "Установить зависимость закреплённой версии"],
    minutes=20,
    task="""\
В локальном репозитории два релиза библиотеки `labcore`: 1.0 и 2.0. Приложению подходит **только 1.0**, но по умолчанию APT выберет 2.0.

1. Создайте `/etc/apt/preferences.d/labcore` с pin на версию `1.0` (приоритет не ниже 1001).
2. Убедитесь, что `apt-cache policy labcore` показывает кандидатом 1.0, и установите пакет `labcore`.
3. После установки `apt-get upgrade -s` не должен предлагать обновление `labcore`.
""",
    hints=["Файл pin: `Package: labcore`, `Pin: version 1.0`, `Pin-Priority: 1001`.", "Проверка: `apt-cache policy labcore` и `apt-get upgrade -s | grep labcore`."],
    checks=[
        ("pin_defined", "Pin на 1.0 с приоритетом ≥ 1001", "Pin задан", "Нужен pin Package: labcore, Pin: version 1.0, Pin-Priority ≥ 1001"),
        ("installed_v1", "Установлена labcore 1.0", "Установлена нужная версия", "Должна быть установлена версия labcore 1.0"),
        ("no_upgrade", "upgrade не предлагает labcore", "Обновления нет", "apt-get upgrade -s предлагает обновить labcore"),
    ],
    setup=REPO + r"""
mkdeb labcore 1.0 'VERSION = "1.0"'
mkdeb labcore 2.0 'VERSION = "2.0"'
reindex
echo 'deb [trusted=yes] file:/srv/repo ./' > /etc/apt/sources.list.d/labrepo.list
apt-get update -qq 2>/dev/null
""",
    validate=r"""
chk pin_defined 'f=/etc/apt/preferences.d/labcore; [ -f $f ] && grep -q "^Package: labcore" $f && grep -Eq "^Pin: version 1\.0" $f && p=$(grep -i "^Pin-Priority" $f | grep -o "[0-9]*") && [ "$p" -ge 1001 ]'
chk installed_v1 '[ "$(dpkg-query -W -f="\${Version}" labcore 2>/dev/null)" = 1.0 ]'
chk no_upgrade '! apt-get upgrade -s 2>/dev/null | grep -q "labcore"'
""",
    solution=r"""
printf 'Package: labcore\nPin: version 1.0\nPin-Priority: 1001\n' | sudo tee /etc/apt/preferences.d/labcore > /dev/null
sudo apt-get install -y labcore
""",
    wrong="sudo apt-get install -y labcore\n",
)

lab(
    id="ld-125", title="Сборка из исходников в отдельный prefix",
    description="Соберите программу из исходников и установите её в собственный prefix, не затрагивая файлы пакетного менеджера.",
    skills=["make", "PREFIX", "PATH", "dpkg -S"],
    objectives=["Собрать из исходников", "Установить в /opt/labtool", "Не касаться /usr"],
    minutes=20,
    task="""\
Исходники утилиты лежат в `/usr/local/src/hello-lab` (Makefile поддерживает `PREFIX`). Соберите и установите её в **`/opt/hello-lab`** (бинарник `/opt/hello-lab/bin/hello-lab`).

Требования: не копировать файлы в `/usr` и `/usr/local`; добавьте `/opt/hello-lab/bin` в `PATH` для всех пользователей через `/etc/profile.d/hello-lab.sh`, чтобы команда `hello-lab` запускалась в новой login-оболочке.
""",
    hints=["`cd /usr/local/src/hello-lab && make && sudo make install PREFIX=/opt/hello-lab`.", "`/etc/profile.d/hello-lab.sh`: `export PATH=$PATH:/opt/hello-lab/bin`."],
    checks=[
        ("installed_prefix", "Бинарник в /opt/hello-lab/bin", "Установлено в свой prefix", "Нет исполняемого /opt/hello-lab/bin/hello-lab, который печатает приветствие"),
        ("usr_clean", "В /usr нет hello-lab", "Системные каталоги не тронуты", "hello-lab найден в /usr или /usr/local"),
        ("on_path", "hello-lab в PATH login-оболочки", "PATH настроен", "В новой login-оболочке команда hello-lab не находится"),
    ],
    setup=r"""
mkdir -p /usr/local/src/hello-lab
cat > /usr/local/src/hello-lab/hello.c <<'EOT'
#include <stdio.h>
int main(void) { puts("hello from lab"); return 0; }
EOT
printf 'PREFIX ?= /usr/local\nall: hello-lab\nhello-lab: hello.c\n\tgcc -o hello-lab hello.c\ninstall: hello-lab\n\tinstall -d $(PREFIX)/bin\n\tinstall -m 755 hello-lab $(PREFIX)/bin/hello-lab\n' > /usr/local/src/hello-lab/Makefile
chmod -R a+rX /usr/local/src/hello-lab
chmod a+w /usr/local/src/hello-lab
""",
    validate=r"""
chk installed_prefix '[ "$(/opt/hello-lab/bin/hello-lab)" = "hello from lab" ]'
chk usr_clean '! find /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin /bin /sbin -name hello-lab -type f 2>/dev/null | grep -q .'
chk on_path '[ "$(runuser -l student -c "hello-lab")" = "hello from lab" ]'
""",
    solution=r"""
cd /usr/local/src/hello-lab && make && sudo make install PREFIX=/opt/hello-lab
echo 'export PATH=$PATH:/opt/hello-lab/bin' | sudo tee /etc/profile.d/hello-lab.sh > /dev/null
""",
    wrong="cd /usr/local/src/hello-lab && make && sudo make install\n",
)

lab(
    id="ld-046", validate_timeout=60, title="Скорость загрузки: найти и устранить задержку через systemd-analyze",
    description="Сравните время загрузки до и после правки: найдите службу, которая тормозит старт, и уберите блокировку.",
    skills=["systemd-analyze", "blame", "critical-chain", "Type=oneshot"],
    objectives=["Найти виновника по blame/critical-chain", "Не блокировать загрузку", "Подтвердить результат после reboot"],
    reboot=True, minutes=25,
    task="""\
Загрузка машины стала медленной. Найдите по `systemd-analyze blame` / `critical-chain` службу, которая замедляет старт, и устраните задержку **без потери функции**: служба `labslow.service` должна по-прежнему выполнять свою задачу (создать `/run/labslow.done`), но **не блокировать** завершение загрузки.

Проверка перезагрузит машину и измерит время запуска пользовательского пространства.
""",
    hints=["`systemd-analyze blame | head` и `systemd-analyze critical-chain`.", "Служба `Type=oneshot` с `sleep 15` блокирует `multi-user.target`. Отвяжите: запуск в фоне (`Type=simple`/`exec`) или `Before=` убрать — главное, чтобы цель не ждала завершения."],
    exercise_timeout=15,
    checks=[
        ("boot_fast", "Загрузка не ждёт labslow", "Загрузка ускорена", "Время userspace-загрузки всё ещё превышает 14 секунд"),
        ("function_kept", "labslow выполняет задачу", "Функция сохранена", "labslow не создал /run/labslow.done (задача потеряна)"),
    ],
    setup=r"""
cat > /etc/systemd/system/labslow.service <<'EOT'
[Unit]
Description=Slow lab initialisation
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'sleep 15; touch /run/labslow.done'
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable labslow >/dev/null 2>&1
""",
    exercise="sleep 1\ntrue\n",
    validate=r"""
for i in $(seq 1 14); do [ -e /run/labslow.done ] && break; sleep 1; done
u=$(systemctl show -p UserspaceTimestampMonotonic --value); f=$(systemctl show -p FinishTimestampMonotonic --value)
t=$(( (f - u) / 1000000 ))
chk boot_fast '[ "$t" -lt 14 ]'
chk function_kept '[ -e /run/labslow.done ]'
""",
    solution=r"""
sudo tee /etc/systemd/system/labslow.service > /dev/null <<'EOT'
[Unit]
Description=Slow lab initialisation
[Service]
Type=exec
ExecStart=/bin/sh -c 'sleep 15; touch /run/labslow.done'
[Install]
WantedBy=multi-user.target
EOT
sudo systemctl daemon-reload
""",
    wrong="sudo systemctl disable labslow\n",
)

lab(
    id="ld-145", title="Namespaces: сравнить PID, mount, network и user namespace",
    description="Сравните идентификаторы namespace процесса в изоляции и в основной системе.",
    skills=["/proc/PID/ns", "unshare", "readlink", "inode namespace"],
    objectives=["Читать inode namespace", "Создать изолированные namespace", "Сопоставить различия"],
    minutes=15,
    task="""\
Запишите в `~/ns.txt` четыре строки в формате `<тип>=<одинаковы|различаются>`: сравнение namespace обычной оболочки и процесса, запущенного через `unshare` (**с** новыми pid, mount, net и user namespace: `unshare --fork --pid --mount-proc --mount --net --user --map-root-user`).

```
pid=...
mnt=...
net=...
user=...
```

Идентификаторы читаются из `/proc/<PID>/ns/*` (`readlink`).
""",
    hints=["`readlink /proc/self/ns/pid` — `pid:[inode]`; сравните inode.", "`unshare --fork --pid --mount-proc --mount --net --user --map-root-user readlink /proc/self/ns/net`."],
    checks=[
        ("all_four", "Четыре строки с допустимыми значениями", "Формат верный", "Нужны строки pid=, mnt=, net=, user= со значениями одинаковы|различаются"),
        ("values_right", "Значения соответствуют реальности", "Значения верны", "Значения не совпадают с реальным сравнением (в изоляции все четыре должны различаться)"),
    ],
    setup="true\n",
    validate=r"""
F=/home/student/ns.txt
v() { grep "^$1=" $F | cut -d= -f2- | tr -d ' '; }
chk all_four '( for k in pid mnt net user; do case "$(v $k)" in одинаковы|различаются) ;; *) exit 1;; esac; done )'
real=$(runuser -u student -- unshare --fork --pid --mount-proc --mount --net --user --map-root-user sh -c 'for n in pid mnt net user; do readlink /proc/self/ns/$n; done' | tr "\n" " ")
mine=$(for n in pid mnt net user; do readlink /proc/$$/ns/$n; done | tr "\n" " ")
chk values_right '[ "$real" != "$mine" ] && [ "$(for i in 1 2 3 4; do a=$(echo $real | cut -d" " -f$i); b=$(echo $mine | cut -d" " -f$i); [ "$a" = "$b" ] && echo одинаковы || echo различаются; done | sort -u)" = "различаются" ] && [ "$(v pid)$(v mnt)$(v net)$(v user)" = "различаютсяразличаютсяразличаютсяразличаются" ]'
""",
    solution=r"""
for n in pid mnt net user; do
  a=$(readlink /proc/self/ns/$n)
  b=$(unshare --fork --pid --mount-proc --mount --net --user --map-root-user readlink /proc/self/ns/$n)
  [ "$a" = "$b" ] && r=одинаковы || r=различаются
  echo "$n=$r"
done > ~/ns.txt
""",
    wrong="printf 'pid=одинаковы\\nmnt=одинаковы\\nnet=одинаковы\\nuser=одинаковы\\n' > ~/ns.txt\n",
)

lab(
    id="ld-146", title="Изолированный network namespace: нет маршрутов, затем связь через veth",
    description="Создайте network namespace, покажите отсутствие маршрутов, затем соедините его с хостом парой veth.",
    skills=["ip netns", "nsenter", "veth", "ip route"],
    objectives=["Создать namespace", "Увидеть пустую таблицу маршрутов", "Настроить veth и проверить связь"],
    minutes=20,
    task="""\
> В учебной машине `ip netns exec` и `ip -n` недоступны (в контейнере нельзя смонтировать `/sys`). Команды внутри namespace выполняйте через `nsenter --net=/run/netns/labns <команда>`.

1. Создайте network namespace `labns` (`ip netns add`). В нём без настройки не должно быть маршрутов и связи наружу (проверьте `nsenter --net=/run/netns/labns ip route`).
2. Соедините его с основной системой парой veth: `vlab0` (основная система, `10.77.0.1/24`) ↔ `vlab1` (в `labns`, `10.77.0.2/24`), поднимите интерфейсы (включая `lo` в namespace).
3. Проверьте, что `ping 10.77.0.2` из основной системы и `ping 10.77.0.1` из `labns` работают.

Интерфейсы и namespace должны остаться настроенными.
""",
    hints=["`sudo ip netns add labns`; `sudo ip link add vlab0 type veth peer name vlab1`; `sudo ip link set vlab1 netns labns`.", "Внутри namespace: `sudo nsenter --net=/run/netns/labns ip addr add 10.77.0.2/24 dev vlab1` и `... ip link set vlab1 up`."],
    checks=[
        ("ns_exists", "Namespace labns существует", "Namespace создан", "Нет network namespace labns"),
        ("veth_pair", "veth vlab0 ↔ vlab1 с нужными адресами", "veth настроен", "Нужны vlab0 (10.77.0.1/24) в основной системе и vlab1 (10.77.0.2/24) в labns, оба UP"),
        ("ping_both", "Ping в обе стороны", "Связь работает", "Ping между основной системой и labns не проходит"),
    ],
    setup="true\n",
    validate=r"""
NS="nsenter --net=/run/netns/labns"
chk ns_exists 'ip netns list | grep -qw labns'
chk veth_pair 'ip -br addr show vlab0 | grep -q "10.77.0.1/24" && $NS ip -br addr show vlab1 | grep -q "10.77.0.2/24" && ip -br link show vlab0 | grep -q UP && $NS ip -br link show vlab1 | grep -q UP'
chk ping_both 'ping -c1 -W2 10.77.0.2 && $NS ping -c1 -W2 10.77.0.1'
""",
    solution=r"""
sudo ip netns add labns
sudo ip link add vlab0 type veth peer name vlab1
sudo ip link set vlab1 netns labns
sudo ip addr add 10.77.0.1/24 dev vlab0
sudo ip link set vlab0 up
sudo nsenter --net=/run/netns/labns ip addr add 10.77.0.2/24 dev vlab1
sudo nsenter --net=/run/netns/labns ip link set vlab1 up
sudo nsenter --net=/run/netns/labns ip link set lo up
""",
    wrong="sudo ip netns add labns\n",
)

lab(
    id="ld-147", title="cgroup v2 вручную: лимит памяти и CPU, события и throttling",
    description="Создайте cgroup вручную, ограничьте процесс по памяти и CPU и прочитайте события.",
    skills=["cgroup v2", "memory.max", "cpu.max", "memory.events"],
    objectives=["Создать группу и записать лимиты", "Поместить процесс в группу", "Прочитать события"],
    minutes=25,
    task="""\
Создайте cgroup `/sys/fs/cgroup/labgrp`, задайте `memory.max` = 50 МБ и `cpu.max` = `20000 100000` (20 % ядра), запустите в ней скрипт `/opt/lab/hog.py` (он выделяет память и крутит CPU) и убедитесь по `memory.events` / `cpu.stat`, что лимиты действуют.

Скрипт запущен как `nohup python3 /opt/lab/hog.py` (PID запишите в `cgroup.procs`). После проверки процесс должен остаться в группе. В `~/cg.txt` запишите: `oom=<число oom/oom_kill из memory.events>` и `throttled=<nr_throttled из cpu.stat>`.
""",
    hints=["`sudo mkdir /sys/fs/cgroup/labgrp`; в `cgroup.subtree_control` родителя нужны cpu и memory; `echo 52428800 | sudo tee .../memory.max`.", "PID добавьте командой `echo PID | sudo tee /sys/fs/cgroup/labgrp/cgroup.procs`."],
    exercise_timeout=15,
    checks=[
        ("limits_ok", "memory.max=50M, cpu.max=20%", "Лимиты заданы", "В labgrp нужны memory.max=52428800 и cpu.max=20000 100000"),
        ("proc_in_group", "hog.py внутри labgrp", "Процесс в группе", "Процесс /opt/lab/hog.py не находится в cgroup labgrp"),
        ("throttle_effect", "nr_throttled > 0", "Throttling виден", "cpu.stat группы не показывает throttling"),
        ("report_ok", "cg.txt: throttled > 0", "Измерения записаны", "В cg.txt должны быть oom=<число> и throttled=<число > 0>"),
    ],
    setup=r"""
install -d /opt/lab
cat > /opt/lab/hog.py <<'EOT'
import time
chunks = []
while True:
    if len(chunks) < 30:
        chunks.append(bytearray(1024 * 1024))   # до 30 МБ малыми порциями (лимит группы 50 МБ)
    x = 0
    for i in range(200000):
        x += i
    time.sleep(0.01)
EOT
""",
    exercise="true\n",
    validate=r"""
g=/sys/fs/cgroup/labgrp
sleep 2
rep() { grep "^$1=" /home/student/cg.txt | cut -d= -f2 | tr -d ' '; }
chk limits_ok '[ "$(cat $g/memory.max)" = 52428800 ] && [ "$(cat $g/cpu.max)" = "20000 100000" ]'
chk proc_in_group 'for p in $(cat $g/cgroup.procs); do tr "\0" " " < /proc/$p/cmdline; echo; done | grep -q hog.py'
chk throttle_effect '[ "$(awk "/^nr_throttled/{print \$2}" $g/cpu.stat)" -gt 0 ]'
chk report_ok '[ -n "$(rep oom)" ] && [ "$(rep throttled)" -gt 0 ]'
""",
    solution=r"""
echo "+cpu +memory" | sudo tee /sys/fs/cgroup/cgroup.subtree_control > /dev/null 2>&1 || true
sudo mkdir -p /sys/fs/cgroup/labgrp
echo 52428800 | sudo tee /sys/fs/cgroup/labgrp/memory.max > /dev/null
echo "20000 100000" | sudo tee /sys/fs/cgroup/labgrp/cpu.max > /dev/null
sudo sh -c 'nohup python3 /opt/lab/hog.py >/dev/null 2>&1 & echo $! > /sys/fs/cgroup/labgrp/cgroup.procs'
sleep 6
o=$(awk '/^oom_kill/{print $2}' /sys/fs/cgroup/labgrp/memory.events)
t=$(awk '/^nr_throttled/{print $2}' /sys/fs/cgroup/labgrp/cpu.stat)
printf 'oom=%s\nthrottled=%s\n' "$o" "$t" > ~/cg.txt
""",
    wrong="sudo mkdir -p /sys/fs/cgroup/labgrp\n",
)

lab(
    id="ld-150", title="Лишняя capability у службы: убрать и доказать по CapEff",
    description="Уберите у службы ненужную Linux capability и подтвердите результат по маске CapEff процесса.",
    skills=["CapabilityBoundingSet", "/proc/PID/status CapEff", "capsh --decode", "наименьшие привилегии"],
    objectives=["Прочитать маску capability процесса", "Сузить набор в unit", "Сохранить работоспособность"],
    minutes=20,
    task="""\
Служба `labcap.service` работает от root с полным набором capability, хотя ей нужна только `CAP_NET_BIND_SERVICE` (она слушает порт 81 и пишет heartbeat).

Сузьте набор до **одной** capability `CAP_NET_BIND_SERVICE` (`CapabilityBoundingSet=` и `AmbientCapabilities=`), так, чтобы:

- в `/proc/PID/status` у основного процесса `CapEff` соответствовал только `cap_net_bind_service`;
- служба продолжала слушать порт 81.
""",
    hints=["`grep Cap /proc/$(systemctl show -p MainPID --value labcap)/status` и `capsh --decode=МАСКА`.", "`CapabilityBoundingSet=CAP_NET_BIND_SERVICE` + `AmbientCapabilities=CAP_NET_BIND_SERVICE` в drop-in."],
    exercise_timeout=15,
    checks=[
        ("capeff_minimal", "CapEff = только net_bind_service", "Набор capability минимален", "CapEff процесса должен содержать только cap_net_bind_service"),
        ("still_listening", "Порт 81 слушается", "Служба работает", "Служба не слушает порт 81"),
    ],
    setup=r"""
install -d /opt/lab
cat > /opt/lab/cap.py <<'EOT'
import socket, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 81))
s.listen(5)
while True:
    time.sleep(60)
EOT
cat > /etc/systemd/system/labcap.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/cap.py
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labcap >/dev/null 2>&1
sleep 1
""",
    exercise="sudo systemctl daemon-reload\nsudo systemctl restart labcap\nsleep 2\ntrue\n",
    validate=r"""
pid=$(systemctl show -p MainPID --value labcap)
eff=$(awk '/^CapEff/{print $2}' /proc/$pid/status)
chk capeff_minimal '[ "$(capsh --decode=$eff | sed "s/^0x[0-9a-f]*=//")" = cap_net_bind_service ]'
chk still_listening 'ss -ltn | grep -q "127.0.0.1:81 "'
""",
    solution=r"""
sudo mkdir -p /etc/systemd/system/labcap.service.d
printf '[Service]\nCapabilityBoundingSet=CAP_NET_BIND_SERVICE\nAmbientCapabilities=CAP_NET_BIND_SERVICE\n' | sudo tee /etc/systemd/system/labcap.service.d/caps.conf > /dev/null
""",
    wrong="sudo mkdir -p /etc/systemd/system/labcap.service.d\nprintf '[Service]\\nCapabilityBoundingSet=~CAP_SYS_ADMIN\\n' | sudo tee /etc/systemd/system/labcap.service.d/caps.conf > /dev/null\n",
)

lab(
    id="ld-151", title="Фильтр системных вызовов (seccomp) для службы",
    description="Ограничьте службу фильтром системных вызовов и докажите, что запрещённый вызов блокируется, а работа продолжается.",
    skills=["SystemCallFilter", "seccomp", "@system-service", "EPERM"],
    objectives=["Задать SystemCallFilter", "Запретить опасную группу вызовов", "Подтвердить блокировку"],
    minutes=20,
    task="""\
Служба `labseccomp.service` каждую секунду пытается выполнить вызов `mount` (запрещённый операции) и записывает в `/var/lib/labapp/seccomp.txt` результат: `mount=allowed|blocked`. Ещё она пишет heartbeat.

Задайте `SystemCallFilter=` так, чтобы использовалась разрешённая группа `@system-service` и **вызов mount был заблокирован** (`SystemCallErrorNumber=EPERM`), при этом служба продолжала работать. Проверьте `seccomp.txt`.
""",
    hints=["Drop-in: `SystemCallFilter=@system-service` и `SystemCallErrorNumber=EPERM`; mount в `@system-service` не входит (он в `@mount`).", "После изменений: `sudo systemctl daemon-reload && sudo systemctl restart labseccomp`."],
    exercise_timeout=15,
    checks=[
        ("filter_set", "SystemCallFilter задан", "Фильтр настроен", "Нужен SystemCallFilter (с @system-service) и SystemCallErrorNumber=EPERM"),
        ("mount_blocked", "mount заблокирован", "Запрещённый вызов блокируется", "seccomp.txt не показывает mount=blocked"),
        ("alive", "Служба работает", "Служба жива", "Служба не пишет heartbeat"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/labapp
cat > /opt/lab/sc.py <<'EOT'
import ctypes, os, time
libc = ctypes.CDLL(None, use_errno=True)
while True:
    r = libc.mount(b"none", b"/mnt", b"tmpfs", 0, None)
    err = ctypes.get_errno()
    if r == 0:
        libc.umount(b"/mnt")
    with open("/var/lib/labapp/seccomp.txt", "w") as f:
        f.write("mount=%s\n" % ("blocked" if (r != 0 and err == 1) else "allowed"))
    with open("/var/lib/labapp/heartbeat2", "w") as f:
        f.write(str(time.time()))
    time.sleep(1)
EOT
cat > /etc/systemd/system/labseccomp.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/sc.py
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labseccomp >/dev/null 2>&1
sleep 2
""",
    exercise="sudo systemctl daemon-reload\nsudo systemctl restart labseccomp\nsleep 3\ntrue\n",
    validate=r"""
chk filter_set 'systemctl show -p SystemCallFilter --value labseccomp | grep -q . && case "$(systemctl show -p SystemCallErrorNumber --value labseccomp)" in EPERM|1) true;; *) false;; esac'
chk mount_blocked 'grep -qx "mount=blocked" /var/lib/labapp/seccomp.txt'
chk alive 'systemctl is-active --quiet labseccomp && [ $(( $(date +%s) - $(cut -d. -f1 /var/lib/labapp/heartbeat2) )) -le 5 ]'
""",
    solution=r"""
sudo mkdir -p /etc/systemd/system/labseccomp.service.d
printf '[Service]\nSystemCallFilter=@system-service\nSystemCallErrorNumber=EPERM\n' | sudo tee /etc/systemd/system/labseccomp.service.d/seccomp.conf > /dev/null
""",
    wrong="sudo mkdir -p /etc/systemd/system/labseccomp.service.d\nprintf '[Service]\\nNoNewPrivileges=yes\\n' | sudo tee /etc/systemd/system/labseccomp.service.d/x.conf > /dev/null\n",
)

lab(
    id="ld-156", title="strace: на каком системном вызове завис процесс",
    description="Диагностируйте зависший процесс по strace и устраните причину.",
    skills=["strace -p", "strace -f", "FIFO", "ожидание ввода-вывода"],
    objectives=["Подключиться к процессу", "Увидеть системный вызов, на котором он ждёт", "Устранить причину"],
    minutes=20,
    task="""\
Служба `labhang.service` «жива», но ничего не делает. Подключитесь к её процессу (`sudo strace -p PID`), найдите системный вызов, на котором она ждёт, и **устраните причину** (не убивая процесс: он должен продолжить работу и записать `/var/lib/labapp/hang-done`).

В `~/syscall.txt` запишите одну строку — имя системного вызова, на котором ждёт процесс (например, `read` или `connect`).
""",
    hints=["`sudo strace -p $(systemctl show -p MainPID --value labhang)` — смотрите, на каком вызове процесс остановился и какой путь/fd использует.", "Если читается FIFO, ему нужен записывающий конец: `echo go > /run/lab/jobs.fifo`."],
    exercise_timeout=15,
    checks=[
        ("syscall_named", "Системный вызов указан верно", "Системный вызов определён", "В syscall.txt нужно имя вызова, на котором ждёт процесс (openat или read для FIFO)"),
        ("unblocked", "Процесс продолжил работу", "Причина устранена", "Файл hang-done не создан: процесс всё ещё ждёт"),
        ("same_process", "Процесс не перезапускали", "Процесс не перезапускали", "Процесс был перезапущен вместо диагностики"),
    ],
    setup=r"""
install -d /opt/lab /run/lab /var/lib/labapp
mkfifo /run/lab/jobs.fifo
chmod 666 /run/lab/jobs.fifo
cat > /opt/lab/hang.py <<'EOT'
with open("/run/lab/jobs.fifo") as f:   # блокируется до появления записывающей стороны
    data = f.read()
open("/var/lib/labapp/hang-done", "w").write("done\n")
import time
while True:
    time.sleep(60)
EOT
cat > /etc/systemd/system/labhang.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/hang.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labhang >/dev/null 2>&1
sleep 1
systemctl show -p MainPID --value labhang > /var/lib/lab-hang-pid
""",
    exercise="true\n",
    validate=r"""
sleep 1
chk syscall_named 'grep -Eqx "(openat|open|read)" <(tr -d " \r" < /home/student/syscall.txt)'
chk unblocked '[ -e /var/lib/labapp/hang-done ]'
chk same_process '[ "$(systemctl show -p MainPID --value labhang)" = "$(cat /var/lib/lab-hang-pid)" ]'
""",
    solution=r"""
timeout 3 sudo strace -p $(systemctl show -p MainPID --value labhang) -o /tmp/st.out || true
cat /tmp/st.out | head -3
echo openat > ~/syscall.txt
echo go > /run/lab/jobs.fifo
sleep 1
""",
    wrong="sudo systemctl restart labhang\necho read > ~/syscall.txt\n",
)

lab(
    id="ld-162", title="SSH baseline: ключи, минимальный доступ, журналирование",
    description="Приведите конфигурацию sshd к безопасной базовой линии и проверьте её через sshd -T.",
    skills=["sshd_config.d", "sshd -T", "PasswordAuthentication", "AllowUsers", "LogLevel"],
    objectives=["Отключить пароли и вход root", "Ограничить пользователей", "Включить журналирование"],
    minutes=20,
    task="""\
Настройте безопасный базовый уровень `sshd` (лучше drop-in в `/etc/ssh/sshd_config.d/`):

- `PasswordAuthentication no`, `PermitRootLogin no`, `PubkeyAuthentication yes`;
- `AllowUsers student`;
- `MaxAuthTries` не более 3, `LogLevel VERBOSE`, `X11Forwarding no`;
- конфигурация должна проходить `sshd -t`.

Эффективные значения проверяются командой `sshd -T`.
""",
    hints=["Файл `/etc/ssh/sshd_config.d/10-baseline.conf` (учтите: ранние файлы в sshd_config.d имеют приоритет над поздними).", "Проверка: `sudo sshd -t && sudo sshd -T | grep -Ei 'passwordauth|permitroot|allowusers|maxauth|loglevel|x11'`."],
    checks=[
        ("auth_hardened", "Пароли и root отключены, ключи включены", "Аутентификация ужесточена", "Нужны passwordauthentication no, permitrootlogin no, pubkeyauthentication yes"),
        ("access_limited", "AllowUsers student, MaxAuthTries ≤ 3", "Доступ ограничен", "Нужны allowusers student и maxauthtries ≤ 3"),
        ("logging", "LogLevel VERBOSE, X11 выключен", "Журналирование настроено", "Нужны loglevel VERBOSE и x11forwarding no"),
        ("syntax_ok", "sshd -t проходит", "Конфигурация валидна", "sshd -t сообщает об ошибке"),
    ],
    setup=r"""
mkdir -p /run/sshd
printf 'PasswordAuthentication yes\nPermitRootLogin yes\nMaxAuthTries 10\nX11Forwarding yes\n' > /etc/ssh/sshd_config.d/00-legacy.conf
""",
    validate=r"""
T=$(sshd -T 2>/dev/null)
chk auth_hardened 'echo "$T" | grep -qx "passwordauthentication no" && echo "$T" | grep -qx "permitrootlogin no" && echo "$T" | grep -qx "pubkeyauthentication yes"'
chk access_limited 'echo "$T" | grep -qx "allowusers student" && [ "$(echo "$T" | awk "/^maxauthtries/{print \$2}")" -le 3 ]'
chk logging 'echo "$T" | grep -qx "loglevel VERBOSE" && echo "$T" | grep -qx "x11forwarding no"'
chk syntax_ok 'sshd -t'
""",
    solution=r"""
sudo rm -f /etc/ssh/sshd_config.d/00-legacy.conf
sudo tee /etc/ssh/sshd_config.d/10-baseline.conf > /dev/null <<'EOT'
PasswordAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
AllowUsers student
MaxAuthTries 3
LogLevel VERBOSE
X11Forwarding no
EOT
""",
    wrong="sudo tee /etc/ssh/sshd_config.d/10-baseline.conf > /dev/null <<'EOT'\nPasswordAuthentication no\nPermitRootLogin no\nEOT\n",
)

lab(
    id="ld-164", title="Контроль целостности: обнаружить несанкционированное изменение",
    description="Снимите эталонные контрольные суммы критичных конфигов и обнаружьте изменение с помощью проверки.",
    skills=["sha256sum", "sha256sum -c", "baseline", "обнаружение изменений"],
    objectives=["Создать эталон", "Выявить изменённый файл", "Восстановить и зафиксировать"],
    minutes=20,
    task="""\
Критичные файлы: `/etc/lab/app.conf`, `/etc/lab/db.conf`, `/etc/lab/acl.conf`. Эталон контрольных сумм хранится в `/var/lib/lab/baseline.sha256` (формат `sha256sum`).

1. Проверкой эталона (`sha256sum -c`) найдите файл, который был изменён без разрешения.
2. Запишите его путь в `~/tampered.txt`.
3. Восстановите файл из резервной копии `/var/backups/lab/` (копия эталонная) и убедитесь, что проверка проходит целиком.
""",
    hints=["`sudo sha256sum -c /var/lib/lab/baseline.sha256 2>&1 | grep -v OK`.", "Восстановление: `sudo cp /var/backups/lab/<файл> /etc/lab/` и повторная проверка."],
    checks=[
        ("found_file", "Изменённый файл назван верно", "Файл найден", "В tampered.txt должен быть путь изменённого файла (только он)"),
        ("restored", "Файл восстановлен, baseline проходит", "Целостность восстановлена", "sha256sum -c baseline всё ещё сообщает о расхождениях"),
        ("baseline_untouched", "Эталон не изменён", "Эталон не подменён", "Эталонный файл baseline.sha256 был изменён"),
    ],
    setup=r"""
install -d /etc/lab /var/lib/lab /var/backups/lab
printf 'port=8080\n' > /etc/lab/app.conf; printf 'host=db1\n' > /etc/lab/db.conf; printf 'allow=10.0.0.0/24\n' > /etc/lab/acl.conf
cp /etc/lab/*.conf /var/backups/lab/
sha256sum /etc/lab/app.conf /etc/lab/db.conf /etc/lab/acl.conf > /var/lib/lab/baseline.sha256
sha256sum /var/lib/lab/baseline.sha256 > /root/.baseline.ref
printf 'allow=0.0.0.0/0\n' > /etc/lab/acl.conf
""",
    validate=r"""
chk found_file '[ "$(tr -d " \r" < /home/student/tampered.txt)" = /etc/lab/acl.conf ]'
chk restored 'sha256sum -c /var/lib/lab/baseline.sha256 >/dev/null 2>&1'
chk baseline_untouched 'sha256sum -c /root/.baseline.ref >/dev/null 2>&1'
""",
    solution=r"""
bad=$(sudo sha256sum -c /var/lib/lab/baseline.sha256 2>/dev/null | grep -v ': OK' | cut -d: -f1)
echo "$bad" > ~/tampered.txt
sudo cp /var/backups/lab/$(basename "$bad") "$bad"
""",
    wrong="sudo sh -c 'sha256sum /etc/lab/*.conf > /var/lib/lab/baseline.sha256'\necho /etc/lab/acl.conf > ~/tampered.txt\n",
)
