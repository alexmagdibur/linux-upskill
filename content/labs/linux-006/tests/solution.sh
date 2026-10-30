cd ~/data
cut -d' ' -f1 access.log | sort -u > ~/ips.txt
grep -c ' 404$' access.log > ~/count404.txt
echo done >> report.txt
ls /nonexistent 2> ~/err.txt
true
