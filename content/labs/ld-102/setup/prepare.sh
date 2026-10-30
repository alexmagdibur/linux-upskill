echo 'net.ipv4.ip_local_port_range = 40000 40003' > /etc/sysctl.d/99-lab-ports.conf
sysctl -q -p /etc/sysctl.d/99-lab-ports.conf
