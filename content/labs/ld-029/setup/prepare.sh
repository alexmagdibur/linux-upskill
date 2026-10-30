groupadd labdev; groupadd labops
useradd -m -G labdev alice; useradd -m -G labops bob; useradd -m carol
install -d -m 755 /srv/shared
