msg=$(sudo journalctl -u labcrash.service -o cat | grep -m1 '^CRASH:')
printf 'unit=labcrash.service\nmessage=%s\nboot=unknown\n' "$msg" > ~/first_failure.txt
