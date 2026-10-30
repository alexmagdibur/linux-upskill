mkdir -p /srv/data
mount -t tmpfs -o size=8m tmpfs /srv/data
echo "keep-me" > /srv/data/marker.txt
mount -o remount,ro /srv/data
