mkdir -p /run/sshd
printf 'PasswordAuthentication yes\nPermitRootLogin yes\nMaxAuthTries 10\nX11Forwarding yes\n' > /etc/ssh/sshd_config.d/00-legacy.conf
