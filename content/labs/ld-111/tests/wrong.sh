sudo nft -f - <<'EOT'
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
    }
}
EOT
