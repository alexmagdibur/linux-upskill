sudo tail -n 3 /var/log/nginx/error.log
echo refused > ~/cause.txt
sudo sed -i 's#127.0.0.1:9001#127.0.0.1:9000#' /etc/nginx/conf.d/api.conf
sudo systemctl reload nginx
