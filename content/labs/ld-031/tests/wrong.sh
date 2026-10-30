echo 'oper ALL=(ALL) NOPASSWD: ALL' | sudo tee /etc/sudoers.d/oper > /dev/null
sudo chmod 440 /etc/sudoers.d/oper
