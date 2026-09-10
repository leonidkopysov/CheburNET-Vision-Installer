#!/bin/sh
set -eu
limit_ok() {
    case "$1" in
        unlimited) return 0;;
        ''|*[!0-9]*) return 1;;
        *) [ "$1" -ge 1048576 ];;
    esac
}
# Читаем фактические Linux-лимиты текущей оболочки, включая unlimited
while read -r first second third soft hard _unit; do
    if [ "$first $second $third" = 'Max open files' ]; then
        limit_ok "$soft"
        limit_ok "$hard"
        exit 0
    fi
done < /proc/self/limits
echo '  ✗ ОШИБКА: не удалось подтвердить лимит открытых файлов контейнера' >&2
exit 1
