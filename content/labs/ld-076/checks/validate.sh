chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk mounted_tmpfs '[ "$(findmnt -n -o FSTYPE /srv/labtmp 2>/dev/null)" = tmpfs ]'
chk size_limited '[ "$(findmnt -n -o SIZE /srv/labtmp 2>/dev/null | tr -d " ")" = 16M ] && ! dd if=/dev/zero of=/srv/labtmp/big bs=1M count=20 2>/dev/null'
chk cleaned_on_reboot '[ ! -e /srv/labtmp/marker.txt ]'
rm -f /srv/labtmp/big
