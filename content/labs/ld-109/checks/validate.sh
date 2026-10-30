chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk rollback_saved 'nft -c -f /etc/lab/rollback.nft && grep -q "dport 22" /etc/lab/rollback.nft && ! grep -q "8443" /etc/lab/rollback.nft'
chk new_applied 'nft list ruleset | grep -q "dport 8443"'
chk ssh_kept 'nft list ruleset | grep -q "dport 22"'
chk draft_valid 'nft -c -f /etc/lab/new.nft'
