echo 'oper ALL=(root) NOPASSWD: /usr/bin/systemctl restart labsvc.service' | sudo tee /etc/sudoers.d/oper > /dev/null
sudo chmod 440 /etc/sudoers.d/oper
sudo visudo -c
