#!/bin/bash
# Сборка базового образа учебных машин `upskill-ubuntu-systemd` на VM-хосте (sudo bash build-base.sh).
# Образ: Ubuntu 24.04 + systemd + инструменты диагностики, пользователь student (uid 1000, sudo без пароля внутри
# изолированного контейнера), без cloud-init. Результат — alias и fingerprint образа (печатается в конце).
set -euo pipefail

NAME=upskill-build
ALIAS=upskill-ubuntu-systemd
POOL="${LXD_POOL:-fast}"

lxc delete -f "$NAME" >/dev/null 2>&1 || true
lxc launch ubuntu:24.04 "$NAME" -s "$POOL" </dev/null
for i in $(seq 1 90); do
  s=$(lxc exec "$NAME" -- systemctl is-system-running </dev/null 2>/dev/null || true)
  [ "$s" = running ] || [ "$s" = degraded ] && break
  sleep 1
done
# сеть для apt (на этапе сборки используется обычный lxdbr0 с выходом наружу)
for i in $(seq 1 30); do lxc exec "$NAME" -- getent hosts archive.ubuntu.com >/dev/null </dev/null 2>&1 && break; sleep 1; done

lxc exec "$NAME" -- bash -s <<'EOS'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  sudo cron rsyslog logrotate iproute2 iputils-ping nftables iptables curl ca-certificates dnsutils tcpdump strace lsof \
  psmisc procps net-tools less nano vim-tiny python3 tar gzip bzip2 xz-utils file acl attr at openssh-client \
  netcat-openbsd util-linux gawk sed findutils grep coreutils bc jq tree \
  nginx-light dnsmasq openssl gcc libc6-dev make dpkg-dev gnupg sqlite3 sysstat traceroute conntrack ethtool inotify-tools rsync \
  ansible-core openssh-server needrestart
# готовим пользователя: ubuntu (uid 1000) заменяем на student
userdel -r ubuntu 2>/dev/null || true
useradd -m -u 1000 -s /bin/bash student
echo 'student ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/student
chmod 440 /etc/sudoers.d/student
echo upskill > /etc/hostname
sed -i 's/^127.0.1.1.*/127.0.1.1 upskill/' /etc/hosts || true
# быстрая загрузка: без cloud-init и ненужных служб
touch /etc/cloud/cloud-init.disabled
systemctl disable --now motd-news.timer apt-daily.timer apt-daily-upgrade.timer 2>/dev/null || true
systemctl mask snapd.service 2>/dev/null || true
systemctl disable nginx dnsmasq ssh 2>/dev/null || true  # задания включают нужные службы сами
apt-get clean
rm -rf /var/lib/apt/lists/* /var/cache/apt/* /usr/share/doc/* /usr/share/man/*
EOS

lxc stop "$NAME" </dev/null
lxc image delete "$ALIAS" >/dev/null 2>&1 || true
lxc publish "$NAME" --alias "$ALIAS" </dev/null >/dev/null
lxc delete -f "$NAME" </dev/null
fp=$(lxc image info "$ALIAS" </dev/null | awk '/^Fingerprint:/{print $2}')
echo "IMAGE_ALIAS=$ALIAS"
echo "IMAGE_FINGERPRINT=$fp"
