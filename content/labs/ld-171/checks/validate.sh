chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
tar -tzf /var/backups/labapp2/latest.tar.gz > /tmp/.l2 2>/dev/null
chk db_included 'grep -q "var/lib/labapp2/db/main.db" /tmp/.l2'
chk uploads_included 'grep -q "var/lib/labapp2/uploads/photo.jpg" /tmp/.l2'
chk config_included 'grep -q "etc/labapp2/app.conf" /tmp/.l2'
chk tmp_excluded '[ -s /tmp/.l2 ] && ! grep -q "\.tmp$" /tmp/.l2'
