rm -rf ~/.ex; mkdir -p ~/.ex
for k in 1 2 3 4; do
  S=~/.ex/st$k
  STATE=$S FAIL_AT=$k timeout 8 bash ~/bin/migrate.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/f$k
  STATE=$S timeout 8 bash ~/bin/migrate.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/r$k
done
true
