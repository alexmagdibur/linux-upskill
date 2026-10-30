sudo rm -f /etc/sysctl.d/99-lab-ports.conf
echo 'net.ipv4.ip_local_port_range = 32768 60999' | sudo tee /etc/sysctl.d/10-ports.conf > /dev/null
sudo sysctl --system > /dev/null
