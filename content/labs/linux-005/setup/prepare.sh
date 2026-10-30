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
gen > /var/log/app/app.log
