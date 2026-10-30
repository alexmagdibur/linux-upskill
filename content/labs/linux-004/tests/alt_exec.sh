find ~/projects -type f -name '*.conf' -print | sort > ~/found_conf.txt
find ~/projects -type f -size 0 -exec rm {} \;
