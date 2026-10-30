"""Данные лабораторий Module A — Linux Basics (linux-002 … linux-008). Генерируются в content/labs/*."""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append(kw)


lab(
    id="linux-002", module="linux-basics", mode="learn", difficulty="beginner", minutes=10, xp=50,
    title="Создание и удаление файлов",
    description="Создавайте каталоги и файлы, копируйте, переименовывайте и удаляйте: mkdir, touch, cp, mv, rm.",
    skills=["mkdir", "touch", "cp", "mv", "rm"],
    objectives=["Создать каталог и пустой файл", "Скопировать и переименовать файлы", "Удалить файлы по маске"],
    task="""\
В каталоге `~/workspace` лежат рабочие файлы.

1. Создайте каталог `~/workspace/project` и в нём **пустой** файл `todo.txt`.
2. Скопируйте `~/workspace/keep.txt` в `~/workspace/project/keep_backup.txt` (оригинал должен остаться на месте).
3. Удалите все файлы `*.log` в `~/workspace`.
4. Переименуйте `~/workspace/old_notes.txt` в `notes.txt`.
""",
    hints=[
        "`mkdir` создаёт каталог, `touch` — пустой файл.",
        "`cp источник приёмник` копирует, `mv` переименовывает, `rm *.log` удаляет по маске.",
    ],
    checks=[
        ("project_todo", "Создан project/todo.txt (пустой)", "Каталог и пустой todo.txt созданы", "Нет каталога ~/workspace/project или пустого файла todo.txt"),
        ("backup_copy", "Сделана копия keep.txt", "Копия создана, оригинал на месте", "Копия keep_backup.txt отсутствует или оригинал keep.txt потерян"),
        ("logs_removed", "Удалены *.log", "Логи удалены", "В ~/workspace остались файлы *.log"),
        ("renamed", "old_notes.txt переименован в notes.txt", "Файл переименован", "Файл notes.txt не найден или остался old_notes.txt"),
    ],
    setup=r"""
mkdir -p ~/workspace
echo "important data" > ~/workspace/keep.txt
echo "draft" > ~/workspace/old_notes.txt
echo "log one" > ~/workspace/tmp1.log
echo "log two" > ~/workspace/tmp2.log
""",
    validate=r"""
W=/home/student/workspace
chk project_todo '[ -d $W/project ] && [ -f $W/project/todo.txt ] && [ ! -s $W/project/todo.txt ]'
chk backup_copy '[ "$(cat $W/keep.txt)" = "important data" ] && [ "$(cat $W/project/keep_backup.txt)" = "important data" ]'
chk logs_removed '[ ! -e $W/tmp1.log ] && [ ! -e $W/tmp2.log ] && [ -f $W/keep.txt ]'
chk renamed '[ "$(cat $W/notes.txt)" = draft ] && [ ! -e $W/old_notes.txt ]'
""",
    solution=r"""
cd ~/workspace && mkdir project && touch project/todo.txt && cp keep.txt project/keep_backup.txt && rm *.log && mv old_notes.txt notes.txt
""",
    wrong=r"""
mkdir ~/workspace/project; touch ~/workspace/project/todo.txt; rm ~/workspace/keep.txt
""",
)

lab(
    id="linux-003", module="linux-basics", mode="learn", difficulty="beginner", minutes=10, xp=50,
    title="Просмотр файлов и потоков",
    description="Читайте файлы по частям и перенаправляйте вывод: head, tail, wc, cat, оператор >.",
    skills=["head", "tail", "wc", "cat", "перенаправление >"],
    objectives=["Прочитать начало и конец файла", "Посчитать строки", "Сохранить вывод команды в файл"],
    task="""\
В `~/data` лежат `server.log` (100 строк) и `names.txt`.

1. Сохраните **последние 5 строк** `server.log` в `~/data/last5.txt`.
2. Сохраните **первые 3 строки** `names.txt` в `~/data/first3.txt`.
3. Запишите **количество строк** `server.log` в `~/data/count.txt`.
""",
    hints=["`tail -n 5 файл` и `head -n 3 файл` показывают конец и начало.", "Результат команды можно сохранить так: `команда > файл`. Для подсчёта строк — `wc -l`."],
    checks=[
        ("last5", "last5.txt содержит последние 5 строк", "Последние 5 строк сохранены", "В last5.txt не последние 5 строк server.log"),
        ("first3", "first3.txt содержит первые 3 строки", "Первые 3 строки сохранены", "В first3.txt не первые 3 строки names.txt"),
        ("count", "count.txt содержит число строк", "Число строк указано верно", "В count.txt неверное количество строк"),
    ],
    setup=r"""
mkdir -p ~/data
seq -f 'event %g ok' 1 100 > ~/data/server.log
printf 'alice\nbob\ncarol\ndave\nerin\n' > ~/data/names.txt
""",
    validate=r"""
D=/home/student/data
chk last5 '[ "$(cat $D/last5.txt)" = "$(seq -f "event %g ok" 96 100)" ]'
chk first3 '[ "$(cat $D/first3.txt)" = "$(printf "alice\nbob\ncarol")" ]'
chk count 'grep -qE "^[[:space:]]*100([[:space:]]|$)" $D/count.txt'
""",
    solution=r"""
cd ~/data && tail -n 5 server.log > last5.txt && head -n 3 names.txt > first3.txt && wc -l < server.log > count.txt
""",
    wrong=r"""
cd ~/data && head -n 5 server.log > last5.txt && tail -n 3 names.txt > first3.txt && echo 99 > count.txt
""",
    alt={"alt_wc_name": r"""
cd ~/data && tail -n5 server.log >last5.txt && sed -n '1,3p' names.txt >first3.txt && wc -l server.log > count.txt
"""},
)

lab(
    id="linux-004", module="linux-basics", mode="practice", difficulty="junior", minutes=15, xp=100,
    title="Поиск файлов через find",
    description="Найдите нужные файлы по имени и размеру и наведите порядок в дереве проекта командой find.",
    skills=["find", "-name", "-type", "-empty"],
    objectives=["Найти файлы по маске имени", "Найти и удалить пустые файлы", "Не задеть остальные файлы"],
    task="""\
В `~/projects` лежит дерево проекта.

1. Найдите все файлы с расширением `.conf` (именно `*.conf`) и запишите их **абсолютные пути**, по одному на строку, в `~/found_conf.txt`.
2. Удалите все **пустые** файлы внутри `~/projects`. Остальные файлы (включая `old.conf.bak`) должны остаться.
""",
    hints=["`find ~/projects -name '*.conf'` ищет по маске; если путь начать с `~/`, результаты будут абсолютными.", "Пустые файлы: `-type f -empty`; у `find` есть действие `-delete`."],
    checks=[
        ("found_conf", "found_conf.txt содержит все *.conf", "Список файлов верный", "В ~/found_conf.txt не тот список *.conf (нужны абсолютные пути, без лишних файлов)"),
        ("empty_removed", "Пустые файлы удалены", "Пустые файлы удалены", "Пустые файлы всё ещё на месте"),
        ("others_intact", "Остальные файлы не затронуты", "Остальные файлы на месте", "Удалены или повреждены непустые файлы"),
    ],
    setup=r"""
mkdir -p ~/projects/web/conf ~/projects/api/conf ~/projects/docs ~/projects/tmp
echo a > ~/projects/web/conf/nginx.conf
echo b > ~/projects/api/conf/app.conf
echo c > ~/projects/api/settings.conf
echo old > ~/projects/web/old.conf.bak
echo d > ~/projects/docs/guide.md
: > ~/projects/tmp/empty1.tmp
: > ~/projects/docs/empty2.txt
echo x > ~/projects/tmp/cache.tmp
""",
    validate=r"""
P=/home/student/projects
exp=$(printf '%s\n' $P/web/conf/nginx.conf $P/api/conf/app.conf $P/api/settings.conf | sort)
chk found_conf '[ -f /home/student/found_conf.txt ] && [ "$(sort /home/student/found_conf.txt)" = "$exp" ]'
chk empty_removed '[ ! -e $P/tmp/empty1.tmp ] && [ ! -e $P/docs/empty2.txt ]'
chk others_intact '[ -f $P/tmp/cache.tmp ] && [ -f $P/docs/guide.md ] && [ -f $P/web/old.conf.bak ] && [ -s $P/web/conf/nginx.conf ] && [ -s $P/api/conf/app.conf ] && [ -s $P/api/settings.conf ]'
""",
    solution=r"""
find ~/projects -name '*.conf' > ~/found_conf.txt
find ~/projects -type f -empty -delete
""",
    wrong=r"""
find ~/projects -name '*.conf*' > ~/found_conf.txt
rm -rf ~/projects/tmp
""",
    alt={"alt_exec": r"""
find ~/projects -type f -name '*.conf' -print | sort > ~/found_conf.txt
find ~/projects -type f -size 0 -exec rm {} \;
"""},
)

lab(
    id="linux-005", module="linux-basics", mode="practice", difficulty="junior", minutes=15, xp=100,
    title="Поиск в логах через grep",
    description="Разберите лог приложения: отфильтруйте ошибки, посчитайте предупреждения и найдите самый «шумный» IP.",
    skills=["grep", "sort", "uniq", "cut", "pipes"],
    objectives=["Отфильтровать строки по уровню", "Посчитать совпадения", "Найти самый частый IP среди ошибок"],
    writable_dirs=["/var/log/app"],
    task="""\
Лог приложения лежит в `/var/log/app/app.log`.

1. Все строки уровня `ERROR` сохраните в `~/errors.txt`.
2. Определите IP-адрес клиента (`client=…`), который чаще всего встречается **среди ERROR-строк**, и запишите только адрес в `~/top_ip.txt`.
3. Количество строк уровня `WARN` запишите числом в `~/warn_count.txt`.
""",
    hints=["Изучите `/var/log/app/app.log` через `less` или `head`; `grep ERROR файл` выбирает нужные строки.", "Чтобы найти самый частый адрес: `grep -o 'client=[0-9.]*'`, затем `sort | uniq -c | sort -rn`.", "Счётчик строк у grep — ключ `-c`."],
    checks=[
        ("errors_file", "errors.txt содержит все ERROR-строки", "ERROR-строки выбраны верно", "В ~/errors.txt не все ERROR-строки или есть лишние"),
        ("top_ip", "top_ip.txt содержит самый частый IP", "IP определён верно", "В ~/top_ip.txt не тот адрес"),
        ("warn_count", "warn_count.txt содержит число WARN", "Число WARN верное", "В ~/warn_count.txt неверное число"),
    ],
    setup=r"""
gen() {
  i=1
  while [ $i -le 120 ]; do
    if [ $((i%6)) -eq 0 ]; then
      lvl=ERROR
      if [ $((i%18)) -eq 0 ]; then ip=10.0.0.9; else ip=10.0.0.2; fi
    elif [ $((i%6)) -eq 3 ]; then lvl=WARN; ip=10.0.1.$((i%3+1))
    else lvl=INFO; ip=10.0.2.$((i%5+1)); fi
    printf '2026-10-30 10:%02d:%02d %s client=%s msg="request %d"\n' $((i/60)) $((i%60)) $lvl $ip $i
    i=$((i+1))
  done
}
gen > /var/log/app/app.log
""",
    validate=r"""
gen() {
  i=1
  while [ $i -le 120 ]; do
    if [ $((i%6)) -eq 0 ]; then
      lvl=ERROR
      if [ $((i%18)) -eq 0 ]; then ip=10.0.0.9; else ip=10.0.0.2; fi
    elif [ $((i%6)) -eq 3 ]; then lvl=WARN; ip=10.0.1.$((i%3+1))
    else lvl=INFO; ip=10.0.2.$((i%5+1)); fi
    printf '2026-10-30 10:%02d:%02d %s client=%s msg="request %d"\n' $((i/60)) $((i%60)) $lvl $ip $i
    i=$((i+1))
  done
}
H=/home/student
chk errors_file '[ "$(sort $H/errors.txt)" = "$(gen | grep " ERROR " | sort)" ]'
chk top_ip '[ "$(tr -d "[:space:]" < $H/top_ip.txt)" = 10.0.0.2 ]'
chk warn_count '[ "$(tr -d "[:space:]" < $H/warn_count.txt)" = "$(gen | grep -c " WARN ")" ]'
""",
    solution=r"""
L=/var/log/app/app.log
grep ERROR $L > ~/errors.txt
grep ERROR $L | grep -o 'client=[0-9.]*' | cut -d= -f2 | sort | uniq -c | sort -rn | head -1 | awk '{print $2}' > ~/top_ip.txt
grep -c WARN $L > ~/warn_count.txt
""",
    wrong=r"""
grep WARN /var/log/app/app.log > ~/errors.txt
echo 10.0.0.9 > ~/top_ip.txt
echo 5 > ~/warn_count.txt
""",
    alt={"alt_awk": r"""
awk '$3=="ERROR"' /var/log/app/app.log > ~/errors.txt
awk '$3=="ERROR"{split($4,a,"="); c[a[2]]++} END{for(k in c) print c[k], k}' /var/log/app/app.log | sort -rn | head -1 | cut -d' ' -f2 > ~/top_ip.txt
awk '$3=="WARN"{n++} END{print n}' /var/log/app/app.log > ~/warn_count.txt
"""},
)

lab(
    id="linux-006", module="linux-basics", mode="practice", difficulty="junior", minutes=15, xp=100,
    title="Pipes и перенаправление вывода",
    description="Соединяйте команды конвейером и управляйте потоками stdout/stderr: |, >, >>, 2>.",
    skills=["|", ">", ">>", "2>", "sort -u", "cut"],
    objectives=["Построить конвейер из нескольких команд", "Дописывать в файл, не затирая его", "Перенаправить поток ошибок"],
    task="""\
В `~/data/access.log` строки вида `IP МЕТОД ПУТЬ СТАТУС`.

1. Сохраните **уникальные IP**, отсортированные по возрастанию, в `~/ips.txt` (по одному на строку).
2. Запишите количество запросов со статусом `404` в `~/count404.txt`.
3. **Допишите** в конец `~/data/report.txt` строку `done` (существующая строка `start` должна сохраниться).
4. Выполните `ls /nonexistent` так, чтобы **сообщение об ошибке** попало в файл `~/err.txt`.
""",
    hints=["`cut -d' ' -f1 access.log | sort -u` — уникальные IP.", "`>>` дописывает в конец файла, `>` перезаписывает.", "Поток ошибок — дескриптор 2: `команда 2> файл`."],
    checks=[
        ("ips_unique", "ips.txt: уникальные отсортированные IP", "Список IP верный", "В ~/ips.txt не тот список уникальных IP"),
        ("count404", "count404.txt: число запросов 404", "Число 404 верное", "В ~/count404.txt неверное число"),
        ("appended", "report.txt: start + done", "Строка дописана, start сохранена", "В report.txt должно быть ровно: start и затем done"),
        ("stderr_redirect", "err.txt содержит сообщение об ошибке ls", "stderr перенаправлен", "В ~/err.txt нет сообщения об ошибке ls"),
    ],
    setup=r"""
mkdir -p ~/data
i=1
while [ $i -le 60 ]; do
  if [ $((i%5)) -eq 0 ]; then st=404; elif [ $((i%11)) -eq 0 ]; then st=500; else st=200; fi
  echo "192.168.1.$((i%7+1)) GET /p$((i%4)) $st"
  i=$((i+1))
done > ~/data/access.log
printf 'start\n' > ~/data/report.txt
""",
    validate=r"""
H=/home/student
chk ips_unique '[ "$(cat $H/ips.txt)" = "$(printf "192.168.1.%s\n" 1 2 3 4 5 6 7)" ]'
chk count404 '[ "$(tr -d "[:space:]" < $H/count404.txt)" = 12 ]'
chk appended '[ "$(cat $H/data/report.txt)" = "$(printf "start\ndone")" ]'
chk stderr_redirect 'grep -q "No such file or directory" $H/err.txt'
""",
    solution=r"""
cd ~/data
cut -d' ' -f1 access.log | sort -u > ~/ips.txt
grep -c ' 404$' access.log > ~/count404.txt
echo done >> report.txt
ls /nonexistent 2> ~/err.txt
true
""",
    wrong=r"""
cut -d' ' -f1 ~/data/access.log | sort > ~/ips.txt
grep -c 404 ~/data/access.log > ~/count404.txt
echo done > ~/data/report.txt
ls /nonexistent > ~/err.txt
true
""",
)

lab(
    id="linux-007", module="linux-basics", mode="practice", difficulty="junior", minutes=15, xp=100,
    title="Архивирование и tar",
    description="Упакуйте каталог в сжатый архив и восстановите файлы из резервной копии: tar czf / xzf.",
    skills=["tar", "gzip", "czf", "xzf", "-C"],
    objectives=["Создать архив tar.gz", "Распаковать архив в нужный каталог", "Проверить содержимое архива"],
    task="""\
1. Упакуйте каталог `~/site` в архив **tar.gz**: `~/site.tar.gz` (внутри должны быть файлы сайта вместе с подкаталогами).
2. В домашнем каталоге лежит резервная копия `~/backup.tar.gz`. Распакуйте её в каталог `~/restore`.
""",
    hints=["Создание: `tar czf архив.tar.gz каталог`. Просмотр содержимого: `tar tzf архив.tar.gz`.", "Распаковка в нужную папку: `tar xzf архив -C папка`."],
    checks=[
        ("site_archive", "site.tar.gz — валидный архив сайта", "Архив сайта создан верно", "~/site.tar.gz отсутствует, не сжат gzip или не содержит файлы сайта"),
        ("restored", "Файлы из backup.tar.gz лежат в ~/restore", "Резервная копия восстановлена", "В ~/restore нет a.txt и b.txt с ожидаемым содержимым"),
        ("site_untouched", "Исходный каталог site цел", "Исходный каталог на месте", "Каталог ~/site повреждён"),
    ],
    setup=r"""
mkdir -p ~/site/css ~/site/img ~/restore
echo "<h1>Hello</h1>" > ~/site/index.html
echo "body{margin:0}" > ~/site/css/style.css
echo "LOGO" > ~/site/img/logo.txt
mkdir -p ~/.stage && echo alpha > ~/.stage/a.txt && echo beta > ~/.stage/b.txt
tar czf ~/backup.tar.gz -C ~/.stage a.txt b.txt && rm -rf ~/.stage
""",
    validate=r"""
H=/home/student
chk site_archive 'gzip -t $H/site.tar.gz && L=$(tar tzf $H/site.tar.gz) && echo "$L" | grep -q "index.html" && echo "$L" | grep -q "css/style.css" && echo "$L" | grep -q "img/logo.txt"'
chk restored '[ "$(cat $H/restore/a.txt)" = alpha ] && [ "$(cat $H/restore/b.txt)" = beta ]'
chk site_untouched '[ "$(cat $H/site/index.html)" = "<h1>Hello</h1>" ] && [ -f $H/site/css/style.css ]'
""",
    solution=r"""
tar czf ~/site.tar.gz -C ~ site && tar xzf ~/backup.tar.gz -C ~/restore
""",
    wrong=r"""
cd ~ && tar cf ~/site.tar.gz site && tar xzf ~/backup.tar.gz
""",
    alt={"alt_cd": r"""
cd ~/site && tar -czvf ../site.tar.gz . && cd ~/restore && tar -xzf ../backup.tar.gz
"""},
)

lab(
    id="linux-008", module="linux-basics", mode="practice", difficulty="junior", minutes=20, xp=100,
    title="Текстовые фильтры awk и sed",
    description="Обработайте CSV и конфиг без текстового редактора: awk для вычислений и выборки, sed для замены.",
    skills=["awk", "sed", "sed -i", "разделитель полей"],
    objectives=["Просуммировать столбец по условию", "Заменить значение в файле на месте", "Вывести отдельный столбец"],
    task="""\
В `~/data` лежат `employees.csv` (`name,dept,salary`, есть строка заголовка) и `config.ini`.

1. Посчитайте сумму зарплат сотрудников отдела `dev` и запишите число в `~/dev_total.txt`.
2. В `~/data/config.ini` замените `debug=true` на `debug=false` **в самом файле** (остальные строки не менять).
3. Сохраните имена сотрудников (первый столбец, **без** заголовка) в `~/names.txt`, по одному на строку.
""",
    hints=["`awk -F, '$2==\"dev\" {s+=$3} END {print s}' файл`.", "`sed -i 's/что/на что/' файл` правит файл на месте.", "Пропустить заголовок в awk: условие `NR>1`."],
    checks=[
        ("dev_total", "dev_total.txt: сумма зарплат dev", "Сумма посчитана верно", "В ~/dev_total.txt неверная сумма"),
        ("config_fixed", "config.ini: debug=false", "Конфиг исправлен, остальное не тронуто", "config.ini должен отличаться от исходного только строкой debug=false"),
        ("names", "names.txt: имена без заголовка", "Список имён верный", "В ~/names.txt не тот список имён"),
    ],
    setup=r"""
mkdir -p ~/data
printf 'name,dept,salary\nAnna,dev,5000\nBoris,ops,4000\nClara,dev,6000\nDenis,hr,3500\nElena,dev,7000\nFedor,ops,4500\n' > ~/data/employees.csv
printf 'debug=true\nport=8080\nname=demo\n' > ~/data/config.ini
""",
    validate=r"""
H=/home/student
chk dev_total '[ "$(tr -d "[:space:]" < $H/dev_total.txt)" = 18000 ]'
chk config_fixed '[ "$(cat $H/data/config.ini)" = "$(printf "debug=false\nport=8080\nname=demo")" ]'
chk names '[ "$(cat $H/names.txt)" = "$(printf "Anna\nBoris\nClara\nDenis\nElena\nFedor")" ]'
""",
    solution=r"""
awk -F, '$2=="dev"{s+=$3} END{print s}' ~/data/employees.csv > ~/dev_total.txt
sed -i 's/debug=true/debug=false/' ~/data/config.ini
awk -F, 'NR>1{print $1}' ~/data/employees.csv > ~/names.txt
""",
    wrong=r"""
awk -F, 'NR>1{s+=$3} END{print s}' ~/data/employees.csv > ~/dev_total.txt
sed 's/debug=true/debug=false/' ~/data/config.ini > /dev/null
cut -d, -f1 ~/data/employees.csv > ~/names.txt
""",
)
