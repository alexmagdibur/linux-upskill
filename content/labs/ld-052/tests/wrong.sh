for u in flaky broken; do
  sudo mkdir -p /etc/systemd/system/$u.service.d
  printf '[Unit]\nStartLimitIntervalSec=0\n\n[Service]\nRestart=always\nRestartSec=1\n' | sudo tee /etc/systemd/system/$u.service.d/restart.conf > /dev/null
done
sudo systemctl daemon-reload
