mkdir -p ~/evidence
sudo cp /usr/local/lib/.upd/agent.sh ~/evidence/agent.sh
sudo cp /etc/cron.d/sysupdate ~/evidence/sysupdate
sudo chown -R student:student ~/evidence
sudo pkill -f '.upd/agent.sh'
sudo rm -f /etc/cron.d/sysupdate
sudo rm -rf /usr/local/lib/.upd
