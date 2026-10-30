sudo nft -f - <<'EOT'
table inet filter {
    chain input {
        type filter hook input priority 0; policy accept;
        ip saddr 10.86.0.0/24 ip daddr 169.254.169.254 tcp dport 80 drop
    }
}
EOT
