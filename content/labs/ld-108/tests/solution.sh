sudo sysctl -w net.ipv4.ip_forward=1
sudo nft -f - <<'EOT'
table ip nat {
    chain prerouting {
        type nat hook prerouting priority -100; policy accept;
        tcp dport 8080 dnat to 10.84.2.2:80
    }
}
EOT
