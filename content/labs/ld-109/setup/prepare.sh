install -d /etc/lab
nft flush ruleset
nft -f - <<'EOT'
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        tcp dport 22 accept
    }
}
EOT
cat > /etc/lab/new.nft <<'EOT'
flush ruleset
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        tcp dport 22 accept
        tcp dport 8443 acept
    }
}
EOT
