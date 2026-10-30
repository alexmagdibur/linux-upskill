sudo rm -f /var/lib/logrotate/status /var/log/lab/app.log.*
sleep 1
sudo logrotate -f /etc/logrotate.d/lablogger 2>/dev/null
sleep 2
sudo logrotate -f /etc/logrotate.d/lablogger 2>/dev/null
sleep 2
echo done > /tmp/.rotated
true
