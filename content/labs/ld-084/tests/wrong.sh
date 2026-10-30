sudo mkdir -p /etc/systemd/system/labbatch.service.d
printf '[Service]\nNice=15\n' | sudo tee /etc/systemd/system/labbatch.service.d/nice.conf > /dev/null
sudo systemctl daemon-reload
sudo systemctl restart labbatch
