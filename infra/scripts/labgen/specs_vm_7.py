"""Задания на учебной машине (LXD), партия 7: многоузловые сценарии на network namespace и локальных службах
(асимметричная маршрутизация, DNS-кэш, keep-alive, bastion/ProxyJump, port forwarding, rolling update, ротация TLS за балансировщиком)."""

from __future__ import annotations

from specs_vm_5 import NODE, NSNOTE, NSX

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append({"runtime_type": "lxd", **kw})


# Узлы Ansible: три экземпляра службы labnode@N (порты 8101..8103), версия в /etc/labnode/N.version,
# /health отвечает 200 только после «прогрева» (3 с после старта).
NODES = r"""
install -d /opt/lab /etc/labnode /var/lib/lab
cat > /opt/lab/labnode.py <<'EOT'
import http.server, socketserver, sys, time
n = sys.argv[1]
started = time.time()
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        ver = open("/etc/labnode/%s.version" % n).read().strip()
        if self.path == "/health" and time.time() - started < 3:
            self.send_response(503); self.send_header("Content-Length", "0"); self.end_headers(); return
        body = (ver + "\n").encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a):
        pass
socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", 8100 + int(n)), H).serve_forever()
EOT
cat > /etc/systemd/system/labnode@.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/labnode.py %i
[Install]
WantedBy=multi-user.target
EOT
for n in 1 2 3; do echo v1 > /etc/labnode/$n.version; done
systemctl daemon-reload
systemctl enable --now labnode@1 labnode@2 labnode@3 >/dev/null 2>&1
sleep 4
"""
NODES_INV = r"""
mkdir -p /home/student/ansible
cat > /home/student/ansible/nodes.ini <<'EOT'
[nodes]
n1 node_id=1
n2 node_id=2
n3 node_id=3

[nodes:vars]
ansible_connection=local
EOT
chown -R student:student /home/student/ansible
"""
MONITOR = r"""
mon_start() { ( while :; do h=0; for p in 8101 8102 8103; do curl -s -m 1 -o /dev/null -w '%{http_code}' http://127.0.0.1:$p/health | grep -q 200 && h=$((h+1)); done; echo $h >> /tmp/.healthy.log; sleep 0.2; done ) & echo $! > /tmp/.mon.pid; }
mon_stop() { kill $(cat /tmp/.mon.pid) 2>/dev/null; }
"""

lab(
    id="ld-095", title="Асимметричная маршрутизация: ответы приходят не оттуда",
    description="Запрос и ответ идут разными путями, и строгий reverse path filter отбрасывает ответы. Найдите причину по счётчикам и устраните.",
    skills=["rp_filter", "nstat IPReversePathFilter", "ip route get", "tcpdump"],
    objectives=["Увидеть, что ответ приходит на другой интерфейс", "Найти отбрасывание по счётчику", "Исправить фильтр обратного пути"],
    minutes=35,
    task=NSNOTE + """\
Узел `peer` соединён с машиной двумя кабелями: сеть A (`10.91.0.0/24`, машина `10.91.0.1`, узел `10.91.0.2`) и сеть B (`10.92.0.0/24`, машина `10.92.0.1`, узел `10.92.0.2`). Сервис на машине слушает порт 8080.

Из узла `peer` запрос с адреса `10.92.0.2` на `10.91.0.1:8080` уходит через сеть A, а ответ машина отправляет в сеть B (так устроены маршруты) — ответ приходит на другой интерфейс узла и **отбрасывается** (`rp_filter`).

Проверьте: `sudo nsenter --net=/run/netns/peer curl --http0.9 --interface 10.92.0.2 -m 3 http://10.91.0.1:8080/` (сервис отвечает без HTTP-заголовков, поэтому нужен ключ `--http0.9`) зависает. Найдите причину (`nstat -az IPReversePathFilter` внутри `peer`) и устраните её в узле `peer` **без изменения маршрутов** (loose-режим `rp_filter=2` на интерфейсах узла).
""",
    hints=["`sudo nsenter --net=/run/netns/peer nstat -az IPReversePathFilter` — счётчик растёт при каждой попытке.", "`sudo nsenter --net=/run/netns/peer sysctl -w net.ipv4.conf.all.rp_filter=2 net.ipv4.conf.p_b.rp_filter=2 net.ipv4.conf.p_a.rp_filter=2`."],
    exercise_timeout=15,
    checks=[
        ("request_works", "Запрос с 10.92.0.2 проходит", "Асимметричный путь работает", "curl с 10.92.0.2 на 10.91.0.1:8080 не получает ответ"),
        ("routes_unchanged", "Маршруты не менялись", "Маршруты не тронуты", "Маршруты машины и узла не должны меняться: исправляется фильтр обратного пути"),
        ("rp_loose", "rp_filter в узле не strict", "Фильтр ослаблен", "В узле peer rp_filter остаётся строгим (1) на интерфейсе сети B"),
    ],
    setup=NODE + r"""
node peer ha p_a 10.91.0.2/24 10.91.0.1/24
ip link add hb type veth peer name p_b
ip link set p_b netns peer
ip addr add 10.92.0.1/24 dev hb; ip link set hb up
nsenter --net=/run/netns/peer ip addr add 10.92.0.2/24 dev p_b
nsenter --net=/run/netns/peer ip link set p_b up
# запросы с 10.92.0.2 к 10.91.0.1 уходят через сеть A (политика по адресу источника), ответ машина шлёт через B
nsenter --net=/run/netns/peer ip rule add from 10.92.0.2 lookup 100
nsenter --net=/run/netns/peer ip route add 10.91.0.0/24 dev p_a table 100
nsenter --net=/run/netns/peer sysctl -qw net.ipv4.conf.all.rp_filter=1 net.ipv4.conf.p_a.rp_filter=1 net.ipv4.conf.p_b.rp_filter=1
sysctl -qw net.ipv4.conf.all.rp_filter=0 net.ipv4.conf.default.rp_filter=0
ip route add 10.92.0.2/32 dev hb
listener web 8080 asym-ok
""",
    exercise="true\n",
    validate=NSX + r"""
chk request_works '[ "$(NS peer curl --http0.9 --interface 10.92.0.2 -s -m 3 http://10.91.0.1:8080/ | tr -d "\n")" = asym-ok ]'
chk routes_unchanged '{ NS peer ip -o route; ip route; NS peer ip route show table 100; } | grep -q "10.92.0.2 dev hb" && NS peer ip rule | grep -q "from 10.92.0.2 lookup 100"'
chk rp_loose '[ "$(NS peer sysctl -n net.ipv4.conf.p_b.rp_filter)" != 1 ] || [ "$(NS peer sysctl -n net.ipv4.conf.all.rp_filter)" = 2 ]'
""",
    solution=r"""
sudo nsenter --net=/run/netns/peer nstat -az IPReversePathFilter | head -3
sudo nsenter --net=/run/netns/peer sysctl -w net.ipv4.conf.all.rp_filter=2 net.ipv4.conf.p_a.rp_filter=2 net.ipv4.conf.p_b.rp_filter=2
""",
    wrong="sudo ip route del 10.92.0.2/32 dev hb\n",
)

lab(
    id="ld-099", title="Имя резолвится в старый адрес: TTL и кэш",
    description="После смены записи клиенты получают старый адрес. Найдите, где держится кэш, и исправьте так, чтобы изменения доходили быстро.",
    skills=["dig +ttl", "dnsmasq cache", "min-cache-ttl", "local-ttl"],
    objectives=["Проследить ответ по цепочке resolver → upstream", "Найти источник завышенного TTL", "Сбросить кэш и поправить TTL"],
    minutes=30,
    task="""\
Запись `app.lab.test` перенесли на новый адрес `10.20.0.55`, но клиенты, ходящие через кэширующий резолвер (`127.0.0.1:5353`), всё ещё получают старый `10.20.0.5`.

Цепочка: клиент → **кэширующий dnsmasq** (`127.0.0.1:5353`, конфиг `/etc/dnsmasq-cache.conf`, служба `dnsmasq-cache`) → **авторитетный dnsmasq** (`127.0.0.2:5300`, конфиг `/etc/dnsmasq-auth.conf`, служба `dnsmasq-auth`; он уже отдаёт новый адрес).

Найдите источник проблемы (`dig +ttl`, сравните ответы обоих серверов) и исправьте:

- кэширующий резолвер должен отдавать новый адрес (сбросьте кэш);
- завышенные TTL больше не должны удерживать старые данные: в конфигах не должно остаться `min-cache-ttl`/`local-ttl` больше 60 секунд.
""",
    hints=["`dig +ttl @127.0.0.1 -p 5353 app.lab.test` против `dig +ttl @127.0.0.2 -p 5300 app.lab.test` — разница в адресе и TTL.", "Уберите/уменьшите `min-cache-ttl` и `local-ttl`, затем `sudo systemctl restart dnsmasq-cache dnsmasq-auth` (перезапуск сбрасывает кэш)."],
    exercise_timeout=15,
    checks=[
        ("new_answer", "Резолвер отдаёт 10.20.0.55", "Резолвер отдаёт актуальный адрес", "Кэширующий резолвер всё ещё отдаёт старый адрес"),
        ("ttl_sane", "TTL в конфигах ≤ 60 с", "TTL приведены в порядок", "min-cache-ttl/local-ttl в конфигурации больше 60 секунд"),
        ("ttl_in_answer", "TTL в ответе ≤ 60", "В ответе небольшой TTL", "TTL ответа резолвера больше 60 секунд"),
    ],
    setup=r"""
cat > /etc/dnsmasq-auth.conf <<'EOT'
port=5300
listen-address=127.0.0.2
bind-interfaces
no-resolv
no-hosts
host-record=app.lab.test,10.20.0.5
local-ttl=3600
pid-file=/run/dnsmasq-auth.pid
EOT
cat > /etc/dnsmasq-cache.conf <<'EOT'
port=5353
listen-address=127.0.0.1
bind-interfaces
no-resolv
no-hosts
server=127.0.0.2#5300
cache-size=200
min-cache-ttl=3600
pid-file=/run/dnsmasq-cache.pid
EOT
for u in auth cache; do
cat > /etc/systemd/system/dnsmasq-$u.service <<EOT
[Service]
ExecStart=/usr/sbin/dnsmasq -k --conf-file=/etc/dnsmasq-$u.conf
[Install]
WantedBy=multi-user.target
EOT
done
systemctl daemon-reload
systemctl enable --now dnsmasq-auth >/dev/null 2>&1; sleep 1
systemctl enable --now dnsmasq-cache >/dev/null 2>&1; sleep 1
dig +short @127.0.0.1 -p 5353 app.lab.test > /dev/null
sed -i 's/host-record=app.lab.test,10.20.0.5/host-record=app.lab.test,10.20.0.55/' /etc/dnsmasq-auth.conf
systemctl restart dnsmasq-auth
sleep 1
""",
    exercise="sleep 1\ntrue\n",
    validate=r"""
a=$(dig +short +time=2 +tries=1 @127.0.0.1 -p 5353 app.lab.test)
ttl=$(dig +noall +answer +ttlid +time=2 +tries=1 @127.0.0.1 -p 5353 app.lab.test | awk '{print $2}' | head -n 1)
big=$(grep -hE "^(min-cache-ttl|local-ttl)=" /etc/dnsmasq-cache.conf /etc/dnsmasq-auth.conf | awk -F= '$2>60{n++} END{print n+0}')
chk new_answer '[ "$a" = 10.20.0.55 ]'
chk ttl_sane '[ "$big" = 0 ]'
chk ttl_in_answer '[ -n "$ttl" ] && [ "$ttl" -le 60 ]'
""",
    solution=r"""
sudo sed -i '/^min-cache-ttl=/d' /etc/dnsmasq-cache.conf
sudo sed -i 's/^local-ttl=.*/local-ttl=30/' /etc/dnsmasq-auth.conf
sudo systemctl restart dnsmasq-auth dnsmasq-cache
sleep 1
""",
    wrong="sudo systemctl restart dnsmasq-cache\nsleep 1\n",
)

lab(
    id="ld-103", title="HTTP keep-alive: соединения до backend за прокси",
    description="Сравните число соединений до backend с повторным использованием соединений и без него и настройте keepalive в nginx.",
    skills=["nginx upstream keepalive", "proxy_http_version 1.1", "Connection", "число соединений"],
    objectives=["Измерить число соединений до backend", "Включить keep-alive к upstream", "Подтвердить измерением"],
    minutes=30,
    task="""\
nginx (`127.0.0.1:8095`) проксирует на backend (`127.0.0.1:9200`), который считает принятые TCP-соединения (`curl http://127.0.0.1:9200/count`).

Сейчас каждый запрос через прокси открывает **новое** соединение до backend. Настройте `/etc/nginx/conf.d/ka.conf` так, чтобы соединения переиспользовались: блок `upstream` с `keepalive`, `proxy_http_version 1.1` и очищенный заголовок `Connection`.

Проверка: после 20 запросов через прокси backend должен принять **не более 3** новых соединений.
""",
    hints=["`upstream lab { server 127.0.0.1:9200; keepalive 8; }`, в `location`: `proxy_pass http://lab; proxy_http_version 1.1; proxy_set_header Connection \"\";`.", "Проверка: запомните `/count`, сделайте 20 запросов `curl http://127.0.0.1:8095/`, снова `/count`."],
    exercise_timeout=15,
    checks=[
        ("reuse_works", "20 запросов → ≤ 3 новых соединений", "Соединения переиспользуются", "20 запросов через прокси создали больше 3 соединений до backend"),
        ("proxy_works", "Прокси отвечает", "Прокси работает", "Прокси на 8095 не возвращает ответ backend"),
        ("upstream_keepalive", "В конфиге keepalive и HTTP/1.1", "Настройки заданы", "В конфиге нужны upstream keepalive и proxy_http_version 1.1"),
    ],
    setup=r"""
install -d /opt/lab
cat > /opt/lab/kabackend.py <<'EOT'
import http.server, socketserver, threading

count = 0
lock = threading.Lock()

class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def setup(self):
        global count
        with lock:
            if not self.path_is_count:
                pass
        super().setup()
    path_is_count = False
    def do_GET(self):
        body = (str(count) + "\n").encode() if self.path == "/count" else b"hello\n"
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a):
        pass

class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    def process_request(self, request, client_address):
        global count
        # /count запрашивается напрямую с адреса 127.0.0.1 тем же сервером, поэтому считаем только соединения от nginx (порты не различаем):
        with lock:
            count += 1
        super().process_request(request, client_address)

S(("127.0.0.1", 9200), H).serve_forever()
EOT
cat > /etc/systemd/system/lab-kabackend.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/kabackend.py
[Install]
WantedBy=multi-user.target
EOT
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/ka.conf <<'EOT'
server {
    listen 127.0.0.1:8095;
    location / { proxy_pass http://127.0.0.1:9200; }
}
EOT
systemctl daemon-reload
systemctl enable --now lab-kabackend nginx >/dev/null 2>&1
sleep 1
""",
    exercise="sudo nginx -t >/dev/null 2>&1 && sudo systemctl reload nginx\nsleep 1\ntrue\n",
    validate=r"""
c0=$(curl -s -m 3 http://127.0.0.1:9200/count | tr -d "\n")
for i in $(seq 1 20); do curl -s -m 3 -o /dev/null http://127.0.0.1:8095/; done
c1=$(curl -s -m 3 http://127.0.0.1:9200/count | tr -d "\n")
chk reuse_works '[ -n "$c0" ] && [ -n "$c1" ] && [ $((c1 - c0 - 1)) -le 3 ]'
chk proxy_works '[ "$(curl -s -m 3 http://127.0.0.1:8095/ | tr -d "\n")" = hello ]'
chk upstream_keepalive 'cat /etc/nginx/conf.d/ka.conf | grep -q "keepalive" && grep -q "proxy_http_version 1.1" /etc/nginx/conf.d/ka.conf'
""",
    solution=r"""
sudo tee /etc/nginx/conf.d/ka.conf > /dev/null <<'EOT'
upstream lab_backend {
    server 127.0.0.1:9200;
    keepalive 8;
}
server {
    listen 127.0.0.1:8095;
    location / {
        proxy_pass http://lab_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
EOT
sudo nginx -t && sudo systemctl reload nginx
""",
    wrong="sudo systemctl reload nginx\n",
)

lab(
    id="ld-114", title="Bastion-доступ к внутреннему узлу через ProxyJump",
    description="Достучитесь до внутреннего узла, не открывая его наружу: через bastion с помощью ProxyJump.",
    skills=["ssh -J / ProxyJump", "~/.ssh/config", "authorized_keys", "изоляция сегментов"],
    objectives=["Понять топологию", "Настроить ключи для bastion и внутреннего узла", "Описать ProxyJump в ssh_config"],
    minutes=40,
    task=NSNOTE + """\
Топология: клиент (`client`, `10.95.1.2`) → **bastion** (машина, `10.95.1.1`, sshd, пользователь `jump`) → **внутренний узел** (`inner`, `10.95.2.2`, отдельный sshd, пользователь `inner`). У клиента **нет** маршрута к `10.95.2.0/24`.

Настройте для пользователя `student` ключи и `~/.ssh/config` так, чтобы из клиента работало:

```
sudo nsenter --net=/run/netns/client runuser -u student -- ssh inner id -un
```

и выводило `inner`: алиас `inner` (`HostName 10.95.2.2`, `User inner`) с `ProxyJump` через bastion (`jump@10.95.1.1`). Прямой доступ клиента к внутреннему узлу открывать нельзя (маршруты не менять). Проверка: `StrictHostKeyChecking` включена, ключи без пароля.
""",
    hints=["Создайте `~/.ssh/id_ed25519` и добавьте публичный ключ в `authorized_keys` пользователей `jump` и `inner` (права 0700/0600, владелец — они).", "Хост-ключи: `ssh-keyscan` для обоих адресов в `~/.ssh/known_hosts`. Config: `Host inner / HostName 10.95.2.2 / User inner / ProxyJump jump@10.95.1.1`."],
    exercise_timeout=20,
    checks=[
        ("jump_works", "ssh inner id -un → inner", "ProxyJump работает", "Из клиента `ssh inner id -un` не выводит inner"),
        ("no_direct_route", "У клиента нет маршрута во внутреннюю сеть", "Внутренняя сеть не открыта", "Клиент получил прямой доступ к 10.95.2.0/24 (маршруты менять нельзя)"),
        ("proxyjump_config", "В ssh_config ProxyJump", "Конфигурация использует ProxyJump", "В ~/.ssh/config для inner нужен ProxyJump через bastion"),
    ],
    setup=NODE + r"""
node client hc c0 10.95.1.2/24 10.95.1.1/24
node inner hi i0 10.95.2.2/24 10.95.2.1/24
nsenter --net=/run/netns/client ip route add default via 10.95.1.1
nsenter --net=/run/netns/inner ip route add default via 10.95.2.1
sysctl -qw net.ipv4.ip_forward=0
useradd -m -s /bin/bash jump; useradd -m -s /bin/bash inner
passwd -l jump >/dev/null; passwd -l inner >/dev/null
mkdir -p /run/sshd /etc/ssh/inner
ssh-keygen -A >/dev/null
ssh-keygen -q -t ed25519 -N '' -f /etc/ssh/inner/host_ed25519
cat > /etc/ssh/inner/sshd_config <<'EOT'
Port 22
ListenAddress 10.95.2.2
HostKey /etc/ssh/inner/host_ed25519
PidFile /run/sshd-inner.pid
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers inner
UsePAM yes
EOT
printf 'PasswordAuthentication no\nPubkeyAuthentication yes\nListenAddress 10.95.1.1\nAllowUsers jump student\n' > /etc/ssh/sshd_config.d/10-lab.conf
cat > /etc/systemd/system/sshd-inner.service <<'EOT'
[Service]
ExecStart=/usr/bin/nsenter --net=/run/netns/inner /usr/sbin/sshd -D -f /etc/ssh/inner/sshd_config
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now ssh sshd-inner >/dev/null 2>&1
sleep 1
""",
    exercise="true\n",
    validate=NSX + r"""
chk jump_works '[ "$(NS client runuser -u student -- ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=8 inner id -un 2>/dev/null | tr -d "\r\n")" = inner ]'
chk no_direct_route '! NS client ping -c1 -W1 10.95.2.2 && [ "$(sysctl -n net.ipv4.ip_forward)" = 0 ]'
chk proxyjump_config 'grep -qiE "^[[:space:]]*(ProxyJump|ProxyCommand)" /home/student/.ssh/config && grep -qi "10.95.2.2" /home/student/.ssh/config'
""",
    solution=r"""
ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q
for u in jump inner; do
  sudo install -d -m 700 -o $u -g $u /home/$u/.ssh
  sudo install -m 600 -o $u -g $u ~/.ssh/id_ed25519.pub /home/$u/.ssh/authorized_keys
done
{ ssh-keyscan -t ed25519 10.95.1.1 2>/dev/null; ssh-keyscan -t ed25519 10.95.2.2 2>/dev/null; } >> ~/.ssh/known_hosts
cat > ~/.ssh/config <<'EOT'
Host inner
    HostName 10.95.2.2
    User inner
    ProxyJump jump@10.95.1.1
EOT
chmod 600 ~/.ssh/config
""",
    wrong="ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q\n",
)

lab(
    id="ld-116", title="SSH port forwarding: локальный и удалённый, кто слушает порт",
    description="Поднимите два туннеля — локальный (-L) и удалённый (-R) — и объясните, на какой стороне открывается порт.",
    skills=["ssh -L", "ssh -R", "ssh -fN", "ss -ltnp"],
    objectives=["Настроить -L и -R", "Проверить через ss и curl", "Понять, где слушает порт"],
    minutes=30,
    task="""\
На машине работает backend `127.0.0.1:8000` (отдаёт `backend-ok`) и `sshd`. Пользователь `labuser` принимает вход по ключу (его ключи для `student` уже настроены).

Поднимите **два фоновых туннеля** (`ssh -f -N …`, не завершайте их):

1. **Локальный (-L)**: порт `127.0.0.1:9000` у клиента (`student`) → `127.0.0.1:8000` через `labuser@127.0.0.1`;
2. **Удалённый (-R)**: порт `127.0.0.1:9100` открывается на **стороне сервера** (sshd) и ведёт в `127.0.0.1:8000`.

Затем запишите в `~/fwd.txt` две строки: `L_listens=<client|server>` и `R_listens=<client|server>` — на чьей стороне ssh открывает порт.
""",
    hints=["`ssh -f -N -L 127.0.0.1:9000:127.0.0.1:8000 labuser@127.0.0.1` и `ssh -f -N -R 127.0.0.1:9100:127.0.0.1:8000 labuser@127.0.0.1`.", "`-L` открывает порт у того, кто запускает ssh (client); `-R` — на стороне sshd (server)."],
    exercise_timeout=15,
    checks=[
        ("local_forward", "127.0.0.1:9000 → backend-ok", "Локальный туннель работает", "curl http://127.0.0.1:9000/ не возвращает backend-ok (нужен ssh -L)"),
        ("remote_forward", "127.0.0.1:9100 → backend-ok, держит sshd", "Удалённый туннель работает", "Порт 9100 не открыт sshd-процессом (нужен ssh -R)"),
        ("sides_ok", "fwd.txt: L=client, R=server", "Стороны определены верно", "fwd.txt: L_listens=client и R_listens=server"),
    ],
    setup=r"""
useradd -m -s /bin/bash labuser; passwd -l labuser >/dev/null
printf 'PasswordAuthentication no\nPubkeyAuthentication yes\nListenAddress 127.0.0.1\nAllowTcpForwarding yes\nGatewayPorts no\n' > /etc/ssh/sshd_config.d/10-lab.conf
mkdir -p /run/sshd; ssh-keygen -A >/dev/null
su - student -c "ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q; ssh-keyscan -t ed25519 127.0.0.1 2>/dev/null > ~/.ssh/known_hosts"
install -d -m 700 -o labuser -g labuser /home/labuser/.ssh
install -m 600 -o labuser -g labuser /home/student/.ssh/id_ed25519.pub /home/labuser/.ssh/authorized_keys
install -d /srv/fwdback; echo backend-ok > /srv/fwdback/index.html
cat > /etc/systemd/system/lab-fwdback.service <<'EOT'
[Service]
WorkingDirectory=/srv/fwdback
ExecStart=/usr/bin/python3 -m http.server 8000 --bind 127.0.0.1
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now ssh lab-fwdback >/dev/null 2>&1
sleep 1
""",
    exercise="true\n",
    validate=r"""
chk local_forward '[ "$(curl -s -m 4 http://127.0.0.1:9000/ | tr -d "\n")" = backend-ok ] && ss -ltnp | grep ":9000 " | grep -q ssh'
chk remote_forward '[ "$(curl -s -m 4 http://127.0.0.1:9100/ | tr -d "\n")" = backend-ok ] && ss -ltnp | grep ":9100 " | grep -q sshd'
chk sides_ok 'grep -qx "L_listens=client" /home/student/fwd.txt && grep -qx "R_listens=server" /home/student/fwd.txt'
""",
    solution=r"""
ssh -f -N -L 127.0.0.1:9000:127.0.0.1:8000 labuser@127.0.0.1
ssh -f -N -R 127.0.0.1:9100:127.0.0.1:8000 labuser@127.0.0.1
printf 'L_listens=client\nR_listens=server\n' > ~/fwd.txt
sleep 1
""",
    wrong="printf 'L_listens=server\\nR_listens=client\\n' > ~/fwd.txt\n",
)

lab(
    id="ld-174", title="Основной узел недоступен, реплика отстаёт: промоутить или ждать",
    description="По метрикам репликации примите решение о переключении и посчитайте потери данных относительно допустимого RPO.",
    skills=["репликация", "lag", "RPO", "принятие решения при отказе"],
    objectives=["Прочитать состояние реплики", "Посчитать потенциальную потерю", "Принять решение по правилу RPO"],
    minutes=25,
    task="""\
Основной узел недоступен. Состояние реплики: `/var/lib/lab/replica.status` (`applied_tx`, `lag_seconds`), последнее известное значение основного: `/var/lib/lab/primary.last` (`committed_tx`). Допустимая потеря — **не более 100 транзакций** (RPO), а при отставании реплики больше 60 секунд она считается небезопасной для переключения без досинхронизации из WAL (`/var/lib/lab/wal.available`: `yes`/`no`).

Правило решения:

- потери ≤ 100 и lag ≤ 60 → `promote` (переключить на реплику);
- иначе, если `wal.available=yes` → `catchup` (досинхронизировать реплику из WAL, потом переключать);
- иначе → `promote_with_loss` (переключить с признанием потерь).

Запишите в `~/decision.txt`: `lost_tx=<committed_tx − applied_tx>` и `action=<promote|catchup|promote_with_loss>`.
""",
    hints=["`cat /var/lib/lab/replica.status /var/lib/lab/primary.last /var/lib/lab/wal.available`.", "Потери — это разность `committed_tx − applied_tx`."],
    checks=[
        ("lost_ok", "lost_tx верно", "Потери посчитаны", "lost_tx должен быть равен committed_tx − applied_tx"),
        ("action_ok", "action по правилу", "Решение принято по правилу", "action не соответствует правилу (потери, отставание, наличие WAL)"),
    ],
    setup=r"""
install -d /var/lib/lab
printf 'applied_tx=15200\nlag_seconds=95\n' > /var/lib/lab/replica.status
printf 'committed_tx=15920\n' > /var/lib/lab/primary.last
printf 'yes\n' > /var/lib/lab/wal.available
""",
    validate=r"""
v() { grep "^$1=" /home/student/decision.txt | cut -d= -f2- | tr -d ' '; }
chk lost_ok '[ "$(v lost_tx)" = 720 ]'
chk action_ok '[ "$(v action)" = catchup ]'
""",
    solution="printf 'lost_tx=720\\naction=catchup\\n' > ~/decision.txt\n",
    wrong="printf 'lost_tx=720\\naction=promote\\n' > ~/decision.txt\n",
)

lab(
    id="ld-182", validate_timeout=60, title="Rolling update трёх узлов с health gate и serial",
    description="Обновите три узла по одному, дожидаясь здоровья каждого перед следующим, чтобы сервис не терял ёмкость.",
    skills=["ansible serial", "health gate", "uri/wait_for", "rolling update"],
    objectives=["Обновлять по одному узлу", "Ждать успешный health-check", "Сохранять минимум двух здоровых узлов"],
    minutes=45,
    task="""\
Три узла `n1`..`n3` (службы `labnode@1..3`, порты 8101..8103, версия в `/etc/labnode/<N>.version`, health — `GET /health`, здоров только через ~3 секунды после старта) работают на версии `v1`. Inventory — `~/ansible/nodes.ini` (переменная `node_id`).

Напишите `~/ansible/rolling.yml`, который обновляет узлы до версии из переменной `new_version` (по умолчанию `v2`):

- обновление по **одному** узлу (`serial: 1`);
- запись версии в `/etc/labnode/<node_id>.version` и перезапуск `labnode@<node_id>`;
- **health gate**: после перезапуска ждать успешного `GET http://127.0.0.1:810<node_id>/health` (`uri` с `until`/`retries` или `wait_for`), только потом переходить к следующему узлу.

Проверка запустит playbook (`ansible-playbook -i nodes.ini rolling.yml`), параллельно следя, чтобы одновременно были здоровы не менее **двух** узлов, и убедится, что все три узла на `v2`.
""",
    hints=["`- hosts: nodes`, `serial: 1`; задачи: copy (`content: \"{{ new_version }}\\n\"`), systemd `restarted`, затем uri с `register`/`until: r.status == 200`, `retries: 20`, `delay: 1`.", "Подключение local уже задано в inventory."],
    exercise_timeout=60,
    checks=[
        ("all_updated", "Все узлы на v2", "Обновлены все узлы", "Не все узлы обновлены до v2"),
        ("capacity_kept", "Всегда ≥ 2 здоровых узла", "Ёмкость сохранялась", "Во время обновления здоровых узлов было меньше двух (нужны serial: 1 и health gate)"),
        ("serial_defined", "serial и health-check в playbook", "serial и health gate на месте", "В playbook нужны serial: 1 и проверка /health"),
    ],
    setup=NODES + NODES_INV,
    exercise="true\n",
    validate=MONITOR + r"""
cd /home/student/ansible
for n in 1 2 3; do echo v1 > /etc/labnode/$n.version; done
systemctl restart labnode@1 labnode@2 labnode@3; sleep 4
: > /tmp/.healthy.log; mon_start
ansible-playbook -i nodes.ini rolling.yml >/tmp/.rolling.out 2>&1
sleep 1; mon_stop
min=$(sort -n /tmp/.healthy.log | head -n 1)
chk all_updated '[ "$(cat /etc/labnode/1.version /etc/labnode/2.version /etc/labnode/3.version | sort -u)" = v2 ] && for p in 8101 8102 8103; do [ "$(curl -s -m 2 http://127.0.0.1:$p/ | tr -d "\n")" = v2 ] || exit 1; done'
chk capacity_kept '[ -n "$min" ] && [ "$min" -ge 2 ]'
chk serial_defined 'grep -qE "serial:[[:space:]]*1" rolling.yml && grep -qE "/health" rolling.yml'
""",
    solution=r"""
cat > ~/ansible/rolling.yml <<'EOT'
- hosts: nodes
  serial: 1
  gather_facts: false
  vars:
    new_version: v2
  tasks:
    - name: version
      ansible.builtin.copy:
        content: "{{ new_version }}\n"
        dest: "/etc/labnode/{{ node_id }}.version"
    - name: restart
      ansible.builtin.systemd:
        name: "labnode@{{ node_id }}"
        state: restarted
    - name: health gate
      ansible.builtin.uri:
        url: "http://127.0.0.1:810{{ node_id }}/health"
        status_code: 200
      register: h
      until: h.status == 200
      retries: 20
      delay: 1
EOT
""",
    wrong="cat > ~/ansible/rolling.yml <<'EOT'\n- hosts: nodes\n  gather_facts: false\n  tasks:\n    - ansible.builtin.copy:\n        content: \"v2\\n\"\n        dest: \"/etc/labnode/{{ node_id }}.version\"\n    - ansible.builtin.systemd:\n        name: \"labnode@{{ node_id }}\"\n        state: restarted\nEOT\n",
)

lab(
    id="ld-183", validate_timeout=60, title="Playbook оставил половину парка в новой версии: восстановить согласованность",
    description="Обновление прервалось на среднем узле. Найдите причину сбоя, исправьте playbook и приведите все узлы к одной версии.",
    skills=["ansible-playbook --limit", "--start-at-task", "диагностика сбоя", "согласованность парка"],
    objectives=["Определить, какие узлы на какой версии", "Найти ошибку в playbook", "Довести обновление до конца"],
    minutes=40,
    task="""\
**Инцидент.** Обновление `~/ansible/update.yml` (inventory `~/ansible/nodes.ini`) прервалось: `n1` уже на `v2`, а `n2` и `n3` остались на `v1` — парк неоднороден.

1. Выясните версии узлов (`curl http://127.0.0.1:810N/`) и найдите ошибку в `update.yml` (запустите playbook и прочитайте сообщение).
2. Исправьте playbook и доведите **все три** узла до `v2`. Узлы должны быть здоровы (`/health` отвечает 200).
""",
    hints=["`cd ~/ansible && ansible-playbook -i nodes.ini update.yml` покажет, на каком узле/задаче падение.", "Ошибка в адресе health-check узла (порт не соответствует `node_id`)."],
    exercise_timeout=60,
    checks=[
        ("fleet_v2", "Все узлы на v2", "Версии выровнены", "Не все узлы на v2"),
        ("fleet_healthy", "Все узлы здоровы", "Узлы здоровы", "Не все узлы отвечают на /health"),
        ("playbook_fixed", "Playbook проходит целиком", "Playbook исправлен", "ansible-playbook update.yml завершается с ошибкой"),
    ],
    setup=NODES + NODES_INV + r"""
cat > /home/student/ansible/update.yml <<'EOT'
- hosts: nodes
  serial: 1
  gather_facts: false
  vars:
    new_version: v2
  tasks:
    - name: version
      ansible.builtin.copy:
        content: "{{ new_version }}\n"
        dest: "/etc/labnode/{{ node_id }}.version"
    - name: restart
      ansible.builtin.systemd:
        name: "labnode@{{ node_id }}"
        state: restarted
    - name: health gate
      ansible.builtin.uri:
        url: "http://127.0.0.1:81{{ node_id }}/health"
        status_code: 200
      register: h
      until: h.status == 200
      retries: 10
      delay: 1
EOT
chown student:student /home/student/ansible/update.yml
echo v2 > /etc/labnode/1.version; systemctl restart labnode@1
""",
    exercise="true\n",
    validate=r"""
cd /home/student/ansible
chk playbook_fixed 'ansible-playbook -i nodes.ini update.yml >/tmp/.upd.out 2>&1'
sleep 4
chk fleet_v2 'for p in 8101 8102 8103; do [ "$(curl -s -m 2 http://127.0.0.1:$p/ | tr -d "\n")" = v2 ] || exit 1; done'
chk fleet_healthy 'for p in 8101 8102 8103; do curl -s -m 2 -o /dev/null -w "%{http_code}" http://127.0.0.1:$p/health | grep -q 200 || exit 1; done'
""",
    solution=r"""
cd ~/ansible
sed -i 's#http://127.0.0.1:81{{ node_id }}/health#http://127.0.0.1:810{{ node_id }}/health#' update.yml
ansible-playbook -i nodes.ini update.yml
""",
    wrong="cd ~/ansible\necho v2 | sudo tee /etc/labnode/2.version > /dev/null\n",
)

lab(
    id="ld-188", title="Сервис падает после ротации TLS только за балансировщиком",
    description="Один из backend-ов продолжает отдавать старый сертификат: за round-robin ошибка проявляется через раз.",
    skills=["openssl s_client", "балансировщик L4", "ротация сертификатов", "поиск проблемного backend"],
    objectives=["Проверить каждый backend отдельно", "Найти узел со старым сертификатом", "Применить новый сертификат"],
    minutes=35,
    task="""\
Клиент ходит на `https://app.lab.test:8443` (L4-балансировщик `lab-lb`, round-robin на два backend-а: `127.0.0.1:9301` и `127.0.0.1:9302`). После ротации сертификата запросы через раз завершаются ошибкой проверки (`curl --cacert /etc/lab/ca/ca.crt --resolve app.lab.test:8443:127.0.0.1 https://app.lab.test:8443/`).

Новый сертификат лежит в `/etc/lab/tls/new.crt` (ключ `new.key`), старый — `/etc/lab/tls/old.crt`. Backend читает сертификат при старте (службы `labtls@1`, `labtls@2`, конфиг — `/etc/lab/tls/labtls-N.env`).

Проверьте каждый backend отдельно, найдите тот, что отдаёт старый сертификат, и устраните (обе службы должны использовать новый). Проверка сделает 10 запросов через балансировщик — все должны проходить.
""",
    hints=["`echo | openssl s_client -connect 127.0.0.1:9301 -servername app.lab.test -CAfile /etc/lab/ca/ca.crt` — для каждого порта; смотрите `Verify return code`.", "В `/etc/lab/tls/labtls-N.env` указаны пути сертификата; затем `sudo systemctl restart labtls@N`."],
    exercise_timeout=20,
    checks=[
        ("all_requests_ok", "10 запросов через LB проходят", "Балансировщик отдаёт валидный сертификат", "Часть запросов через балансировщик не проходит проверку сертификата"),
        ("both_new", "Оба backend-а с новым сертификатом", "Оба backend-а обновлены", "Один из backend-ов всё ещё отдаёт старый сертификат"),
    ],
    setup=r"""
install -d /etc/lab/ca /etc/lab/tls /opt/lab
cd /etc/lab/ca
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -days 3650 -subj "/CN=Lab Root CA" >/dev/null 2>&1
mk() { # имя дней
  openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/$1.key -out /tmp/$1.csr -subj "/CN=app.lab.test" >/dev/null 2>&1
  openssl x509 -req -in /tmp/$1.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days $2 -extfile <(printf 'subjectAltName=DNS:app.lab.test') -out /etc/lab/tls/$1.crt >/dev/null 2>&1
}
mk new 30
# «старый» сертификат — выпущен другим CA, которому клиент не доверяет
openssl req -x509 -newkey rsa:2048 -nodes -keyout /tmp/oldca.key -out /tmp/oldca.crt -days 30 -subj "/CN=Old CA" >/dev/null 2>&1
openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/old.key -out /tmp/old.csr -subj "/CN=app.lab.test" >/dev/null 2>&1
openssl x509 -req -in /tmp/old.csr -CA /tmp/oldca.crt -CAkey /tmp/oldca.key -CAcreateserial -days 30 -extfile <(printf 'subjectAltName=DNS:app.lab.test') -out /etc/lab/tls/old.crt >/dev/null 2>&1
chmod 644 /etc/lab/ca/ca.crt /etc/lab/tls/*.crt; chmod 640 /etc/lab/tls/*.key
printf 'CERT=/etc/lab/tls/new.crt\nKEY=/etc/lab/tls/new.key\n' > /etc/lab/tls/labtls-1.env
printf 'CERT=/etc/lab/tls/old.crt\nKEY=/etc/lab/tls/old.key\n' > /etc/lab/tls/labtls-2.env
cat > /opt/lab/tlsback.py <<'EOT'
import socket, ssl, sys
n = sys.argv[1]
env = dict(l.strip().split("=", 1) for l in open("/etc/lab/tls/labtls-%s.env" % n) if "=" in l)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(env["CERT"], env["KEY"])
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 9300 + int(n))); s.listen(20)
while True:
    c, _ = s.accept()
    try:
        t = ctx.wrap_socket(c, server_side=True)
        t.recv(4096)
        t.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nok\n")
        t.close()
    except Exception:
        c.close()
EOT
cat > /etc/systemd/system/labtls@.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/tlsback.py %i
[Install]
WantedBy=multi-user.target
EOT
cat > /opt/lab/lb.py <<'EOT'
import itertools, socket, threading

backends = itertools.cycle([("127.0.0.1", 9301), ("127.0.0.1", 9302)])

def pipe(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            b.sendall(d)
    except OSError:
        pass
    finally:
        for s in (a, b):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

def handle(c):
    try:
        u = socket.create_connection(next(backends), timeout=3)
    except OSError:
        c.close()
        return
    threading.Thread(target=pipe, args=(c, u), daemon=True).start()
    threading.Thread(target=pipe, args=(u, c), daemon=True).start()

s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 8443)); s.listen(50)
while True:
    c, _ = s.accept()
    threading.Thread(target=handle, args=(c,), daemon=True).start()
EOT
cat > /etc/systemd/system/lab-lb.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/lb.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labtls@1 labtls@2 lab-lb >/dev/null 2>&1
sleep 1
""",
    exercise="sleep 1\ntrue\n",
    validate=r"""
ok=0
for i in $(seq 1 10); do curl -s -m 4 --cacert /etc/lab/ca/ca.crt --resolve app.lab.test:8443:127.0.0.1 https://app.lab.test:8443/ | grep -q ok && ok=$((ok+1)); done
chk all_requests_ok '[ "$ok" = 10 ]'
chk both_new 'for p in 9301 9302; do echo | openssl s_client -connect 127.0.0.1:$p -servername app.lab.test -CAfile /etc/lab/ca/ca.crt -verify_return_error 2>&1 | grep -q "Verify return code: 0 (ok)" || exit 1; done'
""",
    solution=r"""
for p in 9301 9302; do echo | openssl s_client -connect 127.0.0.1:$p -servername app.lab.test -CAfile /etc/lab/ca/ca.crt 2>&1 | grep "Verify return code"; done
sudo sed -i 's#old\.#new.#g' /etc/lab/tls/labtls-2.env
sudo systemctl restart labtls@2
sleep 1
""",
    wrong="sudo systemctl restart labtls@1\n",
)
