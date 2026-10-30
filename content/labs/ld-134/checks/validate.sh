chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex
want="$(printf 'step1\nstep2\nstep3\nstep4')"
ok=1
for k in 1 2 3 4; do [ "$(sort $E/st$k/ledger.txt 2>/dev/null)" = "$want" ] || ok=0; done
chk recovers_all_steps '[ "$ok" = 1 ]'
codes=1
for k in 1 2 3 4; do [ "$(cat $E/f$k)" != 0 ] && [ "$(cat $E/r$k)" = 0 ] || codes=0; done
chk exit_codes '[ "$codes" = 1 ]'
