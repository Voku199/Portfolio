#!/bin/bash
# Nainstaluje denní zálohy na eeebox. Jde spouštět opakovaně, hotové kroky přeskočí.
#   sudo bash deploy/zalohy/instalace.sh
#
# 1. běh vyrobí klíč a řekne, co přidat na eeebox. 2. běh založí repozitář a zapne časovač.
# Heslo k záloze ulož i mimo RPi, bez něj je záloha po smrti SD karty k ničemu.
set -euo pipefail
[ "$EUID" -eq 0 ] || { echo "Spust pres sudo: sudo bash $0"; exit 1; }

HERE="$(dirname "$(readlink -f "$0")")"
EEEBOX_IP=10.0.0.132
EEEBOX_PORT=2222
EEEBOX_USER=voku
ENV=/etc/vokudev/restic-eeebox.env
KEY=/root/.ssh/zaloha_ed25519

command -v restic >/dev/null || apt-get install -y restic
install -d -m 700 /etc/vokudev /root/.ssh

if [ ! -f "$ENV" ]; then
  umask 077
  printf 'RESTIC_REPOSITORY=sftp:eeebox-zaloha:zalohy/rpi\nRESTIC_PASSWORD=%s\n' "$(openssl rand -base64 32)" > "$ENV"
  umask 022
  echo "Vytvořeno $ENV. Heslo si ulož mimo RPi: sudo cat $ENV"
fi

[ -f "$KEY" ] || ssh-keygen -q -t ed25519 -N '' -C 'rpi-zaloha' -f "$KEY"
grep -q '^Host eeebox-zaloha$' /root/.ssh/config 2>/dev/null || cat >> /root/.ssh/config <<EOF
Host eeebox-zaloha
    HostName $EEEBOX_IP
    Port $EEEBOX_PORT
    User $EEEBOX_USER
    IdentityFile $KEY
    IdentitiesOnly yes
EOF
chmod 600 /root/.ssh/config
ssh-keygen -F "[$EEEBOX_IP]:$EEEBOX_PORT" -f /root/.ssh/known_hosts >/dev/null 2>&1 \
  || ssh-keyscan -p "$EEEBOX_PORT" "$EEEBOX_IP" >> /root/.ssh/known_hosts 2>/dev/null

if ! ssh -o BatchMode=yes -o ConnectTimeout=8 eeebox-zaloha 'mkdir -p zalohy'; then
  echo
  echo "Teď přidej tenhle klíč na eeebox do ~/.ssh/authorized_keys a spusť skript znovu:"
  echo
  cat "$KEY.pub"
  exit 2
fi

set -a; . "$ENV"; set +a
restic cat config >/dev/null 2>&1 || restic init

install -m 755 "$HERE/zaloha.sh" /usr/local/sbin/vokudev-zaloha
install -m 644 "$HERE/vokudev-zaloha.service" "$HERE/vokudev-zaloha.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vokudev-zaloha.timer
systemctl list-timers vokudev-zaloha.timer --no-pager
echo
echo "Hotovo. První zálohu pusť hned: sudo systemctl start --no-block vokudev-zaloha"
echo "Průběh: journalctl -fu vokudev-zaloha"
