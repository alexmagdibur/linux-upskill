mkdir -p ~/.ex/src; echo data > ~/.ex/src/f.txt
rm -f ~/.ex/out.tar.gz ~/.ex/x.tar.gz
if [ -f ~/bin/arch.sh ]; then
  timeout 8 bash ~/bin/arch.sh -h > ~/.ex/h.out 2> ~/.ex/h.err < /dev/null; echo $? > ~/.ex/h.rc
  timeout 8 bash ~/bin/arch.sh > ~/.ex/n.out 2> ~/.ex/n.err < /dev/null; echo $? > ~/.ex/n.rc
  timeout 8 bash ~/bin/arch.sh ~/.ex/src ~/.ex/out.tar.gz > ~/.ex/ok.out 2> ~/.ex/ok.err < /dev/null; echo $? > ~/.ex/ok.rc
  timeout 8 bash ~/bin/arch.sh ~/.ex/nosuch ~/.ex/x.tar.gz > ~/.ex/m.out 2> ~/.ex/m.err < /dev/null; echo $? > ~/.ex/m.rc
fi
true
