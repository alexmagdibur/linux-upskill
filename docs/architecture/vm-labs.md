# Учебные машины (runtime `lxd`)

Задания, которым нужен настоящий systemd, root, журналы, сеть и перезагрузка, выполняются не в Docker-песочнице, а в **учебной
машине** — системном контейнере LXD с полноценным init, который создаётся на отдельной VM-хосте.

```text
 worker (Windows/Linux)  ──SSH (ключ, host key по known_hosts)──►  VM-хост (Ubuntu + LXD + btrfs)
   RuntimeRouter                                                     ├─ профиль upskill-lab (лимиты, непривилегированная)
   ├─ DockerAdapter  → контейнеры-песочницы (runtime.type: container)├─ сеть lab<8hex> на каждую сессию (без NAT/DNS/маршрута)
   └─ LXDAdapter     → учебные машины       (runtime.type: lxd)     ├─ nft-таблица inet upskill_lab (изоляция)
                                                                     └─ машины upskill-<session_uuid> из образа по fingerprint
```

## Свойства

| Что | Как |
|---|---|
| Настоящий systemd, `journald`, `cron`, `nft`, пакеты | образ `upskill-ubuntu-systemd` (Ubuntu 24.04), собирается `infra/lxd/build-base.sh` |
| Root для задач администрирования | пользователь `student` с `sudo` **внутри** машины; машина непривилегированная (user namespace), без `security.nesting` и без raw.lxc |
| Изоляция сети | отдельный мост на сессию (`ipv4.nat=false`, `ipv4.routing=false`, `dns.mode=none`) + правила хоста: из `lab*` нельзя ни на хост, ни в LAN, ни в интернет, ни в чужие сессии; внутри одной сессии машины видят друг друга (для многоузловых заданий) |
| Лимиты | 1 vCPU, 512 МиБ без swap, 512 процессов, диск 3 ГиБ (профиль `upskill-lab`), TTL и сборка мусора (reconciler + gc сетей) |
| Быстрый старт | btrfs-пул: клон + загрузка systemd ≈ 6–7 с (на `dir`-пуле было ~28 с) |
| Проверка | `setup` (root), затем `exercise` (student) → **перезагрузка** (если `reboot_before_validate`) → `validate` (root); скрипты идут через stdin отдельного SSH-канала |
| Терминал | SSH-канал с PTY → `lxc exec ... bash -l` от student; resize доходит до PTY |

## Ограничения

- **Network namespace вместо нескольких машин.** Многоузловые сценарии (маршрутизация, firewall, bastion, DNS, rolling update) строятся из network namespace и локальных служб одной машины; `ip netns exec` и `ip -n` в контейнере недоступны (нельзя смонтировать `/sys`), поэтому команды в namespace выполняются через `nsenter --net=/run/netns/<имя>`.
- **Нет вложенного KVM** на текущей VMware-VM (AMD-V недоступен при включённом Hyper-V/WSL2 на Windows). Поэтому *не* реализуются
  задания про загрузчик, ядро/модули и настоящие блочные устройства (LVM, разметка дисков) — они остаются описанными.
- Ядро общее с VM-хостом: уязвимость ядра — общий риск (см. `docs/security/README.md`); для публичного доступа нужны VM/microVM.
- Ученик с `sudo` внутри машины может читать память процессов root на время проверки (скрипт проверки идёт через stdin, а не файл).
  Это допустимо для учебной среды: подделать результат можно, но тем самым ученик обманывает только себя.
- Проверка с перезагрузкой завершает shell ученика: после «Проверить» терминал нужно переподключить.

## Добавить задание на машине

В `infra/scripts/labgen/specs_vm_*.py` спецификация (`lab(...)` ставит `runtime_type="lxd"`) с полями `setup` (от root),
`exercise` (от student, с `sudo`), `validate` (от root), `reboot` и `exercise_timeout`; обязательно `solution` и `wrong` (и `alt`).
Затем `python infra/scripts/labgen/generate.py` и `pytest tests/test_lxd_labs.py`.

## Подготовка VM-хоста

```bash
python infra/scripts/build_lxd_image.py ПОЛЬЗОВАТЕЛЬ@IP     # host-setup.sh (firewall, профиль) + build-base.sh (образ) + lock
# .env: LXD_SSH_HOST=IP, LXD_SSH_USER=ПОЛЬЗОВАТЕЛЬ  (вход по ключу; host key должен быть в known_hosts)
```
