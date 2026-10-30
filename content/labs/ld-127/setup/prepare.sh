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
    return str(x)'
mkdeb labapp 1.0 'VERSION = "1.0"' labfmt
mkdeb labgdb-tools 1.0 'TOOLS = True'
mkdeb labdebug 1.0 'DEBUG = True' labgdb-tools
reindex
echo 'deb [trusted=yes] file:/srv/repo ./' > /etc/apt/sources.list.d/labrepo.list
apt-get update -qq 2>/dev/null
apt-get install -y -qq labapp labdebug >/dev/null
mkdir -p /etc/lab; printf 'allow: labapp labfmt\n' > /etc/lab/runtime-policy
