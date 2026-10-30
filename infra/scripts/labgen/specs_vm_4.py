"""Задания на учебной машине (LXD), партия 4: сеть на network namespace (вместо нескольких узлов), DNS, SSH, TLS, nginx.

В машине нельзя смонтировать /sys, поэтому `ip netns exec` и `ip -n` недоступны: команды в namespace выполняются через
`nsenter --net=/run/netns/<имя>`. Учебные «узлы» — network namespace, соединённые veth/bridge.
"""

from __future__ import annotations

SPECS: list[dict] = []


def lab(**kw: object) -> None:
    SPECS.append({"runtime_type": "lxd", **kw})


NSNOTE = (
    "> В учебной машине `ip netns exec` и `ip -n` недоступны (в контейнере нельзя смонтировать `/sys`). "
    "Команды внутри namespace выполняйте так: `sudo nsenter --net=/run/netns/ИМЯ команда`.\n\n"
)
NSX = 'NS() { n=$1; shift; nsenter --net=/run/netns/$n "$@"; }\n'

# Три «узла»: host ↔ r ↔ far (маршрутизация), а также общая PKI для заданий про TLS.
PKI = r"""
install -d /etc/lab/ca /etc/lab/tls
cd /etc/lab/ca
openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.crt -days 3650 -subj "/CN=Lab Root CA" >/dev/null 2>&1
"""

lab(
    id="ld-089", title="Путь пакета: адрес источника, интерфейс, шлюз и MAC соседа",
    description="По ip addr, ip route и ip neigh восстановите, как пакет покидает машину.",
    skills=["ip addr", "ip route get", "ip neigh", "ARP"],
    objectives=["Определить source IP и интерфейс", "Найти next hop по таблице маршрутов", "Прочитать MAC соседа из ARP"],
    minutes=15,
    task=NSNOTE + """\
Машина соединена с соседним узлом `peer` (network namespace) кабелем veth, адрес соседа `10.50.1.2`. К подсети `10.50.9.0/24` ведёт статический маршрут через него.

Запишите в `~/path.txt`:

```
src=<IP-адрес, с которого уходят пакеты к 10.50.1.2>
dev=<интерфейс, через который уходит трафик к 10.50.1.2>
via=<шлюз для адреса 10.50.9.5>
mac=<MAC-адрес соседа 10.50.1.2 из таблицы соседей>
```

Чтобы в таблице соседей появилась запись, сначала отправьте соседу `ping`.
""",
    hints=["`ip route get 10.50.1.2` — source IP и интерфейс; `ip route get 10.50.9.5` — шлюз (via).", "После `ping -c1 10.50.1.2` смотрите `ip neigh show 10.50.1.2`."],
    checks=[
        ("src_dev_ok", "src и dev", "Источник и интерфейс верны", "src и dev не совпадают с `ip route get 10.50.1.2`"),
        ("via_ok", "via для 10.50.9.5", "Шлюз определён", "via должен совпасть с next hop из `ip route get 10.50.9.5`"),
        ("mac_ok", "mac соседа", "MAC определён", "mac должен совпасть с MAC интерфейса соседа (ip neigh)"),
    ],
    setup=r"""
ip netns add peer
ip link add hv0 type veth peer name hv1
ip link set hv1 netns peer
ip addr add 10.50.1.1/24 dev hv0; ip link set hv0 up
nsenter --net=/run/netns/peer ip addr add 10.50.1.2/24 dev hv1
nsenter --net=/run/netns/peer ip link set hv1 up
nsenter --net=/run/netns/peer ip link set lo up
ip route add 10.50.9.0/24 via 10.50.1.2
""",
    validate=NSX + r"""
F=/home/student/path.txt
v() { grep "^$1=" $F | cut -d= -f2- | tr -d ' '; }
rg=$(ip route get 10.50.1.2)
chk src_dev_ok '[ "$(v src)" = "$(echo "$rg" | grep -o "src [0-9.]*" | cut -d" " -f2)" ] && [ "$(v dev)" = "$(echo "$rg" | grep -o "dev [a-z0-9]*" | cut -d" " -f2)" ]'
chk via_ok '[ "$(v via)" = "$(ip route get 10.50.9.5 | grep -o "via [0-9.]*" | cut -d" " -f2)" ]'
chk mac_ok '[ "$(v mac | tr A-Z a-z)" = "$(NS peer ip -br link show hv1 | awk "{print \$3}")" ]'
""",
    solution=r"""
ping -c1 -W2 10.50.1.2 >/dev/null
src=$(ip route get 10.50.1.2 | grep -o 'src [0-9.]*' | cut -d' ' -f2)
dev=$(ip route get 10.50.1.2 | grep -o 'dev [a-z0-9]*' | cut -d' ' -f2)
via=$(ip route get 10.50.9.5 | grep -o 'via [0-9.]*' | cut -d' ' -f2)
mac=$(ip neigh show 10.50.1.2 | awk '{print $5}')
printf 'src=%s\ndev=%s\nvia=%s\nmac=%s\n' "$src" "$dev" "$via" "$mac" > ~/path.txt
""",
    wrong="printf 'src=1.1.1.1\\ndev=eth0\\nvia=10.0.0.1\\nmac=00:00:00:00:00:00\\n' > ~/path.txt\n",
)

lab(
    id="ld-090", title="Неверная маска и подсеть на учебном интерфейсе",
    description="Интерфейс настроен в чужой подсети: узел не видит шлюз. Исправьте адрес и маску.",
    skills=["ip addr", "ip route", "маска сети", "ping"],
    objectives=["Увидеть несовпадение подсетей", "Исправить адрес и маску", "Проверить связь со шлюзом"],
    minutes=15,
    task=NSNOTE + """\
Интерфейс `hv0` подключён к шлюзу `10.60.0.1/24` (network namespace `gw`), но шлюз недоступен.

Исправьте настройку так, чтобы `hv0` имел адрес из подсети `10.60.0.0/24` с маской `/24` (например, `10.60.0.5/24`), без адреса шлюза, и `ping 10.60.0.1` проходил. Лишних адресов на `hv0` оставаться не должно.
""",
    hints=["`ip -br addr show hv0` и `ip route`. Адрес сейчас из другой подсети.", "`sudo ip addr flush dev hv0` и `sudo ip addr add 10.60.0.5/24 dev hv0`."],
    checks=[
        ("addr_ok", "hv0 в подсети 10.60.0.0/24", "Адрес и маска верны", "Адрес hv0 должен быть из 10.60.0.0/24 с маской /24 (но не 10.60.0.1)"),
        ("only_one_addr", "Единственный IPv4-адрес", "Лишних адресов нет", "На hv0 остались лишние IPv4-адреса"),
        ("gw_pingable", "Шлюз отвечает на ping", "Шлюз доступен", "Шлюз 10.60.0.1 не отвечает"),
    ],
    setup=r"""
ip netns add gw
ip link add hv0 type veth peer name gv0
ip link set gv0 netns gw
nsenter --net=/run/netns/gw ip addr add 10.60.0.1/24 dev gv0
nsenter --net=/run/netns/gw ip link set gv0 up
nsenter --net=/run/netns/gw ip link set lo up
ip addr add 10.60.1.5/24 dev hv0
ip link set hv0 up
""",
    validate=r"""
a=$(ip -4 -o addr show dev hv0 | awk '{print $4}')
chk addr_ok '[ "${a##*/}" = 24 ] && [ "${a%.*}" = 10.60.0 ] && [ "${a%/*}" != 10.60.0.1 ] && [ "${a%/*}" != 10.60.0.0 ] && [ "${a%/*}" != 10.60.0.255 ]'
chk only_one_addr '[ "$(ip -4 -o addr show dev hv0 | wc -l)" = 1 ]'
chk gw_pingable 'ping -c1 -W2 10.60.0.1'
""",
    solution="sudo ip addr flush dev hv0\nsudo ip addr add 10.60.0.5/24 dev hv0\nsudo ip link set hv0 up\n",
    wrong="sudo ip addr add 10.60.0.5/24 dev hv0\n",
)

lab(
    id="ld-091", title="Шлюз пингуется, а удалённая подсеть — нет: маршруты и forwarding",
    description="Найдите три причины недоступности удалённой подсети: нет маршрута на клиенте, выключен forwarding на маршрутизаторе, нет обратного маршрута.",
    skills=["ip route", "ip_forward", "traceroute", "обратный маршрут"],
    objectives=["Идти по пути пакета узел за узлом", "Включить forwarding", "Добавить маршруты в обе стороны"],
    minutes=30,
    task=NSNOTE + """\
Топология: **машина** (`10.61.0.1`) — **маршрутизатор** `r` (`10.61.0.2` / `10.62.0.2`) — узел `far` (`10.62.0.3`).

Машина пингует маршрутизатор (`10.61.0.2`), но **не** `10.62.0.3`. Найдите все причины и устраните:

- `ping 10.62.0.3` с машины должен проходить;
- маршрутизатор должен пересылать пакеты (`net.ipv4.ip_forward=1` внутри `r`);
- узлы `far` должен знать обратный путь к `10.61.0.0/24`.

Подсказка: проверяйте по очереди — таблицу маршрутов на машине, forwarding на `r`, маршрут на `far`.
""",
    hints=["На машине: `ip route` — нет маршрута к `10.62.0.0/24` через `10.61.0.2`.", "На `r`: `sudo nsenter --net=/run/netns/r sysctl net.ipv4.ip_forward` (должно быть 1); на `far`: `ip route` и маршрут обратно через `10.62.0.2`."],
    checks=[
        ("end_to_end", "ping машина → far", "Связь есть", "ping 10.62.0.3 не проходит"),
        ("forwarding_on", "ip_forward=1 в r", "Forwarding включён", "В namespace r выключен net.ipv4.ip_forward"),
        ("return_route", "far знает путь к 10.61.0.0/24", "Обратный маршрут есть", "На far нет маршрута к 10.61.0.0/24 через r"),
    ],
    setup=r"""
for n in r far; do ip netns add $n; done
ip link add hv0 type veth peer name rv0
ip link set rv0 netns r
ip link add rv1 type veth peer name fv1
ip link set rv1 netns r
ip link set fv1 netns far
ip addr add 10.61.0.1/24 dev hv0; ip link set hv0 up
R="nsenter --net=/run/netns/r"; F="nsenter --net=/run/netns/far"
$R ip addr add 10.61.0.2/24 dev rv0; $R ip link set rv0 up
$R ip addr add 10.62.0.2/24 dev rv1; $R ip link set rv1 up; $R ip link set lo up
$F ip addr add 10.62.0.3/24 dev fv1; $F ip link set fv1 up; $F ip link set lo up
$R sysctl -qw net.ipv4.ip_forward=0
""",
    validate=NSX + r"""
chk end_to_end 'ping -c1 -W2 10.62.0.3'
chk forwarding_on '[ "$(NS r sysctl -n net.ipv4.ip_forward)" = 1 ]'
chk return_route 'NS far ip route get 10.61.0.1 | grep -q "via 10.62.0.2"'
""",
    solution=r"""
sudo ip route add 10.62.0.0/24 via 10.61.0.2
sudo nsenter --net=/run/netns/r sysctl -w net.ipv4.ip_forward=1
sudo nsenter --net=/run/netns/far ip route add 10.61.0.0/24 via 10.62.0.2
""",
    wrong="sudo ip route add 10.62.0.0/24 via 10.61.0.2\n",
)

lab(
    id="ld-092", title="Виртуальный bridge: соединить два узла в один L2-сегмент",
    description="Создайте bridge и подключите к нему два узла так, чтобы они увидели друг друга без маршрутизации.",
    skills=["ip link add type bridge", "ip link set master", "L2-сегмент", "ping"],
    objectives=["Создать bridge", "Подключить порты", "Проверить связность на втором уровне"],
    minutes=20,
    task=NSNOTE + """\
Два узла `a` (`10.63.0.1/24`) и `b` (`10.63.0.2/24`) уже настроены, их кабели (veth) подключены к машине концами `ha` и `hb`, но не соединены между собой.

Создайте bridge `labbr0`, добавьте в него `ha` и `hb`, поднимите все интерфейсы так, чтобы `a` пинговал `b`. Адрес на bridge назначать не нужно.
""",
    hints=["`sudo ip link add labbr0 type bridge`; `sudo ip link set ha master labbr0`.", "Не забудьте `ip link set ... up` для bridge и обоих портов."],
    checks=[
        ("bridge_ports", "labbr0 с портами ha и hb", "Bridge собран", "Нужен bridge labbr0 с портами ha и hb"),
        ("ports_up", "bridge и порты UP", "Интерфейсы подняты", "Bridge и порты должны быть в состоянии UP"),
        ("a_pings_b", "a → b проходит", "Узлы видят друг друга", "ping из a в b не проходит"),
    ],
    setup=r"""
for n in a b; do ip netns add $n; ip link add h$n type veth peer name ${n}0; ip link set ${n}0 netns $n; done
nsenter --net=/run/netns/a ip addr add 10.63.0.1/24 dev a0; nsenter --net=/run/netns/a ip link set a0 up
nsenter --net=/run/netns/b ip addr add 10.63.0.2/24 dev b0; nsenter --net=/run/netns/b ip link set b0 up
""",
    validate=NSX + r"""
chk bridge_ports '[ "$(ip -br link show master labbr0 2>/dev/null | awk "{print \$1}" | sed "s/@.*//" | sort | tr "\n" " ")" = "ha hb " ]'
chk ports_up 'ip -br link show labbr0 | grep -q "UP" && [ "$(cat /sys/class/net/ha/operstate)" = up ] && [ "$(cat /sys/class/net/hb/operstate)" = up ]'
chk a_pings_b 'NS a ping -c2 -W2 10.63.0.2'
""",
    solution=r"""
sudo ip link add labbr0 type bridge
sudo ip link set ha master labbr0
sudo ip link set hb master labbr0
sudo ip link set labbr0 up; sudo ip link set ha up; sudo ip link set hb up
sleep 1
""",
    wrong="sudo ip link add labbr0 type bridge\nsudo ip link set labbr0 up\n",
)

lab(
    id="ld-093", title="Соединение зависает на больших пакетах: MTU",
    description="Малые пакеты проходят, а большие нет. Найдите звено с меньшим MTU и устраните несоответствие.",
    skills=["ip link mtu", "ping -M do", "tracepath", "PMTU"],
    objectives=["Подтвердить проблему ping с DF", "Найти узкое звено", "Выровнять MTU"],
    minutes=20,
    task=NSNOTE + """\
Узел `srv` (`10.64.0.2`) подключён к машине (`10.64.0.1`). `ping 10.64.0.2` работает, но пакеты побольше (`ping -M do -s 1400 10.64.0.2`) пропадают.

Найдите звено с меньшим MTU и выровняйте MTU по обе стороны так, чтобы `ping -M do -s 1400 10.64.0.2` проходил. MTU обоих концов кабеля должен быть **одинаковым**.
""",
    hints=["`ip -d link show hv0` и `sudo nsenter --net=/run/netns/srv ip link show sv0` — сравните mtu.", "`sudo nsenter --net=/run/netns/srv ip link set sv0 mtu 1500`."],
    checks=[
        ("big_ping", "ping -M do -s 1400 проходит", "Большие пакеты проходят", "Пакеты 1400 байт с DF не проходят"),
        ("mtu_equal", "MTU обоих концов одинаков", "MTU выровнен", "MTU на концах кабеля различается"),
    ],
    setup=r"""
ip netns add srv
ip link add hv0 type veth peer name sv0
ip link set sv0 netns srv
ip addr add 10.64.0.1/24 dev hv0; ip link set hv0 up
nsenter --net=/run/netns/srv ip addr add 10.64.0.2/24 dev sv0
nsenter --net=/run/netns/srv ip link set sv0 mtu 1300
nsenter --net=/run/netns/srv ip link set sv0 up
""",
    validate=NSX + r"""
chk big_ping 'ping -M do -s 1400 -c2 -W2 10.64.0.2'
chk mtu_equal '[ "$(cat /sys/class/net/hv0/mtu)" = "$(NS srv ip -o link show sv0 | grep -o "mtu [0-9]*" | cut -d" " -f2)" ]'
""",
    solution="sudo nsenter --net=/run/netns/srv ip link set sv0 mtu 1500\n",
    wrong="sudo ip link set hv0 mtu 1300\n",
)

lab(
    id="ld-094", title="Network namespace-ы с veth и маршрутизацией через хост",
    description="Постройте два изолированных узла и соедините их через основную систему как маршрутизатор.",
    skills=["ip netns add", "veth", "ip_forward", "default route"],
    objectives=["Создать два namespace", "Соединить через veth с хостом", "Включить forwarding и маршруты"],
    minutes=30,
    task=NSNOTE + """\
Постройте схему: узел **`app`** (`10.70.1.2/24`) — **машина** (`10.70.1.1/24` и `10.70.2.1/24`) — узел **`db`** (`10.70.2.2/24`).

- создайте network namespace `app` и `db`;
- соедините каждый veth-кабелем с машиной (концы на машине: `ha1` и `hd1`);
- включите пересылку на машине (`net.ipv4.ip_forward=1`);
- в каждом узле добавьте маршрут по умолчанию через машину;
- `app` должен пинговать `db` (`10.70.2.2`), и наоборот.
""",
    hints=["Для каждого узла: `ip netns add`, `ip link add ha1 type veth peer name a0`, `ip link set a0 netns app`, адреса и `up`.", "Маршрут в узле: `sudo nsenter --net=/run/netns/app ip route add default via 10.70.1.1`."],
    checks=[
        ("topology", "Узлы app и db с нужными адресами", "Топология собрана", "Нужны namespace app (10.70.1.2/24) и db (10.70.2.2/24), на машине 10.70.1.1/24 и 10.70.2.1/24"),
        ("forwarding", "ip_forward=1", "Forwarding включён", "На машине выключен net.ipv4.ip_forward"),
        ("app_to_db", "app ↔ db", "Узлы видят друг друга", "ping между app и db не проходит"),
    ],
    setup="true\n",
    validate=NSX + r"""
chk topology 'ip netns list | grep -qw app && ip netns list | grep -qw db && NS app ip -4 -br addr | grep -q "10.70.1.2/24" && NS db ip -4 -br addr | grep -q "10.70.2.2/24" && ip -4 -br addr | grep -q "10.70.1.1/24" && ip -4 -br addr | grep -q "10.70.2.1/24"'
chk forwarding '[ "$(sysctl -n net.ipv4.ip_forward)" = 1 ]'
chk app_to_db 'NS app ping -c1 -W2 10.70.2.2 && NS db ping -c1 -W2 10.70.1.2'
""",
    solution=r"""
for pair in "app a 1" "db d 2"; do set -- $pair
  n=$1; p=$2; k=$3
  sudo ip netns add $n
  sudo ip link add h${p}1 type veth peer name ${p}0
  sudo ip link set ${p}0 netns $n
  sudo ip addr add 10.70.$k.1/24 dev h${p}1; sudo ip link set h${p}1 up
  sudo nsenter --net=/run/netns/$n ip addr add 10.70.$k.2/24 dev ${p}0
  sudo nsenter --net=/run/netns/$n ip link set ${p}0 up
  sudo nsenter --net=/run/netns/$n ip link set lo up
  sudo nsenter --net=/run/netns/$n ip route add default via 10.70.$k.1
done
sudo sysctl -w net.ipv4.ip_forward=1
""",
    wrong="sudo ip netns add app\nsudo ip netns add db\n",
)

lab(
    id="ld-097", title="Сервис слушает не там: адрес bind и недоступность снаружи",
    description="Служба отвечает локально, но недоступна для клиента из другого узла. Найдите адрес bind и исправьте.",
    skills=["ss -ltnp", "bind address", "127.0.0.1 vs 0.0.0.0", "curl"],
    objectives=["Определить, на каком адресе и порту слушает сервис", "Понять разницу loopback и внешнего адреса", "Исправить конфигурацию"],
    minutes=20,
    task=NSNOTE + """\
Служба `labweb.service` (HTTP, порт `8081`) отвечает на `127.0.0.1`, но клиент в узле `cli` (`10.65.0.2`) не может подключиться к машине (`10.65.0.1:8081`).

1. Определите по `ss -ltnp`, на каком адресе слушает служба.
2. Исправьте конфигурацию службы (адрес — аргумент после порта в `ExecStart`), перезапустите её.

Результат: `curl http://10.65.0.1:8081/` из узла `cli` возвращает `lab-ok`. Служба не должна слушать «все интерфейсы», если можно ограничиться адресом `10.65.0.1` (допустим и `0.0.0.0`).
""",
    hints=["`ss -ltnp | grep 8081` — адрес `127.0.0.1` значит «только локально».", "В unit замените адрес в `ExecStart` на `10.65.0.1`, затем `sudo systemctl daemon-reload && sudo systemctl restart labweb`."],
    exercise_timeout=15,
    checks=[
        ("client_ok", "cli получает lab-ok", "Клиент достучался", "curl из cli на 10.65.0.1:8081 не возвращает lab-ok"),
        ("not_loopback_only", "Слушает не только loopback", "Адрес bind исправлен", "Служба по-прежнему слушает только 127.0.0.1"),
    ],
    setup=r"""
install -d /srv/labweb
echo lab-ok > /srv/labweb/index.html
ip netns add cli
ip link add hv0 type veth peer name cv0
ip link set cv0 netns cli
ip addr add 10.65.0.1/24 dev hv0; ip link set hv0 up
nsenter --net=/run/netns/cli ip addr add 10.65.0.2/24 dev cv0
nsenter --net=/run/netns/cli ip link set cv0 up
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
cat > /etc/systemd/system/labweb.service <<'EOT'
[Service]
WorkingDirectory=/srv/labweb
ExecStart=/usr/bin/python3 /opt/lab/httpd.py 8081 127.0.0.1
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labweb >/dev/null 2>&1
sleep 1
""",
    exercise="sleep 1\ntrue\n",
    validate=NSX + r"""
chk client_ok '[ "$(NS cli curl -s -m 3 http://10.65.0.1:8081/ | tr -d "\n")" = lab-ok ]'
chk not_loopback_only '! ss -ltn | grep ":8081 " | grep -q "127.0.0.1:8081"'
""",
    solution=r"""
sudo sed -i 's/8081 127.0.0.1/8081 10.65.0.1/' /etc/systemd/system/labweb.service
sudo systemctl daemon-reload
sudo systemctl restart labweb
sleep 1
""",
    wrong="sudo systemctl restart labweb\n",
)

lab(
    id="ld-098", title="Захват TCP handshake: SYN, SYN-ACK, ACK и закрытие",
    description="Снимите короткий дамп соединения и подпишите этапы установления и закрытия TCP.",
    skills=["tcpdump -w/-r", "флаги TCP", "SYN/ACK/FIN", "pcap"],
    objectives=["Захватить трафик одного соединения", "Найти этапы handshake", "Подписать закрытие"],
    minutes=20,
    task="""\
На `127.0.0.1:8099` слушает учебный сервер: он принимает соединение, отвечает строкой и закрывает его.

1. Запустите захват на интерфейсе `lo` только для порта 8099 в файл `~/hs.pcap` (`tcpdump -i lo -nn port 8099 -w ~/hs.pcap`), затем сделайте одно подключение (`nc 127.0.0.1 8099`) и остановите захват.
2. В `~/hs.txt` перечислите этапы в порядке следования, по одному слову через запятую: `SYN,SYN-ACK,ACK,FIN` (допустимы и другие слова, но эти четыре должны присутствовать).
""",
    hints=["Захват нужен с правами root: `sudo tcpdump -i lo -nn port 8099 -w ~/hs.pcap &`, потом `nc`, затем `sudo pkill tcpdump`.", "Читать дамп: `tcpdump -nn -r ~/hs.pcap` — флаги `[S]`, `[S.]`, `[.]`, `[F.]`."],
    checks=[
        ("pcap_has_handshake", "В дампе SYN, SYN-ACK и ACK", "Handshake захвачен", "В hs.pcap нет полного рукопожатия [S], [S.], [.]"),
        ("pcap_has_fin", "В дампе закрытие FIN", "Закрытие захвачено", "В hs.pcap нет FIN ([F.])"),
        ("notes_ok", "hs.txt с этапами", "Этапы подписаны", "В hs.txt должны быть SYN, SYN-ACK, ACK и FIN"),
    ],
    setup=r"""
install -d /opt/lab
cat > /opt/lab/hs.py <<'EOT'
import socket
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("127.0.0.1", 8099))
s.listen(5)
while True:
    c, _ = s.accept()
    c.sendall(b"hello\n")
    c.close()
EOT
cat > /etc/systemd/system/labhs.service <<'EOT'
[Service]
ExecStart=/usr/bin/python3 /opt/lab/hs.py
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labhs >/dev/null 2>&1
""",
    validate=r"""
P=/home/student/hs.pcap
D=$(tcpdump -nn -r $P 2>/dev/null)
chk pcap_has_handshake 'echo "$D" | grep -q "Flags \[S\]," && echo "$D" | grep -q "Flags \[S\.\]," && echo "$D" | grep -q "Flags \[\.\],"'
chk pcap_has_fin 'echo "$D" | grep -q "Flags \[F"'
chk notes_ok 'for w in SYN SYN-ACK ACK FIN; do grep -qi "$w" /home/student/hs.txt || exit 1; done'
""",
    solution=r"""
sudo timeout 5 tcpdump -i lo -nn port 8099 -w /home/student/hs.pcap -U >/dev/null 2>&1 &
sleep 1
nc -w2 127.0.0.1 8099 < /dev/null
sleep 1
sudo pkill tcpdump
sleep 1
echo "SYN,SYN-ACK,ACK,FIN" > ~/hs.txt
""",
    wrong="echo 'SYN,SYN-ACK,ACK,FIN' > ~/hs.txt\n",
)

lab(
    id="ld-101", title="Локальный DNS: A, AAAA, CNAME и отрицательный ответ",
    description="Настройте локальный DNS-сервер (dnsmasq) с записями A/AAAA/CNAME и ответом NXDOMAIN для запрещённого имени.",
    skills=["dnsmasq", "dig", "host-record", "cname", "NXDOMAIN"],
    objectives=["Описать записи в dnsmasq", "Проверить dig-ом", "Получить NXDOMAIN"],
    minutes=25,
    task="""\
Локальный `dnsmasq` слушает `127.0.0.1:5353` (общие настройки — `/etc/dnsmasq.d/00-base.conf`, не меняйте их). Добавьте файл `/etc/dnsmasq.d/10-lab.conf`, чтобы:

- `web.lab.test` → A `10.20.0.10` и AAAA `fd00::10`;
- `www.lab.test` → CNAME на `web.lab.test`;
- `blocked.lab.test` → **NXDOMAIN**.

Затем перезапустите службу: `sudo systemctl restart dnsmasq`. Проверка: `dig @127.0.0.1 -p 5353 web.lab.test`.
""",
    hints=["`host-record=web.lab.test,10.20.0.10,fd00::10`, `cname=www.lab.test,web.lab.test`.", "NXDOMAIN для имени: `address=/blocked.lab.test/` (пустой адрес); проверка конфигурации — `dnsmasq --test`."],
    exercise_timeout=15,
    checks=[
        ("a_aaaa", "web: A и AAAA", "A и AAAA возвращаются", "web.lab.test должен отдавать A 10.20.0.10 и AAAA fd00::10"),
        ("cname_ok", "www → CNAME web", "CNAME работает", "www.lab.test должен быть CNAME на web.lab.test"),
        ("nxdomain_ok", "blocked → NXDOMAIN", "Отрицательный ответ получен", "blocked.lab.test должен отвечать NXDOMAIN"),
    ],
    setup=r"""
printf 'port=5353\nlisten-address=127.0.0.1\nbind-interfaces\nno-resolv\nno-hosts\n' > /etc/dnsmasq.d/00-base.conf
systemctl enable --now dnsmasq >/dev/null 2>&1
""",
    exercise="sudo systemctl restart dnsmasq 2>/dev/null\nsleep 1\ntrue\n",
    validate=r"""
q() { dig +short +time=2 +tries=1 @127.0.0.1 -p 5353 "$@"; }
chk a_aaaa '[ "$(q web.lab.test A)" = 10.20.0.10 ] && [ "$(q web.lab.test AAAA)" = fd00::10 ]'
chk cname_ok 'q www.lab.test CNAME | grep -qx "web.lab.test."'
chk nxdomain_ok 'dig @127.0.0.1 -p 5353 +time=2 +tries=1 blocked.lab.test A | grep -q "status: NXDOMAIN"'
""",
    solution=r"""
sudo tee /etc/dnsmasq.d/10-lab.conf > /dev/null <<'EOT'
host-record=web.lab.test,10.20.0.10,fd00::10
cname=www.lab.test,web.lab.test
address=/blocked.lab.test/
EOT
sudo systemctl restart dnsmasq
sleep 1
""",
    wrong="echo 'host-record=web.lab.test,10.20.0.10' | sudo tee /etc/dnsmasq.d/10-lab.conf > /dev/null\nsudo systemctl restart dnsmasq\n",
)

lab(
    id="ld-102", title="Периодические таймауты: исчерпание эфемерных портов",
    description="Клиент не может открыть новые соединения: слишком узкий диапазон локальных портов.",
    skills=["ip_local_port_range", "ss -s", "sysctl.d", "эфемерные порты"],
    objectives=["Заподозрить нехватку портов", "Измерить диапазон", "Исправить и закрепить через sysctl.d"],
    minutes=20,
    task="""\
**Инцидент.** Клиентское приложение периодически падает с `Cannot assign requested address` при открытии соединений. Нагрузка не выросла.

Найдите причину (`sysctl net.ipv4.ip_local_port_range`, `ss -s`), верните нормальный диапазон (не уже `32768 60999`, то есть не менее 20000 портов) и **закрепите** настройку так, чтобы она переживала перезагрузку (файл в `/etc/sysctl.d/`, а плохую настройку уберите).
""",
    hints=["`sysctl net.ipv4.ip_local_port_range` — диапазон из четырёх портов.", "`grep -r port_range /etc/sysctl.d/` найдёт источник; поправьте значение и `sudo sysctl --system`."],
    checks=[
        ("range_wide", "Диапазон ≥ 20000 портов", "Диапазон восстановлен", "Диапазон эфемерных портов слишком узкий"),
        ("persisted_ok", "Конфигурация sysctl.d исправлена", "Настройка закреплена", "В /etc/sysctl.d остался узкий диапазон"),
        ("connections_ok", "100 одновременных соединений открываются", "Соединения открываются", "Открыть 100 одновременных соединений не удалось"),
    ],
    setup=r"""
echo 'net.ipv4.ip_local_port_range = 40000 40003' > /etc/sysctl.d/99-lab-ports.conf
sysctl -q -p /etc/sysctl.d/99-lab-ports.conf
""",
    validate=r"""
r=$(sysctl -n net.ipv4.ip_local_port_range)
w=$(echo "$r" | awk '{print $2-$1}')
bad=$(grep -rhE "^[[:space:]]*net.ipv4.ip_local_port_range" /etc/sysctl.d /etc/sysctl.conf 2>/dev/null | awk -F= '{split($2,a," "); if (a[2]-a[1] < 20000) n++} END{print n+0}')
chk range_wide '[ "$w" -ge 20000 ]'
chk persisted_ok '[ "$bad" = 0 ]'
chk connections_ok 'python3 - <<EOT
import socket
srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(200)
port = srv.getsockname()[1]
cs = [socket.create_connection(("127.0.0.1", port)) for _ in range(100)]
EOT'
""",
    solution=r"""
sudo rm -f /etc/sysctl.d/99-lab-ports.conf
echo 'net.ipv4.ip_local_port_range = 32768 60999' | sudo tee /etc/sysctl.d/10-ports.conf > /dev/null
sudo sysctl --system > /dev/null
""",
    wrong="sudo sysctl -w net.ipv4.ip_local_port_range='32768 60999'\n",
)

lab(
    id="ld-113", title="Вход по SSH-ключу с проверкой host key",
    description="Настройте вход по ключу для учебного пользователя и проверяйте отпечаток сервера, а не принимайте его вслепую.",
    skills=["ssh-keygen", "authorized_keys", "known_hosts", "StrictHostKeyChecking"],
    objectives=["Создать ключ", "Установить публичный ключ на сервер", "Добавить host key в known_hosts после проверки отпечатка"],
    minutes=25,
    task="""\
На этой же машине работает `sshd`. Пользователь `labuser` (пароля у него нет) должен принимать вход по ключу.

1. Создайте у себя (`student`) ключ `ed25519` (`~/.ssh/id_ed25519`, без пароля допустимо для обучения).
2. Установите публичный ключ в `~labuser/.ssh/authorized_keys` с правильными правами (каталог `0700`, файл `0600`, владелец `labuser`).
3. Добавьте host key сервера в `~/.ssh/known_hosts`, **сверив отпечаток** (`ssh-keyscan` + `ssh-keygen -lf` с отпечатком `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`).

Проверка: `ssh -o BatchMode=yes -o StrictHostKeyChecking=yes labuser@127.0.0.1 echo ok`.
""",
    hints=["`ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519`; публичный ключ — `sudo install -d -m700 -o labuser ...`, `sudo tee -a`.", "`ssh-keyscan -t ed25519 127.0.0.1 >> ~/.ssh/known_hosts` после сверки отпечатков."],
    exercise_timeout=15,
    checks=[
        ("login_ok", "Вход по ключу со строгой проверкой host key", "Вход по ключу работает", "ssh с BatchMode и StrictHostKeyChecking=yes не проходит"),
        ("perms_ok", "Права на ключ и authorized_keys", "Права корректны", "Нужны ~/.ssh/id_ed25519 0600, authorized_keys 0600, владелец labuser"),
        ("hostkey_pinned", "host key в known_hosts совпадает с сервером", "Host key закреплён", "В known_hosts нет записи с отпечатком host key сервера"),
    ],
    setup=r"""
useradd -m -s /bin/bash labuser
passwd -l labuser >/dev/null
printf 'PasswordAuthentication no\nPubkeyAuthentication yes\nListenAddress 127.0.0.1\n' > /etc/ssh/sshd_config.d/10-lab.conf
mkdir -p /run/sshd
ssh-keygen -A >/dev/null
systemctl enable --now ssh >/dev/null 2>&1
sleep 1
""",
    exercise="true\n",
    validate=r"""
S="runuser -u student --"
chk login_ok '$S ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 labuser@127.0.0.1 echo ok | grep -qx ok'
chk perms_ok '[ "$(stat -c %a /home/student/.ssh/id_ed25519)" = 600 ] && [ "$(stat -c %a /home/labuser/.ssh/authorized_keys)" = 600 ] && [ "$(stat -c %U /home/labuser/.ssh/authorized_keys)" = labuser ] && [ "$(stat -c %a /home/labuser/.ssh)" = 700 ]'
srv=$(ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub | awk '{print $2}')
chk hostkey_pinned 'ssh-keygen -lf /home/student/.ssh/known_hosts | awk "{print \$2}" | grep -qx "$srv"'
""",
    solution=r"""
ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q
sudo install -d -m 700 -o labuser -g labuser /home/labuser/.ssh
sudo install -m 600 -o labuser -g labuser ~/.ssh/id_ed25519.pub /home/labuser/.ssh/authorized_keys
ssh-keyscan -t ed25519 127.0.0.1 2>/dev/null > /tmp/hk
ssh-keygen -lf /tmp/hk
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
cat /tmp/hk >> ~/.ssh/known_hosts
""",
    wrong="ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q\n",
)

lab(
    id="ld-115", title="SSH не пускает: права на ~/.ssh и authorized_keys",
    description="Вход по ключу отклоняется из-за небезопасных прав. Исправьте именно права, не ослабляя StrictModes.",
    skills=["StrictModes", "chmod 700/600", "journalctl -u ssh", "authorized_keys"],
    objectives=["Найти причину по журналу sshd", "Исправить права", "Не отключать защитные проверки"],
    minutes=20,
    task="""\
**Инцидент.** Вход `ssh labuser@127.0.0.1` по ключу `student` отклоняется (`Permission denied (publickey)`), хотя ключ в `authorized_keys` есть.

Найдите причину (журнал `sshd`: `Authentication refused: bad ownership or modes`) и исправьте **права** на домашний каталог, `~/.ssh` и `authorized_keys` пользователя `labuser`. Опцию `StrictModes` отключать нельзя.
""",
    hints=["`sudo journalctl -u ssh -n 20` — причина указана в журнале.", "Домашний каталог не должен быть записываемым для группы и других; `.ssh` — `0700`; `authorized_keys` — `0600`."],
    exercise_timeout=15,
    checks=[
        ("login_ok", "Вход по ключу проходит", "Вход работает", "Вход по ключу всё ещё отклоняется"),
        ("strict_on", "StrictModes включён", "StrictModes включён", "Нельзя отключать StrictModes"),
        ("perms_safe", "Права безопасные", "Права корректны", "Домашний каталог, .ssh или authorized_keys имеют небезопасные права"),
    ],
    setup=r"""
useradd -m -s /bin/bash labuser
passwd -l labuser >/dev/null
printf 'PasswordAuthentication no\nPubkeyAuthentication yes\nListenAddress 127.0.0.1\n' > /etc/ssh/sshd_config.d/10-lab.conf
mkdir -p /run/sshd; ssh-keygen -A >/dev/null
su - student -c "ssh-keygen -t ed25519 -N '' -f ~/.ssh/id_ed25519 -q; ssh-keyscan -t ed25519 127.0.0.1 2>/dev/null > ~/.ssh/known_hosts" 2>/dev/null || true
mkdir -p /home/labuser/.ssh
cp /home/student/.ssh/id_ed25519.pub /home/labuser/.ssh/authorized_keys
chown -R labuser:labuser /home/labuser
chmod 777 /home/labuser; chmod 777 /home/labuser/.ssh; chmod 666 /home/labuser/.ssh/authorized_keys
systemctl enable --now ssh >/dev/null 2>&1
sleep 1
""",
    exercise="true\n",
    validate=r"""
chk login_ok 'runuser -u student -- ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=5 labuser@127.0.0.1 echo ok | grep -qx ok'
chk strict_on '[ "$(sshd -T | awk "/^strictmodes/{print \$2}")" = yes ]'
chk perms_safe '[ $(( 0$(stat -c %a /home/labuser) & 0022 )) -eq 0 ] && [ "$(stat -c %a /home/labuser/.ssh)" = 700 ] && [ $(( 0$(stat -c %a /home/labuser/.ssh/authorized_keys) & 0077 )) -eq 0 ]'
""",
    solution="sudo chmod 755 /home/labuser\nsudo chmod 700 /home/labuser/.ssh\nsudo chmod 600 /home/labuser/.ssh/authorized_keys\n",
    wrong="echo 'StrictModes no' | sudo tee /etc/ssh/sshd_config.d/99-weak.conf > /dev/null\nsudo systemctl restart ssh\n",
)

lab(
    id="ld-117", title="TLS-сертификат выдан для другого имени: SAN",
    description="Клиент отвергает сертификат из-за несовпадения имени. Выпустите правильный сертификат с SAN и подключите его.",
    skills=["openssl req/x509", "subjectAltName", "curl --cacert", "nginx ssl_certificate"],
    objectives=["Найти причину ошибки проверки имени", "Выпустить сертификат со SAN", "Заменить его в nginx и перезагрузить"],
    minutes=30,
    task="""\
Сайт `https://app.lab.test` (nginx, порт 443) отдаёт сертификат, выписанный на другое имя — клиент проверку не проходит. Учебный корневой CA лежит в `/etc/lab/ca/` (`ca.crt`, `ca.key`).

1. Убедитесь в проблеме: `curl --cacert /etc/lab/ca/ca.crt --resolve app.lab.test:443:127.0.0.1 https://app.lab.test/`.
2. Выпустите новый ключ и сертификат для `app.lab.test` **со SAN** (`DNS:app.lab.test`), подписанный этим CA.
3. Подставьте их в nginx (`/etc/lab/tls/app.crt`, `/etc/lab/tls/app.key`) и перезагрузите конфигурацию.
""",
    hints=["CSR: `openssl req -new -newkey rsa:2048 -nodes -keyout app.key -out app.csr -subj /CN=app.lab.test`.", "Подпись с SAN: `openssl x509 -req -in app.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 30 -extfile <(printf 'subjectAltName=DNS:app.lab.test') -out app.crt`."],
    exercise_timeout=15,
    checks=[
        ("verified_https", "curl с проверкой цепочки и имени успешен", "Клиент принимает сертификат", "curl --cacert ... https://app.lab.test/ не проходит проверку"),
        ("san_present", "В сертификате SAN app.lab.test", "SAN есть", "В сертификате нет subjectAltName DNS:app.lab.test"),
    ],
    setup=PKI + r"""
openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/app.key -out /tmp/w.csr -subj "/CN=wrong.example" >/dev/null 2>&1
openssl x509 -req -in /tmp/w.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 30 -extfile <(printf 'subjectAltName=DNS:wrong.example') -out /etc/lab/tls/app.crt >/dev/null 2>&1
chmod 644 /etc/lab/ca/ca.crt; chmod 600 /etc/lab/tls/app.key
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/app.conf <<'EOT'
server {
    listen 443 ssl;
    server_name app.lab.test;
    ssl_certificate /etc/lab/tls/app.crt;
    ssl_certificate_key /etc/lab/tls/app.key;
    location / { return 200 "secure-ok\n"; }
}
EOT
systemctl enable --now nginx >/dev/null 2>&1
sleep 1
""",
    exercise="sudo nginx -t >/dev/null 2>&1 && sudo systemctl reload nginx\nsleep 1\ntrue\n",
    validate=r"""
chk verified_https '[ "$(curl -s -m 5 --cacert /etc/lab/ca/ca.crt --resolve app.lab.test:443:127.0.0.1 https://app.lab.test/ | tr -d "\n")" = secure-ok ]'
chk san_present 'openssl x509 -in /etc/lab/tls/app.crt -noout -ext subjectAltName | grep -q "DNS:app.lab.test"'
""",
    solution=r"""
cd /etc/lab/tls
sudo openssl req -new -newkey rsa:2048 -nodes -keyout app.key -out /tmp/app.csr -subj /CN=app.lab.test 2>/dev/null
sudo sh -c "printf 'subjectAltName=DNS:app.lab.test' > /tmp/san.ext"
sudo openssl x509 -req -in /tmp/app.csr -CA /etc/lab/ca/ca.crt -CAkey /etc/lab/ca/ca.key -CAcreateserial -days 30 -extfile /tmp/san.ext -out app.crt 2>/dev/null
sudo chmod 600 app.key
sudo systemctl reload nginx
""",
    wrong="cd /etc/lab/tls\nsudo openssl req -x509 -newkey rsa:2048 -nodes -keyout app.key -out app.crt -days 30 -subj /CN=app.lab.test 2>/dev/null\nsudo systemctl reload nginx\n",
)

lab(
    id="ld-118", title="TLS termination и перенаправление HTTP на HTTPS",
    description="Настройте nginx как TLS-терминатор перед backend и добавьте постоянный редирект с HTTP.",
    skills=["nginx server blocks", "ssl_certificate", "return 301", "proxy_pass"],
    objectives=["Настроить HTTPS-сервер", "Проксировать на backend", "Добавить редирект с порта 80"],
    minutes=30,
    task="""\
Backend (`labback`) слушает `127.0.0.1:9000` и отвечает `backend-ok`. Готовый сертификат для `app.lab.test` лежит в `/etc/lab/tls/` (`app.crt`, `app.key`; CA — `/etc/lab/ca/ca.crt`).

Настройте nginx (`/etc/nginx/conf.d/app.conf`):

- порт 443: TLS, `proxy_pass` на `http://127.0.0.1:9000`;
- порт 80: постоянное перенаправление (`301`) на `https://$host$request_uri`.

Конфигурация должна проходить `nginx -t`; примените её (`reload`).
""",
    hints=["Два блока `server`: `listen 80; return 301 https://$host$request_uri;` и `listen 443 ssl; ssl_certificate ...; location / { proxy_pass http://127.0.0.1:9000; }`.", "Проверка: `curl -sI -H 'Host: app.lab.test' http://127.0.0.1/x` и `curl --cacert ... --resolve ... https://app.lab.test/`."],
    exercise_timeout=15,
    checks=[
        ("redirect_301", "HTTP → 301 на HTTPS с путём", "Редирект настроен", "http://…/x должен отвечать 301 на https://app.lab.test/x"),
        ("https_proxy", "HTTPS отдаёт ответ backend", "TLS-терминация работает", "https://app.lab.test/ не возвращает backend-ok с проверкой сертификата"),
        ("nginx_valid", "nginx -t проходит", "Конфигурация валидна", "nginx -t сообщает об ошибке"),
    ],
    setup=PKI + r"""
openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/app.key -out /tmp/a.csr -subj "/CN=app.lab.test" >/dev/null 2>&1
openssl x509 -req -in /tmp/a.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 30 -extfile <(printf 'subjectAltName=DNS:app.lab.test') -out /etc/lab/tls/app.crt >/dev/null 2>&1
chmod 644 /etc/lab/ca/ca.crt /etc/lab/tls/app.crt; chmod 640 /etc/lab/tls/app.key; chgrp www-data /etc/lab/tls/app.key
rm -f /etc/nginx/sites-enabled/default
install -d /srv/labback; echo backend-ok > /srv/labback/index.html
cat > /etc/systemd/system/labback.service <<'EOT'
[Service]
WorkingDirectory=/srv/labback
ExecStart=/usr/bin/python3 -m http.server 9000 --bind 127.0.0.1
[Install]
WantedBy=multi-user.target
EOT
systemctl daemon-reload
systemctl enable --now labback nginx >/dev/null 2>&1
sleep 1
""",
    exercise="sudo nginx -t >/dev/null 2>&1 && sudo systemctl reload nginx\nsleep 1\ntrue\n",
    validate=r"""
chk redirect_301 'h=$(curl -s -m 5 -I -H "Host: app.lab.test" http://127.0.0.1/x); echo "$h" | head -n 1 | grep -q " 301 " && echo "$h" | tr -d "\r" | grep -qi "^location: https://app.lab.test/x$"'
chk https_proxy '[ "$(curl -s -m 5 --cacert /etc/lab/ca/ca.crt --resolve app.lab.test:443:127.0.0.1 https://app.lab.test/ | tr -d "\n")" = backend-ok ]'
chk nginx_valid 'nginx -t'
""",
    solution=r"""
sudo tee /etc/nginx/conf.d/app.conf > /dev/null <<'EOT'
server {
    listen 80;
    server_name app.lab.test;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    server_name app.lab.test;
    ssl_certificate /etc/lab/tls/app.crt;
    ssl_certificate_key /etc/lab/tls/app.key;
    location / { proxy_pass http://127.0.0.1:9000; }
}
EOT
sudo nginx -t && sudo systemctl reload nginx
""",
    wrong="sudo tee /etc/nginx/conf.d/app.conf > /dev/null <<'EOT'\nserver {\n    listen 80;\n    location / { proxy_pass http://127.0.0.1:9000; }\n}\nEOT\nsudo systemctl reload nginx\n",
)

lab(
    id="ld-119", title="Ротация сертификата: неполная цепочка ломает часть клиентов",
    description="После ротации сервер отдаёт только листовой сертификат. Клиенты с одним корневым CA не могут построить цепочку.",
    skills=["fullchain", "openssl s_client", "intermediate CA", "ssl_certificate"],
    objectives=["Увидеть ошибку построения цепочки", "Собрать fullchain", "Подтвердить проверкой клиента"],
    minutes=30,
    task="""\
После ротации nginx отдаёт только листовой сертификат (`/etc/lab/tls/leaf.crt`). Клиент, доверяющий только корню (`/etc/lab/ca/root.crt`), получает `unable to get local issuer certificate`.

Исправьте так, чтобы сервер отдавал **полную цепочку** (лист + промежуточный `/etc/lab/ca/inter.crt`) и проверка клиента проходила:

`openssl s_client -connect 127.0.0.1:443 -servername app.lab.test -CAfile /etc/lab/ca/root.crt -verify_return_error`
""",
    hints=["`cat leaf.crt inter.crt > fullchain.crt` и укажите fullchain в `ssl_certificate`.", "Порядок важен: сначала лист, затем промежуточный."],
    exercise_timeout=15,
    checks=[
        ("chain_verifies", "Цепочка проверяется от корня", "Цепочка полная", "openssl s_client не может построить цепочку до корня"),
        ("served_chain_len", "Сервер отдаёт ≥ 2 сертификата", "Отдаётся лист и промежуточный", "Сервер отдаёт только один сертификат"),
    ],
    setup=r"""
install -d /etc/lab/ca /etc/lab/tls
cd /etc/lab/ca
openssl req -x509 -newkey rsa:2048 -nodes -keyout root.key -out root.crt -days 3650 -subj "/CN=Lab Root" >/dev/null 2>&1
openssl req -new -newkey rsa:2048 -nodes -keyout inter.key -out inter.csr -subj "/CN=Lab Intermediate" >/dev/null 2>&1
openssl x509 -req -in inter.csr -CA root.crt -CAkey root.key -CAcreateserial -days 3000 -extfile <(printf 'basicConstraints=critical,CA:TRUE\nkeyUsage=keyCertSign,cRLSign') -out inter.crt >/dev/null 2>&1
openssl req -new -newkey rsa:2048 -nodes -keyout /etc/lab/tls/leaf.key -out /tmp/leaf.csr -subj "/CN=app.lab.test" >/dev/null 2>&1
openssl x509 -req -in /tmp/leaf.csr -CA inter.crt -CAkey inter.key -CAcreateserial -days 30 -extfile <(printf 'subjectAltName=DNS:app.lab.test') -out /etc/lab/tls/leaf.crt >/dev/null 2>&1
chmod 644 /etc/lab/ca/*.crt /etc/lab/tls/leaf.crt; chmod 600 /etc/lab/tls/leaf.key
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/app.conf <<'EOT'
server {
    listen 443 ssl;
    server_name app.lab.test;
    ssl_certificate /etc/lab/tls/leaf.crt;
    ssl_certificate_key /etc/lab/tls/leaf.key;
    location / { return 200 "chain-ok\n"; }
}
EOT
systemctl enable --now nginx >/dev/null 2>&1
sleep 1
""",
    exercise="sudo nginx -t >/dev/null 2>&1 && sudo systemctl reload nginx\nsleep 1\ntrue\n",
    validate=r"""
S() { echo | timeout 8 openssl s_client -connect 127.0.0.1:443 -servername app.lab.test "$@" 2>&1; }
chk chain_verifies 'S -CAfile /etc/lab/ca/root.crt -verify_return_error | grep -q "Verify return code: 0 (ok)"'
chk served_chain_len '[ "$(S -showcerts | grep -c "BEGIN CERTIFICATE")" -ge 2 ]'
""",
    solution=r"""
sudo sh -c 'cat /etc/lab/tls/leaf.crt /etc/lab/ca/inter.crt > /etc/lab/tls/fullchain.crt'
sudo sed -i 's#ssl_certificate /etc/lab/tls/leaf.crt;#ssl_certificate /etc/lab/tls/fullchain.crt;#' /etc/nginx/conf.d/app.conf
sudo nginx -t && sudo systemctl reload nginx
""",
    wrong="sudo systemctl reload nginx\n",
)

lab(
    id="ld-100", title="HTTP 502 при живом backend: где ломается цепочка",
    description="Прокси отвечает 502, хотя backend жив. Разделите ошибки DNS, connect, timeout и ответа upstream и исправьте причину.",
    skills=["nginx error.log", "502 vs 504", "proxy_pass", "ss -ltnp"],
    objectives=["Прочитать причину в error.log", "Отличить connect refused от timeout", "Исправить адрес upstream"],
    minutes=25,
    task="""\
**Инцидент.** `curl http://127.0.0.1:8088/` отвечает `502 Bad Gateway`, хотя backend (`labapi`) жив и отвечает на `127.0.0.1:9000`.

1. По `/var/log/nginx/error.log` определите категорию ошибки и запишите в `~/cause.txt` одно слово: `dns`, `refused`, `timeout` или `upstream-response`.
2. Исправьте конфигурацию прокси, чтобы `curl http://127.0.0.1:8088/` возвращал `api-ok`.
""",
    hints=["`sudo tail /var/log/nginx/error.log`: `connect() failed (111: Connection refused)` означает, что по адресу upstream никто не слушает.", "`ss -ltnp` покажет реальный порт backend; поправьте `proxy_pass` и `sudo systemctl reload nginx`."],
    exercise_timeout=15,
    checks=[
        ("cause_ok", "cause.txt: refused", "Категория определена", "В cause.txt должно быть слово refused"),
        ("proxy_ok", "Прокси возвращает api-ok", "Прокси работает", "curl http://127.0.0.1:8088/ не возвращает api-ok"),
    ],
    setup=r"""
install -d /srv/labapi; echo api-ok > /srv/labapi/index.html
cat > /etc/systemd/system/labapi.service <<'EOT'
[Service]
WorkingDirectory=/srv/labapi
ExecStart=/usr/bin/python3 -m http.server 9000 --bind 127.0.0.1
[Install]
WantedBy=multi-user.target
EOT
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/api.conf <<'EOT'
server {
    listen 127.0.0.1:8088;
    location / { proxy_pass http://127.0.0.1:9001; }
}
EOT
systemctl daemon-reload
systemctl enable --now labapi nginx >/dev/null 2>&1
curl -s -m 3 http://127.0.0.1:8088/ >/dev/null
""",
    exercise="sudo nginx -t >/dev/null 2>&1 && sudo systemctl reload nginx\nsleep 1\ntrue\n",
    validate=r"""
chk cause_ok '[ "$(tr -d " \r\n" < /home/student/cause.txt | tr A-Z a-z)" = refused ]'
chk proxy_ok '[ "$(curl -s -m 5 http://127.0.0.1:8088/ | tr -d "\n")" = api-ok ]'
""",
    solution=r"""
sudo tail -n 3 /var/log/nginx/error.log
echo refused > ~/cause.txt
sudo sed -i 's#127.0.0.1:9001#127.0.0.1:9000#' /etc/nginx/conf.d/api.conf
sudo systemctl reload nginx
""",
    wrong="echo timeout > ~/cause.txt\n",
)
