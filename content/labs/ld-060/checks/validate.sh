chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
sleep 2
chk logging_again 'now=$(date +%s); last=$(tail -n 1 /var/log/labapp/app.log | awk "{print \$2}"); [ -n "$last" ] && [ $((now - last)) -le 5 ]'
chk space_free '[ "$(df -k --output=avail /var/log/labapp | tail -n 1 | tr -d " ")" -ge 1024 ] && grep -q boot-record /var/log/labapp/app.log'
chk rotation_configured 'f=/etc/logrotate.d/labapp; [ -f $f ] && grep -q "rotate" $f && grep -q "compress" $f && grep -Eq "size|daily|weekly|monthly" $f && logrotate -d $f >/dev/null 2>&1'
