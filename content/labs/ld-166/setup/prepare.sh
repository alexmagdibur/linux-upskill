install -d /usr/local/lib/.upd /var/lib/lab
cat > /usr/local/lib/.upd/agent.sh <<'EOT'
#!/bin/bash
# system update helper
while true; do sleep 30; done
EOT
chmod 755 /usr/local/lib/.upd/agent.sh
printf '@reboot root /usr/local/lib/.upd/agent.sh >/dev/null 2>&1 &\n' > /etc/cron.d/sysupdate
sha256sum /usr/local/lib/.upd/agent.sh /etc/cron.d/sysupdate > /var/lib/lab/ref.sha256
( setsid nohup /usr/local/lib/.upd/agent.sh >/dev/null 2>&1 </dev/null & )
sleep 1
