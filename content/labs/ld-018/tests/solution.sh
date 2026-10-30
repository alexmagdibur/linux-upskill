cd ~/links && ln orig.txt hard && ln -s orig.txt soft
ino=$(stat -c %i orig.txt)
rm orig.txt
echo "inode=$ino; hard: данные сохранились; soft: битая ссылка" > report.txt
