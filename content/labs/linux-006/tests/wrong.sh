cut -d' ' -f1 ~/data/access.log | sort > ~/ips.txt
grep -c 404 ~/data/access.log > ~/count404.txt
echo done > ~/data/report.txt
ls /nonexistent > ~/err.txt
true
