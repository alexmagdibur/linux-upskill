mkdir -p ~/links
echo data > ~/links/orig.txt
stat -c %i ~/links/orig.txt > ~/.ref_inode
