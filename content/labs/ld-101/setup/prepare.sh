printf 'port=5353\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\n' > /etc/dnsmasq.d/00-base.conf
systemctl enable --now dnsmasq >/dev/null 2>&1
