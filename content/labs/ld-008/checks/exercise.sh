mkdir -p ~/.ex; rm -f ~/.ex/rc1 ~/.ex/rc2 ~/.ex/st1 ~/.ex/st2 ~/out/status.txt ~/out/sorted.txt
mv ~/in/input.txt ~/in/input.hold
timeout 8 bash ~/bin/report.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc1; cp ~/out/status.txt ~/.ex/st1 2>/dev/null
mv ~/in/input.hold ~/in/input.txt
rm -f ~/out/status.txt ~/out/sorted.txt
timeout 8 bash ~/bin/report.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rc2; cp ~/out/status.txt ~/.ex/st2 2>/dev/null
true
