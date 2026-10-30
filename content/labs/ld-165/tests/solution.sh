echo 'DB_PASSWORD=S3cr3tPass' | sudo tee /etc/lab/secrets.env > /dev/null
sudo chmod 600 /etc/lab/secrets.env
sudo tee /etc/systemd/system/labsecret.service > /dev/null <<'EOT'
[Service]
EnvironmentFile=/etc/lab/secrets.env
ExecStart=/usr/bin/python3 /opt/lab/secapp.py --user=db
[Install]
WantedBy=multi-user.target
EOT
sudo systemctl daemon-reload
