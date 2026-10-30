for n in pid mnt net user; do
  a=$(readlink /proc/self/ns/$n)
  b=$(unshare --fork --pid --mount-proc --mount --net --user --map-root-user readlink /proc/self/ns/$n)
  [ "$a" = "$b" ] && r=одинаковы || r=различаются
  echo "$n=$r"
done > ~/ns.txt
