#!/usr/bin/env bash
set -Eeuo pipefail
export LC_ALL=C
BASE=/opt/remnanode
[[ -f $BASE/.cheburnet-managed ]] || exit 1
command -v sshd >/dev/null || { echo 'Ошибка: не найден sshd из пакета openssh-server.' >&2; exit 1; }
SSH_MODE=''
if systemctl is-active --quiet ssh.service; then
    SSH_MODE=service
elif systemctl is-active --quiet ssh.socket; then
    SSH_MODE=socket
else
    echo 'Ошибка: не найдена активная служба ssh.service или ssh.socket.' >&2
    exit 1
fi
install -d -m 700 "$BASE/backups"
# Only these agreed connection limits are changed. Authentication and TCP
# forwarding retain their effective configuration, including Match sections.
sshd -t
sshd -T > "$BASE/backups/sshd-effective-before.txt"
SSH_DROPIN=/etc/ssh/sshd_config.d/00-cheburnet-vision.conf
[[ ! -L $SSH_DROPIN ]] || { echo 'Ошибка: SSH drop-in является ссылкой.' >&2; exit 1; }
# Первоначальный снимок хранится отдельно от отката текущей попытки
if [[ ! -e $BASE/backups/sshd-initial.saved ]]; then
    if [[ -f $SSH_DROPIN ]]; then
        cp -p "$SSH_DROPIN" "$BASE/backups/sshd-dropin-initial.conf"
    fi
    cp -p "$BASE/backups/sshd-effective-before.txt" "$BASE/backups/sshd-effective-initial.txt"
    touch "$BASE/backups/sshd-initial.saved"
fi
HAD_DROPIN=0
if [[ -f $SSH_DROPIN ]]; then
    cp -p "$SSH_DROPIN" "$BASE/backups/sshd-dropin-before.conf"
    HAD_DROPIN=1
fi
restore_ssh() {
    if [[ $HAD_DROPIN == 1 ]]; then
        cp -p "$BASE/backups/sshd-dropin-before.conf" "$SSH_DROPIN"
    else
        # Keep a harmless empty owned file; do not delete any SSH configuration.
        : > "$SSH_DROPIN"
    fi
    if [[ $SSH_MODE == service ]]; then
        systemctl try-reload-or-restart ssh.service >/dev/null 2>&1 || true
    else
        systemctl daemon-reload >/dev/null 2>&1 || true
    fi
    echo 'Ошибка применения SSH: предыдущая конфигурация восстановлена.' >&2
}
install -d -m 755 /etc/ssh/sshd_config.d
cat > "$SSH_DROPIN" <<'CONF'
# ЧебурNET Vision: ограничения SSH; AllowTcpForwarding не изменяется.
MaxAuthTries 3
LoginGraceTime 30
AllowAgentForwarding no
PermitTunnel no
X11Forwarding no
GatewayPorts no
CONF
chmod 644 "$SSH_DROPIN"
if ! sshd -t; then restore_ssh; exit 1; fi
sshd -T > "$BASE/backups/sshd-effective-after.txt"
if ! python3 - "$BASE/backups" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
def read(name):
    return dict(line.split(None,1) for line in (p/name).read_text(encoding='utf-8').splitlines() if ' ' in line)
before=read('sshd-effective-before.txt');after=read('sshd-effective-after.txt')
expected={'maxauthtries':'3','logingracetime':'30','allowagentforwarding':'no',
          'permittunnel':'no','x11forwarding':'no','gatewayports':'no'}
ok=all(after.get(k)==v for k,v in expected.items())
ok=ok and all(after.get(k)==before.get(k) for k in ('allowtcpforwarding',
    'passwordauthentication','pubkeyauthentication','permitrootlogin',
    'kbdinteractiveauthentication','authenticationmethods'))
if not ok: print('Действующие правила SSH конфликтуют с предложенными ограничениями.',file=sys.stderr)
sys.exit(0 if ok else 1)
PY
then restore_ssh; exit 1; fi
if [[ $SSH_MODE == service ]]; then
    if ! systemctl try-reload-or-restart ssh.service; then restore_ssh; exit 1; fi
else
    # daemon-reload повторно запускает sshd-generator Ubuntu 24.04.
    if ! systemctl daemon-reload || ! systemctl is-active --quiet ssh.socket; then
        restore_ssh
        exit 1
    fi
fi
echo '✓ SSH: ограничения применены; AllowTcpForwarding и способ входа сохранены.'
# Do not rewrite the vendor tuner. Apply the agreed TFO setting separately.
TFO=/etc/sysctl.d/99-cheburnet-tcp-fastopen.conf
[[ ! -L $TFO ]] || { echo 'Ошибка: файл TCP Fast Open является ссылкой.' >&2; exit 1; }
if [[ -f $TFO && ! -f $BASE/backups/tcp-fastopen.conf ]]; then
    cp -p "$TFO" "$BASE/backups/tcp-fastopen.conf"
fi
printf 'net.ipv4.tcp_fastopen = 3\n' > "$TFO"
chmod 644 "$TFO"
sysctl -p "$TFO"
