"""Данные новых лабораторий программы, часть A: этап 1 «Новичок» (NB-001 … NB-012)."""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append(kw)


lab(
    id="nb-001", title="Командная строка и текущий каталог",
    description="Узнайте, в каком каталоге вы находитесь сразу после открытия терминала, и запишите абсолютный путь.",
    skills=["pwd", "перенаправление >"],
    objectives=["Определить текущий каталог", "Записать результат команды в файл"],
    task="""\
Вы только что открыли терминал.

1. Узнайте **текущий каталог** (абсолютный путь).
2. Запишите этот путь в файл `~/answer.txt`.
""",
    hints=["Команда `pwd` печатает абсолютный путь текущего каталога.", "Вывод в файл: `pwd > ~/answer.txt`."],
    checks=[("answer", "answer.txt: текущий каталог", "Путь записан верно", "В ~/answer.txt должен быть абсолютный путь каталога, в котором вы находитесь")],
    setup="true\n",
    validate=r"""
chk answer '[ "$(tr -d "\n" < /home/student/answer.txt)" = /home/student ]'
""",
    solution="pwd > ~/answer.txt\n",
    wrong="echo /tmp > ~/answer.txt\n",
)

lab(
    id="nb-002", title="Просмотр каталога: обычные и скрытые записи",
    description="Разделите содержимое каталога на обычные и скрытые записи и сохраните имена в два файла.",
    skills=["ls", "ls -A", "скрытые файлы"],
    objectives=["Увидеть скрытые записи", "Разделить списки без лишних элементов"],
    task="""\
В каталоге `~/tree` есть обычные и скрытые (начинаются с точки) записи.

1. Имена **обычных** записей сохраните в `~/visible.txt`, по одному на строку.
2. Имена **скрытых** записей — в `~/hidden.txt` (без `.` и `..`).
""",
    hints=["`ls` не показывает скрытые записи, `ls -A` показывает их (без `.` и `..`).", "Отфильтровать скрытые можно по первому символу: `grep '^\\.'`."],
    checks=[
        ("visible", "visible.txt: обычные записи", "Список обычных записей верный", "В visible.txt должны быть ровно обычные записи ~/tree"),
        ("hidden", "hidden.txt: скрытые записи", "Список скрытых записей верный", "В hidden.txt должны быть ровно скрытые записи ~/tree"),
    ],
    setup=r"""
mkdir -p ~/tree/docs
echo a > ~/tree/a.txt; echo b > ~/tree/b.txt; echo n > ~/tree/notes.md
echo e > ~/tree/.env; echo s > ~/tree/.secret; mkdir -p ~/tree/.cache
""",
    validate=r"""
H=/home/student
chk visible '[ "$(sort $H/visible.txt)" = "$(printf "a.txt\nb.txt\ndocs\nnotes.md")" ]'
chk hidden '[ "$(sort $H/hidden.txt)" = "$(printf ".cache\n.env\n.secret")" ]'
""",
    solution=r"""
cd ~/tree && ls > ~/visible.txt && ls -A | grep '^\.' > ~/hidden.txt
""",
    wrong=r"""
cd ~/tree && ls -a > ~/visible.txt && ls -a > ~/hidden.txt
""",
)

lab(
    id="nb-003", title="Переход между каталогами",
    description="Перейдите в глубоко вложенный каталог, затем к его родителю и зафиксируйте оба пути.",
    skills=["cd", "cd ..", "pwd"],
    objectives=["Перейти в каталог по пути", "Подняться к родителю", "Не изменить проект"],
    task="""\
Проект лежит в `~/project`.

1. Перейдите в `~/project/src/app/core` и запишите абсолютный путь в `~/paths/core.txt`.
2. Поднимитесь на уровень выше (`cd ..`) и запишите новый путь в `~/paths/parent.txt`.

Файлы проекта менять не нужно.
""",
    hints=["`cd путь` переходит, `cd ..` поднимается к родителю.", "После каждого перехода выполняйте `pwd > файл`."],
    checks=[
        ("core", "core.txt: путь вложенного каталога", "Путь вложенного каталога верный", "В paths/core.txt должен быть путь ~/project/src/app/core"),
        ("parent", "parent.txt: путь родителя", "Путь родителя верный", "В paths/parent.txt должен быть путь ~/project/src/app"),
        ("project_intact", "Проект не изменён", "Проект на месте", "Файлы проекта изменены или удалены"),
    ],
    setup=r"""
mkdir -p ~/project/src/app/core ~/paths
echo "print(1)" > ~/project/src/app/core/main.py
echo "# demo" > ~/project/README.md
""",
    validate=r"""
H=/home/student
chk core '[ "$(tr -d "\n" < $H/paths/core.txt)" = $H/project/src/app/core ]'
chk parent '[ "$(tr -d "\n" < $H/paths/parent.txt)" = $H/project/src/app ]'
chk project_intact '[ "$(cat $H/project/src/app/core/main.py)" = "print(1)" ] && [ "$(cat $H/project/README.md)" = "# demo" ]'
""",
    solution=r"""
cd ~/project/src/app/core && pwd > ~/paths/core.txt && cd .. && pwd > ~/paths/parent.txt
""",
    wrong=r"""
cd ~/project/src/app/core && pwd > ~/paths/core.txt && cd ../.. && pwd > ~/paths/parent.txt
""",
)

lab(
    id="nb-004", title="Абсолютные и относительные пути",
    description="Опишите один и тот же файл двумя способами: абсолютным и относительным путём из рабочего каталога.",
    skills=["абсолютный путь", "относительный путь", "pwd"],
    objectives=["Составить абсолютный путь", "Составить относительный путь", "Убедиться, что оба ведут к одному файлу"],
    task="""\
Рабочий каталог — `~/work`; в нём лежит `data/report.txt`.

Запишите в `~/work/paths.txt` **две строки**: на первой — абсолютный путь к `report.txt`, на второй — относительный путь к нему **из каталога `~/work`**.
""",
    hints=["Абсолютный путь начинается с `/`.", "Относительный путь не начинается с `/` и считается от рабочего каталога: `data/report.txt`."],
    checks=[
        ("absolute", "Первая строка — абсолютный путь", "Абсолютный путь верный", "Первая строка должна быть абсолютным путём к report.txt"),
        ("relative", "Вторая строка — относительный путь", "Относительный путь верный", "Вторая строка должна быть относительным путём (из ~/work) к тому же файлу"),
    ],
    setup=r"""
mkdir -p ~/work/data
echo "Q3 report" > ~/work/data/report.txt
""",
    validate=r"""
W=/home/student/work
l1=$(sed -n 1p $W/paths.txt); l2=$(sed -n 2p $W/paths.txt)
chk absolute '[ "$l1" = $W/data/report.txt ]'
chk relative 'cd $W && case "$l2" in /*|"") exit 1;; esac && [ "$(stat -c %i "$l2")" = "$(stat -c %i $W/data/report.txt)" ]'
""",
    solution=r"""
printf '%s\n%s\n' /home/student/work/data/report.txt data/report.txt > ~/work/paths.txt
""",
    wrong=r"""
printf '%s\n%s\n' /home/student/work/data/report.txt /home/student/work/data/report.txt > ~/work/paths.txt
""",
)

lab(
    id="nb-005", title="Справка: man и --help",
    description="Найдите в справке нужную опцию ls и подтвердите её реальным вызовом.",
    skills=["--help", "ls -S", "чтение справки"],
    objectives=["Найти опцию в справке", "Описать её смысл", "Применить опцию"],
    task="""\
В `~/files` лежат файлы разного размера.

1. Через справку (`ls --help`) найдите опцию, которая **сортирует по размеру** (самые большие первыми).
2. Создайте `~/option.txt` с названием опции и кратким смыслом (в тексте должны быть сама опция и слово `size` или `размер`).
3. Подтвердите находку: сохраните вывод `ls` с этой опцией для `~/files` в `~/sorted.txt`.
""",
    hints=["`ls --help | less` или `ls --help | grep -i size`.", "Нужная опция — одна буква, например `-S`."],
    checks=[
        ("option_named", "option.txt: опция и смысл", "Опция и смысл указаны", "В option.txt нужны опция -S и слово size/размер"),
        ("sorted_by_size", "sorted.txt: файлы по убыванию размера", "Результат подтверждён вызовом", "В sorted.txt файлы не отсортированы по убыванию размера"),
    ],
    setup=r"""
mkdir -p ~/files
head -c 10 /dev/zero > ~/files/tiny.dat
head -c 300 /dev/zero > ~/files/mid.dat
head -c 50 /dev/zero > ~/files/small.dat
head -c 1000 /dev/zero > ~/files/big.dat
""",
    validate=r"""
H=/home/student
chk option_named 'grep -q -- "-S" $H/option.txt && grep -qiE "size|размер" $H/option.txt'
chk sorted_by_size '[ "$(cat $H/sorted.txt)" = "$(printf "big.dat\nmid.dat\nsmall.dat\ntiny.dat")" ]'
""",
    solution=r"""
ls --help | grep -- '-S' > /dev/null
echo "-S : сортировка по размеру (size), крупные первыми" > ~/option.txt
ls -S ~/files > ~/sorted.txt
""",
    wrong=r"""
echo "-t : по времени" > ~/option.txt
ls -t ~/files > ~/sorted.txt
""",
)

lab(
    id="nb-006", title="Создание каталогов",
    description="Создайте дерево каталогов одной командой, не трогая соседние данные.",
    skills=["mkdir -p"],
    objectives=["Создать вложенный путь без ручного создания каждого уровня", "Сохранить существующие данные"],
    task="""\
В `~/practice` уже есть данные. Создайте дерево `~/practice/project/docs` **одной командой**.

Существующие файлы (`~/practice/keep.txt`, `~/practice/project/old.txt`) должны остаться на месте.
""",
    hints=["У `mkdir` есть опция `-p`: создаёт все недостающие уровни и не ругается, если каталог уже есть."],
    checks=[
        ("tree", "Создан ~/practice/project/docs", "Дерево создано", "Каталог ~/practice/project/docs не найден"),
        ("data_intact", "Соседние данные сохранены", "Данные сохранены", "Файлы keep.txt и project/old.txt удалены или изменены"),
    ],
    setup=r"""
mkdir -p ~/practice/project
echo keep > ~/practice/keep.txt
echo old > ~/practice/project/old.txt
""",
    validate=r"""
P=/home/student/practice
chk tree '[ -d $P/project/docs ]'
chk data_intact '[ "$(cat $P/keep.txt)" = keep ] && [ "$(cat $P/project/old.txt)" = old ]'
""",
    solution="mkdir -p ~/practice/project/docs\n",
    wrong="rm -rf ~/practice && mkdir -p ~/practice/project/docs\n",
)

lab(
    id="nb-007", title="Создание и чтение файла",
    description="Создайте пустой файл и файл с заданной строкой, затем прочитайте оба.",
    skills=["touch", "echo", "cat"],
    objectives=["Отличить пустой файл от отсутствующего", "Записать точную строку"],
    task="""\
В каталоге `~/notes`:

1. Создайте **пустой** файл `notes.txt`.
2. Создайте файл `message.txt` со строкой `Hello, Linux!`.
3. Прочитайте оба файла (`cat`, `ls -l`) и убедитесь, что размеры — 0 и 14 байт.
""",
    hints=["`touch notes.txt` создаёт пустой файл.", "`echo 'Hello, Linux!' > message.txt` создаёт файл со строкой."],
    checks=[
        ("empty_file", "notes.txt пуст", "notes.txt существует и пуст", "notes.txt должен существовать и быть пустым"),
        ("message", "message.txt: Hello, Linux!", "message.txt содержит нужную строку", "message.txt должен содержать ровно строку Hello, Linux!"),
    ],
    setup="mkdir -p ~/notes\n",
    validate=r"""
N=/home/student/notes
chk empty_file '[ -f $N/notes.txt ] && [ ! -s $N/notes.txt ]'
chk message '[ "$(cat $N/message.txt)" = "Hello, Linux!" ]'
""",
    solution="cd ~/notes && touch notes.txt && echo 'Hello, Linux!' > message.txt && cat notes.txt message.txt\n",
    wrong="cd ~/notes && echo 'hello' > notes.txt && echo 'Hello Linux' > message.txt\n",
)

lab(
    id="nb-008", title="Копирование и переименование",
    description="Скопируйте один файл и переименуйте другой, проверяя дерево после каждого шага.",
    skills=["cp", "mv", "ls"],
    objectives=["Отличить копирование от переименования", "Сохранить исходник при копировании"],
    task="""\
В `~/files` лежат `report.txt` и `draft.txt`.

1. Скопируйте `report.txt` в каталог `~/backup` (оригинал остаётся).
2. Переименуйте `draft.txt` в `final.txt`.
""",
    hints=["`cp источник приёмник` копирует, оригинал остаётся.", "`mv старое новое` переименовывает: старого имени больше нет."],
    checks=[
        ("copied", "Копия report.txt в ~/backup, оригинал на месте", "Копия создана, оригинал на месте", "Нужна копия в ~/backup и оригинал в ~/files"),
        ("renamed", "draft.txt переименован в final.txt", "Файл переименован", "final.txt отсутствует или остался draft.txt"),
    ],
    setup=r"""
mkdir -p ~/files ~/backup
echo "Q3" > ~/files/report.txt
echo "v1" > ~/files/draft.txt
""",
    validate=r"""
H=/home/student
chk copied '[ "$(cat $H/backup/report.txt)" = Q3 ] && [ "$(cat $H/files/report.txt)" = Q3 ]'
chk renamed '[ "$(cat $H/files/final.txt)" = v1 ] && [ ! -e $H/files/draft.txt ]'
""",
    solution="cd ~/files && cp report.txt ~/backup/ && mv draft.txt final.txt\n",
    wrong="cd ~/files && mv report.txt ~/backup/ && cp draft.txt final.txt\n",
)

lab(
    id="nb-009", title="Безопасное удаление",
    description="Удалите только временные .log, сохранив контрольные файлы.",
    skills=["rm", "маски *.log", "ls перед rm"],
    objectives=["Проверить, что выберет маска", "Удалить ровно разрешённые файлы"],
    task="""\
В `~/logs` лежат файлы разных типов.

Удалите **только файлы `*.log`**. Остальные (в том числе `c.log.bak`, `keep.txt`, `readme.md`) должны остаться.

Совет: сначала выполните `ls *.log`, чтобы увидеть, что выберет маска.
""",
    hints=["`ls *.log` покажет, какие имена подойдут под маску, прежде чем удалять.", "Маска `*.log` не совпадает с `c.log.bak` — имя должно заканчиваться на `.log`."],
    checks=[
        ("logs_removed", "*.log удалены", "Логи удалены", "В ~/logs остались файлы *.log"),
        ("others_kept", "Остальные файлы на месте", "Остальные файлы сохранены", "Удалены файлы, которые удалять было нельзя"),
    ],
    setup=r"""
mkdir -p ~/logs && cd ~/logs
echo 1 > a.log; echo 2 > b.log; echo 3 > c.log; echo bak > c.log.bak; echo k > keep.txt; echo r > readme.md
""",
    validate=r"""
L=/home/student/logs
chk logs_removed '[ ! -e $L/a.log ] && [ ! -e $L/b.log ] && [ ! -e $L/c.log ]'
chk others_kept '[ -f $L/c.log.bak ] && [ -f $L/keep.txt ] && [ -f $L/readme.md ]'
""",
    solution="cd ~/logs && ls *.log && rm *.log\n",
    wrong="cd ~/logs && rm -f *log*\n",
)

lab(
    id="nb-010", title="Начало, конец и размер файла",
    description="Выделите первые и последние строки журнала и посчитайте число строк.",
    skills=["head", "tail", "wc -l"],
    objectives=["Получить первые 5 строк", "Получить последние 5 строк", "Посчитать строки"],
    task="""\
В `~/data/app.log` — журнал из 40 строк.

1. Первые 5 строк сохраните в `~/head5.txt`.
2. Последние 5 строк — в `~/tail5.txt`.
3. Число строк (только число) — в `~/lines.txt`.
""",
    hints=["`head -n 5` и `tail -n 5`.", "`wc -l < файл` печатает только число строк."],
    checks=[
        ("head5", "head5.txt: первые 5 строк", "Начало журнала верное", "В head5.txt не первые 5 строк"),
        ("tail5", "tail5.txt: последние 5 строк", "Конец журнала верный", "В tail5.txt не последние 5 строк"),
        ("lines", "lines.txt: 40", "Число строк верное", "В lines.txt неверное число строк"),
    ],
    setup=r"""
mkdir -p ~/data
seq -f 'event %g ok' 1 40 > ~/data/app.log
""",
    validate=r"""
H=/home/student
chk head5 '[ "$(cat $H/head5.txt)" = "$(seq -f "event %g ok" 1 5)" ]'
chk tail5 '[ "$(cat $H/tail5.txt)" = "$(seq -f "event %g ok" 36 40)" ]'
chk lines 'grep -qE "^[[:space:]]*40([[:space:]]|$)" $H/lines.txt'
""",
    solution="cd ~/data && head -n 5 app.log > ~/head5.txt && tail -n 5 app.log > ~/tail5.txt && wc -l < app.log > ~/lines.txt\n",
    wrong="cd ~/data && tail -n 5 app.log > ~/head5.txt && head -n 5 app.log > ~/tail5.txt && echo 39 > ~/lines.txt\n",
)

lab(
    id="nb-011", title="Перенаправление вывода",
    description="Соберите отчёт из вывода двух команд, не потеряв первую запись.",
    skills=[">", ">>", "hostname"],
    objectives=["Отличить > от >>", "Сохранить порядок записей"],
    task="""\
Создайте `~/report.txt` из вывода двух команд **в таком порядке**:

1. `echo "Report: begin"`
2. `hostname`

Первая запись не должна пропасть.
""",
    hints=["`>` перезаписывает файл, `>>` дописывает в конец.", "Первую команду пишите через `>`, вторую — через `>>`."],
    checks=[("report", "report.txt: две строки по порядку", "Отчёт собран верно", "В report.txt должны быть строки «Report: begin» и имя хоста — именно в таком порядке")],
    setup="true\n",
    validate=r"""
chk report '[ "$(cat /home/student/report.txt)" = "$(printf "Report: begin\nupskill")" ]'
""",
    solution='echo "Report: begin" > ~/report.txt && hostname >> ~/report.txt\n',
    wrong='echo "Report: begin" > ~/report.txt && hostname > ~/report.txt\n',
)

lab(
    id="nb-012", title="Код завершения и простая диагностика",
    description="Выполните успешную и ошибочную команду, запишите коды завершения и объясните причину ошибки.",
    skills=["$?", "коды завершения", "ls"],
    objectives=["Прочитать код последней команды", "Объяснить причину ошибки"],
    task="""\
1. Выполните `ls ~/lab` (успешно) и сразу запишите код завершения (`$?`).
2. Выполните `ls ~/lab/missing` (ошибка) и запишите её код.
3. Запишите в `~/codes.txt` две строки: `ok=<код первой команды>` и `fail=<код второй>`.
4. В `~/why.txt` объясните причину ошибки одной фразой (должно быть понятно, что файла не существует).
""",
    hints=["Статус последней команды хранится в `$?`: `echo $?`.", "Сообщение ls об ошибке содержит фразу «No such file or directory»."],
    checks=[
        ("codes", "codes.txt: ok=0 и fail=2", "Коды верные", "В codes.txt должны быть строки ok=0 и fail=2"),
        ("why", "why.txt: причина ошибки", "Причина объяснена", "В why.txt должно быть сказано, что файла не существует (No such file / не существует)"),
    ],
    setup="mkdir -p ~/lab\n",
    validate=r"""
H=/home/student
chk codes '[ "$(sed -n 1p $H/codes.txt)" = ok=0 ] && [ "$(sed -n 2p $H/codes.txt)" = fail=2 ]'
chk why 'grep -qiE "no such file|не существует|нет такого" $H/why.txt'
""",
    solution=r"""
ls ~/lab > /dev/null; echo "ok=$?" > ~/codes.txt
ls ~/lab/missing 2> /dev/null; echo "fail=$?" >> ~/codes.txt
echo "No such file or directory: файл не существует" > ~/why.txt
""",
    wrong=r"""
echo "ok=0" > ~/codes.txt; echo "fail=1" >> ~/codes.txt; echo "не знаю" > ~/why.txt
""",
)
