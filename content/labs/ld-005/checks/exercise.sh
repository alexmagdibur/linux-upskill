mkdir -p ~/.ex; rm -f ~/.ex/a ~/.ex/b
[ -f ~/run.sh ] || exit 0
TRACE=~/.ex/a timeout 8 bash ~/run.sh > /dev/null 2>&1 < /dev/null
FAIL_FIRST=1 TRACE=~/.ex/b timeout 8 bash ~/run.sh > /dev/null 2>&1 < /dev/null
true
