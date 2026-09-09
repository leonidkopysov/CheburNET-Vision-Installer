#!/usr/bin/env bash
set -Eeuo pipefail
# Если helper сохранился, закрываем собственные правила даже без маркера.
# Это не позволяет пропустить очистку после частичного удаления компонента.
if [[ ! -x /opt/remnanode/acme-firewall.sh ]]; then
    [[ ! -f /opt/remnanode/.cheburnet-managed ]] || {
        printf '  ✗ ОШИБКА: обработчик firewall отсутствует; проверьте временные правила TCP/80\n' >&2
        exit 1
    }
    exit 0
fi
exec /opt/remnanode/acme-firewall.sh close
