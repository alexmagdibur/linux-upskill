for u in crit batch; do
cat > /etc/systemd/system/lab$u.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 -c "while True: pass"
[Install]
WantedBy=multi-user.target
EOT
done
systemctl daemon-reload
systemctl enable --now labcrit labbatch >/dev/null 2>&1
