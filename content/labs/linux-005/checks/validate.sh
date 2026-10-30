chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; fi; }
gen() {
  i=1
  while [ $i -le 120 ]; do
    if [ $((i%6)) -eq 0 ]; then
      lvl=ERROR
      if [ $((i%18)) -eq 0 ]; then ip=10.0.0.9; else ip=10.0.0.2; fi
    elif [ $((i%6)) -eq 3 ]; then lvl=WARN; ip=10.0.1.$((i%3+1))
    else lvl=INFO; ip=10.0.2.$((i%5+1)); fi
    printf '2026-10-30 10:%02d:%02d %s client=%s msg="request %d"\n' $((i/60)) $((i%60)) $lvl $ip $i
    i=$((i+1))
  done
}
H=/home/student
chk errors_file '[ "$(sort $H/errors.txt)" = "$(gen | grep " ERROR " | sort)" ]'
chk top_ip '[ "$(tr -d "[:space:]" < $H/top_ip.txt)" = 10.0.0.2 ]'
chk warn_count '[ "$(tr -d "[:space:]" < $H/warn_count.txt)" = "$(gen | grep -c " WARN ")" ]'
