L=/var/log/app/app.log
grep ERROR $L > ~/errors.txt
grep ERROR $L | grep -o 'client=[0-9.]*' | cut -d= -f2 | sort | uniq -c | sort -rn | head -1 | awk '{print $2}' > ~/top_ip.txt
grep -c WARN $L > ~/warn_count.txt
