dpkg-query -W -f='${Package} ${Version}\n' 'lab*' | sort > ~/sbom.txt
