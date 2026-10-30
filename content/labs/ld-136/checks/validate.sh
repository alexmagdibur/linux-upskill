chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
E=/home/student/.ex
goodsum=$(sha256sum < $E/good.conf)
allgood=1
for h in h1 h2 h3 h4 h5 h6; do grep -qx "$h:$goodsum" $E/sA || allgood=0; done
chk good_rollout '[ "$(cat $E/rcA)" = 0 ] && [ "$allgood" = 1 ]'
chk invalid_blocked '[ "$(cat $E/rcB)" != 0 ] && cmp -s $E/sB $E/pristine'
chk rollback_on_failure '[ "$(cat $E/rcC)" != 0 ] && cmp -s $E/sC $E/pristine'
chk canary_failure '[ "$(cat $E/rcD)" != 0 ] && cmp -s $E/sD $E/pristine'
