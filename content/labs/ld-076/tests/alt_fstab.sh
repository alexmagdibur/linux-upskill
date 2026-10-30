echo 'tmpfs /srv/labtmp tmpfs size=16M,mode=1777 0 0' | sudo tee -a /etc/fstab > /dev/null
sudo systemctl daemon-reload
sudo mount -a
