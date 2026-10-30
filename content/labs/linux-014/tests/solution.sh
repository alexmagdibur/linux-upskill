du -sk ~/disk/* | sort -rn | head -1 | cut -f2 > ~/biggest.txt
rm ~/disk/cache/*.cache.old
