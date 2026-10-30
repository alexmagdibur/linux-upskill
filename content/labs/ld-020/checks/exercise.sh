mkdir -p ~/.ex
diff -r ~/src ~/dst > /dev/null 2>&1; echo $? > ~/.ex/diff.rc
true
