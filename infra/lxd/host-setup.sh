#!/bin/bash
# Идемпотентная подготовка VM-хоста для учебных LXD-машин (запускается на VM от root: sudo bash host-setup.sh).
#  - профиль `upskill-lab` без сетевых устройств (сеть добавляется отдельной изолированной сетью на каждую сессию);
#  - firewall-таблица `inet upskill_lab`: учебные сети (lab*) НЕ видят хост, LAN, интернет и друг друга за пределами своего моста;
#  - systemd-юнит, который грузит правила при старте.
set -euo pipefail

POOL="${LXD_POOL:-fast}"

if ! lxc profile show upskill-lab >/dev/null 2>&1; then
  lxc profile create upskill-lab
fi
lxc profile edit upskill-lab <<EOF
description: Linux Upskill — учебная машина без сети по умолчанию, с жёсткими лимитами
config:
  boot.autostart: "false"
  security.privileged: "false"
  security.nesting: "false"
  limits.cpu: "1"
  limits.memory: 512MiB
  limits.memory.swap: "false"
  limits.processes: "512"
devices:
  root:
    path: /
    pool: ${POOL}
    size: 3GiB
    type: disk
EOF

install -d /etc/upskill
cat > /etc/upskill/lab-firewall.nft <<'EOF'
# Правила применяются ДО правил LXD (priority -5); drop в любой цепочке окончателен.
table inet upskill_lab
delete table inet upskill_lab
table inet upskill_lab {
  chain input {
    type filter hook input priority -5; policy accept;
    # учебная машина может только получить адрес по DHCP — больше ничего на хосте ей недоступно
    iifname "lab*" udp dport 67 accept
    iifname "lab*" drop
  }
  chain forward {
    type filter hook forward priority -5; policy accept;
    # никакой маршрутизации из учебных сетей наружу и в них (внутри одного моста — L2, нужный для multi-node)
    iifname "lab*" drop
    oifname "lab*" drop
  }
  chain output {
    type filter hook output priority -5; policy accept;
    # хост сам не инициирует соединения в учебные сети (кроме DHCP-ответов)
    oifname "lab*" udp sport 67 accept
    oifname "lab*" ct state established,related accept
    oifname "lab*" drop
  }
}
EOF

cat > /etc/systemd/system/upskill-lab-firewall.service <<'EOF'
[Unit]
Description=Linux Upskill lab network isolation
After=network-pre.target
Before=network.target snap.lxd.daemon.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nft -f /etc/upskill/lab-firewall.nft
ExecStop=/usr/sbin/nft delete table inet upskill_lab

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable upskill-lab-firewall.service >/dev/null 2>&1
systemctl restart upskill-lab-firewall.service
nft list table inet upskill_lab | head -30
echo "host-setup ok"
