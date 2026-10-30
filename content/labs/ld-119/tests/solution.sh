sudo sh -c 'cat /etc/lab/tls/leaf.crt /etc/lab/ca/inter.crt > /etc/lab/tls/fullchain.crt'
sudo sed -i 's#ssl_certificate /etc/lab/tls/leaf.crt;#ssl_certificate /etc/lab/tls/fullchain.crt;#' /etc/nginx/conf.d/app.conf
sudo nginx -t && sudo systemctl reload nginx
