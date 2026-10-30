install -d /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=volatile\n' > /etc/systemd/journald.conf.d/00-lab.conf
rm -rf /var/log/journal
systemctl restart systemd-journald
