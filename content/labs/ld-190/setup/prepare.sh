install -d /opt/lab /var/lib/lab
cat > /opt/lab/job.sh <<'EOT'
#!/bin/bash
L="${LEDGER:-/var/lib/lab/ledger.txt}"
slot=$(date +%F-%H%M)
sleep 1
echo "run $slot" >> "$L"
EOT
chmod 755 /opt/lab/job.sh
printf '* * * * * root /opt/lab/job.sh\n' > /etc/cron.d/labjob
cat > /etc/systemd/system/labjob.service <<'EOT'
[Service]
Type=oneshot
ExecStart=/opt/lab/job.sh
EOT
cat > /etc/systemd/system/labjob.timer <<'EOT'
[Timer]
OnCalendar=minutely
[Install]
WantedBy=timers.target
EOT
systemctl daemon-reload
systemctl enable --now labjob.timer >/dev/null 2>&1
printf 'run 2026-10-29-0101\nrun 2026-10-29-0101\nrun 2026-10-29-0102\nrun 2026-10-29-0102\nrun 2026-10-29-0103\nrun 2026-10-29-0104\nrun 2026-10-29-0104\n' > /var/lib/lab/ledger.txt
