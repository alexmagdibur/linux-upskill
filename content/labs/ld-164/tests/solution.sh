bad=$(sudo sha256sum -c /var/lib/lab/baseline.sha256 2>/dev/null | grep -v ': OK' | cut -d: -f1)
echo "$bad" > ~/tampered.txt
sudo cp /var/backups/lab/$(basename "$bad") "$bad"
