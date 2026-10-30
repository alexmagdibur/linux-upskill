chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
L=/home/student/app/app.log
chk starts_ok 'grep -qx "app started mode=production" $L'
chk reads_real_config 'grep -qx "app started mode=canary" $L'
chk config_intact 'grep -qx "MODE=production" /etc/myapp/app.conf && grep -qx "LEVEL=info" /etc/myapp/app.conf'
