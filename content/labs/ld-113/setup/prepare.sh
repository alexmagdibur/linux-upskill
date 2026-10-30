useradd -m -s /bin/bash labuser
passwd -l labuser >/dev/null
printf 'PasswordAuthentication no\nPubkeyAuthentication yes\nListenAddress 127.0.0.1\n' > /etc/ssh/sshd_config.d/10-lab.conf
mkdir -p /run/sshd
ssh-keygen -A >/dev/null
systemctl enable --now ssh >/dev/null 2>&1
sleep 1
