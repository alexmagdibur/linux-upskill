"""Данные новых лабораторий программы, часть B: этап 2 «Джун» (терминал, файлы, потоки, права, процессы, bash, backup)."""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append(kw)


# ------------------------------------------------------------------ Терминал, shell и окружение
lab(
    id="ld-001", title="Где я? Текущий каталог, HOME и путь к bash",
    description="Среди одинаково названных файлов найдите нужные пути и запишите их в JSON.",
    skills=["pwd", "$HOME", "command -v", "JSON"],
    objectives=["Определить cwd, HOME и интерпретатор", "Не перепутать декоры с настоящими путями"],
    task="""\
В `~/maze` много одинаковых имён (`bash`, `b`, …) — это ловушки.

1. Перейдите в `~/maze/a/b`.
2. Запишите в `~/answer.json` JSON-объект с тремя ключами:
   - `cwd` — абсолютный путь текущего каталога;
   - `home` — ваш домашний каталог;
   - `bash` — абсолютный путь **исполняемого** `bash`, который запускается по имени.
""",
    hints=["`pwd`, `echo $HOME` и `command -v bash` дают нужные значения.", "Соберите JSON через `printf '{\"cwd\":\"%s\",...}\\n' ...`."],
    checks=[
        ("json_valid", "answer.json — корректный JSON", "JSON корректен", "~/answer.json не является корректным JSON-объектом"),
        ("paths_ok", "cwd, home и bash указаны верно", "Пути верные", "Пути в answer.json неверны (cwd=~/maze/a/b, home, настоящий bash)"),
    ],
    setup=r"""
mkdir -p ~/maze/a/b ~/maze/c/b
: > ~/maze/a/b/bash; : > ~/maze/c/b/bash
""",
    validate=r"""
chk_py() { python3 - "$1" <<'EOT'
import json, os, sys
try:
    d = json.load(open("/home/student/answer.json"))
except Exception:
    print("BAD"); sys.exit()
if sys.argv[1] == "valid":
    print("OK" if isinstance(d, dict) and {"cwd", "home", "bash"} <= set(d) else "BAD")
else:
    ok = d.get("cwd") == "/home/student/maze/a/b" and d.get("home") == "/home/student" and d.get("bash") in ("/usr/bin/bash", "/bin/bash")
    print("OK" if ok else "BAD")
EOT
}
chk json_valid '[ "$(chk_py valid)" = OK ]'
chk paths_ok '[ "$(chk_py paths)" = OK ]'
""",
    solution=r"""
cd ~/maze/a/b && printf '{"cwd":"%s","home":"%s","bash":"%s"}\n' "$PWD" "$HOME" "$(command -v bash)" > ~/answer.json
""",
    wrong=r"""
printf '{"cwd":"%s","home":"%s","bash":"%s"}\n' "$HOME/maze/c/b" "$HOME" "$HOME/maze/a/b/bash" > ~/answer.json
""",
)

lab(
    id="ld-002", title="Относительные пути и соседний процесс",
    description="Создайте каталог в проекте через относительные пути, не затронув процесс в соседнем каталоге.",
    skills=["cd", "mkdir -p", "относительные пути"],
    objectives=["Создать reports/today в нужном проекте", "Не вмешиваться в соседние процессы и файлы"],
    task="""\
Есть два каталога: проект `~/work/proj` и соседний `~/work/other` (там работает фоновый процесс и лежат файлы).

Перейдите в проект и создайте `reports/today` **внутри `~/work/proj`**. Соседний каталог, его файлы и процесс трогать нельзя.
""",
    hints=["Убедитесь, где находитесь: `pwd`. Создавайте путь относительно проекта.", "`mkdir -p reports/today` создаёт оба уровня."],
    checks=[
        ("created", "Создан ~/work/proj/reports/today", "Каталог создан в проекте", "Каталог ~/work/proj/reports/today не найден"),
        ("neighbors_intact", "Соседние файлы и процесс целы", "Соседний процесс и файлы целы", "Соседний каталог изменён или его процесс остановлен"),
    ],
    setup=r"""
mkdir -p ~/work/proj ~/work/other
echo keep > ~/work/other/keep.txt
( cd ~/work/other && setsid nohup sleep 3601 ) >/dev/null 2>&1 </dev/null &
sleep 0.3
""",
    validate=r"""
W=/home/student/work
chk created '[ -d $W/proj/reports/today ] && [ ! -e $W/reports ]'
chk neighbors_intact 'pgrep -f "sleep 3601" && [ "$(cat $W/other/keep.txt)" = keep ] && [ ! -e $W/other/reports ]'
""",
    solution="cd ~/work/proj && mkdir -p reports/today\n",
    wrong="mkdir -p ~/work/reports/today\n",
)

lab(
    id="ld-003", title="Alias, функция или бинарник: что реально запускается",
    description="В окружении подменён grep: выясните, что запускается на самом деле, и вызовите системный бинарник.",
    skills=["type", "alias", "command", "/usr/bin/grep"],
    objectives=["Отличить alias, function и бинарник", "Вызвать настоящий grep"],
    task="""\
В вашей оболочке `grep` ведёт себя странно: `grep apple ~/data/fruit.txt` печатает не то, что ожидается.

1. Выясните, чем на самом деле является `grep` (`type grep`) и где лежит настоящий бинарник.
2. В `~/report.txt` напишите одной-двумя фразами: что это (слово `alias`) и путь настоящего бинарника.
3. Настоящим `grep` найдите строки с `apple` в `~/data/fruit.txt` и сохраните их в `~/apples.txt`.

Подсказка: попробуйте открыть новую login-оболочку (`bash -l`), если подмена не видна.
""",
    hints=["`type grep` покажет, что это alias, а `type -a grep` — все варианты.", "Обойти alias можно так: `/usr/bin/grep`, `command grep` или `\\grep`."],
    checks=[
        ("report", "report.txt: alias и путь бинарника", "Отчёт различает alias и бинарник", "В report.txt должны быть слово alias и путь /usr/bin/grep"),
        ("apples", "apples.txt: строки с apple", "Результат поиска верный", "В apples.txt не те строки: ищите настоящим grep"),
    ],
    setup=r"""
mkdir -p ~/data
printf 'apple pie\nbanana\ngreen apple\ncherry\n' > ~/data/fruit.txt
printf '[ -f ~/.bashrc ] && . ~/.bashrc\n' > ~/.profile
printf "alias grep='grep -v'\n" > ~/.bashrc
""",
    validate=r"""
H=/home/student
chk report 'grep -qi alias $H/report.txt && grep -q "/usr/bin/grep" $H/report.txt'
chk apples '[ "$(cat $H/apples.txt)" = "$(printf "apple pie\ngreen apple")" ]'
""",
    solution=r"""
echo "grep — это alias на 'grep -v'; настоящий бинарник: /usr/bin/grep" > ~/report.txt
/usr/bin/grep apple ~/data/fruit.txt > ~/apples.txt
""",
    wrong=r"""
echo "grep сломан" > ~/report.txt
grep -v apple ~/data/fruit.txt > ~/apples.txt
""",
)

lab(
    id="ld-004", title="Переменная окружения только для дочерних процессов",
    description="Передайте APP_MODE дочернему процессу, но не сохраняйте её в профиле.",
    skills=["export", "окружение процесса", "~/.profile"],
    objectives=["Экспортировать переменную", "Не сделать её постоянной"],
    task="""\
Скрипт `~/bin/show_mode.sh` печатает `mode=$APP_MODE`.

1. Сделайте `APP_MODE=prod` доступной **дочернему** процессу и сохраните вывод скрипта в `~/child_out.txt`.
2. Не записывайте переменную ни в один файл профиля: новая независимая оболочка её видеть не должна.
""",
    hints=["Без `export` дочерний процесс переменную не увидит.", "Запись в `~/.profile`/`~/.bashrc` сделала бы переменную постоянной — этого делать не нужно."],
    checks=[
        ("child_sees", "Дочерний скрипт видит APP_MODE", "Дочерний процесс увидел значение", "В child_out.txt должно быть mode=prod"),
        ("not_persistent", "Новый сеанс переменную не видит", "Переменная не сохранилась", "Переменная попала в профиль и видна в новом сеансе"),
    ],
    setup=r"""
mkdir -p ~/bin
printf '#!/bin/bash\necho "mode=$APP_MODE"\n' > ~/bin/show_mode.sh
chmod +x ~/bin/show_mode.sh
""",
    exercise=r"""
mkdir -p ~/.ex
env -i HOME=/home/student PATH=/usr/local/bin:/usr/bin:/bin bash -lc 'echo ${APP_MODE:-unset}' > ~/.ex/fresh 2>/dev/null
true
""",
    validate=r"""
H=/home/student
chk child_sees '[ "$(cat $H/child_out.txt)" = mode=prod ]'
chk not_persistent '[ "$(cat $H/.ex/fresh)" = unset ]'
""",
    solution="export APP_MODE=prod\n~/bin/show_mode.sh > ~/child_out.txt\n",
    wrong="echo 'export APP_MODE=prod' >> ~/.profile\nexport APP_MODE=prod\n~/bin/show_mode.sh > ~/child_out.txt\n",
)

lab(
    id="ld-005", title="Условное выполнение: && и очистка при любом исходе",
    description="Соберите запуск трёх шагов: второй — только после успеха первого, очистка — всегда.",
    skills=["&&", ";", "trap", "коды завершения"],
    objectives=["Выполнять второй шаг только при успехе первого", "Гарантировать очистку"],
    task="""\
Есть шаги `~/bin/first.sh`, `~/bin/second.sh` и `~/bin/cleanup.sh` (каждый дописывает своё имя в файл `$TRACE`).

Напишите `~/run.sh`, который:

- запускает `second.sh` **только если** `first.sh` завершился успешно;
- запускает `cleanup.sh` **всегда**, независимо от результата первого.

Проверка запустит `bash ~/run.sh` дважды: когда `first.sh` успешен и когда он падает (переменная `FAIL_FIRST=1`).
""",
    hints=["`a && b` запускает b только при успехе a; `;` выполняет следующую команду всегда.", "Другой вариант — `trap ~/bin/cleanup.sh EXIT` в начале скрипта."],
    checks=[
        ("success_path", "При успехе: first, second, cleanup", "Успешный путь верный", "При успехе first должны идти first, second, cleanup"),
        ("failure_path", "При сбое: first, cleanup", "Путь при сбое верный", "При падении first должны выполниться только first и cleanup"),
    ],
    setup=r"""
mkdir -p ~/bin
printf '#!/bin/bash\necho first >> "$TRACE"\n[ -z "$FAIL_FIRST" ]\n' > ~/bin/first.sh
printf '#!/bin/bash\necho second >> "$TRACE"\n' > ~/bin/second.sh
printf '#!/bin/bash\necho cleanup >> "$TRACE"\n' > ~/bin/cleanup.sh
chmod +x ~/bin/*.sh
""",
    exercise=r"""
mkdir -p ~/.ex; rm -f ~/.ex/a ~/.ex/b
[ -f ~/run.sh ] || exit 0
TRACE=~/.ex/a timeout 8 bash ~/run.sh > /dev/null 2>&1 < /dev/null
FAIL_FIRST=1 TRACE=~/.ex/b timeout 8 bash ~/run.sh > /dev/null 2>&1 < /dev/null
true
""",
    validate=r"""
E=/home/student/.ex
chk success_path '[ "$(cat $E/a)" = "$(printf "first\nsecond\ncleanup")" ]'
chk failure_path '[ "$(cat $E/b)" = "$(printf "first\ncleanup")" ]'
""",
    solution="printf '#!/bin/bash\\n~/bin/first.sh && ~/bin/second.sh\\n~/bin/cleanup.sh\\n' > ~/run.sh\n",
    wrong="printf '#!/bin/bash\\n~/bin/first.sh && ~/bin/second.sh && ~/bin/cleanup.sh\\n' > ~/run.sh\n",
    alt={"alt_trap": "printf '#!/bin/bash\\ntrap ~/bin/cleanup.sh EXIT\\n~/bin/first.sh && ~/bin/second.sh\\n' > ~/run.sh\n"},
)

lab(
    id="ld-006", title="Инцидент: скрипт запускает не тот python3",
    description="Из-за порядка PATH скрипт берёт чужой python3. Исправьте окружение, не удаляя ни одну версию.",
    skills=["PATH", "command -v", "type -a", "~/.profile"],
    objectives=["Доказать, какой интерпретатор запускается", "Исправить порядок PATH", "Сохранить оба бинарника"],
    task="""\
**Инцидент.** `~/app/run.sh` печатает `OLD python …` и падает: вместо системного Python запускается старый из `~/opt/old`.

Исправьте среду запуска так, чтобы скрипт использовал системный `python3` (`OK python 3.x`). **Удалять `~/opt/old/python3` нельзя** — он нужен для совместимости и должен остаться доступным (в конце PATH).

Проверка запускает скрипт в новой login-оболочке.
""",
    hints=["`type -a python3` покажет все `python3` в порядке PATH.", "PATH задаётся в `~/.profile`: нужный каталог должен стоять **после** системных."],
    checks=[
        ("uses_system_python", "Скрипт использует системный python3", "Скрипт использует системный Python", "В новой login-оболочке run.sh всё ещё берёт старый python3"),
        ("both_available", "Оба бинарника сохранены", "Оба интерпретатора на месте", "~/opt/old/python3 или системный python3 пропали"),
    ],
    setup=r"""
mkdir -p ~/opt/old ~/app
printf '#!/bin/bash\necho "OLD python 2.7 (legacy)"\nexit 1\n' > ~/opt/old/python3
chmod +x ~/opt/old/python3
printf 'import sys\nprint("OK python %%d.%%d" %% sys.version_info[:2])\n' > ~/app/check.py
printf '#!/bin/bash\npython3 "$HOME/app/check.py"\n' > ~/app/run.sh
chmod +x ~/app/run.sh
printf 'export PATH="$HOME/opt/old:$PATH"\n' > ~/.profile
""",
    exercise=r"""
mkdir -p ~/.ex
env -i HOME=/home/student PATH=/usr/local/bin:/usr/bin:/bin timeout 8 bash -lc '~/app/run.sh' > ~/.ex/out 2>&1 < /dev/null
true
""",
    validate=r"""
H=/home/student
chk uses_system_python 'grep -q "^OK python 3" $H/.ex/out'
chk both_available '[ -x $H/opt/old/python3 ] && [ -x /usr/bin/python3 ]'
""",
    solution="sed -i 's#^export PATH=.*#export PATH=\"$PATH:$HOME/opt/old\"#' ~/.profile\n",
    wrong="rm -rf ~/opt/old\n",
)

# ---------------------------------------------------------------------------- Файлы и каталоги
lab(
    id="ld-017", title="Поиск крупных свежих файлов без кэша",
    description="Найдите файлы больше заданного размера, изменённые за последние сутки, исключив кэш.",
    skills=["find", "-size", "-mtime", "-not -path"],
    objectives=["Объединить условия find", "Исключить каталог кэша"],
    task="""\
В `~/tree` лежат файлы разного размера и возраста.

Запишите в `~/found.txt` абсолютные пути файлов, которые **одновременно**: больше 1 МБ, изменены за последние сутки и **не лежат в каталоге `cache`**. По одному пути на строку.
""",
    hints=["`find ~/tree -type f -size +1M -mtime -1` выбирает по размеру и возрасту.", "Исключить каталог: `-not -path '*/cache/*'`."],
    checks=[("found", "found.txt: нужные файлы", "Список верный", "В found.txt не тот список файлов (проверьте размер, возраст и исключение cache)")],
    setup=r"""
mkdir -p ~/tree/data ~/tree/cache ~/tree/old
truncate -s 2M ~/tree/data/big_recent.bin
truncate -s 2M ~/tree/cache/big_cached.bin
truncate -s 2M ~/tree/old/big_old.bin; touch -d '5 days ago' ~/tree/old/big_old.bin
truncate -s 100K ~/tree/data/small_recent.bin
""",
    validate=r"""
chk found '[ "$(sort /home/student/found.txt)" = "/home/student/tree/data/big_recent.bin" ]'
""",
    solution="find ~/tree -type f -size +1M -mtime -1 -not -path '*/cache/*' > ~/found.txt\n",
    wrong="find ~/tree -type f -size +1M -mtime -1 > ~/found.txt\n",
)

lab(
    id="ld-018", title="Символическая и жёсткая ссылки",
    description="Отличите symlink от hardlink и докажите, что остаётся после удаления исходного имени.",
    skills=["ln", "ln -s", "stat", "inode"],
    objectives=["Создать обе ссылки", "Зафиксировать inode", "Увидеть последствия удаления"],
    task="""\
В `~/links` лежит `orig.txt`.

1. Создайте жёсткую ссылку `hard` и символическую ссылку `soft` на `orig.txt` (в том же каталоге, `soft` — относительная).
2. Запомните номер inode `orig.txt` (`stat -c %i`), затем **удалите** `orig.txt`.
3. В `~/links/report.txt` запишите номер inode и по одной фразе о том, что стало с `hard` и с `soft` (используйте слова `hard` и `soft`).
""",
    hints=["`ln orig.txt hard` — жёсткая, `ln -s orig.txt soft` — символическая.", "Жёсткая ссылка — то же имя того же inode; symlink хранит лишь путь и «ломается» после удаления цели."],
    checks=[
        ("hard_survives", "hard сохранила данные (тот же inode)", "Жёсткая ссылка пережила удаление", "hard должна быть жёсткой ссылкой на исходный inode с содержимым data"),
        ("soft_dangles", "soft стала «битой»", "Символическая ссылка стала битой", "soft должна быть относительной ссылкой на orig.txt и после удаления оригинала — битой"),
        ("report", "Отчёт: inode, hard, soft", "Отчёт содержит inode и выводы", "В report.txt нужны номер inode и слова hard и soft"),
    ],
    setup=r"""
mkdir -p ~/links
echo data > ~/links/orig.txt
stat -c %i ~/links/orig.txt > ~/.ref_inode
""",
    validate=r"""
L=/home/student/links
ref=$(cat /home/student/.ref_inode)
chk hard_survives '[ ! -e $L/orig.txt ] && [ "$(stat -c %i $L/hard)" = "$ref" ] && [ "$(cat $L/hard)" = data ]'
chk soft_dangles '[ -L $L/soft ] && [ ! -e $L/soft ] && [ "$(readlink $L/soft)" = orig.txt ]'
chk report 'grep -q "$ref" $L/report.txt && grep -qi hard $L/report.txt && grep -qi soft $L/report.txt'
""",
    solution=r"""
cd ~/links && ln orig.txt hard && ln -s orig.txt soft
ino=$(stat -c %i orig.txt)
rm orig.txt
echo "inode=$ino; hard: данные сохранились; soft: битая ссылка" > report.txt
""",
    wrong=r"""
cd ~/links && cp orig.txt hard && ln -s orig.txt soft && rm orig.txt
echo "всё сломалось" > report.txt
""",
)

lab(
    id="ld-019", title="Инцидент: приложение читает старый конфиг через неверную ссылку",
    description="Относительная ссылка указывает на старую конфигурацию. Исправьте ссылку, не копируя конфиг.",
    skills=["ln -sfn", "readlink -f", "относительные ссылки"],
    objectives=["Найти цель ссылки", "Перенаправить её на новую версию", "Не копировать файл"],
    task="""\
**Инцидент.** После релиза `~/app/run.sh` печатает `LEVEL=old`, хотя новая конфигурация лежит в `~/app/releases/v2/app.conf`.

`~/app/config` — символическая ссылка (смотрите `ls -l`). Направьте её на новую конфигурацию (относительным путём). **Копировать файл нельзя.**
""",
    hints=["`readlink config` и `ls -l` покажут, куда ведёт ссылка.", "`ln -sfn releases/v2/app.conf config` пересоздаёт ссылку (путь считается от каталога самой ссылки)."],
    checks=[
        ("points_to_v2", "config ведёт на releases/v2/app.conf", "Ссылка указывает на новую конфигурацию", "config должен быть символической ссылкой на releases/v2/app.conf"),
        ("app_sees_new", "Приложение видит LEVEL=new", "Приложение читает новую конфигурацию", "run.sh всё ещё не видит новое значение"),
        ("no_copy", "Файлы конфигурации не подменены", "Файлы конфигурации целы", "Содержимое old/ или v2/ изменено"),
    ],
    setup=r"""
mkdir -p ~/app/old ~/app/releases/v2
echo LEVEL=old > ~/app/old/app.conf
echo LEVEL=new > ~/app/releases/v2/app.conf
ln -s old/app.conf ~/app/config
printf '#!/bin/bash\ncd "$(dirname "$0")" && cat config\n' > ~/app/run.sh
chmod +x ~/app/run.sh
""",
    exercise=r"""
mkdir -p ~/.ex
~/app/run.sh > ~/.ex/out 2>&1
true
""",
    validate=r"""
A=/home/student/app
chk points_to_v2 '[ -L $A/config ] && [ "$(readlink -f $A/config)" = $A/releases/v2/app.conf ]'
chk app_sees_new '[ "$(cat /home/student/.ex/out)" = LEVEL=new ]'
chk no_copy '[ "$(cat $A/old/app.conf)" = LEVEL=old ] && [ "$(cat $A/releases/v2/app.conf)" = LEVEL=new ]'
""",
    solution="cd ~/app && ln -sfn releases/v2/app.conf config\n",
    wrong="cp ~/app/releases/v2/app.conf ~/app/config\n",
)

# ------------------------------------------------------------------------- Потоки, текст и данные
lab(
    id="ld-009", title="Разделение stdout и stderr с сохранением кода выхода",
    description="Запустите утилиту так, чтобы поток результата и поток ошибок попали в разные файлы, а код выхода не потерялся.",
    skills=["2>", ">", "$?", "потоки"],
    objectives=["Разделить потоки", "Сохранить код выхода"],
    task="""\
`~/bin/tool.sh` печатает результат в stdout, предупреждение в stderr и завершается с ненулевым кодом.

Запустите его **один раз** так, чтобы:

- stdout попал в `~/out.txt`;
- stderr — в `~/err.txt`;
- **код выхода** утилиты записан в `~/rc.txt`.
""",
    hints=["`команда > out.txt 2> err.txt` разделяет потоки.", "Код выхода читается сразу после запуска: `echo $? > rc.txt`."],
    checks=[
        ("stdout", "out.txt: только stdout", "stdout в правильном файле", "В out.txt должна быть только строка stdout утилиты"),
        ("stderr", "err.txt: только stderr", "stderr в правильном файле", "В err.txt должна быть только строка stderr утилиты"),
        ("rc", "rc.txt: исходный код выхода", "Код выхода сохранён", "В rc.txt должен быть код выхода утилиты (3)"),
    ],
    setup=r"""
mkdir -p ~/bin
printf '#!/bin/bash\necho "stdout: ready"\necho "stderr: warning" >&2\nexit 3\n' > ~/bin/tool.sh
chmod +x ~/bin/tool.sh
""",
    validate=r"""
H=/home/student
chk stdout '[ "$(cat $H/out.txt)" = "stdout: ready" ]'
chk stderr '[ "$(cat $H/err.txt)" = "stderr: warning" ]'
chk rc '[ "$(tr -d "[:space:]" < $H/rc.txt)" = 3 ]'
""",
    solution="~/bin/tool.sh > ~/out.txt 2> ~/err.txt; echo $? > ~/rc.txt\n",
    wrong="~/bin/tool.sh > ~/out.txt 2>&1; echo $? > ~/rc.txt\n",
)

lab(
    id="ld-010", title="Топ IP из лога в CSV",
    description="Напишите скрипт, который считает запросы по IP и выдаёт CSV, отсортированный по частоте.",
    skills=["awk", "sort", "uniq -c", "CSV"],
    objectives=["Подсчитать уникальные IP", "Отсортировать по частоте и по IP при равенстве", "Выдать корректный CSV"],
    task="""\
Напишите `~/ipcount.sh ЛОГ`, который выводит в stdout CSV:

- первая строка — заголовок `ip,count`;
- далее по строке на каждый уникальный IP (первое поле строки лога) и число его запросов;
- сортировка: **по убыванию числа запросов**, при равенстве — **по возрастанию IP**.

Пример лога — `~/data/access.log`. Проверка запустит скрипт на скрытом логе.
""",
    hints=["`awk '{print $1}' лог | sort | uniq -c` даёт пары «число IP».", "Двухключевая сортировка: `sort -k1,1nr -k2,2`; затем переставьте поля в `ip,count`."],
    checks=[("csv", "CSV верен на скрытом логе", "CSV посчитан верно", "Вывод ipcount.sh на скрытом логе не совпадает с эталоном (заголовок, счётчики, порядок при равенстве)")],
    setup=r"""
mkdir -p ~/data
printf '10.0.0.1 - GET /a 200\n10.0.0.2 - GET /b 200\n10.0.0.1 - GET /c 404\n' > ~/data/access.log
""",
    exercise=r"""
mkdir -p ~/.ex
python3 - > ~/.ex/hidden.log <<'EOT'
import random
random.seed(7)
ips = ["10.1.1.%d" % i for i in range(1, 9)]
weights = [3, 9, 1, 7, 5, 9, 2, 5]
for _ in range(120):
    print("%s - GET /x 200" % random.choices(ips, weights)[0])
EOT
[ -f ~/ipcount.sh ] && timeout 8 bash ~/ipcount.sh ~/.ex/hidden.log > ~/.ex/out.csv 2>/dev/null < /dev/null
true
""",
    validate=r"""
expected() { python3 - <<'EOT'
import collections
c = collections.Counter(l.split()[0] for l in open("/home/student/.ex/hidden.log"))
print("ip,count")
for ip, n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])):
    print("%s,%d" % (ip, n))
EOT
}
chk csv '[ "$(cat /home/student/.ex/out.csv)" = "$(expected)" ]'
""",
    solution=r"""
cat > ~/ipcount.sh <<'EOT'
#!/bin/bash
echo "ip,count"
awk '{print $1}' "$1" | sort | uniq -c | sort -k1,1nr -k2,2 | awk '{print $2 "," $1}'
EOT
""",
    wrong=r"""
cat > ~/ipcount.sh <<'EOT'
#!/bin/bash
echo "ip,count"
awk '{print $1}' "$1" | sort | uniq -c | awk '{print $2 "," $1}'
EOT
""",
)

lab(
    id="ld-011", title="CSV с кавычками и запятыми в полях",
    description="Извлеките записи с ошибкой из CSV, где поля содержат запятые и кавычки; простой cut здесь не подходит.",
    skills=["python3 csv", "awk", "краевые случаи"],
    objectives=["Корректно разобрать CSV", "Сохранить исходное квотирование"],
    task="""\
В `~/data/events.csv` колонки `id,message,level,host`; в сообщениях бывают запятые и кавычки.

Сохраните в `~/errors.csv` заголовок и **только записи, где `level` = `ERROR`**. Файл должен оставаться корректным CSV (поля с запятыми — в кавычках).

Подсказка: `cut -d,` ломается на запятых внутри кавычек — используйте модуль `csv` в `python3`.
""",
    hints=["Посмотрите файл: `cat ~/data/events.csv`.", "`python3 -c 'import csv,sys; ...'` — читайте `csv.reader`, пишите `csv.writer`."],
    checks=[("errors", "errors.csv: только ERROR-записи", "Записи извлечены верно", "errors.csv должен содержать заголовок и только строки ERROR, с корректным CSV-квотированием")],
    setup=r'''
mkdir -p ~/data
cat > ~/data/events.csv <<'EOT'
id,message,level,host
1,"started, ok",INFO,web1
2,"disk full, retry later",ERROR,db1
3,plain failure,ERROR,web2
4,"say ""hi""",WARN,web1
5,"multi, comma, fields",ERROR,cache1
6,done,INFO,web2
EOT
''',
    validate=r"""
chk_csv() { python3 - <<'EOT'
import csv
try:
    rows = list(csv.reader(open("/home/student/errors.csv", newline="")))
except Exception:
    print("BAD"); raise SystemExit
exp = [["id", "message", "level", "host"], ["2", "disk full, retry later", "ERROR", "db1"], ["3", "plain failure", "ERROR", "web2"], ["5", "multi, comma, fields", "ERROR", "cache1"]]
print("OK" if rows == exp else "BAD")
EOT
}
chk errors '[ "$(chk_csv)" = OK ]'
""",
    solution=r"""
python3 - <<'EOT'
import csv
with open("/home/student/data/events.csv", newline="") as src, open("/home/student/errors.csv", "w", newline="") as dst:
    r, w = csv.reader(src), csv.writer(dst)
    header = next(r)
    w.writerow(header)
    for row in r:
        if row[2] == "ERROR":
            w.writerow(row)
EOT
""",
    wrong="awk -F, 'NR==1 || $3==\"ERROR\"' ~/data/events.csv > ~/errors.csv\n",
)

# ------------------------------------------------------------------------- Права и пользователи
lab(
    id="ld-025", title="Чтение отчёта для группы при закрытом ключе",
    description="Дайте группе devs читать отчёт, оставив ключ в том же каталоге закрытым.",
    skills=["chgrp", "chmod", "права группы"],
    objectives=["Выдать группе минимально необходимый доступ", "Сохранить секрет закрытым"],
    task="""\
В `~/secure` лежат `report.txt` и `key.pem` (оба `600`, каталог `700`).

Дайте **группе `devs`** право **читать `report.txt`** (для этого группа должна «заходить» в каталог). Файл `key.pem` должен остаться закрытым: никакого доступа ни группе, ни остальным.

Проверка читает файлы от имени другого пользователя из группы `devs`.
""",
    hints=["Сначала смените группу каталога и отчёта на `devs` (`chgrp`), затем добавьте права: каталогу `g+x`, отчёту `g+r`.", "Не используйте `chmod -R 777`: ключ откроется всем."],
    checks=[
        ("report_readable", "Группа читает report.txt", "Группа может читать отчёт", "Пользователь группы devs не может прочитать report.txt"),
        ("key_closed", "key.pem остаётся закрытым", "Ключ закрыт", "key.pem должен остаться 600 и недоступным группе и остальным"),
    ],
    setup=r"""
mkdir -p ~/secure
echo "Q3 results" > ~/secure/report.txt; chmod 600 ~/secure/report.txt
echo "PRIVATE KEY" > ~/secure/key.pem; chmod 600 ~/secure/key.pem
chmod 700 ~/secure
""",
    validate=r"""
S=/home/student/secure
chk report_readable '[ "$(cat $S/report.txt)" = "Q3 results" ]'
chk key_closed '[ "$(stat -c %a $S/key.pem)" = 600 ] && [ ! -r $S/key.pem ]'
""",
    solution="cd ~/secure && chgrp devs . report.txt && chmod 750 . && chmod 640 report.txt\n",
    wrong="chmod -R 777 ~/secure\n",
)

lab(
    id="ld-026", title="Зачем каталогу бит x",
    description="Экспериментом покажите, что без бита x на каталоге файл внутри недоступен, даже если сам читаем.",
    skills=["chmod", "stat", "права каталога"],
    objectives=["Воспроизвести Permission denied", "Исправить правом x у каталога", "Зафиксировать права до/после"],
    task="""\
Каталог `~/exp/vault` имеет режим `644` и содержит читаемый файл `note.txt`.

1. Убедитесь, что `cat ~/exp/vault/note.txt` даёт `Permission denied`.
2. Исправьте каталог так, чтобы владелец мог в него входить (добавьте `x`).
3. Запишите в `~/exp/answer.txt` одну строку вида `before=<режим до> after=<режим после>` (из `stat -c %a`).
""",
    hints=["Для доступа к файлу по пути нужен бит `x` на каждом каталоге пути (право «входа»).", "`stat -c %a ~/exp/vault` покажет режим до и после `chmod u+x`."],
    checks=[
        ("dir_has_x", "У каталога появился бит x для владельца", "Каталог доступен для входа", "У каталога vault должен быть бит x для владельца"),
        ("answer", "answer.txt: режимы до и после", "Режимы зафиксированы", "В answer.txt должно быть before=644 и after=<текущий режим каталога>"),
        ("access_works", "Файл читается", "Файл внутри каталога читается", "note.txt всё ещё недоступен"),
    ],
    setup=r"""
mkdir -p ~/exp/vault
echo note > ~/exp/vault/note.txt
chmod 644 ~/exp/vault/note.txt
chmod 644 ~/exp/vault
""",
    exercise=r"""
mkdir -p ~/.ex
cat ~/exp/vault/note.txt > ~/.ex/cat.out 2>&1
true
""",
    validate=r"""
V=/home/student/exp/vault
chk dir_has_x '[ $(( 0$(stat -c %a $V) & 0100 )) -ne 0 ]'
chk answer 'grep -q "before=644" /home/student/exp/answer.txt && grep -q "after=$(stat -c %a $V)" /home/student/exp/answer.txt'
chk access_works '[ "$(cat /home/student/.ex/cat.out)" = note ]'
""",
    solution=r"""
v=~/exp/vault
before=$(stat -c %a $v)
chmod u+x $v
after=$(stat -c %a $v)
echo "before=$before after=$after" > ~/exp/answer.txt
""",
    wrong="echo 'before=644 after=644' > ~/exp/answer.txt\n",
)

lab(
    id="ld-027", title="Инцидент: «Permission denied» у исполняемого скрипта",
    description="Скрипт исполняемый, но не запускается. Найдите настоящую причину (права, путь или noexec) и исправьте только её.",
    skills=["ls -l", "mount", "noexec", "диагностика запуска"],
    objectives=["Отличить причины Permission denied", "Не применять chmod -R наугад"],
    task="""\
**Инцидент.** `/tmp/job/run.sh` имеет права `755`, но при запуске даёт `Permission denied`.

Выясните причину (`ls -l`, `mount | grep ' /tmp '`) и исправьте **только действительный источник** проблемы: после исправления `~/jobs/run.sh` должен запускаться и печатать `job done`.

Права файлов в `/tmp/job` менять нельзя (в частности, `chmod -R` — ошибка).
""",
    hints=["`mount | grep ' /tmp '` покажет опции монтирования: `noexec` запрещает запуск программ с этого раздела.", "Запускаемый скрипт нужно держать на разделе без `noexec`, например скопировать в `~/jobs`."],
    checks=[
        ("job_runs", "~/jobs/run.sh запускается", "Скрипт запускается и печатает job done", "~/jobs/run.sh не запускается или не печатает job done"),
        ("tmp_untouched", "Права в /tmp/job не тронуты", "Права в /tmp/job не менялись", "Права файлов в /tmp/job изменены (chmod -R — не решение)"),
    ],
    setup=r"""
mkdir -p /tmp/job
printf '#!/bin/bash\necho "job done"\n' > /tmp/job/run.sh
chmod 755 /tmp/job/run.sh
echo data > /tmp/job/data.txt; chmod 644 /tmp/job/data.txt
""",
    exercise=r"""
mkdir -p ~/.ex
~/jobs/run.sh > ~/.ex/out 2>&1
true
""",
    validate=r"""
chk job_runs '[ "$(cat /home/student/.ex/out)" = "job done" ]'
chk tmp_untouched '[ "$(stat -c %a /tmp/job/data.txt)" = 644 ] && { [ ! -e /tmp/job/run.sh ] || [ "$(stat -c %a /tmp/job/run.sh)" = 755 ]; }'
""",
    solution="mkdir -p ~/jobs && cp /tmp/job/run.sh ~/jobs/ && ~/jobs/run.sh\n",
    wrong="chmod -R 777 /tmp/job\n",
)

# ------------------------------------------------------------------------------------- Процессы
lab(
    id="ld-033", title="PID по сокету, а не по имени",
    description="Среди одинаково называющихся процессов найдите тот, который слушает заданный порт.",
    skills=["ss -ltnp", "pgrep -f", "/proc"],
    objectives=["Найти процесс по порту", "Не выбрать одноимённый процесс"],
    task="""\
Запущены три одинаковых по имени сервиса `python3 svc.py` на портах 9101, 9102 и 9103 (loopback).

Найдите PID процесса, который **слушает порт 9102**, и запишите его в `~/pid.txt`. Процессы не завершайте.
""",
    hints=["`ss -ltnp` показывает порты и PID процессов.", "Отфильтруйте нужный порт: `ss -ltnp | grep 9102`; PID — в `pid=...`."],
    checks=[
        ("right_pid", "pid.txt: PID сервиса на порту 9102", "PID определён верно", "В pid.txt не PID процесса, слушающего порт 9102"),
        ("all_alive", "Все три сервиса работают", "Сервисы не затронуты", "Один из сервисов остановлен — завершать процессы не нужно"),
    ],
    setup=r"""
mkdir -p ~/srv
cat > ~/srv/svc.py <<'EOT'
import socket, sys, time
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", int(sys.argv[1])))
s.listen(5)
while True:
    time.sleep(60)
EOT
for p in 9101 9102 9103; do setsid nohup python3 ~/srv/svc.py $p >/dev/null 2>&1 </dev/null & done
sleep 1
""",
    validate=r"""
want=$(pgrep -f 'svc.py 9102' | head -n 1)
chk right_pid '[ -n "$want" ] && [ "$(tr -d "[:space:]" < /home/student/pid.txt)" = "$want" ]'
chk all_alive 'pgrep -f "svc.py 9101" && pgrep -f "svc.py 9102" && pgrep -f "svc.py 9103"'
""",
    solution="ss -ltnp | grep ':9102 ' | grep -o 'pid=[0-9]*' | cut -d= -f2 > ~/pid.txt\n",
    wrong="pgrep python3 | head -n 1 > ~/pid.txt\n",
)

lab(
    id="ld-034", title="Штатное завершение фонового процесса",
    description="Завершите процесс сигналом SIGTERM и убедитесь, что он корректно освободил ресурсы.",
    skills=["kill", "pkill", "SIGTERM", "проверка после завершения"],
    objectives=["Применить штатный сигнал", "Проверить результат завершения"],
    task="""\
Фоновый `holder.py` держит открытым файл `~/run/data.lock` и при штатном завершении пишет `clean exit` в `~/run/exit.log`.

Завершите его **штатным сигналом SIGTERM** (не `kill -9`) и убедитесь, что процесса не осталось.
""",
    hints=["`pkill -TERM -f holder.py` или `kill $(pgrep -f holder.py)` — по умолчанию `kill` шлёт SIGTERM.", "`kill -9` не даёт процессу выполнить обработчик и записать `clean exit`."],
    checks=[
        ("process_gone", "Процесса holder.py нет", "Процесс завершён", "holder.py всё ещё работает"),
        ("clean_exit", "Процесс завершился штатно", "Процесс завершился штатно", "В exit.log нет clean exit: процесс был убит без обработки SIGTERM"),
    ],
    setup=r"""
mkdir -p ~/run
cat > ~/run/holder.py <<'EOT'
import os, signal, sys, time
fd = open(os.path.expanduser("~/run/data.lock"), "w")
def bye(*_):
    with open(os.path.expanduser("~/run/exit.log"), "w") as f:
        f.write("clean exit\n")
    sys.exit(0)
signal.signal(signal.SIGTERM, bye)
while True:
    time.sleep(1)
EOT
setsid nohup python3 ~/run/holder.py >/dev/null 2>&1 </dev/null &
sleep 0.5
""",
    validate=r"""
chk process_gone '! pgrep -f "run/holder.py"'
chk clean_exit 'grep -qx "clean exit" /home/student/run/exit.log'
""",
    solution="pkill -TERM -f run/holder.py; sleep 0.7\n",
    wrong="pkill -9 -f run/holder.py; sleep 0.3\n",
)

# ------------------------------------------------------------------------------------ Bash и Python
lab(
    id="ld-129", title="Скрипт архивации: аргументы, коды выхода, справка",
    description="Напишите скрипт с проверкой аргументов, справкой и предсказуемыми кодами завершения.",
    skills=["bash", "$#", "exit-коды", "tar", "usage"],
    objectives=["Обработать -h и неверные вызовы", "Сообщить об ошибке кодом возврата"],
    task="""\
Напишите `~/bin/arch.sh`:

- `arch.sh -h` — печатает справку со словом `Usage` в stdout, код `0`;
- без аргументов — справка в **stderr**, код `2`;
- `arch.sh ИСТОЧНИК АРХИВ.tar.gz` — создаёт архив каталога-источника, код `0`;
- если источника нет — сообщение в stderr, код `1`, архив **не создаётся**.
""",
    hints=["Проверьте `$#` и `$1` в начале скрипта.", "`tar czf \"$dest\" -C \"$src\" .` создаёт архив содержимого каталога."],
    checks=[
        ("help_ok", "-h: Usage и код 0", "Справка работает", "arch.sh -h должен печатать Usage и возвращать 0"),
        ("no_args", "Без аргументов: код 2 и Usage в stderr", "Вызов без аргументов обработан", "Без аргументов нужен код 2 и справка в stderr"),
        ("archive_made", "Архив создан, код 0", "Архив создан", "Корректный вызов должен создать валидный архив и вернуть 0"),
        ("missing_src", "Нет источника: код 1, архива нет", "Ошибка источника обработана", "Для несуществующего источника нужен код 1 и отсутствие архива"),
    ],
    setup="mkdir -p ~/bin\n",
    exercise=r"""
mkdir -p ~/.ex/src; echo data > ~/.ex/src/f.txt
rm -f ~/.ex/out.tar.gz ~/.ex/x.tar.gz
if [ -f ~/bin/arch.sh ]; then
  timeout 8 bash ~/bin/arch.sh -h > ~/.ex/h.out 2> ~/.ex/h.err < /dev/null; echo $? > ~/.ex/h.rc
  timeout 8 bash ~/bin/arch.sh > ~/.ex/n.out 2> ~/.ex/n.err < /dev/null; echo $? > ~/.ex/n.rc
  timeout 8 bash ~/bin/arch.sh ~/.ex/src ~/.ex/out.tar.gz > ~/.ex/ok.out 2> ~/.ex/ok.err < /dev/null; echo $? > ~/.ex/ok.rc
  timeout 8 bash ~/bin/arch.sh ~/.ex/nosuch ~/.ex/x.tar.gz > ~/.ex/m.out 2> ~/.ex/m.err < /dev/null; echo $? > ~/.ex/m.rc
fi
true
""",
    validate=r"""
E=/home/student/.ex
chk help_ok '[ "$(cat $E/h.rc)" = 0 ] && grep -q Usage $E/h.out'
chk no_args '[ "$(cat $E/n.rc)" = 2 ] && grep -q Usage $E/n.err'
chk archive_made '[ "$(cat $E/ok.rc)" = 0 ] && gzip -t $E/out.tar.gz && tar tzf $E/out.tar.gz | grep -q f.txt'
chk missing_src '[ "$(cat $E/m.rc)" = 1 ] && [ ! -e $E/x.tar.gz ]'
""",
    solution=r"""
cat > ~/bin/arch.sh <<'EOT'
#!/bin/bash
usage() { echo "Usage: arch.sh SRC_DIR DEST.tar.gz"; }
if [ "$1" = "-h" ]; then usage; exit 0; fi
if [ $# -ne 2 ]; then usage >&2; exit 2; fi
src="$1"; dest="$2"
if [ ! -d "$src" ]; then echo "error: no such directory: $src" >&2; exit 1; fi
tar czf "$dest" -C "$src" .
EOT
""",
    wrong="printf '#!/bin/bash\\necho ok\\nexit 0\\n' > ~/bin/arch.sh\n",
)

# --------------------------------------------------------------------------------- Память и CPU
lab(
    id="ld-081", title="Доступная память: free, /proc/meminfo и cgroup",
    description="Сравните то, что показывают free и /proc/meminfo, с реальным лимитом cgroup, и объясните доступную память процесса.",
    skills=["free", "/proc/meminfo", "cgroup memory.max", "page cache"],
    objectives=["Найти фактический предел контейнера", "Не путать cache с «потерянной» RAM"],
    task="""\
Процесс в контейнере ограничен cgroup, а `free` показывает память всего хоста.

Создайте `~/mem.txt` с тремя строками:

1. `limit_bytes=<значение лимита памяти из cgroup>` (файл `/sys/fs/cgroup/memory.max`);
2. `memtotal_kb=<MemTotal из /proc/meminfo>`;
3. `note=<1–2 фразы>`: почему `MemTotal` не равен лимиту процесса и при чём тут cache.
""",
    hints=["`cat /sys/fs/cgroup/memory.max` — предел контейнера; `grep MemTotal /proc/meminfo` — память хоста.", "Page cache учитывается как used, но возвращается системе при нехватке памяти — это не «утечка»."],
    checks=[
        ("limit", "limit_bytes: лимит cgroup", "Лимит cgroup указан верно", "limit_bytes должен совпадать с /sys/fs/cgroup/memory.max"),
        ("memtotal", "memtotal_kb: MemTotal", "MemTotal указан верно", "memtotal_kb должен совпадать с MemTotal из /proc/meminfo"),
        ("note", "note: объяснение про cache", "Объяснение содержит cache", "В note нужно объяснение, упоминающее cache (кэш)"),
    ],
    setup="true\n",
    validate=r"""
lim=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
tot=$(awk '/MemTotal/{print $2}' /proc/meminfo)
chk limit '[ "$(grep ^limit_bytes= /home/student/mem.txt | cut -d= -f2)" = "$lim" ]'
chk memtotal '[ "$(grep ^memtotal_kb= /home/student/mem.txt | cut -d= -f2)" = "$tot" ]'
chk note 'grep ^note= /home/student/mem.txt | grep -qiE "cache|кэш|кеш"'
""",
    solution=r"""
lim=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
{ echo "limit_bytes=$lim"; echo "memtotal_kb=$(awk '/MemTotal/{print $2}' /proc/meminfo)"; echo "note=MemTotal — память хоста, а предел процесса задаёт cgroup; page cache входит в used, но освобождается при нехватке"; } > ~/mem.txt
""",
    wrong=r"""
{ echo "limit_bytes=$(awk '/MemTotal/{print $2}' /proc/meminfo)"; echo "memtotal_kb=1"; echo "note=память потерялась"; } > ~/mem.txt
""",
)

# --------------------------------------------------------------------------- Backup и восстановление
lab(
    id="ld-169", title="Архив с правами и проверка восстановления",
    description="Сделайте архив, сохраняющий права, восстановите его в чистый каталог и сверьте содержимое и метаданные.",
    skills=["tar -p", "sha256sum", "diff -r", "восстановление"],
    objectives=["Сохранить права и ссылки", "Проверить восстановление", "Зафиксировать контрольную сумму"],
    task="""\
В `~/data` лежат файлы с разными правами (`a.sh` — 755, `secret.txt` — 600, `shared.txt` — 664) и ссылка `latest`.

1. Создайте `~/backup.tar.gz` с каталогом `data` (права должны сохраниться).
2. Запишите контрольную сумму архива (`sha256sum`) в `~/backup.sha256`.
3. Восстановите архив в **чистый** каталог `~/restore` — права, содержимое и ссылка должны совпасть с оригиналом.
""",
    hints=["Для сохранения прав при распаковке пользователю нужен ключ `-p`: `tar xzpf`.", "Сравнить деревья: `diff -r ~/data ~/restore/data`, права — `stat -c '%a %n'`."],
    checks=[
        ("archive", "backup.tar.gz валиден", "Архив создан", "~/backup.tar.gz отсутствует или повреждён"),
        ("checksum", "backup.sha256 соответствует архиву", "Контрольная сумма верна", "В backup.sha256 нет верной SHA-256 архива"),
        ("perms", "Права после восстановления совпали", "Права сохранены", "Права в ~/restore/data отличаются от ~/data"),
        ("content", "Содержимое и ссылка совпали", "Содержимое и ссылка совпали", "Содержимое или символическая ссылка отличаются от оригинала"),
    ],
    setup=r"""
mkdir -p ~/data ~/restore
printf '#!/bin/bash\necho a\n' > ~/data/a.sh; chmod 755 ~/data/a.sh
echo secret > ~/data/secret.txt; chmod 600 ~/data/secret.txt
echo shared > ~/data/shared.txt; chmod 664 ~/data/shared.txt
ln -s shared.txt ~/data/latest
touch -d '2020-01-02 03:04:05' ~/data/a.sh ~/data/secret.txt ~/data/shared.txt
""",
    exercise=r"""
mkdir -p ~/.ex
diff -r ~/data ~/restore/data > /dev/null 2>&1; echo $? > ~/.ex/diff.rc
true
""",
    validate=r"""
H=/home/student
chk archive 'gzip -t $H/backup.tar.gz && tar tzf $H/backup.tar.gz | grep -q "data/secret.txt"'
chk checksum 'grep -q "$(sha256sum $H/backup.tar.gz | cut -d" " -f1)" $H/backup.sha256'
chk perms '[ "$(stat -c %a $H/restore/data/a.sh)" = 755 ] && [ "$(stat -c %a $H/restore/data/secret.txt)" = 600 ] && [ "$(stat -c %a $H/restore/data/shared.txt)" = 664 ]'
chk content '[ "$(cat $H/.ex/diff.rc)" = 0 ] && [ -L $H/restore/data/latest ] && [ "$(readlink $H/restore/data/latest)" = shared.txt ]'
""",
    solution=r"""
cd ~ && tar czpf backup.tar.gz data && sha256sum backup.tar.gz > backup.sha256 && tar xzpf backup.tar.gz -C ~/restore
""",
    wrong=r"""
cd ~ && tar czf backup.tar.gz data && sha256sum backup.tar.gz > backup.sha256 && tar xzf backup.tar.gz -C ~/restore
""",
)
