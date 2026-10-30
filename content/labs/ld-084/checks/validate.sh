chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
u1=0; u2=0
systemctl stop labcrit
cg=/sys/fs/cgroup/system.slice/labbatch.service
u1=$(awk '/^usage_usec/{print $2}' $cg/cpu.stat); sleep 4; u2=$(awk '/^usage_usec/{print $2}' $cg/cpu.stat)
share=$(( (u2 - u1) / 40000 ))   # проценты одного ядра за 4 секунды
systemctl start labcrit
chk batch_capped '[ "$share" -le 30 ]'
chk batch_nice '[ "$(systemctl show -p Nice --value labbatch)" -gt 0 ]'
chk crit_untouched 'systemctl is-active --quiet labcrit && [ "$(systemctl show -p CPUQuotaPerSecUSec --value labcrit)" = infinity ]'
