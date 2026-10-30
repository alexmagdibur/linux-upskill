mkdir -p ~/.ex; rm -f ~/.ex/g1 ~/.ex/g2 ~/.ex/g3 ~/.ex/g4
[ -f ~/lib/safe.sh ] || exit 0
i=0
for name in "my dir" 'a*b' '-dash' 'plain'; do
  i=$((i+1))
  timeout 5 bash -c 'source ~/lib/safe.sh; godir "$1"; pwd' _ "$name" > ~/.ex/g$i 2>&1 < /dev/null
done
true
