mkdir -p ~/disk/cache ~/disk/logs ~/disk/media
i=1; while [ $i -le 6 ]; do dd if=/dev/zero of=$HOME/disk/cache/blob$i.cache.old bs=1M count=1 2>/dev/null; i=$((i+1)); done
i=1; while [ $i -le 3 ]; do dd if=/dev/zero of=$HOME/disk/logs/app$i.log bs=1M count=1 2>/dev/null; i=$((i+1)); done
dd if=/dev/zero of=$HOME/disk/media/video1.bin bs=1M count=1 2>/dev/null
dd if=/dev/zero of=$HOME/disk/media/video2.bin bs=1M count=1 2>/dev/null
