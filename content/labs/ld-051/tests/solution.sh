sudo sed -i 's#^WorkingDirectory=.*#WorkingDirectory=/opt/labapp/releases/1#' /etc/systemd/system/labapp.service
sudo systemctl daemon-reload
sudo systemctl restart labapp
sleep 7
