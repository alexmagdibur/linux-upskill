cd ~/report && id -Gn > groups.txt && id -u > uid.txt && getent passwd 1001 | cut -d: -f1 > user1001.txt && getent group devs | cut -d: -f3 > gid_devs.txt
