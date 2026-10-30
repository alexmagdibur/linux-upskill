sudo tee /etc/systemd/system/srv-labtmp.mount > /dev/null <<'EOT'
[Unit]
Description=Lab tmpfs

[Mount]
What=tmpfs
Where=/srv/labtmp
Type=tmpfs
Options=size=16M,mode=1777

[Install]
WantedBy=multi-user.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now srv-labtmp.mount
