useradd -m -s /bin/bash labuser
passwd -l labuser >/dev/null
printf 'PasswordAuthentication no\nPubkeyAuthentication yes\nListenAddress 127.0.0.1\n' > /etc/ssh/sshd_config.d/10-lab.conf
mkdir -p /run/sshd; ssh-keygen -A >/dev/null
su - student -c "ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q; ssh-keyscan -t ed25519 127.0.0.1 2>/dev/null > ~/.ssh/known_hosts" 2>/dev/null || true
mkdir -p /home/labuser/.ssh
cp /home/student/.ssh/id_ed25519.pub /home/labuser/.ssh/authorized_keys
chown -R labuser:labuser /home/labuser
chmod 777 /home/labuser; chmod 777 /home/labuser/.ssh; chmod 666 /home/labuser/.ssh/authorized_keys
systemctl enable --now ssh >/dev/null 2>&1
sleep 1
