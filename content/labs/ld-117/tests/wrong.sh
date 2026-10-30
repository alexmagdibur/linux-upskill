cd /etc/lab/tls
sudo openssl req -x509 -newkey rsa:2048 -nodes -keyout app.key -out app.crt -days 30 -subj /CN=app.lab.test 2>/dev/null
sudo systemctl reload nginx
