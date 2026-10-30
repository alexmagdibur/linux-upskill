cd /etc/lab/tls
sudo openssl req -new -newkey rsa:2048 -nodes -keyout app.key -out /tmp/app.csr -subj /CN=app.lab.test 2>/dev/null
sudo sh -c "printf 'subjectAltName=DNS:app.lab.test' > /tmp/san.ext"
sudo openssl x509 -req -in /tmp/app.csr -CA /etc/lab/ca/ca.crt -CAkey /etc/lab/ca/ca.key -CAcreateserial -days 30 -extfile /tmp/san.ext -out app.crt 2>/dev/null
sudo chmod 600 app.key
sudo systemctl reload nginx
