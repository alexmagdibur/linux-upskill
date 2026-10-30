"""Данные лабораторий Module B — Administration (linux-009 … linux-015)."""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append(kw)


lab(
    id="linux-009", module="administration", mode="learn", difficulty="beginner", minutes=10, xp=50,
    title="Права доступа chmod",
    description="Научитесь читать и менять права доступа к файлам: символьная и числовая запись, chmod.",
    skills=["chmod", "ls -l", "rwx", "восьмеричные права"],
    objectives=["Сделать скрипт исполняемым", "Ограничить доступ к секретному файлу", "Настроить права каталога"],
    task="""\
В каталоге `~/perm` лежат файлы с неудачными правами (посмотрите `ls -l ~/perm`).

1. `script.sh` — сделайте исполняемым для владельца; запись для группы и остальных не нужна.
2. `secret.txt` — доступ **только владельцу** на чтение и запись (`600`).
3. `public.txt` — владелец читает и пишет, остальные только читают (`644`).
4. Каталог `shared` — `rwxr-xr-x` (`755`).
""",
    hints=["`chmod u+x файл` добавляет владельцу право исполнения.", "Числовая запись: r=4, w=2, x=1; три цифры — владелец, группа, остальные."],
    checks=[
        ("script_exec", "script.sh исполняемый", "script.sh исполняемый", "script.sh должен быть исполняемым для владельца и недоступным для записи другим"),
        ("secret_mode", "secret.txt: 600", "secret.txt доступен только владельцу", "У secret.txt права должны быть 600"),
        ("public_mode", "public.txt: 644", "public.txt настроен верно", "У public.txt права должны быть 644"),
        ("shared_mode", "shared: 755", "Права каталога shared верные", "У каталога shared права должны быть 755"),
    ],
    setup=r"""
mkdir -p ~/perm/shared
printf '#!/bin/bash\necho hi\n' > ~/perm/script.sh; chmod 644 ~/perm/script.sh
echo secret > ~/perm/secret.txt; chmod 666 ~/perm/secret.txt
echo public > ~/perm/public.txt; chmod 600 ~/perm/public.txt
chmod 700 ~/perm/shared
""",
    validate=r"""
P=/home/student/perm
m() { stat -c %a "$1"; }
chk script_exec '[ $(( 0$(m $P/script.sh) & 0100 )) -ne 0 ] && [ $(( 0$(m $P/script.sh) & 0022 )) -eq 0 ]'
chk secret_mode '[ "$(m $P/secret.txt)" = 600 ]'
chk public_mode '[ "$(m $P/public.txt)" = 644 ]'
chk shared_mode '[ "$(m $P/shared)" = 755 ]'
""",
    solution=r"""
cd ~/perm && chmod u+x script.sh && chmod 600 secret.txt && chmod 644 public.txt && chmod 755 shared
""",
    wrong=r"""
cd ~/perm && chmod 777 script.sh && chmod 600 secret.txt && chmod 666 public.txt
""",
)

lab(
    id="linux-010", module="administration", mode="practice", difficulty="junior", minutes=15, xp=100,
    title="Владельцы файлов chown (без выдачи опасных прав)",
    description="Управляйте группой-владельцем: chown :группа, chgrp -R и setgid-каталог. Смена пользователя-владельца требует root и в песочнице не выдаётся.",
    skills=["chown", "chgrp", "ls -l", "setgid"],
    objectives=["Сменить группу-владельца файла", "Рекурсивно сменить группу каталога", "Настроить setgid для общего каталога"],
    task="""\
Вы работаете **без прав root**: пользователя-владельца файлов менять нельзя, но группу — можно, если вы в ней состоите (`id`).

В `~/project`:

1. Файл `app.conf` — группа-владелец `devs` (`chown :devs` или `chgrp`).
2. Каталог `src` вместе со всем содержимым — группа `ops`.
3. Каталог `shared` — группа `devs` и **setgid-бит** (режим `2775`), чтобы новые файлы наследовали группу.
4. `deploy.sh` не трогайте — его группа должна остаться прежней.
""",
    hints=["`ls -l` показывает владельца и группу; `id` — группы, в которых вы состоите.", "`chgrp -R группа каталог` меняет группу рекурсивно.", "Setgid для каталога: `chmod 2775 каталог` (или `chmod g+s`)."],
    checks=[
        ("conf_group", "app.conf в группе devs", "Группа app.conf верная", "Группа app.conf должна быть devs"),
        ("src_group", "src и всё внутри в группе ops", "Группа каталога src верная", "Всё содержимое src (и сам каталог) должно быть в группе ops"),
        ("shared_setgid", "shared: группа devs + setgid", "Каталог shared настроен верно", "У shared должны быть группа devs и бит setgid (2775)"),
        ("deploy_untouched", "deploy.sh не затронут", "deploy.sh не изменён", "Группа deploy.sh была изменена, а не должна"),
    ],
    setup=r"""
mkdir -p ~/project/src ~/project/shared
echo "x=1" > ~/project/app.conf
echo "echo deploy" > ~/project/deploy.sh
echo "main" > ~/project/src/main.c
echo "util" > ~/project/src/util.c
""",
    validate=r"""
P=/home/student/project
chk conf_group '[ "$(stat -c %G $P/app.conf)" = devs ]'
chk src_group '[ "$(stat -c %G $P/src)" = ops ] && [ -z "$(find $P/src ! -group ops)" ]'
chk shared_setgid '[ "$(stat -c %G $P/shared)" = devs ] && [ -g $P/shared ]'
chk deploy_untouched '[ "$(stat -c %G $P/deploy.sh)" = student ]'
""",
    solution=r"""
cd ~/project && chown :devs app.conf && chgrp -R ops src && chgrp devs shared && chmod 2775 shared
""",
    wrong=r"""
chgrp -R devs ~/project
""",
)

lab(
    id="linux-011", module="administration", mode="practice", difficulty="junior", minutes=10, xp=100,
    title="Пользователи и группы (без host privileges)",
    description="Исследуйте учётные записи системы: id, getent, /etc/passwd и /etc/group. Создание пользователей в песочнице недоступно.",
    skills=["id", "getent", "/etc/passwd", "/etc/group"],
    objectives=["Определить свои группы и UID", "Найти пользователя по UID", "Найти GID группы"],
    task="""\
Создавать пользователей без root нельзя — зато можно хорошо изучить существующих. Результаты записывайте в каталог `~/report` (он уже создан).

1. `groups.txt` — **имена групп**, в которых вы состоите (через пробел или по одному на строку).
2. `uid.txt` — ваш числовой UID.
3. `user1001.txt` — имя пользователя с UID `1001`.
4. `gid_devs.txt` — числовой GID группы `devs`.
""",
    hints=["`id` и `id -Gn` покажут ваши UID и группы.", "Данные учётных записей: `getent passwd`, `getent group` или файлы `/etc/passwd` и `/etc/group`."],
    checks=[
        ("groups", "groups.txt: ваши группы", "Список групп верный", "В groups.txt должны быть имена всех ваших групп"),
        ("uid", "uid.txt: ваш UID", "UID верный", "В uid.txt неверное значение"),
        ("user1001", "user1001.txt: имя пользователя 1001", "Пользователь найден верно", "В user1001.txt неверное имя"),
        ("gid_devs", "gid_devs.txt: GID группы devs", "GID верный", "В gid_devs.txt неверное значение"),
    ],
    setup=r"""
mkdir -p ~/report
""",
    validate=r"""
R=/home/student/report
chk groups '[ "$(tr -s " \n" "\n\n" < $R/groups.txt | grep -v "^$" | sort | paste -sd" ")" = "devs ops student" ]'
chk uid '[ "$(tr -d "[:space:]" < $R/uid.txt)" = 1000 ]'
chk user1001 '[ "$(tr -d "[:space:]" < $R/user1001.txt)" = validator ]'
chk gid_devs '[ "$(tr -d "[:space:]" < $R/gid_devs.txt)" = 2001 ]'
""",
    solution=r"""
cd ~/report && id -Gn > groups.txt && id -u > uid.txt && getent passwd 1001 | cut -d: -f1 > user1001.txt && getent group devs | cut -d: -f3 > gid_devs.txt
""",
    wrong=r"""
cd ~/report && id -un > groups.txt && echo 0 > uid.txt && echo root > user1001.txt && echo 1000 > gid_devs.txt
""",
)

lab(
    id="linux-012", module="administration", mode="learn", difficulty="beginner", minutes=15, xp=50,
    title="Переменные окружения",
    description="Разберитесь, как переменные окружения передаются дочерним процессам и как сделать PATH постоянным.",
    skills=["export", "env", "PATH", "~/.profile"],
    objectives=["Экспортировать переменную в дочерний процесс", "Задать переменную на одну команду", "Добавить ~/bin в PATH навсегда"],
    task="""\
1. Выполните `export APP_ENV=production`, затем запустите **дочерний** shell, который напечатает эту переменную, и сохраните его вывод в `~/env_child.txt` (подсказка: `bash -c 'echo $APP_ENV'`).
2. Задайте переменную `GREETING=hi` **только на время одной команды** и сохраните вывод `bash -c 'echo $GREETING'` в `~/greeting.txt`.
3. Создайте исполняемый скрипт `~/bin/hello`, печатающий `hello`, и сделайте так, чтобы команда `hello` находилась **в новой сессии**: добавьте `~/bin` в `PATH` в `~/.profile`.
""",
    hints=["Без `export` переменная видна только текущему shell и не передаётся дочерним процессам.", "`VAR=значение команда` задаёт переменную только для этой команды.", "Постоянные настройки login-shell хранятся в `~/.profile`: `export PATH=\"$HOME/bin:$PATH\"`."],
    checks=[
        ("exported_var", "env_child.txt: production", "Переменная экспортирована", "В ~/env_child.txt должно быть production (нужен export)"),
        ("inline_var", "greeting.txt: hi", "Переменная на одну команду работает", "В ~/greeting.txt должно быть hi"),
        ("hello_in_path", "hello доступен в новой сессии", "Команда hello находится в PATH", "В новой сессии команда hello не находится: добавьте ~/bin в PATH в ~/.profile"),
    ],
    setup=r"""
true
""",
    exercise=r"""
cd ~
rm -f ~/.hello_out
{ bash -lc 'hello' 2>/dev/null; bash -ic 'hello' 2>/dev/null; } | head -n 1 > ~/.hello_out
true
""",
    validate=r"""
H=/home/student
chk exported_var '[ "$(cat $H/env_child.txt)" = production ]'
chk inline_var '[ "$(cat $H/greeting.txt)" = hi ]'
chk hello_in_path '[ -x $H/bin/hello ] && [ "$(cat $H/.hello_out)" = hello ]'
""",
    solution=r"""
export APP_ENV=production
bash -c 'echo $APP_ENV' > ~/env_child.txt
GREETING=hi bash -c 'echo $GREETING' > ~/greeting.txt
mkdir -p ~/bin
printf '#!/bin/bash\necho hello\n' > ~/bin/hello
chmod +x ~/bin/hello
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.profile
""",
    wrong=r"""
APP_ENV=production
bash -c 'echo $APP_ENV' > ~/env_child.txt
GREETING=hi bash -c 'echo $GREETING' > ~/greeting.txt
mkdir -p ~/bin
printf '#!/bin/bash\necho hello\n' > ~/bin/hello
chmod +x ~/bin/hello
export PATH="$HOME/bin:$PATH"
""",
)

lab(
    id="linux-013", module="administration", mode="practice", difficulty="junior", minutes=15, xp=100,
    title="Процессы и сигналы",
    description="Найдите процесс по имени, узнайте его PID и корректно завершите «зависший» процесс, игнорирующий SIGTERM.",
    skills=["ps", "pgrep", "kill", "pkill", "SIGTERM", "SIGKILL"],
    objectives=["Найти PID процесса", "Завершить процесс, игнорирующий SIGTERM", "Не затронуть соседние процессы"],
    task="""\
В песочнице работают два фоновых процесса: `worker.sh` (нужный сервис) и `stuck.sh` (завис и игнорирует обычный `SIGTERM`).

1. Найдите PID процесса `worker.sh` и запишите его в `~/found_pid.txt`.
2. Завершите `stuck.sh`. Процесс `worker.sh` должен продолжить работу!
""",
    hints=["`ps aux | grep -v grep | grep worker` или `pgrep -f worker.sh` покажут PID.", "`kill PID` посылает SIGTERM, который `stuck.sh` игнорирует. Нужен сигнал, который перехватить нельзя: `kill -9`."],
    checks=[
        ("worker_alive", "worker.sh продолжает работать", "worker.sh работает", "Процесс worker.sh завершён — он должен продолжать работу"),
        ("pid_found", "found_pid.txt: PID worker.sh", "PID указан верно", "В ~/found_pid.txt не PID процесса worker.sh"),
        ("stuck_stopped", "stuck.sh завершён", "stuck.sh завершён", "Процесс stuck.sh всё ещё работает"),
    ],
    setup=r"""
mkdir -p ~/bin
printf '#!/bin/bash\nwhile true; do sleep 1; done\n' > ~/bin/worker.sh
printf '#!/bin/bash\ntrap "" TERM INT\nwhile true; do sleep 1; done\n' > ~/bin/stuck.sh
chmod +x ~/bin/worker.sh ~/bin/stuck.sh
setsid nohup ~/bin/worker.sh >/dev/null 2>&1 </dev/null &
setsid nohup ~/bin/stuck.sh >/dev/null 2>&1 </dev/null &
sleep 0.5
""",
    validate=r"""
wp=$(pgrep -f 'bin/worker.sh' | head -n 1)
chk worker_alive '[ -n "$wp" ]'
chk pid_found '[ -n "$wp" ] && [ "$(tr -d "[:space:]" < /home/student/found_pid.txt)" = "$wp" ]'
chk stuck_stopped '! pgrep -f "bin/stuck.sh" > /dev/null'
""",
    solution=r"""
pgrep -f bin/worker.sh > ~/found_pid.txt
pkill -9 -f bin/stuck.sh
sleep 0.3
""",
    wrong=r"""
pgrep -f bin/stuck.sh > ~/found_pid.txt
pkill -f bin/stuck.sh
pkill -9 -f bin/worker.sh
sleep 0.3
""",
    alt={"alt_ps": r"""
ps -eo pid,args | awk '/bin\/worker.sh/ && !/awk/ {print $1}' > ~/found_pid.txt
kill -KILL $(pgrep -f bin/stuck.sh)
sleep 0.3
"""},
)

lab(
    id="linux-014", module="administration", mode="practice", difficulty="junior", minutes=15, xp=100,
    title="Диагностика дискового пространства (quota/workspace)",
    description="Рабочее пространство ограничено по размеру. Найдите, что занимает место, и освободите его, не удалив ценные данные.",
    skills=["du", "df", "sort", "rm"],
    objectives=["Найти самый «тяжёлый» подкаталог", "Освободить место безопасно", "Не удалить важные файлы"],
    task="""\
Каталог `~/disk` почти заполнил квоту рабочего пространства. Внутри три подкаталога: `cache`, `logs`, `media`.

1. Определите **самый большой подкаталог** `~/disk` и запишите его имя (или путь) в `~/biggest.txt`.
2. Освободите место: суммарный размер `~/disk` должен стать **меньше 8 МБ**. Каталог `media` содержит ценные видео — **не удаляйте его файлы**.
""",
    hints=["`du -sk ~/disk/*` покажет размеры подкаталогов (в КБ); отсортируйте `sort -rn`.", "В `cache` лежат устаревшие файлы `*.cache.old` — их безопасно удалить."],
    checks=[
        ("biggest", "biggest.txt: самый большой подкаталог", "Самый большой каталог определён верно", "В ~/biggest.txt указан не самый большой каталог"),
        ("space_freed", "Размер ~/disk меньше 8 МБ", "Место освобождено", "Размер ~/disk всё ещё не меньше 8 МБ"),
        ("media_intact", "Файлы media сохранены", "Ценные файлы целы", "Файлы каталога media удалены или изменены"),
    ],
    setup=r"""
mkdir -p ~/disk/cache ~/disk/logs ~/disk/media
i=1; while [ $i -le 6 ]; do dd if=/dev/zero of=$HOME/disk/cache/blob$i.cache.old bs=1M count=1 2>/dev/null; i=$((i+1)); done
i=1; while [ $i -le 3 ]; do dd if=/dev/zero of=$HOME/disk/logs/app$i.log bs=1M count=1 2>/dev/null; i=$((i+1)); done
dd if=/dev/zero of=$HOME/disk/media/video1.bin bs=1M count=1 2>/dev/null
dd if=/dev/zero of=$HOME/disk/media/video2.bin bs=1M count=1 2>/dev/null
""",
    validate=r"""
D=/home/student/disk
chk biggest '[ "$(basename "$(tr -d "\n" < /home/student/biggest.txt)")" = cache ]'
chk space_freed '[ "$(du -sk $D | cut -f1)" -lt 8192 ]'
chk media_intact '[ "$(stat -c %s $D/media/video1.bin)" = 1048576 ] && [ "$(stat -c %s $D/media/video2.bin)" = 1048576 ]'
""",
    solution=r"""
du -sk ~/disk/* | sort -rn | head -1 | cut -f2 > ~/biggest.txt
rm ~/disk/cache/*.cache.old
""",
    wrong=r"""
echo logs > ~/biggest.txt
rm -rf ~/disk/media
""",
)

lab(
    id="linux-015", module="administration", mode="practice", difficulty="middle", minutes=25, xp=150,
    title="Bash-скрипт резервного копирования",
    description="Напишите настоящий bash-скрипт: аргументы, проверки, код возврата и создание датированного архива.",
    skills=["bash", "аргументы $1 $2", "date", "tar", "коды возврата"],
    objectives=["Принять каталоги через аргументы", "Создать датированный tar.gz", "Корректно сообщить об ошибке кодом возврата"],
    task="""\
Напишите скрипт `~/backup.sh`, который вызывается так: `bash ~/backup.sh ИСТОЧНИК НАЗНАЧЕНИЕ`.

Требования:

- создаёт каталог назначения, если его нет;
- упаковывает **содержимое** каталога-источника в `НАЗНАЧЕНИЕ/backup-ГГГГ-ММ-ДД.tar.gz` (дата сегодняшняя, формат `date +%F`);
- при успехе печатает `Backup created: <путь к архиву>` и завершается с кодом `0`;
- если источника не существует — печатает ошибку в **stderr**, **ничего не создаёт** и завершается с ненулевым кодом.

Проверка запустит ваш скрипт на каталоге `~/data` (внутри `report.txt` и `notes.md`).
""",
    hints=["Начните со строк `src=\"$1\"; dest=\"$2\"` и проверки `[ -d \"$src\" ] || exit 1`.", "Имя архива: `backup-$(date +%F).tar.gz`; содержимое каталога: `tar czf архив -C \"$src\" .`.", "Ошибки пишутся в stderr так: `echo \"...\" >&2`."],
    checks=[
        ("script_exists", "Скрипт ~/backup.sh создан", "Скрипт найден", "Файл ~/backup.sh не найден"),
        ("backup_created", "Создан backup-ГГГГ-ММ-ДД.tar.gz", "Архив создан с верным именем", "В ~/backups нет архива backup-<сегодняшняя дата>.tar.gz"),
        ("archive_valid", "Архив валиден и содержит файлы", "Архив содержит report.txt и notes.md", "Архив повреждён или не содержит report.txt и notes.md"),
        ("exit_code_ok", "Код возврата 0 и сообщение Backup created", "Успешный запуск оформлен верно", "При успехе скрипт должен вернуть 0 и напечатать «Backup created: …»"),
        ("missing_source", "Отсутствующий источник даёт ошибку", "Ошибка обрабатывается верно", "Для несуществующего источника нужен ненулевой код возврата и отсутствие архива"),
    ],
    setup=r"""
mkdir -p ~/data
printf 'quarterly report\n' > ~/data/report.txt
printf '# notes\n' > ~/data/notes.md
""",
    exercise=r"""
cd ~
rm -rf ~/backups ~/backups2 ~/.ex
mkdir -p ~/.ex
if [ -f ~/backup.sh ]; then
  timeout 8 bash ~/backup.sh ~/data ~/backups > ~/.ex/out1.txt 2>&1 < /dev/null; echo $? > ~/.ex/rc1.txt
  timeout 8 bash ~/backup.sh ~/no_such_dir ~/backups2 > ~/.ex/out2.txt 2>&1 < /dev/null; echo $? > ~/.ex/rc2.txt
fi
true
""",
    validate=r"""
H=/home/student
E=$H/.ex
F=$H/backups/backup-$(date +%F).tar.gz
chk script_exists '[ -f $H/backup.sh ]'
chk backup_created '[ -f $F ]'
chk archive_valid 'gzip -t $F && L=$(tar tzf $F) && echo "$L" | grep -q report.txt && echo "$L" | grep -q notes.md'
chk exit_code_ok '[ "$(cat $E/rc1.txt)" = 0 ] && grep -q "Backup created" $E/out1.txt'
chk missing_source '[ -n "$(cat $E/rc2.txt)" ] && [ "$(cat $E/rc2.txt)" != 0 ] && [ ! -e $H/backups2 ]'
""",
    solution=r"""
cat > ~/backup.sh <<'EOT'
#!/bin/bash
src="$1"; dest="$2"
if [ ! -d "$src" ]; then
  echo "error: source directory not found: $src" >&2
  exit 1
fi
mkdir -p "$dest"
out="$dest/backup-$(date +%F).tar.gz"
tar czf "$out" -C "$src" . && echo "Backup created: $out"
EOT
""",
    wrong=r"""
printf '#!/bin/bash\necho "Backup created"\nexit 0\n' > ~/backup.sh
""",
)
