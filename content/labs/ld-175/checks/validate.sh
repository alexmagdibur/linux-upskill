chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
chk files_restored '[ "$(wc -l < /var/backups/vol/MANIFEST.sha256)" = 6 ] && ( while read -r s f; do [ -f "/srv/vol/$f" ] || exit 1; done < /var/backups/vol/MANIFEST.sha256 )'
chk checksums_ok '(cd /srv/vol && sha256sum -c /var/backups/vol/MANIFEST.sha256 >/dev/null 2>&1)'
chk backup_untouched 'sha256sum -c /root/.vol.ref >/dev/null 2>&1'
