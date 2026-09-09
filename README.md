<div align="center">

<img src="assets/cheburnet-scripts-banner.jpg" alt="ЧебурNET" width="100%">

# ЧебурNET Vision Installer

### VLESS TLS Vision + Unix-Socket Decoy для Remnawave

![Version](https://img.shields.io/badge/version-1.1.0-8b5cf6?style=for-the-badge)
[![Validation](https://img.shields.io/github/actions/workflow/status/leonidkopysov/CheburNET-Vision-Installer/validate.yml?branch=main&style=for-the-badge&label=проверка)](https://github.com/leonidkopysov/CheburNET-Vision-Installer/actions/workflows/validate.yml)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)
![TLS](https://img.shields.io/badge/TLS-1.3-06b6d4?style=for-the-badge)

**RemnaNode · Xray · TLS 1.3 · XTLS Vision · nginx · Unix sockets · Auto Tuning · Traffic Control**

</div>

## Назначение

ЧебурNET Vision Installer разворачивает отдельную Remnawave-ноду с VLESS TCP/RAW, TLS 1.3 и XTLS Vision. Валидные VPN-подключения обслуживаются Xray, а обычные HTTPS-запросы направляются в локальный decoy-сайт через изолированный nginx и два Unix-сокета для HTTP/1.1 и HTTP/2. Nginx не имеет собственных TCP-listener’ов, поэтому внешне сервис ведёт себя как обычный HTTPS-сайт на единственном TCP/443.

Установщик дополнительно выполняет полное обновление текущего выпуска ОС, продвинутую настройку сервера, защищает API ноды и по выбору устанавливает ЧебурNET Traffic Control.

## Что устанавливается

- Remnawave Node последней стабильной версии на момент выпуска (`3.4.1`) в Docker с образом, закреплённым по digest;
- Xray с VLESS, TLS 1.3 и режимом Vision;
- сертификат Let's Encrypt, автоматическое продление и проверка `certbot renew --dry-run`;
- нейтральный локальный сайт-заглушка;
- nginx с HTTP/1.1 и HTTP/2 только через `h1.sock` и `h2.sock`;
- ЧебурNET Auto Tuning `1.0.0`;
- ЧебурNET Traffic Control `1.0.0` — по отдельному согласию;
- UFW, Fail2ban, ZRAM, BBR/fq и системные защитные настройки;
- готовый профиль ноды и параметры Host для Remnawave.

## Схема работы

<p align="center">
  <a href="assets/vless-tls-vision-unix-socket-decoy.jpeg">
    <img src="assets/vless-tls-vision-unix-socket-decoy.jpeg" alt="Схема VLESS TLS Vision и Unix-Socket Decoy" width="100%">
  </a>
</p>

Внешний TCP/443 принадлежит Xray. nginx обслуживает только Unix-сокеты. API RemnaNode слушает заданный порт, но UFW разрешает доступ только исходящим IP панели. Traffic Control применяется последним отдельным слоем nftables.

## Алгоритм установки

| Этап | Действие |
|---:|---|
| 00 | Проверка `root`, systemd, ОС, архитектуры, APT и обязательных компонентов |
| 00 | Обновление индекса APT, показ плана и отдельное согласие на `full-upgrade` |
| 01 | Запрос домена, API-порта, IP панели, версии панели, email и секретного ключа |
| 02 | Проверка DNS, свободного места, портов, SSH и отсутствия конфликтующей установки |
| 03 | Установка Docker из официального репозитория и подготовка проекта |
| 04 | Загрузка закреплённого образа RemnaNode и запуск nginx через два Unix-сокета |
| 05 | Продвинутая настройка сервера и включение UFW до запуска API |
| 06 | Усиление SSH с сохранением действующего способа входа и `AllowTcpForwarding` |
| 07 | Запуск RemnaNode и проверка API по mTLS |
| 08 | Выпуск сертификата, проверка домена, dry-run продления и закрытие TCP/80 |
| 09 | Предложение установить Traffic Control, применение списков и самодиагностика |
| Итог | Проверка Xray, TLS, Unix-сокетов, контейнера, firewall, служб и вывод профиля |

Traffic Control устанавливается последним — после загрузок и первичного ACME-цикла. Итоговая проверка выполняется уже со всеми компонентами.

## Требования

- чистый сервер Ubuntu 22.04/24.04 или Debian 12/13;
- архитектура `x86_64` или `arm64`, права `root` и systemd;
- прямой публичный адрес и свободные TCP-порты `80`, `443` и порт API;
- домен с A/AAAA-записями только на адреса этого сервера, без CDN-проксирования;
- Remnawave Panel 3.3.0+;
- созданная нода с API-портом `2222` и полным `SECRET_KEY`;
- исходящий IP панели и email для Let's Encrypt;
- аварийная консоль хостера на время первой установки.

## Быстрая установка

Запустите от `root`:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/leonidkopysov/CheburNET-Vision-Installer/main/cheburnet-vision-install.sh)
```

## Установка с проверкой SHA-256

```bash
curl -fsSLO https://raw.githubusercontent.com/leonidkopysov/CheburNET-Vision-Installer/main/cheburnet-vision-install.sh
curl -fsSLO https://raw.githubusercontent.com/leonidkopysov/CheburNET-Vision-Installer/main/SHA256SUMS
sha256sum -c SHA256SUMS && bash ./cheburnet-vision-install.sh
```

Установщик дважды спрашивает разрешение перед системными изменениями: сначала на обновление индекса APT, затем на установку компонентов и рассчитанный `full-upgrade`. Phased updates Ubuntu не форсируются.

> [!CAUTION]
> Установка рассчитана на отдельный чистый сервер. Не закрывайте текущую SSH-сессию до проверки повторного входа. Секретный ключ ноды никогда не публикуйте в Issues или диагностических отчётах.

## Продвинутая настройка — Auto Tuning

Встроенный ЧебурNET Auto Tuning рассчитывает настройки по CPU и RAM и применяет их до первого запуска API:

<p align="center">
  <a href="assets/auto-tuning-scheme.jpeg">
    <img src="assets/auto-tuning-scheme.jpeg" alt="Схема работы ЧебурNET Auto Tuning" width="100%">
  </a>
</p>

- включает BBR и целевой `fq`, настраивает TCP/UDP-буферы, backlog и SYN backlog;
- рассчитывает `conntrack`, диапазон временных портов и безопасные сетевые параметры;
- создаёт и дважды проверяет ZRAM, добавляет безопасные VM-настройки;
- включает RPS для распределения обработки пакетов по доступным ядрам;
- подготавливает лимиты нагрузки и `NOFILE` для RemnaNode;
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

## Traffic Control

ЧебурNET Traffic Control — утилита сетевой защиты Linux-сервера от автоматического сканирования портов и нежелательных подключений. Блокирует известные IP-адреса и подсети сканеров на уровне `nftables`, включая сети российских государственных структур, Роскомнадзора и связанных с ними организаций при использовании соответствующих списков блокировки. Поддерживает IPv4/IPv6, три внешних списка, логирование и статистику срабатываний. Устанавливается только после согласия пользователя.

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
| ALPN | `h2`, `http/1.1` | выбор соответствующего Unix fallback |
| h2 fallback | `/run/xray-fallback/h2.sock` | HTTP/2-заглушка |
| h1 fallback | `/run/xray-fallback/h1.sock` | HTTP/1.1-заглушка |
| `rejectUnknownSni` | `true` | отклонение неизвестного SNI |
| DNS | AdGuard DoH, Comss DoH | шифрованное разрешение имён |
| `clients` | `[]` | клиентов динамически добавляет Remnawave |

### Шаблон профиля для копирования

Замените два вхождения `<ДОМЕН_НОДЫ>` своим доменом:

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
      {"type": "field", "ip": ["geoip:private"], "outboundTag": "BLOCK"},
      {"type": "field", "domain": ["geosite:private"], "outboundTag": "BLOCK"},
      {
        "type": "field",
        "domain": [
          "geosite:category-ads-all",
          "domain:analytics.google.com",
          "domain:adjust.net.in",
          "domain:amplitude.com",
          "domain:metrika.yandex.ru",
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
| `/opt/remnanode/tuning-report.log` | отчёт продвинутой настройки |
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
