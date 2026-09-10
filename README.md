<div align="center">

<img src="assets/cheburnet-scripts-banner.jpg" alt="ЧебурNET" width="100%">

# ЧебурNET Vision Installer

### VLESS TLS Vision + Unix-Socket Decoy для Remnawave

![Version](https://img.shields.io/badge/version-1.1.5-8b5cf6?style=for-the-badge)
[![Validation](https://img.shields.io/github/actions/workflow/status/leonidkopysov/CheburNET-Vision-Installer/validate.yml?branch=main&style=for-the-badge&label=проверка)](https://github.com/leonidkopysov/CheburNET-Vision-Installer/actions/workflows/validate.yml)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
![TLS](https://img.shields.io/badge/TLS-1.3-06b6d4?style=for-the-badge)

**Remnawave Node · Xray · TLS 1.3 · XTLS Vision · nginx · Unix sockets · Auto Tuning · Traffic Control**

</div>

## Назначение

ЧебурNET Vision Installer разворачивает отдельную Remnawave-ноду с VLESS TCP/RAW, TLS 1.3 и XTLS Vision. Валидные VPN-подключения обслуживаются Xray, а обычные HTTPS-запросы направляются в локальный decoy-сайт через изолированный nginx и два Unix-сокета для HTTP/1.1 и HTTP/2. Nginx не имеет собственных TCP-listener’ов, поэтому внешне сервис ведёт себя как обычный HTTPS-сайт на единственном TCP/443.

Установщик дополнительно предлагает обновления текущего выпуска ОС, выполняет расширенную настройку сервера, защищает API ноды и по выбору устанавливает ЧебурNET Traffic Control. Удаление системных пакетов автоматически не выполняется.

## Что устанавливается

- актуальная проверенная Remnawave Node в Docker (для выпуска 1.1.5 — `3.4.1`), заранее закреплённая по multi-arch дайджесту SHA-256;
- Xray с VLESS, TLS 1.3 и режимом Vision;
- сертификат Let’s Encrypt, автоматическое продление и проверка `certbot renew --dry-run`;
- нейтральный локальный сайт-журнал «Тихая Среда»: шесть статей, фильтры по темам, окна чтения и плавные анимации;
- nginx с HTTP/1.1 и HTTP/2 только через `h1.sock` и `h2.sock`;
- ЧебурNET Auto Tuning `1.0.0`;
- ЧебурNET Traffic Control `1.0.0` — по отдельному согласию;
- UFW, Fail2ban, ZRAM, BBR/fq и системные защитные настройки;
- защита от входящих IPv4/IPv6 echo-запросов и IPv4 timestamp-проб с автозапуском до сети;
- готовый профиль ноды и параметры Host для Remnawave.

<h3>Схема работы</h3>

![Схема VLESS TLS Vision и Unix-Socket Decoy](assets/vless-tls-vision-unix-socket-decoy.jpeg)

Внешний TCP/443 принадлежит Xray. nginx обслуживает только Unix-сокеты. API Remnawave Node слушает заданный порт, но UFW разрешает доступ только исходящим IP панели. Traffic Control применяется последним отдельным слоем nftables.

## Алгоритм установки

| Этап | Действие |
|---:|---|
| До APT | Проверка `root`, systemd, ОС, архитектуры, доступных ранних условий и контрольной суммы встроенного архива |
| 00 | Одно согласие на все действия APT текущего запуска; показ и повторная проверка каждого плана; остановка при удалениях |
| 01 | Запрос домена, API-порта, IP панели, версии панели, email и секретного ключа |
| 02 | Проверка DNS, свободного места, портов, SSH и отсутствия конфликтующей установки |
| 03 | План и установка Docker; атомарное сохранение проекта; подготовка пакетов тюнинга; маскировка штатного nginx до установки пакета; установка служб |
| 04 | Загрузка заранее закреплённого образа Remnawave Node и запуск nginx через два Unix-сокета |
| 05 | Расширенная настройка без отдельных установок пакетов; разрешение TCP/443 даже при ранее активном UFW; вывод правил и проверка ограничений API |
| 06 | Усиление SSH с сохранением действующего способа входа и `AllowTcpForwarding`; включение защиты от входящих ping- и timestamp-проб |
| 07 | Повторная строгая проверка UFW для обеих адресных семейств, запуск Remnawave Node и ожидание TCP-listener API (mTLS проверяется при связи с панелью) |
| 08 | Выпуск сертификата, проверка имени, dry-run продления и удаление временного правила TCP/80; включение контроля срока ACME |
| 09 | Предложение установить Traffic Control, подтверждение исключений, необязательный ввод IP входных/relay-нод, применение списков и самодиагностика |
| Ожидание | Вывод профиля и настроек хоста; выделенный жёлтый блок «Нода установлена и стала зелёной в панели?» |
| Итог | После ответа «Да» — диагностика Xray, TLS, Unix-сокетов, контейнера, межсетевого экрана и служб; «Нет» — состояние ожидания, код 2 |

Traffic Control устанавливается последним — после загрузок и первичного ACME-цикла. Перед итоговой диагностикой установщик ждёт подтверждения зелёного статуса ноды в панели. Ответ «Да» не подменяет технические проверки, а запускает их. При «Нет» повторная установка не нужна: подключите ноду и выполните `bash /opt/remnanode/installer.sh --check`. Все вопросы и приглашения ввода выделены жирным жёлтым в терминале; `NO_COLOR` отключает оформление

## Требования

- чистый сервер Ubuntu 22.04/24.04 или Debian 12/13;
- архитектура `x86_64` или `arm64`, права `root` и systemd;
- прямой публичный адрес и свободные TCP-порты `80`, `443` и порт API;
- домен с A/AAAA-записями только на адреса этого сервера, без CDN-проксирования;
- Remnawave Panel 3.3.0+;
- созданная нода с API-портом `2222` и полным `SECRET_KEY`;
- исходящий IP панели и email для Let’s Encrypt;
- аварийная консоль хостера на время первой установки.

## Быстрая установка

Запустите от `root`:

```bash
curl -fsSLo cheburnet-vision-install.sh https://raw.githubusercontent.com/leonidkopysov/CheburNET-Vision-Installer/main/cheburnet-vision-install.sh && bash ./cheburnet-vision-install.sh
```

## Установка с проверкой SHA-256

```bash
curl -fsSLO https://raw.githubusercontent.com/leonidkopysov/CheburNET-Vision-Installer/main/cheburnet-vision-install.sh &&
curl -fsSLO https://raw.githubusercontent.com/leonidkopysov/CheburNET-Vision-Installer/main/SHA256SUMS &&
sha256sum -c SHA256SUMS && bash ./cheburnet-vision-install.sh
```

Одно разрешение в начале действует на все действия APT текущего запуска, включая Docker, nginx, Fail2ban, unattended-upgrades и необходимые компоненты ZRAM. Каждый план показывается и повторно проверяется; удаление пакетов запрещено через `--no-remove`. При продолжении установки разрешение запрашивается заново только при необходимости пакетных изменений. Вызовы APT используют ожидание блокировки dpkg до 600 секунд, неинтерактивное окружение и `umask 022`; файлы проекта сохраняют строгие права. Phased updates не форсируются. Внутренняя установка пакетов Auto Tuning отключена: необходимые компоненты готовит основной установщик

Версия следующего изменения — `1.1.5`. История, прежние теги и релизы сохраняются. До слияния изменения нужны успешный CI и прогоны на тестовой VPS по [чек-листу](docs/TEST-REPORT.md). Слияние в `main` запускает публикацию версии через GitHub Actions. [Описание изменений](docs/RELEASE-NOTES-1.1.5.md)

Пока изменение не слито, команды с `main` устанавливают предыдущий выпуск. Для теста 1.1.5 скачайте установщик и SHA256SUMS из ветки `fix/vision-1.1.5` либо из одного полного SHA её коммита, проверьте сумму и `--version`. Не запускайте тестовую сборку поверх рабочей ноды

`main` изменяется со временем. Для воспроизводимой установки используйте файлы [конкретного выпуска](https://github.com/leonidkopysov/CheburNET-Vision-Installer/releases) или URL с полным SHA коммита. Сумма, скачанная рядом со скриптом, обнаруживает повреждение/рассинхронизацию, но не является независимой подписью. Быстрый вариант не проверяет SHA-256 самого установщика

## Версия, коды завершения и продолжение

```bash
bash ./cheburnet-vision-install.sh --version
bash /opt/remnanode/installer.sh --resume
bash /opt/remnanode/installer.sh --check
```

Коды `--install`, `--resume`, `--check`: `0` — локальные проверки пройдены; `1` — ошибка; `2` — компоненты установлены, но ещё ожидается профиль TLS/443 из панели. `130` — прерывание, `143` — сигнал TERM. Код `2` не означает необходимость переустановки. Лишние аргументы отклоняются. Приглашения подтверждения видны в SSH-терминале даже при перенаправлении stdout в файл.

Сначала проект целиком записывается во временный каталог рядом с `/opt/remnanode`, синхронизируется с диском и атомарно переименовывается. Вместе с настройками сохраняются менеджер, исходные файлы bootstrap и отметка `.bootstrap-pending`. Установка nginx и служб выполняется после этого. При обычном сбое временный каталог удаляется. После SIGKILL или отключения питания новый запуск удаляет только проверенный `/opt/remnanode.staging.*` с владельцем `root:root` и правами `0700`; подозрительный путь требует ручной проверки.

Если `/opt/remnanode` уже создан этой версией, `--resume` повторяет подготовительные этапы с сохранёнными настройками. Чисто отменённая установка Traffic Control может быть предложена повторно; остатки файлов, служб или таблицы требуют проверки, а не автоматического удаления. `--resume` не обновляет предыдущие версии до 1.1.5 и не мигрирует между версиями. Публикация на GitHub сама по себе не меняет уже работающие серверы

### Обновление списков и продление сертификатов

ACME и Traffic Control используют общую блокировку. Временное разрешение TCP/80 сохраняется при пересоздании таблицы TC до завершения проверки сертификата. В nftables используется набор с таймаутом не более часа; post-hook удаляет исключение сразу. Дополнительный `cheburnet-acme-expiry.timer` проверяет просроченную отметку каждую минуту и удаляет также временное правило UFW, а загрузочный cleanup убирает остатки после перезагрузки. Ошибка удаления сохраняет отметку для повторной попытки

Внешние списки ограничены минимальным префиксом `/16` для IPv4 и `/24` для IPv6. Суммарное объединение трёх источников не должно превышать 4 000 000 IPv4-адресов и `2^104` IPv6-адресов (охват одного `/24`). Это консервативные ограничения продукта, не гарантия доверенности источников. Некорректное или слишком широкое обновление отклоняется целиком без замены последней корректной конфигурации. Ручные блокировки имеют отдельную проверку и не подчиняются этим лимитам внешних источников

Traffic Control внутри этой сборки имеет базовую версию `1.0.0` и отдельную редакцию интеграции `Vision 1.1.5`. Она отличается от самостоятельного релиза TC исправлениями диагностики, списков, ACME и интерфейса. Самостоятельные репозитории компонентов этим изменением не обновляются

## Изменения вне каталога ноды и ограничения отката

Помимо `/opt/remnanode`, установка затрагивает:

- пакеты APT, Docker и nginx; `/etc/apt/keyrings/cheburnet-docker.asc`, `/etc/apt/sources.list.d/cheburnet-docker.sources`;
- `/var/www/decoy`, собственные `cheburnet-decoy.service` и `cheburnet-acme-cleanup.service`; штатная `nginx.service` останавливается и маскируется;
- `/etc/letsencrypt` и собственные хуки `90-cheburnet-vision` в каталогах pre/post/deploy; `certbot.timer`;
- `cheburnet-acme-expiry.service`, `cheburnet-acme-expiry.timer` и временную отметку `/run/cheburnet-vision-acme.active`;
- drop-in SSH `/etc/ssh/sshd_config.d/00-cheburnet-vision.conf`, собственные sysctl-файлы и резервные копии;
- настройки и службы Auto Tuning, UFW, Fail2ban, `/usr/local/sbin/cheburnet-two-way-ping.sh`, `cheburnet-two-way-ping.service`, таблицу `inet cheburnet_privacy`, а при согласии — файлы и таблицу nftables Traffic Control;
- блокировку `/run/cheburnet-vision.lock`, временные каталоги подготовки и журналы.

Полного автоматического отката APT, Docker, тюнинга и firewall нет. Обработчик завершения удаляет свои временные файлы и пытается закрыть собственный временный доступ ACME; состояние сервера после ошибки нужно проверить. Для удаления нужен отдельный план с учётом реально установленных компонентов — не используйте `rm -rf /opt/remnanode` как деинсталляцию.

Pre/post-хуки Certbot глобальны для хоста. После удаления компонента они не вызывают отсутствующий helper. При частично повреждённой установленной ноде выводится ошибка; если helper сохранился, post-hook закрывает только собственные временные правила даже без маркера. Ошибка хука сама по себе не доказывает, что Certbot отменил продление: проверяйте результат и TCP/80 отдельно.

Docker-ключ загружается с официального HTTPS-адреса, ограничен `Signed-By` и сверяется с отпечатком Docker `9DC8 5822 9FC7 DD38 854A E2D8 8D81 803C 0EBC FD88`. Образ Node `3.4.1` указан с заранее проверенным multi-arch дайджестом. Встроенные Auto Tuning и Traffic Control закреплены SHA-256 на этапе сборки.

> [!CAUTION]
> Установка рассчитана на отдельный чистый сервер. Не закрывайте текущую SSH-сессию до проверки повторного входа. Секретный ключ ноды никогда не публикуйте в Issues или диагностических отчётах.

## Расширенная настройка — Auto Tuning

Встроенный ЧебурNET Auto Tuning рассчитывает настройки по CPU и RAM и применяет их до первого запуска API:

<h3>Схема работы</h3>

<p align="center">
  <a href="assets/auto-tuning-scheme.jpeg">
    <img src="assets/auto-tuning-scheme.jpeg" alt="Схема работы ЧебурNET Auto Tuning" width="100%">
  </a>
</p>

- включает BBR и целевой `fq`, настраивает TCP/UDP-буферы, backlog и SYN backlog;
- рассчитывает `conntrack`, диапазон временных портов и безопасные сетевые параметры;
- создаёт и дважды проверяет ZRAM, добавляет безопасные VM-настройки;
- включает RPS для распределения обработки пакетов по доступным ядрам;
- подготавливает лимиты нагрузки и `NOFILE` для Remnawave Node;
- устанавливает и проверяет Fail2ban;
- включает UFW с запретом входящих соединений по умолчанию;
- оставляет TCP/443 публичным, а API разрешает только IP панели;
- проверяет NTP, TRIM, место, inode, Docker socket и чувствительные порты;
- сохраняет снимок состояния и планирует самопроверку после перезагрузки.

Настройка не отключает и не выбирает семейство IP. Сертификатом управляет сам Vision Installer на этапе 08, после чего итоговая проверка подтверждает его состояние.

Отчёты:

```text
/opt/remnanode/tuning-report.log
/var/lib/cheburnet-tuning/post-reboot-last.txt
```

## Защита от Two-Way Ping

На этапе усиления сервера устанавливается отдельный ранний nftables-слой `inet cheburnet_privacy`. Он блокирует только входящие IPv4/IPv6 echo-request и IPv4 timestamp-request. Исходящий ping, ответы на исходящие запросы, ICMP-ошибки, Path MTU Discovery и служебные ICMPv6-сообщения не блокируются.

```bash
systemctl status cheburnet-two-way-ping.service
/usr/local/sbin/cheburnet-two-way-ping.sh status
```

Служба восстанавливает правила при загрузке до `network-pre.target`. Остановить защиту до следующего запуска службы можно командой `systemctl stop cheburnet-two-way-ping.service`, вернуть — `systemctl start cheburnet-two-way-ping.service`.

## Traffic Control

ЧебурNET Traffic Control — утилита сетевой защиты Linux-сервера от автоматического сканирования портов и нежелательных подключений. Блокирует известные IP-адреса и подсети сканеров на уровне `nftables`, включая сети российских государственных структур, Роскомнадзора и связанных с ними организаций при использовании соответствующих списков блокировки. Поддерживает IPv4/IPv6, три внешних списка, логирование и статистику срабатываний. Устанавливается только после согласия пользователя.

<h3>Схема работы</h3>

<p align="center">
  <a href="assets/traffic-control-scheme.jpeg">
    <img src="assets/traffic-control-scheme.jpeg" alt="Схема работы ЧебурNET Traffic Control" width="100%">
  </a>
</p>

Компонент:

- загружает три внешних списка: `antiscanner`, `government_networks`, `skipa`;
- проверяет размер, формат и синтаксис полученных IP/CIDR;
- объединяет записи в интервальные наборы nftables;
- автоматически определяет IP текущего администратора и SSH-порт;
- предлагает подтвердить исходящие IP панели;
- добавляет администратора и панель в исключения;
- не применяет списки к SSH-порту, чтобы снизить риск потери доступа;
- ведёт ограниченный журнал блокировок и показывает топ-10 IP;
- восстанавливает правила после загрузки;
- ежедневно обновляет списки и сразу применяет проверенную версию;
- имеет самодиагностику и автоматическое восстановление компонентов;
- не изменяет посторонние таблицы nftables и правила UFW.

### Короткие команды

| Команда | Назначение |
|---|---|
| `ctc` | открыть главное меню |
| `ctc s` | показать состояние и размеры списков |
| `ctc t` | показать топ-10 заблокированных IP |
| `ctc c` | выполнить самодиагностику |
| `ctc u` | обновить три внешних списка |
| `ctc l` | показать последние журналы |
| `ctc r` | показать правила nftables |
| `ctc fix` | исправить обнаруженные проблемы |
| `ctc on` | включить фильтрацию и автозапуск |
| `ctc off` | выключить фильтрацию без удаления программы |

Полная справка: `cheburnet-traffic-control --help`.

## Профиль ноды

После установки профиль сохраняется в `/opt/remnanode/vision-config-profile.json`. Создайте в Remnawave новый профиль конфигурации, вставьте JSON целиком и назначьте профиль нужной ноде. Пользователей в `clients` вручную добавлять не нужно.

### Ключевые параметры профиля

| Параметр | Значение | Назначение |
|---|---|---|
| Inbound tag | `Vision-TLS` | имя inbound для Host |
| Protocol | `vless` | протокол подключения пользователей |
| Port | `443` | внешний TLS endpoint |
| Network | `tcp` | транспорт TCP/RAW |
| Security | `tls` | TLS завершает Xray |
| TLS minVersion | `1.3` | TLS 1.2 отклоняется |
| Flow | `xtls-rprx-vision` | режим Vision |
| `tcpFastOpen` | `true` | включает TCP Fast Open на входящем сокете Xray |
| `tcpcongestion` | `bbr` | закрепляет BBR для TCP-соединений inbound |
| TCP keepalive | idle `60`, interval `30` | обнаруживает потерянные долгоживущие соединения |
| ALPN | `h2`, `http/1.1` | выбор соответствующего Unix fallback |
| h2 fallback | `/run/xray-fallback/h2.sock` | HTTP/2-заглушка |
| h1 fallback | `/run/xray-fallback/h1.sock` | HTTP/1.1-заглушка |
| `rejectUnknownSni` | `true` | отклонение неизвестного SNI |
| DNS | AdGuard DoH, Comss DoH | шифрованное разрешение имён |
| `clients` | `[]` | клиентов динамически добавляет Remnawave |

### Шаблон профиля для копирования

Замените два вхождения `<ДОМЕН_НОДЫ>` своим доменом, а `<ПУБЛИЧНЫЙ_IP_НОДЫ>` — адресом A-записи. Если у домена есть AAAA-запись, добавьте её в тот же массив. Установщик делает это автоматически.

```json
{
  "log": {"access": "none", "dnsLog": false, "loglevel": "warning"},
  "dns": {
    "servers": [
      {"address": "https+local://dns.adguard-dns.com/dns-query", "timeoutMs": 3000},
      {"address": "https+local://dns.comss.one/dns-query", "timeoutMs": 3000}
    ],
    "disableCache": false,
    "disableFallback": false,
    "enableParallelQuery": false
  },
  "inbounds": [
    {
      "tag": "Vision-TLS",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "flow": "xtls-rprx-vision",
        "clients": [],
        "fallbacks": [
          {"alpn": "h2", "dest": "/run/xray-fallback/h2.sock", "xver": 0},
          {"dest": "/run/xray-fallback/h1.sock", "xver": 0}
        ],
        "decryption": "none"
      },
      "sniffing": {
        "enabled": true,
        "routeOnly": true,
        "destOverride": ["http", "tls", "quic"]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "tls",
        "sockopt": {
          "tcpFastOpen": true,
          "tcpcongestion": "bbr",
          "tcpKeepAliveIdle": 60,
          "tcpKeepAliveInterval": 30
        },
        "tlsSettings": {
          "alpn": ["h2", "http/1.1"],
          "minVersion": "1.3",
          "certificates": [
            {
              "keyFile": "/etc/letsencrypt/live/<ДОМЕН_НОДЫ>/privkey.pem",
              "certificateFile": "/etc/letsencrypt/live/<ДОМЕН_НОДЫ>/fullchain.pem"
            }
          ],
          "rejectUnknownSni": true
        }
      }
    }
  ],
  "outbounds": [
    {"tag": "DIRECT", "protocol": "freedom"},
    {"tag": "BLOCK", "protocol": "blackhole"}
  ],
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      {"type": "field", "port": "443", "network": "udp", "inboundTag": ["Vision-TLS"], "outboundTag": "BLOCK"},
      {"type": "field", "port": "25", "network": "tcp", "outboundTag": "BLOCK"},
      {"type": "field", "protocol": ["bittorrent"], "outboundTag": "BLOCK"},
      {"type": "field", "ip": ["geoip:private", "<ПУБЛИЧНЫЙ_IP_НОДЫ>"], "outboundTag": "BLOCK"},
      {"type": "field", "domain": ["geosite:private"], "outboundTag": "BLOCK"},
      {
        "type": "field",
        "domain": [
          "geosite:category-ads-all",
          "domain:google-analytics.com",
          "domain:adjust.net.in",
          "domain:amplitude.com",
          "domain:mc.yandex.ru",
          "domain:mytracker.ru"
        ],
        "outboundTag": "BLOCK"
      }
    ]
  }
}
```

## Настройки Host в Remnawave

```text
Адрес:          ваш-домен.example
Порт:           443
SNI:            ваш-домен.example
Security Layer: TLS (Transport Layer Security)
Отпечаток:      firefox
ALPN:           h2,http/1.1
Inbound:        Vision-TLS
```

Адрес и SNI должны совпадать с доменом сертификата. Готовая памятка сохраняется в `/opt/remnanode/host-settings.txt`.

## Проверка и обслуживание

```bash
bash /opt/remnanode/installer.sh --check
```

Проверяются API, Xray, TLS 1.3, отклонение TLS 1.2, сертификат, HTTP/1.1 и HTTP/2, Unix-сокеты, UFW, Traffic Control, AppArmor, seccomp, `no-new-privileges`, BBR/fq/TFO, Fail2ban и автозапуск служб.

| Путь | Назначение |
|---|---|
| `/opt/remnanode/installer.sh` | обслуживание и повторная проверка |
| `/opt/remnanode/vision-config-profile.json` | профиль ноды |
| `/opt/remnanode/host-settings.txt` | настройки Host |
| `/opt/remnanode/fallback-sockets/` | Unix-сокеты h1/h2 |
| `/opt/remnanode/tuning-report.log` | отчёт расширенной настройки |
| `/var/www/decoy/index.html` | нейтральная заглушка |

## Сетевые порты

| Порт | Доступ |
|---|---|
| SSH-порт | административный доступ; сохраняется установщиком |
| `443/tcp` | публичный VLESS TLS Vision и HTTPS-заглушка |
| `2222/tcp` | только исходящие IP панели Remnawave |
| `80/tcp` | временно во время Certbot HTTP-01 |
| `8080/8081/18080/18081` | закрыты и не используются |

## Автор и лицензия

**Леонид Копысов**  
GitHub: **[leonidkopysov](https://github.com/leonidkopysov)**  
Telegram: **[@kopysovleonid](https://t.me/kopysovleonid)**

Оригинальный код ЧебурNET распространяется по лицензии [MIT](LICENSE). Источники внешних списков и общие пакеты перечислены в [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
