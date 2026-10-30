install -d /var/lib/lab
cat > /var/lib/lab/events.log <<'EOT'
02:00:05 backup_done
02:15:04 backup_done
02:30:06 backup_done
02:47:30 failure
02:55:10 restore_start
03:26:40 restore_done
EOT
