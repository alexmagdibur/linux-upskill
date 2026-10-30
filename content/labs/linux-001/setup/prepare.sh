mkdir -p ~/lab/docs ~/lab/src/app ~/lab/src/lib ~/lab/data/archive
echo "# Учебный проект" > ~/lab/docs/README.md
echo "Заметки по релизу" > ~/lab/docs/release.txt
printf '[server]\nport=8080\n' > ~/lab/src/app/config.ini
echo 'print("hello")' > ~/lab/src/app/main.py
echo 'def util(): pass' > ~/lab/src/lib/util.py
printf 'id,value\n1,10\n2,20\n' > ~/lab/data/archive/old.csv
