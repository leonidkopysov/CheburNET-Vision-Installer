#!/usr/bin/env bash
set -Eeuo pipefail
BASE=/opt/remnanode
[[ -f $BASE/.cheburnet-managed ]] || exit 0
domain=$(python3 -c 'import json;print(json.load(open("/opt/remnanode/settings.json"))["domain"])')
[[ ${RENEWED_LINEAGE:-} == "/etc/letsencrypt/live/$domain" ]] || exit 0
docker exec remnanode xray run -test -config /opt/cheburnet/profile.json
# A successful renewal triggers a short node restart; the panel restores active config.
docker restart remnanode >/dev/null
