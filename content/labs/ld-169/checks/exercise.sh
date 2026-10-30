mkdir -p ~/.ex
diff -r ~/data ~/restore/data > /dev/null 2>&1; echo $? > ~/.ex/diff.rc
true
