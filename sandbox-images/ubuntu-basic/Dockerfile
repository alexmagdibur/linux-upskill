# Образ учебной песочницы Linux Upskill. Базовый образ зафиксирован по digest.
FROM ubuntu:24.04@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852

ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bash coreutils findutils grep sed gawk tar gzip bzip2 xz-utils procps less nano file \
      iproute2 python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/* /usr/share/doc/* /usr/share/man/* /var/cache/apt/* \
 # ubuntu:24.04 содержит пользователя ubuntu с uid 1000 — заменяем его на student
 && userdel -r ubuntu \
 && groupadd -g 2001 devs && groupadd -g 2002 ops \
 && useradd -m -u 1000 -U -s /bin/bash -G devs,ops student \
 && useradd -M -u 1001 -s /usr/sbin/nologin -G devs validator \
 # у образа не должно быть setuid/setgid-бинарников
 && find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

COPY bashrc /etc/skel-upskill-bashrc
RUN cat /etc/skel-upskill-bashrc >> /etc/bash.bashrc && rm /etc/skel-upskill-bashrc

USER student
WORKDIR /home/student
CMD ["/usr/bin/sleep", "infinity"]
