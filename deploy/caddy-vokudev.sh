#!/bin/bash
# Nahradí blok vokudev.cz v Caddyfile blokem z deploy/vokudev.caddy. Spouští se jednou (a po změně bloku):
#   sudo bash /home/voku/vokudev/deploy/caddy-vokudev.sh
# Ostatních bloků se nedotkne. Když nová konfigurace neprojde validací, vrátí zálohu.
set -euo pipefail
[ "$EUID" -eq 0 ] || { echo "Spust pres sudo: sudo bash $0"; exit 1; }

CF=/etc/caddy/Caddyfile
NEW="$(dirname "$(readlink -f "$0")")/vokudev.caddy"
BAK="$CF.bak-$(date +%Y%m%d-%H%M%S)"
cp "$CF" "$BAK"

# vyhodí každý blok, jehož hlavička obsahuje vokudev.cz (počítá složené závorky, takže i vnořené bloky)
awk '
  depth == 0 && /vokudev\.cz/ && /\{[[:space:]]*$/ { skip = 1 }
  {
    line = $0
    opens = gsub(/\{/, "{", line); closes = gsub(/\}/, "}", line)
    if (!skip) print
    depth += opens - closes
    if (skip && depth == 0) skip = 0
  }
' "$BAK" | cat -s > "$CF.tmp"
{ cat "$CF.tmp"; echo; grep -v '^#' "$NEW"; } > "$CF"
rm -f "$CF.tmp"

# Caddy musí projít /home/voku a číst web
setfacl -m u:caddy:--x /home/voku
setfacl -R -m u:caddy:rX /home/voku/vokudev

if out=$(caddy validate --config "$CF" --adapter caddyfile 2>&1); then
  systemctl reload caddy
  echo "OK: Caddy nacten, zaloha $BAK"
else
  echo "$out" | tail -5
  cp "$BAK" "$CF"
  echo "CHYBA: nova konfigurace neprosla, vracena zaloha $BAK"
  exit 1
fi
