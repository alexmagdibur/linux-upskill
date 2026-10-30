for u in flaky broken; do
  sudo mkdir -p /etc/systemd/system/$u.service.d
  printf '[Unit]\nStartLimitIntervalSec=30\nStartLimitBurst=4\n\n[Service]\nRestart=on-failure\nRestartSec=1\n' | sudo tee /etc/systemd/system/$u.service.d/restart.conf > /dev/null
done
sudo systemctl daemon-reload
