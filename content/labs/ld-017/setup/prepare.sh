mkdir -p ~/tree/data ~/tree/cache ~/tree/old
truncate -s 2M ~/tree/data/big_recent.bin
truncate -s 2M ~/tree/cache/big_cached.bin
truncate -s 2M ~/tree/old/big_old.bin; touch -d '5 days ago' ~/tree/old/big_old.bin
truncate -s 100K ~/tree/data/small_recent.bin
