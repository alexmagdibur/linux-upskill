sudo systemctl stop flaky broken 2>/dev/null
sudo systemctl reset-failed flaky broken 2>/dev/null
sudo rm -f /var/lib/lab/flaky.count
sudo systemctl daemon-reload
sudo systemctl start flaky broken 2>/dev/null
sleep 9
true
