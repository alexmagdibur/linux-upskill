chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
inst=$(dpkg-query -W -f='${Package} ${Version}\n' 'lab*' 2>/dev/null | sort)
chk extras_removed '! dpkg -s labdebug 2>/dev/null | grep -q "^Status: install ok installed" && ! dpkg -s labgdb-tools 2>/dev/null | grep -q "^Status: install ok installed"'
chk required_kept 'dpkg -s labapp 2>/dev/null | grep -q "install ok installed" && dpkg -s labfmt 2>/dev/null | grep -q "install ok installed"'
chk sbom_ok '[ -n "$inst" ] && [ "$(sort /home/student/sbom.txt)" = "$inst" ] && [ "$(cat /home/student/sbom.txt)" = "$(sort /home/student/sbom.txt)" ]'
