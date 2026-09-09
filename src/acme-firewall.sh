#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C
# Only rules with this exact owned comment are removed. Never reset the firewall.
readonly OWN_COMMENT=CheburNET-Vision-ACME-temporary
remove_own_rules() {
    local n
    while IFS= read -r n; do
        [[ $n =~ ^[0-9]+$ ]] || continue
        ufw --force delete "$n" >/dev/null
    done < <(ufw status numbered | awk -v comment="$OWN_COMMENT" \
      'index($0,comment) {if(match($0,/\[[ ]*[0-9]+\]/)){n=substr($0,RSTART,RLENGTH);gsub(/[^0-9]/,"",n); print n}}' | sort -rn)
}
remove_own_traffic_control_rules() {
    local handle
    nft list chain inet cheburnet_tc ingress >/dev/null 2>&1 || return 0
    while IFS= read -r handle; do
        [[ $handle =~ ^[0-9]+$ ]] || continue
        nft delete rule inet cheburnet_tc ingress handle "$handle"
    done < <(
        nft -a list chain inet cheburnet_tc ingress | awk -v comment="$OWN_COMMENT" \
          'index($0,"comment \"" comment "\"") {for(i=1;i<=NF;i++) if($i=="handle") print $(i+1)}'
    )
}
case "${1:-}" in
    open)
        ufw status | awk '/^Status: active$/ {ok=1} END {exit !ok}'
        remove_own_rules
        remove_own_traffic_control_rules
        # Traffic Control runs before UFW. Its temporary return lets the ACME
        # validator reach the UFW rule without weakening any other port.
        if nft list chain inet cheburnet_tc ingress >/dev/null 2>&1; then
            nft insert rule inet cheburnet_tc ingress tcp dport 80 counter return comment "$OWN_COMMENT"
        fi
        ufw insert 1 allow 80/tcp comment "$OWN_COMMENT" >/dev/null
        ;;
    close)
        remove_own_rules
        remove_own_traffic_control_rules
        ;;
    *) exit 2;;
esac
