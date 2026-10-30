"""Данные новых лабораторий программы, часть C: этапы 3–4 («Мидл», «Синьор») — то, что безопасно выполняется в контейнере."""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append(kw)


# ------------------------------------------------------------------ Терминал, shell и окружение
lab(
    id="ld-007", title="Безопасная функция перехода в каталог по имени",
    description="Напишите функцию оболочки, корректно работающую с именами, содержащими пробелы, `*` и ведущий дефис.",
    skills=["кавычки", "cd --", "функции bash", "globbing"],
    objectives=["Не допустить разбиения по пробелам и раскрытия масок", "Обработать имя с дефисом"],
    task="""\
В `~/dirs` лежат каталоги с «неудобными» именами: `my dir`, `a*b`, `-dash`, `plain` (и похожие ловушки: `aXb`).

Напишите в `~/lib/safe.sh` функцию `godir ИМЯ`, которая переходит в `~/dirs/ИМЯ`. Для любого из этих имён она должна попадать **ровно в нужный каталог** (без раскрытия `*`, без разбиения по пробелу).

Проверка выполнит `source ~/lib/safe.sh; godir "<имя>"; pwd` для каждого имени.
""",
    hints=["Переменные и подстановки всегда берите в двойные кавычки: `\"$1\"`.", "`cd -- \"$HOME/dirs/$1\"`: двойное тире защищает от имён, похожих на опции."],
    checks=[
        ("function_defined", "Функция godir определена в ~/lib/safe.sh", "Функция определена", "В ~/lib/safe.sh должна быть функция godir"),
        ("all_names_safe", "Все четыре имени обрабатываются верно", "Все имена обработаны верно", "godir ломается на пробелах, * или ведущем дефисе"),
    ],
    setup=r"""
mkdir -p ~/dirs ~/lib
mkdir -p ~/dirs/'my dir' ~/dirs/'a*b' ~/dirs/-dash ~/dirs/plain ~/dirs/aXb ~/dirs/my ~/dirs/dir
""",
    exercise=r"""
mkdir -p ~/.ex; rm -f ~/.ex/g1 ~/.ex/g2 ~/.ex/g3 ~/.ex/g4
[ -f ~/lib/safe.sh ] || exit 0
i=0
for name in "my dir" 'a*b' '-dash' 'plain'; do
  i=$((i+1))
  timeout 5 bash -c 'source ~/lib/safe.sh; godir "$1"; pwd' _ "$name" > ~/.ex/g$i 2>&1 < /dev/null
done
true
""",
    validate=r"""
E=/home/student/.ex; D=/home/student/dirs
chk function_defined 'grep -q "godir" /home/student/lib/safe.sh'
chk all_names_safe '[ "$(cat $E/g1)" = "$D/my dir" ] && [ "$(cat $E/g2)" = "$D/a*b" ] && [ "$(cat $E/g3)" = "$D/-dash" ] && [ "$(cat $E/g4)" = "$D/plain" ]'
""",
    solution=r"""
cat > ~/lib/safe.sh <<'EOT'
godir() {
  cd -- "$HOME/dirs/$1"
}
EOT
""",
    wrong=r"""
cat > ~/lib/safe.sh <<'EOT'
godir() {
  cd $HOME/dirs/$1
}
EOT
""",
)

lab(
    id="ld-008", title="Инцидент: «успешный» отчёт при ошибке в начале конвейера",
    description="Скрипт возвращает 0, хотя первый этап конвейера упал. Настройте обработку ошибок, чтобы сбой был виден.",
    skills=["pipefail", "set -o", "коды завершения", "конвейеры"],
    objectives=["Увидеть, почему статус конвейера — это статус последней команды", "Сделать сбой видимым в коде выхода и в отчёте"],
    task="""\
**Инцидент.** `~/bin/report.sh` сортирует `~/in/input.txt` в `~/out/sorted.txt` и пишет `status: OK` в `~/out/status.txt`. Когда входной файл пропадает, скрипт всё равно говорит «OK» и возвращает `0`.

Исправьте `~/bin/report.sh`:

- при сбое любого этапа конвейера — **ненулевой код выхода** и `status: FAILED` в `status.txt`;
- при успехе — код `0` и `status: OK`.
""",
    hints=["Код конвейера по умолчанию — код последней команды; `set -o pipefail` берёт первый ненулевой код.", "Проверьте результат через `if конвейер; then ... else ... fi`."],
    checks=[
        ("fails_loudly", "Сбой: код ≠ 0 и status: FAILED", "Сбой виден в коде и отчёте", "При пропавшем input.txt скрипт должен вернуть ненулевой код и записать status: FAILED"),
        ("success_ok", "Успех: код 0 и status: OK", "Успешный путь не сломан", "При наличии input.txt нужен код 0, status: OK и отсортированный результат"),
    ],
    setup=r"""
mkdir -p ~/bin ~/in ~/out
printf 'b\na\nc\n' > ~/in/input.txt
cat > ~/bin/report.sh <<'EOT'
#!/bin/bash
mkdir -p ~/out
cat ~/in/input.txt | sort > ~/out/sorted.txt
echo "status: OK" > ~/out/status.txt
EOT
chmod +x ~/bin/report.sh
""",
    exercise=r"""
mkdir -p ~/.ex; rm -f ~/.ex/rc1 ~/.ex/rc2 ~/.ex/st1 ~/.ex/st2 ~/out/status.txt ~/out/sorted.txt
mv ~/in/input.txt ~/in/input.hold
timeout 8 bash ~/bin/report.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc1; cp ~/out/status.txt ~/.ex/st1 2>/dev/null
mv ~/in/input.hold ~/in/input.txt
rm -f ~/out/status.txt ~/out/sorted.txt
timeout 8 bash ~/bin/report.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc2; cp ~/out/status.txt ~/.ex/st2 2>/dev/null
true
""",
    validate=r"""
E=/home/student/.ex
chk fails_loudly '[ "$(cat $E/rc1)" != 0 ] && grep -q FAILED $E/st1'
chk success_ok '[ "$(cat $E/rc2)" = 0 ] && grep -q "status: OK" $E/st2 && [ "$(cat /home/student/out/sorted.txt)" = "$(printf "a\nb\nc")" ]'
""",
    solution=r"""
cat > ~/bin/report.sh <<'EOT'
#!/bin/bash
set -o pipefail
mkdir -p ~/out
if cat ~/in/input.txt | sort > ~/out/sorted.txt; then
  echo "status: OK" > ~/out/status.txt
else
  echo "status: FAILED" > ~/out/status.txt
  exit 1
fi
EOT
""",
    wrong="true\n",
)

# ---------------------------------------------------------------------------- Файлы и каталоги
lab(
    id="ld-020", title="Копирование дерева с сохранением метаданных",
    description="Скопируйте дерево, сохранив времена, права и символические ссылки, и сравните источник с копией.",
    skills=["cp -a", "stat", "find -printf", "tar-конвейер"],
    objectives=["Сохранить mtime, права и ссылки", "Сравнить не только байты"],
    task="""\
В `~/src` лежит дерево: файлы с разными правами и временами, символическая ссылка и пустой каталог.

Создайте точную копию в `~/dst` так, чтобы совпали **содержимое, права, времена изменения и символические ссылки** (без разыменования).
""",
    hints=["У `cp` есть режим архива `-a`, он сохраняет права, времена и ссылки.", "Сравнить метаданные: `find . -printf '%p %m %T@ %l\\n' | sort` в обоих каталогах."],
    checks=[
        ("metadata", "Права, времена и ссылки совпадают", "Метаданные совпали", "Права, времена изменения или ссылки в ~/dst отличаются от ~/src"),
        ("content", "Содержимое совпадает", "Содержимое совпало", "Содержимое файлов отличается"),
    ],
    setup=r"""
mkdir -p ~/src/bin ~/src/conf ~/src/empty
printf '#!/bin/bash\necho hi\n' > ~/src/bin/run.sh; chmod 755 ~/src/bin/run.sh
echo "key=1" > ~/src/conf/app.conf; chmod 664 ~/src/conf/app.conf
echo "note" > ~/src/notes.txt; chmod 600 ~/src/notes.txt
ln -s conf/app.conf ~/src/current
touch -d '2021-03-04 05:06:07' ~/src/bin/run.sh ~/src/conf/app.conf ~/src/notes.txt
touch -d '2021-03-04 05:06:07' ~/src/bin ~/src/conf ~/src/empty
""",
    exercise=r"""
mkdir -p ~/.ex
diff -r ~/src ~/dst > /dev/null 2>&1; echo $? > ~/.ex/diff.rc
true
""",
    validate=r"""
H=/home/student
meta() { (cd "$1" && find . -printf '%p %m %T@ %y %l\n' | sort); }
chk metadata '[ -d $H/dst ] && [ "$(meta $H/src)" = "$(meta $H/dst)" ]'
chk content '[ "$(cat $H/.ex/diff.rc)" = 0 ]'
""",
    solution="cp -a ~/src ~/dst\n",
    wrong="cp -r ~/src ~/dst\n",
)

lab(
    id="ld-021", title="Контрольные суммы SHA-256 и обнаружение подмены",
    description="Посчитайте SHA-256 для набора артефактов и найдите среди «полученных» файл, изменённый при передаче.",
    skills=["sha256sum", "sha256sum -c", "целостность"],
    objectives=["Составить файл контрольных сумм", "Проверить полученные файлы", "Найти изменённый артефакт"],
    task="""\
Каталог `~/release` содержит артефакты `*.bin`, а `~/received` — их копии после «передачи» (один файл изменился).

1. Создайте `~/release/SHA256SUMS` с суммами всех `*.bin` из `~/release` (формат `sha256sum`).
2. Проверьте `~/received` по этому файлу и запишите **имена повреждённых** артефактов (по одному на строку) в `~/bad.txt`.
""",
    hints=["`cd ~/release && sha256sum *.bin > SHA256SUMS`.", "`cd ~/received && sha256sum -c ~/release/SHA256SUMS` помечает несовпадения как FAILED."],
    checks=[
        ("sums_file", "SHA256SUMS содержит верные суммы", "Файл сумм верный", "~/release/SHA256SUMS отсутствует или суммы неверны"),
        ("bad_found", "bad.txt: повреждённый артефакт", "Повреждённый файл найден", "В bad.txt должен быть ровно тот артефакт, который изменился"),
    ],
    setup=r"""
mkdir -p ~/release ~/received
printf 'alpha-artifact\n' > ~/release/a.bin
printf 'beta-artifact\n' > ~/release/b.bin
printf 'gamma-artifact\n' > ~/release/c.bin
cp ~/release/*.bin ~/received/
echo tampered >> ~/received/b.bin
""",
    validate=r"""
R=/home/student/release
chk sums_file '[ "$(sort $R/SHA256SUMS)" = "$(cd $R && sha256sum a.bin b.bin c.bin | sort)" ]'
chk bad_found '[ "$(sort /home/student/bad.txt)" = b.bin ]'
""",
    solution=r"""
cd ~/release && sha256sum *.bin > SHA256SUMS
cd ~/received && sha256sum -c ~/release/SHA256SUMS 2>/dev/null | grep FAILED | cut -d: -f1 > ~/bad.txt
true
""",
    wrong=r"""
cd ~/release && sha256sum a.bin > SHA256SUMS
echo a.bin > ~/bad.txt
""",
)

lab(
    id="ld-022", title="Инцидент: файл удалён, а место не освободилось",
    description="Удалённый файл держит открытый дескриптор процесса. Найдите виновника и освободите место, не уронив сервис.",
    skills=["df", "du", "/proc/PID/fd", "сигналы"],
    objectives=["Объяснить расхождение du и df", "Найти удалённый, но открытый inode", "Освободить место без остановки сервиса"],
    task="""\
**Инцидент.** В `~/spool` удалили огромный `big.log`, но `df -h ~` по-прежнему показывает занятое место. Сервис `~/spool/holder.py` должен продолжать работать: он пишет `~/spool/app.log`.

Найдите процесс с открытым удалённым файлом (`ls -l /proc/PID/fd | grep deleted`) и освободите место **без остановки сервиса**. Сервис перечитывает/закрывает лишние дескрипторы по сигналу `SIGUSR1`.

Нужно, чтобы свободного места стало больше 40 МБ.
""",
    hints=["`du` считает видимые файлы, а `df` — занятые блоки; удалённый, но открытый файл занимает место, пока его держит процесс.", "Освободить можно, заставив процесс закрыть дескриптор: `kill -USR1 PID`."],
    checks=[
        ("space_freed", "Свободно больше 40 МБ", "Место освобождено", "Свободного места всё ещё меньше 40 МБ"),
        ("service_alive", "Сервис holder.py работает", "Сервис продолжает работать", "Процесс holder.py остановлен — сервис терять нельзя"),
    ],
    setup=r"""
mkdir -p ~/spool
cat > ~/spool/holder.py <<'EOT'
import os, signal, time
base = os.path.expanduser("~/spool")
big = open(os.path.join(base, "big.log"), "wb")
big.write(b"x" * (20 * 1024 * 1024))
big.flush()
os.unlink(os.path.join(base, "big.log"))  # файл удалён, но дескриптор открыт
def reopen(*_):
    big.close()
signal.signal(signal.SIGUSR1, reopen)
log = open(os.path.join(base, "app.log"), "a")
while True:
    log.write("tick\n"); log.flush()
    time.sleep(1)
EOT
setsid nohup python3 ~/spool/holder.py >/dev/null 2>&1 </dev/null &
sleep 1.5
""",
    validate=r"""
chk space_freed '[ "$(df -k --output=avail /home/student | tail -n 1 | tr -d " ")" -gt 40960 ]'
chk service_alive 'pgrep -f "spool/holder.py" && [ -f /home/student/spool/app.log ]'
""",
    solution="kill -USR1 $(pgrep -f spool/holder.py); sleep 1\n",
    wrong="pkill -9 -f spool/holder.py; sleep 0.5\n",
)

lab(
    id="ld-023", title="Атомарная замена конфигурационного файла",
    description="Напишите скрипт, который заменяет конфиг так, чтобы читатель всегда видел либо старую, либо новую полную версию.",
    skills=["mktemp", "mv (rename)", "sync", "атомарность"],
    objectives=["Писать во временный файл в том же каталоге", "Заменять через rename", "Не допускать частичного файла"],
    task="""\
Напишите `~/bin/update_config.sh НОВЫЙ_ФАЙЛ`, которая заменяет `~/app/app.conf` содержимым `НОВЫЙ_ФАЙЛ` **атомарно**:

- сначала пишет полный временный файл **в том же каталоге**, что и `app.conf`;
- сбрасывает данные на диск (`sync`);
- затем подменяет файл переименованием (`mv`).

Проверка запустит скрипт на большом файле (≈3 МБ) и параллельно будет читать `app.conf`: любое чтение обязано дать либо старую, либо новую версию целиком.
""",
    hints=["`tmp=$(mktemp \"$(dirname \"$dst\")/.app.conf.XXXXXX\")`, потом `cp`, `sync` и `mv -f \"$tmp\" \"$dst\"`.", "Переименование в пределах одной файловой системы атомарно, запись «поверх» файла — нет."],
    checks=[
        ("uses_rename", "Скрипт подменяет файл через mv/rename", "Подмена через rename", "Скрипт должен подменять app.conf командой mv (rename) временного файла"),
        ("temp_in_same_dir", "Временный файл создаётся рядом с app.conf", "Временный файл в том же каталоге", "Временный файл должен создаваться в каталоге app.conf (mktemp с dirname или .tmp рядом)"),
        ("no_partial_reads", "Читатель не видел частичных версий", "Частичных чтений нет", "Во время обновления читатель увидел неполный app.conf"),
        ("final_content", "Итоговый файл — новая версия", "Новая версия на месте", "После обновления app.conf не совпадает с новым файлом"),
    ],
    setup=r"""
mkdir -p ~/app ~/bin
echo "version=1" > ~/app/app.conf
""",
    exercise=r"""
mkdir -p ~/.ex; rm -f ~/.ex/partial ~/.ex/final
python3 - <<'EOT'
import os
open(os.path.expanduser("~/.ex/new.conf"), "w").write("version=2\n" + "pad=" + "x" * 3000000 + "\n")
EOT
echo "version=1" > ~/app/app.conf
[ -f ~/bin/update_config.sh ] || exit 0
( sleep 0.05; timeout 10 bash ~/bin/update_config.sh ~/.ex/new.conf > /dev/null 2>&1 < /dev/null ) &
python3 - > ~/.ex/partial <<'EOT'
import os, time
new = open(os.path.expanduser("~/.ex/new.conf"), "rb").read()
old = b"version=1\n"
bad = 0
for _ in range(400):
    data = open(os.path.expanduser("~/app/app.conf"), "rb").read()
    if data != old and data != new:
        bad += 1
    time.sleep(0.003)
print(bad)
EOT
wait
sha256sum < ~/app/app.conf > ~/.ex/final
true
""",
    validate=r"""
H=/home/student; S=$H/bin/update_config.sh
chk uses_rename 'grep -Eq "(^|[[:space:];&|(])(mv|rename)[[:space:]]" $S'
chk temp_in_same_dir 'grep -Eq "dirname|mktemp|\.tmp|\.new" $S'
chk no_partial_reads '[ "$(cat $H/.ex/partial)" = 0 ]'
chk final_content '[ "$(cat $H/.ex/final)" = "$(sha256sum < $H/.ex/new.conf)" ]'
""",
    solution=r"""
cat > ~/bin/update_config.sh <<'EOT'
#!/bin/bash
set -e
new="$1"
dst="$HOME/app/app.conf"
tmp="$(mktemp "$(dirname "$dst")/.app.conf.XXXXXX")"
cp "$new" "$tmp"
chmod 644 "$tmp"
sync "$tmp" 2>/dev/null || sync
mv -f "$tmp" "$dst"
EOT
chmod +x ~/bin/update_config.sh
""",
    wrong=r"""
printf '#!/bin/bash\ncat "$1" > "$HOME/app/app.conf"\n' > ~/bin/update_config.sh
""",
)

# ------------------------------------------------------------------------- Потоки, текст и данные
lab(
    id="ld-012", title="Нулевой разделитель: странные имена файлов",
    description="Обработайте файлы с пробелами, переводами строки и ведущим дефисом так, чтобы ни один не потерялся.",
    skills=["find -print0", "xargs -0", "cp --", "имена файлов"],
    objectives=["Не полагаться на построчное чтение имён", "Не дать имени превратиться в опцию"],
    task="""\
В `~/files` лежат пять файлов с «опасными» именами (пробел, перевод строки в имени, ведущий дефис, имя `--help`).

Скопируйте **все** файлы в каталог `~/out` (плоско, имена сохранить). Ни один файл не должен потеряться и не должен быть воспринят как опция команды.
""",
    hints=["Список имён с нулевым разделителем: `find ... -print0`, читать его — `xargs -0`.", "Отделите опции от имён: `cp -- имя ~/out/` (`xargs -0 -I{} cp -- {} ~/out/`)."],
    checks=[
        ("names_preserved", "Все 5 имён сохранены", "Все имена сохранены", "В ~/out нет всех пяти файлов с исходными именами"),
        ("content_preserved", "Содержимое файлов сохранено", "Содержимое сохранено", "Содержимое скопированных файлов не совпадает"),
    ],
    setup=r"""
mkdir -p ~/files ~/out && cd ~/files
printf 'a b.txt' > 'a b.txt'
printf 'line\nbreak.txt' > "$(printf 'line\nbreak.txt')"
printf -- '-rf.txt' > ./-rf.txt
printf -- '--help' > ./--help
printf 'normal.txt' > normal.txt
""",
    validate=r"""
chk_files() { python3 - "$1" <<'EOT'
import os, sys
names = ["a b.txt", "line\nbreak.txt", "-rf.txt", "--help", "normal.txt"]
out = "/home/student/out"
have = set(os.listdir(out))
if sys.argv[1] == "names":
    print("OK" if have == set(names) else "BAD")
else:
    ok = all(os.path.isfile(os.path.join(out, n)) and open(os.path.join(out, n)).read() == n for n in names)
    print("OK" if ok else "BAD")
EOT
}
chk names_preserved '[ "$(chk_files names)" = OK ]'
chk content_preserved '[ "$(chk_files content)" = OK ]'
""",
    solution="cd ~/files && find . -type f -print0 | xargs -0 -I{} cp -- {} ~/out/\n",
    wrong="for f in $(find ~/files -type f); do cp $f ~/out/; done\n",
)

lab(
    id="ld-013", title="95-й перцентиль времени ответа по endpoint",
    description="Из JSON-логов посчитайте p95 времени ответа по каждому endpoint.",
    skills=["python3 json", "перцентили", "агрегация по ключу"],
    objectives=["Сгруппировать записи по endpoint", "Вычислить p95, а не максимум"],
    task="""\
В `~/data/resp.jsonl` — строки JSON вида `{"endpoint": "/a", "ms": 42}` (по 100 замеров на endpoint).

Запишите в `~/p95.json` JSON-объект `{"<endpoint>": <p95 в мс>, ...}`. Допустимо любое стандартное определение перцентиля (ближайший ранг или интерполяция), допуск ≈1 %.
""",
    hints=["Сгруппируйте значения по endpoint, отсортируйте и возьмите элемент с рангом ceil(0.95·N).", "Максимум и p95 — разные вещи: p95 отбрасывает 5 % самых медленных ответов."],
    checks=[("p95", "p95.json: верные p95", "Перцентили посчитаны верно", "Значения p95 в p95.json неверны (не путайте с максимумом)")],
    setup=r"""
mkdir -p ~/data
python3 - <<'EOT'
import json, os
rows = []
for i in range(1, 101):
    rows.append({"endpoint": "/a", "ms": (i * 37) % 100 + 1})
    rows.append({"endpoint": "/b", "ms": (i * 53) % 100 + 1})
    rows.append({"endpoint": "/c", "ms": ((i * 7) % 100 + 1) * 2})
with open(os.path.expanduser("~/data/resp.jsonl"), "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
EOT
""",
    validate=r"""
chk_p95() { python3 - <<'EOT'
import json, math
try:
    got = json.load(open("/home/student/p95.json"))
except Exception:
    print("BAD"); raise SystemExit
data = {}
for line in open("/home/student/data/resp.jsonl"):
    r = json.loads(line)
    data.setdefault(r["endpoint"], []).append(r["ms"])
ok = set(got) == set(data)
for ep, vals in data.items():
    vals.sort()
    exp = vals[math.ceil(0.95 * len(vals)) - 1]
    if ep in got and abs(float(got[ep]) - exp) > max(1.0, 0.01 * exp):
        ok = False
print("OK" if ok else "BAD")
EOT
}
chk p95 '[ "$(chk_p95)" = OK ]'
""",
    solution=r"""
python3 - <<'EOT'
import json, math
data = {}
for line in open("/home/student/data/resp.jsonl"):
    r = json.loads(line)
    data.setdefault(r["endpoint"], []).append(r["ms"])
out = {ep: sorted(v)[math.ceil(0.95 * len(v)) - 1] for ep, v in data.items()}
json.dump(out, open("/home/student/p95.json", "w"))
EOT
""",
    wrong=r"""
python3 - <<'EOT'
import json
data = {}
for line in open("/home/student/data/resp.jsonl"):
    r = json.loads(line)
    data.setdefault(r["endpoint"], []).append(r["ms"])
json.dump({ep: max(v) for ep, v in data.items()}, open("/home/student/p95.json", "w"))
EOT
""",
)

lab(
    id="ld-014", title="Инцидент: отчёт зависит от локали",
    description="Отчёт «плывёт» в зависимости от LC_ALL. Сделайте его воспроизводимым для обеих локалей.",
    skills=["LC_ALL", "locale", "awk length", "воспроизводимость"],
    objectives=["Понять, какие переменные влияют на вывод", "Зафиксировать локаль в скрипте"],
    task="""\
**Инцидент.** `~/bin/report.sh` строит отчёт (имя и длина имени в символах). Запущенный с `LC_ALL=C` и с `LC_ALL=C.UTF-8`, он выдаёт **разные байты** (для кириллицы длина считается то в байтах, то в символах).

Исправьте скрипт, чтобы его вывод был **побайтно одинаков** при обеих локалях (стабилизируйте окружение внутри скрипта).
""",
    hints=["Запустите скрипт двумя способами и сравните: `LC_ALL=C bash report.sh | md5sum` и `LC_ALL=C.UTF-8 bash report.sh | md5sum`.", "Зафиксируйте локаль первой строкой скрипта: `export LC_ALL=...`."],
    checks=[
        ("same_bytes", "Вывод одинаков при LC_ALL=C и C.UTF-8", "Вывод воспроизводим", "Вывод скрипта различается при разных локалях"),
        ("report_complete", "Отчёт не пуст (4 строки)", "Отчёт полный", "Отчёт должен содержать 4 строки"),
    ],
    setup=r"""
mkdir -p ~/bin ~/data ~/out
printf 'Ёлка\nÄrger\nplain\nZebra\n' > ~/data/names.txt
cat > ~/bin/report.sh <<'EOT'
#!/bin/bash
mkdir -p ~/out
awk '{ print $1, length($1) }' ~/data/names.txt | sort
EOT
chmod +x ~/bin/report.sh
""",
    exercise=r"""
mkdir -p ~/.ex; rm -f ~/.ex/r1 ~/.ex/r2
LC_ALL=C timeout 8 bash ~/bin/report.sh > ~/.ex/r1 2>/dev/null < /dev/null
LC_ALL=C.UTF-8 timeout 8 bash ~/bin/report.sh > ~/.ex/r2 2>/dev/null < /dev/null
true
""",
    validate=r"""
E=/home/student/.ex
chk same_bytes 'cmp -s $E/r1 $E/r2'
chk report_complete '[ "$(wc -l < $E/r1)" = 4 ]'
""",
    solution="sed -i '2i export LC_ALL=C.UTF-8' ~/bin/report.sh\n",
    wrong="true\n",
    alt={"alt_c_locale": "sed -i '2i export LC_ALL=C' ~/bin/report.sh\n"},
)

lab(
    id="ld-015", title="Маскирование секретов в логе",
    description="Замените секреты в копии лога, сохранив структуру строк и возможность группировки по request ID.",
    skills=["sed -E", "регулярные выражения", "анонимизация логов"],
    objectives=["Скрыть значения секретов", "Не потерять события", "Сохранить request ID"],
    task="""\
В `~/logs/app.log` есть строки с секретами (`token=…`, `password=…`, `api_key=…`).

Создайте копию `~/logs/sanitized.log`, где **значения секретов заменены на `[REDACTED]`** (ключ остаётся: `token=[REDACTED]`). Число строк и `req=…` каждой строки менять нельзя; исходный `app.log` оставьте как есть.
""",
    hints=["`sed -E 's/(token|password|api_key)=[^ ]+/\\1=[REDACTED]/g'`.", "Удалять строки целиком нельзя: при расследовании пропадут события."],
    checks=[
        ("secrets_gone", "Секретов в копии нет", "Секреты скрыты", "В sanitized.log остались секретные значения"),
        ("structure_kept", "Число строк и request ID сохранены", "Структура сохранена", "Число строк или идентификаторы req отличаются от исходных"),
        ("keys_kept", "Ключи сохранены, значения заменены", "Ключи сохранены", "Строки с секретами должны сохранить ключ: token=[REDACTED]"),
    ],
    setup=r"""
mkdir -p ~/logs
cat > ~/logs/app.log <<'EOT'
req=r001 user=alice token=tok_ABC123 msg=login
req=r002 user=bob password=hunter2 msg=signup
req=r003 user=carol msg=ok
req=r004 user=dave api_key=sk_live_99XYZ msg=call
req=r005 user=erin token=tok_QRS789 password=p4ssw0rd msg=reset
req=r006 user=frank msg=logout
EOT
""",
    validate=r"""
L=/home/student/logs
chk secrets_gone '! grep -qE "tok_ABC123|hunter2|sk_live_99XYZ|tok_QRS789|p4ssw0rd" $L/sanitized.log'
chk structure_kept '[ "$(wc -l < $L/sanitized.log)" = "$(wc -l < $L/app.log)" ] && [ "$(grep -o "req=r[0-9]*" $L/sanitized.log)" = "$(grep -o "req=r[0-9]*" $L/app.log)" ]'
chk keys_kept '[ "$(grep -o "[a-z_]*=\[REDACTED\]" $L/sanitized.log | wc -l)" = 5 ] && grep -q "token=\[REDACTED\]" $L/sanitized.log && grep -q "password=\[REDACTED\]" $L/sanitized.log && grep -q "api_key=\[REDACTED\]" $L/sanitized.log'
""",
    solution=r"""
sed -E 's/(token|password|api_key)=[^ ]+/\1=[REDACTED]/g' ~/logs/app.log > ~/logs/sanitized.log
""",
    wrong=r"""
grep -vE 'token=|password=|api_key=' ~/logs/app.log > ~/logs/sanitized.log
""",
)

# ------------------------------------------------------------------------------------- Процессы
lab(
    id="ld-035", title="Процесс, переживающий закрытие терминала",
    description="Запустите длинную задачу так, чтобы закрытие терминала (SIGHUP) её не убило.",
    skills=["nohup", "setsid", "SIGHUP", "сессии"],
    objectives=["Объяснить роль сессии и SIGHUP", "Запустить задачу в отвязанном виде"],
    task="""\
Скрипт `~/bin/longjob.sh` работает ~4 секунды, а в начале записывает в `~/job.info` свой PID, SID и маску игнорируемых сигналов, в конце создаёт `~/job.done`.

Запустите его **в фоне так, чтобы он пережил закрытие терминала** (отвязка от сессии или игнорирование SIGHUP) и дождитесь `~/job.done`.
""",
    hints=["Простое `&` оставляет задачу в той же сессии: при закрытии терминала она получит SIGHUP.", "`nohup команда &` или `setsid команда &`."],
    checks=[
        ("job_done", "Задача завершилась: job.done создан", "Задача выполнена", "Файл ~/job.done не появился"),
        ("survives_hup", "Задача защищена от SIGHUP", "Задача отвязана от терминала", "Задача не защищена от закрытия терминала (нужны nohup или setsid)"),
    ],
    setup=r"""
mkdir -p ~/bin
rm -f ~/job.done ~/job.info
cat > ~/bin/longjob.sh <<'EOT'
#!/bin/bash
{
  echo "pid=$$"
  echo "sid=$(ps -o sid= -p $$ | tr -d ' ')"
  echo "ign=$(awk '/SigIgn/{print $2}' /proc/$$/status)"
} > "$HOME/job.info"
sleep 4
echo done > "$HOME/job.done"
EOT
chmod +x ~/bin/longjob.sh
""",
    validate=r"""
I=/home/student/job.info
chk job_done '[ -f /home/student/job.done ]'
chk survives_hup 'pid=$(grep ^pid= $I | cut -d= -f2); sid=$(grep ^sid= $I | cut -d= -f2); ign=$(grep ^ign= $I | cut -d= -f2); [ "$pid" = "$sid" ] || [ $(( 0x$ign & 1 )) -eq 1 ]'
""",
    solution="nohup ~/bin/longjob.sh >/dev/null 2>&1 &\nsleep 6\n",
    wrong="~/bin/longjob.sh &\nsleep 6\n",
    alt={"alt_setsid": "setsid ~/bin/longjob.sh >/dev/null 2>&1 &\nsleep 6\n"},
)

lab(
    id="ld-036", title="Инцидент: zombie-процессы в учебном супервизоре",
    description="Супервизор запускает детей и не вызывает wait(): остаются zombie. Исправьте обработку завершений.",
    skills=["ps", "zombie", "wait()", "SIGCHLD"],
    objectives=["Найти родителя zombie", "Исправить код супервизора", "Убедиться, что zombie не остаются"],
    task="""\
**Инцидент.** `~/sup/supervisor.py` запускает 20 короткоживущих детей, но не забирает их статусы: `ps` показывает множество процессов в состоянии `Z`.

Найдите родителя zombie (`ps -eo pid,ppid,stat,cmd | grep Z`), **исправьте код** супервизора (родитель обязан забрать статусы детей: `wait()`, `poll()` или `SIGCHLD`) и перезапустите его. После этого zombie остаться не должно, а супервизор должен работать.
""",
    hints=["Zombie — завершившийся ребёнок, чей статус родитель ещё не прочитал. Сигнал «убить zombie» не поможет.", "В Python достаточно `subprocess.Popen(...).wait()` или `signal.signal(signal.SIGCHLD, signal.SIG_IGN)`."],
    checks=[
        ("no_zombies", "Zombie-процессов нет", "Zombie-процессов нет", "В системе остаются zombie-процессы"),
        ("supervisor_alive", "Исправленный супервизор работает", "Супервизор работает", "Супервизор не запущен — его нужно перезапустить после исправления"),
    ],
    setup=r"""
mkdir -p ~/sup
cat > ~/sup/supervisor.py <<'EOT'
import subprocess, time
for _ in range(20):
    subprocess.Popen(["/bin/true"])  # статус ребёнка никто не забирает
    time.sleep(0.15)
while True:
    time.sleep(1)
EOT
setsid nohup python3 ~/sup/supervisor.py >/dev/null 2>&1 </dev/null &
sleep 3.8
""",
    validate=r"""
sleep 4
chk no_zombies '[ "$(ps -eo stat= | grep -c "^Z")" = 0 ]'
chk supervisor_alive 'pgrep -f "sup/supervisor.py"'
""",
    solution=r"""
pkill -f sup/supervisor.py
cat > ~/sup/supervisor.py <<'EOT'
import subprocess, time
for _ in range(20):
    subprocess.Popen(["/bin/true"]).wait()
    time.sleep(0.15)
while True:
    time.sleep(1)
EOT
setsid nohup python3 ~/sup/supervisor.py >/dev/null 2>&1 </dev/null &
sleep 3.5
""",
    wrong="pkill -f sup/supervisor.py\nsleep 0.5\n",
)

lab(
    id="ld-037", title="Инцидент: сервис не завершается по SIGTERM из-за зависшего child",
    description="Добавьте контролируемое завершение: дать ребёнку время, затем принудительно убить и выйти в срок.",
    skills=["signal", "SIGTERM/SIGKILL", "дедлайн", "subprocess"],
    objectives=["Корректно завершать дочерние процессы", "Не превышать дедлайн остановки"],
    task="""\
**Инцидент.** `~/svc/service.py` запускает дочерний процесс, который **игнорирует SIGTERM**. По SIGTERM сервис ждёт ребёнка вечно, и оркестратор вынужден убивать его через SIGKILL.

Исправьте обработчик SIGTERM: послать ребёнку `terminate()`, подождать **не более 3 секунд**, затем `kill()`, и завершить сервис с кодом 0. После остановки не должно оставаться ни сервиса, ни ребёнка, а вся остановка — уложиться в ~6 секунд.
""",
    hints=["`child.terminate()`, затем `child.wait(timeout=3)` внутри `try/except subprocess.TimeoutExpired`.", "После истечения дедлайна — `child.kill(); child.wait()` и `sys.exit(0)`."],
    checks=[
        ("service_exits", "Сервис завершился по SIGTERM", "Сервис завершился", "Сервис не завершился по SIGTERM"),
        ("no_children", "Дочерних процессов не осталось", "Дочерних процессов нет", "После остановки остался дочерний процесс"),
        ("in_deadline", "Остановка уложилась в дедлайн", "Остановка уложилась в срок", "Остановка заняла слишком долго"),
    ],
    setup=r"""
mkdir -p ~/svc
cat > ~/svc/service.py <<'EOT'
import signal, subprocess, sys, time

child = subprocess.Popen([sys.executable, "-c",
    "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(3600)  # STUCKCHILD"])

def on_term(*_):
    child.wait()      # ждём вечно: ребёнок игнорирует SIGTERM
    sys.exit(0)

signal.signal(signal.SIGTERM, on_term)
while True:
    time.sleep(0.5)
EOT
""",
    exercise=r"""
mkdir -p ~/.ex; rm -f ~/.ex/res
cd ~/svc
python3 service.py > /dev/null 2>&1 < /dev/null &
pid=$!
sleep 1
kill -TERM $pid
t0=$(date +%s.%N)
alive() { s=$(ps -o stat= -p $pid 2>/dev/null); [ -n "$s" ] && [ "${s:0:1}" != Z ]; }
for i in $(seq 1 90); do alive || break; sleep 0.1; done
t1=$(date +%s.%N)
a=0; alive && a=1
k=$(pgrep -fc 'STUCK[C]HILD' || true)
secs=$(awk -v a="$t0" -v b="$t1" 'BEGIN{printf "%.1f", b-a}')
echo "alive=$a kids=${k:-0} secs=$secs" > ~/.ex/res
pkill -9 -f 'STUCK[C]HILD'; kill -9 $pid 2>/dev/null
true
""",
    validate=r"""
R=$(cat /home/student/.ex/res)
chk service_exits 'echo "$R" | grep -q "alive=0"'
chk no_children 'echo "$R" | grep -q "kids=0"'
chk in_deadline 'awk -v s="$(echo "$R" | sed "s/.*secs=//")" "BEGIN{exit !(s+0 <= 6.0)}"'
""",
    solution=r"""
cat > ~/svc/service.py <<'EOT'
import signal, subprocess, sys, time

child = subprocess.Popen([sys.executable, "-c",
    "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(3600)  # STUCKCHILD"])

def on_term(*_):
    child.terminate()
    try:
        child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait()
    sys.exit(0)

signal.signal(signal.SIGTERM, on_term)
while True:
    time.sleep(0.5)
EOT
""",
    wrong=r"""
sed -i 's/    child.wait()      # ждём вечно: ребёнок игнорирует SIGTERM/    pass/' ~/svc/service.py
""",
)

lab(
    id="ld-038", title="Что знает /proc о процессе",
    description="Определите cwd, окружение, открытые файлы, лимиты и cgroup процесса по /proc/<pid>.",
    skills=["/proc/PID", "readlink", "environ", "limits", "cgroup"],
    objectives=["Читать состояние процесса из /proc", "Составить отчёт по контрольному процессу"],
    task="""\
Запущен контрольный процесс `probe.py`. Найдите его PID и запишите в `~/proc_report.txt` пять строк:

```
cwd=<рабочий каталог процесса>
token=<значение переменной PROBE_TOKEN из его окружения>
open_file=<путь файла held.txt, который он держит открытым>
nofile_soft=<мягкий лимит открытых файлов (Max open files)>
cgroup=<содержимое /proc/PID/cgroup>
```
""",
    hints=["`readlink /proc/PID/cwd`, `tr '\\0' '\\n' < /proc/PID/environ`, `ls -l /proc/PID/fd`.", "Лимиты — `/proc/PID/limits`, cgroup — `/proc/PID/cgroup`."],
    checks=[
        ("cwd", "cwd процесса", "cwd указан верно", "cwd должен быть ~/probe_dir"),
        ("token", "PROBE_TOKEN из окружения", "Переменная окружения прочитана", "token должен быть значением PROBE_TOKEN процесса"),
        ("open_file", "Открытый файл held.txt", "Открытый файл найден", "open_file должен быть путём held.txt, открытого процессом"),
        ("limits_cgroup", "nofile_soft и cgroup", "Лимит и cgroup указаны верно", "nofile_soft и cgroup должны совпадать с /proc/PID/limits и /proc/PID/cgroup"),
    ],
    setup=r"""
mkdir -p ~/probe_dir
cat > ~/probe.py <<'EOT'
import os, time
os.chdir(os.path.expanduser("~/probe_dir"))
held = open("held.txt", "w")
while True:
    time.sleep(1)
EOT
PROBE_TOKEN=xyz123 setsid nohup python3 ~/probe.py >/dev/null 2>&1 </dev/null &
sleep 0.7
""",
    validate=r"""
R=/home/student/proc_report.txt
pid=$(pgrep -f 'probe.py' | head -n 1)
soft=$(awk '/Max open files/{print $4}' /proc/$pid/limits)
cg=$(cat /proc/$pid/cgroup | head -n 1)
chk cwd '[ "$(grep ^cwd= $R | cut -d= -f2-)" = /home/student/probe_dir ]'
chk token '[ "$(grep ^token= $R | cut -d= -f2-)" = xyz123 ]'
chk open_file '[ "$(grep ^open_file= $R | cut -d= -f2-)" = /home/student/probe_dir/held.txt ]'
chk limits_cgroup '[ "$(grep ^nofile_soft= $R | cut -d= -f2-)" = "$soft" ] && [ "$(grep ^cgroup= $R | head -n 1 | cut -d= -f2-)" = "$cg" ]'
""",
    solution=r"""
pid=$(pgrep -f probe.py | head -n 1)
{
  echo "cwd=$(readlink /proc/$pid/cwd)"
  echo "token=$(tr '\0' '\n' < /proc/$pid/environ | grep ^PROBE_TOKEN= | cut -d= -f2)"
  echo "open_file=$(ls -l /proc/$pid/fd | grep held.txt | sed 's/.* -> //')"
  echo "nofile_soft=$(awk '/Max open files/{print $4}' /proc/$pid/limits)"
  echo "cgroup=$(head -n 1 /proc/$pid/cgroup)"
} > ~/proc_report.txt
""",
    wrong="echo 'cwd=/' > ~/proc_report.txt\n",
)

# ------------------------------------------------------------------------------------ Bash и Python
lab(
    id="ld-130", title="Идемпотентный скрипт подготовки",
    description="Сделайте скрипт идемпотентным: повторный запуск не создаёт дублей и не портит данные.",
    skills=["идемпотентность", "grep -qx", "mkdir -p", "безопасные повторы"],
    objectives=["Проверять состояние перед изменением", "Получать одинаковый результат при повторном запуске"],
    task="""\
Напишите `~/bin/provision.sh`, который готовит `~/srv/app`:

- создаёт каталог `~/srv/app`, если его нет;
- гарантирует, что в `~/srv/app/app.conf` есть **ровно одна** строка `port=8080`;
- гарантирует, что в `~/srv/app/users.txt` есть строки `alice` и `bob` **по одному разу**;
- не трогает существующие данные (`~/srv/app/data.txt`).

Проверка запустит скрипт дважды: состояние после первого и второго запусков должно совпасть, оба кода выхода — `0`.
""",
    hints=["Перед добавлением строки проверяйте: `grep -qx 'port=8080' файл || echo 'port=8080' >> файл`.", "`mkdir -p` не падает, если каталог уже есть."],
    checks=[
        ("exit_codes", "Оба запуска завершились с кодом 0", "Оба запуска успешны", "Каждый запуск provision.sh должен завершаться кодом 0"),
        ("same_state", "Состояние после двух запусков одинаково", "Повторный запуск не меняет состояние", "Повторный запуск изменил состояние (дубли строк)"),
        ("content_ok", "Конфиг, пользователи и data.txt верны", "Содержимое верное", "Нужно: одна строка port=8080, alice и bob по разу, data.txt не тронут"),
    ],
    setup=r"""
mkdir -p ~/srv/app ~/bin
echo "keep-me" > ~/srv/app/data.txt
""",
    exercise=r"""
mkdir -p ~/.ex; rm -f ~/.ex/rc1 ~/.ex/rc2 ~/.ex/s1 ~/.ex/s2 ~/srv/app/app.conf ~/srv/app/users.txt
[ -f ~/bin/provision.sh ] || exit 0
timeout 8 bash ~/bin/provision.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc1
(cd ~/srv && find . -type f | sort | xargs sha256sum) > ~/.ex/s1 2>/dev/null
timeout 8 bash ~/bin/provision.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc2
(cd ~/srv && find . -type f | sort | xargs sha256sum) > ~/.ex/s2 2>/dev/null
true
""",
    validate=r"""
E=/home/student/.ex; A=/home/student/srv/app
chk exit_codes '[ "$(cat $E/rc1)" = 0 ] && [ "$(cat $E/rc2)" = 0 ]'
chk same_state '[ -s $E/s1 ] && cmp -s $E/s1 $E/s2'
chk content_ok '[ "$(grep -cx port=8080 $A/app.conf)" = 1 ] && [ "$(grep -cx alice $A/users.txt)" = 1 ] && [ "$(grep -cx bob $A/users.txt)" = 1 ] && [ "$(cat $A/data.txt)" = keep-me ]'
""",
    solution=r"""
cat > ~/bin/provision.sh <<'EOT'
#!/bin/bash
mkdir -p ~/srv/app
grep -qx 'port=8080' ~/srv/app/app.conf 2>/dev/null || echo 'port=8080' >> ~/srv/app/app.conf
for u in alice bob; do
  grep -qx "$u" ~/srv/app/users.txt 2>/dev/null || echo "$u" >> ~/srv/app/users.txt
done
EOT
""",
    wrong=r"""
cat > ~/bin/provision.sh <<'EOT'
#!/bin/bash
mkdir -p ~/srv/app
echo 'port=8080' >> ~/srv/app/app.conf
echo alice >> ~/srv/app/users.txt
echo bob >> ~/srv/app/users.txt
EOT
""",
)

lab(
    id="ld-131", title="Инцидент: скрипт удаляет не тот каталог при пустой переменной",
    description="Исправьте валидацию входа и quoting, чтобы опасные значения отклонялись до изменения файловой системы.",
    skills=["quoting", "валидация входа", "cd ... &&", "find -delete"],
    objectives=["Проверять preconditions до удаления", "Корректно работать с пробелами в путях"],
    task="""\
**Инцидент.** `~/bin/cleanup.sh` очищает каталог `$DIR`, но при пустой или неверной переменной удаляет содержимое **текущего** каталога (`cd` не удался, `rm -rf ./*` выполнился). С путями, содержащими пробелы, он тоже не работает.

Исправьте скрипт:

- пустой или несуществующий `DIR` — сообщение в stderr, код `1` и **ничего не удаляется**;
- корректный `DIR` (в том числе с пробелами) — удалить всё содержимое (включая скрытые файлы), код `0`.
""",
    hints=["Проверьте `[ -n \"$DIR\" ] && [ -d \"$DIR\" ]` ДО любых изменений и завершайтесь с кодом 1.", "`find \"$DIR\" -mindepth 1 -delete` не зависит от текущего каталога и корректно работает с пробелами."],
    checks=[
        ("empty_dir_rejected", "DIR пуст: отказ, файлы целы", "Пустой DIR отклонён", "При пустом DIR скрипт должен отказаться (код ≠ 0) и ничего не удалять"),
        ("missing_dir_rejected", "DIR не существует: отказ, файлы целы", "Несуществующий DIR отклонён", "При несуществующем DIR скрипт должен отказаться (код ≠ 0) и ничего не удалять"),
        ("valid_cleaned", "Корректный DIR (с пробелом) очищен", "Корректный каталог очищен", "Каталог с пробелом в имени должен быть очищен с кодом 0"),
    ],
    setup=r"""
mkdir -p ~/bin
cat > ~/bin/cleanup.sh <<'EOT'
#!/bin/bash
cd $DIR
rm -rf ./*
EOT
chmod +x ~/bin/cleanup.sh
""",
    exercise=r"""
rm -rf ~/.ex; mkdir -p ~/.ex/sA ~/.ex/sB ~/.ex/sC "$HOME/.ex/target dir"
echo x > ~/.ex/sA/keep; echo x > ~/.ex/sB/keep; echo x > ~/.ex/sC/keep
echo 1 > "$HOME/.ex/target dir/f1"; echo 2 > "$HOME/.ex/target dir/.hidden"
( cd ~/.ex/sA && DIR= timeout 8 bash ~/bin/cleanup.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rcA )
( cd ~/.ex/sB && DIR=/nonexistent_dir_xyz timeout 8 bash ~/bin/cleanup.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rcB )
( cd ~/.ex/sC && DIR="$HOME/.ex/target dir" timeout 8 bash ~/bin/cleanup.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rcC )
true
""",
    validate=r"""
E=/home/student/.ex
chk empty_dir_rejected '[ -f $E/sA/keep ] && [ "$(cat $E/rcA)" != 0 ]'
chk missing_dir_rejected '[ -f $E/sB/keep ] && [ "$(cat $E/rcB)" != 0 ]'
chk valid_cleaned '[ "$(cat $E/rcC)" = 0 ] && [ -z "$(ls -A "$E/target dir")" ] && [ -f $E/sC/keep ]'
""",
    solution=r"""
cat > ~/bin/cleanup.sh <<'EOT'
#!/bin/bash
dir="${DIR:-}"
if [ -z "$dir" ] || [ ! -d "$dir" ]; then
  echo "refusing to clean: DIR is empty or not a directory" >&2
  exit 1
fi
find "$dir" -mindepth 1 -delete
EOT
""",
    wrong="true\n",
)

lab(
    id="ld-132", title="Блокировка для cron/timer-задачи",
    description="Добавьте lock: две параллельные копии не работают одновременно, а блокировка не «залипает» после SIGTERM.",
    skills=["flock", "lock-файлы", "trap", "stale lock"],
    objectives=["Не допустить двойного выполнения", "Освобождать lock при завершении"],
    task="""\
`~/bin/work.sh` выполняет работу ~2 секунды и дописывает `ran` в файл `$COUNTER`.

Напишите обёртку `~/bin/job_locked.sh`, которая запускает `work.sh` под блокировкой:

- если задача уже выполняется — **сразу выходит** (код 0), не выполняя работу второй раз;
- если выполняющуюся задачу убили (SIGTERM группе процессов), **блокировка не остаётся** и следующий запуск работает.
""",
    hints=["`flock -n 9` вместе с `exec 9>файл` держит блокировку, пока жив процесс-владелец, и снимается ядром при его смерти.", "Если делаете lock через `mkdir`, добавьте `trap 'rmdir ...' EXIT TERM`."],
    checks=[
        ("no_double_run", "Две параллельные копии: работа выполнена один раз", "Двойной запуск исключён", "При двух параллельных запусках работа выполнилась не один раз"),
        ("no_stale_lock", "После SIGTERM блокировка не залипла", "Блокировка снимается", "После убитой задачи следующий запуск не смог выполнить работу (залипший lock)"),
    ],
    setup=r"""
mkdir -p ~/bin
printf '#!/bin/bash\nsleep 2\necho ran >> "$COUNTER"\n' > ~/bin/work.sh
chmod +x ~/bin/work.sh
""",
    exercise=r"""
mkdir -p ~/.ex; rm -f ~/.ex/counter ~/.ex/c1 ~/.ex/c2 ~/.job.lock; rm -rf ~/.job.lock.d ~/.job.lockdir
[ -f ~/bin/job_locked.sh ] || exit 0
export COUNTER=$HOME/.ex/counter
setsid bash ~/bin/job_locked.sh > /dev/null 2>&1 < /dev/null &
setsid bash ~/bin/job_locked.sh > /dev/null 2>&1 < /dev/null &
sleep 3.5
( [ -f ~/.ex/counter ] && wc -l < ~/.ex/counter || echo 0 ) > ~/.ex/c1
setsid bash ~/bin/job_locked.sh > /dev/null 2>&1 < /dev/null &
jp=$!
sleep 0.6
kill -TERM -- -$jp 2>/dev/null
sleep 0.4
timeout 6 bash ~/bin/job_locked.sh > /dev/null 2>&1 < /dev/null
( [ -f ~/.ex/counter ] && wc -l < ~/.ex/counter || echo 0 ) > ~/.ex/c2
true
""",
    validate=r"""
E=/home/student/.ex
chk no_double_run '[ "$(tr -d " " < $E/c1)" = 1 ]'
chk no_stale_lock '[ "$(tr -d " " < $E/c2)" = 2 ]'
""",
    solution=r"""
cat > ~/bin/job_locked.sh <<'EOT'
#!/bin/bash
exec 9>"$HOME/.job.lock"
if ! flock -n 9; then
  echo "already running"
  exit 0
fi
~/bin/work.sh
EOT
""",
    wrong=r"""
printf '#!/bin/bash\n~/bin/work.sh\n' > ~/bin/job_locked.sh
""",
    alt={"alt_mkdir_trap": r"""
cat > ~/bin/job_locked.sh <<'EOT'
#!/bin/bash
lock="$HOME/.job.lockdir"
if ! mkdir "$lock" 2>/dev/null; then echo "already running"; exit 0; fi
trap 'rmdir "$lock"' EXIT
trap 'exit 143' TERM
~/bin/work.sh &
wait $!
EOT
"""},
)

lab(
    id="ld-133", title="Потоковый парсер JSON на Python",
    description="Перепишите разбор JSON-строк в Python с потоковым чтением: большой вход не должен приводить к OOM.",
    skills=["python3", "json", "потоковая обработка", "ulimit -v"],
    objectives=["Читать stdin построчно", "Игнорировать битые строки", "Укладываться в ограничение памяти"],
    task="""\
Напишите `~/bin/parse.py`: читает со stdin **JSON-строки** вида `{"user": "...", "amount": число, "status": "..."}` и печатает в stdout один JSON-объект `{"<user>": <сумма amount>, ...}` — только по записям со `status == "ok"`.

- битые строки и записи без `user`/`amount` — пропускать (можно писать в stderr);
- суммы округлять до 2 знаков;
- читать вход **потоково**: проверка подаст ~600 тыс. строк при ограничении памяти процесса ≈120 МБ.
""",
    hints=["Не собирайте все строки в список: `for line in sys.stdin:` и накапливайте только словарь сумм.", "`json.loads` в `try/except ValueError`, значения — через `float()`."],
    checks=[
        ("small_cases", "Малые входы: битые строки, юникод", "Малый вход разобран верно", "На малом входе (битые строки, юникод) результат неверен"),
        ("large_stream", "Большой вход в ограничении памяти", "Большой вход обработан потоково", "На большом входе при лимите памяти результат неверен (читайте stdin построчно)"),
    ],
    setup="mkdir -p ~/bin\n",
    exercise=r"""
mkdir -p ~/.ex; rm -f ~/.ex/small.out ~/.ex/large.out
[ -f ~/bin/parse.py ] || exit 0
cat > ~/.ex/small.jsonl <<'EOT'
{"user":"alice","amount":10.5,"status":"ok"}
{"user":"bob","amount":3,"status":"ok"}
not json at all
{"user":"alice","amount":4.25,"status":"fail"}
{"user":"юзер","amount":1.1,"status":"ok"}
{"user":"bob","amount":2.2,"status":"ok"}
{"amount":5,"status":"ok"}
EOT
timeout 8 python3 ~/bin/parse.py < ~/.ex/small.jsonl > ~/.ex/small.out 2>/dev/null
python3 - <<'EOT' | ( ulimit -v 130000; timeout 12 python3 ~/bin/parse.py > ~/.ex/large.out 2>/dev/null )
import sys
w = sys.stdout.write
for i in range(600000):
    w('{"user":"u%d","amount":%s,"status":"%s"}\n' % (i % 10, (i % 7) + 0.5, "ok" if i % 3 else "fail"))
EOT
true
""",
    validate=r"""
cmp_json() { python3 - "$1" <<'EOT'
import json, sys
try:
    got = json.load(open("/home/student/.ex/%s.out" % sys.argv[1]))
except Exception:
    print("BAD"); raise SystemExit
if sys.argv[1] == "small":
    exp = {"alice": 10.5, "bob": 5.2, "юзер": 1.1}
else:
    exp = {}
    for i in range(600000):
        if i % 3:
            exp["u%d" % (i % 10)] = exp.get("u%d" % (i % 10), 0) + (i % 7) + 0.5
ok = set(got) == set(exp) and all(abs(float(got[k]) - exp[k]) < 0.011 for k in exp)
print("OK" if ok else "BAD")
EOT
}
chk small_cases '[ "$(cmp_json small)" = OK ]'
chk large_stream '[ "$(cmp_json large)" = OK ]'
""",
    solution=r"""
cat > ~/bin/parse.py <<'EOT'
import json, sys

totals = {}
for line in sys.stdin:
    try:
        rec = json.loads(line)
        if rec.get("status") != "ok":
            continue
        user, amount = rec["user"], float(rec["amount"])
    except (ValueError, KeyError, TypeError, AttributeError):
        print("skip: %r" % line[:40], file=sys.stderr)
        continue
    totals[user] = totals.get(user, 0.0) + amount
print(json.dumps({k: round(v, 2) for k, v in totals.items()}, ensure_ascii=False))
EOT
""",
    wrong=r"""
cat > ~/bin/parse.py <<'EOT'
import json, sys

rows = [json.loads(l) for l in sys.stdin]
totals = {}
for r in rows:
    if r.get("status") == "ok":
        totals[r["user"]] = totals.get(r["user"], 0.0) + float(r["amount"])
print(json.dumps(totals))
EOT
""",
)

# --------------------------------------------------------------------------------- Память и CPU
lab(
    id="ld-082", title="Инцидент: процесс убит OOM killer в контейнере",
    description="Найдите лимит памяти контейнера, число OOM-убийств и пик потребления по счётчикам cgroup.",
    skills=["cgroup v2", "memory.max", "memory.events", "memory.peak"],
    objectives=["Подтвердить OOM счётчиками", "Назвать лимит и пик"],
    task="""\
**Инцидент.** Приложение `~/bin/hog.py` при старте было убито: `Killed`.

Подтвердите причину по счётчикам cgroup контейнера и запишите в `~/oom_report.txt`:

```
limit_bytes=<значение /sys/fs/cgroup/memory.max>
oom_kills=<oom_kill из /sys/fs/cgroup/memory.events>
peak_bytes=<значение /sys/fs/cgroup/memory.peak>
```
""",
    hints=["Все счётчики лежат в `/sys/fs/cgroup/`: `memory.max`, `memory.events`, `memory.peak`.", "В `memory.events` строка `oom_kill N` — сколько процессов убито за нехватку памяти."],
    checks=[
        ("limit", "limit_bytes совпадает с memory.max", "Лимит указан верно", "limit_bytes должен совпадать с /sys/fs/cgroup/memory.max"),
        ("oom_kills", "oom_kills ≥ 1 и совпадает со счётчиком", "OOM-убийства подтверждены", "oom_kills должен совпадать с oom_kill в memory.events (и быть ≥ 1)"),
        ("peak", "peak_bytes: пик около лимита", "Пик указан верно", "peak_bytes должен быть значением memory.peak (пик достигал лимита)"),
    ],
    setup=r"""
mkdir -p ~/bin
printf 'x = bytearray(600 * 1024 * 1024)\nprint("allocated")\n' > ~/bin/hog.py
python3 ~/bin/hog.py > /dev/null 2>&1 || true
true
""",
    validate=r"""
R=/home/student/oom_report.txt
lim=$(cat /sys/fs/cgroup/memory.max)
oom=$(awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events)
peak=$(cat /sys/fs/cgroup/memory.peak 2>/dev/null)
chk limit '[ "$(grep ^limit_bytes= $R | cut -d= -f2)" = "$lim" ]'
chk oom_kills '[ "$oom" -ge 1 ] && [ "$(grep ^oom_kills= $R | cut -d= -f2)" = "$oom" ]'
chk peak '[ -n "$peak" ] && [ "$(grep ^peak_bytes= $R | cut -d= -f2)" -ge $(( $(cat /sys/fs/cgroup/memory.max) / 2 )) ] && [ "$(grep ^peak_bytes= $R | cut -d= -f2)" -le "$peak" ]'
""",
    solution=r"""
{
  echo "limit_bytes=$(cat /sys/fs/cgroup/memory.max)"
  echo "oom_kills=$(awk '/^oom_kill /{print $2}' /sys/fs/cgroup/memory.events)"
  echo "peak_bytes=$(cat /sys/fs/cgroup/memory.peak)"
} > ~/oom_report.txt
""",
    wrong="printf 'limit_bytes=0\\noom_kills=0\\npeak_bytes=0\\n' > ~/oom_report.txt\n",
)

# ------------------------------------------------------------------------------- Этап 4: синьор
lab(
    id="ld-016", title="Потоковая обработка большого журнала с атомарной публикацией",
    description="Обработайте журнал без загрузки в память и опубликуйте отчёт так, чтобы при сбое не появлялся частичный результат.",
    skills=["потоковая обработка", "os.replace", "fsync", "временные файлы"],
    objectives=["Считать статистику построчно", "Публиковать атомарно", "Оставлять прежний отчёт при сбое"],
    task="""\
Напишите `~/bin/report.py ЖУРНАЛ ОТЧЁТ`:

- читает журнал **построчно** (проверка подаст ~300 тыс. строк при лимите памяти ≈120 МБ) и считает число строк по коду `status=NNN`;
- записывает отчёт — JSON-объект `{"200": n, "404": m, ...}` — в `ОТЧЁТ` **атомарно** (запись во временный файл рядом + `os.replace`);
- если в журнале встретилась строка со словом `CORRUPT`, завершается с кодом `2`, **не трогая прежний отчёт** и не оставляя временных файлов.
""",
    hints=["Сначала посчитайте всё в памяти (словарь счётчиков), только потом пишите отчёт во временный файл и `os.replace`.", "При исключении удаляйте временный файл и выходите с кодом 2."],
    checks=[
        ("counts_ok", "Большой журнал: верные счётчики в лимите памяти", "Счётчики верны", "На большом журнале счётчики неверны или процесс не уложился в память"),
        ("failure_keeps_old", "Сбой: прежний отчёт цел, код 2", "При сбое прежний отчёт сохранён", "При CORRUPT нужен код 2 и неизменённый прежний отчёт"),
        ("no_temp_leftovers", "Временных файлов не осталось", "Временных файлов нет", "Рядом с отчётом остались временные файлы"),
    ],
    setup="mkdir -p ~/bin\n",
    exercise=r"""
rm -rf ~/.ex; mkdir -p ~/.ex/rep
[ -f ~/bin/report.py ] || exit 0
python3 - > ~/.ex/rep/big.log <<'EOT'
import sys
w = sys.stdout.write
codes = [200, 200, 200, 404, 500]
for i in range(300000):
    w("10.0.0.%d GET /p status=%d\n" % (i % 250, codes[i % 5]))
EOT
( ulimit -v 130000; timeout 12 python3 ~/bin/report.py ~/.ex/rep/big.log ~/.ex/rep/out.json > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc_ok )
printf '10.0.0.1 GET / status=200\n10.0.0.2 CORRUPT line\n10.0.0.3 GET / status=200\n' > ~/.ex/rep/bad.log
echo OLD > ~/.ex/rep/out2.json
timeout 8 python3 ~/bin/report.py ~/.ex/rep/bad.log ~/.ex/rep/out2.json > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc_bad
ls -A ~/.ex/rep > ~/.ex/listing
true
""",
    validate=r"""
E=/home/student/.ex
chk_counts() { python3 - <<'EOT'
import json
try:
    got = json.load(open("/home/student/.ex/rep/out.json"))
except Exception:
    print("BAD"); raise SystemExit
print("OK" if got == {"200": 180000, "404": 60000, "500": 60000} else "BAD")
EOT
}
chk counts_ok '[ "$(cat $E/rc_ok)" = 0 ] && [ "$(chk_counts)" = OK ]'
chk failure_keeps_old '[ "$(cat $E/rc_bad)" = 2 ] && [ "$(cat $E/rep/out2.json)" = OLD ]'
chk no_temp_leftovers '[ "$(sort $E/listing | paste -sd,)" = "bad.log,big.log,out.json,out2.json" ]'
""",
    solution=r"""
cat > ~/bin/report.py <<'EOT'
import collections, json, os, sys

log, out = sys.argv[1], sys.argv[2]
tmp = out + ".tmp"
try:
    counts = collections.Counter()
    with open(log) as f:
        for line in f:
            if "CORRUPT" in line:
                raise ValueError("corrupt line")
            i = line.find("status=")
            if i >= 0:
                counts[line[i + 7:i + 10]] += 1
    with open(tmp, "w") as w:
        json.dump(counts, w)
        w.flush()
        os.fsync(w.fileno())
    os.replace(tmp, out)
except Exception as exc:
    if os.path.exists(tmp):
        os.unlink(tmp)
    print("error:", exc, file=sys.stderr)
    sys.exit(2)
EOT
""",
    wrong=r"""
cat > ~/bin/report.py <<'EOT'
import collections, json, sys

log, out = sys.argv[1], sys.argv[2]
w = open(out, "w")
counts = collections.Counter()
for line in open(log):
    if "CORRUPT" in line:
        sys.exit(2)
    i = line.find("status=")
    if i >= 0:
        counts[line[i + 7:i + 10]] += 1
json.dump(counts, w)
w.close()
EOT
""",
)

lab(
    id="ld-134", title="Инцидент: частично выполненная автоматизация создаёт дубли",
    description="Добавьте checkpoint и идемпотентный повтор: сбой на любом шаге должен восстанавливаться без дублей.",
    skills=["checkpoint", "идемпотентность", "retry", "восстановление"],
    objectives=["Запоминать выполненные шаги", "Безопасно повторять после сбоя"],
    task="""\
**Инцидент.** `~/bin/migrate.sh` выполняет 4 шага (каждый дописывает `stepN` в `$STATE/ledger.txt`). При сбое посередине повторный запуск начинает с начала и создаёт дубли.

Доработайте скрипт: после сбоя на **любом** шаге повторный запуск должен завершиться кодом `0` и оставить в `ledger.txt` каждый из `step1…step4` **ровно по одному разу** (сохраняйте прогресс — checkpoint).

Переменная `FAIL_AT=N` имитирует сбой перед шагом N.
""",
    hints=["Ведите файл `$STATE/done` с выполненными шагами и пропускайте их при повторе.", "Записывайте checkpoint ПОСЛЕ успешного шага, чтобы повтор не пропустил невыполненное."],
    checks=[
        ("recovers_all_steps", "Восстановление после сбоя на каждом из 4 шагов", "Все сбои восстанавливаются без дублей", "После сбоя на одном из шагов ledger содержит дубли или не все шаги"),
        ("exit_codes", "Сбой даёт ≠ 0, повтор даёт 0", "Коды завершения верны", "Запуск со сбоем должен вернуть ненулевой код, повторный — 0"),
    ],
    setup=r"""
mkdir -p ~/bin
cat > ~/bin/migrate.sh <<'EOT'
#!/bin/bash
STATE="${STATE:-$HOME/state}"
mkdir -p "$STATE"
for n in 1 2 3 4; do
  if [ "$FAIL_AT" = "$n" ]; then
    echo "step $n failed" >&2
    exit 1
  fi
  echo "step$n" >> "$STATE/ledger.txt"
done
EOT
chmod +x ~/bin/migrate.sh
""",
    exercise=r"""
rm -rf ~/.ex; mkdir -p ~/.ex
for k in 1 2 3 4; do
  S=~/.ex/st$k
  STATE=$S FAIL_AT=$k timeout 8 bash ~/bin/migrate.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/f$k
  STATE=$S timeout 8 bash ~/bin/migrate.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/r$k
done
true
""",
    validate=r"""
E=/home/student/.ex
want="$(printf 'step1\nstep2\nstep3\nstep4')"
ok=1
for k in 1 2 3 4; do [ "$(sort $E/st$k/ledger.txt 2>/dev/null)" = "$want" ] || ok=0; done
chk recovers_all_steps '[ "$ok" = 1 ]'
codes=1
for k in 1 2 3 4; do [ "$(cat $E/f$k)" != 0 ] && [ "$(cat $E/r$k)" = 0 ] || codes=0; done
chk exit_codes '[ "$codes" = 1 ]'
""",
    solution=r"""
cat > ~/bin/migrate.sh <<'EOT'
#!/bin/bash
STATE="${STATE:-$HOME/state}"
mkdir -p "$STATE"
for n in 1 2 3 4; do
  grep -qx "step$n" "$STATE/done" 2>/dev/null && continue
  if [ "$FAIL_AT" = "$n" ]; then
    echo "step $n failed" >&2
    exit 1
  fi
  echo "step$n" >> "$STATE/ledger.txt"
  echo "step$n" >> "$STATE/done"
done
EOT
""",
    wrong="true\n",
)

lab(
    id="ld-135", title="CLI-утилита: dry-run, структурные логи, таймауты, лимит параллелизма",
    description="Соберите утилиту пакетного запуска с режимом dry-run, JSON-логами, таймаутом и ограничением параллелизма.",
    skills=["argparse", "JSON-логи", "ThreadPoolExecutor", "timeout", "dry-run"],
    objectives=["Реализовать dry-run без побочных эффектов", "Ограничить параллелизм", "Убивать зависшие задачи по таймауту"],
    task="""\
Напишите `~/bin/batch.py [--dry-run] [--max-parallel N] [--timeout S] --out ДИР ФАЙЛ_ЗАДАЧ`.

Файл задач — строки `имя секунды`. Задача «работает» `секунды` (запустите `sleep`), затем создаёт `ДИР/имя.done`.

В stdout — **по одной JSON-строке на событие** с ключами `event`, `task`, `ts` (число, секунды):

- `plan` — для каждой задачи при `--dry-run` (тогда **ничего** не запускается и не создаётся);
- `start` / `finish` — начало и конец задачи;
- `timeout` — задача превысила `--timeout`: её процесс убивается, `.done` не создаётся.

Одновременно работает не более `--max-parallel` задач (по умолчанию 2).
""",
    hints=["`concurrent.futures.ThreadPoolExecutor(max_workers=N)` ограничивает параллелизм.", "`subprocess.run(['sleep', str(sec)], timeout=T)`: при `TimeoutExpired` логируйте `timeout` и не создавайте `.done`."],
    checks=[
        ("dry_run", "dry-run: план без побочных эффектов", "dry-run ничего не меняет", "В режиме dry-run нужны события plan для всех задач и ни одного созданного файла"),
        ("parallel_limit", "Параллелизм ≤ --max-parallel, результат создан", "Лимит параллелизма соблюдается", "Одновременно выполнялось больше задач, чем --max-parallel, или не все .done созданы"),
        ("timeout_kills", "Зависшая задача убита по таймауту", "Таймаут работает", "Задача, превысившая --timeout, должна дать событие timeout и не создать .done"),
        ("json_logs", "Логи — JSON-строки с event/task/ts", "Логи структурированы", "Каждая строка лога должна быть JSON с ключами event, task, ts"),
    ],
    setup="mkdir -p ~/bin\n",
    exercise=r"""
rm -rf ~/.ex; mkdir -p ~/.ex/out
printf 't1 1\nt2 1\nt3 1\nt4 1\nt5 1\nt6 1\n' > ~/.ex/tasks.txt
printf 'slow 5\nfast 0.2\n' > ~/.ex/tasks2.txt
[ -f ~/bin/batch.py ] || exit 0
timeout 6 python3 ~/bin/batch.py --dry-run --out ~/.ex/out ~/.ex/tasks.txt > ~/.ex/dry.log 2>/dev/null < /dev/null; echo $? > ~/.ex/dry.rc
ls -A ~/.ex/out | wc -l > ~/.ex/dry.n
timeout 10 python3 ~/bin/batch.py --max-parallel 2 --out ~/.ex/out ~/.ex/tasks.txt > ~/.ex/run.log 2>/dev/null < /dev/null; echo $? > ~/.ex/run.rc
ls ~/.ex/out | sort > ~/.ex/run.files
rm -f ~/.ex/out/*
timeout 8 python3 ~/bin/batch.py --timeout 1 --out ~/.ex/out ~/.ex/tasks2.txt > ~/.ex/to.log 2>/dev/null < /dev/null; echo $? > ~/.ex/to.rc
ls ~/.ex/out | sort > ~/.ex/to.files
true
""",
    validate=r"""
analyze() { python3 - "$1" <<'EOT'
import json, os, sys
E = "/home/student/.ex"
def events(name):
    out = []
    for line in open(os.path.join(E, name)):
        out.append(json.loads(line))
    return out
what = sys.argv[1]
try:
    if what == "dry":
        ev = events("dry.log")
        ok = sum(1 for e in ev if e["event"] == "plan") == 6 and open(E + "/dry.n").read().strip() == "0"
    elif what == "parallel":
        ev = events("run.log")
        marks = sorted((e["ts"], 1 if e["event"] == "start" else -1) for e in ev if e["event"] in ("start", "finish"))
        cur = peak = 0
        for _, d in sorted(marks, key=lambda m: (m[0], m[1])):
            cur += d
            peak = max(peak, cur)
        files = open(E + "/run.files").read().split()
        ok = 1 <= peak <= 2 and files == ["t%d.done" % i for i in range(1, 7)] and peak == 2
    elif what == "timeout":
        ev = events("to.log")
        files = open(E + "/to.files").read().split()
        ok = any(e["event"] == "timeout" and e["task"] == "slow" for e in ev) and files == ["fast.done"]
    else:
        ev = events("run.log") + events("dry.log")
        ok = bool(ev) and all({"event", "task", "ts"} <= set(e) and isinstance(e["ts"], (int, float)) for e in ev)
except Exception:
    ok = False
print("OK" if ok else "BAD")
EOT
}
chk dry_run '[ "$(analyze dry)" = OK ]'
chk parallel_limit '[ "$(analyze parallel)" = OK ]'
chk timeout_kills '[ "$(analyze timeout)" = OK ]'
chk json_logs '[ "$(analyze logs)" = OK ]'
""",
    solution=r"""
cat > ~/bin/batch.py <<'EOT'
import argparse, json, os, subprocess, sys, threading, time
from concurrent.futures import ThreadPoolExecutor

lock = threading.Lock()

def log(event, task):
    with lock:
        print(json.dumps({"event": event, "task": task, "ts": time.time()}), flush=True)

def run_task(name, seconds, out, timeout):
    log("start", name)
    try:
        subprocess.run(["sleep", str(seconds)], timeout=timeout, check=True)
    except subprocess.TimeoutExpired:
        log("timeout", name)
        return
    open(os.path.join(out, name + ".done"), "w").close()
    log("finish", name)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-parallel", type=int, default=2)
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("tasks")
    a = ap.parse_args()
    tasks = [l.split() for l in open(a.tasks) if l.strip()]
    if a.dry_run:
        for name, _ in tasks:
            log("plan", name)
        return
    os.makedirs(a.out, exist_ok=True)
    with ThreadPoolExecutor(max_workers=a.max_parallel) as pool:
        for name, sec in tasks:
            pool.submit(run_task, name, sec, a.out, a.timeout)

main()
EOT
""",
    wrong=r"""
cat > ~/bin/batch.py <<'EOT'
import argparse, json, os, subprocess, threading, time

def log(event, task):
    print(json.dumps({"event": event, "task": task, "ts": time.time()}), flush=True)

ap = argparse.ArgumentParser()
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--max-parallel", type=int, default=2)
ap.add_argument("--timeout", type=float, default=None)
ap.add_argument("--out", required=True)
ap.add_argument("tasks")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
ths = []
for l in open(a.tasks):
    name, sec = l.split()
    def w(n=name, s=sec):
        log("start", n)
        subprocess.run(["sleep", s])
        open(os.path.join(a.out, n + ".done"), "w").close()
        log("finish", n)
    t = threading.Thread(target=w); t.start(); ths.append(t)
for t in ths:
    t.join()
EOT
""",
)

lab(
    id="ld-136", title="Массовое изменение конфигураций: план, валидация, canary, rollback",
    description="Автоматизируйте раскатку конфигурации на парк узлов с проверкой, canary и откатом.",
    skills=["canary", "rollback", "валидация конфигурации", "безопасная раскатка"],
    objectives=["Валидировать до изменений", "Раскатывать начиная с canary", "Откатывать всё при сбое"],
    task="""\
В `~/fleet/hosts/h1…h6/app.conf` — конфигурации шести «хостов». Напишите `~/bin/rollout.sh НОВЫЙ_КОНФИГ`:

1. **План:** выведите список хостов (в stdout).
2. **Валидация до изменений:** `~/bin/validate_conf.sh` — если новый конфиг некорректен, **ничего не менять**, код `1`.
3. **Canary и раскатка:** по очереди `h1` (canary), затем остальные; после каждого хоста — `validate_conf.sh` на его `app.conf` и `~/bin/healthcheck.sh ДИР_ХОСТА`.
4. **Откат:** при сбое проверки на любом хосте вернуть **все** уже изменённые хосты к прежним конфигам, код `1`.

Каталог парка можно переопределить переменной `FLEET` (по умолчанию `~/fleet/hosts`).
""",
    hints=["Перед изменением хоста сохраняйте `app.conf.bak`; при откате восстанавливайте из него (и удаляйте `.bak`).", "Валидируйте новый конфиг ДО цикла по хостам — тогда плохой файл не затронет ни одного узла."],
    checks=[
        ("good_rollout", "Корректный конфиг применён ко всем хостам", "Корректная раскатка прошла", "Корректный конфиг должен оказаться на всех шести хостах (код 0)"),
        ("invalid_blocked", "Некорректный конфиг блокирует раскатку", "Некорректный конфиг заблокирован", "Некорректный конфиг не должен менять ни один хост (код ≠ 0)"),
        ("rollback_on_failure", "Сбой health-check откатывает всё", "Сбой привёл к полному откату", "При сбое health-check все хосты должны вернуться к прежней конфигурации (код ≠ 0)"),
        ("canary_failure", "Сбой canary не затрагивает остальных", "Сбой canary остановил раскатку", "При сбое на h1 остальные хосты не должны измениться"),
    ],
    setup=r"""
mkdir -p ~/fleet ~/bin ~/.fleet_pristine
for h in h1 h2 h3 h4 h5 h6; do
  mkdir -p ~/fleet/hosts/$h
  printf 'port=8080\nmode=prod\n' > ~/fleet/hosts/$h/app.conf
done
cp -a ~/fleet/hosts ~/.fleet_pristine/
printf '#!/bin/bash\ngrep -qE "^port=[0-9]+$" "$1" && grep -qE "^mode=(prod|stage)$" "$1"\n' > ~/bin/validate_conf.sh
printf '#!/bin/bash\n[ ! -e "$1/.broken" ]\n' > ~/bin/healthcheck.sh
chmod +x ~/bin/validate_conf.sh ~/bin/healthcheck.sh
""",
    exercise=r"""
rm -rf ~/.ex; mkdir -p ~/.ex
[ -f ~/bin/rollout.sh ] || exit 0
printf 'port=9090\nmode=stage\n' > ~/.ex/good.conf
printf 'port=abc\nmode=prod\n' > ~/.ex/bad.conf
reset() { rm -rf ~/fleet/hosts; cp -a ~/.fleet_pristine/hosts ~/fleet/hosts; }
snap() { (cd ~/fleet/hosts && for h in h1 h2 h3 h4 h5 h6; do printf '%s:' $h; sha256sum < $h/app.conf; done) > "$1"; }
run() { timeout 10 bash ~/bin/rollout.sh "$1" > /dev/null 2>&1 < /dev/null; echo $? > "$2"; }
reset; run ~/.ex/good.conf ~/.ex/rcA; snap ~/.ex/sA
reset; run ~/.ex/bad.conf ~/.ex/rcB; snap ~/.ex/sB
reset; touch ~/fleet/hosts/h4/.broken; run ~/.ex/good.conf ~/.ex/rcC; snap ~/.ex/sC
reset; touch ~/fleet/hosts/h1/.broken; run ~/.ex/good.conf ~/.ex/rcD; snap ~/.ex/sD
reset; snap ~/.ex/pristine
true
""",
    validate=r"""
E=/home/student/.ex
goodsum=$(sha256sum < $E/good.conf)
allgood=1
for h in h1 h2 h3 h4 h5 h6; do grep -qx "$h:$goodsum" $E/sA || allgood=0; done
chk good_rollout '[ "$(cat $E/rcA)" = 0 ] && [ "$allgood" = 1 ]'
chk invalid_blocked '[ "$(cat $E/rcB)" != 0 ] && cmp -s $E/sB $E/pristine'
chk rollback_on_failure '[ "$(cat $E/rcC)" != 0 ] && cmp -s $E/sC $E/pristine'
chk canary_failure '[ "$(cat $E/rcD)" != 0 ] && cmp -s $E/sD $E/pristine'
""",
    solution=r"""
cat > ~/bin/rollout.sh <<'EOT'
#!/bin/bash
new="$1"
FLEET="${FLEET:-$HOME/fleet/hosts}"
[ -f "$new" ] || { echo "config not found" >&2; exit 2; }
hosts=$(ls "$FLEET")
echo "plan: $hosts"
if ! ~/bin/validate_conf.sh "$new"; then
  echo "invalid config, nothing changed" >&2
  exit 1
fi
changed=()
rollback() {
  for h in "${changed[@]}"; do
    cp -p "$FLEET/$h/app.conf.bak" "$FLEET/$h/app.conf" && rm -f "$FLEET/$h/app.conf.bak"
  done
}
for h in $hosts; do
  cp -p "$FLEET/$h/app.conf" "$FLEET/$h/app.conf.bak"
  changed+=("$h")
  cp "$new" "$FLEET/$h/app.conf"
  if ! ~/bin/validate_conf.sh "$FLEET/$h/app.conf" || ! ~/bin/healthcheck.sh "$FLEET/$h"; then
    echo "host $h failed, rolling back" >&2
    rollback
    exit 1
  fi
done
rm -f "$FLEET"/*/app.conf.bak
EOT
""",
    wrong=r"""
cat > ~/bin/rollout.sh <<'EOT'
#!/bin/bash
for h in $(ls "${FLEET:-$HOME/fleet/hosts}"); do cp "$1" "${FLEET:-$HOME/fleet/hosts}/$h/app.conf"; done
EOT
""",
)
