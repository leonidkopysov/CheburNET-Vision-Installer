#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C
# Only rules with this exact owned comment are removed. Never reset the firewall.
readonly OWN_COMMENT=CheburNET-Vision-ACME-temporary
readonly ACME_MARKER=/run/cheburnet-vision-acme.active
# Та же блокировка, что у TC: обновление списков сохраняет активное исключение
exec 8>/run/cheburnet-traffic-control.lock
flock -w 600 8 || { echo '  ✗ ОШИБКА: не удалось дождаться блокировки Traffic Control' >&2; exit 1; }
[[ ! -L $ACME_MARKER ]] || { echo '  ✗ ОШИБКА: отметка ACME является ссылкой' >&2; exit 1; }
remove_own_rules() {
    local n rules
    rules=$(ufw status numbered) || return "$?"
    while IFS= read -r n; do
        [[ $n =~ ^[0-9]+$ ]] || continue
        ufw --force delete "$n" >/dev/null || return "$?"
    done < <(printf '%s\n' "$rules" | awk -v comment="$OWN_COMMENT" \
      'index($0,comment) {if(match($0,/\[[ ]*[0-9]+\]/)){n=substr($0,RSTART,RLENGTH);gsub(/[^0-9]/,"",n); print n}}' | sort -rn)
}
remove_own_traffic_control_rules() {
    local handle tables rules
    tables=$(nft list tables) || return "$?"
    [[ $tables == *'table inet cheburnet_tc'* ]] || return 0
    rules=$(nft -a list chain inet cheburnet_tc ingress) || return "$?"
    while IFS= read -r handle; do
        [[ $handle =~ ^[0-9]+$ ]] || continue
        nft delete rule inet cheburnet_tc ingress handle "$handle" || return "$?"
    done < <(
        printf '%s\n' "$rules" | awk -v comment="$OWN_COMMENT" \
          'index($0,"comment \"" comment "\"") {for(i=1;i<=NF;i++) if($i=="handle") print $(i+1)}'
    )
    if nft list set inet cheburnet_tc acme_ports >/dev/null 2>&1; then
        nft flush set inet cheburnet_tc acme_ports
    fi
}
close_acme() {
    remove_own_rules || return "$?"
    remove_own_traffic_control_rules || return "$?"
    # При ошибке удаления отметка остаётся для следующей попытки таймера
    rm -f -- "$ACME_MARKER"
}
cleanup_failed_open() {
    local rc=$?
    if (( rc != 0 )); then close_acme || true; fi
}
case "${1:-}" in
    open)
        trap cleanup_failed_open EXIT
        ufw status | awk '/^Status: active$/ {ok=1} END {exit !ok}'
        remove_own_rules
        remove_own_traffic_control_rules
        # Часовой срок ограничивает исключение даже при аварии Certbot
        (umask 077; printf '%s\n' "$(($(date +%s) + 3600))" > "$ACME_MARKER")
        # Traffic Control runs before UFW. Its temporary return lets the ACME
        # validator reach the UFW rule without weakening any other port.
        if nft list chain inet cheburnet_tc ingress >/dev/null 2>&1; then
            if ! nft list set inet cheburnet_tc acme_ports >/dev/null 2>&1; then
                nft 'add set inet cheburnet_tc acme_ports { type inet_service; flags timeout; }'
            fi
            nft 'add element inet cheburnet_tc acme_ports { 80 timeout 3600s }'
            nft insert rule inet cheburnet_tc ingress tcp dport @acme_ports counter return comment "$OWN_COMMENT"
        fi
        ufw insert 1 allow 80/tcp comment "$OWN_COMMENT" >/dev/null
        ;;
    close)
        close_acme
        ;;
    expire)
        if [[ -f $ACME_MARKER ]]; then
            expires=$(<"$ACME_MARKER")
            if [[ ! $expires =~ ^[0-9]{1,12}$ ]] || (( expires <= $(date +%s) )); then
                close_acme
            fi
        fi
        ;;
    *) exit 2;;
esac
