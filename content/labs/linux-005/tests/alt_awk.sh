awk '$3=="ERROR"' /var/log/app/app.log > ~/errors.txt
awk '$3=="ERROR"{split($4,a,"="); c[a[2]]++} END{for(k in c) print c[k], k}' /var/log/app/app.log | sort -rn | head -1 | cut -d' ' -f2 > ~/top_ip.txt
awk '$3=="WARN"{n++} END{print n}' /var/log/app/app.log > ~/warn_count.txt
