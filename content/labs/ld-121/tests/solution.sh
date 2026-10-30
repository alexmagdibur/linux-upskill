pkg=$(dpkg -S /usr/bin/jq | cut -d: -f1)
ver=$(dpkg-query -W -f='${Version}' "$pkg")
deps=$(dpkg-query -W -f='${Depends}' "$pkg" | sed 's/ ([^)]*)//g; s/, /,/g')
printf 'package=%s\nversion=%s\ndepends=%s\n' "$pkg" "$ver" "$deps" > ~/pkg.txt
