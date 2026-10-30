cut=$(cat ~/cutoff.txt)
msg=$(sudo journalctl -u labcrash.service --since "$cut" -o cat | grep -m1 '^CRASH:')
boot=$(sudo journalctl -u labcrash.service --since "$cut" -o json | head -n 1 | python3 -c 'import sys, json; print(json.loads(sys.stdin.readline())["_BOOT_ID"])')
printf 'unit=labcrash.service\nmessage=%s\nboot=%s\n' "$msg" "$boot" > ~/first_failure.txt
