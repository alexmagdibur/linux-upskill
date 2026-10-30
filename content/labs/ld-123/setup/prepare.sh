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

mkdeb labfmt 1.0 'def render(x):
    return "[" + str(x) + "]"'
mkdeb labfmt 2.0 'def format_value(x):
    return "<" + str(x) + ">"'
reindex
echo 'deb [trusted=yes] file:/srv/repo ./' > /etc/apt/sources.list.d/labrepo.list
apt-get update -qq 2>/dev/null
apt-get install -y -qq labfmt=1.0 >/dev/null
install -d /opt/lab
cat > /opt/lab/fmtapp.py <<'EOT'
import time
import labfmt
while True:
    labfmt.render("ok")
    time.sleep(1)
EOT
cat > /etc/systemd/system/labapp.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/fmtapp.py
Restart=on-failure
RestartSec=1
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable labapp >/dev/null 2>&1
apt-get install -y -qq labfmt=2.0 >/dev/null
systemctl restart labapp
sleep 2
