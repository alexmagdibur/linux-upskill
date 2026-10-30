sudo nft -f - <<'EOT'
flush table ip6 filter6
table ip6 filter6 {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        icmpv6 type { nd-neighbor-solicit, nd-neighbor-advert, nd-router-solicit, nd-router-advert, echo-request } accept
        ip6 saddr fd00:85::/64 tcp dport 8080 accept
        tcp dport 22 accept
    }
}
EOT
