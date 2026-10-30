echo 'StrictModes no' | sudo tee /etc/ssh/sshd_config.d/99-weak.conf > /dev/null
sudo systemctl restart ssh
