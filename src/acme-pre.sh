#!/usr/bin/env bash
set -Eeuo pipefail
[[ -f /opt/remnanode/.cheburnet-managed ]] || exit 0
[[ -x /opt/remnanode/acme-firewall.sh ]] || {
    printf '  ✗ ОШИБКА: не найден обработчик firewall установленной ноды\n' >&2
    exit 1
}
exec /opt/remnanode/acme-firewall.sh open
