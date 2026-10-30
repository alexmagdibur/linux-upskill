install -d -m 700 /srv/labsvc /srv/labsvc/data /srv/secret
echo "port=8080" > /srv/labsvc/app.conf; chmod 600 /srv/labsvc/app.conf
echo "TOP-SECRET" > /srv/secret/key; chmod 600 /srv/secret/key
