ping -c1 -W2 10.50.1.2 >/dev/null
src=$(ip route get 10.50.1.2 | grep -o 'src [0-9.]*' | cut -d' ' -f2)
dev=$(ip route get 10.50.1.2 | grep -o 'dev [a-z0-9]*' | cut -d' ' -f2)
via=$(ip route get 10.50.9.5 | grep -o 'via [0-9.]*' | cut -d' ' -f2)
mac=$(ip neigh show 10.50.1.2 | awk '{print $5}')
printf 'src=%s\ndev=%s\nvia=%s\nmac=%s\n' "$src" "$dev" "$via" "$mac" > ~/path.txt
