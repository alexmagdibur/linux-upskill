mkdir -p ~/.ex; rm -f ~/.ex/r1 ~/.ex/r2
LC_ALL=C timeout 8 bash ~/bin/report.sh > ~/.ex/r1 2>/dev/null < /dev/null
LC_ALL=C.UTF-8 timeout 8 bash ~/bin/report.sh > ~/.ex/r2 2>/dev/null < /dev/null
true
