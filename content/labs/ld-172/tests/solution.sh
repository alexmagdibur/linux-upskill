sudo sqlite3 /var/lib/labapp/orders.db ".backup '/var/backups/labapp/orders.bak'"
sudo cp /var/backups/labapp/orders.bak /var/lib/labapp/restored.db
sqlite3 /var/lib/labapp/restored.db "PRAGMA integrity_check"
