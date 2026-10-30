cd ~
rm -rf ~/backups ~/backups2 ~/.ex
mkdir -p ~/.ex
if [ -f ~/backup.sh ]; then
  timeout 8 bash ~/backup.sh ~/data ~/backups > ~/.ex/out1.txt 2>&1 < /dev/null; echo $? > ~/.ex/rc1.txt
  timeout 8 bash ~/backup.sh ~/no_such_dir ~/backups2 > ~/.ex/out2.txt 2>&1 < /dev/null; echo $? > ~/.ex/rc2.txt
fi
true
