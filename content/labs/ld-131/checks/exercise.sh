rm -rf ~/.ex; mkdir -p ~/.ex/sA ~/.ex/sB ~/.ex/sC "$HOME/.ex/target dir"
echo x > ~/.ex/sA/keep; echo x > ~/.ex/sB/keep; echo x > ~/.ex/sC/keep
echo 1 > "$HOME/.ex/target dir/f1"; echo 2 > "$HOME/.ex/target dir/.hidden"
( cd ~/.ex/sA && DIR= timeout 8 bash ~/bin/cleanup.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rcA )
( cd ~/.ex/sB && DIR=/nonexistent_dir_xyz timeout 8 bash ~/bin/cleanup.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rcB )
( cd ~/.ex/sC && DIR="$HOME/.ex/target dir" timeout 8 bash ~/bin/cleanup.sh > /dev/null 2>&1 < /dev/null; echo $? > ~/.ex/rcC )
true
