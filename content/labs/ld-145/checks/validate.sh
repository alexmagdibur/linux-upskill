chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
F=/home/student/ns.txt
v() { grep "^$1=" $F | cut -d= -f2- | tr -d ' '; }
chk all_four '( for k in pid mnt net user; do case "$(v $k)" in одинаковы|различаются) ;; *) exit 1;; esac; done )'
real=$(runuser -u student -- unshare --fork --pid --mount-proc --mount --net --user --map-root-user sh -c 'for n in pid mnt net user; do readlink /proc/self/ns/$n; done' | tr "\n" " ")
mine=$(for n in pid mnt net user; do readlink /proc/$$/ns/$n; done | tr "\n" " ")
chk values_right '[ "$real" != "$mine" ] && [ "$(for i in 1 2 3 4; do a=$(echo $real | cut -d" " -f$i); b=$(echo $mine | cut -d" " -f$i); [ "$a" = "$b" ] && echo одинаковы || echo различаются; done | sort -u)" = "различаются" ] && [ "$(v pid)$(v mnt)$(v net)$(v user)" = "различаютсяразличаютсяразличаютсяразличаются" ]'
