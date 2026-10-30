mv /etc/apt/sources.list.d/ubuntu.sources /root/ubuntu.sources.off 2>/dev/null || true
mkdir -p /srv/repo
mkdeb() { # имя версия содержимое-модуля [зависимости]
  d=$(mktemp -d); mkdir -p $d/DEBIAN $d/usr/lib/python3/dist-packages
  printf 'Package: %s\nVersion: %s\nArchitecture: all\nMaintainer: Lab <lab@example.com>\nDescription: lab package %s\n' "$1" "$2" "$1" > $d/DEBIAN/control
  [ -n "${4:-}" ] && printf 'Depends: %s\n' "$4" >> $d/DEBIAN/control
  printf '%s\n' "$3" > $d/usr/lib/python3/dist-packages/$1.py
  dpkg-deb --build -Zgzip $d /srv/repo/${1}_${2}_all.deb >/dev/null; rm -rf $d
}
reindex() { (cd /srv/repo && dpkg-scanpackages --multiversion . /dev/null > Packages 2>/dev/null && gzip -kf Packages); }

mkdeb labtool 1.0 'VERSION = "1.0"'
reindex
export GNUPGHOME=$(mktemp -d)
cat > /tmp/gk <<'EOT'
%no-protection
Key-Type: RSA
Key-Length: 2048
Name-Real: Lab Repo
Name-Email: repo@lab.example
Expire-Date: 0
%commit
EOT
gpg --batch --gen-key /tmp/gk 2>/dev/null
(cd /srv/repo && apt-ftparchive release . > Release && gpg --batch --yes --clearsign -o InRelease Release && gpg --batch --yes -abs -o Release.gpg Release)
gpg --armor --export repo@lab.example > /srv/repo/key.asc
rm -rf "$GNUPGHOME" /tmp/gk
chmod -R a+rX /srv/repo
