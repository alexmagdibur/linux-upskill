chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
P=/home/student/perm
m() { stat -c %a "$1"; }
chk script_exec '[ $(( 0$(m $P/script.sh) & 0100 )) -ne 0 ] && [ $(( 0$(m $P/script.sh) & 0022 )) -eq 0 ]'
chk secret_mode '[ "$(m $P/secret.txt)" = 600 ]'
chk public_mode '[ "$(m $P/public.txt)" = 644 ]'
chk shared_mode '[ "$(m $P/shared)" = 755 ]'
