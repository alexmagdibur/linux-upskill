sudo rm -f /etc/ssh/sshd_config.d/00-legacy.conf
sudo tee /etc/ssh/sshd_config.d/10-baseline.conf > /dev/null <<'EOT'
PasswordAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
AllowUsers student
MaxAuthTries 3
LogLevel VERBOSE
X11Forwarding no
EOT
