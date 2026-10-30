"""Задания на учебной машине (LXD), партия 5: firewall и NAT (nftables) на network namespace, резервное копирование и восстановление."""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append({"runtime_type": "lxd", **kw})


NSNOTE = (
    "> В учебной машине `ip netns exec` и `ip -n` недоступны (в контейнере нельзя смонтировать `/sys`). "
    "Команды внутри namespace выполняйте так: `sudo nsenter --net=/run/netns/ИМЯ команда`.\n\n"
)
NSX = 'NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }\n'
# TCP-проба из namespace: 0 — соединение установлено, иначе — отброшено/отказ/таймаут
PROBE = 'probe() { nsenter --net=/run/netns/$1 nc -z -w2 $2 $3; }\n'
# поднять «узел»: node <ns> <хостовая-пара> <адрес-узла/маска> <адрес-на-машине/маска>
NODE = r"""
node() { # ns hostif nsif nsaddr hostaddr
  ip netns add $1; ip link add $2 type veth peer name $3; ip link set $3 netns $1
  ip addr add $5 dev $2; ip link set $2 up
  nsenter --net=/run/netns/$1 ip addr add $4 dev $3
  nsenter --net=/run/netns/$1 ip link set $3 up; nsenter --net=/run/netns/$1 ip link set lo up
}
listener() { # имя порт [текст]
  mkdir -p /opt/lab
  cat > /opt/lab/listen_$1.py <<EOT
import socket
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", $2)); s.listen(20)
while True:
    c, _ = s.accept(); c.settimeout(0.5)
    try:
        c.recv(1024)
    except OSError:
        pass
    c.sendall(b"${3:-$1}\n"); c.close()
EOT
  cat > /etc/systemd/system/lab-$1.service <<EOT
[Service]
ExecStart=/usr/bin/python3 /opt/lab/listen_$1.py
[Install]
WantedBy=multi-user.target
EOT
  systemctl daemon-reload; systemctl enable --now lab-$1 >/dev/null 2>&1
}
"""

lab(
    id="ld-105", title="nftables: SSH только с управляющего узла, HTTP — из клиентской сети",
    description="Настройте input-политику с запретом по умолчанию и точечными разрешениями по подсетям.",
    skills=["nft", "input chain", "policy drop", "ct state", "ip saddr"],
    objectives=["Запретить входящее по умолчанию", "Разрешить SSH только с mgmt", "Разрешить HTTP только из клиентской сети"],
    minutes=30,
    task=NSNOTE + """\
Узлы: **`mgmt`** (`10.81.1.2`, управляющая сеть) и **`cli`** (`10.81.2.2`, клиентская сеть). На машине слушают порты `22` (учебный «SSH») и `80` (HTTP).

Настройте nftables (таблица `inet filter`, цепочка `input`, hook input) так, чтобы:

- политика по умолчанию — **drop**; loopback и уже установленные соединения (`ct state established,related`) разрешены;
- порт **22** доступен **только** из `10.81.1.0/24`;
- порт **80** доступен **только** из `10.81.2.0/24`;
- ICMP ping от обоих узлов разрешён.

Сохраните правила в `/etc/nftables.conf` (чтобы они переживали перезагрузку) и примените их.
""",
    hints=["Основа: `table inet filter { chain input { type filter hook input priority 0; policy drop; ... } }`.", "Правила: `iif lo accept`, `ct state established,related accept`, `ip saddr 10.81.1.0/24 tcp dport 22 accept` и т. д. Применить: `sudo nft -f /etc/nftables.conf`."],
    exercise_timeout=15,
    checks=[
        ("ssh_only_mgmt", "22: mgmt да, cli нет", "SSH только с управляющего узла", "Порт 22 должен быть доступен из mgmt и закрыт для cli"),
        ("http_only_cli", "80: cli да, mgmt нет", "HTTP только из клиентской сети", "Порт 80 должен быть доступен из cli и закрыт для mgmt"),
        ("default_drop_ping", "policy drop и ping разрешён", "Политика по умолчанию — drop", "Нужна цепочка input с policy drop; ping с обоих узлов разрешён"),
        ("persisted", "Правила сохранены в /etc/nftables.conf", "Правила сохранены", "/etc/nftables.conf не проходит nft -c или не содержит политику drop и порты 22/80"),
    ],
    setup=NODE + r"""
node mgmt hm0 m0 10.81.1.2/24 10.81.1.1/24
node cli hc0 c0 10.81.2.2/24 10.81.2.1/24
listener ssh 22 ssh-banner
listener http 80 http-ok
nft flush ruleset
""",
    exercise="sudo nft list ruleset >/dev/null\ntrue\n",
    validate=NSX + PROBE + r"""
chk ssh_only_mgmt 'probe mgmt 10.81.1.1 22 && ! probe cli 10.81.2.1 22'
chk http_only_cli 'probe cli 10.81.2.1 80 && ! probe mgmt 10.81.1.1 80'
chk default_drop_ping 'nft list chain inet filter input | grep -q "policy drop" && NS mgmt ping -c1 -W2 10.81.1.1 && NS cli ping -c1 -W2 10.81.2.1'
chk persisted 'nft -c -f /etc/nftables.conf && grep -q "policy drop" /etc/nftables.conf && grep -q "dport 22" /etc/nftables.conf && grep -q "dport 80" /etc/nftables.conf'
""",
    solution=r"""
sudo tee /etc/nftables.conf > /dev/null <<'EOT'
#!/usr/sbin/nft -f
flush ruleset
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        icmp type echo-request accept
        ip saddr 10.81.1.0/24 tcp dport 22 accept
        ip saddr 10.81.2.0/24 tcp dport 80 accept
    }
}
EOT
sudo nft -f /etc/nftables.conf
""",
    wrong="sudo nft add table inet filter\nsudo nft add chain inet filter input '{ type filter hook input priority 0; policy accept; }'\n",
)

lab(
    id="ld-106", title="Stateful-правило: почему ответы не возвращаются",
    description="Входящая политика drop блокирует ответы на исходящие соединения. Добавьте правило для established/related и объясните причину.",
    skills=["conntrack", "ct state", "established,related", "ответный трафик"],
    objectives=["Увидеть, что ответы отбрасываются", "Добавить stateful-правило", "Объяснить причину письменно"],
    minutes=20,
    task=NSNOTE + """\
Машина обращается к серверу в узле `srv` (`10.82.0.2:8000`), но `curl http://10.82.0.2:8000/` зависает: ответы блокирует входящая политика `drop`.

1. Добавьте в цепочку `inet filter input` правило `ct state established,related accept` (политика drop остаётся; в **закрытый** порт 9999 соединения извне по-прежнему не пускаются).
2. В `~/why.txt` одной-двумя фразами объясните причину (упомяните слова `established` и `conntrack`).
""",
    hints=["`sudo nft list ruleset` покажет цепочку с `policy drop` и счётчики.", "`sudo nft insert rule inet filter input ct state established,related accept`."],
    exercise_timeout=15,
    checks=[
        ("outbound_works", "curl к srv работает", "Ответы возвращаются", "Машина не получает ответ от 10.82.0.2:8000"),
        ("still_closed", "Порт 9999 закрыт извне, политика drop", "Входящие по-прежнему закрыты", "Новые входящие соединения (порт 9999) не должны пускаться; политика должна остаться drop"),
        ("explained", "why.txt: established и conntrack", "Причина объяснена", "В why.txt нужно объяснение со словами established и conntrack"),
    ],
    setup=NODE + r"""
node srv hs0 s0 10.82.0.2/24 10.82.0.1/24
install -d /opt/lab
cat > /opt/lab/httpd.py <<'EOT'
import http.server, os, socketserver, sys

class Server(http.server.ThreadingHTTPServer):
    def server_bind(self):  # без обратного DNS-запроса (getfqdn), который в изолированной сети подвисает
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[0], self.server_address[1]

port, bind = int(sys.argv[1]), sys.argv[2]
if len(sys.argv) > 3:
    os.chdir(sys.argv[3])
Server((bind, port), http.server.SimpleHTTPRequestHandler).serve_forever()
EOT
cat > /etc/systemd/system/lab-srvhttp.service <<'EOT'
[Service]
WorkingDirectory=/tmp
ExecStart=/usr/bin/nsenter --net=/run/netns/srv /usr/bin/python3 /opt/lab/httpd.py 8000 10.82.0.2 /tmp
[Install]
WantedBy=multi-user.target
EOT
listener closed 9999 closed
systemctl daemon-reload; systemctl enable --now lab-srvhttp >/dev/null 2>&1
nft flush ruleset
nft add table inet filter
nft add chain inet filter input '{ type filter hook input priority 0; policy drop; }'
nft add rule inet filter input iif lo accept
sleep 1
""",
    exercise="true\n",
    validate=NSX + PROBE + r"""
chk outbound_works 'curl -s -m 4 -o /dev/null -w "%{http_code}" http://10.82.0.2:8000/ | grep -q 200'
chk still_closed '! probe srv 10.82.0.1 9999 && nft list chain inet filter input | grep -q "policy drop"'
chk explained 'grep -qi established /home/student/why.txt && grep -qi conntrack /home/student/why.txt'
""",
    solution=r"""
sudo nft insert rule inet filter input ct state established,related accept
echo "Ответы на исходящие соединения входят в ту же conntrack-запись; без правила ct state established,related политика drop их отбрасывает (conntrack отслеживает состояние)." > ~/why.txt
""",
    wrong="sudo nft flush ruleset\nsudo nft add table inet filter\nsudo nft add chain inet filter input '{ type filter hook input priority 0; policy accept; }'\n",
)

lab(
    id="ld-107", title="Инцидент: неверное правило блокирует healthcheck после деплоя",
    description="После обновления правил балансировщик перестал получать ответ healthcheck. Найдите виновное правило по счётчикам и удалите именно его.",
    skills=["nft list ruleset -a", "counter", "delete rule handle", "порядок правил"],
    objectives=["Найти правило по росту счётчиков", "Удалить по handle", "Не сломать остальные правила"],
    minutes=25,
    task=NSNOTE + """\
**Инцидент.** Узел `hc` (`10.83.0.2`) проверяет `10.83.0.1:8080` и после деплоя правил получает таймаут. Остальные правила (SSH с `10.83.0.0/24`, остальной ruleset) должны остаться как есть.

Найдите по счётчикам (`sudo nft -a list ruleset`, после нескольких проверок с `hc`) правило, которое отбрасывает healthcheck, и **удалите именно его** (`nft delete rule ... handle N`), не сбрасывая весь ruleset.
""",
    hints=["Отправьте несколько проверок: `sudo nsenter --net=/run/netns/hc nc -z -w2 10.83.0.1 8080` — у виновного правила вырастет `packets`.", "`sudo nft delete rule inet filter input handle N`."],
    exercise_timeout=15,
    checks=[
        ("healthcheck_ok", "Healthcheck проходит", "Healthcheck проходит", "hc не может подключиться к 10.83.0.1:8080"),
        ("others_kept", "Остальные правила на месте", "Остальные правила сохранены", "Правила для SSH и policy drop должны остаться"),
        ("bad_rule_gone", "Виновного правила нет", "Виновное правило удалено", "Правило с drop для порта 8080 всё ещё в ruleset"),
    ],
    setup=NODE + r"""
node hc hh0 h0 10.83.0.2/24 10.83.0.1/24
listener app 8080 app-ok
listener ssh 22 ssh
nft flush ruleset
nft -f - <<'EOT'
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        tcp dport 8080 ip saddr 10.83.0.0/24 counter drop
        ip saddr 10.83.0.0/24 tcp dport 22 counter accept
        ip saddr 10.83.0.0/24 tcp dport 8080 counter accept
        icmp type echo-request accept
    }
}
EOT
""",
    exercise="true\n",
    validate=NSX + PROBE + r"""
chk healthcheck_ok 'probe hc 10.83.0.1 8080'
chk others_kept 'nft list chain inet filter input | grep -q "policy drop" && nft list chain inet filter input | grep -q "tcp dport 22" && probe hc 10.83.0.1 22'
chk bad_rule_gone '! nft list chain inet filter input | grep -E "tcp dport 8080" | grep -q drop'
""",
    solution=r"""
sudo nsenter --net=/run/netns/hc nc -z -w2 10.83.0.1 8080 || true
h=$(sudo nft -a list chain inet filter input | grep -E 'dport 8080.*drop' | grep -o 'handle [0-9]*' | awk '{print $2}')
sudo nft delete rule inet filter input handle $h
""",
    wrong="sudo nft flush ruleset\n",
)

lab(
    id="ld-108", title="DNAT к backend с сохранением реального адреса клиента",
    description="Настройте перенаправление порта на backend так, чтобы backend видел настоящий IP клиента, а не адрес маршрутизатора.",
    skills=["nft nat prerouting", "dnat to", "ip_forward", "masquerade vs без SNAT"],
    objectives=["Настроить DNAT", "Разрешить forwarding", "Не маскарадить трафик"],
    minutes=35,
    task=NSNOTE + """\
Схема: клиент **`cli`** (`10.84.1.2`) → **машина** (`10.84.1.1`, порт `8080`) → backend **`be`** (`10.84.2.2`, порт `80`, возвращает `backend`, логирует адрес клиента в `/var/lib/lab/seen`).

Настройте на машине:

- включённый `net.ipv4.ip_forward`;
- DNAT: запросы на `10.84.1.1:8080` перенаправляются на `10.84.2.2:80` (таблица `ip nat`, цепочка prerouting);
- правило разрешающего forward, если у вас включён firewall;
- **без masquerade/SNAT**: backend должен видеть адрес клиента `10.84.1.2`.

Проверка: `curl http://10.84.1.1:8080/` из `cli` возвращает `backend`, а в `seen` — `10.84.1.2`.
""",
    hints=["`sudo sysctl -w net.ipv4.ip_forward=1`; `table ip nat { chain prerouting { type nat hook prerouting priority -100; tcp dport 8080 dnat to 10.84.2.2:80 } }`.", "Backend знает путь обратно через машину (default via 10.84.2.1), поэтому SNAT не нужен."],
    exercise_timeout=15,
    checks=[
        ("dnat_works", "cli получает ответ backend", "DNAT работает", "curl http://10.84.1.1:8080/ из cli не возвращает backend"),
        ("client_ip_kept", "backend видит 10.84.1.2", "Адрес клиента сохранён", "backend видит адрес не клиента (проверьте, что нет masquerade/SNAT)"),
        ("forward_on", "ip_forward=1", "Forwarding включён", "net.ipv4.ip_forward должен быть 1"),
    ],
    setup=NODE + r"""
node cli hc1 c1 10.84.1.2/24 10.84.1.1/24
node be hb1 b1 10.84.2.2/24 10.84.2.1/24
nsenter --net=/run/netns/cli ip route add default via 10.84.1.1
nsenter --net=/run/netns/be ip route add default via 10.84.2.1
sysctl -qw net.ipv4.ip_forward=0
install -d /opt/lab /var/lib/lab
cat > /opt/lab/be.py <<'EOT'
import http.server, socketserver

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        with open("/var/lib/lab/seen", "a") as f:
            f.write(self.client_address[0] + "\n")
        body = b"backend\n"
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a):
        pass

socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("10.84.2.2", 80), H).serve_forever()
EOT
cat > /etc/systemd/system/lab-be.service <<'EOT'
[Service]
ExecStart=/usr/bin/nsenter --net=/run/netns/be /usr/bin/python3 /opt/lab/be.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload; systemctl enable --now lab-be >/dev/null 2>&1
nft flush ruleset
sleep 1
""",
    exercise=": > /dev/null\ntrue\n",
    validate=NSX + r"""
sudo_t() { :; }
: > /var/lib/lab/seen
out=$(NS cli curl -s -m 4 http://10.84.1.1:8080/ | tr -d "\n")
chk dnat_works '[ "$out" = backend ]'
chk client_ip_kept '[ "$(tail -n 1 /var/lib/lab/seen)" = 10.84.1.2 ]'
chk forward_on '[ "$(sysctl -n net.ipv4.ip_forward)" = 1 ]'
""",
    solution=r"""
sudo sysctl -w net.ipv4.ip_forward=1
sudo nft -f - <<'EOT'
table ip nat {
    chain prerouting {
        type nat hook prerouting priority -100; policy accept;
        tcp dport 8080 dnat to 10.84.2.2:80
    }
}
EOT
""",
    wrong="sudo sysctl -w net.ipv4.ip_forward=1\nsudo nft -f - <<'EOT'\ntable ip nat {\n    chain prerouting { type nat hook prerouting priority -100; tcp dport 8080 dnat to 10.84.2.2:80 }\n    chain postrouting { type nat hook postrouting priority 100; masquerade }\n}\nEOT\n",
)

lab(
    id="ld-109", title="Атомарное применение ruleset: проверка синтаксиса и откат",
    description="Подготовьте откат, проверьте новый ruleset без применения и примените его одной атомарной операцией.",
    skills=["nft -c -f", "nft -f", "flush ruleset", "rollback"],
    objectives=["Сохранить текущее состояние для отката", "Найти ошибку в черновике", "Применить одной транзакцией"],
    minutes=25,
    task="""\
Текущий ruleset разрешает SSH (22). Новый черновик лежит в `/etc/lab/new.nft`: он добавляет порт `8443`, но в нём синтаксическая ошибка.

1. Сохраните **текущий** ruleset для отката в `/etc/lab/rollback.nft` (`nft list ruleset`; файл должен проходить `nft -c -f`).
2. Проверьте черновик без применения (`nft -c -f /etc/lab/new.nft`), исправьте ошибку.
3. Примените исправленный `/etc/lab/new.nft` целиком (`nft -f`). После применения правила для SSH должны остаться, а порт 8443 — быть открыт.
""",
    hints=["`sudo sh -c 'nft list ruleset > /etc/lab/rollback.nft'`.", "`sudo nft -c -f /etc/lab/new.nft` покажет строку с ошибкой (опечатка в ключевом слове)."],
    checks=[
        ("rollback_saved", "rollback.nft: прежний ruleset", "Откат подготовлен", "Нужен /etc/lab/rollback.nft с прежними правилами (порт 22), проходящий nft -c -f"),
        ("new_applied", "Новый ruleset применён", "Новый ruleset применён", "В действующем ruleset нет правила для порта 8443"),
        ("ssh_kept", "SSH не потерян", "Доступ по SSH сохранён", "В ruleset пропало правило для порта 22"),
        ("draft_valid", "new.nft проходит проверку", "Черновик исправлен", "/etc/lab/new.nft не проходит nft -c -f"),
    ],
    setup=r"""
install -d /etc/lab
nft flush ruleset
nft -f - <<'EOT'
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        tcp dport 22 accept
    }
}
EOT
cat > /etc/lab/new.nft <<'EOT'
flush ruleset
table inet filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        tcp dport 22 accept
        tcp dport 8443 acept
    }
}
EOT
""",
    validate=r"""
chk rollback_saved 'nft -c -f /etc/lab/rollback.nft && grep -q "dport 22" /etc/lab/rollback.nft && ! grep -q "8443" /etc/lab/rollback.nft'
chk new_applied 'nft list ruleset | grep -q "dport 8443"'
chk ssh_kept 'nft list ruleset | grep -q "dport 22"'
chk draft_valid 'nft -c -f /etc/lab/new.nft'
""",
    solution=r"""
sudo sh -c 'nft list ruleset > /etc/lab/rollback.nft'
sudo sed -i 's/acept/accept/' /etc/lab/new.nft
sudo nft -c -f /etc/lab/new.nft
sudo nft -f /etc/lab/new.nft
""",
    wrong="sudo sed -i 's/acept/accept/' /etc/lab/new.nft\nsudo nft -f /etc/lab/new.nft\n",
)

lab(
    id="ld-110", title="Доступно по IPv4, но открыто лишним клиентам по IPv6",
    description="Правила ограничивают только IPv4. Выровняйте политику для IPv6, не ломая доступ разрешённого клиента.",
    skills=["inet table", "ip6 saddr", "nft", "dual-stack"],
    objectives=["Обнаружить дыру в IPv6", "Описать политику для обоих семейств", "Проверить обе стороны"],
    minutes=30,
    task=NSNOTE + """\
Сервис на порту `8080` должен быть доступен только клиенту `ok` (`10.85.0.2` / `fd00:85::2`). Лишний клиент `bad` (`10.85.1.2` / `fd00:85:1::2`) по IPv4 заблокирован, но по IPv6 всё ещё подключается.

Исправьте политику (желательно одной таблицей `inet`), чтобы:

- `ok` подключался и по IPv4, и по IPv6;
- `bad` не подключался ни по IPv4, ни по IPv6;
- остальные правила (SSH `22`) остались.
""",
    hints=["`sudo nft list ruleset` — нет ни одного правила для `ip6`.", "Добавьте `ip6 saddr fd00:85::/64 tcp dport 8080 accept` (при policy drop остальное блокируется)."],
    exercise_timeout=15,
    checks=[
        ("ok_both", "ok: IPv4 и IPv6", "Разрешённый клиент работает", "Клиент ok должен подключаться и по IPv4, и по IPv6"),
        ("bad_blocked_both", "bad: ни IPv4, ни IPv6", "Лишний клиент заблокирован", "Клиент bad подключается по IPv4 или IPv6"),
        ("ssh_kept", "Правило SSH сохранено", "SSH сохранён", "Правило для порта 22 пропало"),
    ],
    setup=NODE + r"""
node ok hk0 k0 10.85.0.2/24 10.85.0.1/24
node bad hx0 x0 10.85.1.2/24 10.85.1.1/24
ip -6 addr add fd00:85::1/64 dev hk0 nodad; nsenter --net=/run/netns/ok ip -6 addr add fd00:85::2/64 dev k0 nodad
ip -6 addr add fd00:85:1::1/64 dev hx0 nodad; nsenter --net=/run/netns/bad ip -6 addr add fd00:85:1::2/64 dev x0 nodad
mkdir -p /opt/lab
cat > /opt/lab/listen6.py <<'EOT'
import socket
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
s.bind(("::", 8080)); s.listen(20)
while True:
    c, _ = s.accept(); c.sendall(b"ok\n"); c.close()
EOT
cat > /etc/systemd/system/lab-dual.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/listen6.py
[Install]
WantedBy=multi-user.target
EOT
listener ssh 22 ssh
systemctl daemon-reload; systemctl enable --now lab-dual >/dev/null 2>&1
nft flush ruleset
nft -f - <<'EOT'
table ip filter {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        ip saddr 10.85.0.0/24 tcp dport 8080 accept
        tcp dport 22 accept
    }
}
table ip6 filter6 {
    chain input {
        type filter hook input priority 0; policy accept;
    }
}
EOT
sleep 1
""",
    exercise="true\n",
    validate=NSX + r"""
p6() { nsenter --net=/run/netns/$1 nc -6 -z -w2 $2 $3; }
p4() { nsenter --net=/run/netns/$1 nc -z -w2 $2 $3; }
chk ok_both 'p4 ok 10.85.0.1 8080 && p6 ok fd00:85::1 8080'
chk bad_blocked_both '! p4 bad 10.85.1.1 8080 && ! p6 bad fd00:85:1::1 8080'
chk ssh_kept 'nft list ruleset | grep -q "dport 22"'
""",
    solution=r"""
sudo nft -f - <<'EOT'
flush table ip6 filter6
table ip6 filter6 {
    chain input {
        type filter hook input priority 0; policy drop;
        iif lo accept
        ct state established,related accept
        icmpv6 type { nd-neighbor-solicit, nd-neighbor-advert, nd-router-solicit, nd-router-advert, echo-request } accept
        ip6 saddr fd00:85::/64 tcp dport 8080 accept
        tcp dport 22 accept
    }
}
EOT
""",
    wrong="sudo nft flush ruleset\n",
)

lab(
    id="ld-111", title="Изоляция metadata-endpoint от учебной нагрузки на сетевом уровне",
    description="Закройте служебный адрес (metadata) для узла-нагрузки, оставив ей доступ к обычному приложению.",
    skills=["nft", "169.254.169.254", "изоляция сегментов", "fwd/input"],
    objectives=["Определить, что доступно нагрузке", "Закрыть только metadata", "Не сломать приложение"],
    minutes=25,
    task=NSNOTE + """\
На машине есть служебный адрес `169.254.169.254` (порт 80 — «metadata», в ответе секретный токен) и приложение `10.86.0.1:8080`. Узел-нагрузка **`wl`** (`10.86.0.2`) не должен иметь доступа к metadata, но приложение должно оставаться доступным.

Настройте nftables:

- `wl` **не** подключается к `169.254.169.254:80`;
- `wl` подключается к `10.86.0.1:8080`;
- сама машина по-прежнему обращается к metadata.

Подсказка: адрес `169.254.169.254` принадлежит машине, значит трафик идёт в цепочку `input`.
""",
    hints=["`ip saddr 10.86.0.0/24 ip daddr 169.254.169.254 tcp dport 80 drop` в цепочке `input`.", "Не используйте общий `policy drop` без разрешений: приложение на 8080 должно остаться доступным."],
    exercise_timeout=15,
    checks=[
        ("metadata_blocked", "wl не достучится до metadata", "Metadata закрыт для нагрузки", "wl подключается к 169.254.169.254:80"),
        ("app_open", "wl → приложение 8080 работает", "Приложение доступно", "wl не подключается к 10.86.0.1:8080"),
        ("host_still_ok", "Машина читает metadata", "Машина по-прежнему видит metadata", "Сама машина не может подключиться к metadata"),
    ],
    setup=NODE + r"""
node wl hw0 w0 10.86.0.2/24 10.86.0.1/24
nsenter --net=/run/netns/wl ip route add 169.254.169.254/32 via 10.86.0.1
ip link add meta0 type dummy; ip addr add 169.254.169.254/32 dev meta0; ip link set meta0 up
mkdir -p /opt/lab
cat > /opt/lab/meta.py <<'EOT'
import socket
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("169.254.169.254", 80)); s.listen(20)
while True:
    c, _ = s.accept(); c.sendall(b"TOKEN-SECRET\n"); c.close()
EOT
cat > /etc/systemd/system/lab-meta.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/meta.py
[Install]
WantedBy=multi-user.target
EOT
listener app 8080 app
systemctl daemon-reload; systemctl enable --now lab-meta >/dev/null 2>&1
nft flush ruleset
sleep 1
""",
    exercise="true\n",
    validate=NSX + PROBE + r"""
chk metadata_blocked '! probe wl 169.254.169.254 80'
chk app_open 'probe wl 10.86.0.1 8080'
chk host_still_ok 'nc -z -w2 169.254.169.254 80'
""",
    solution=r"""
sudo nft -f - <<'EOT'
table inet filter {
    chain input {
        type filter hook input priority 0; policy accept;
        ip saddr 10.86.0.0/24 ip daddr 169.254.169.254 tcp dport 80 drop
    }
}
EOT
""",
    wrong="sudo nft -f - <<'EOT'\ntable inet filter {\n    chain input {\n        type filter hook input priority 0; policy drop;\n    }\n}\nEOT\n",
)

lab(
    id="ld-170", title="Периодический backup приложения с ротацией и проверкой",
    description="Настройте резервное копирование по расписанию: архив, проверка целостности и хранение только последних копий.",
    skills=["tar", "systemd timer / cron", "ротация", "проверка архива"],
    objectives=["Написать скрипт backup", "Запускать по расписанию", "Хранить последние три копии и проверять каждую"],
    minutes=35,
    task="""\
Данные приложения лежат в `/var/lib/labapp/data` (файлы `users.db`, `settings.conf`, каталог `uploads/`). Настройте резервное копирование:

- скрипт `/usr/local/bin/lab-backup.sh` создаёт архив `/var/backups/labapp/labapp-<время>.tar.gz` (время с точностью до секунды), **проверяет** его (`tar -tzf`) и пишет рядом файл `.sha256`;
- хранятся только **3 последних** архива (старые удаляются);
- запуск по расписанию — systemd-таймер `lab-backup.timer` (служба `lab-backup.service`), включённый (`enabled`).

Проверка запустит `lab-backup.service` несколько раз подряд.
""",
    hints=["В скрипте: `ts=$(date +%Y%m%d-%H%M%S)`, `tar -czf`, `tar -tzf` для проверки, `sha256sum`, затем `ls -1t ... | tail -n +4 | xargs -r rm`.", "Таймер: `[Timer] OnCalendar=daily`, `Persistent=true`; `sudo systemctl enable --now lab-backup.timer`."],
    exercise_timeout=40,
    checks=[
        ("rotation_ok", "После 5 запусков осталось ровно 3 архива", "Ротация работает", "После нескольких запусков должно остаться ровно 3 архива с .sha256"),
        ("archive_valid", "Новейший архив содержит данные и валиден", "Архив валиден", "Новейший архив повреждён или не содержит users.db, settings.conf и uploads/"),
        ("timer_enabled", "Таймер включён и имеет расписание", "Расписание настроено", "lab-backup.timer должен быть enabled и иметь OnCalendar"),
    ],
    setup=r"""
install -d /var/lib/labapp/data/uploads /var/backups/labapp
echo "users" > /var/lib/labapp/data/users.db; echo "port=1" > /var/lib/labapp/data/settings.conf; echo f1 > /var/lib/labapp/data/uploads/a.txt
""",
    exercise=r"""
for i in 1 2 3 4 5; do sudo systemctl start lab-backup.service; sleep 1.2; done
true
""",
    validate=r"""
D=/var/backups/labapp
newest=$(ls -1t $D/labapp-*.tar.gz 2>/dev/null | head -n 1)
chk rotation_ok '[ "$(ls $D/labapp-*.tar.gz 2>/dev/null | wc -l)" = 3 ] && [ "$(ls $D/labapp-*.sha256 2>/dev/null | wc -l)" -ge 1 ]'
chk archive_valid '[ -n "$newest" ] && tar -tzf "$newest" > /tmp/.list 2>/dev/null && grep -q users.db /tmp/.list && grep -q settings.conf /tmp/.list && grep -q "uploads/" /tmp/.list'
chk timer_enabled 'systemctl is-enabled --quiet lab-backup.timer && systemctl cat lab-backup.timer | grep -q "^OnCalendar="'
""",
    solution=r"""
sudo tee /usr/local/bin/lab-backup.sh > /dev/null <<'EOT'
#!/bin/bash
set -euo pipefail
D=/var/backups/labapp
ts=$(date +%Y%m%d-%H%M%S)
f=$D/labapp-$ts.tar.gz
tar -czf "$f" -C /var/lib/labapp data
tar -tzf "$f" > /dev/null
(cd "$D" && sha256sum "$(basename "$f")" > "$(basename "$f").sha256")
ls -1t $D/labapp-*.tar.gz | tail -n +4 | while read -r old; do rm -f "$old" "$old.sha256"; done
EOT
sudo chmod 755 /usr/local/bin/lab-backup.sh
sudo tee /etc/systemd/system/lab-backup.service > /dev/null <<'EOT'
[Service]
Type=oneshot
ExecStart=/usr/local/bin/lab-backup.sh
EOT
sudo tee /etc/systemd/system/lab-backup.timer > /dev/null <<'EOT'
[Timer]
OnCalendar=daily
Persistent=true
[Install]
WantedBy=timers.target
EOT
sudo systemctl daemon-reload
sudo systemctl enable --now lab-backup.timer
""",
    wrong="sudo tee /usr/local/bin/lab-backup.sh > /dev/null <<'EOT'\n#!/bin/bash\ntar -czf /var/backups/labapp/labapp-$(date +%s).tar.gz /var/lib/labapp/data\nEOT\nsudo chmod 755 /usr/local/bin/lab-backup.sh\nsudo tee /etc/systemd/system/lab-backup.service > /dev/null <<'EOT'\n[Service]\nType=oneshot\nExecStart=/usr/local/bin/lab-backup.sh\nEOT\nsudo systemctl daemon-reload\n",
)

lab(
    id="ld-171", title="Backup «успешен», но важных файлов в нём нет",
    description="Резервная копия создаётся без ошибок, но в архиве нет нужных данных из-за неверных путей и исключений.",
    skills=["tar --exclude", "tar -tzf", "проверка содержимого backup", "пути"],
    objectives=["Проверить содержимое архива, а не только код возврата", "Найти ошибку в скрипте", "Исправить и убедиться"],
    minutes=25,
    task="""\
**Инцидент.** Скрипт `/usr/local/bin/lab-backup2.sh` отрабатывает с кодом 0 и создаёт `/var/backups/labapp2/latest.tar.gz`, но при восстановлении выясняется, что в нём нет базы и загрузок пользователей.

Критичные данные: `/var/lib/labapp2/db/main.db`, `/var/lib/labapp2/uploads/*`, `/etc/labapp2/app.conf`.

Исправьте скрипт так, чтобы архив содержал **все три** группы файлов (при этом временные файлы `*.tmp` в архив попадать не должны), и **проверьте содержимое** `tar -tzf`. Проверка запустит скрипт сама.
""",
    hints=["`tar -tzf /var/backups/labapp2/latest.tar.gz` — посмотрите, что реально лежит в архиве.", "Ищите ошибочный путь и слишком широкий `--exclude` в скрипте."],
    exercise_timeout=20,
    checks=[
        ("db_included", "В архиве main.db", "База в архиве", "В архиве нет базы /var/lib/labapp2/db/main.db"),
        ("uploads_included", "В архиве uploads", "Загрузки в архиве", "В архиве нет загрузок пользователей"),
        ("config_included", "В архиве app.conf", "Конфиг в архиве", "В архиве нет /etc/labapp2/app.conf"),
        ("tmp_excluded", "Временных файлов нет", "Временные файлы исключены", "В архиве не должно быть *.tmp"),
    ],
    setup=r"""
install -d /var/lib/labapp2/db /var/lib/labapp2/uploads /etc/labapp2 /var/backups/labapp2
echo db > /var/lib/labapp2/db/main.db; echo up1 > /var/lib/labapp2/uploads/photo.jpg; echo cache > /var/lib/labapp2/uploads/cache.tmp
echo cfg > /etc/labapp2/app.conf
cat > /usr/local/bin/lab-backup2.sh <<'EOT'
#!/bin/bash
set -e
tar -czf /var/backups/labapp2/latest.tar.gz --exclude='db' --exclude='*.tmp' /var/lib/labapp2/uploadz /etc/labapp 2>/dev/null || true
EOT
chmod 755 /usr/local/bin/lab-backup2.sh
""",
    exercise="sudo rm -f /var/backups/labapp2/latest.tar.gz\nsudo /usr/local/bin/lab-backup2.sh\ntrue\n",
    validate=r"""
tar -tzf /var/backups/labapp2/latest.tar.gz > /tmp/.l2 2>/dev/null
chk db_included 'grep -q "var/lib/labapp2/db/main.db" /tmp/.l2'
chk uploads_included 'grep -q "var/lib/labapp2/uploads/photo.jpg" /tmp/.l2'
chk config_included 'grep -q "etc/labapp2/app.conf" /tmp/.l2'
chk tmp_excluded '[ -s /tmp/.l2 ] && ! grep -q "\.tmp$" /tmp/.l2'
""",
    solution=r"""
sudo tee /usr/local/bin/lab-backup2.sh > /dev/null <<'EOT'
#!/bin/bash
set -e
tar -czf /var/backups/labapp2/latest.tar.gz --exclude='*.tmp' /var/lib/labapp2 /etc/labapp2
tar -tzf /var/backups/labapp2/latest.tar.gz > /dev/null
EOT
""",
    wrong="sudo sed -i \"s/--exclude='db' //\" /usr/local/bin/lab-backup2.sh\n",
)

lab(
    id="ld-172", title="Согласованный backup приложения и БД и восстановление",
    description="Снимите непротиворечивую копию SQLite-базы под нагрузкой и убедитесь, что восстановление работает.",
    skills=["sqlite3 .backup", "integrity_check", "согласованность", "restore"],
    objectives=["Понять, почему cp под записью опасен", "Снять копию средствами БД", "Восстановить и проверить"],
    minutes=30,
    task="""\
Служба `labdb-writer.service` непрерывно пишет в `/var/lib/labapp/orders.db` (SQLite). Обычный `cp` под записью может дать повреждённую копию.

1. Снимите **согласованную** копию в `/var/backups/labapp/orders.bak` (используйте встроенный механизм: `sqlite3 ... ".backup ..."`).
2. **Восстановите** копию как новую базу `/var/lib/labapp/restored.db` и убедитесь, что `PRAGMA integrity_check` возвращает `ok`, а таблица `orders` не пуста.
3. Рабочую базу не останавливайте и не меняйте.
""",
    hints=["`sudo sqlite3 /var/lib/labapp/orders.db \".backup '/var/backups/labapp/orders.bak'\"`.", "Восстановление: `sudo cp /var/backups/labapp/orders.bak /var/lib/labapp/restored.db` и `sqlite3 ... 'PRAGMA integrity_check'`."],
    exercise_timeout=20,
    checks=[
        ("backup_valid", "orders.bak проходит integrity_check", "Копия согласована", "orders.bak повреждена или не является корректной базой SQLite"),
        ("restore_valid", "restored.db восстановлена, orders не пуста", "Восстановление проверено", "restored.db отсутствует, повреждена или таблица orders пуста"),
        ("source_running", "Источник работает и растёт", "Рабочая база не затронута", "Служба-писатель остановлена или база не обновляется"),
    ],
    setup=r"""
install -d /opt/lab /var/lib/labapp /var/backups/labapp
cat > /opt/lab/writer.py <<'EOT'
import sqlite3, time
db = sqlite3.connect("/var/lib/labapp/orders.db", isolation_level=None)
db.execute("PRAGMA journal_mode=WAL")
db.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, ts REAL, note TEXT)")
while True:
    db.execute("INSERT INTO orders (ts, note) VALUES (?, ?)", (time.time(), "x" * 200))
    time.sleep(0.02)
EOT
cat > /etc/systemd/system/labdb-writer.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/writer.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labdb-writer >/dev/null 2>&1
sleep 2
""",
    exercise="true\n",
    validate=r"""
n1=$(sqlite3 /var/lib/labapp/orders.db "select count(*) from orders"); sleep 1; n2=$(sqlite3 /var/lib/labapp/orders.db "select count(*) from orders")
chk backup_valid '[ "$(sqlite3 /var/backups/labapp/orders.bak "PRAGMA integrity_check")" = ok ] && [ "$(sqlite3 /var/backups/labapp/orders.bak "select count(*) from orders")" -gt 0 ]'
chk restore_valid '[ "$(sqlite3 /var/lib/labapp/restored.db "PRAGMA integrity_check")" = ok ] && [ "$(sqlite3 /var/lib/labapp/restored.db "select count(*) from orders")" -gt 0 ]'
chk source_running 'systemctl is-active --quiet labdb-writer && [ "$n2" -gt "$n1" ]'
""",
    solution=r"""
sudo sqlite3 /var/lib/labapp/orders.db ".backup '/var/backups/labapp/orders.bak'"
sudo cp /var/backups/labapp/orders.bak /var/lib/labapp/restored.db
sqlite3 /var/lib/labapp/restored.db "PRAGMA integrity_check"
""",
    wrong="sudo cp /var/lib/labapp/orders.db /var/backups/labapp/orders.bak\n",
)

lab(
    id="ld-173", title="Измерение реальных RPO и RTO на учебном отказе",
    description="По журналу событий отказа посчитайте фактические RPO и RTO и сравните с целевыми.",
    skills=["RPO", "RTO", "журнал событий", "timeline"],
    objectives=["Построить хронологию", "Посчитать потерю данных и время восстановления", "Сравнить с целями"],
    minutes=20,
    task="""\
Журнал учебного отказа: `/var/lib/lab/events.log` (формат `ЧЧ:ММ:СС событие`). События: `backup_done` (может быть несколько), `failure`, `restore_start`, `restore_done`. Целевые значения: **RPO 15 минут**, **RTO 30 минут**.

Запишите в `~/rpo.txt`:

```
rpo_minutes=<сколько минут данных потеряно: от последнего backup_done до failure, целое число минут>
rto_minutes=<сколько минут заняло восстановление: от failure до restore_done>
rpo_met=<yes|no>
rto_met=<yes|no>
```
""",
    hints=["Последний `backup_done` до `failure` — граница потерянных данных (RPO).", "RTO считается от `failure` до `restore_done` (а не от `restore_start`)."],
    checks=[
        ("rpo_ok", "rpo_minutes верен", "RPO посчитан", "rpo_minutes не совпадает с интервалом между последним backup_done и failure"),
        ("rto_ok", "rto_minutes верен", "RTO посчитан", "rto_minutes не совпадает с интервалом failure → restore_done"),
        ("goals_ok", "rpo_met / rto_met верны", "Соответствие целям определено", "rpo_met/rto_met не соответствуют целям (15 и 30 минут)"),
    ],
    setup=r"""
install -d /var/lib/lab
cat > /var/lib/lab/events.log <<'EOT'
02:00:05 backup_done
02:15:04 backup_done
02:30:06 backup_done
02:47:30 failure
02:55:10 restore_start
03:26:40 restore_done
EOT
""",
    validate=r"""
F=/home/student/rpo.txt
v() { grep "^$1=" $F | cut -d= -f2- | tr -d ' '; }
chk rpo_ok '[ "$(v rpo_minutes)" = 17 ]'
chk rto_ok '[ "$(v rto_minutes)" = 39 ]'
chk goals_ok '[ "$(v rpo_met)" = no ] && [ "$(v rto_met)" = no ]'
""",
    solution="printf 'rpo_minutes=17\\nrto_minutes=39\\nrpo_met=no\\nrto_met=no\\n' > ~/rpo.txt\n",
    wrong="printf 'rpo_minutes=0\\nrto_minutes=31\\nrpo_met=yes\\nrto_met=yes\\n' > ~/rpo.txt\n",
)

lab(
    id="ld-175", title="Тест восстановления после удаления тома",
    description="Данные потеряны вместе с каталогом. Восстановите их из backup и проверьте контрольные суммы по манифесту.",
    skills=["tar -xzf", "sha256sum -c", "манифест", "проверка восстановления"],
    objectives=["Восстановить из архива", "Сверить контрольные суммы", "Убедиться в полноте"],
    minutes=25,
    task="""\
**Инцидент.** Каталог данных `/srv/vol` с приложением был очищен. Резервная копия: `/var/backups/vol/vol-backup.tar.gz`, манифест контрольных сумм: `/var/backups/vol/MANIFEST.sha256` (пути относительно `/srv/vol`).

Восстановите данные в `/srv/vol` и убедитесь, что **все** файлы совпадают с манифестом (`sha256sum -c`). Манифест и архив менять нельзя.
""",
    hints=["`sudo tar -xzf /var/backups/vol/vol-backup.tar.gz -C /srv/vol`.", "Проверка: `cd /srv/vol && sha256sum -c /var/backups/vol/MANIFEST.sha256`."],
    checks=[
        ("files_restored", "Все файлы манифеста на месте", "Файлы восстановлены", "Не все файлы из манифеста восстановлены в /srv/vol"),
        ("checksums_ok", "sha256sum -c проходит", "Контрольные суммы сходятся", "Контрольные суммы не совпадают с манифестом"),
        ("backup_untouched", "Архив и манифест не изменены", "Резервная копия цела", "Архив или манифест изменены"),
    ],
    setup=r"""
install -d /srv/vol/data /srv/vol/conf /var/backups/vol
for i in 1 2 3 4 5; do echo "record $i" > /srv/vol/data/r$i.txt; done
echo "mode=prod" > /srv/vol/conf/app.conf
(cd /srv/vol && find . -type f | sort | xargs sha256sum | sed 's# \./# #' > /var/backups/vol/MANIFEST.sha256)
tar -czf /var/backups/vol/vol-backup.tar.gz -C /srv/vol .
sha256sum /var/backups/vol/vol-backup.tar.gz /var/backups/vol/MANIFEST.sha256 > /root/.vol.ref
rm -rf /srv/vol/*
""",
    validate=r"""
chk files_restored '[ "$(wc -l < /var/backups/vol/MANIFEST.sha256)" = 6 ] && ( while read -r s f; do [ -f "/srv/vol/$f" ] || exit 1; done < /var/backups/vol/MANIFEST.sha256 )'
chk checksums_ok '(cd /srv/vol && sha256sum -c /var/backups/vol/MANIFEST.sha256 >/dev/null 2>&1)'
chk backup_untouched 'sha256sum -c /root/.vol.ref >/dev/null 2>&1'
""",
    solution=r"""
sudo tar -xzf /var/backups/vol/vol-backup.tar.gz -C /srv/vol
cd /srv/vol && sha256sum -c /var/backups/vol/MANIFEST.sha256
""",
    wrong="sudo mkdir -p /srv/vol/data\necho 'record 1' | sudo tee /srv/vol/data/r1.txt > /dev/null\n",
)
