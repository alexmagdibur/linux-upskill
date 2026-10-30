sudo tee /etc/nftables.conf > /dev/null <<'EOT'
#!/usr/sbin/nft -f
flush ruleset
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        icmp type echo-request accept
        ip saddr 10.81.1.0/24 tcp dport 22 accept
        ip saddr 10.81.2.0/24 tcp dport 80 accept
    }
}
EOT
sudo nft -f /etc/nftables.conf
