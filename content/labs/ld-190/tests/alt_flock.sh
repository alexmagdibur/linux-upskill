sudo tee /opt/lab/job.sh > /dev/null <<'EOT'
#!/bin/bash
L="${LEDGER:-/var/lib/lab/ledger.txt}"
slot=$(date +%F-%H%M)
exec 9>/var/lock/labjob.lock
flock 9
grep -qx "run $slot" "$L" 2>/dev/null && exit 0
sleep 1
echo "run $slot" >> "$L"
EOT
sudo sort -u -o /var/lib/lab/ledger.txt /var/lib/lab/ledger.txt
