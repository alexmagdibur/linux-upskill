T=/tmp/ledger.test
sudo rm -f $T
sudo systemctl set-environment LEDGER=$T
cronline=$(grep -hv '^#' /etc/cron.d/labjob 2>/dev/null | awk 'NF>6{ $1=$2=$3=$4=$5=$6=""; print }')
if [ -n "$cronline" ]; then sudo env LEDGER=$T bash -c "$cronline" & fi
if systemctl is-active --quiet labjob.timer || systemctl is-enabled --quiet labjob.timer 2>/dev/null; then sudo systemctl start labjob.service & fi
wait
sudo systemctl unset-environment LEDGER
true
