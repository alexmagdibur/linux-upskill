sudo tee /etc/ssh/sshd_config.d/10-baseline.conf > /dev/null <<'EOT'
PasswordAuthentication no
PermitRootLogin no
EOT
