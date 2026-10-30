mkdir -p ~/data
i=1
while [ $i -le 60 ]; do
  if [ $((i%5)) -eq 0 ]; then st=404; elif [ $((i%11)) -eq 0 ]; then st=500; else st=200; fi
  echo "192.168.1.$((i%7+1)) GET /p$((i%4)) $st"
  i=$((i+1))
done > ~/data/access.log
printf 'start\n' > ~/data/report.txt
