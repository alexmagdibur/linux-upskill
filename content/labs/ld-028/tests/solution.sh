sudo useradd --system --no-create-home --shell /usr/sbin/nologin labsvc
sudo chown root:labsvc /srv/labsvc /srv/labsvc/app.conf
sudo chmod 750 /srv/labsvc
sudo chmod 640 /srv/labsvc/app.conf
sudo chown labsvc:labsvc /srv/labsvc/data
sudo chmod 750 /srv/labsvc/data
